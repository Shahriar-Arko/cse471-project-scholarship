import os
import time
from werkzeug.utils import secure_filename
from flask import render_template, request, jsonify, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from mongoengine.queryset.visitor import Q

from app.models.professor import Professor
from app.models.user import User
from app.models.pitch import ResearchPitch
from app.models.vacancy import Vacancy, VacancyApplication
from . import student_bp

ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'png', 'jpg', 'jpeg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@student_bp.route('/professor-finder', methods=['GET'])
@login_required
def professor_finder():
    if current_user.role != 'student':
        return redirect(url_for('dashboard'))
    
    countries = sorted([c for c in set(Professor.objects.distinct('country')) if c])
    institutions = sorted([i for i in set(Professor.objects.distinct('institution')) if i])
    departments = sorted([d for d in set(Professor.objects.distinct('department')) if d])
    domains = sorted([dom for dom in set(Professor.objects.distinct('primary_domain')) if dom])
    
    bookmarked_ids = []
    if hasattr(current_user, 'bookmarked_professors') and current_user.bookmarked_professors:
        for p in current_user.bookmarked_professors:
            try:
                if p and p.id:
                    bookmarked_ids.append(str(p.id))
            except Exception:
                continue

    return render_template(
        'dashboard/professor_finder.html',
        countries=countries,
        institutions=institutions,
        departments=departments,
        domains=domains,
        bookmarked_ids=bookmarked_ids
    )


@student_bp.route('/api/professors', methods=['GET'])
@login_required
def api_get_professors():
    """Directory query engine for faculty discovery."""
    query_text = request.args.get('search', '').strip()
    country = request.args.get('country', '').strip()
    institution = request.args.get('institution', '').strip()
    department = request.args.get('department', '').strip()
    domain = request.args.get('domain', '').strip()
    funding_only = request.args.get('funding_only', 'false').lower() == 'true'
    bookmarked_only = request.args.get('bookmarked_only', 'false').lower() == 'true'
    pitched_only = request.args.get('pitched_only', 'false').lower() == 'true'

    query = Q()

    if query_text:
        query &= (
            Q(full_name__icontains=query_text) |
            Q(institution__icontains=query_text) |
            Q(department__icontains=query_text) |
            Q(primary_domain__icontains=query_text) |
            Q(research_interests__icontains=query_text) |
            Q(lab_name__icontains=query_text)
        )

    if country:
        query &= Q(country=country)
    if institution:
        query &= Q(institution=institution)
    if department:
        query &= Q(department=department)
    if domain:
        query &= Q(primary_domain=domain)
    if funding_only:
        query &= Q(has_funding=True) & Q(accepting_students=True)

    student_bookmarked_ids = set()
    if hasattr(current_user, 'bookmarked_professors') and current_user.bookmarked_professors:
        for p in current_user.bookmarked_professors:
            try:
                if p and p.id:
                    student_bookmarked_ids.add(str(p.id))
            except Exception:
                continue

    student_pitches = {}
    for pitch in ResearchPitch.objects(student=current_user.id):
        try:
            if pitch.professor:
                student_pitches[str(pitch.professor.id)] = pitch
        except Exception:
            continue

    if bookmarked_only:
        query &= Q(id__in=list(student_bookmarked_ids))

    if pitched_only:
        query &= Q(id__in=list(student_pitches.keys()))

    professors = Professor.objects(query).order_by('-created_at')

    results = []
    for prof in professors:
        prof_id_str = str(prof.id)
        
        pubs = []
        for pub in prof.publications:
            pubs.append({
                'title': pub.title,
                'year': pub.year,
                'venue': pub.venue,
                'citation_url': pub.citation_url,
                'citations_count': pub.citations_count
            })

        grants = []
        for g in prof.grant_projects:
            grants.append({
                'title': g.title,
                'agency': g.agency,
                'amount': g.amount,
                'status': g.status
            })

        pitch_info = None
        prof_pitch = student_pitches.get(prof_id_str)
        if prof_pitch:
            pitch_info = {
                'id': str(prof_pitch.id),
                'status': prof_pitch.status,
                'target_domain': prof_pitch.target_domain,
                'pitch_text': prof_pitch.pitch_text,
                'created_at': prof_pitch.created_at.strftime('%b %d, %Y')
            }

        results.append({
            'id': prof_id_str,
            'full_name': prof.full_name,
            'title': prof.title,
            'email': prof.email,
            'avatar_url': prof.avatar_url,
            'institution': prof.institution,
            'department': prof.department,
            'country': prof.country,
            'office_location': prof.office_location,
            'website_url': prof.website_url,
            'primary_domain': prof.primary_domain,
            'research_interests': prof.research_interests or [],
            'bio_summary': prof.bio_summary or '',
            'lab_name': prof.lab_name or 'Independent Research Lab',
            'lab_website': prof.lab_website or '',
            'accepting_students': prof.accepting_students,
            'has_funding': prof.has_funding,
            'funding_types': prof.funding_types or [],
            'open_positions_count': prof.open_positions_count,
            'publications': pubs,
            'grant_projects': grants,
            'is_bookmarked': prof_id_str in student_bookmarked_ids,
            'pitch_info': pitch_info
        })

    return jsonify({'status': 'success', 'count': len(results), 'professors': results})


