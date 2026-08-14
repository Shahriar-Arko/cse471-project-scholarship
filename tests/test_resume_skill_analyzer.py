from app.services.resume_skill_analyzer import analyze_skills


def test_exact_skill_matches():
    result = analyze_skills("Python, C++, Java, MongoDB")

    assert result["skill_count"] == 4
    assert "Python" in result["skills"]
    assert "C++" in result["skills"]
    assert "Java" in result["skills"]
    assert "MongoDB" in result["skills"]


def test_mixed_capitalization():
    result = analyze_skills("python, JAVASCRIPT, TensorFlow, ros2")

    assert "Python" in result["skills"]
    assert "JavaScript" in result["skills"]
    assert "TensorFlow" in result["skills"]
    assert "ROS2" in result["skills"]


def test_multiple_categories():
    result = analyze_skills("Skills: Python, Flask, TensorFlow, MongoDB, ROS")

    assert result["skill_count"] == 5
    assert "Python" in result["categories"]["Programming"]
    assert "Flask" in result["categories"]["Web Development"]
    assert "TensorFlow" in result["categories"]["AI/ML"]
    assert "MongoDB" in result["categories"]["Database"]
    assert "ROS" in result["categories"]["Robotics"]


def test_missing_skills():
    result = analyze_skills("I have no technical skills listed here.")

    assert result["skills"] == []
    assert result["skill_count"] == 0
    assert result["score"] == 0
