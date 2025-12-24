from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import yaml

MANIFEST_NAME = "manifest.yaml"


def load_manifest(manifest_path: Path) -> List[Dict]:
    return yaml.safe_load(manifest_path.read_text()) or []


def validate_resources(resources_path: Path) -> List[str]:
    """Validate that manifest and referenced documents exist."""
    errors: List[str] = []
    manifest_path = resources_path / MANIFEST_NAME
    if not manifest_path.exists():
        errors.append(f"Missing manifest at {manifest_path}")
        return errors

    manifest = load_manifest(manifest_path)
    for doc in manifest:
        filename = doc.get("filename")
        if not filename:
            errors.append(f"Doc {doc.get('doc_id')} missing filename")
            continue
        doc_path = resources_path / filename
        if not doc_path.exists():
            errors.append(f"Missing document file {doc_path}")
    return errors


def load_document_text(doc_path: Path) -> str:
    if doc_path.suffix.lower() == ".txt":
        return doc_path.read_text(errors="ignore")
    if doc_path.suffix.lower() in {".htm", ".html"}:
        return doc_path.read_text(errors="ignore")
    if doc_path.suffix.lower() == ".pdf":
        try:
            from PyPDF2 import PdfReader
        except Exception:
            return ""
        try:
            reader = PdfReader(str(doc_path))
            return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            return ""
    return doc_path.read_text(errors="ignore")
