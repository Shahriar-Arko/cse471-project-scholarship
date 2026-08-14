from app.services.resume_scorer import DEFAULT_WEIGHTS, calculate_overall_score


def test_calculate_weighted_score_matches_expected_values():
    scores = {
        "formatting": 80,
        "academic": 70,
        "skills": 90,
        "completeness": 60,
    }

    result = calculate_overall_score(scores)

    expected = (
        80 * DEFAULT_WEIGHTS["formatting"]
        + 70 * DEFAULT_WEIGHTS["academic"]
        + 90 * DEFAULT_WEIGHTS["skills"]
        + 60 * DEFAULT_WEIGHTS["completeness"]
    )

    assert result == round(expected, 2)
    assert result == 74.5


def test_custom_weights_are_used():
    scores = {
        "formatting": 100,
        "academic": 50,
        "skills": 90,
        "completeness": 70,
    }

    custom_weights = {
        "formatting": 0.5,
        "academic": 0.2,
        "skills": 0.2,
        "completeness": 0.1,
    }

    result = calculate_overall_score(scores, custom_weights)

    expected = (
        100 * 0.5
        + 50 * 0.2
        + 90 * 0.2
        + 70 * 0.1
    )

    assert result == round(expected, 2)
    assert result == 85.0
