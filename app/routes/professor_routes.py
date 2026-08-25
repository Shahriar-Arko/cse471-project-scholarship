import os
import smtplib
import threading
from email.message import EmailMessage
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models.professor import Professor
from app.models.pitch import ResearchPitch
from app.models.user import User
# from app.models.vacancy import Vacancy, VacancyApplication
from app.models.research_profile import StudentResearchProfile
from app.services.research_analyzer_service import cosine_similarity, get_gemini_embedding

professor_bp = Blueprint('professor', __name__, url_prefix='/professor')

def send_student_email_async(to_email, student_name, prof_name, subject, message_body):
    """Sends direct email from professor to student asynchronously via Gmail SMTP."""
    try:
        sender_email = os.environ.get('MAIL_USERNAME')
        sender_password = os.environ.get('MAIL_PASSWORD')
        
        if not sender_email or not sender_password:
            print(f"[DEV EMAIL LOG] To: {to_email} | Subject: {subject} | Body:\n{message_body}")
            return

        msg = EmailMessage()
        msg['Subject'] = f"ScholarMatch: {subject}"
        msg['From'] = f"{prof_name} via ScholarMatch <{sender_email}>"
        msg['To'] = to_email
        msg['Reply-To'] = prof_email
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #f8fafc;">
            <div style="text-align: center; margin-bottom: 20px;">
                <h2 style="color: #059669; margin: 0;">ScholarMatch Research Portal</h2>
                <p style="color: #64748b; font-size: 13px;">Faculty Notification on Research Position</p>
            </div>
            
            <p style="color: #334155; font-size: 15px;">Dear <strong>{student_name}</strong>,</p>
            
            <p style="color: #334155; font-size: 15px; line-height: 1.6;">
                <strong>Prof. {prof_name}</strong> has reached out to you regarding research collaboration:
            </p>
            
            <div style="background-color: #ffffff; padding: 18px; border-radius: 8px; border-left: 4px solid #059669; margin: 20px 0; color: #1e293b; font-size: 14px; line-height: 1.6; white-space: pre-wrap;">
{message_body}
            </div>
            
            <p style="color: #64748b; font-size: 13px; margin-top: 24px; border-top: 1px solid #e2e8f0; padding-top: 12px; text-align: center;">
                You can review this decision in your ScholarMatch student dashboard under 'Apply for RA/TA'.
            </p>
        </div>
        """
        
        msg.set_content(message_body)
        msg.add_alternative(html_content, subtype='html')

        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(sender_email, sender_password)
            smtp.send_message(msg)
            
    except Exception as e:
        print(f"[PROFESSOR EMAIL ERROR]: {e}")


# =========================================================================
# STEP 5: AI CANDIDATE FILTER & INVITATIONS
# =========================================================================

@professor_bp.route('/candidates')
@login_required
def candidate_filter():
    """Renders the AI Candidate Filter pool ranked by alignment to professor's lab."""
    if current_user.role != 'professor':
        return redirect(url_for('dashboard'))

    prof = Professor.objects(id=current_user.id).first()
    visible_profiles = StudentResearchProfile.objects(is_visible_to_faculty=True)
    
    prof_text = f"{prof.primary_domain} {' '.join(prof.research_interests)} {prof.bio_summary or ''}"
    prof_vector = get_gemini_embedding(prof_text)

    ranked_candidates = []
    for p in visible_profiles:
        student = p.student
        if not student:
            continue

        sim = 0.5
        if prof_vector and p.embedding:
            sim = max(0.0, min(1.0, cosine_similarity(prof_vector, p.embedding)))
        
        # Calculate compatibility index
        score = round(min(98.0, max(50.0, (sim * 80.0) + 18.0)), 1)
        
        niches = [s.get('niche') for s in p.top_specializations if isinstance(s, dict)]

        ranked_candidates.append({
            'student_id': str(student.id),
            'student_name': student.full_name,
            'student_email': student.email,
            'degree_level': p.degree_level,
            'major': p.major,
            'cgpa': p.cgpa,
            'research_statement': p.research_statement,
            'top_niches': niches[:3],
            'technical_skills': p.technical_skills[:6],
            'compatibility_score': score
        })

    ranked_candidates.sort(key=lambda x: x['compatibility_score'], reverse=True)
    return render_template('dashboard/professor_candidates.html', candidates=ranked_candidates)


