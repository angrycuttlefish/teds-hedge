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

## Phase 3: Input Handling ✅ (Done)

### 3.1 YouTube video + transcript ingestion
- [x] `src/inputs/youtube.py` — Full YouTube video ingestion (not just audio/transcript)
- [x] **Download full video** via `yt-dlp` (not just audio — charts/graphs shown on screen matter)
- [x] Extract transcript via `youtube-transcript-api` (captions) as the text layer
- [x] **Extract key frames** from video using `opencv-python` — detect scene changes, chart/slide transitions
- [x] **Visual analysis** — Send extracted frames to LLM vision for chart/graph/slide interpretation
- [x] Combine transcript text + visual descriptions into enriched transcript
- [x] Extract video metadata (title, channel, date, duration)
- [x] Store downloaded video + extracted frames in local `data/videos/` directory
- [x] Configurable: `--skip-video` flag to fall back to transcript-only mode for speed

### 3.2 Substack post fetcher
- [x] `src/inputs/substack.py` — Fetch and parse Substack article from URL
- [x] Extract article text, author, date
- [x] Handle paywalled content gracefully (error message)

### 3.3 PDF reader
- [x] `src/inputs/pdf_reader.py` — Extract text from uploaded PDF files
- [x] Handle multi-page research reports
- [x] Support tables and structured content

### 3.4 Unified input handler
- [x] `src/inputs/__init__.py` — Auto-detect input type (URL vs file path vs raw text)
- [x] Route to appropriate fetcher based on input
- [x] Normalize all inputs to enriched transcript format (text + visual descriptions)
- [x] For YouTube: merge transcript text with visual frame analysis into single enriched document

---

## Phase 4: Market Data + Storage ✅ (Done)

### 4.1 yfinance integration
- [x] `src/data/market_data.py` — Fetch historical stock prices, options chains, fundamentals via yfinance
- [x] Replace/supplement Financial Datasets API calls where applicable
- [x] Support options data (chains, greeks, IV) for equity screener output

### 4.2 DuckDB local database
- [x] `src/data/db.py` — DuckDB connection manager
- [x] Schema for storing: research runs, themes, theses, equity ideas, market data
- [x] Query helpers for retrieving past research
- [x] `src/data/schema.sql` — DDL for all tables

### 4.3 Research persistence
- [x] Save each pipeline run to DuckDB with timestamp
- [x] Track thesis confidence over time (as new evidence arrives)
- [x] Query past runs: "What did we think about AI infrastructure 3 months ago?"

---

## Phase 5: Deep Research Integration ✅ (Done)

- [x] Connect Stage 3 output to web search / document retrieval — `src/data/web_search.py`
- [x] SEC filing fetcher (EDGAR API) — `src/data/sec_fetcher.py`
- [ ] Earnings call transcript integration (future — can use SEC 8-K filings)
- [x] Feed retrieved research back into Stage 4 — all agents now fetch real data and inject into prompts

---

## Phase 6: Portfolio Integration ✅ (Done)

- [x] Connect Stage 5 output to existing hedge fund agents — `src/integrated_pipeline.py`
- [x] Cross-reference screened equities with portfolio positions
- [x] yfinance options data for trade sizing — `src/data/market_data.py`
- [x] Feed into risk manager and portfolio manager

---

## Phase 7: Research Pipeline Web UI ✅ (Done)

### 7.1 Backend SSE endpoint
- [x] `app/backend/routes/research_pipeline.py` — SSE streaming at `POST /research-pipeline/run`
- [x] `ResearchPipelineRequest` schema added to `app/backend/models/schemas.py`
- [x] Content ingestion in background thread with progress events
- [x] Client disconnect detection and task cancellation

### 7.2 Frontend research view
- [x] `app/frontend/src/components/research/research-pipeline-view.tsx` — Full pipeline UI
- [x] `app/frontend/src/services/research-api.ts` — SSE client service
- [x] Extended tab system with `'research'` tab type
- [x] "Research Pipeline" button in left sidebar
- [x] Vertical stepper with animated status indicators (idle/running/complete/error)
- [x] Results display: Top Picks, Themes, Thesis Confidence bars, Equity Ideas table

