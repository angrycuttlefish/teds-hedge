"""Web search for deep research.

Uses DuckDuckGo search (no API key required) to find recent news,
analyst reports, and other information relevant to investment theses.
"""

import json
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup


def search_web(query: str, max_results: int = 5) -> list[dict]:
    """Search the web using DuckDuckGo HTML search (no API key needed).

    Args:
        query: Search query string
        max_results: Maximum number of results to return

    Returns:
        List of dicts with keys: title, url, snippet
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"Warning: Web search failed: {e}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    for result_div in soup.select(".result"):
        title_el = result_div.select_one(".result__title a")
        snippet_el = result_div.select_one(".result__snippet")

        if not title_el:
            continue

        title = title_el.get_text(strip=True)
        link = title_el.get("href", "")
        snippet = snippet_el.get_text(strip=True) if snippet_el else ""

        # DuckDuckGo wraps URLs in a redirect — extract the actual URL
        if "uddg=" in link:
            from urllib.parse import parse_qs, urlparse

            parsed = urlparse(link)
            params = parse_qs(parsed.query)
            link = params.get("uddg", [link])[0]

        results.append({"title": title, "url": link, "snippet": snippet})

        if len(results) >= max_results:
            break

    return results


def fetch_page_text(url: str, max_chars: int = 10000) -> str | None:
    """Fetch and extract readable text from a web page.

    Args:
        url: URL to fetch
        max_chars: Maximum characters to return

    Returns:
        Extracted text or None on failure
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    # Remove non-content elements
    for el in soup(["script", "style", "nav", "footer", "header", "aside"]):
        el.decompose()

    text = soup.get_text(separator="\n", strip=True)
    return text[:max_chars] if text else None


def research_ticker(ticker: str, thesis: str = "", max_results: int = 5) -> str:
    """Search for recent information about a ticker relevant to a thesis.

    Args:
        ticker: Stock ticker symbol
        thesis: Investment thesis to focus the search
        max_results: Maximum search results to return

    Returns:
        Formatted research text with search results and snippets
    """
    # Build focused search queries
    queries = [f"{ticker} stock analysis {thesis[:50]}" if thesis else f"{ticker} stock analysis recent news"]

    all_results = []
    seen_urls = set()

    for query in queries:
        results = search_web(query, max_results=max_results)
        for r in results:
            if r["url"] not in seen_urls:
                all_results.append(r)
                seen_urls.add(r["url"])

    if not all_results:
        return f"No web search results found for {ticker}"

    sections = []
    sections.append(f"# Web Research: {ticker}")
    if thesis:
        sections.append(f"**Thesis:** {thesis[:100]}")
    sections.append("")

    for i, result in enumerate(all_results[:max_results], 1):
        sections.append(f"### {i}. {result['title']}")
        sections.append(f"**Source:** {result['url']}")
        if result["snippet"]:
            sections.append(f"{result['snippet']}")
        sections.append("")

    return "\n".join(sections)


def research_thesis(thesis: str, tickers: list[str] | None = None, max_results: int = 5) -> str:
    """Search for information relevant to an investment thesis.

    Args:
        thesis: The investment thesis to research
        tickers: Optional list of related ticker symbols
        max_results: Maximum search results

    Returns:
        Formatted research text
    """
    # Search for the thesis itself
    results = search_web(thesis[:100], max_results=max_results)

    sections = []
    sections.append(f"# Thesis Research")
    sections.append(f"**Thesis:** {thesis}")
    sections.append("")

    if results:
        sections.append("## Search Results")
        for i, r in enumerate(results, 1):
            sections.append(f"### {i}. {r['title']}")
            sections.append(f"**Source:** {r['url']}")
            if r["snippet"]:
                sections.append(f"{r['snippet']}")
            sections.append("")

    # Also search for each ticker if provided
    if tickers:
        for ticker in tickers[:3]:
            ticker_results = search_web(f"{ticker} {thesis[:50]}", max_results=3)
            if ticker_results:
                sections.append(f"## {ticker} — Related Coverage")
                for r in ticker_results:
                    sections.append(f"- **{r['title']}**: {r['snippet']}")
                sections.append("")

    return "\n".join(sections)
