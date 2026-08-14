from app.services.resume_format_analyzer import analyze_resume_format


def test_format_analysis_detects_basic_issues():
    text = """
    Alice Student
    Student at University of Dhaka
    01700000000
    Education
    BSc in Computer Science
    Skills
    Python, JavaScript
    """
    result = analyze_resume_format(text, page_count=1)

    assert result["score"] <= 100
    assert isinstance(result["issues"], list)
    assert result["metrics"]["email_present"] is False
    assert result["metrics"]["phone_present"] is True
    assert result["metrics"]["section_count"] >= 2


def test_format_analysis_handles_good_format():
    text = """
    Name: Alice Student
    Email: alice@example.com
    Phone: +8801700000000

    Education
    BSc in Computer Science

    Skills
    Python, JavaScript, SQL

    Experience
    Software Engineer Intern
    """
    result = analyze_resume_format(text, page_count=1)

    assert result["metrics"]["email_present"] is True
    assert result["metrics"]["phone_present"] is True
    assert result["score"] >= 70


def test_format_analysis_flags_excessive_length():
    long_text = "Alice Student\n" + "This is a paragraph.\n" * 200
    result = analyze_resume_format(long_text, page_count=3)

    assert any("exceeds two pages" in issue.lower() for issue in result["issues"])
    assert result["metrics"]["excessively_long"] is True


def test_format_analysis_handles_empty_text():
    result = analyze_resume_format("")

    assert result["score"] == 0
    assert result["issues"]