# =========================================================================
# STUDENT RA/TA VACANCY DISCOVERY & APPLICATION (WITH FILE UPLOADS)
# =========================================================================

@student_bp.route('/api/vacancies', methods=['GET'])
@login_required
def get_student_vacancies():
    """Fetches active RA/TA vacancies with remaining slot calculation and student status."""
    try:
        vacancies = Vacancy.objects(is_active=True).order_by('-created_at')
        
        my_applications = {}
        for app in VacancyApplication.objects(student=current_user.id):
            if app.vacancy:
                my_applications[str(app.vacancy.id)] = app
        
        # Safely parse student CGPA
        student_gpa_raw = getattr(current_user, 'gpa', 3.5)
        try:
            student_gpa_float = float(student_gpa_raw) if student_gpa_raw else 3.5
        except (ValueError, TypeError):
            student_gpa_float = 3.5

        results = []
        for v in vacancies:
            prof = v.professor
            if not prof:
                continue

            app = my_applications.get(str(v.id))
            min_cgpa_req = float(v.min_cgpa or 3.0)
            
            # Calculate remaining slots: total openings minus accepted/offered applicants
            offered_count = VacancyApplication.objects(vacancy=v, status='Offered').count()
            total_openings = int(v.openings_count or 1)
            remaining_slots = max(0, total_openings - offered_count)
            is_full = (remaining_slots <= 0)

            results.append({
                'id': str(v.id),
                'title': v.title,
                'position_type': v.position_type,
                'department': v.department,
                'domain': v.domain,
                'funding_stipend': v.funding_stipend,
                'openings_count': total_openings,
                'remaining_slots': remaining_slots,
                'is_full': is_full,
                'min_cgpa': min_cgpa_req,
                'is_eligible': student_gpa_float >= min_cgpa_req,
                'student_gpa': student_gpa_float,
                'target_degrees': v.target_degrees or ['Masters', 'PhD'],
                'required_skills': v.required_skills or [],
                'description': v.description,
                'created_at': v.created_at.strftime('%b %d, %Y') if v.created_at else 'Recent',
                'professor': {
                    'id': str(prof.id),
                    'full_name': prof.full_name,
                    'institution': prof.institution,
                    'lab_name': prof.lab_name or 'Research Lab',
                    'avatar_url': getattr(prof, 'avatar_url', None)
                },
                'application_status': app.status if app else None,
                'applied_at': app.created_at.strftime('%b %d, %Y') if app and app.created_at else None
            })

        return jsonify({'status': 'success', 'vacancies': results})
    except Exception as e:
        print(f"[VACANCIES API ERROR]: {e}")
        return jsonify({'status': 'error', 'error': str(e)}), 500


