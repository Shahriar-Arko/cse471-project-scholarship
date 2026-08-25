import datetime
from flask import Blueprint, render_template, request, jsonify, redirect, url_for
from flask_login import login_required, current_user
from app.models.research_profile import StudentResearchProfile
from app.services.research_analyzer_service import (
    get_gemini_embedding,
    vector_search_taxonomies,
    match_professors_by_vector,
    match_scholarships_by_domain
)

analyzer_bp = Blueprint('analyzer', __name__, url_prefix='/student')

@analyzer_bp.route('/api/research-analyzer/run', methods=['POST'])
@login_required
def run_research_analyzer():
    if current_user.role != 'student':
        return jsonify({'error': 'Unauthorized'}), 403

    data = request.get_json() or {}
    degree_level = data.get('degree_level', 'Masters').strip()
    major = data.get('major', 'Computer Science').strip()
    cgpa = float(data.get('cgpa', getattr(current_user, 'gpa', 3.5) or 3.5))
    research_statement = data.get('research_statement', '').strip()
    project_abstracts = data.get('project_abstracts', '').strip()
    
    skills_raw = data.get('technical_skills', '')
    technical_skills = [s.strip() for s in skills_raw.split(',') if s.strip()] if isinstance(skills_raw, str) else skills_raw

    if not research_statement or not project_abstracts:
        return jsonify({'error': 'Research statement and project abstract are required.'}), 400

    # 1. Convert live student inputs into a 768-D Query Vector
    combined_query_text = (
        f"Degree: {degree_level} {major}. "
        f"Target Research Interest: {research_statement}. "
        f"Past Projects and Capstone Thesis: {project_abstracts}. "
        f"Technical Skills: {', '.join(technical_skills)}"
    )
    student_vector = get_gemini_embedding(combined_query_text)

    if not student_vector:
        return jsonify({'error': 'Failed to generate embedding vector. Verify GEMINI_API_KEY.'}), 500

    # 2. Pure Vector Search against Pre-Stored MongoDB Taxonomies
    top_niches, matched_skills, missing_skills = vector_search_taxonomies(student_vector, technical_skills, top_k=3)

    # 3. Vector Match Professors & Scholarships
    matched_profs = match_professors_by_vector(student_vector, top_niches)
    matched_scholarships = match_scholarships_by_domain(top_niches)

    # 4. Save to Student Research Profile in MongoDB
    profile = StudentResearchProfile.objects(student=current_user.id).first()
    if not profile:
        profile = StudentResearchProfile(student=current_user.id)

    profile.degree_level = degree_level
    profile.major = major
    profile.cgpa = cgpa
    profile.research_statement = research_statement
    profile.project_abstracts = project_abstracts
    profile.technical_skills = technical_skills
    profile.top_specializations = top_niches
    profile.identified_strengths = matched_skills
    profile.missing_skills = missing_skills
    profile.embedding = student_vector
    profile.updated_at = datetime.datetime.utcnow()
    profile.save()

    return jsonify({
        'status': 'success',
        'message': 'Vector search completed against academic taxonomy index!',
        'analysis': {
            'top_specializations': top_niches,
            'identified_strengths': matched_skills,
            'missing_skills': missing_skills
        },
        'matched_professors': matched_profs,
        'matched_scholarships': matched_scholarships
    })

@analyzer_bp.route('/api/research-analyzer/toggle-visibility', methods=['POST'])
@login_required
def toggle_visibility():
    if current_user.role != 'student':
        return jsonify({'error': 'Unauthorized'}), 403

    profile = StudentResearchProfile.objects(student=current_user.id).first()
    if not profile:
        return jsonify({'error': 'Please analyze your research profile first.'}), 400

    profile.is_visible_to_faculty = not profile.is_visible_to_faculty
    profile.save()

    return jsonify({
        'status': 'success',
        'is_visible': profile.is_visible_to_faculty,
        'message': f"Profile is now {'Visible to Professors in Candidate Pool' if profile.is_visible_to_faculty else 'Private'}."
    })