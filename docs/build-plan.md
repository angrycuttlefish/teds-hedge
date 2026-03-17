# Build Plan: Agentic Research Workflow

## Goal
Implement the 5-stage AI Research Skill Architecture as a new pipeline in the existing ai-hedge-fund repo, powered by Claude Max subscription (OAuth token), with YouTube/Substack/PDF input support, yfinance for market data, and DuckDB for local storage.

---

## Phase 1: Core Pipeline Agents ✅ (Done)

### 1.1 Create new agent module structure
- [x] `src/agents/research/podcast_signal_extractor.py` — Stage 1
- [x] `src/agents/research/hedge_fund_analyst.py` — Stage 2
- [x] `src/agents/research/deep_research_synthesizer.py` — Stage 3
- [x] `src/agents/research/research_consolidator.py` — Stage 4
- [x] `src/agents/research/equity_screener.py` — Stage 5
- [x] `src/agents/research/__init__.py` — Package init

### 1.2 Define pipeline state
- [x] `src/graph/research_state.py` — TypedDict for research pipeline state

### 1.3 Create pipeline orchestrator
- [x] `src/research_pipeline.py` — CLI entry point that chains the 5 stages via LangGraph

### 1.4 Project configuration
- [x] `.claude/CLAUDE.md` — Claude Code instructions
- [x] `.claude/commands/` — Agent skills (next-task, status, verify)
- [x] `docs/research-workflow-spec.md` — Pipeline specification
- [x] `docs/build-plan.md` — This file

---

## Phase 2: Claude Max + LLM Setup ✅ (Done)

### 2.1 Claude Max setup token integration
- [x] Created `.env` with `CLAUDE_CODE_OAUTH_TOKEN` placeholder
- [x] Updated `.env.example` with setup token as primary auth method
- [x] Updated `src/llm/models.py` — Anthropic provider checks `CLAUDE_CODE_OAUTH_TOKEN` first, falls back to `ANTHROPIC_API_KEY`
- [x] Changed default model from GPT-4.1/OpenAI to claude-sonnet-4-20250514/Anthropic in `call_llm`, `get_agent_model_config`, and `main.py`
- [x] Added Claude Sonnet 4 to `api_models.json` and moved Claude models to top of list
- [ ] **USER ACTION:** Run `claude setup-token` (outside Claude Code) and paste token into `.env`

### 2.2 Dependencies
- [x] Add `youtube-transcript-api` to pyproject.toml
- [x] Add `yfinance` to pyproject.toml
- [x] Add `duckdb` to pyproject.toml
- [x] Add `pdfplumber` to pyproject.toml
- [x] Add `beautifulsoup4` for Substack parsing
- [x] Add `yt-dlp` to pyproject.toml (full video download for visual analysis)
- [x] Add `opencv-python` to pyproject.toml (frame extraction from video)

---

## Phase 3: Input Handling (Next Sprint)

### 3.1 YouTube video + transcript ingestion
- [ ] `src/inputs/youtube.py` — Full YouTube video ingestion (not just audio/transcript)
- [ ] **Download full video** via `yt-dlp` (not just audio — charts/graphs shown on screen matter)
- [ ] Extract transcript via `youtube-transcript-api` (captions) as the text layer
- [ ] **Extract key frames** from video using `opencv-python` — detect scene changes, chart/slide transitions
- [ ] **Visual analysis** — Send extracted frames to Claude vision for chart/graph/slide interpretation
- [ ] Combine transcript text + visual descriptions into enriched transcript
- [ ] Extract video metadata (title, channel, date, duration)
- [ ] Store downloaded video + extracted frames in local `data/videos/` directory
- [ ] Configurable: `--skip-video` flag to fall back to transcript-only mode for speed

### 3.2 Substack post fetcher
- [ ] `src/inputs/substack.py` — Fetch and parse Substack article from URL
- [ ] Extract article text, author, date
- [ ] Handle paywalled content gracefully (error message)

### 3.3 PDF reader
- [ ] `src/inputs/pdf_reader.py` — Extract text from uploaded PDF files
- [ ] Handle multi-page research reports
- [ ] Support tables and structured content

