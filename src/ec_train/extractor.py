"""Content extraction helpers for EC training documents."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import pdfplumber
from docx import Document

PAY_ITEM_REGEX = re.compile(r"\b205[-\s]?12616\b", re.IGNORECASE)
KEYWORDS = [
    "erosion",
    "control",
    "drain",
    "soil",
    "silt",
    "sediment",
    "temporary",
    "permanent",
    "vegetation",
    "mulch",
    "blanket",
]


@dataclass(slots=True)
class ExtractedContent:
    """Lightweight representation of extracted findings."""

    path: Path
    findings: list[str]
    spec_refs: list[str]
    pages: list[int]


def extract_text_from_pdf(path: Path) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def extract_text_from_docx(path: Path) -> str:
    doc = Document(path)
    return "\n".join(paragraph.text for paragraph in doc.paragraphs)


def extract_content(path: Path) -> ExtractedContent:
    """Extract relevant snippets and references from a document."""
    if path.suffix.lower() == ".pdf":
        text = extract_text_from_pdf(path)
    elif path.suffix.lower() in {".doc", ".docx"}:
        text = extract_text_from_docx(path)
    else:
        text = path.read_text(encoding="utf-8", errors="ignore")

    lines = text.splitlines()
    findings: list[str] = []
    spec_refs: list[str] = []
    pages: list[int] = []
    for idx, line in enumerate(lines, start=1):
        lower = line.lower()
        if any(keyword in lower for keyword in KEYWORDS) or PAY_ITEM_REGEX.search(lower):
            findings.append(line.strip())
            if "205" in lower or "section" in lower:
                spec_refs.append(line.strip())
            pages.append(idx)
    return ExtractedContent(path=path, findings=findings[:20], spec_refs=list(dict.fromkeys(spec_refs)), pages=pages[:20])


__all__ = ["ExtractedContent", "extract_content", "KEYWORDS", "PAY_ITEM_REGEX"]
