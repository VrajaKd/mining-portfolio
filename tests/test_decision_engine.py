import math

from modules.decision_engine import determine_action

SETTINGS = {
    "model": {
        "decision": {
            "buy_score_min": 8.4,
            "buy_ev_min": 4.5,
            "add_ev_min": 5.0,
            "hold_score_min": 7.0,
            "sell_risk_min": 9,
        }
    }
}


def test_buy():
    assert determine_action(8.5, 5.0, 5, SETTINGS) == "BUY"


def test_add():
    assert determine_action(7.5, 5.5, 6, SETTINGS) == "ADD"


def test_hold():
    assert determine_action(7.5, 3.0, 6, SETTINGS) == "HOLD"


def test_sell_by_risk():
    assert determine_action(8.5, 5.0, 9, SETTINGS) == "SELL"


def test_sell_low_score():
    assert determine_action(5.0, 2.0, 6, SETTINGS) == "SELL"


def test_sell_priority_over_buy():
    # Risk >= 9 should override even good score/EV
    assert determine_action(9.0, 6.0, 9, SETTINGS) == "SELL"


def test_no_data_both_none():
    assert determine_action(None, None, None, SETTINGS) == "NO_DATA"


def test_no_data_score_only():
    assert determine_action(8.0, None, 6, SETTINGS) == "NO_DATA"


def test_no_data_ev_only():
    assert determine_action(None, 5.0, 6, SETTINGS) == "NO_DATA"


def test_no_data_but_high_risk_sells():
    assert determine_action(None, None, 9, SETTINGS) == "SELL"


def test_buy_threshold_exact():
    assert determine_action(8.4, 4.5, 5, SETTINGS) == "BUY"


def test_below_buy_but_add():
    assert determine_action(8.0, 5.0, 5, SETTINGS) == "ADD"


def test_no_data_nan_score():
    assert determine_action(math.nan, math.nan, 6, SETTINGS) == "NO_DATA"


def test_no_data_nan_high_risk_sells():
    assert determine_action(math.nan, math.nan, 9, SETTINGS) == "SELL"
