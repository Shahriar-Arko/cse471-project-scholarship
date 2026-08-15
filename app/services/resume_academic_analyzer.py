import re
from typing import List, Optional


ACADEMIC_SECTION_KEYWORDS = {
    "awards": ["awards", "award", "honors", "honour", "honourable mentions", "scholarships", "scholarship"],
    "achievements": ["achievements", "achievement", "academic achievements", "academic achievement", "merits", "distinctions"],
    "research": ["research", "research experience", "publications", "publication", "journal", "conference", "paper"],
}


def _normalize_spaces(value):
    if not value:
        return ""
    value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _find_first_match(patterns, text):
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(0).strip()
    return None


def _clean_match(match_value):
    if match_value is None:
        return None
    cleaned = re.sub(r"\s+", " ", str(match_value)).strip(" ,;:-")
    return cleaned or None


def extract_gpa(text):
    """Extract GPA/CGPA values from resumes using deterministic regex rules."""
    if not text:
        return None

    patterns = [
        r"(?i)\b(?:cgpa|cumulative\s*gpa|gpa)\s*[:\-]?\s*(\d+(?:\.\d+)?)\b",
        r"(?i)\b(?:cgpa|gpa)\s+(\d+(?:\.\d+)?)\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            value = float(match.group(1))
            if value >= 0:
                return round(value, 2)
    return None


def extract_university(text):
    """Extract a plausible university or institute name from the resume text."""
    if not text:
        return None

    patterns = [
        r"(?i)\b(?:from|at|of|\- )?(?:the\s+)?(?:university\s+of\s+[A-Za-z][A-Za-z\s&.-]+|(?:[A-Za-z][A-Za-z\s&.-]+\s+)?institute\s+of\s+[A-Za-z][A-Za-z\s&.-]+|(?:[A-Za-z][A-Za-z\s&.-]+\s+)?college\s+of\s+[A-Za-z][A-Za-z\s&.-]+)",
        r"(?i)\b(?:university|institute|college)\s+(?:of\s+)?[A-Za-z][A-Za-z&.\- '\\]+{2,}",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            value = match.group(0)
            value = re.sub(r"\s+", " ", value).strip(" ,;:-")
            if len(value) > 3:
                return value
    return None


def extract_degree(text):
    """Extract the most likely degree from the resume text."""
    if not text:
        return None

    patterns = [
        r"(?i)\b(?:B\.Sc\.?|BSc|Bachelor\s+of\s+Science|BS\.?|Bachelor\s+of\s+Technology|B\.Tech\.?|BTech|Bachelor\s+of\s+Engineering|BE\.?|Bachelor\s+of\s+Arts|BA\.?|B\.A\.?|M\.Sc\.?|MSc|Master\s+of\s+Science|MS\.?|Master\s+of\s+Engineering|M\.Eng\.?|MEng|MBA|PhD|Ph\.D\.|Doctorate|Diploma)\b",
        r"(?i)\b(?:Bachelor|Master|Doctoral|Diploma|Certificate)\s+(?:of\s+)?[A-Za-z][A-Za-z\s&.-]+",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            degree = match.group(0)
            degree = re.sub(r"\s+", " ", degree).strip(" ,;:-")
            if degree:
                return degree
    return None


def extract_major(text):
    """Extract the resume's major/specialization where clearly identifiable."""
    if not text:
        return None

    patterns = [
        r"(?i)\b(?:major|field\s+of\s+study|specialization|specialisation)\s*[:\-]?\s*([A-Za-z][A-Za-z\s&./()-]+)",
        r"(?i)\b(?:B\.Sc\.?|BSc|BS\.?|Bachelor\s+of\s+Science|B\.Tech\.?|BTech|Bachelor\s+of\s+Technology|M\.Sc\.?|MSc|Master\s+of\s+Science|MS\.?|Master\s+of\s+Engineering|M\.Eng\.?|MEng|MBA|PhD|Ph\.D\.)\s+(?:in|of)\s+([A-Za-z][A-Za-z\s&./()-]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            major = match.group(1)
            major = re.sub(r"\s+", " ", major).strip(" ,;:-")
            if major and len(major) > 2:
                return major
    return None


def extract_graduation_year(text):
    """Extract graduation year using resume-specific phrasing when available."""
    if not text:
        return None

    patterns = [
        r"(?i)\b(?:expected\s+)?(?:graduation\s+(?:year|date)|graduated\s+in|batch\s+of|class\s+of|passed\s+out\s+in|graduation)\s*[:\-]?\s*(19\d{2}|20\d{2})\b",
        r"(?i)\b(?:expected\s+)?(?:graduation\s+year|graduation\s+date)\s*[:\-]?\s*(19\d{2}|20\d{2})\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return int(match.group(1))

    # fallback: only when the resume contains a clear graduation signal and a single prominent year.
    year_matches = re.findall(r"\b(?:19\d{2}|20\d{2})\b", text)
    for year in reversed(year_matches):
        if "graduation" in text.lower() or "class of" in text.lower() or "batch" in text.lower():
            return int(year)
    return None


def _section_lines(text, keywords):
    lines = [line.strip() for line in text.split("\n")]
    results = []
    for idx, line in enumerate(lines):
        lower_line = line.lower()
        if any(keyword in lower_line for keyword in keywords):
            results.append(line)
            continue

        if idx > 0 and results:
            previous = lines[idx - 1].lower()
            if any(keyword in previous for keyword in keywords):
                results.append(line)
    return [line for line in results if line and len(line) > 2]


def extract_academic_achievements(text):
    """Collect achievement entries when the resume lists academic awards or distinctions."""
    if not text:
        return []

    achievements = []
    for keyword_group in [ACADEMIC_SECTION_KEYWORDS["achievements"], ACADEMIC_SECTION_KEYWORDS["awards"]]:
        for item in _section_lines(text, keyword_group):
            if item.lower() not in {"achievements", "award", "awards", "honors", "scholarships"}:
                achievements.append(item)

    unique = []
    seen = set()
    for item in achievements:
        cleaned = _normalize_spaces(item)
        if cleaned and cleaned.lower() not in seen:
            unique.append(cleaned)
            seen.add(cleaned.lower())
    return unique


def extract_research_publications(text):
    """Collect research or publication entries only when plainly identifiable."""
    if not text:
        return []

    research_entries = []
    for item in _section_lines(text, ACADEMIC_SECTION_KEYWORDS["research"]):
        lower_item = item.lower()
        if any(keyword in lower_item for keyword in ["publication", "published", "conference", "journal", "research", "paper", "workshop"]):
            research_entries.append(_normalize_spaces(item))

    unique = []
    seen = set()
    for item in research_entries:
        if item and item.lower() not in seen:
            unique.append(item)
            seen.add(item.lower())
    return unique


def analyze_academic_profile(text):
    """Return a structured academic profile and score."""
    if not text:
        return {
            "gpa": None,
            "university": None,
            "degree": None,
            "major": None,
            "graduation_year": None,
            "academic_achievements": [],
            "awards": [],
            "research_publications": [],
            "academic_score": 0,
            "score": 0,
        }

    normalized = _normalize_spaces(text)
    gpa = extract_gpa(normalized)
    university = extract_university(normalized)
    degree = extract_degree(normalized)
    major = extract_major(normalized)
    graduation_year = extract_graduation_year(normalized)

    achievements = extract_academic_achievements(normalized)
    awards = [item for item in achievements if any(keyword in item.lower() for keyword in ["award", "honor", "scholarship", "rank", "distinction"]) ]
    other_achievements = [item for item in achievements if item not in awards]

    research_publications = extract_research_publications(normalized)

    academic_score = 0
    if gpa is not None:
        academic_score += 30
    if university:
        academic_score += 15
    if degree:
        academic_score += 15
    if major:
        academic_score += 15
    if graduation_year:
        academic_score += 10
    if achievements:
        academic_score += 10
    if research_publications:
        academic_score += 5
    academic_score = min(100, academic_score)

    return {
        "gpa": gpa,
        "university": university,
        "degree": degree,
        "major": major,
        "graduation_year": graduation_year,
        "academic_achievements": other_achievements,
        "awards": awards,
        "research_publications": research_publications,
        "academic_score": academic_score,
        "score": academic_score,
    }


analyze_academic_data = analyze_academic_profile
extract_academic_profile = analyze_academic_profile
