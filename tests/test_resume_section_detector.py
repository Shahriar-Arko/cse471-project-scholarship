from app.services.resume_section_detector import detect_resume_sections


def test_detect_education_variations():
    text = "EDUCATION\nBSc in Computer Science\nUniversity of Dhaka"
    detected = detect_resume_sections(text)
    assert detected["education"] is True

    text = "Academic Background\n2009-2013"
    detected = detect_resume_sections(text)
    assert detected["education"] is True


def test_detect_skills_variations():
    text = "Technical Skills\nPython, JavaScript, SQL, MongoDB"
    detected = detect_resume_sections(text)
    assert detected["skills"] is True

    text = "Core Competencies\nFlask, Docker, Linux"
    detected = detect_resume_sections(text)
    assert detected["skills"] is True


def test_detect_multiple_sections():
    text = """
    Education
    BSc in CSE

    Skills
    Python, C++, Flask

    Projects
    Scholarship Portal
    """
    detected = detect_resume_sections(text)
    assert detected["education"] is True
    assert detected["skills"] is True
    assert detected["projects"] is True
    assert detected["experience"] is False


def test_detect_other_sections():
    text = "Research\nPublished in IEEE\nCertifications\nAWS Cloud Practitioner\nLanguages\nEnglish, Bengali"
    detected = detect_resume_sections(text)
    assert detected["research"] is True
    assert detected["certifications"] is True
    assert detected["languages"] is True
