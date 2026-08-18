import os
import smtplib
import threading
from email.message import EmailMessage
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.models.professor import Professor
from app.models.pitch import ResearchPitch
from app.models.user import User

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
        
        html_content = f"""
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 24px; border: 1px solid #e2e8f0; border-radius: 12px; background-color: #f8fafc;">
            <div style="text-align: center; margin-bottom: 20px;">
                <h2 style="color: #059669; margin: 0;">ScholarMatch Research Portal</h2>
                <p style="color: #64748b; font-size: 13px;">Faculty Response to Research Expression of Interest</p>
            </div>
            
            <p style="color: #334155; font-size: 15px;">Dear <strong>{student_name}</strong>,</p>
            
            <p style="color: #334155; font-size: 15px; line-height: 1.6;">
                <strong>Prof. {prof_name}</strong> has reviewed your research pitch and sent you the following direct message:
            </p>
            
            <div style="background-color: #ffffff; padding: 18px; border-radius: 8px; border-left: 4px solid #059669; margin: 20px 0; color: #1e293b; font-size: 14px; line-height: 1.6; white-space: pre-wrap;">
{message_body}
            </div>
            
            <p style="color: #64748b; font-size: 13px; margin-top: 24px; border-top: 1px solid #e2e8f0; padding-top: 12px; text-align: center;">
                You can reply directly by logging into your ScholarMatch student dashboard.
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


@professor_bp.route('/profile/setup', methods=['GET', 'POST'])
@login_required
def setup_profile():
    # Ensure only professors can access this
    if current_user.role != 'professor':
        return redirect(url_for('dashboard'))

    prof = Professor.objects(id=current_user.id).first()

    if request.method == 'POST':
        # Update fields from the form
        prof.institution = request.form.get('institution', '').strip()
        prof.department = request.form.get('department', '').strip()
        prof.country = request.form.get('country', '').strip()
        prof.primary_domain = request.form.get('primary_domain', '').strip()
        prof.bio_summary = request.form.get('bio_summary', '').strip()
        prof.lab_name = request.form.get('lab_name', '').strip()
        
        # Checkboxes
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

    # Fetch all pitches sent to this professor
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
    """API endpoint to dispatch email from professor to student."""
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

    # Trigger async email sender in background
    threading.Thread(
        target=send_student_email_async,
        args=(student.email, student.full_name, current_user.full_name, subject, body)
    ).start()

    return jsonify({'status': 'success', 'message': f'Email successfully sent to {student.email}!'})