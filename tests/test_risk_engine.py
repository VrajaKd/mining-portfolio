from modules.risk_engine import calculate_risk, get_risk_flags

SETTINGS = {
    "model": {
        "risk_thresholds": {
            "sell_candidate": 9,
            "swap_trigger": 9,
            "weak_holding": 7,
        }
    }
}


def test_risk_high_score_high_ev():
    assert calculate_risk(8.5, 5.0) == 5


def test_risk_good_score():
    assert calculate_risk(7.8, 4.0) == 6


def test_risk_moderate():
    assert calculate_risk(7.2, 3.2) == 7


def test_risk_weak_score():
    assert calculate_risk(6.8, 2.8) == 8


def test_risk_sell_territory():
    assert calculate_risk(6.0, 2.0) == 9


def test_risk_none_values():
    assert calculate_risk(None, None) == 7


def test_risk_manual_override():
    assert calculate_risk(9.0, 6.0, manual_override=10) == 10


def test_risk_override_clamped():
    assert calculate_risk(5.0, 1.0, manual_override=3) == 5
    assert calculate_risk(5.0, 1.0, manual_override=12) == 10


def test_flags_sell():
    flags = get_risk_flags(9, SETTINGS)
    assert "SELL_CANDIDATE" in flags
    assert "SWAP_ELIGIBLE" in flags


def test_flags_weak():
    flags = get_risk_flags(7, SETTINGS)
    assert "WEAK_HOLDING" in flags


def test_flags_ok():
    flags = get_risk_flags(5, SETTINGS)
    assert flags == []
