"""Stage 5: Equity Screener — Identifies first-, second-, and third-order winners."""

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from src.graph.research_state import ResearchState
from src.utils.llm import call_llm
from src.utils.progress import progress
import json


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

Given consolidated research with confidence scores, you must:

1. **Map themes to equities** — For each validated thesis, identify specific stocks that would benefit. Be specific with tickers.

2. **Classify by order of impact:**
   - **1st Order (Direct):** Companies directly in the path of the theme. E.g., if the theme is "AI infrastructure buildout," NVDA is a 1st-order play.
   - **2nd Order (Supply Chain):** Companies that supply or enable the 1st-order players. E.g., TSMC, ASML for the AI infrastructure theme.
   - **3rd Order (Derivative):** Companies that benefit indirectly. E.g., commercial real estate near data centers, power utilities serving AI clusters.

3. **Rank by conviction** — Consider:
   - Strength of the thesis connection
   - Confidence score from research consolidation
   - Magnitude of potential impact on the company's fundamentals
   - Catalyst timeline (sooner = higher conviction for near-term trades)

4. **Identify the key metric** — For each equity, what's the single most important number to watch? This is the "canary in the coal mine" for whether the thesis is playing out.

5. **Portfolio construction notes** — How should these ideas be combined? Consider:
   - Position sizing relative to conviction
   - Correlation between picks (avoid concentration risk)
   - Natural hedges within the portfolio
   - Long/short opportunities

Focus on liquid, publicly traded US equities. Include international ADRs where relevant. Prioritize actionability — these ideas should be tradeable tomorrow.

You MUST respond with a JSON object matching the required schema."""


def equity_screener_agent(state: ResearchState, agent_id: str = "equity_screener"):
    """Identifies first-, second-, and third-order equity winners from consolidated research."""
    data = state["data"]
    consolidated = data.get("consolidated_research", {})
    theses = data.get("analyst_theses", {})

    progress.update_status(agent_id, None, "Screening equities")

    combined_input = {
        "consolidated_research": consolidated,
        "analyst_theses": theses,
    }

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "Screen for equity ideas based on this consolidated research:\n\n{research_data}"),
    ])

    chain_input = prompt.invoke({"research_data": json.dumps(combined_input, indent=2)})

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
