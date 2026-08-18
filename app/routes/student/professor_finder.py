from flask import render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from mongoengine.queryset.visitor import Q

from app.models.professor import Professor
from app.models.user import User
from app.models.pitch import ResearchPitch
from . import student_bp

@student_bp.route('/professor-finder', methods=['GET'])
@login_required
def professor_finder():
    if current_user.role != 'student':
        return redirect(url_for('dashboard'))
    
    # Extract unique filter values dynamically from database
    countries = sorted([c for c in set(Professor.objects.distinct('country')) if c])
    institutions = sorted([i for i in set(Professor.objects.distinct('institution')) if i])
    departments = sorted([d for d in set(Professor.objects.distinct('department')) if d])
    domains = sorted([dom for dom in set(Professor.objects.distinct('primary_domain')) if dom])
    
    # Extract student's bookmarked professor IDs safely
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
    """Live multi-parameter search & query engine with pitch tracking."""
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

    # 1. Fetch student's bookmarked professor IDs
    student_bookmarked_ids = set()
    if hasattr(current_user, 'bookmarked_professors') and current_user.bookmarked_professors:
        for p in current_user.bookmarked_professors:
            try:
                if p and p.id:
                    student_bookmarked_ids.add(str(p.id))
            except Exception:
                continue

    # 2. Fetch all pitches submitted by this student
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
        
        # Serialize publications
        pubs = []
        for pub in prof.publications:
            pubs.append({
                'title': pub.title,
                'year': pub.year,
                'venue': pub.venue,
                'citation_url': pub.citation_url,
                'citations_count': pub.citations_count
            })

        # Serialize grants
        grants = []
        for g in prof.grant_projects:
            grants.append({
                'title': g.title,
                'agency': g.agency,
                'amount': g.amount,
                'status': g.status
            })

        # Attach pitch status if the student has applied
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


@student_bp.route('/api/professors/bookmark/<prof_id>', methods=['POST'])
@login_required
def toggle_bookmark(prof_id):
    """Toggle bookmark / shortlist status for student research pipeline."""
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
    """Handles structured research pitch submissions with instant feedback serialization."""
    if current_user.role != 'student':
        return jsonify({'error': 'Unauthorized: Only students can submit pitches.'}), 403

    try:
        professor = Professor.objects(id=prof_id).first()
        if not professor:
            return jsonify({'error': 'Professor not found.'}), 404

        student = User.objects(id=current_user.id).first()
        if not student:
            return jsonify({'error': 'Student user not found.'}), 404

        data = request.get_json(silent=True) or {}
        target_domain = data.get('target_domain', '').strip()
        pitch_text = data.get('pitch_text', '').strip()

        if not target_domain or not pitch_text:
            return jsonify({'error': 'Please select a research area and write your pitch.'}), 400
            
        if len(pitch_text) > 1500:
            return jsonify({'error': 'Pitch exceeds the 1500 character limit.'}), 400

        # Prevent duplicate pitch
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