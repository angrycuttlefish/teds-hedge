"""Stage 2: Hedge-Fund Analyst — Transforms themes into institutional analysis.

Tools available: yfinance (company info, fundamentals, current prices).
Enriches analysis with real market data for any companies mentioned in themes.
"""

import json
import re

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from src.graph.research_state import ResearchState
from src.utils.llm import call_llm
from src.utils.progress import progress


class ThesisAnalysis(BaseModel):
    theme: str = Field(description="The original theme being analyzed")
    investment_thesis: str = Field(description="Structured investment thesis statement")
    tam_estimate: str = Field(description="Total addressable market size estimate with reasoning")
    supply_chain_map: list[str] = Field(description="Key players in the supply chain for this theme")
    competitive_landscape: str = Field(description="Analysis of competitive dynamics")
    key_catalysts: list[str] = Field(description="Near-term catalysts that could drive the thesis")
    key_risks: list[str] = Field(description="Primary risks that could invalidate the thesis")
    time_horizon: str = Field(description="Expected time horizon: near-term (0-6mo), medium (6-18mo), or long-term (18mo+)")
    conviction_level: str = Field(description="Analyst conviction: high, medium, or low")


class HedgeFundAnalystOutput(BaseModel):
    analyses: list[ThesisAnalysis] = Field(description="Institutional-grade analysis for each theme")
    cross_theme_insights: str = Field(description="How themes relate to or reinforce each other")


SYSTEM_PROMPT = """You are a senior hedge fund analyst at a top-tier fundamental long/short equity fund. You transform raw investment themes into institutional-grade analysis.

## Your Role
You are Stage 2 of a 5-stage research pipeline. You receive extracted themes from Stage 1 (Podcast Signal Extractor) and your output feeds into Stage 3 (Deep Research Synthesizer) which will design research plans to validate your theses.

## Available Data
You have been provided with **real-time market data** for companies mentioned in the themes. This data was fetched via yfinance and includes:
- **Company info**: sector, industry, market cap, employee count
- **Fundamentals**: P/E ratio, profit margins, revenue growth, debt/equity, free cash flow
- **Current price**: latest stock price

Use this data to ground your analysis in reality. Reference specific numbers from the market data when building theses (e.g., "NVDA's trailing P/E of 65x implies the market already prices in significant growth...").

## Your Tasks

For each theme provided, you must produce:

1. **Investment Thesis** — Frame the theme as a clear, testable investment thesis. Use the format: "We believe [X] because [Y], which will drive [Z]." Ground this in the provided market data where relevant.

2. **TAM Estimation** — Estimate the total addressable market. Use top-down and bottom-up approaches. Reference real market caps and revenue figures from the provided data.

3. **Supply Chain Mapping** — Identify key players across the value chain: suppliers, manufacturers, distributors, end customers. Include ticker symbols where possible.

4. **Competitive Landscape** — Who are the incumbents? Who are the disruptors? What are the barriers to entry? Reference real market cap and margin data for competitive comparisons.

5. **Catalysts** — What near-term events could prove or disprove the thesis? Earnings, regulatory decisions, product launches, macro shifts.

6. **Risks** — What could go wrong? Consider execution risk, competition, regulation, macro headwinds. Reference valuation multiples from the data to assess downside risk.

7. **Time Horizon** — When do you expect the thesis to play out?

8. **Cross-Theme Analysis** — How do the themes interact? Are there reinforcing dynamics or contradictions?

## Quality Standards
- Every thesis must reference at least one specific data point from the market data provided
- TAM estimates must show math, not just assertions
- Supply chain maps must include real companies (with tickers when possible)
- Conviction levels must be justified by the strength of evidence and data support
- Be intellectually honest about uncertainties — don't overstate what the data shows

Think like a PM presenting to the investment committee. Be specific, quantitative where possible, and intellectually honest about uncertainties.

You MUST respond with a JSON object matching the required schema."""


