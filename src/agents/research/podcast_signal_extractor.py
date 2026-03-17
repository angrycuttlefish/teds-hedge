"""Stage 1: Podcast Signal Extractor — Separates signal from noise in long-form podcasts."""

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from src.graph.research_state import ResearchState
from src.utils.llm import call_llm
from src.utils.progress import progress
import json


class PodcastTheme(BaseModel):
    theme: str = Field(description="The investable theme or signal identified")
    category: str = Field(description="Category: macro, sector, company-specific, or contrarian")
    signal_strength: str = Field(description="Speaker conviction: high, medium, or low")
    supporting_quotes: list[str] = Field(description="Direct quotes from the transcript supporting this theme")
    context: str = Field(description="Brief context around why this theme matters")


class PodcastSignalOutput(BaseModel):
    themes: list[PodcastTheme] = Field(description="List of investable themes extracted from the podcast")
    podcast_summary: str = Field(description="One-paragraph summary of the podcast's key investment thesis")
    speakers_identified: list[str] = Field(description="Names/roles of speakers if identifiable")


SYSTEM_PROMPT = """You are an expert financial analyst specializing in extracting investable signals from long-form podcast and video content. Your job is to separate signal from noise.

Given a podcast or video transcript, you must:

1. **Identify investable themes** — Look for macro trends, sector calls, company-specific insights, and contrarian views that could drive investment decisions.

2. **Extract supporting quotes** — Pull direct quotes that substantiate each theme. These should be the strongest evidence for the thesis.

3. **Categorize each theme:**
   - `macro` — Broad economic or market-level signals (interest rates, inflation, geopolitics)
   - `sector` — Industry or sector-level calls (AI infrastructure, energy transition, biotech)
   - `company-specific` — Direct mentions of individual companies or their prospects
   - `contrarian` — Views that go against consensus or conventional wisdom

4. **Rate signal strength** based on the speaker's conviction:
   - `high` — Speaker is emphatic, uses definitive language, backs with data
   - `medium` — Speaker is thoughtful but hedged, mentions risks
   - `low` — Passing mention, speculative, or tangential

5. **Provide context** — Why does this theme matter? What's the investment implication?

Focus on actionable intelligence. Ignore filler, self-promotion, and off-topic tangents.

You MUST respond with a JSON object matching the required schema."""


def podcast_signal_extractor_agent(state: ResearchState, agent_id: str = "podcast_signal_extractor"):
    """Extracts investable themes and signals from a podcast/video transcript."""
    data = state["data"]
    transcript = data.get("transcript", "")

    progress.update_status(agent_id, None, "Analyzing transcript")

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "Analyze this transcript and extract all investable themes:\n\n{transcript}"),
    ])

    chain_input = prompt.invoke({"transcript": transcript})

    result = call_llm(
        prompt=chain_input,
        pydantic_model=PodcastSignalOutput,
        agent_name=agent_id,
        state=state,
    )

    themes_data = result.model_dump()

    progress.update_status(agent_id, None, f"Extracted {len(themes_data['themes'])} themes")

    message = HumanMessage(content=json.dumps(themes_data), name=agent_id)

    data["themes"] = themes_data

    progress.update_status(agent_id, None, "Done")

    return {"messages": [message], "data": data}
