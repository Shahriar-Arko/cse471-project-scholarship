from app.services.resume_completeness import analyze_completeness


def test_required_sections_missing():
    resume = """
    Alice Student
    No details here.
    """
    result = analyze_completeness(resume)

    assert "email" in result["required_missing"]
    assert "education" in result["required_missing"]
    assert "skills" in result["required_missing"]
    assert result["score"] < 100


def test_recommended_and_optional_missing_only_lightly_penalized():
    resume = """
    Alice Student
    Email: alice@example.com
    Education
    BSc in Computer Science
    Skills
    Python, JavaScript
    """
    result = analyze_completeness(resume)

    assert result["required_missing"] == []
    assert "projects" in result["recommended_missing"]
    assert "experience" in result["recommended_missing"]
    assert "achievements" in result["recommended_missing"]
    assert result["score"] > 60


def test_optional_missing_are_not_heavily_penalized():
    resume = """
    Alice Student
    Email: alice@example.com
    Education
    BSc in Computer Science
    Skills
    Python, JavaScript
    Projects
    Scholarship Portal
    Experience
    Software Developer Intern
    Achievements
    Dean's List
    """
    result = analyze_completeness(resume)

    assert result["optional_missing"]
    assert result["score"] >= 70
