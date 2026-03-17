"""Stage 3: Deep Research Synthesizer — Designs and partially executes research plans.

Tools available: SEC EDGAR (10-K, 10-Q filings), web search (DuckDuckGo),
yfinance (financials, company facts). Fetches real data to answer research
questions where possible, enriching the LLM's research plan with evidence.
"""

import json
import re

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from src.graph.research_state import ResearchState
from src.utils.llm import call_llm
from src.utils.progress import progress


class ResearchQuestion(BaseModel):
    question: str = Field(description="The specific research question to investigate")
    information_value: str = Field(description="Why answering this question matters: high, medium, or low impact on thesis")
    data_sources: list[str] = Field(description="Where to find the answer: SEC filings, earnings calls, industry reports, etc.")
    confirming_evidence: str = Field(description="What evidence would confirm the thesis")
    refuting_evidence: str = Field(description="What evidence would refute the thesis")


class ThesisResearchPlan(BaseModel):
    thesis: str = Field(description="The investment thesis being researched")
    research_questions: list[ResearchQuestion] = Field(description="Prioritized research questions for this thesis")
    critical_data_points: list[str] = Field(description="The single most important data points to find")


class DeepResearchOutput(BaseModel):
    research_plans: list[ThesisResearchPlan] = Field(description="Research plan for each thesis")
    cross_cutting_questions: list[str] = Field(description="Questions that apply across multiple theses")


SYSTEM_PROMPT = """You are a research director at an elite fundamental equity research firm. Your job is to design the most efficient research plan to validate or invalidate investment theses.

## Your Role
You are Stage 3 of a 5-stage research pipeline. You receive investment theses from Stage 2 (Hedge Fund Analyst) and your output feeds into Stage 4 (Research Consolidator) which will weigh evidence and assign confidence scores.

## Available Tools (Already Executed)
The following data has been automatically gathered for you using real tools:

1. **SEC EDGAR Filings** — Recent 10-K annual reports for companies mentioned in the theses have been fetched. Filing metadata and key excerpts are provided below.

2. **Web Search Results** — DuckDuckGo searches related to each thesis have been executed. Recent news, analysis, and data are provided below.

3. **Financial Statements** — yfinance financial data (income statement, balance sheet, cash flow) for key companies has been retrieved.

Use this pre-fetched evidence to enrich your research plan. When a research question can already be partially answered by the provided data, note what the data shows and what remains unanswered.

## Your Tasks

For each thesis provided, design a research plan that:

1. **Generates targeted research questions** — Each question should be specific enough to have a definitive answer. Avoid vague questions. Good: "What is TSMC's capital expenditure guidance for 2025 in advanced nodes?" Bad: "Is the semiconductor industry growing?"

2. **Prioritizes by information value** — Rank questions by how much they would change the investment decision if answered. Focus on the questions where the answer is most uncertain and most impactful.

3. **Maps to data sources** — For each question, specify where to find the answer:
   - SEC filings (10-K, 10-Q, proxy statements) — check if the provided filing data already answers it
   - Earnings call transcripts
   - Industry reports (Gartner, McKinsey, etc.)
   - Government data (BLS, Census, Fed)
   - Company investor presentations
   - Web search — check if the provided search results already answer it
   - Patent filings
   - Import/export data

4. **Defines confirming vs. refuting evidence** — For each question, clearly state what answer would confirm the thesis and what would refute it. This prevents confirmation bias.

5. **Identifies critical data points** — What are the 2-3 numbers or facts that would most decisively prove or disprove the thesis? Reference the provided data where it already supplies these numbers.

## Quality Standards
- Research questions must be specific and answerable — no vague open-ended questions
- If the provided data already answers a question, acknowledge it and note the answer
- Each thesis should have 3-7 targeted research questions
- Critical data points must be quantitative where possible (revenue figures, growth rates, market share)
- Cross-cutting questions should reveal systemic risks or reinforcing dynamics

Design research that is efficient — a PM should be able to execute this plan in hours, not weeks.

You MUST respond with a JSON object matching the required schema."""


