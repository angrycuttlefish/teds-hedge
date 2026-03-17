-- DuckDB schema for AI Hedge Fund research persistence
-- All tables use IF NOT EXISTS for idempotent creation

-- Research pipeline runs
CREATE TABLE IF NOT EXISTS research_runs (
    run_id VARCHAR PRIMARY KEY,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    input_source VARCHAR,
    input_type VARCHAR,
    model_name VARCHAR,
    model_provider VARCHAR,
    transcript_chars INTEGER,
    status VARCHAR DEFAULT 'running'
);

-- Extracted themes from podcast/video signals (Stage 1 output)
CREATE TABLE IF NOT EXISTS themes (
    id INTEGER PRIMARY KEY,
    run_id VARCHAR REFERENCES research_runs(run_id),
    theme VARCHAR,
    category VARCHAR,
    signal_strength VARCHAR,
    raw_json JSON
);

-- Investment theses from hedge fund analyst (Stage 2 output)
CREATE TABLE IF NOT EXISTS theses (
    id INTEGER PRIMARY KEY,
    run_id VARCHAR REFERENCES research_runs(run_id),
    thesis VARCHAR,
    tam_estimate VARCHAR,
    supply_chain_analysis VARCHAR,
    competitive_landscape VARCHAR,
    raw_json JSON
);

-- Research questions from deep research synthesizer (Stage 3 output)
CREATE TABLE IF NOT EXISTS research_questions (
    id INTEGER PRIMARY KEY,
    run_id VARCHAR REFERENCES research_runs(run_id),
    thesis VARCHAR,
    question VARCHAR,
    information_value VARCHAR,
    data_sources JSON,
    raw_json JSON
);

-- Consolidated research with confidence scores (Stage 4 output)
CREATE TABLE IF NOT EXISTS consolidated_research (
    id INTEGER PRIMARY KEY,
    run_id VARCHAR REFERENCES research_runs(run_id),
    thesis VARCHAR,
    confidence_score INTEGER,
    key_assumption VARCHAR,
    raw_json JSON
);

-- Equity ideas from screener (Stage 5 output)
CREATE TABLE IF NOT EXISTS equity_ideas (
    id INTEGER PRIMARY KEY,
    run_id VARCHAR REFERENCES research_runs(run_id),
    ticker VARCHAR,
    company_name VARCHAR,
    sector VARCHAR,
    impact_order VARCHAR,
    conviction VARCHAR,
    thesis_connection VARCHAR,
    expected_impact VARCHAR,
    catalyst_timeline VARCHAR,
    upside_potential VARCHAR,
    key_metric_to_watch VARCHAR
);

-- Market data cache (prices)
CREATE TABLE IF NOT EXISTS price_cache (
    ticker VARCHAR,
    trade_date DATE,
    open DOUBLE,
    high DOUBLE,
    low DOUBLE,
    close DOUBLE,
    volume BIGINT,
    PRIMARY KEY (ticker, trade_date)
);

-- Market data cache (fundamentals snapshot)
CREATE TABLE IF NOT EXISTS fundamentals_cache (
    ticker VARCHAR,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    data JSON,
    PRIMARY KEY (ticker, fetched_at)
);

-- SEC filing metadata
CREATE TABLE IF NOT EXISTS sec_filings (
    id INTEGER PRIMARY KEY,
    ticker VARCHAR,
    cik VARCHAR,
    filing_type VARCHAR,
    filing_date DATE,
    accession_number VARCHAR UNIQUE,
    document_url VARCHAR,
    description VARCHAR,
    raw_text TEXT,
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create sequences for auto-increment IDs
CREATE SEQUENCE IF NOT EXISTS themes_id_seq;
CREATE SEQUENCE IF NOT EXISTS theses_id_seq;
CREATE SEQUENCE IF NOT EXISTS research_questions_id_seq;
CREATE SEQUENCE IF NOT EXISTS consolidated_research_id_seq;
CREATE SEQUENCE IF NOT EXISTS equity_ideas_id_seq;
CREATE SEQUENCE IF NOT EXISTS sec_filings_id_seq;