### 3.4 Unified input handler
- [ ] `src/inputs/__init__.py` — Auto-detect input type (URL vs file path vs raw text)
- [ ] Route to appropriate fetcher based on input
- [ ] Normalize all inputs to enriched transcript format (text + visual descriptions)
- [ ] For YouTube: merge transcript text with visual frame analysis into single enriched document

---

## Phase 4: Market Data + Storage (Future)

### 4.1 yfinance integration
- [ ] `src/data/market_data.py` — Fetch historical stock prices, options chains, fundamentals via yfinance
- [ ] Replace/supplement Financial Datasets API calls where applicable
- [ ] Support options data (chains, greeks, IV) for equity screener output

### 4.2 DuckDB local database
- [ ] `src/data/db.py` — DuckDB connection manager
- [ ] Schema for storing: research runs, themes, theses, equity ideas, market data
- [ ] Query helpers for retrieving past research
- [ ] `src/data/schema.sql` — DDL for all tables

### 4.3 Research persistence
- [ ] Save each pipeline run to DuckDB with timestamp
- [ ] Track thesis confidence over time (as new evidence arrives)
- [ ] Query past runs: "What did we think about AI infrastructure 3 months ago?"

---

## Phase 5: Deep Research Integration (Future)

- [ ] Connect Stage 3 output to web search / document retrieval
- [ ] SEC filing fetcher (EDGAR API)
- [ ] Earnings call transcript integration
- [ ] Feed retrieved research back into Stage 4

---

## Phase 6: Portfolio Integration (Future)

- [ ] Connect Stage 5 output to existing hedge fund agents
- [ ] Cross-reference screened equities with portfolio positions
- [ ] yfinance options data for trade sizing
- [ ] Feed into risk manager and portfolio manager

---

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| LLM Provider | Anthropic (API key) | Best models for financial analysis |
| Orchestration | LangGraph | Already used in repo |
| Model | claude-sonnet-4-6 | Latest Sonnet — best balance of speed/quality |
| Market Data | yfinance | Free, no API key needed, covers stocks + options |
| Database | DuckDB | Fast local analytics DB, zero config, SQL interface |
| Input Sources | YouTube (video+transcript), Substack, PDF | Primary content formats for research workflow |
| Video Download | yt-dlp | Full video download — charts/slides shown on screen are critical signals |
| Frame Extraction | opencv-python | Detect scene changes, extract chart/slide frames for vision analysis |
| Visual Analysis | Claude Vision | Send key frames to Claude for chart/graph/slide interpretation |
| State mgmt | TypedDict | Consistent with existing `AgentState` |
| Output format | Structured JSON + DuckDB | Machine-readable, queryable, persistent |

---

## Environment Setup

### Required
```bash
# Add to .env — get key at https://console.anthropic.com
ANTHROPIC_API_KEY=sk-ant-...
```

### Optional
```bash
FINANCIAL_DATASETS_API_KEY=...  # Legacy, yfinance preferred
```

### Run the pipeline
```bash
# From YouTube video
poetry run python src/research_pipeline.py --transcript "https://youtube.com/watch?v=..."

# From Substack post
poetry run python src/research_pipeline.py --transcript "https://example.substack.com/p/..."

# From PDF file
poetry run python src/research_pipeline.py --transcript path/to/report.pdf

# From text file
poetry run python src/research_pipeline.py --transcript path/to/transcript.txt
```

---

## File Structure
```
src/
├── agents/
│   └── research/
│       ├── __init__.py
│       ├── podcast_signal_extractor.py    ✅
│       ├── hedge_fund_analyst.py          ✅
│       ├── deep_research_synthesizer.py   ✅
│       ├── research_consolidator.py       ✅
│       └── equity_screener.py             ✅
├── inputs/                                🔲 Phase 3
│   ├── __init__.py
│   ├── youtube.py         (yt-dlp + transcript + frame extraction + vision)
│   ├── substack.py
│   └── pdf_reader.py
├── data/                                  🔲 Phase 4
│   ├── market_data.py    (yfinance)
│   ├── db.py             (DuckDB)
│   └── schema.sql
├── graph/
│   └── research_state.py                  ✅
└── research_pipeline.py                   ✅
docs/
├── research-workflow-spec.md              ✅
└── build-plan.md                          ✅
.claude/
├── CLAUDE.md                              ✅
└── commands/
    ├── next-task.md                       ✅
    ├── status.md                          ✅
    └── verify.md                          ✅
```
