from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import numpy as np


@dataclass
class Citation:
    doc_id: str
    page: int | None
    excerpt: str
    score: float

    def label(self) -> str:
        if self.page:
            return f"[INDOT:{self.doc_id} p.{self.page} \"{self.excerpt[:80].strip()}\"]"
        return f"[INDOT:{self.doc_id} \"{self.excerpt[:80].strip()}\"]"


def load_index(index_path: Path) -> Dict[str, Any]:
    with open(index_path, "rb") as f:
        return pickle.load(f)


def retrieve(query: str, index: Dict[str, Any], top_k: int = 3) -> List[Citation]:
    vectorizer = index["vectorizer"]
    matrix = index["matrix"]
    documents = index["documents"]

    query_vec = vectorizer.transform([query])
    scores = (matrix @ query_vec.T).toarray().ravel()
    top_indices = np.argsort(scores)[::-1][:top_k]
    citations: List[Citation] = []
    for idx in top_indices:
        if scores[idx] <= 0:
            continue
        doc = documents[idx]
        citations.append(
            Citation(
                doc_id=doc["doc_id"],
                page=doc.get("page"),
                excerpt=doc["text"][:200],
                score=float(scores[idx]),
            )
        )
    return citations
