from modules.market_data import map_ticker_to_yfinance


def test_map_ticker_asx():
    assert map_ticker_to_yfinance("SGQ", "ASX") == "SGQ.AX"


def test_map_ticker_tsx():
    assert map_ticker_to_yfinance("MAG", "TSX") == "MAG.TO"


def test_map_ticker_tsxv():
    assert map_ticker_to_yfinance("DEF", "TSXV") == "DEF.V"


def test_map_ticker_venture():
    assert map_ticker_to_yfinance("DEF", "VENTURE") == "DEF.V"


def test_map_ticker_nyse():
    assert map_ticker_to_yfinance("AAPL", "NYSE") == "AAPL"


def test_map_ticker_empty_exchange():
    assert map_ticker_to_yfinance("XYZ", "") == "XYZ"


def test_map_ticker_unknown_exchange():
    assert map_ticker_to_yfinance("XYZ", "UNKNOWN") == "XYZ"
