import re

SECTION_ALIASES = {
    "education": [
        "education",
        "academic background",
        "academic qualifications",
        "academic history",
        "education background",
        "qualification",
        "qualifications",
    ],
    "skills": [
        "skills",
        "technical skills",
        "core competencies",
        "competencies",
        "areas of expertise",
        "technologies",
        "professional skills",
    ],
    "projects": [
        "projects",
        "project experience",
        "selected projects",
        "academic projects",
        "key projects",
    ],
    "experience": [
        "experience",
        "work experience",
        "professional experience",
        "employment history",
        "internships",
        "career experience",
    ],
    "achievements": [
        "achievements",
        "awards",
        "honors",
        "recognitions",
        "academic achievements",
        "distinctions",
    ],
    "research": [
        "research",
        "research experience",
        "publications",
        "research publications",
        "research interests",
    ],
    "certifications": [
        "certifications",
        "certification",
        "licenses",
        "courses",
        "training",
    ],
    "languages": [
        "languages",
        "language proficiency",
        "language skills",
        "foreign languages",
    ],
}

SECTION_ORDER = [
    "education",
    "skills",
    "projects",
    "experience",
    "achievements",
    "research",
    "certifications",
    "languages",
]


def _normalize_section_name(value):
    if not value:
        return ""
    cleaned = re.sub(r"[^a-zA-Z0-9\s]+", " ", value)
    cleaned = re.sub(r"\s+", " ", cleaned).strip().lower()
    return cleaned


def detect_resume_sections(text):
    """Detect section headings in a resume using case-insensitive regex matching."""
    if not text:
        return {section: False for section in SECTION_ORDER}

    normalized_text = text.replace("\r\n", "\n").replace("\r", "\n")
    results = {section: False for section in SECTION_ORDER}

    lines = [line.strip() for line in normalized_text.split("\n")]
    for section_name, aliases in SECTION_ALIASES.items():
        alias_patterns = []
        for alias in aliases:
            alias_patterns.append(re.escape(_normalize_section_name(alias)))

        pattern = r"(?i)^(?:" + "|".join(alias_patterns) + r")\s*[:\-]?$"
        for line in lines:
            if re.fullmatch(pattern, _normalize_section_name(line)):
                results[section_name] = True
                break

        if not results[section_name]:
            for alias in aliases:
                alias_norm = _normalize_section_name(alias)
                if alias_norm and alias_norm in _normalize_section_name(normalized_text):
                    results[section_name] = True
                    break

    return results


def detect_sections_in_resume(text):
    return detect_resume_sections(text)
