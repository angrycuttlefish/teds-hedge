"""Stage 5: Equity Screener — Identifies first-, second-, and third-order winners.

Tools available: yfinance (current prices, fundamentals, options chains, company info).
Enriches equity ideas with real market data so recommendations are grounded in
current valuations, not just narrative.
"""

import json
import re

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from src.graph.research_state import ResearchState
from src.utils.llm import call_llm
from src.utils.progress import progress


class EquityIdea(BaseModel):
    ticker: str = Field(description="Stock ticker symbol")
    company_name: str = Field(description="Full company name")
    sector: str = Field(description="Sector classification")
    order: str = Field(description="Impact order: 1st-order (direct), 2nd-order (supply chain), or 3rd-order (derivative)")
    thesis_connection: str = Field(description="How this equity connects to the investment thesis")
    expected_impact: str = Field(description="Expected magnitude of impact: transformative, significant, moderate, or marginal")
    catalyst_timeline: str = Field(description="When the catalyst is expected to play out")
    conviction: str = Field(description="Conviction level: high, medium, or low")
    upside_potential: str = Field(description="Qualitative upside assessment with reasoning")
    key_metric_to_watch: str = Field(description="The single metric that will confirm or deny the thesis for this stock")


class SectorCluster(BaseModel):
    sector: str = Field(description="Sector name")
    equities: list[EquityIdea] = Field(description="Equity ideas in this sector")
    sector_thesis: str = Field(description="The overarching thesis for this sector")


class EquityScreenerOutput(BaseModel):
    sectors: list[SectorCluster] = Field(description="Equity ideas organized by sector")
    top_picks: list[str] = Field(description="Top 3-5 highest conviction tickers across all sectors")
    portfolio_construction_notes: str = Field(description="Notes on how to construct a portfolio from these ideas — sizing, hedges, correlation")


SYSTEM_PROMPT = """You are a portfolio strategist at a multi-strategy hedge fund. Your role is to translate research insights into specific equity ideas, organized by order of impact.

## Your Role
You are Stage 5 — the final stage — of a 5-stage research pipeline. You receive consolidated research with confidence scores from Stage 4 and investment theses from Stage 2. Your output is the actionable end product: specific equity ideas that a portfolio manager can trade.

## Available Data (Already Fetched)
You have been provided with **real-time market data** for potential equity picks, fetched via yfinance:

1. **Current Prices** — Latest stock prices so your recommendations reflect today's entry points.
2. **Fundamentals** — P/E ratios, revenue growth, margins, debt levels, free cash flow — use these to assess whether the thesis is already priced in.
3. **Market Caps** — For position sizing context (large-cap vs. mid-cap vs. small-cap).
4. **Options Data** — Available expirations and option chain info for hedging/leveraging positions.

Use this data to make your recommendations actionable. Reference specific valuations when discussing upside potential. Flag stocks where the thesis may already be priced in (high P/E, strong recent price appreciation).

## Your Tasks

Given consolidated research with confidence scores, you must:

1. **Map themes to equities** — For each validated thesis (especially those with high confidence scores), identify specific stocks that would benefit. Be specific with tickers. Only recommend tickers that exist and are tradeable.

2. **Classify by order of impact:**
   - **1st Order (Direct):** Companies directly in the path of the theme. E.g., if the theme is "AI infrastructure buildout," NVDA is a 1st-order play.
   - **2nd Order (Supply Chain):** Companies that supply or enable the 1st-order players. E.g., TSMC, ASML for the AI infrastructure theme.
   - **3rd Order (Derivative):** Companies that benefit indirectly. E.g., commercial real estate near data centers, power utilities serving AI clusters.

3. **Rank by conviction** — Consider:
   - Strength of the thesis connection
   - Confidence score from research consolidation (Stage 4)
   - Current valuation relative to thesis upside (use the provided P/E, price data)
   - Magnitude of potential impact on the company's fundamentals
   - Catalyst timeline (sooner = higher conviction for near-term trades)

4. **Identify the key metric** — For each equity, what's the single most important number to watch? This is the "canary in the coal mine" for whether the thesis is playing out. Be specific (e.g., "Data center revenue growth rate in Q3 earnings" not "revenue growth").

5. **Portfolio construction notes** — How should these ideas be combined? Consider:
   - Position sizing relative to conviction and market cap (larger positions in high-conviction, liquid names)
   - Correlation between picks (avoid concentration risk)
   - Natural hedges within the portfolio
   - Long/short opportunities (if a thesis has losers, identify them)
   - Reference current prices for entry point context

## Quality Standards
- Every ticker must be a real, currently traded US stock (or ADR)
- Upside potential assessments must reference the provided valuation data (e.g., "Trading at 25x P/E vs. sector average of 30x suggests room for multiple expansion")
- Top picks must include at least one 2nd or 3rd order idea (not just obvious 1st-order plays)
- Portfolio construction notes must be specific enough to guide actual position sizing
- Flag any picks where the thesis may already be fully priced in based on current multiples

Focus on liquid, publicly traded US equities. Include international ADRs where relevant. Prioritize actionability — these ideas should be tradeable tomorrow.

You MUST respond with a JSON object matching the required schema."""


