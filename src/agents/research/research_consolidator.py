"""Stage 4: Research Consolidator — Weighs evidence, assigns confidence scores.

Tools available: yfinance (price trends, fundamentals verification),
web search (recent news, sentiment check). Uses real data to verify
or challenge thesis assumptions before assigning confidence scores.
"""

import json
import re

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from src.graph.research_state import ResearchState
from src.utils.llm import call_llm
from src.utils.progress import progress


class EvidenceAssessment(BaseModel):
    thesis: str = Field(description="The thesis being assessed")
    supporting_evidence: list[str] = Field(description="Evidence supporting the thesis")
    contradicting_evidence: list[str] = Field(description="Evidence contradicting the thesis")
    unresolved_questions: list[str] = Field(description="Key questions that remain unanswered")
    confidence_score: int = Field(description="Confidence score 0-100")
    confidence_rationale: str = Field(description="Why this confidence score was assigned")
    key_assumption: str = Field(description="The single assumption on which the thesis stands or falls")
    what_would_change_view: str = Field(description="Specific, measurable trigger that would change the assessment")


class ResearchConsolidatorOutput(BaseModel):
    assessments: list[EvidenceAssessment] = Field(description="Evidence assessment for each thesis")
    contradictions_found: list[str] = Field(description="Material contradictions between or within theses")
    highest_conviction_thesis: str = Field(description="The thesis with strongest evidence")
    action_items: list[str] = Field(description="Remaining research actions before capital deployment")


SYSTEM_PROMPT = """You are the chief research officer at a systematic macro hedge fund. Your role is to synthesize multiple research streams, weigh evidence, and resolve contradictions before capital is deployed.

## Your Role
You are Stage 4 of a 5-stage research pipeline. You receive research plans from Stage 3 (Deep Research Synthesizer) and investment theses from Stage 2. Your output feeds into Stage 5 (Equity Screener) which will translate your confidence scores into specific equity ideas. The Equity Screener will only act on theses you give high confidence scores — your judgment is the gateway.

## Available Data (Already Fetched)
The following real-time data has been gathered to help you verify thesis assumptions:

1. **Stock Price Trends** — Recent price action for mentioned companies, showing how the market is already pricing these theses.
2. **Fundamental Verification** — Key financial metrics (revenue growth, margins, valuation multiples) from yfinance to ground-truth thesis assumptions.
3. **Recent News** — Latest web search results providing current market sentiment and developments.

Use this data to assign evidence-based confidence scores. A thesis with strong supporting data should score higher. A thesis contradicted by the actual numbers should score lower — regardless of how compelling the narrative sounds.

## Your Tasks

Given research plans and any available evidence, you must:

1. **Synthesize evidence streams** — Pull together all available evidence for each thesis. Reference specific data points from the provided market data and news. Look for convergence across multiple data sources.

2. **Identify contradictions** — Where does the evidence conflict? Between theses? Within a single thesis? Between the narrative and the actual numbers? Flag these explicitly.

3. **Assign confidence scores (0-100):**
   - 80-100: Strong evidence from multiple sources, actual financial data confirms thesis, limited contradictions
   - 60-79: Good evidence but some uncertainty remains, data partially confirms
   - 40-59: Mixed evidence, material contradictions exist between narrative and data
   - 20-39: Weak evidence, thesis is speculative, data does not yet support the narrative
   - 0-19: Evidence largely contradicts the thesis, financial data refutes key assumptions

4. **Identify the critical assumption** — Every thesis stands or falls on one key assumption. Name it and assess whether the provided data supports it.

5. **Define what would change your view** — Be specific and quantitative. "If NVDA's data center revenue growth decelerates below 30% YoY in the next earnings report" is better than "if AI demand slows."

6. **Rank by conviction** — Which thesis has the strongest evidence? This should be the focus for capital allocation.

7. **List remaining action items** — What research still needs to happen before you'd recommend trading on these theses?

## Quality Standards
- Confidence scores must be justified by specific evidence, not vibes
- Every score must reference at least one data point from the provided market data
- Contradicting evidence must be honestly reported — don't bury inconvenient facts
- "What would change your view" must be specific enough to be falsifiable within a defined timeframe
- Action items must be concrete and actionable (not "do more research")

Be intellectually honest. It's better to say "we don't know" than to overstate confidence. The PM needs to understand the true state of knowledge.

You MUST respond with a JSON object matching the required schema."""


