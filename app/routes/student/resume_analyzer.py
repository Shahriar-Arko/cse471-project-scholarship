import os
import re
from flask import flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from app.models.resume_analysis import ResumeAnalysis
from app.services.resume_analysis_pipeline import run_resume_analysis
from app.services.resume_parser import ResumeParseError, parse_resume_document
from app.services.resume_scholarship_matcher import find_relevant_scholarships
from . import student_bp

ALLOWED_RESUME_EXTENSIONS = {".pdf", ".docx"}
MAX_RESUME_SIZE_BYTES = 10 * 1024 * 1024


def _validate_resume_upload(file_storage):
    if file_storage is None or not getattr(file_storage, 'filename', '').strip():
        return False, 'Please choose a PDF or DOCX file.'

    filename = secure_filename(file_storage.filename or '')
    if not filename:
        return False, 'Uploaded file name is invalid.'

    extension = os.path.splitext(filename)[1].lower()
    if extension not in ALLOWED_RESUME_EXTENSIONS:
        return False, 'Only PDF and DOCX resume files are allowed.'

    mime_type = (file_storage.mimetype or '').lower()
    allowed_mimes = {
        '.pdf': {'application/pdf'},
        '.docx': {'application/vnd.openxmlformats-officedocument.wordprocessingml.document'}
    }
    if mime_type and mime_type not in allowed_mimes.get(extension, set()):
        return False, 'The uploaded file does not match a supported resume format.'

    try:
        file_storage.stream.seek(0, os.SEEK_END)
        file_size = file_storage.stream.tell()
        file_storage.stream.seek(0)
    except (AttributeError, OSError):
        file_size = 0

    if file_size <= 0:
        return False, 'The uploaded file is empty.'

    if file_size > MAX_RESUME_SIZE_BYTES:
        return False, 'Resume file is too large. Please upload a file smaller than 10MB.'

    return True, filename


@student_bp.route('/resume_analyzer', methods=['GET'])
@login_required
def resume_analyzer():
    if current_user.role != 'student':
        return redirect(url_for('dashboard'))
    previous_analyses = ResumeAnalysis.objects(user=current_user).order_by('-created_at')
    return render_template('dashboard/resume_analyzer.html', previous_analyses=previous_analyses)


@student_bp.route('/resume_analyzer/<analysis_id>', methods=['GET'])
@login_required
def resume_analysis_detail(analysis_id):
    if current_user.role != 'student':
        return redirect(url_for('dashboard'))

    analysis = ResumeAnalysis.objects(id=analysis_id, user=current_user).first()
    if not analysis:
        flash('You do not have access to that resume analysis.', 'error')
        return redirect(url_for('student.resume_analyzer'))

    return render_template('dashboard/resume_analysis_detail.html', analysis=analysis)


@student_bp.route('/resume_analyzer/upload', methods=['POST'])
@login_required
def resume_analyzer_upload():
    if current_user.role != 'student':
        return redirect(url_for('dashboard'))

    if 'resume_file' not in request.files:
        flash('No file was uploaded. Please choose a PDF or DOCX resume.', 'error')
        return redirect(url_for('student.resume_analyzer'))

    uploaded_file = request.files['resume_file']
    valid, message = _validate_resume_upload(uploaded_file)

    if not valid:
        flash(message, 'error')
        return redirect(url_for('student.resume_analyzer'))

    secure_name = secure_filename(message)

    try:
        parsed_resume = parse_resume_document(uploaded_file, filename=secure_name)
    except ResumeParseError as exc:
        flash(str(exc), 'error')
        return redirect(url_for('student.resume_analyzer'))

    summary = (parsed_resume.get('text') or '')
    summary_preview = summary[:220].replace('\n', ' ')
    summary_preview = ' '.join(summary_preview.split())

    analysis_result = run_resume_analysis(parsed_resume, filename=secure_name)
    scholarship_matches = find_relevant_scholarships(analysis_result.get('extracted_data', {}), limit=6)
    analysis_result['scholarship_matches'] = scholarship_matches
    analysis_result['recommendations'] = list(analysis_result.get('recommendations', [])) + scholarship_matches.get('recommendation_lines', [])

    history_entry = ResumeAnalysis(
        user=current_user,
        filename=secure_name,
        overall_score=analysis_result.get('overall_score', 0),
        formatting_score=analysis_result.get('formatting_score', 0),
        academic_score=analysis_result.get('academic_score', 0),
        skills_score=analysis_result.get('skills_score', 0),
        completeness_score=analysis_result.get('completeness_score', 0),
        extracted_data=analysis_result.get('extracted_data', {}),
        missing_information=analysis_result.get('missing_information', {}),
        recommendations=analysis_result.get('recommendations', []),
        scholarship_matches=scholarship_matches,
    )

    try:
        history_entry.save()
    except Exception:
        flash('Your resume was parsed successfully, but saving the analysis could not be completed.', 'error')
        return redirect(url_for('student.resume_analyzer'))

    previous_analyses = ResumeAnalysis.objects(user=current_user).order_by('-created_at')

    flash(f"Valid resume received: {secure_name}. Extraction succeeded and the analysis was saved securely.", 'success')
    return render_template(
        'dashboard/resume_analyzer.html',
        uploaded_filename=secure_name,
        upload_status='received',
        parsed_resume=parsed_resume,
        resume_summary=summary_preview,
        resume_word_count=parsed_resume.get('word_count', 0),
        resume_page_count=parsed_resume.get('page_count', 1),
        detected_sections=analysis_result.get('detected_sections', {}),
        analysis_record=history_entry,
        overall_score=analysis_result.get('overall_score', 0),
        formatting_score=analysis_result.get('formatting_score', 0),
        academic_score=analysis_result.get('academic_score', 0),
        skills_score=analysis_result.get('skills_score', 0),
        completeness_score=analysis_result.get('completeness_score', 0),
        recommendations=analysis_result.get('recommendations', []),
        extracted_data=analysis_result.get('extracted_data', {}),
        missing_information=analysis_result.get('missing_information', {}),
        scholarship_matches=scholarship_matches,
        previous_analyses=previous_analyses,
    )