@student_bp.route('/api/vacancies/apply/<vacancy_id>', methods=['POST'])
@login_required
def apply_for_vacancy(vacancy_id):
    """Submits a direct application with up to 3 document attachments."""
    if current_user.role != 'student':
        return jsonify({'error': 'Unauthorized: Only students can apply.'}), 403

    try:
        vacancy = Vacancy.objects(id=vacancy_id, is_active=True).first()
        if not vacancy:
            return jsonify({'error': 'Position is no longer active or available.'}), 404

        # Check if all slots are filled
        offered_count = VacancyApplication.objects(vacancy=vacancy, status='Offered').count()
        if offered_count >= vacancy.openings_count:
            return jsonify({'error': 'All vacancy positions for this lab opening have been filled.'}), 400

        student = User.objects(id=current_user.id).first()
        if not student:
            return jsonify({'error': 'Student account not found.'}), 404

        # Duplicate check
        existing = VacancyApplication.objects(student=student, vacancy=vacancy).first()
        if existing:
            return jsonify({'error': 'You have already submitted an application for this position.'}), 400

        cover_letter = request.form.get('cover_letter', '').strip()
        if not cover_letter:
            return jsonify({'error': 'Statement of interest / Cover letter cannot be empty.'}), 400

        # Handle up to 3 document uploads
        uploaded_docs = []
        files = request.files.getlist('documents')
        if len(files) > 3:
            return jsonify({'error': 'A maximum of 3 documents can be uploaded.'}), 400

        upload_dir = os.path.join(current_app.root_path, 'static', 'uploads', 'applications')
        os.makedirs(upload_dir, exist_ok=True)

        for file in files:
            if file and file.filename and allowed_file(file.filename):
                original_name = secure_filename(file.filename)
                unique_name = f"{int(time.time())}{str(current_user.id)[:6]}{original_name}"
                file_path = os.path.join(upload_dir, unique_name)
                file.save(file_path)
                
                uploaded_docs.append({
                    'name': original_name,
                    'url': f"/static/uploads/applications/{unique_name}"
                })

        student_gpa_val = None
        raw_gpa = getattr(student, 'gpa', None)
        if raw_gpa is not None:
            try:
                student_gpa_val = float(raw_gpa)
            except (ValueError, TypeError):
                student_gpa_val = None

        application = VacancyApplication(
            vacancy=vacancy,
            student=student,
            professor=vacancy.professor,
            cover_letter=cover_letter,
            documents=uploaded_docs,
            applicant_cgpa=student_gpa_val,
            applicant_major=getattr(student, 'major', 'Computer Science') or 'General',
            applicant_degree=getattr(student, 'degree_level', 'Masters') or 'Masters',
            status='Submitted'
        )
        application.save()

        prof_name = vacancy.professor.full_name if vacancy.professor else "the faculty member"
        return jsonify({
            'status': 'success',
            'message': f'Application and {len(uploaded_docs)} document(s) successfully delivered to Prof. {prof_name}!'
        }), 200

    except Exception as e:
        print(f"[VACANCY APPLY ERROR]: {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500


@student_bp.route('/api/professors/bookmark/<prof_id>', methods=['POST'])
@login_required
def toggle_bookmark(prof_id):
    if current_user.role != 'student':
        return jsonify({'error': 'Unauthorized'}), 403

    professor = Professor.objects(id=prof_id).first()
    if not professor:
        return jsonify({'error': 'Professor not found'}), 404

    if not hasattr(current_user, 'bookmarked_professors') or current_user.bookmarked_professors is None:
        current_user.bookmarked_professors = []

    is_bookmarked = False
    existing_ids = []
    for p in current_user.bookmarked_professors:
        try:
            if p and p.id:
                existing_ids.append(str(p.id))
        except Exception:
            continue

    if str(professor.id) in existing_ids:
        current_user.bookmarked_professors = [
            p for p in current_user.bookmarked_professors if p and str(p.id) != str(professor.id)
        ]
        is_bookmarked = False
        message = f"Removed {professor.full_name} from your research pipeline."
    else:
        current_user.bookmarked_professors.append(professor)
        is_bookmarked = True
        message = f"Shortlisted {professor.full_name} into your research pipeline!"

    current_user.save()
    return jsonify({
        'status': 'success',
        'is_bookmarked': is_bookmarked,
        'message': message
    })


@student_bp.route('/api/professors/pitch/<prof_id>', methods=['POST'])
@login_required
def submit_pitch(prof_id):
    if current_user.role != 'student':
        return jsonify({'error': 'Unauthorized: Only students can submit pitches.'}), 403

    try:
        professor = Professor.objects(id=prof_id).first()
        if not professor:
            return jsonify({'error': 'Professor not found.'}), 404

        student = User.objects(id=current_user.id).first()
        data = request.get_json(silent=True) or {}
        target_domain = data.get('target_domain', '').strip()
        pitch_text = data.get('pitch_text', '').strip()

        if not target_domain or not pitch_text:
            return jsonify({'error': 'Please select a research area and write your pitch.'}), 400

        existing_pitch = ResearchPitch.objects(student=student, professor=professor).first()
        if existing_pitch:
            return jsonify({'error': f'You have already submitted a research pitch to {professor.full_name}.'}), 400

        new_pitch = ResearchPitch(
            student=student,
            professor=professor,
            target_domain=target_domain,
            pitch_text=pitch_text
        )
        new_pitch.save()

        return jsonify({
            'status': 'success',
            'message': f'Your research pitch has been sent to {professor.full_name}!',
            'pitch_info': {
                'id': str(new_pitch.id),
                'status': new_pitch.status,
                'target_domain': new_pitch.target_domain,
                'pitch_text': new_pitch.pitch_text,
                'created_at': new_pitch.created_at.strftime('%b %d, %Y')
            }
        }), 200

    except Exception as e:
        print(f"[PITCH SUBMIT ERROR] {e}")
        return jsonify({'error': f'Server error: {str(e)}'}), 500