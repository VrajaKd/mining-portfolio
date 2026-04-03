from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

SCORE_CRITERIA = [
    "geology",
    "discovery_probability",
    "scale_potential",
    "management",
    "jurisdiction",
    "catalysts",
    "capital_structure",
    "market_positioning",
    "strategic_value",
    "esg_permitting",
]


def init_database(db_path: str | Path) -> None:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS scores (
                ticker TEXT PRIMARY KEY,
                updated_at TEXT NOT NULL,
                geology REAL,
                discovery_probability REAL,
                scale_potential REAL,
                management REAL,
                jurisdiction REAL,
                catalysts REAL,
                capital_structure REAL,
                market_positioning REAL,
                strategic_value REAL,
                esg_permitting REAL,
                final_score REAL,
                notes TEXT
            );

            CREATE TABLE IF NOT EXISTS ev_data (
                ticker TEXT PRIMARY KEY,
                updated_at TEXT NOT NULL,
                upside_multiple REAL,
                success_probability REAL,
                downside REAL,
                catalyst_timing TEXT,
                catalyst_multiplier REAL,
                ev_raw REAL,
                ev_adjusted REAL,
                tier TEXT
            );

            CREATE TABLE IF NOT EXISTS portfolio_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_date TEXT NOT NULL,
                ticker TEXT NOT NULL,
                quantity REAL,
                market_value REAL,
                avg_cost REAL,
                portfolio_weight_pct REAL,
                score REAL,
                ev_adjusted REAL,
                risk_score INTEGER,
                action TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_snapshots_date_ticker
            ON portfolio_snapshots(snapshot_date, ticker);
        """)


def save_scores(
    db_path: str | Path, ticker: str, scores: dict
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO scores
            (ticker, updated_at, geology, discovery_probability,
             scale_potential, management, jurisdiction, catalysts,
             capital_structure, market_positioning,
             strategic_value, esg_permitting, final_score, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                ticker,
                now,
                scores.get("geology"),
                scores.get("discovery_probability"),
                scores.get("scale_potential"),
                scores.get("management"),
                scores.get("jurisdiction"),
                scores.get("catalysts"),
                scores.get("capital_structure"),
                scores.get("market_positioning"),
                scores.get("strategic_value"),
                scores.get("esg_permitting"),
                scores.get("final_score"),
                scores.get("notes"),
            ),
        )


def load_scores(
    db_path: str | Path, ticker: str
) -> dict | None:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM scores WHERE ticker = ?", (ticker,)
        ).fetchone()
    if row is None:
        return None
    return dict(row)


def load_all_scores(db_path: str | Path) -> pd.DataFrame:
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql("SELECT * FROM scores", conn)
    return df


def save_ev_data(
    db_path: str | Path, ticker: str, ev: dict
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """INSERT OR REPLACE INTO ev_data
            (ticker, updated_at, upside_multiple, success_probability,
             downside, catalyst_timing, catalyst_multiplier,
             ev_raw, ev_adjusted, tier)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                ticker,
                now,
                ev.get("upside_multiple"),
                ev.get("success_probability"),
                ev.get("downside"),
                ev.get("catalyst_timing"),
                ev.get("catalyst_multiplier"),
                ev.get("ev_raw"),
                ev.get("ev_adjusted"),
                ev.get("tier"),
            ),
        )


def load_ev_data(
    db_path: str | Path, ticker: str
) -> dict | None:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT * FROM ev_data WHERE ticker = ?", (ticker,)
        ).fetchone()
    if row is None:
        return None
    return dict(row)


def load_all_ev_data(db_path: str | Path) -> pd.DataFrame:
    with sqlite3.connect(db_path) as conn:
        df = pd.read_sql("SELECT * FROM ev_data", conn)
    return df


def save_portfolio_snapshot(
    db_path: str | Path,
    df: pd.DataFrame,
    snapshot_date: str | None = None,
) -> None:
    if df.empty:
        return
    date = snapshot_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with sqlite3.connect(db_path) as conn:
        for _, row in df.iterrows():
            conn.execute(
                """INSERT INTO portfolio_snapshots
                (snapshot_date, ticker, quantity, market_value,
                 avg_cost, portfolio_weight_pct, score,
                 ev_adjusted, risk_score, action)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    date,
                    row.get("ticker"),
                    row.get("quantity"),
                    row.get("market_value"),
                    row.get("avg_cost"),
                    row.get("portfolio_weight_pct"),
                    row.get("score"),
                    row.get("ev_adjusted"),
                    row.get("risk_score"),
                    row.get("action"),
                ),
            )
