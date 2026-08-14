DEFAULT_WEIGHTS = {
    "formatting": 0.20,
    "academic": 0.30,
    "skills": 0.25,
    "completeness": 0.25,
}


def calculate_overall_score(scores, weights=None):
    """Compute a weighted overall resume score from sub-scores."""
    if weights is None:
        weights = DEFAULT_WEIGHTS

    normalized = {
        "formatting": float(scores.get("formatting", 0) or 0),
        "academic": float(scores.get("academic", 0) or 0),
        "skills": float(scores.get("skills", 0) or 0),
        "completeness": float(scores.get("completeness", 0) or 0),
    }

    overall = (
        normalized["formatting"] * weights.get("formatting", 0)
        + normalized["academic"] * weights.get("academic", 0)
        + normalized["skills"] * weights.get("skills", 0)
        + normalized["completeness"] * weights.get("completeness", 0)
    )

    return round(overall, 2)


def build_score_summary(scores, weights=None):
    return {
        "overall_score": calculate_overall_score(scores, weights),
        "weights": dict(weights or DEFAULT_WEIGHTS),
    }