def _extract_candidate_tickers(data: dict) -> list[str]:
    """Extract potential ticker symbols from consolidated research and theses."""
    tickers = set()
    text = json.dumps(data)

    noise = {"THE", "AND", "FOR", "NOT", "BUT", "ALL", "CAN", "HAS", "HER", "WAS", "ONE", "OUR", "OUT", "ARE", "HIS", "HOW", "ITS", "MAY", "NEW", "NOW", "OLD", "SEE", "WAY", "WHO", "DID", "GET", "LET", "SAY", "SHE", "TOO", "USE", "TAM", "CEO", "CFO", "IPO", "ETF", "GDP", "YOY", "QOQ"}
    pattern = r"\b([A-Z]{2,5})\b"
    for match in re.finditer(pattern, text):
        candidate = match.group(1)
        if candidate not in noise:
            tickers.add(candidate)

    return list(tickers)[:20]


def _fetch_screening_data(tickers: list[str]) -> str:
    """Fetch current prices, fundamentals, and options info for equity screening."""
    from src.data.market_data import (
        get_company_info,
        get_current_price,
        get_fundamentals,
        get_options_chain,
    )

    sections = []
    equity_data = []

    for ticker in tickers:
        try:
            price = get_current_price(ticker)
            if not price:
                continue

            info = get_company_info(ticker)
            fundamentals = get_fundamentals(ticker)

            parts = [f"### {ticker} — {info.name}"]
            if info.sector:
                parts.append(f"Sector: {info.sector} | Industry: {info.industry or 'N/A'}")
            parts.append(f"Price: ${price:.2f}")
            if fundamentals.get("market_cap"):
                mcap = fundamentals["market_cap"]
                size = "Large-cap" if mcap > 10e9 else "Mid-cap" if mcap > 2e9 else "Small-cap"
                parts.append(f"Market Cap: ${mcap / 1e9:.1f}B ({size})")
            if fundamentals.get("pe_ratio"):
                parts.append(f"P/E (TTM): {fundamentals['pe_ratio']:.1f}")
            if fundamentals.get("forward_pe"):
                parts.append(f"Forward P/E: {fundamentals['forward_pe']:.1f}")
            if fundamentals.get("revenue_growth"):
                parts.append(f"Revenue Growth: {fundamentals['revenue_growth'] * 100:.1f}%")
            if fundamentals.get("profit_margin"):
                parts.append(f"Profit Margin: {fundamentals['profit_margin'] * 100:.1f}%")
            if fundamentals.get("free_cash_flow"):
                parts.append(f"FCF: ${fundamentals['free_cash_flow'] / 1e9:.2f}B")
            if fundamentals.get("beta"):
                parts.append(f"Beta: {fundamentals['beta']:.2f}")

            equity_data.append("\n".join(parts))
        except Exception:
            continue

    if equity_data:
        sections.append("## Equity Screening Data (via yfinance)\n\n" + "\n\n".join(equity_data))

    # Options availability for top tickers
    options_sections = []
    for ticker in tickers[:5]:
        try:
            chain = get_options_chain(ticker)
            if chain.get("available_expirations"):
                exps = chain["available_expirations"][:3]
                options_sections.append(f"- **{ticker}**: Options available, nearest expirations: {', '.join(exps)}")
        except Exception:
            continue

    if options_sections:
        sections.append("## Options Availability\n" + "\n".join(options_sections))

    return "\n\n".join(sections) if sections else ""


def equity_screener_agent(state: ResearchState, agent_id: str = "equity_screener"):
    """Identifies first-, second-, and third-order equity winners from consolidated research."""
    data = state["data"]
    consolidated = data.get("consolidated_research", {})
    theses = data.get("analyst_theses", {})

    progress.update_status(agent_id, None, "Screening equities")

    # Fetch real market data for screening
    progress.update_status(agent_id, None, "Fetching market data for candidates")
    combined = {"consolidated_research": consolidated, "analyst_theses": theses}
    tickers = _extract_candidate_tickers(combined)
    screening_data = _fetch_screening_data(tickers) if tickers else ""

    # Build enriched prompt
    combined_input = {
        "consolidated_research": consolidated,
        "analyst_theses": theses,
    }

    human_content = "Screen for equity ideas based on this consolidated research:\n\n{research_data}"
    if screening_data:
        human_content += "\n\n---\n\n{screening_data}"

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", human_content),
        ]
    )

    chain_input = prompt.invoke({"research_data": json.dumps(combined_input, indent=2), "screening_data": screening_data})

    result = call_llm(
        prompt=chain_input,
        pydantic_model=EquityScreenerOutput,
        agent_name=agent_id,
        state=state,
    )

    screener_data = result.model_dump()

    total_equities = sum(len(sector["equities"]) for sector in screener_data["sectors"])
    progress.update_status(agent_id, None, f"Identified {total_equities} equity ideas")

    message = HumanMessage(content=json.dumps(screener_data), name=agent_id)

    data["equity_ideas"] = screener_data

    progress.update_status(agent_id, None, "Done")

    return {"messages": [message], "data": data}
