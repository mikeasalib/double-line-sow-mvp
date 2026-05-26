"""
SOW ingestion layer.
Handles plain text and PDF input, returns normalized text.
"""
import os
from pathlib import Path


def ingest(source: str) -> str:
    """
    Read a SOW from a file path (text or PDF) or raw string.
    Returns cleaned text content.
    """
    path = Path(source)

    if path.exists():
        if path.suffix.lower() == ".pdf":
            return _read_pdf(path)
        else:
            return _read_text(path)

    # Treat as raw text input
    if len(source) > 200:
        return source.strip()

    raise FileNotFoundError(f"Could not find file or interpret input: {source[:100]}")


def _read_text(path: Path) -> str:
    """Read plain text file."""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return content.strip()


def _read_pdf(path: Path) -> str:
    """Extract text from PDF using pdfplumber."""
    try:
        import pdfplumber
    except ImportError:
        raise ImportError("pdfplumber is required for PDF input. Run: pip install pdfplumber")

    pages = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                pages.append(text)

    if not pages:
        raise ValueError(f"No extractable text found in PDF: {path}")

    return "\n\n".join(pages)
