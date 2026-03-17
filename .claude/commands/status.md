# /status — Check current build progress

Read `docs/build-plan.md`, then report:

1. **Project status** — What phases are complete, what's in progress, what's blocked
2. **What's next** — The first unchecked task in the current phase
3. **Build health** — Run these checks and report results:

```bash
poetry run black src/ --check   # Formatting OK?
poetry run isort src/ --check   # Import order OK?
poetry run flake8 src/          # Lint OK?
poetry run pytest               # Tests pass?
```

4. **Import check** — Verify key modules are importable:
```bash
poetry run python -c "from src.research_pipeline import run_research_pipeline; print('Pipeline OK')"
poetry run python -c "from src.main import run_hedge_fund; print('Hedge fund OK')"
```

5. **Git status** — Current branch? Uncommitted changes? Ahead/behind remote?
6. **Merge readiness** — Can the current branch be merged?
   - All QA checks pass?
   - Local functional test run?
   - Self-improvement step done?

Report as a summary table:

| Area | Status | Details |
|------|--------|---------|
| Formatting | PASS/FAIL | error count |
| Imports | PASS/FAIL | error count |
| Lint | PASS/FAIL | error count |
| Tests | PASS/FAIL | pass/fail counts |
| Pipeline Import | PASS/FAIL | error details |
| Git | branch name | clean/dirty |
| Merge Ready | YES/NO | what's blocking |
