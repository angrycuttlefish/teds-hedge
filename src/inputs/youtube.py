"""YouTube video + transcript ingestion.

Downloads full video via yt-dlp, extracts transcript via youtube-transcript-api,
extracts key frames via opencv-python for visual analysis (charts/slides),
and combines everything into an enriched transcript.
"""

import os
import re
import tempfile
from pathlib import Path

import cv2
import numpy as np

VIDEO_DIR = Path("data/videos")


def extract_video_id(url: str) -> str | None:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r"(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})",
        r"(?:embed/)([a-zA-Z0-9_-]{11})",
        r"(?:shorts/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None


def get_transcript(video_id: str) -> str | None:
    """Fetch transcript/captions for a YouTube video."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi

        ytt_api = YouTubeTranscriptApi()
        transcript_list = ytt_api.fetch(video_id)
        lines = []
        for entry in transcript_list:
            text = entry.text.strip()
            if text:
                lines.append(text)
        return " ".join(lines)
    except Exception as e:
        print(f"Warning: Could not fetch transcript for {video_id}: {e}")
        return None


def get_video_metadata(url: str) -> dict:
    """Extract video metadata (title, channel, date, duration) via yt-dlp."""
    try:
        import yt_dlp

        opts = {"quiet": True, "no_warnings": True, "skip_download": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return {
                "title": info.get("title", ""),
                "channel": info.get("channel", info.get("uploader", "")),
                "upload_date": info.get("upload_date", ""),
                "duration_seconds": info.get("duration", 0),
                "description": info.get("description", "")[:500],
            }
    except Exception as e:
        print(f"Warning: Could not fetch video metadata: {e}")
        return {}


def download_video(url: str, output_dir: Path | None = None) -> str | None:
    """Download full video via yt-dlp. Returns path to downloaded file."""
    try:
        import yt_dlp

        if output_dir is None:
            output_dir = VIDEO_DIR
        output_dir.mkdir(parents=True, exist_ok=True)

        video_id = extract_video_id(url)
        output_path = str(output_dir / f"{video_id}.%(ext)s")

        opts = {
            "format": "best[height<=720]",  # Cap at 720p for efficiency
            "outtmpl": output_path,
            "quiet": True,
            "no_warnings": True,
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            return filename
    except Exception as e:
        print(f"Warning: Could not download video: {e}")
        return None


def extract_key_frames(video_path: str, max_frames: int = 20, threshold: float = 30.0) -> list[str]:
    """Extract key frames from video using scene change detection.

    Uses histogram difference to detect significant visual changes (charts, slides, etc.).
    Returns list of paths to saved frame images.
    """
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"Warning: Could not open video: {video_path}")
        return []

    frames_dir = Path(video_path).parent / f"{Path(video_path).stem}_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    frame_paths = []
    prev_hist = None
    frame_idx = 0
    fps = cap.get(cv2.CAP_PROP_FPS) or 30
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    # Sample every 2 seconds to avoid processing every frame
    sample_interval = max(1, int(fps * 2))

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % sample_interval == 0:
            # Convert to HSV and compute histogram
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
            hist = cv2.calcHist([hsv], [0, 1], None, [50, 60], [0, 180, 0, 256])
            cv2.normalize(hist, hist)

            if prev_hist is not None:
                diff = cv2.compareHist(prev_hist, hist, cv2.HISTCMP_CHISQR)
                if diff > threshold:
                    timestamp = frame_idx / fps
                    frame_path = str(frames_dir / f"frame_{frame_idx:06d}_{timestamp:.1f}s.jpg")
                    cv2.imwrite(frame_path, frame)
                    frame_paths.append(frame_path)

                    if len(frame_paths) >= max_frames:
                        break

            prev_hist = hist

        frame_idx += 1

    cap.release()

    # Always capture first frame if we didn't get any scene changes
    if not frame_paths and total_frames > 0:
        cap = cv2.VideoCapture(video_path)
        ret, frame = cap.read()
        if ret:
            frame_path = str(frames_dir / "frame_000000_0.0s.jpg")
            cv2.imwrite(frame_path, frame)
            frame_paths.append(frame_path)
        cap.release()

    return frame_paths


def describe_frames_with_llm(frame_paths: list[str], model_name: str = "qwen-3.5-9b", model_provider: str = "LM Studio") -> list[dict]:
    """Send extracted frames to an LLM with vision for chart/graph/slide interpretation.

    Returns list of dicts with 'timestamp' and 'description' keys.
    """
    import base64

    from src.llm.models import get_model

    descriptions = []

    # Only attempt vision analysis if we have frames
    if not frame_paths:
        return descriptions

    llm = get_model(model_name, model_provider)

    for frame_path in frame_paths:
        try:
            # Extract timestamp from filename
            filename = Path(frame_path).stem
            parts = filename.split("_")
            timestamp_str = parts[-1].replace("s", "") if len(parts) >= 3 else "0"

            with open(frame_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode("utf-8")

            message = {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Describe what is shown in this frame from a financial podcast/video. Focus on any charts, graphs, data tables, slides, or visual information that would be relevant for investment analysis. If this is just a talking head with no visual data, say 'No visual data — speaker on camera.' Be concise."},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}},
                ],
            }

            result = llm.invoke([message])
            description = result.content if hasattr(result, "content") else str(result)

            descriptions.append({"timestamp": timestamp_str, "description": description})
        except Exception as e:
            print(f"Warning: Could not analyze frame {frame_path}: {e}")
            descriptions.append({"timestamp": timestamp_str, "description": f"[Frame analysis failed: {e}]"})

    return descriptions


def build_enriched_transcript(transcript_text: str | None, metadata: dict, frame_descriptions: list[dict]) -> str:
    """Combine transcript text + video metadata + visual descriptions into enriched transcript."""
    sections = []

    # Metadata header
    if metadata:
        sections.append(f"# Video: {metadata.get('title', 'Unknown')}")
        sections.append(f"**Channel:** {metadata.get('channel', 'Unknown')}")
        sections.append(f"**Date:** {metadata.get('upload_date', 'Unknown')}")
        duration = metadata.get("duration_seconds", 0)
        if duration:
            mins, secs = divmod(duration, 60)
            sections.append(f"**Duration:** {int(mins)}m {int(secs)}s")
        sections.append("")

    # Transcript
    if transcript_text:
        sections.append("## Transcript")
        sections.append(transcript_text)
        sections.append("")

    # Visual analysis
    if frame_descriptions:
        visual_data = [d for d in frame_descriptions if "No visual data" not in d.get("description", "")]
        if visual_data:
            sections.append("## Visual Analysis (Charts/Slides/Graphs)")
            for desc in visual_data:
                sections.append(f"**[{desc['timestamp']}s]** {desc['description']}")
            sections.append("")

    return "\n".join(sections)


def ingest_youtube(url: str, skip_video: bool = False, model_name: str = "qwen-3.5-9b", model_provider: str = "LM Studio") -> str:
    """Full YouTube ingestion pipeline.

    Args:
        url: YouTube video URL
        skip_video: If True, only fetch transcript (no video download/frame analysis)
        model_name: LLM model for vision analysis
        model_provider: LLM provider for vision analysis

    Returns:
        Enriched transcript string combining text + visual analysis
    """
    video_id = extract_video_id(url)
    if not video_id:
        raise ValueError(f"Could not extract video ID from URL: {url}")

    # Get metadata
    metadata = get_video_metadata(url)

    # Get transcript
    transcript_text = get_transcript(video_id)

    frame_descriptions = []
    if not skip_video:
        # Download video
        video_path = download_video(url)
        if video_path and os.path.exists(video_path):
            # Extract key frames
            frame_paths = extract_key_frames(video_path)
            if frame_paths:
                # Analyze frames with vision LLM
                frame_descriptions = describe_frames_with_llm(frame_paths, model_name, model_provider)

    if not transcript_text and not frame_descriptions:
        raise ValueError(f"Could not extract any content from YouTube video: {url}")

    return build_enriched_transcript(transcript_text, metadata, frame_descriptions)