def _extract_tickers_from_theses(theses: dict) -> list[str]:
    """Extract ticker symbols from thesis analysis text."""
    tickers = set()
    text = json.dumps(theses)

    noise = {"THE", "AND", "FOR", "NOT", "BUT", "ALL", "CAN", "HAS", "HER", "WAS", "ONE", "OUR", "OUT", "ARE", "HIS", "HOW", "ITS", "MAY", "NEW", "NOW", "OLD", "SEE", "WAY", "WHO", "DID", "GET", "LET", "SAY", "SHE", "TOO", "USE", "TAM", "CEO", "CFO", "IPO", "ETF", "GDP", "YOY", "QOQ"}
    pattern = r"\b([A-Z]{2,5})\b"
    for match in re.finditer(pattern, text):
        candidate = match.group(1)
        if candidate not in noise:
            tickers.add(candidate)

    return list(tickers)[:10]


def _fetch_research_context(tickers: list[str], theses: dict) -> str:
    """Fetch SEC filings, web search results, and financial data for research context."""
    sections = []

    # SEC filings for top tickers
    try:
        from src.data.sec_fetcher import get_filings

        filing_sections = []
        for ticker in tickers[:5]:
            filings = get_filings(ticker, filing_type="10-K", limit=1)
            if filings:
                f = filings[0]
                filing_sections.append(f"- **{ticker}** 10-K filed {f['filing_date']} (Accession: {f['accession_number']})")

        if filing_sections:
            sections.append("## SEC Filing Data (via EDGAR)\n" + "\n".join(filing_sections))
    except Exception as e:
        sections.append(f"## SEC Filing Data\n[SEC fetch failed: {e}]")

    # Web search for each thesis
    try:
        from src.data.web_search import search_web

        search_sections = []
        for analysis in theses.get("analyses", []):
            thesis_text = analysis.get("investment_thesis", analysis.get("theme", ""))[:80]
            results = search_web(thesis_text, max_results=3)
            if results:
                search_sections.append(f'### Search: "{thesis_text}"')
                for r in results:
                    search_sections.append(f"- [{r['title'][:60]}]({r['url']}): {r['snippet'][:100]}")

        if search_sections:
            sections.append("## Web Search Results (via DuckDuckGo)\n" + "\n".join(search_sections))
    except Exception as e:
        sections.append(f"## Web Search Results\n[Search failed: {e}]")

    # Financial statements for key tickers
    try:
        from src.data.market_data import get_financials

        fin_sections = []
        for ticker in tickers[:3]:
            fins = get_financials(ticker)
            if fins.get("income_statement"):
                fin_sections.append(f"- **{ticker}**: Financial statements available (income, balance sheet, cash flow)")

        if fin_sections:
            sections.append("## Financial Statements (via yfinance)\n" + "\n".join(fin_sections))
    except Exception:
        pass

    return "\n\n".join(sections) if sections else ""


def deep_research_synthesizer_agent(state: ResearchState, agent_id: str = "deep_research_synthesizer"):
    """Designs high-leverage research questions and prompts for each thesis."""
    data = state["data"]
    theses = data.get("analyst_theses", {})

    progress.update_status(agent_id, None, "Designing research prompts")

    # Fetch real research context
    progress.update_status(agent_id, None, "Fetching SEC filings + web data")
    tickers = _extract_tickers_from_theses(theses)
    research_context = _fetch_research_context(tickers, theses) if tickers else ""

    # Build enriched prompt
    human_content = "Design a research plan for these investment theses:\n\n{theses}"
    if research_context:
        human_content += "\n\n---\n\n## Pre-Fetched Research Data\n\n{research_context}"

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", human_content),
        ]
    )

    chain_input = prompt.invoke({"theses": json.dumps(theses, indent=2), "research_context": research_context})

    result = call_llm(
        prompt=chain_input,
        pydantic_model=DeepResearchOutput,
        agent_name=agent_id,
        state=state,
    )

    research_data = result.model_dump()

    total_questions = sum(len(plan["research_questions"]) for plan in research_data["research_plans"])
    progress.update_status(agent_id, None, f"Generated {total_questions} research questions")

    message = HumanMessage(content=json.dumps(research_data), name=agent_id)

    data["research_plans"] = research_data

    progress.update_status(agent_id, None, "Done")

    return {"messages": [message], "data": data}