def _extract_tickers(data: dict) -> list[str]:
    """Extract ticker symbols from thesis and research data."""
    tickers = set()
    text = json.dumps(data)

    noise = {"THE", "AND", "FOR", "NOT", "BUT", "ALL", "CAN", "HAS", "HER", "WAS", "ONE", "OUR", "OUT", "ARE", "HIS", "HOW", "ITS", "MAY", "NEW", "NOW", "OLD", "SEE", "WAY", "WHO", "DID", "GET", "LET", "SAY", "SHE", "TOO", "USE", "TAM", "CEO", "CFO", "IPO", "ETF", "GDP", "YOY", "QOQ"}
    pattern = r"\b([A-Z]{2,5})\b"
    for match in re.finditer(pattern, text):
        candidate = match.group(1)
        if candidate not in noise:
            tickers.add(candidate)

    return list(tickers)[:10]


def _fetch_verification_data(tickers: list[str]) -> str:
    """Fetch price trends, fundamentals, and recent news for evidence verification."""
    sections = []

    # Price trends
    try:
        from datetime import datetime

        from dateutil.relativedelta import relativedelta

        from src.data.market_data import get_stock_prices

        end = datetime.now().strftime("%Y-%m-%d")
        start = (datetime.now() - relativedelta(months=3)).strftime("%Y-%m-%d")

        price_sections = []
        for ticker in tickers[:5]:
            prices = get_stock_prices(ticker, start, end)
            if prices and len(prices) >= 2:
                first = prices[0].close
                last = prices[-1].close
                change_pct = ((last - first) / first) * 100
                direction = "up" if change_pct > 0 else "down"
                price_sections.append(f"- **{ticker}**: ${last:.2f} ({direction} {abs(change_pct):.1f}% over 3 months)")

        if price_sections:
            sections.append("## Price Trends (3-month, via yfinance)\n" + "\n".join(price_sections))
    except Exception:
        pass

    # Key fundamentals for verification
    try:
        from src.data.market_data import get_fundamentals

        fund_sections = []
        for ticker in tickers[:5]:
            f = get_fundamentals(ticker)
            if f.get("market_cap"):
                parts = [f"**{ticker}**:"]
                if f.get("revenue_growth"):
                    parts.append(f"Rev Growth {f['revenue_growth'] * 100:.1f}%")
                if f.get("profit_margin"):
                    parts.append(f"Margin {f['profit_margin'] * 100:.1f}%")
                if f.get("pe_ratio"):
                    parts.append(f"P/E {f['pe_ratio']:.1f}")
                fund_sections.append("- " + " | ".join(parts))

        if fund_sections:
            sections.append("## Fundamental Verification (via yfinance)\n" + "\n".join(fund_sections))
    except Exception:
        pass

    # Recent news
    try:
        from src.data.web_search import search_web

        news_sections = []
        for ticker in tickers[:3]:
            results = search_web(f"{ticker} stock news latest", max_results=2)
            for r in results:
                news_sections.append(f"- **{ticker}**: {r['title'][:60]} — {r['snippet'][:80]}")

        if news_sections:
            sections.append("## Recent News (via web search)\n" + "\n".join(news_sections))
    except Exception:
        pass

    return "\n\n".join(sections) if sections else ""


def research_consolidator_agent(state: ResearchState, agent_id: str = "research_consolidator"):
    """Weighs evidence, assigns confidence scores, and resolves contradictions."""
    data = state["data"]
    research_plans = data.get("research_plans", {})
    theses = data.get("analyst_theses", {})

    progress.update_status(agent_id, None, "Consolidating research")

    # Fetch real verification data
    progress.update_status(agent_id, None, "Verifying with market data")
    combined = {"theses": theses, "research_plans": research_plans}
    tickers = _extract_tickers(combined)
    verification_data = _fetch_verification_data(tickers) if tickers else ""

    # Build enriched prompt
    combined_input = {
        "theses": theses,
        "research_plans": research_plans,
    }

    human_content = "Consolidate the research and weigh the evidence for these theses:\n\n{research_data}"
    if verification_data:
        human_content += "\n\n---\n\n## Real-Time Verification Data\n\n{verification_data}"

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", human_content),
        ]
    )

    chain_input = prompt.invoke({"research_data": json.dumps(combined_input, indent=2), "verification_data": verification_data})

    result = call_llm(
        prompt=chain_input,
        pydantic_model=ResearchConsolidatorOutput,
        agent_name=agent_id,
        state=state,
    )

    consolidated_data = result.model_dump()

    progress.update_status(agent_id, None, f"Assessed {len(consolidated_data['assessments'])} theses")

    message = HumanMessage(content=json.dumps(consolidated_data), name=agent_id)

    data["consolidated_research"] = consolidated_data

    progress.update_status(agent_id, None, "Done")

    return {"messages": [message], "data": data}
