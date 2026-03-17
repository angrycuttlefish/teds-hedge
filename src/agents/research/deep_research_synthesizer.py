"""Stage 3: Deep Research Synthesizer — Designs high-leverage research prompts."""

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from src.graph.research_state import ResearchState
from src.utils.llm import call_llm
from src.utils.progress import progress
import json


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

For each thesis provided, design a research plan that:

1. **Generates targeted research questions** — Each question should be specific enough to have a definitive answer. Avoid vague questions. Good: "What is TSMC's capital expenditure guidance for 2025 in advanced nodes?" Bad: "Is the semiconductor industry growing?"

2. **Prioritizes by information value** — Rank questions by how much they would change the investment decision if answered. Focus on the questions where the answer is most uncertain and most impactful.

3. **Maps to data sources** — For each question, specify where to find the answer:
   - SEC filings (10-K, 10-Q, proxy statements)
   - Earnings call transcripts
   - Industry reports (Gartner, McKinsey, etc.)
   - Government data (BLS, Census, Fed)
   - Company investor presentations
   - Patent filings
   - Import/export data
   - Web search for recent developments

4. **Defines confirming vs. refuting evidence** — For each question, clearly state what answer would confirm the thesis and what would refute it. This prevents confirmation bias.

5. **Identifies critical data points** — What are the 2-3 numbers or facts that would most decisively prove or disprove the thesis?

Design research that is efficient — a PM should be able to execute this plan in hours, not weeks.

You MUST respond with a JSON object matching the required schema."""


def deep_research_synthesizer_agent(state: ResearchState, agent_id: str = "deep_research_synthesizer"):
    """Designs high-leverage research questions and prompts for each thesis."""
    data = state["data"]
    theses = data.get("analyst_theses", {})

    progress.update_status(agent_id, None, "Designing research prompts")

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "Design a research plan for these investment theses:\n\n{theses}"),
    ])

    chain_input = prompt.invoke({"theses": json.dumps(theses, indent=2)})

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
