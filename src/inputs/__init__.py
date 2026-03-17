"""Unified input handler — auto-detects input type and routes to the appropriate fetcher.

Supports:
- YouTube URLs → full video download + transcript + frame analysis
- Substack URLs → article text extraction
- PDF files → text + table extraction
- Text files → direct read
- Raw text → pass-through
"""

import os
from pathlib import Path
from urllib.parse import urlparse

from src.inputs.pdf_reader import extract_pdf
from src.inputs.substack import fetch_substack, is_substack_url
from src.inputs.youtube import extract_video_id, ingest_youtube


class InputType:
    YOUTUBE = "youtube"
    SUBSTACK = "substack"
    PDF = "pdf"
    TEXT_FILE = "text_file"
    RAW_TEXT = "raw_text"


def detect_input_type(source: str) -> str:
    """Auto-detect the input type from a source string.

    Args:
        source: URL, file path, or raw text

    Returns:
        One of InputType constants
    """
    # Check if it looks like a URL
    if source.startswith(("http://", "https://", "www.")):
        # YouTube
        if extract_video_id(source):
            return InputType.YOUTUBE

        # Substack
        if is_substack_url(source):
            return InputType.SUBSTACK

        # Unknown URL — treat as generic text (could be fetched later)
        return InputType.RAW_TEXT

    # Check if it's a file path
    path = Path(source)
    if path.exists() and path.is_file():
        if path.suffix.lower() == ".pdf":
            return InputType.PDF
        return InputType.TEXT_FILE

    # Fallback: raw text
    return InputType.RAW_TEXT


def ingest(source: str, skip_video: bool = False, model_name: str = "qwen-3.5-9b", model_provider: str = "LM Studio") -> tuple[str, str]:
    """Ingest content from any supported source.

    Args:
        source: YouTube URL, Substack URL, file path, or raw text
        skip_video: For YouTube — skip video download, transcript only
        model_name: LLM model for vision analysis (YouTube frames)
        model_provider: LLM provider for vision analysis

    Returns:
        Tuple of (enriched_text, input_type)

    Raises:
        ValueError: If the source cannot be processed
    """
    input_type = detect_input_type(source)

    if input_type == InputType.YOUTUBE:
        text = ingest_youtube(source, skip_video=skip_video, model_name=model_name, model_provider=model_provider)
        return text, input_type

    if input_type == InputType.SUBSTACK:
        text = fetch_substack(source)
        return text, input_type

    if input_type == InputType.PDF:
        text = extract_pdf(source)
        return text, input_type

    if input_type == InputType.TEXT_FILE:
        with open(source, "r") as f:
            text = f.read()
        if not text.strip():
            raise ValueError(f"Text file is empty: {source}")
        return text, input_type

    # Raw text
    if not source.strip():
        raise ValueError("Empty input provided")
    return source, InputType.RAW_TEXT
