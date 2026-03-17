"""Integrated Pipeline — Research to Trading.

Runs the research pipeline first to identify equity opportunities,
then feeds those tickers into the existing hedge fund trading agents
for full analysis and portfolio decision-making.

Usage:
    poetry run python src/integrated_pipeline.py --input "https://youtube.com/watch?v=..."
    poetry run python src/integrated_pipeline.py --input path/to/transcript.txt --initial-cash 500000
"""

import argparse
import json
import sys
from datetime import datetime

from dateutil.relativedelta import relativedelta
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.inputs import detect_input_type, ingest, InputType
from src.main import run_hedge_fund
from src.research_pipeline import run_research_pipeline
from src.utils.display import print_trading_output

load_dotenv()

console = Console()


def extract_tickers_from_research(research_state: dict) -> list[str]:
    """Extract unique tickers from equity screener output, ordered by conviction."""
    data = research_state.get("data", {})
    equity_ideas = data.get("equity_ideas", {})

    if not equity_ideas or "sectors" not in equity_ideas:
        return []

    # Prioritize by conviction: high > medium > low
    conviction_order = {"high": 0, "medium": 1, "low": 2}
    tickers_with_priority = []

    for sector in equity_ideas["sectors"]:
        for eq in sector.get("equities", []):
            ticker = eq.get("ticker", "").strip().upper()
            conviction = eq.get("conviction", "low").lower()
            if ticker:
                tickers_with_priority.append((ticker, conviction_order.get(conviction, 3)))

    # Sort by conviction priority, deduplicate
    tickers_with_priority.sort(key=lambda x: x[1])
    seen = set()
    tickers = []
    for ticker, _ in tickers_with_priority:
        if ticker not in seen:
            seen.add(ticker)
            tickers.append(ticker)

    return tickers


def run_integrated_pipeline(
    source: str,
    skip_video: bool = False,
    model_name: str = "qwen-3.5-9b",
    model_provider: str = "LM Studio",
    show_reasoning: bool = False,
    initial_cash: float = 100000.0,
    margin_requirement: float = 0.0,
    selected_analysts: list[str] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    max_tickers: int = 10,
):
    """Run the full integrated pipeline: Research → Trading.

    1. Ingests content (YouTube, Substack, PDF, text)
    2. Runs 5-stage research pipeline to identify equity opportunities
    3. Extracts tickers from research output
    4. Runs trading pipeline on those tickers for portfolio decisions
    """
    # Ingest content
    input_type = detect_input_type(source)
    type_labels = {
        InputType.YOUTUBE: "YouTube Video",
        InputType.SUBSTACK: "Substack Article",
        InputType.PDF: "PDF Document",
        InputType.TEXT_FILE: "Text File",
        InputType.RAW_TEXT: "Raw Text",
    }

    console.print(
        Panel(
            f"Source: {type_labels.get(input_type, input_type)}\n" f"Model: {model_name} | Provider: {model_provider}\n" f"Cash: ${initial_cash:,.0f} | Max Tickers: {max_tickers}",
            title="Integrated Pipeline: Research → Trading",
            style="bold magenta",
        )
    )
    console.print()

    console.print("[bold]Stage 1/2: Ingesting content...[/bold]")
    try:
        transcript, actual_type = ingest(source, skip_video=skip_video, model_name=model_name, model_provider=model_provider)
        console.print(f"[green]Ingested {type_labels.get(actual_type, actual_type)}[/green] ({len(transcript)} chars)")
    except Exception as e:
        console.print(f"[red]Error ingesting content:[/red] {e}")
        return None

    # Run research pipeline
    console.print()
    console.print("[bold]Stage 2/2: Running research pipeline...[/bold]")
    research_state = run_research_pipeline(
        transcript=transcript,
        model_name=model_name,
        model_provider=model_provider,
        show_reasoning=show_reasoning,
        input_source=source,
        input_type=actual_type,
    )

    # Extract tickers
    tickers = extract_tickers_from_research(research_state)
    if not tickers:
        console.print("[yellow]No tradeable tickers identified from research. Pipeline complete.[/yellow]")
        return research_state

    # Cap tickers
    tickers = tickers[:max_tickers]

    console.print()
    console.print(
        Panel(
            " | ".join(tickers),
            title=f"Research → {len(tickers)} Tickers for Trading Analysis",
            style="bold cyan",
        )
    )

    # Set date range
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")
    if not start_date:
        start_date = (datetime.now() - relativedelta(months=3)).strftime("%Y-%m-%d")

    # Build portfolio
    portfolio = {
        "cash": initial_cash,
        "margin_requirement": margin_requirement,
        "margin_used": 0.0,
        "positions": {ticker: {"long": 0, "short": 0, "long_cost_basis": 0.0, "short_cost_basis": 0.0, "short_margin_used": 0.0} for ticker in tickers},
        "realized_gains": {ticker: {"long": 0.0, "short": 0.0} for ticker in tickers},
    }

    # Run trading pipeline
    console.print()
    console.print("[bold]Running trading analysis on research-identified tickers...[/bold]")

    result = run_hedge_fund(
        tickers=tickers,
        start_date=start_date,
        end_date=end_date,
        portfolio=portfolio,
        show_reasoning=show_reasoning,
        selected_analysts=selected_analysts or [],
        model_name=model_name,
        model_provider=model_provider,
    )

    print_trading_output(result)

    return {"research": research_state, "trading": result}


def main():
    parser = argparse.ArgumentParser(description="Integrated Pipeline: Research → Trading Decisions")
    parser.add_argument("--input", type=str, required=True, help="YouTube URL, Substack URL, PDF path, text file, or raw text")
    parser.add_argument("--model", type=str, default="qwen-3.5-9b", help="LLM model (default: qwen-3.5-9b)")
    parser.add_argument("--provider", type=str, default="LM Studio", help="LLM provider (default: LM Studio)")
    parser.add_argument("--initial-cash", type=float, default=100000.0, help="Starting cash (default: $100,000)")
    parser.add_argument("--margin-requirement", type=float, default=0.0, help="Margin requirement (default: 0)")
    parser.add_argument("--start-date", type=str, help="Analysis start date (default: 3 months ago)")
    parser.add_argument("--end-date", type=str, help="Analysis end date (default: today)")
    parser.add_argument("--max-tickers", type=int, default=10, help="Max tickers from research (default: 10)")
    parser.add_argument("--show-reasoning", action="store_true", help="Show detailed reasoning")
    parser.add_argument("--skip-video", action="store_true", help="Skip video download for YouTube")
    args = parser.parse_args()

    run_integrated_pipeline(
        source=args.input,
        skip_video=args.skip_video,
        model_name=args.model,
        model_provider=args.provider,
        show_reasoning=args.show_reasoning,
        initial_cash=args.initial_cash,
        margin_requirement=args.margin_requirement,
        start_date=args.start_date,
        end_date=args.end_date,
        max_tickers=args.max_tickers,
    )


if __name__ == "__main__":
    main()
