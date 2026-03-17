"""DuckDB database manager for research persistence and market data caching.

Zero-config embedded analytics database. All data stored locally in data/hedge_fund.duckdb.
"""

import json
import uuid
from datetime import datetime
from pathlib import Path

import duckdb

DB_DIR = Path("data")
DB_PATH = DB_DIR / "hedge_fund.duckdb"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def get_connection() -> duckdb.DuckDBPyConnection:
    """Get a DuckDB connection, creating the database and schema if needed."""
    DB_DIR.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(DB_PATH))

    # Initialize schema on first connection
    schema_sql = SCHEMA_PATH.read_text()
    conn.execute(schema_sql)

    return conn


def save_research_run(conn: duckdb.DuckDBPyConnection, input_source: str, input_type: str, model_name: str, model_provider: str, transcript_chars: int) -> str:
    """Create a new research run record. Returns the run_id."""
    run_id = str(uuid.uuid4())[:8]
    conn.execute(
        "INSERT INTO research_runs (run_id, input_source, input_type, model_name, model_provider, transcript_chars) VALUES (?, ?, ?, ?, ?, ?)",
        [run_id, input_source, input_type, model_name, model_provider, transcript_chars],
    )
    return run_id


def complete_research_run(conn: duckdb.DuckDBPyConnection, run_id: str):
    """Mark a research run as completed."""
    conn.execute("UPDATE research_runs SET status = 'completed' WHERE run_id = ?", [run_id])


def save_themes(conn: duckdb.DuckDBPyConnection, run_id: str, themes_data: dict):
    """Save extracted themes (Stage 1 output)."""
    for theme in themes_data.get("themes", []):
        conn.execute(
            "INSERT INTO themes (id, run_id, theme, category, signal_strength, raw_json) VALUES (nextval('themes_id_seq'), ?, ?, ?, ?, ?)",
            [run_id, theme.get("theme", ""), theme.get("category", ""), theme.get("signal_strength", ""), json.dumps(theme)],
        )


def save_theses(conn: duckdb.DuckDBPyConnection, run_id: str, theses_data: dict):
    """Save investment theses (Stage 2 output)."""
    for thesis in theses_data.get("theses", []):
        conn.execute(
            "INSERT INTO theses (id, run_id, thesis, tam_estimate, supply_chain_analysis, competitive_landscape, raw_json) VALUES (nextval('theses_id_seq'), ?, ?, ?, ?, ?, ?)",
            [
                run_id,
                thesis.get("thesis", ""),
                thesis.get("tam_estimate", ""),
                thesis.get("supply_chain_analysis", ""),
                thesis.get("competitive_landscape", ""),
                json.dumps(thesis),
            ],
        )


def save_research_questions(conn: duckdb.DuckDBPyConnection, run_id: str, research_data: dict):
    """Save research questions (Stage 3 output)."""
    for plan in research_data.get("research_plans", []):
        for q in plan.get("research_questions", []):
            conn.execute(
                "INSERT INTO research_questions (id, run_id, thesis, question, information_value, data_sources, raw_json) VALUES (nextval('research_questions_id_seq'), ?, ?, ?, ?, ?, ?)",
                [
                    run_id,
                    plan.get("thesis", ""),
                    q.get("question", ""),
                    q.get("information_value", ""),
                    json.dumps(q.get("data_sources", [])),
                    json.dumps(q),
                ],
            )


def save_consolidated_research(conn: duckdb.DuckDBPyConnection, run_id: str, consolidated_data: dict):
    """Save consolidated research with confidence scores (Stage 4 output)."""
    for assessment in consolidated_data.get("assessments", []):
        conn.execute(
            "INSERT INTO consolidated_research (id, run_id, thesis, confidence_score, key_assumption, raw_json) VALUES (nextval('consolidated_research_id_seq'), ?, ?, ?, ?, ?)",
            [
                run_id,
                assessment.get("thesis", ""),
                assessment.get("confidence_score", 0),
                assessment.get("key_assumption", ""),
                json.dumps(assessment),
            ],
        )


