from modules.scoring import (
    calculate_weighted_score,
    get_scoring_rubric,
    load_rubrics,
    validate_scores,
    validate_weights,
)

WEIGHTS = {
    "geology": 0.20,
    "discovery_probability": 0.15,
    "scale_potential": 0.15,
    "management": 0.10,
    "jurisdiction": 0.10,
    "catalysts": 0.10,
    "capital_structure": 0.05,
    "market_positioning": 0.05,
    "strategic_value": 0.05,
    "esg_permitting": 0.05,
}


def _all_scores(value: float) -> dict:
    return {c: value for c in WEIGHTS}


def test_weighted_score_equal_inputs():
    scores = _all_scores(8.0)
    result = calculate_weighted_score(scores, WEIGHTS)
    assert result == 8.0


def test_weighted_score_varied():
    scores = {
        "geology": 9.0,
        "discovery_probability": 8.0,
        "scale_potential": 7.0,
        "management": 6.0,
        "jurisdiction": 8.0,
        "catalysts": 7.0,
        "capital_structure": 5.0,
        "market_positioning": 6.0,
        "strategic_value": 7.0,
        "esg_permitting": 8.0,
    }
    result = calculate_weighted_score(scores, WEIGHTS)
    expected = (
        9.0 * 0.20
        + 8.0 * 0.15
        + 7.0 * 0.15
        + 6.0 * 0.10
        + 8.0 * 0.10
        + 7.0 * 0.10
        + 5.0 * 0.05
        + 6.0 * 0.05
        + 7.0 * 0.05
        + 8.0 * 0.05
    )
    assert result == round(expected, 2)


def test_validate_scores_valid():
    ok, warnings = validate_scores(_all_scores(7.5))
    assert ok
    assert warnings == []


def test_validate_scores_out_of_range():
    scores = _all_scores(7.5)
    scores["geology"] = 11.0
    ok, warnings = validate_scores(scores)
    assert not ok
    assert any("geology" in w for w in warnings)


def test_validate_scores_missing():
    ok, warnings = validate_scores({"geology": 8.0})
    assert not ok
    assert len(warnings) == 9


def test_validate_weights_valid():
    ok, warnings = validate_weights(WEIGHTS)
    assert ok


def test_validate_weights_bad_sum():
    bad = {**WEIGHTS, "geology": 0.50}
    ok, warnings = validate_weights(bad)
    assert not ok


def test_rubrics_load():
    rubrics = load_rubrics("config/scoring_rubrics.yaml")
    assert "geology" in rubrics
    assert "bands" in rubrics["geology"]


def test_rubric_high_score():
    rubrics = load_rubrics("config/scoring_rubrics.yaml")
    text = get_scoring_rubric(rubrics, "geology", 9.5)
    assert "district" in text.lower()


def test_rubric_low_score():
    rubrics = load_rubrics("config/scoring_rubrics.yaml")
    text = get_scoring_rubric(rubrics, "geology", 1.0)
    assert "no meaningful" in text.lower()