@professor_bp.route('/api/candidates/invite/<student_id>', methods=['POST'])
@login_required
def invite_candidate(student_id):
    """Sends direct invitation to student to apply for RA/TA position."""
    if current_user.role != 'professor':
        return jsonify({'error': 'Unauthorized'}), 403

    student = User.objects(id=student_id).first()
    if not student or not student.email:
        return jsonify({'error': 'Student not found.'}), 404

    data = request.get_json() or {}
    subject = data.get('subject', f"Research Opportunity in {current_user.lab_name}").strip()
    body = data.get('body', '').strip()

    if not body:
        return jsonify({'error': 'Invitation message body is required.'}), 400

    threading.Thread(
        target=send_student_email_async,
        args=(student.email, student.full_name, current_user.full_name,current_user.email, subject, body)
    ).start()

    return jsonify({'status': 'success', 'message': f'Invitation successfully delivered to {student.email}!'})


@professor_bp.route('/profile/setup', methods=['GET', 'POST'])
@login_required
def setup_profile():
    if current_user.role != 'professor':
        return redirect(url_for('dashboard'))

    prof = Professor.objects(id=current_user.id).first()

    if request.method == 'POST':
        prof.institution = request.form.get('institution', '').strip()
        prof.department = request.form.get('department', '').strip()
        prof.country = request.form.get('country', '').strip()
        prof.primary_domain = request.form.get('primary_domain', '').strip()
        prof.bio_summary = request.form.get('bio_summary', '').strip()
        prof.lab_name = request.form.get('lab_name', '').strip()
        prof.accepting_students = 'accepting_students' in request.form
        prof.has_funding = 'has_funding' in request.form
        
        prof.save()
        flash('Profile setup complete! Welcome to ScholarMatch.', 'success')
        return redirect(url_for('dashboard'))

    return render_template('dashboard/professor_profile_setup.html', prof=prof)


@professor_bp.route('/pipeline')
@login_required
def review_pipeline():
    if current_user.role != 'professor':
        return redirect(url_for('dashboard'))

    pitches = ResearchPitch.objects(professor=current_user.id).order_by('-created_at')
    return render_template('dashboard/professor_pipeline.html', pitches=pitches)


@professor_bp.route('/api/pitch/<pitch_id>/status', methods=['POST'])
@login_required
def update_pitch_status(pitch_id):
    if current_user.role != 'professor':
        return jsonify({'error': 'Unauthorized'}), 403

    pitch = ResearchPitch.objects(id=pitch_id, professor=current_user.id).first()
    if not pitch:
        return jsonify({'error': 'Pitch not found'}), 404

    data = request.get_json() or {}
    new_status = data.get('status')
    
    if new_status in ['pending', 'shortlisted', 'declined']:
        pitch.status = new_status
        pitch.save()
        return jsonify({'status': 'success', 'message': f'Application moved to {new_status.capitalize()}'})
    
    return jsonify({'error': 'Invalid status'}), 400


@professor_bp.route('/api/pitch/<pitch_id>/send-email', methods=['POST'])
@login_required
def send_email_to_student(pitch_id):
    if current_user.role != 'professor':
        return jsonify({'error': 'Unauthorized'}), 403

    pitch = ResearchPitch.objects(id=pitch_id, professor=current_user.id).first()
    if not pitch:
        return jsonify({'error': 'Application not found'}), 404

    student = pitch.student
    if not student or not student.email:
        return jsonify({'error': 'Student email not found'}), 404

    data = request.get_json() or {}
    subject = data.get('subject', '').strip()
    body = data.get('body', '').strip()

    if not subject or not body:
        return jsonify({'error': 'Subject and message body are required.'}), 400

    threading.Thread(
        target=send_student_email_async,
        args=(student.email, student.full_name, current_user.full_name, subject, body)
    ).start()

    return jsonify({'status': 'success', 'message': f'Email successfully sent to {student.email}!'})


@professor_bp.route('/postings')
@login_required
def manage_postings():
    if current_user.role != 'professor':
        return redirect(url_for('dashboard'))

    vacancies = Vacancy.objects(professor=current_user.id).order_by('-created_at')
    vacancy_list = []
    for v in vacancies:
        apps = VacancyApplication.objects(vacancy=v)
        offered = apps.filter(status='Offered').count()
        vacancy_list.append({
            'vacancy': v,
            'total_applicants': apps.count(),
            'shortlisted_count': apps.filter(status='Shortlisted').count(),
            'offered_count': offered,
            'remaining_slots': max(0, v.openings_count - offered)
        })

    return render_template('dashboard/professor_postings.html', vacancies_data=vacancy_list)