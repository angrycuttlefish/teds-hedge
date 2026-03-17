"""Stage 1: Podcast Signal Extractor — Separates signal from noise in long-form podcasts."""

import json

from langchain_core.messages import HumanMessage
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field

from src.graph.research_state import ResearchState
from src.utils.llm import call_llm
from src.utils.progress import progress


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

## Your Role
You are Stage 1 of a 5-stage research pipeline. Your output feeds directly into a Hedge Fund Analyst (Stage 2) who will build institutional-grade theses from your themes. The quality of your extraction determines the quality of every downstream stage.

## Available Context
You will receive a transcript that may include:
- **Text transcript** — Spoken words from the podcast/video
- **Visual analysis** — Descriptions of charts, graphs, and slides shown on screen (if video was processed)
- **Video metadata** — Title, channel, date, duration (if available)

Pay special attention to visual analysis sections — charts and data shown on screen often contain the most actionable signals that speakers reference but don't fully verbalize.

## Your Tasks

1. **Identify investable themes** — Look for macro trends, sector calls, company-specific insights, and contrarian views that could drive investment decisions. Extract at least 3-5 themes from any substantive transcript.

2. **Extract supporting quotes** — Pull direct quotes that substantiate each theme. These should be the strongest evidence for the thesis. Include references to visual data if relevant (e.g., "Chart showed 40% YoY growth in data center revenue").

3. **Categorize each theme:**
   - `macro` — Broad economic or market-level signals (interest rates, inflation, geopolitics)
   - `sector` — Industry or sector-level calls (AI infrastructure, energy transition, biotech)
   - `company-specific` — Direct mentions of individual companies or their prospects
   - `contrarian` — Views that go against consensus or conventional wisdom

4. **Rate signal strength** based on the speaker's conviction:
   - `high` — Speaker is emphatic, uses definitive language, backs with data or visual evidence
   - `medium` — Speaker is thoughtful but hedged, mentions risks
   - `low` — Passing mention, speculative, or tangential

5. **Provide context** — Why does this theme matter? What's the investment implication? Connect to current market conditions where possible.

## Quality Standards
- Every theme must have at least 1 supporting quote
- Themes must be specific enough to generate an investment thesis (not generic like "markets are volatile")
- Signal strength must be honest — don't inflate weak signals
- If the transcript mentions specific tickers, companies, or data points, capture them precisely

Focus on actionable intelligence. Ignore filler, self-promotion, and off-topic tangents.

You MUST respond with a JSON object matching the required schema."""


def podcast_signal_extractor_agent(state: ResearchState, agent_id: str = "podcast_signal_extractor"):
    """Extracts investable themes and signals from a podcast/video transcript."""
    data = state["data"]
    transcript = data.get("transcript", "")

    progress.update_status(agent_id, None, "Analyzing transcript")

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", "Analyze this transcript and extract all investable themes:\n\n{transcript}"),
        ]
    )

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
