import re
from collections import OrderedDict


SKILL_TAXONOMY = OrderedDict([
    ("Programming", [
        ("Python", ["python", "py"]),
        ("C", []),
        ("C++", ["c++", "cpp"]),
        ("Java", ["java"]),
        ("JavaScript", ["javascript", "js"]),
        ("C#", ["c#", "csharp"]),
        ("Go", ["go", "golang"]),
        ("Rust", ["rust"]),
        ("SQL", ["sql"]),
        ("MATLAB", ["matlab"]),
    ]),
    ("AI/ML", [
        ("Machine Learning", ["machine learning", "ml"]),
        ("Deep Learning", ["deep learning", "dl"]),
        ("TensorFlow", ["tensorflow", "tf"]),
        ("PyTorch", ["pytorch", "torch"]),
        ("OpenCV", ["opencv"]),
        ("YOLO", ["yolo"]),
        ("NLP", ["nlp"]),
    ]),
    ("Web Development", [
        ("HTML", ["html"]),
        ("CSS", ["css"]),
        ("React", ["react"]),
        ("Flask", ["flask"]),
        ("Django", ["django"]),
        ("Node.js", ["node.js", "nodejs", "node js"]),
        ("Express", ["express"]),
        ("FastAPI", ["fastapi"]),
    ]),
    ("Database", [
        ("MongoDB", ["mongodb"]),
        ("MySQL", ["mysql"]),
        ("PostgreSQL", ["postgresql", "postgres"]),
        ("SQLite", ["sqlite"]),
        ("Redis", ["redis"]),
    ]),
    ("Robotics", [
        ("ROS", ["ros"]),
        ("ROS2", ["ros2", "ros 2"]),
        ("Gazebo", ["gazebo"]),
        ("PX4", ["px4"]),
        ("ArduPilot", ["ardupilot"]),
    ]),
])


def _boundary_pattern(alias):
    alias = re.escape(alias)
    return rf"(?<![A-Za-z0-9])(?:{alias})(?![A-Za-z0-9])"


def _canonical_pattern(canonical):
    if canonical == "C":
        return r"(?<![A-Za-z0-9])C(?![A-Za-z0-9+#])"
    if canonical == "C++":
        return r"(?<![A-Za-z0-9])C\+\+(?![A-Za-z0-9])"
    if canonical == "C#":
        return r"(?<![A-Za-z0-9])C#(?![A-Za-z0-9])"
    return _boundary_pattern(canonical.lower())


def _build_skill_matchers():
    matchers = []
    for category, skills in SKILL_TAXONOMY.items():
        for canonical, aliases in skills:
            patterns = [_canonical_pattern(canonical)]
            for alias in aliases:
                patterns.append(_boundary_pattern(alias.lower()))
            patterns.append(_canonical_pattern(canonical))
            matchers.append({
                "category": category,
                "canonical": canonical,
                "pattern": re.compile("|".join(patterns), re.IGNORECASE),
            })
    return matchers


SKILL_MATCHERS = _build_skill_matchers()


def _normalize_text(text):
    if not text:
        return ""
    value = text.replace("\r\n", "\n").replace("\r", "\n")
    return re.sub(r"\s+", " ", value).strip()


def analyze_skills(text):
    normalized = _normalize_text(text)
    if not normalized:
        return {
            "skills": [],
            "categories": {category: [] for category in SKILL_TAXONOMY.keys()},
            "skill_count": 0,
            "score": 0,
        }

    detected = []
    category_map = {category: [] for category in SKILL_TAXONOMY.keys()}
    seen = set()

    for matcher in SKILL_MATCHERS:
        if matcher["pattern"].search(normalized):
            canonical = matcher["canonical"]
            if canonical in seen:
                continue
            detected.append(canonical)
            seen.add(canonical)
            category_map[matcher["category"]].append(canonical)

    total_taxonomy_skills = sum(len(skills) for skills in SKILL_TAXONOMY.values())
    skill_count = len(detected)
    score = round(min(100.0, (skill_count / max(1, total_taxonomy_skills)) * 100.0), 2)

    return {
        "skills": detected,
        "categories": category_map,
        "skill_count": skill_count,
        "score": score,
    }


calculate_skill_score = analyze_skills
extract_skills = analyze_skills
