"""Substack article fetcher.

Fetches and parses Substack articles from URLs, extracting article text,
author, date, and metadata.
"""

import re
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


def is_substack_url(url: str) -> bool:
    """Check if a URL is a Substack article."""
    parsed = urlparse(url)
    # substack.com subdomain or custom domain with /p/ path
    if "substack.com" in parsed.hostname:
        return True
    # Many substacks use /p/ for posts
    if "/p/" in parsed.path:
        return True
    return False


def fetch_substack(url: str) -> str:
    """Fetch and parse a Substack article from URL.

    Args:
        url: Substack article URL

    Returns:
        Formatted article text with metadata

    Raises:
        ValueError: If the article cannot be fetched or parsed
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        if response.status_code == 403:
            raise ValueError(f"Access denied — this Substack post may be paywalled: {url}") from e
        raise ValueError(f"Could not fetch Substack article (HTTP {response.status_code}): {url}") from e
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Network error fetching Substack article: {e}") from e

    soup = BeautifulSoup(response.text, "html.parser")

    # Extract title
    title = ""
    title_el = soup.find("h1", class_="post-title") or soup.find("h1")
    if title_el:
        title = title_el.get_text(strip=True)

    # Extract subtitle
    subtitle = ""
    subtitle_el = soup.find("h3", class_="subtitle") or soup.find("h2", class_="subtitle")
    if subtitle_el:
        subtitle = subtitle_el.get_text(strip=True)

    # Extract author
    author = ""
    author_el = soup.find("a", class_="frontend-pencraft-Text-module__decoration-hover-underline--BEYAn")
    if not author_el:
        # Try meta tag
        meta_author = soup.find("meta", attrs={"name": "author"})
        if meta_author:
            author = meta_author.get("content", "")
    else:
        author = author_el.get_text(strip=True)

    # Extract date
    date = ""
    time_el = soup.find("time")
    if time_el:
        date = time_el.get("datetime", time_el.get_text(strip=True))

    # Extract article body
    body_el = soup.find("div", class_="body") or soup.find("div", class_="post-content") or soup.find("article")
    if not body_el:
        # Fallback: find the main content area
        body_el = soup.find("div", class_="available-content")

    if not body_el:
        raise ValueError(f"Could not find article content in page: {url}")

    # Extract text preserving paragraph structure
    paragraphs = []
    for el in body_el.find_all(["p", "h1", "h2", "h3", "h4", "li", "blockquote"]):
        text = el.get_text(strip=True)
        if text:
            tag = el.name
            if tag.startswith("h"):
                level = int(tag[1])
                paragraphs.append(f"{'#' * level} {text}")
            elif tag == "li":
                paragraphs.append(f"- {text}")
            elif tag == "blockquote":
                paragraphs.append(f"> {text}")
            else:
                paragraphs.append(text)

    if not paragraphs:
        raise ValueError(f"Article appears empty or paywalled: {url}")

    # Build formatted output
    sections = []
    sections.append(f"# {title}" if title else "# Substack Article")
    if subtitle:
        sections.append(f"*{subtitle}*")
    if author:
        sections.append(f"**Author:** {author}")
    if date:
        sections.append(f"**Date:** {date}")
    sections.append(f"**Source:** {url}")
    sections.append("")
    sections.append("\n\n".join(paragraphs))

    return "\n".join(sections)
