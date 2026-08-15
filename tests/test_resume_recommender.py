from app.services.resume_recommender import generate_recommendations


def test_generate_project_and_achievement_recommendations():
    analysis = {
        "required_missing": ["email"],
        "recommended_missing": ["projects", "achievements"],
        "optional_missing": ["research"],
        "formatting_issues": [],
        "detected_skills": [],
        "skill_score": 80,
        "formatting_score": 90,
    }

    recommendations = generate_recommendations(analysis)

    assert any("Projects section" in item for item in recommendations)
    assert any("academic awards" in item.lower() for item in recommendations)
    assert any("professional email address" in item.lower() for item in recommendations)


def test_generate_formatting_and_skill_recommendations():
    analysis = {
        "required_missing": [],
        "recommended_missing": [],
        "optional_missing": [],
        "formatting_issues": ["Resume exceeds two pages.", "Experience section contains very long paragraphs."],
        "detected_skills": ["Python"],
        "skill_score": 25,
        "formatting_score": 60,
    }

    recommendations = generate_recommendations(analysis)

    assert any("two pages" in item.lower() for item in recommendations)
    assert any("bullet points" in item.lower() for item in recommendations)
    assert any("technical skills" in item.lower() for item in recommendations)


def test_generate_no_recommendations_default_message():
    analysis = {
        "required_missing": [],
        "recommended_missing": [],
        "optional_missing": [],
        "formatting_issues": [],
        "detected_skills": ["Python", "Flask"],
        "skill_score": 90,
        "formatting_score": 95,
    }

    recommendations = generate_recommendations(analysis)

    assert recommendations
    assert "Keep the resume focused" in recommendations[0]
