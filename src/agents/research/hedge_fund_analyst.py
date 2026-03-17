"""Stage 2: Hedge-Fund Analyst — Transforms themes into institutional analysis."""

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from src.graph.research_state import ResearchState
from src.utils.llm import call_llm
from src.utils.progress import progress
import json


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

For each theme provided, you must produce:

1. **Investment Thesis** — Frame the theme as a clear, testable investment thesis. Use the format: "We believe [X] because [Y], which will drive [Z]."

2. **TAM Estimation** — Estimate the total addressable market. Use top-down and bottom-up approaches. Show your reasoning.

3. **Supply Chain Mapping** — Identify key players across the value chain: suppliers, manufacturers, distributors, end customers.

4. **Competitive Landscape** — Who are the incumbents? Who are the disruptors? What are the barriers to entry? What's the competitive moat?

5. **Catalysts** — What near-term events could prove or disprove the thesis? Earnings, regulatory decisions, product launches, macro shifts.

6. **Risks** — What could go wrong? Consider execution risk, competition, regulation, macro headwinds.

7. **Time Horizon** — When do you expect the thesis to play out?

8. **Cross-Theme Analysis** — How do the themes interact? Are there reinforcing dynamics or contradictions?

Think like a PM presenting to the investment committee. Be specific, quantitative where possible, and intellectually honest about uncertainties.

You MUST respond with a JSON object matching the required schema."""


def hedge_fund_analyst_agent(state: ResearchState, agent_id: str = "hedge_fund_analyst"):
    """Transforms extracted themes into institutional-grade investment analysis."""
    data = state["data"]
    themes = data.get("themes", {})

    progress.update_status(agent_id, None, "Building institutional analysis")

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "Analyze these podcast themes and produce institutional-grade investment analysis:\n\n{themes}"),
    ])

    chain_input = prompt.invoke({"themes": json.dumps(themes, indent=2)})

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
