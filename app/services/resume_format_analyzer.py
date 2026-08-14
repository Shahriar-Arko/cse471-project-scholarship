import re


EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"(?:(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?){2,3}\d{3,4})")
SECTION_PATTERN = re.compile(r"^(education|skills|projects|experience|achievements|research|certifications|languages)\s*[:\-]?$", re.IGNORECASE)


def _normalize_whitespace(text):
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _count_lines(text):
    if not text:
        return 0
    return len([line for line in text.split("\n") if line.strip()])


def _extract_sections(text):
    detected = []
    for line in (text or "").split("\n"):
        stripped = line.strip()
        if SECTION_PATTERN.fullmatch(stripped):
            detected.append(stripped.lower())
    return detected


def analyze_resume_format(text, page_count=1):
    normalized = _normalize_whitespace(text)
    issues = []
    metrics = {
        "page_count": page_count,
        "email_present": bool(EMAIL_PATTERN.search(normalized)),
        "phone_present": bool(PHONE_PATTERN.search(normalized)),
        "section_count": 0,
        "section_names": [],
        "word_count": len(re.findall(r"\b\w+\b", normalized)),
        "paragraph_count": 0,
        "bullet_count": 0,
        "density": 0.0,
        "excessively_long": False,
    }

    if not normalized:
        return {"score": 0, "issues": ["Resume text is empty."], "metrics": metrics}

    sections = _extract_sections(text)
    metrics["section_names"] = sections
    metrics["section_count"] = len(sections)

    lines = [line.strip() for line in (text or "").split("\n") if line.strip()]
    metrics["paragraph_count"] = len(lines)
    metrics["bullet_count"] = sum(1 for line in lines if re.match(r"^[\-\*•\d\.)\]]", line))

    if page_count > 2:
        issues.append("Resume exceeds two pages.")

    if not metrics["email_present"]:
        issues.append("Email address is missing.")

    if not metrics["phone_present"]:
        issues.append("Phone number is missing.")

    if metrics["section_count"] < 3:
        issues.append("Resume has few clearly labeled sections.")

    if metrics["word_count"] > 900 or page_count > 2:
        issues.append("Resume appears unusually long for a typical student profile.")
        metrics["excessively_long"] = True

    if metrics["paragraph_count"] > 0:
        metrics["density"] = round((metrics["bullet_count"] / metrics["paragraph_count"]) * 100, 2)

    if metrics["paragraph_count"] > 0 and metrics["density"] > 70:
        issues.append("Resume appears heavily bullet-based and may lack narrative detail.")
    elif metrics["paragraph_count"] > 0 and metrics["density"] < 20 and metrics["paragraph_count"] > 15:
        issues.append("Experience section contains very long paragraphs.")

    score = 100
    score -= len(issues) * 8
    score -= max(0, page_count - 2) * 5
    score = max(0, min(100, score))

    return {"score": score, "issues": issues, "metrics": metrics}


analyze_format = analyze_resume_format