def save_equity_ideas(conn: duckdb.DuckDBPyConnection, run_id: str, equity_data: dict):
    """Save equity ideas (Stage 5 output)."""
    for sector in equity_data.get("sectors", []):
        for eq in sector.get("equities", []):
            conn.execute(
                """INSERT INTO equity_ideas (id, run_id, ticker, company_name, sector, impact_order, conviction,
                   thesis_connection, expected_impact, catalyst_timeline, upside_potential, key_metric_to_watch)
                   VALUES (nextval('equity_ideas_id_seq'), ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    run_id,
                    eq.get("ticker", ""),
                    eq.get("company_name", ""),
                    eq.get("sector", sector.get("sector", "")),
                    eq.get("order", ""),
                    eq.get("conviction", ""),
                    eq.get("thesis_connection", ""),
                    eq.get("expected_impact", ""),
                    eq.get("catalyst_timeline", ""),
                    eq.get("upside_potential", ""),
                    eq.get("key_metric_to_watch", ""),
                ],
            )


def save_full_pipeline_output(conn: duckdb.DuckDBPyConnection, run_id: str, data: dict):
    """Save all pipeline stage outputs to the database."""
    if "themes" in data:
        save_themes(conn, run_id, data["themes"])
    if "analyst_theses" in data:
        save_theses(conn, run_id, data["analyst_theses"])
    if "research_plans" in data:
        save_research_questions(conn, run_id, data["research_plans"])
    if "consolidated_research" in data:
        save_consolidated_research(conn, run_id, data["consolidated_research"])
    if "equity_ideas" in data:
        save_equity_ideas(conn, run_id, data["equity_ideas"])


def cache_prices(conn: duckdb.DuckDBPyConnection, ticker: str, prices: list):
    """Cache price data in DuckDB."""
    for p in prices:
        conn.execute(
            """INSERT OR REPLACE INTO price_cache (ticker, trade_date, open, high, low, close, volume)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [ticker, p.time if hasattr(p, "time") else p["time"], p.open if hasattr(p, "open") else p["open"], p.high if hasattr(p, "high") else p["high"], p.low if hasattr(p, "low") else p["low"], p.close if hasattr(p, "close") else p["close"], p.volume if hasattr(p, "volume") else p["volume"]],
        )


def get_cached_prices(conn: duckdb.DuckDBPyConnection, ticker: str, start_date: str, end_date: str) -> list[dict]:
    """Retrieve cached prices from DuckDB."""
    result = conn.execute(
        "SELECT trade_date, open, high, low, close, volume FROM price_cache WHERE ticker = ? AND trade_date >= ? AND trade_date <= ? ORDER BY trade_date",
        [ticker, start_date, end_date],
    ).fetchall()

    return [{"time": str(r[0]), "open": r[1], "high": r[2], "low": r[3], "close": r[4], "volume": r[5]} for r in result]


# Query helpers


def get_recent_runs(conn: duckdb.DuckDBPyConnection, limit: int = 10) -> list[dict]:
    """Get the most recent research runs."""
    result = conn.execute("SELECT * FROM research_runs ORDER BY created_at DESC LIMIT ?", [limit]).fetchdf()
    return result.to_dict(orient="records")


def get_run_equity_ideas(conn: duckdb.DuckDBPyConnection, run_id: str) -> list[dict]:
    """Get equity ideas for a specific run."""
    result = conn.execute("SELECT * FROM equity_ideas WHERE run_id = ? ORDER BY conviction DESC, ticker", [run_id]).fetchdf()
    return result.to_dict(orient="records")


def get_thesis_history(conn: duckdb.DuckDBPyConnection, thesis_keyword: str) -> list[dict]:
    """Track thesis confidence over time by searching across runs."""
    result = conn.execute(
        """SELECT r.run_id, r.created_at, c.thesis, c.confidence_score, c.key_assumption
           FROM consolidated_research c
           JOIN research_runs r ON c.run_id = r.run_id
           WHERE c.thesis ILIKE ?
           ORDER BY r.created_at DESC""",
        [f"%{thesis_keyword}%"],
    ).fetchdf()
    return result.to_dict(orient="records")


def get_ticker_history(conn: duckdb.DuckDBPyConnection, ticker: str) -> list[dict]:
    """Get all equity ideas for a ticker across all runs."""
    result = conn.execute(
        """SELECT e.*, r.created_at, r.input_source
           FROM equity_ideas e
           JOIN research_runs r ON e.run_id = r.run_id
           WHERE e.ticker = ?
           ORDER BY r.created_at DESC""",
        [ticker],
    ).fetchdf()
    return result.to_dict(orient="records")
