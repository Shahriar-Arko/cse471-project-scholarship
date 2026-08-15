import re


REQUIRED_FIELDS = {
    "name": "name",
    "email": "email",
    "education": "education",
    "skills": "skills",
}

RECOMMENDED_FIELDS = {
    "projects": "projects",
    "experience": "experience",
    "achievements": "achievements",
}

OPTIONAL_FIELDS = {
    "research": "research",
    "certifications": "certifications",
    "languages": "languages",
}


def _normalize_text(value):
    if not value:
        return ""
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _has_email(text):
    return bool(re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text or ""))


def _has_name(text):
    if not text:
        return False
    raw_lines = [line.strip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n") if line.strip()]
    if not raw_lines:
        return False
    first_line = raw_lines[0].lower()
    return bool(first_line) and not any(token in first_line for token in ["resume", "cv", "profile", "summary", "skills", "education"])


def _has_section(text, section_name):
    if not text:
        return False
    normalized = text.lower()
    aliases = {
        "name": ["name"],
        "email": ["email"],
        "education": ["education", "academic background", "academic qualifications"],
        "skills": ["skills", "technical skills", "core competencies"],
        "projects": ["projects", "selected projects", "key projects"],
        "experience": ["experience", "work experience", "professional experience"],
        "achievements": ["achievements", "awards", "honors"],
        "research": ["research", "publications"],
        "certifications": ["certifications", "courses", "training"],
        "languages": ["languages", "language proficiency"],
    }
    for alias in aliases.get(section_name, [section_name]):
        if alias in normalized:
            return True
    return False


def analyze_completeness(text):
    raw_text = text or ""
    normalized = _normalize_text(text)
    required_missing = []
    recommended_missing = []
    optional_missing = []

    if not _has_name(raw_text):
        required_missing.append("name")
    if not _has_email(normalized):
        required_missing.append("email")
    if not _has_section(normalized, "education"):
        required_missing.append("education")
    if not _has_section(normalized, "skills"):
        required_missing.append("skills")

    for field in REQUIRED_FIELDS:
        if field not in required_missing and field in ["name", "email", "education", "skills"]:
            pass

    for field in RECOMMENDED_FIELDS:
        if not _has_section(normalized, field):
            recommended_missing.append(field)

    for field in OPTIONAL_FIELDS:
        if not _has_section(normalized, field):
            optional_missing.append(field)

    total_weight = len(REQUIRED_FIELDS) * 30 + len(RECOMMENDED_FIELDS) * 15 + len(OPTIONAL_FIELDS) * 5
    missing_weight = len(required_missing) * 30 + len(recommended_missing) * 15 + len(optional_missing) * 5
    score = max(0, round(((total_weight - missing_weight) / total_weight) * 100, 2))

    return {
        "required_missing": required_missing,
        "recommended_missing": recommended_missing,
        "optional_missing": optional_missing,
        "score": score,
    }


check_completeness = analyze_completeness
