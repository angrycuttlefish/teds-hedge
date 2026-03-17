# AI Research Skill Architecture: From Podcast Signal to Equity Ideas

## Overview

A 5-stage agentic pipeline that transforms unstructured podcast/video content into actionable equity investment ideas. Each stage transforms information into progressively more decision-grade insight.

## Pipeline Stages

### Stage 1: Podcast Signal Extractor
- **Input:** Enriched transcript (text + visual frame descriptions from video)
- **Output:** Structured themes with supporting quotes and visual evidence
- **Purpose:** Separates signal from noise in long-form podcasts and videos
- **Key capabilities:**
  - Identify investable themes, macro signals, sector calls
  - Extract direct quotes with context
  - **Interpret charts, graphs, and slides** shown on screen during the video (via Claude Vision on extracted frames)
  - Tag themes by category (macro, sector, company-specific, contrarian)
  - Rate signal strength (conviction level of the speaker)
  - Cross-reference spoken claims with visual data shown on screen

### Stage 2: Hedge-Fund Analyst
- **Input:** Podcast themes (from Stage 1)
- **Output:** Institutional-grade analysis per theme
- **Purpose:** Transforms themes into institutional analysis
- **Key capabilities:**
  - TAM / market size estimation
  - Supply chain mapping
  - Competitive landscape analysis
  - Identify key risks and catalysts
  - Frame each theme as a testable investment thesis

### Stage 3: Deep Research Synthesizer
- **Input:** Analyst thesis (from Stage 2)
- **Output:** High-leverage research questions / prompts
- **Purpose:** Designs high-leverage research prompts
- **Key capabilities:**
  - Generate targeted research questions per thesis
  - Identify what evidence would confirm or refute each thesis
  - Prioritize questions by information value
  - Map questions to data sources (SEC filings, earnings calls, industry reports)

### Stage 4: Research Consolidator
- **Input:** Research reports / evidence streams (from Stage 3 execution)
- **Output:** Action-ready insights with confidence scores
- **Purpose:** Weighs evidence and resolves contradictions
- **Key capabilities:**
  - Synthesize multiple evidence streams
  - Identify and resolve contradictions
  - Assign confidence probability to each thesis
  - Highlight key uncertainties and what would change the view

### Stage 5: Equity Screener
- **Input:** Synthesized research (from Stage 4)
- **Output:** Ranked equity ideas by order of impact
- **Purpose:** Identifies first-, second-, and third-order winners
- **Key capabilities:**
  - Map themes to specific equities by sector
  - Identify 1st order (direct beneficiaries), 2nd order (supply chain), 3rd order (derivative plays)
  - Rank by conviction, upside potential, and catalyst timeline
  - Cross-reference with existing portfolio positions

## IP / Competitive Advantage

> "Your IP lives in how each step transforms information into decision-grade insight."

The value is in the transformation logic at each stage — the prompts, the analytical frameworks, and the way evidence is weighted and synthesized.
