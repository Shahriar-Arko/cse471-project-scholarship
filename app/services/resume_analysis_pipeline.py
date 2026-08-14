import re

from app.services.resume_academic_analyzer import analyze_academic_profile
from app.services.resume_completeness import analyze_completeness
from app.services.resume_format_analyzer import analyze_resume_format
from app.services.resume_recommender import generate_recommendations
from app.services.resume_scorer import calculate_overall_score
from app.services.resume_section_detector import detect_resume_sections
from app.services.resume_skill_analyzer import analyze_skills


def run_resume_analysis(parsed_resume, filename=None):
    resume_text = (parsed_resume or {}).get('text') or ''
    page_count = (parsed_resume or {}).get('page_count', 1) or 1

    section_data = detect_resume_sections(resume_text)
    academic_data = analyze_academic_profile(resume_text)
    skills_data = analyze_skills(resume_text)
    formatting_data = analyze_resume_format(resume_text, page_count=page_count)
    completeness_data = analyze_completeness(resume_text)

    overall_score = calculate_overall_score({
        'formatting': formatting_data.get('score', 0),
        'academic': academic_data.get('academic_score', 0),
        'skills': skills_data.get('score', 0),
        'completeness': completeness_data.get('score', 0),
    })

    recommendations = generate_recommendations({
        'required_missing': completeness_data.get('required_missing', []),
        'recommended_missing': completeness_data.get('recommended_missing', []),
        'optional_missing': completeness_data.get('optional_missing', []),
        'formatting_issues': formatting_data.get('issues', []),
        'detected_skills': skills_data.get('skills', []),
        'skill_score': skills_data.get('score', 0),
        'formatting_score': formatting_data.get('score', 0),
    })

    email_match = re.search(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', resume_text)
    phone_match = re.search(r'(?:(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?){2,3}\d{3,4})', resume_text)
    first_line = next((line.strip() for line in resume_text.splitlines() if line.strip()), '')

    extracted_data = {
        'name': first_line,
        'email': email_match.group(0) if email_match else None,
        'phone': phone_match.group(0).strip() if phone_match else None,
        'sections': section_data,
        'gpa': academic_data.get('gpa'),
        'degree': academic_data.get('degree'),
        'major': academic_data.get('major'),
        'university': academic_data.get('university'),
        'graduation_year': academic_data.get('graduation_year'),
        'skills': skills_data.get('skills', []),
        'academic_achievements': academic_data.get('academic_achievements', []),
        'awards': academic_data.get('awards', []),
    }

    return {
        'filename': filename,
        'overall_score': overall_score,
        'formatting_score': formatting_data.get('score', 0),
        'academic_score': academic_data.get('academic_score', 0),
        'skills_score': skills_data.get('score', 0),
        'completeness_score': completeness_data.get('score', 0),
        'extracted_data': extracted_data,
        'missing_information': {
            'required_missing': completeness_data.get('required_missing', []),
            'recommended_missing': completeness_data.get('recommended_missing', []),
            'optional_missing': completeness_data.get('optional_missing', []),
        },
        'recommendations': recommendations,
        'detected_sections': section_data,
        'formatting_analysis': formatting_data,
        'academic_analysis': academic_data,
        'skills_analysis': skills_data,
        'completeness_analysis': completeness_data,
    }
