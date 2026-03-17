"""SEC EDGAR filing fetcher.

Fetches SEC filings (10-K, 10-Q, 8-K, etc.) from the EDGAR API.
No API key required — SEC EDGAR is free and public.
"""

import json
import time

import requests

# SEC requires a User-Agent with contact info
EDGAR_HEADERS = {
    "User-Agent": "AIHedgeFund research@example.com",
    "Accept": "application/json",
}

EDGAR_BASE = "https://efts.sec.gov/LATEST"
EDGAR_FILING_BASE = "https://www.sec.gov/Archives/edgar/data"


def get_cik(ticker: str) -> str | None:
    """Look up the CIK (Central Index Key) for a ticker symbol."""
    try:
        url = "https://www.sec.gov/files/company_tickers.json"
        resp = requests.get(url, headers=EDGAR_HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        ticker_upper = ticker.upper()
        for entry in data.values():
            if entry.get("ticker", "").upper() == ticker_upper:
                # CIK must be zero-padded to 10 digits
                return str(entry["cik_str"]).zfill(10)
        return None
    except Exception as e:
        print(f"Warning: Could not look up CIK for {ticker}: {e}")
        return None


def get_filings(ticker: str, filing_type: str = "10-K", limit: int = 5) -> list[dict]:
    """Fetch recent SEC filings for a ticker.

    Args:
        ticker: Stock ticker symbol
        filing_type: Filing type (10-K, 10-Q, 8-K, etc.)
        limit: Maximum number of filings to return

    Returns:
        List of filing metadata dicts with keys: filing_type, filing_date,
        accession_number, document_url, description
    """
    cik = get_cik(ticker)
    if not cik:
        return []

    try:
        url = f"https://data.sec.gov/submissions/CIK{cik}.json"
        resp = requests.get(url, headers=EDGAR_HEADERS, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        recent = data.get("filings", {}).get("recent", {})
        if not recent:
            return []

        forms = recent.get("form", [])
        dates = recent.get("filingDate", [])
        accessions = recent.get("accessionNumber", [])
        primary_docs = recent.get("primaryDocument", [])
        descriptions = recent.get("primaryDocDescription", [])

        filings = []
        for i in range(len(forms)):
            if forms[i] == filing_type:
                accession_clean = accessions[i].replace("-", "")
                doc_url = f"{EDGAR_FILING_BASE}/{cik.lstrip('0')}/{accession_clean}/{primary_docs[i]}"

                filings.append(
                    {
                        "ticker": ticker,
                        "cik": cik,
                        "filing_type": forms[i],
                        "filing_date": dates[i],
                        "accession_number": accessions[i],
                        "document_url": doc_url,
                        "description": descriptions[i] if i < len(descriptions) else "",
                    }
                )

                if len(filings) >= limit:
                    break

        return filings

    except Exception as e:
        print(f"Warning: Could not fetch filings for {ticker}: {e}")
        return []


def fetch_filing_text(filing: dict, max_chars: int = 100000) -> str | None:
    """Download and extract text from a filing document.

    Args:
        filing: Filing metadata dict (from get_filings)
        max_chars: Maximum characters to extract (default 100k)

    Returns:
        Extracted text content, or None on failure
    """
    url = filing.get("document_url", "")
    if not url:
        return None

    try:
        # Rate limit — SEC asks for max 10 requests/second
        time.sleep(0.2)

        resp = requests.get(url, headers=EDGAR_HEADERS, timeout=30)
        resp.raise_for_status()

        content_type = resp.headers.get("Content-Type", "")

        if "html" in content_type or url.endswith(".htm") or url.endswith(".html"):
            # Parse HTML filing
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(resp.text, "html.parser")

            # Remove script and style elements
            for element in soup(["script", "style"]):
                element.decompose()

            text = soup.get_text(separator="\n", strip=True)
            return text[:max_chars]

        elif url.endswith(".txt"):
            return resp.text[:max_chars]

        else:
            # Try as text
            return resp.text[:max_chars]

    except Exception as e:
        print(f"Warning: Could not fetch filing text from {url}: {e}")
        return None


def get_filing_summary(ticker: str, filing_type: str = "10-K") -> str:
    """Convenience function: fetch the most recent filing and return its text.

    Args:
        ticker: Stock ticker symbol
        filing_type: Type of filing (default: 10-K annual report)

    Returns:
        Formatted text with filing metadata and content
    """
    filings = get_filings(ticker, filing_type=filing_type, limit=1)
    if not filings:
        return f"No {filing_type} filings found for {ticker}"

    filing = filings[0]
    text = fetch_filing_text(filing)

    sections = []
    sections.append(f"# SEC {filing['filing_type']} — {ticker}")
    sections.append(f"**Filed:** {filing['filing_date']}")
    sections.append(f"**Accession:** {filing['accession_number']}")
    sections.append(f"**URL:** {filing['document_url']}")
    sections.append("")

    if text:
        sections.append(text)
    else:
        sections.append("[Filing text could not be extracted]")

    return "\n".join(sections)