### 7.3 Agent tool integration
- [x] All 5 research agents now fetch real data (yfinance, SEC, web search) before LLM calls
- [x] Agent prompts include role context, available data descriptions, and quality standards

---

## Technical Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| LLM Provider | LM Studio (local) | Free, no API key, runs Qwen 3.5 9B locally |
| Orchestration | LangGraph | Already used in repo |
| Model | qwen-3.5-9b (LM Studio) | Free local model, no API costs |
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
- LM Studio installed and running with Qwen 3.5 9B loaded
- No API key needed — uses local OpenAI-compatible API at `http://localhost:1234/v1`

### Optional
```bash
ANTHROPIC_API_KEY=sk-ant-...    # For Anthropic Claude models
FINANCIAL_DATASETS_API_KEY=...  # Legacy, yfinance preferred
```

### Run the research pipeline
```bash
# From YouTube video
poetry run python src/research_pipeline.py --input "https://youtube.com/watch?v=..."

# From Substack post
poetry run python src/research_pipeline.py --input "https://example.substack.com/p/..."

# From PDF file
poetry run python src/research_pipeline.py --input path/to/report.pdf

# From text file
poetry run python src/research_pipeline.py --input path/to/transcript.txt

# YouTube transcript-only mode (skip video download)
poetry run python src/research_pipeline.py --input "https://youtube.com/watch?v=..." --skip-video
```

### Run the integrated pipeline (Research → Trading)
```bash
# Research a YouTube video, then run trading analysis on identified tickers
poetry run python src/integrated_pipeline.py --input "https://youtube.com/watch?v=..." --initial-cash 500000

# Research a PDF report, then trade
poetry run python src/integrated_pipeline.py --input path/to/report.pdf --max-tickers 5
```

---

## File Structure
```
src/
├── agents/
│   └── research/
│       ├── __init__.py
│       ├── podcast_signal_extractor.py    ✅ (with visual analysis awareness)
│       ├── hedge_fund_analyst.py          ✅ (with yfinance data injection)
│       ├── deep_research_synthesizer.py   ✅ (with SEC + web search + financials)
│       ├── research_consolidator.py       ✅ (with price trends + news verification)
│       └── equity_screener.py             ✅ (with fundamentals + options data)
├── inputs/                                ✅ Phase 3
│   ├── __init__.py        (unified input handler + auto-detection)
│   ├── youtube.py         (yt-dlp + transcript + frame extraction + vision)
│   ├── substack.py        (article fetcher + paywall handling)
│   └── pdf_reader.py      (pdfplumber text + table extraction)
├── data/                                  ✅ Phase 4 + 5
│   ├── market_data.py    (yfinance: prices, options, fundamentals)
│   ├── db.py             (DuckDB connection + research persistence)
│   ├── schema.sql        (DDL for all tables)
│   ├── sec_fetcher.py    (SEC EDGAR 10-K/10-Q fetcher)
│   └── web_search.py     (DuckDuckGo web search for research)
├── graph/
│   └── research_state.py                  ✅
├── research_pipeline.py                   ✅ (with DuckDB persistence)
└── integrated_pipeline.py                 ✅ Phase 6 (Research → Trading)
app/
├── backend/
│   └── routes/
│       └── research_pipeline.py           ✅ Phase 7 (SSE streaming endpoint)
└── frontend/
    └── src/
        ├── components/research/
        │   └── research-pipeline-view.tsx  ✅ Phase 7 (Research pipeline UI)
        └── services/
            └── research-api.ts            ✅ Phase 7 (SSE client)
docs/
├── research-workflow-spec.md              ✅
└── build-plan.md                          ✅
.claude/
├── CLAUDE.md                              ✅
├── launch.json                            ✅ (dev server configs)
└── commands/
    ├── next-task.md                       ✅
    ├── status.md                          ✅
    └── verify.md                          ✅
```