def _extract_tickers_from_themes(themes: dict) -> list[str]:
    """Extract potential ticker symbols from theme text."""
    tickers = set()
    text = json.dumps(themes)

    # Look for common ticker patterns (1-5 uppercase letters)
    # Filter out common English words that look like tickers
    noise = {"THE", "AND", "FOR", "NOT", "BUT", "ALL", "CAN", "HAS", "HER", "WAS", "ONE", "OUR", "OUT", "ARE", "HIS", "HOW", "ITS", "MAY", "NEW", "NOW", "OLD", "SEE", "WAY", "WHO", "DID", "GET", "LET", "SAY", "SHE", "TOO", "USE", "TAM", "CEO", "CFO", "IPO", "ETF", "GDP", "YOY", "QOQ"}
    pattern = r"\b([A-Z]{2,5})\b"
    for match in re.finditer(pattern, text):
        candidate = match.group(1)
        if candidate not in noise and len(candidate) <= 5:
            tickers.add(candidate)

    return list(tickers)[:15]  # Cap at 15 to avoid excessive API calls


def _fetch_company_data(tickers: list[str]) -> str:
    """Fetch real market data for mentioned companies via yfinance."""
    from src.data.market_data import (
        get_company_info,
        get_current_price,
        get_fundamentals,
    )

    sections = []
    for ticker in tickers:
        try:
            info = get_company_info(ticker)
            fundamentals = get_fundamentals(ticker)
            price = get_current_price(ticker)

            if not info.name or info.name == ticker:
                continue

            parts = [f"### {ticker} — {info.name}"]
            if info.sector:
                parts.append(f"Sector: {info.sector} | Industry: {info.industry or 'N/A'}")
            if fundamentals.get("market_cap"):
                mcap = fundamentals["market_cap"]
                parts.append(f"Market Cap: ${mcap / 1e9:.1f}B")
            if price:
                parts.append(f"Current Price: ${price:.2f}")
            if fundamentals.get("pe_ratio"):
                parts.append(f"P/E (TTM): {fundamentals['pe_ratio']:.1f}")
            if fundamentals.get("profit_margin"):
                parts.append(f"Profit Margin: {fundamentals['profit_margin'] * 100:.1f}%")
            if fundamentals.get("revenue_growth"):
                parts.append(f"Revenue Growth: {fundamentals['revenue_growth'] * 100:.1f}%")
            if fundamentals.get("debt_to_equity"):
                parts.append(f"Debt/Equity: {fundamentals['debt_to_equity']:.1f}")
            if fundamentals.get("free_cash_flow"):
                parts.append(f"Free Cash Flow: ${fundamentals['free_cash_flow'] / 1e9:.2f}B")

            sections.append("\n".join(parts))
        except Exception:
            continue

    if not sections:
        return ""

    return "## Market Data (via yfinance)\n\n" + "\n\n".join(sections)


def hedge_fund_analyst_agent(state: ResearchState, agent_id: str = "hedge_fund_analyst"):
    """Transforms extracted themes into institutional-grade investment analysis."""
    data = state["data"]
    themes = data.get("themes", {})

    progress.update_status(agent_id, None, "Building institutional analysis")

    # Fetch real market data for mentioned companies
    progress.update_status(agent_id, None, "Fetching market data")
    tickers = _extract_tickers_from_themes(themes)
    market_data_context = _fetch_company_data(tickers) if tickers else ""

    # Build enriched prompt with real data
    human_content = "Analyze these podcast themes and produce institutional-grade investment analysis:\n\n{themes}"
    if market_data_context:
        human_content += "\n\n---\n\n{market_data}"

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", human_content),
        ]
    )

    chain_input = prompt.invoke({"themes": json.dumps(themes, indent=2), "market_data": market_data_context})

    result = call_llm(
        prompt=chain_input,
        pydantic_model=HedgeFundAnalystOutput,
        agent_name=agent_id,
        state=state,
    )

    analysis_data = result.model_dump()

    progress.update_status(agent_id, None, f"Analyzed {len(analysis_data['analyses'])} theses")

    message = HumanMessage(content=json.dumps(analysis_data), name=agent_id)

    data["analyst_theses"] = analysis_data

    progress.update_status(agent_id, None, "Done")

    return {"messages": [message], "data": data}
