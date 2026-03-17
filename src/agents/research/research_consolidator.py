"""Stage 4: Research Consolidator — Weighs evidence and resolves contradictions."""

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from src.graph.research_state import ResearchState
from src.utils.llm import call_llm
from src.utils.progress import progress
import json


class EvidenceAssessment(BaseModel):
    thesis: str = Field(description="The investment thesis being assessed")
    supporting_evidence: list[str] = Field(description="Evidence supporting the thesis")
    contradicting_evidence: list[str] = Field(description="Evidence contradicting the thesis")
    unresolved_questions: list[str] = Field(description="Key questions that remain unanswered")
    confidence_score: int = Field(description="Confidence in the thesis 0-100")
    confidence_rationale: str = Field(description="Why this confidence level was assigned")
    key_assumption: str = Field(description="The single most critical assumption the thesis depends on")
    what_would_change_view: str = Field(description="What new information would flip the view")


class ResearchConsolidatorOutput(BaseModel):
    assessments: list[EvidenceAssessment] = Field(description="Evidence assessment for each thesis")
    contradictions_found: list[str] = Field(description="Contradictions between different theses or evidence streams")
    highest_conviction_thesis: str = Field(description="Which thesis has the strongest evidence base")
    action_items: list[str] = Field(description="Remaining research actions needed before trading")


SYSTEM_PROMPT = """You are the chief research officer at a systematic macro hedge fund. Your role is to synthesize multiple research streams, weigh evidence, and resolve contradictions before capital is deployed.

Given research plans and any available evidence, you must:

1. **Synthesize evidence streams** — Pull together all available evidence for each thesis. Look for convergence across multiple data sources.

2. **Identify contradictions** — Where does the evidence conflict? Between theses? Within a single thesis? Flag these explicitly.

3. **Assign confidence scores (0-100):**
   - 80-100: Strong evidence, multiple confirming sources, limited contradictions
   - 60-79: Good evidence but some uncertainty remains
   - 40-59: Mixed evidence, material contradictions exist
   - 20-39: Weak evidence, thesis is speculative
   - 0-19: Evidence largely contradicts the thesis

4. **Identify the critical assumption** — Every thesis stands or falls on one key assumption. Name it.

5. **Define what would change your view** — Be specific. "If NVDA's data center revenue growth decelerates below 30% YoY" is better than "if AI demand slows."

6. **Rank by conviction** — Which thesis has the strongest evidence? This should be the focus for capital allocation.

7. **List remaining action items** — What research still needs to happen before you'd recommend trading on these theses?

Be intellectually honest. It's better to say "we don't know" than to overstate confidence. The PM needs to understand the true state of knowledge.

You MUST respond with a JSON object matching the required schema."""


def research_consolidator_agent(state: ResearchState, agent_id: str = "research_consolidator"):
    """Weighs evidence, assigns confidence scores, and resolves contradictions."""
    data = state["data"]
    research_plans = data.get("research_plans", {})
    theses = data.get("analyst_theses", {})

    progress.update_status(agent_id, None, "Consolidating research")

    combined_input = {
        "theses": theses,
        "research_plans": research_plans,
    }

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "Consolidate the research and weigh the evidence for these theses:\n\n{research_data}"),
    ])

    chain_input = prompt.invoke({"research_data": json.dumps(combined_input, indent=2)})

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
