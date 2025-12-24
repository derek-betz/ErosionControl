from __future__ import annotations


def format_citation(doc_id: str, page: int | None = None, excerpt: str | None = None) -> str:
    if doc_id is None:
        return "No INDOT citation available (placeholder)"
    if page:
        return f"[INDOT:{doc_id} p.{page}{f' \"{excerpt}\"' if excerpt else ''}]"
    return f"[INDOT:{doc_id}{f' \"{excerpt}\"' if excerpt else ''}]"


def ensure_indot(doc_id: str, allow_non_indot: bool = False) -> str:
    if doc_id.startswith("INDOT"):
        return doc_id
    return doc_id if allow_non_indot else "No INDOT citation available (placeholder)"
