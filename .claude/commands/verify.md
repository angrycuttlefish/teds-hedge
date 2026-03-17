# /verify — Run full verification suite before merge

This command runs ALL checks required before a PR can be merged to main.

## Pre-merge checklist

### 1. Code quality checks
```bash
poetry run black src/ --check     # Formatting
poetry run isort src/ --check     # Import order
poetry run flake8 src/            # Lint
poetry run pytest                 # Unit tests
```

### 2. Import verification
```bash
poetry run python -c "from src.research_pipeline import run_research_pipeline; print('Research pipeline: OK')"
poetry run python -c "from src.main import run_hedge_fund; print('Hedge fund: OK')"
poetry run python -c "from src.backtester import main; print('Backtester: OK')"
```

### 3. Functional test (run at least ONE)
- **CLI test:** Run the affected pipeline with real or test inputs
- **Browser test:** Start the web app and verify in browser
- Report what was tested and what the output was

### 4. Self-improvement check
- Review changes made in this branch
- Check if any new pitfalls were discovered
- Verify `.claude/CLAUDE.md` Common Pitfalls is up to date
- Verify `docs/build-plan.md` reflects current state

## Report format

| Check | Status | Details |
|-------|--------|---------|
| Black | PASS/FAIL | file count |
| Isort | PASS/FAIL | file count |
| Flake8 | PASS/FAIL | error count |
| Tests | PASS/FAIL | pass/fail/skip counts |
| Research Pipeline Import | PASS/FAIL | error details |
| Hedge Fund Import | PASS/FAIL | error details |
| Backtester Import | PASS/FAIL | error details |
| Functional Test | PASS/FAIL/NOT RUN | what was tested |
| Self-improvement | DONE/NOT DONE | what was updated |

## Verdict

After running all checks, report one of:
- **READY TO MERGE** — All checks pass, functional test done, self-improvement complete
- **NOT READY** — List what's failing and what needs to be fixed
- **BLOCKED** — External dependency or issue preventing verification

Also report:
- Any missing agent files in `src/agents/research/`
- Uncommitted changes in the working tree
- Current branch name
