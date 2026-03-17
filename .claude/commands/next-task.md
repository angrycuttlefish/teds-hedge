# /next-task — Pick up the next uncompleted task

1. Read `docs/build-plan.md`
2. Find the first unchecked `[ ]` item in the current phase
3. For actionable tasks:
   a. Read the relevant docs (`docs/research-workflow-spec.md`, existing agent files for patterns)
   b. **Create a feature branch** before making changes: `git checkout -b feature/description`
   c. Implement following all standards in `.claude/CLAUDE.md`
   d. Use existing patterns from `src/agents/` as reference
   e. Run the full QA suite:
      ```bash
      poetry run black src/ --check
      poetry run isort src/ --check
      poetry run flake8 src/
      poetry run pytest
      ```
   f. **Run a local functional test** of the affected feature (CLI or browser):
      - Research pipeline: `poetry run python src/research_pipeline.py --transcript <test_input>`
      - Trading pipeline: `poetry run python src/main.py --ticker AAPL --start-date 2024-01-01 --end-date 2024-06-01`
      - Import check: `poetry run python -c "from src.research_pipeline import run_research_pipeline"`
   g. Commit with a conventional commit message
   h. Push the branch and create a PR: `gh pr create --title "..." --body "..."`
   i. Update `docs/build-plan.md` — check off completed items

4. **Self-improvement step** (mandatory):
   - Did anything fail unexpectedly? Document it in `.claude/CLAUDE.md` under Common Pitfalls
   - Did you discover a new pattern or constraint? Update the relevant docs
   - Include a `## Self-improvement` section in the PR body noting any doc updates

**IMPORTANT:**
- Never commit directly to `main`. Always use feature branches + PRs.
- Never request a merge until local testing passes (QA + functional test).
- Every task must leave the docs smarter than it found them.
