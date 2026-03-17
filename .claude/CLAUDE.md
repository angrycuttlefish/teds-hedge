# AI Hedge Fund — Claude Code Instructions

## Project Overview

AI-powered hedge fund proof of concept for educational purposes. Uses multiple AI agents (based on famous investors' philosophies) to analyze stocks and make collaborative trading decisions. Also includes a **research pipeline** that transforms podcast/video signals into actionable equity ideas.

**Always read these files first when starting work:**
- `docs/build-plan.md` — Current task checklist and project status
- `docs/research-workflow-spec.md` — Research pipeline specification

## Repository Structure

```
teds-hedge/
├── src/
│   ├── agents/              # Trading agents (investor personas + analysts)
│   │   └── research/        # Research pipeline agents (5-stage workflow)
│   ├── backtesting/         # Backtesting engine
│   ├── graph/               # LangGraph state definitions
│   ├── llm/                 # LLM provider configs and model definitions
│   ├── tools/               # Financial data API client
│   ├── utils/               # Shared utilities (display, progress, LLM helpers)
│   ├── cli/                 # CLI argument parsing
│   ├── main.py              # Hedge fund CLI entry point
│   ├── backtester.py        # Backtester CLI entry point
│   └── research_pipeline.py # Research pipeline CLI entry point
├── app/
│   ├── backend/             # FastAPI REST API
│   └── frontend/            # React + TypeScript + Vite dashboard
├── docs/                    # Specifications and build plans
└── .claude/                 # Claude Code instructions (this file)
```

---

## Git Workflow (CRITICAL)

**NEVER commit directly to `main`.** All changes go through feature branches and pull requests. No exceptions.

### Branch → PR → Test → Merge flow

```
1. git checkout -b feat/my-feature    # Create branch from main
2. <make changes, commit>
3. Run full QA suite (see below)
4. git push -u origin feat/my-feature
5. gh pr create --title "feat: ..." --body "..."
6. LOCAL TESTING MUST PASS before requesting merge
7. gh pr merge <number> --merge       # Only after QA passes
8. git checkout main && git pull
```

### Branch naming

| Type | Pattern | Example |
|------|---------|---------|
| Feature | `feature/description` | `feature/agentic-research-workflow` |
| Bug fix | `fix/description` | `fix/bare-except-api-parsing` |
| Docs | `docs/description` | `docs/research-pipeline-spec` |
| Chore | `chore/description` | `chore/update-dependencies` |

### Commit messages

Use conventional commits: `feat:`, `fix:`, `docs:`, `chore:`, `refactor:`, `test:`

Keep commits atomic — one logical change per commit. Never commit secrets or `.env` files.

---

## Quality Assurance (MUST PASS BEFORE MERGE)

**No PR may be merged to `main` until local testing passes.** This is non-negotiable.

### Before every commit

```bash
poetry run black src/ --check
poetry run isort src/ --check
poetry run flake8 src/
poetry run pytest
```

### Before requesting a merge to main

1. **Lint + format + tests** — All four checks above must pass
2. **Local functional test** — Run the affected feature end-to-end:
   - Trading pipeline: `poetry run python src/main.py --ticker AAPL --start-date 2024-01-01 --end-date 2024-06-01`
   - Research pipeline: `poetry run python src/research_pipeline.py --transcript <test_input>`
   - Backtester: `poetry run python src/backtester.py --ticker AAPL --start-date 2024-01-01 --end-date 2024-06-01`
   - Web app: `./run.sh` and verify in browser
3. **Import check** — `poetry run python -c "from src.research_pipeline import run_research_pipeline"` (or equivalent for changed modules)
4. **No regressions** — Your changes must not break other features

### Testing can be via
- **CLI** — Run the pipeline with test inputs and verify output
- **Web browser GUI** — Start the app and verify in browser
- **Unit tests** — `poetry run pytest`

### Key checks
- All Python files must pass black formatting (line-length=420)
- No unused imports
- Tests in `tests/` directory

---

## Technology Stack

| Layer | Technology |
|-------|-----------|
| LLM Orchestration | LangGraph, LangChain |
| LLM Provider (default) | LM Studio (Qwen 3.5 9B local) |
| Market Data | yfinance (stocks, options, fundamentals) |
| Database | DuckDB (local analytics, research persistence) |
| Backend | FastAPI, SQLAlchemy, Alembic |
| Frontend | React, TypeScript, Vite, Tailwind |
| Data | Pandas, NumPy |
| Display | Rich, Colorama |
| Package Manager | Poetry |
| Python | 3.11+ |

---

## LLM Configuration

### LM Studio + Qwen 3.5 9B (Default)
The pipeline defaults to `qwen-3.5-9b` served locally via LM Studio's OpenAI-compatible API at `http://localhost:1234/v1`. No API key needed — just have LM Studio running with the model loaded.

```bash
# Optional: override the default LM Studio URL in .env
# LM_STUDIO_BASE_URL=http://localhost:1234/v1
```

Other providers (Anthropic, OpenAI, Groq, etc.) are also supported — pass `--model` and `--provider` at the CLI.

### Agent LLM calls
All agent LLM calls go through `src/utils/llm.py:call_llm()` which handles:
- Model selection from state metadata
- Structured output (JSON mode or manual extraction)
- Retry logic with defaults on failure

### Model configs
Model configs in `src/llm/models.py` with JSON model lists in `src/llm/api_models.json`.

---

## Research Pipeline (New)

The research pipeline is a 5-stage agentic workflow in `src/agents/research/`:

1. **Podcast Signal Extractor** — Extracts investable themes from transcripts
2. **Hedge-Fund Analyst** — Transforms themes into institutional analysis
3. **Deep Research Synthesizer** — Generates high-leverage research prompts
4. **Research Consolidator** — Weighs evidence, resolves contradictions
5. **Equity Screener** — Identifies first/second/third-order equity winners

Entry point: `src/research_pipeline.py`

### Input sources
- **YouTube videos** — Paste URL, downloads full video via `yt-dlp`, extracts transcript + key frames. Charts/graphs shown on screen are analyzed via Claude Vision and merged into an enriched transcript. Use `--skip-video` for transcript-only mode.
- **Substack posts** — Paste URL, auto-fetches article text
- **PDF files** — Provide file path, extracts text

### Run examples
```bash
poetry run python src/research_pipeline.py --transcript "https://youtube.com/watch?v=..."
poetry run python src/research_pipeline.py --transcript "https://example.substack.com/p/..."
poetry run python src/research_pipeline.py --transcript path/to/report.pdf
poetry run python src/research_pipeline.py --transcript path/to/transcript.txt
```

---

## Common Patterns

### Adding a new agent
1. Create agent file in `src/agents/` (or `src/agents/research/` for research pipeline)
2. Define a Pydantic model for structured output
3. Write the agent function taking `AgentState` + `agent_id`
4. Use `call_llm()` for LLM calls
5. Use `progress.update_status()` for terminal progress
6. Return `{"messages": [...], "data": data}`

### State management
- Trading agents use `AgentState` from `src/graph/state.py`
- Research pipeline uses `ResearchState` from `src/graph/research_state.py`
- Both are TypedDict with `Annotated` merge functions

---

## Data & Storage

### yfinance (Market Data)
Used for historical stock prices, options chains, fundamentals. No API key needed.
- Module: `src/data/market_data.py`
- Covers: price history, options data, company info, financials

### DuckDB (Local Database)
Zero-config embedded analytics database for persisting research runs.
- Module: `src/data/db.py`
- Schema: `src/data/schema.sql`
- Stores: research runs, themes, theses, equity ideas, market data snapshots
- Query past research to track thesis evolution over time

---

## Environment Variables

Required:
- **LM Studio running** with Qwen 3.5 9B loaded (default, no API key needed)

Optional in `.env`:
- `LM_STUDIO_BASE_URL` — Override LM Studio URL (default: `http://localhost:1234/v1`)
- `ANTHROPIC_API_KEY` — For Anthropic Claude models
- `FINANCIAL_DATASETS_API_KEY` — For stock data (legacy, yfinance preferred)
- `OPENAI_API_KEY`, `GROQ_API_KEY`, etc. — For other LLM providers

---

## Continuous Self-Improvement (IMPORTANT)

Every task that surfaces a new lesson must leave the codebase documentation and agent definitions smarter than before. This is a core operating principle — not optional.

### After Every Task / PR

1. **Identify lessons learned** — Ask yourself:
   - Did anything fail unexpectedly? What was the root cause?
   - Did I hit a pitfall that isn't documented?
   - Did I discover a new pattern, convention, or constraint?
   - Did a workaround become a permanent pattern worth codifying?

2. **Update the right place:**
   - **Agent-specific lesson** (e.g., research pipeline prompt pattern) → Update the relevant agent file in `src/agents/research/`
   - **Repo-wide lesson** (e.g., LangGraph behaviour, poetry/dependency issue, LLM provider quirk) → Update this file (`.claude/CLAUDE.md`)
   - **New reusable check or workflow** → Add or update a slash command in `.claude/commands/`
   - **Build plan change** → Update `docs/build-plan.md`

3. **Include in the PR** — When proposing a PR, note any doc/agent updates made under a `## Self-improvement` section in the PR body:
   ```
   ## Self-improvement
   - Added "XYZ" to CLAUDE.md common pitfalls
   - Updated QA checklist with new check for ABC
   ```

4. **Keep it actionable** — Document the specific pattern or check that would have prevented the issue, not just a description of what went wrong. Future agents should be able to follow the instruction without needing the backstory.

Mistakes are valuable — but only if they're captured so they never repeat.

---

## Common Pitfalls (Learned from Experience)

_This section grows over time. Add new entries as they are discovered._

1. **Poetry + Python version mismatch:** Poetry may auto-select a different Python version than expected. Check `poetry env info` and ensure the venv matches the project's `python` constraint in `pyproject.toml`.
2. **youtube-transcript-api Python cap:** This package has an upper Python version bound (`<3.15`). Use `python = "<3.15"` marker in pyproject.toml.
3. **LangGraph state merging:** TypedDict fields with `Annotated[..., merge_dicts]` do a shallow merge. Nested dicts must be handled carefully — don't rely on deep merge behaviour.
4. **Pydantic v1 vs v2:** LangChain still references Pydantic v1 compatibility layer. On Python 3.14+ you'll see deprecation warnings. These are harmless but noisy.
5. **`call_llm` defaults:** Always pass state and agent_name to `call_llm` to use the configured provider. Without them it falls back to the system default (currently qwen-3.5-9b/LM Studio).
6. **Claude Max setup tokens don't work with the API:** OAuth tokens from `claude setup-token` (sk-ant-oat01-...) only work with claude.ai's internal systems. They return 400 errors when used with `api.anthropic.com`. You must use a regular API key from https://console.anthropic.com.
