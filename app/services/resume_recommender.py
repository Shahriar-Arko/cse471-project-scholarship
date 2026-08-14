def generate_recommendations(analysis):
    """Generate deterministic recommendations from structured resume analysis."""
    recommendations = []

    if not analysis:
        return recommendations

    required_missing = analysis.get("required_missing") or []
    recommended_missing = analysis.get("recommended_missing") or []
    optional_missing = analysis.get("optional_missing") or []
    formatting_issues = analysis.get("formatting_issues") or []
    detected_skills = analysis.get("detected_skills") or []
    skill_score = analysis.get("skill_score") or 0
    formatting_score = analysis.get("formatting_score") or 0

    if "projects" in recommended_missing:
        recommendations.append("Add a Projects section highlighting relevant academic or technical projects.")

    if "achievements" in recommended_missing:
        recommendations.append("Consider adding academic awards, scholarships, competition results, or other measurable achievements if applicable.")

    if "email" in required_missing:
        recommendations.append("Add a professional email address.")

    if "name" in required_missing:
        recommendations.append("Add your full name clearly at the top of the resume.")

    if "education" in required_missing:
        recommendations.append("Include your degree, major, university, and graduation timeline clearly.")

    if "skills" in required_missing:
        recommendations.append("Add relevant technical skills demonstrated through your academic or project experience.")

    if skill_score < 40 and detected_skills:
        recommendations.append("Consider adding relevant technical skills demonstrated through your academic or project experience.")
    elif skill_score < 40:
        recommendations.append("Consider adding relevant technical skills demonstrated through your academic or project experience.")

    if "experience" in recommended_missing:
        recommendations.append("Highlight internship, work, or project experience with measurable outcomes and tools used.")

    if "research" in optional_missing:
        recommendations.append("If applicable, include research projects, publications, or technical contributions to strengthen your academic profile.")

    if formatting_score < 70 and formatting_issues:
        for issue in formatting_issues:
            issue_lower = issue.lower()
            if "email" in issue_lower:
                recommendations.append("Add a professional email address to improve contact clarity.")
            elif "phone" in issue_lower:
                recommendations.append("Add a phone number in a clear, readable format.")
            elif "exceeds two pages" in issue_lower:
                recommendations.append("Trim lengthy content and keep the resume concise, ideally within two pages.")
            elif "few clearly labeled sections" in issue_lower:
                recommendations.append("Organize the resume with clear section headings such as Education, Skills, Projects, and Experience.")
            elif "very long paragraphs" in issue_lower:
                recommendations.append("Break long paragraphs into concise bullet points to improve readability.")

    if not recommendations:
        recommendations.append("Keep the resume focused on measurable achievements, skills, and academic outcomes.")

    unique = []
    seen = set()
    for item in recommendations:
        if item not in seen:
            unique.append(item)
            seen.add(item)
    return unique


def build_recommendations(analysis):
    return generate_recommendations(analysis)
