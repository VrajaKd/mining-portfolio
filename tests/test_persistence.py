import os
import tempfile

from modules.persistence import (
    init_database,
    load_all_scores,
    load_ev_data,
    load_scores,
    save_ev_data,
    save_scores,
)


def _tmp_db():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    init_database(path)
    return path


def test_init_creates_tables():
    db = _tmp_db()
    import sqlite3

    conn = sqlite3.connect(db)
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    conn.close()
    os.unlink(db)
    names = [t[0] for t in tables]
    assert "scores" in names
    assert "ev_data" in names
    assert "portfolio_snapshots" in names


def test_save_and_load_scores():
    db = _tmp_db()
    scores = {
        "geology": 8.5,
        "discovery_probability": 7.0,
        "scale_potential": 9.0,
        "management": 6.5,
        "jurisdiction": 8.0,
        "catalysts": 7.5,
        "capital_structure": 6.0,
        "market_positioning": 5.5,
        "strategic_value": 7.0,
        "esg_permitting": 8.0,
        "final_score": 7.65,
    }
    save_scores(db, "AAA", scores)
    loaded = load_scores(db, "AAA")
    os.unlink(db)

    assert loaded is not None
    assert loaded["ticker"] == "AAA"
    assert loaded["geology"] == 8.5
    assert loaded["final_score"] == 7.65


def test_upsert_overwrites():
    db = _tmp_db()
    save_scores(db, "AAA", {"geology": 8.0, "final_score": 7.0})
    save_scores(db, "AAA", {"geology": 9.0, "final_score": 8.0})
    loaded = load_scores(db, "AAA")
    os.unlink(db)
    assert loaded["geology"] == 9.0


def test_load_nonexistent():
    db = _tmp_db()
    loaded = load_scores(db, "ZZZ")
    os.unlink(db)
    assert loaded is None


def test_load_all_scores():
    db = _tmp_db()
    save_scores(db, "AAA", {"geology": 8.0, "final_score": 7.0})
    save_scores(db, "BBB", {"geology": 6.0, "final_score": 5.0})
    df = load_all_scores(db)
    os.unlink(db)
    assert len(df) == 2
    assert set(df["ticker"]) == {"AAA", "BBB"}


def test_save_and_load_ev():
    db = _tmp_db()
    ev = {
        "upside_multiple": 15.0,
        "success_probability": 0.50,
        "downside": 1.0,
        "catalyst_timing": "near_term",
        "catalyst_multiplier": 1.2,
        "ev_raw": 6.5,
        "ev_adjusted": 7.8,
        "tier": "core",
    }
    save_ev_data(db, "AAA", ev)
    loaded = load_ev_data(db, "AAA")
    os.unlink(db)
    assert loaded is not None
    assert loaded["ev_adjusted"] == 7.8
    assert loaded["tier"] == "core"
