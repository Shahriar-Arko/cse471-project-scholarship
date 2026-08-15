from app.services.resume_academic_analyzer import analyze_academic_profile, extract_gpa


def test_extract_multiple_gpa_formats():
    assert extract_gpa("CGPA: 3.72") == 3.72
    assert extract_gpa("CGPA 3.72") == 3.72
    assert extract_gpa("GPA: 3.8") == 3.8
    assert extract_gpa("GPA 3.80") == 3.8


def test_analyze_academic_profile_fields():
    resume = """
    Alice Student
    BSc in Computer Science
    University of Dhaka
    CGPA: 3.72
    Expected Graduation: 2025
    Awards: Dean's List 2023
    Research: "A Real-Time Detection System" published in IEEE
    """

    result = analyze_academic_profile(resume)

    assert result["gpa"] == 3.72
    assert result["degree"] is not None
    assert "Computer Science" in (result["major"] or "")
    assert result["university"] is not None
    assert result["graduation_year"] == 2025
    assert result["academic_score"] > 0


def test_missing_gpa_returns_none():
    resume = """
    Bob Student
    BSc in Software Engineering
    University of Chittagong
    Expected Graduation: 2026
    """

    result = analyze_academic_profile(resume)

    assert result["gpa"] is None
    assert result["academic_score"] < 100
    assert result["degree"] is not None
