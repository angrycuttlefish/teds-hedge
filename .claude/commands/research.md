# /research — Run the 5-stage research pipeline from within Claude Code

Accepts a URL (YouTube, Substack), PDF path, ticker symbol, or raw text and runs the full research pipeline step-by-step, reporting progress at each stage.

## Input: $ARGUMENTS

## Instructions

1. **Detect input type** and report what was received:
   - YouTube URL → will download video + transcript (or transcript-only with `--skip-video`)
   - Substack URL → will fetch article text
   - PDF file path → will extract text from PDF
   - Ticker symbol (e.g. AAPL, NVDA) → will fetch recent news/data via yfinance and create a research brief
   - Raw text → will use directly as transcript

2. **Run the research pipeline** end-to-end:

```bash
poetry run python src/research_pipeline.py --input "$ARGUMENTS" --skip-video
```

Use `--skip-video` by default for speed. If the user explicitly asks for video/visual analysis, remove the flag.

3. **Monitor and report progress** through the 5 stages:
   - Stage 1: Podcast Signal Extractor — extracting investable themes
   - Stage 2: Hedge-Fund Analyst — transforming themes into institutional analysis
   - Stage 3: Deep Research Synthesizer — generating research prompts + fetching data
   - Stage 4: Research Consolidator — weighing evidence, resolving contradictions
   - Stage 5: Equity Screener — identifying equity winners with entry/exit levels

4. **If the pipeline fails**, check these common causes:
   - LM Studio not running → remind user to start LM Studio with Qwen 3.5 9B loaded
   - Context window too small → suggest increasing `n_ctx` to 16384+ in LM Studio
   - YouTube transcript unavailable → suggest trying `--skip-video` or a different URL
   - Network errors for SEC/web search → these are non-fatal, pipeline will continue with available data

5. **Display results** after completion:
   - Read `research_output.json` in the project root (the pipeline writes output there)
   - Summarize: top equity picks, key themes, thesis confidence levels
   - Present the most actionable ideas in a clear format

6. **If input is a ticker symbol** (no URL or file path detected):
   - First, create a brief research prompt about the ticker using yfinance data
   - Then run the pipeline with that generated text as input:
   ```bash
   poetry run python -c "
   import yfinance as yf
   t = yf.Ticker('$ARGUMENTS')
   info = t.info
   print(f'Research brief for {info.get(\"shortName\", \"$ARGUMENTS\")} ({\"$ARGUMENTS\"}):')
   print(f'Sector: {info.get(\"sector\", \"N/A\")}')
   print(f'Industry: {info.get(\"industry\", \"N/A\")}')
   print(f'Market Cap: {info.get(\"marketCap\", \"N/A\")}')
   print(f'Current Price: {info.get(\"currentPrice\", \"N/A\")}')
   print(f'52w Range: {info.get(\"fiftyTwoWeekLow\", \"N/A\")} - {info.get(\"fiftyTwoWeekHigh\", \"N/A\")}')
   print(f'Summary: {info.get(\"longBusinessSummary\", \"N/A\")[:500]}')
   " > /tmp/ticker_brief.txt && poetry run python src/research_pipeline.py --input /tmp/ticker_brief.txt
   ```

**IMPORTANT:** Always run the pipeline from the project root directory (`/Users/dylan/Documents/GitHub/b/teds-hedge`).
