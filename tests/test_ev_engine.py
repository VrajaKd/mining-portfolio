from modules.ev_engine import calculate_ev, determine_tier, validate_ev_inputs

SETTINGS = {
    "model": {
        "ev_model": {
            "catalyst_multipliers": {
                "near_term": 1.2,
                "mid_term": 1.0,
                "long_term": 0.8,
            },
            "probability_range": {"min": 0.25, "max": 0.80},
            "upside_range": {"min": 5, "max": 50},
        },
        "ev_scaling": {"core": 5.0, "core_min": 4.0, "secondary": 3.0},
    }
}


def test_calculate_ev_basic():
    result = calculate_ev(10.0, 0.50, 1.0, "mid_term")
    # EV_raw = (10 * 0.5) - 1 = 4.0, mid_term multiplier = 1.0
    assert result["ev_raw"] == 4.0
    assert result["ev_adjusted"] == 4.0
    assert result["catalyst_multiplier"] == 1.0


def test_calculate_ev_near_term():
    result = calculate_ev(10.0, 0.50, 1.0, "near_term")
    # EV_raw = 4.0, near_term multiplier = 1.2
    assert result["ev_raw"] == 4.0
    assert result["ev_adjusted"] == 4.8


def test_calculate_ev_long_term():
    result = calculate_ev(10.0, 0.50, 1.0, "long_term")
    # EV_raw = 4.0, long_term multiplier = 0.8
    assert result["ev_adjusted"] == 3.2


def test_calculate_ev_high_upside():
    result = calculate_ev(30.0, 0.60, 2.0, "near_term")
    # EV_raw = (30 * 0.6) - 2 = 16.0, * 1.2 = 19.2
    assert result["ev_raw"] == 16.0
    assert result["ev_adjusted"] == 19.2


def test_calculate_ev_negative():
    result = calculate_ev(5.0, 0.30, 3.0, "long_term")
    # EV_raw = (5 * 0.3) - 3 = -1.5, * 0.8 = -1.2
    assert result["ev_raw"] == -1.5
    assert result["ev_adjusted"] == -1.2


def test_validate_ev_valid():
    ok, warnings = validate_ev_inputs(15.0, 0.50, 1.0, SETTINGS)
    assert ok


def test_validate_ev_probability_high():
    ok, warnings = validate_ev_inputs(15.0, 0.95, 1.0, SETTINGS)
    assert not ok
    assert any("probability" in w.lower() for w in warnings)


def test_validate_ev_upside_low():
    ok, warnings = validate_ev_inputs(2.0, 0.50, 1.0, SETTINGS)
    assert not ok
    assert any("upside" in w.lower() for w in warnings)


def test_validate_ev_downside_exceeds():
    ok, warnings = validate_ev_inputs(10.0, 0.30, 5.0, SETTINGS)
    assert not ok
    assert any("downside exceeds" in w.lower() for w in warnings)


def test_tier_core():
    assert determine_tier(6.0, SETTINGS) == "core"


def test_tier_core_min():
    assert determine_tier(4.5, SETTINGS) == "core_min"


def test_tier_secondary():
    assert determine_tier(3.5, SETTINGS) == "secondary"


def test_tier_speculative():
    assert determine_tier(2.0, SETTINGS) == "speculative"
