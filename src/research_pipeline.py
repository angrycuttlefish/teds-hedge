"""Research Pipeline — 5-stage agentic workflow from podcast signal to equity ideas.

Usage:
    poetry run python src/research_pipeline.py --transcript path/to/transcript.txt
    poetry run python src/research_pipeline.py --transcript path/to/transcript.txt --model qwen-3.5-9b
"""

import argparse
import json
import sys

from dotenv import load_dotenv
from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph
from colorama import init
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.json import JSON as RichJSON

from src.agents.research.podcast_signal_extractor import podcast_signal_extractor_agent
from src.agents.research.hedge_fund_analyst import hedge_fund_analyst_agent
from src.agents.research.deep_research_synthesizer import deep_research_synthesizer_agent
from src.agents.research.research_consolidator import research_consolidator_agent
from src.agents.research.equity_screener import equity_screener_agent
from src.graph.research_state import ResearchState
from src.utils.progress import progress

load_dotenv()
init(autoreset=True)

console = Console()

PIPELINE_STAGES = [
    ("podcast_signal_extractor", podcast_signal_extractor_agent),
    ("hedge_fund_analyst", hedge_fund_analyst_agent),
    ("deep_research_synthesizer", deep_research_synthesizer_agent),
    ("research_consolidator", research_consolidator_agent),
    ("equity_screener", equity_screener_agent),
]


def create_research_workflow():
    """Creates the LangGraph workflow for the research pipeline."""
    workflow = StateGraph(ResearchState)

    # Add all stage nodes
    for name, func in PIPELINE_STAGES:
        workflow.add_node(name, func)

    # Chain stages sequentially
    workflow.set_entry_point("podcast_signal_extractor")
    for i in range(len(PIPELINE_STAGES) - 1):
        workflow.add_edge(PIPELINE_STAGES[i][0], PIPELINE_STAGES[i + 1][0])
    workflow.add_edge(PIPELINE_STAGES[-1][0], END)

    return workflow


def display_results(final_state: dict):
    """Display the pipeline results using Rich formatting."""
    data = final_state.get("data", {})

    # Themes summary
    themes = data.get("themes", {})
    if themes and "themes" in themes:
        table = Table(title="Extracted Themes", show_header=True)
        table.add_column("Theme", style="cyan", max_width=40)
        table.add_column("Category", style="green")
        table.add_column("Signal", style="yellow")
        for t in themes["themes"]:
            table.add_row(t["theme"], t["category"], t["signal_strength"])
        console.print(table)
        console.print()

    # Consolidated research
    consolidated = data.get("consolidated_research", {})
    if consolidated and "assessments" in consolidated:
        table = Table(title="Thesis Confidence Scores", show_header=True)
        table.add_column("Thesis", style="cyan", max_width=50)
        table.add_column("Confidence", style="bold")
        table.add_column("Key Assumption", style="yellow", max_width=40)
        for a in consolidated["assessments"]:
            score = a["confidence_score"]
            color = "green" if score >= 70 else "yellow" if score >= 40 else "red"
            table.add_row(a["thesis"][:50], f"[{color}]{score}%[/{color}]", a["key_assumption"][:40])
        console.print(table)
        console.print()

    # Equity ideas
    equity_ideas = data.get("equity_ideas", {})
    if equity_ideas and "sectors" in equity_ideas:
        table = Table(title="Equity Ideas by Sector", show_header=True)
        table.add_column("Ticker", style="bold cyan")
        table.add_column("Company", style="white")
        table.add_column("Sector", style="green")
        table.add_column("Order", style="yellow")
        table.add_column("Conviction", style="bold")
        for sector in equity_ideas["sectors"]:
            for eq in sector["equities"]:
                table.add_row(eq["ticker"], eq["company_name"], eq["sector"], eq["order"], eq["conviction"])
        console.print(table)
        console.print()

        if equity_ideas.get("top_picks"):
            console.print(
                Panel(
                    " | ".join(equity_ideas["top_picks"]),
                    title="Top Picks",
                    style="bold green",
                )
            )
            console.print()

        if equity_ideas.get("portfolio_construction_notes"):
            console.print(
                Panel(
                    equity_ideas["portfolio_construction_notes"],
                    title="Portfolio Construction Notes",
                    style="blue",
                )
            )

    # Save full output
    output_path = "research_output.json"
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)
    console.print(f"\nFull output saved to [bold]{output_path}[/bold]")


def run_research_pipeline(transcript: str, model_name: str = "qwen-3.5-9b", model_provider: str = "LM Studio", show_reasoning: bool = False):
    """Run the full 5-stage research pipeline on a transcript."""
    progress.start()

    try:
        workflow = create_research_workflow()
        agent = workflow.compile()

        final_state = agent.invoke(
            {
                "messages": [HumanMessage(content="Analyze this transcript and generate equity ideas.")],
                "data": {"transcript": transcript},
                "metadata": {
                    "show_reasoning": show_reasoning,
                    "model_name": model_name,
                    "model_provider": model_provider,
                },
            }
        )

        display_results(final_state)
        return final_state

    finally:
        progress.stop()


def main():
    parser = argparse.ArgumentParser(description="Research Pipeline: From Podcast Signal to Equity Ideas")
    parser.add_argument("--transcript", type=str, required=True, help="Path to transcript file or raw text")
    parser.add_argument("--model", type=str, default="qwen-3.5-9b", help="LLM model to use (default: qwen-3.5-9b)")
    parser.add_argument("--provider", type=str, default="LM Studio", help="LLM provider (default: LM Studio)")
    parser.add_argument("--show-reasoning", action="store_true", help="Show detailed reasoning from each stage")
    parser.add_argument("--output", type=str, default="research_output.json", help="Output file path (default: research_output.json)")
    args = parser.parse_args()

    # Load transcript
    transcript = args.transcript
    try:
        with open(transcript, "r") as f:
            transcript = f.read()
        console.print(f"Loaded transcript from [bold]{args.transcript}[/bold] ({len(transcript)} chars)")
    except FileNotFoundError:
        # Treat as raw text if not a file
        console.print(f"Using provided text as transcript ({len(transcript)} chars)")

    console.print(
        Panel(
            f"Model: {args.model} | Provider: {args.provider}",
            title="Research Pipeline Configuration",
            style="bold blue",
        )
    )
    console.print()

    run_research_pipeline(
        transcript=transcript,
        model_name=args.model,
        model_provider=args.provider,
        show_reasoning=args.show_reasoning,
    )


if __name__ == "__main__":
    main()
