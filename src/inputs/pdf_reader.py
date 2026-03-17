"""PDF text extraction.

Extracts text from PDF files using pdfplumber, handling multi-page
research reports with table support.
"""

from pathlib import Path

import pdfplumber


def extract_pdf(file_path: str) -> str:
    """Extract text from a PDF file.

    Handles multi-page documents and preserves table structure where possible.

    Args:
        file_path: Path to the PDF file

    Returns:
        Extracted text with page markers

    Raises:
        FileNotFoundError: If the PDF file doesn't exist
        ValueError: If the PDF cannot be read or is empty
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF file not found: {file_path}")
    if not path.suffix.lower() == ".pdf":
        raise ValueError(f"Not a PDF file: {file_path}")

    sections = []
    sections.append(f"# PDF: {path.name}")
    sections.append("")

    try:
        with pdfplumber.open(file_path) as pdf:
            if not pdf.pages:
                raise ValueError(f"PDF has no pages: {file_path}")

            sections.append(f"**Pages:** {len(pdf.pages)}")
            sections.append("")

            for i, page in enumerate(pdf.pages, 1):
                page_text = page.extract_text()

                # Try to extract tables
                tables = page.extract_tables()

                if page_text or tables:
                    sections.append(f"## Page {i}")

                    if page_text:
                        sections.append(page_text)

                    if tables:
                        for t_idx, table in enumerate(tables):
                            if not table:
                                continue
                            sections.append(f"\n**Table {t_idx + 1}:**")
                            for row in table:
                                # Clean None values and join cells
                                cleaned = [str(cell).strip() if cell else "" for cell in row]
                                sections.append(" | ".join(cleaned))

                    sections.append("")

    except Exception as e:
        raise ValueError(f"Error reading PDF: {e}") from e

    text = "\n".join(sections)
    if len(text.strip()) < 50:
        raise ValueError(f"PDF appears to contain no extractable text (may be scanned/image-only): {file_path}")

    return text
