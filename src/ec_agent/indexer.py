from __future__ import annotations

import pickle
from pathlib import Path
from typing import Dict, List

from sklearn.feature_extraction.text import TfidfVectorizer

from .loader import load_manifest, load_document_text, MANIFEST_NAME


def chunk_text(text: str, size: int = 400) -> List[str]:
    words = text.split()
    chunks = []
    for i in range(0, len(words), size):
        chunk = " ".join(words[i : i + size])
        if chunk.strip():
            chunks.append(chunk)
    return chunks or [text]


def build_index(resources_path: Path, index_path: Path) -> Dict:
    manifest_path = resources_path / MANIFEST_NAME
    manifest = load_manifest(manifest_path)
    documents: List[Dict] = []

    for doc in manifest:
        doc_id = doc["doc_id"]
        filename = doc["filename"]
        doc_text = load_document_text(resources_path / filename)
        for page_no, chunk in enumerate(chunk_text(doc_text), start=1):
            documents.append({"doc_id": doc_id, "page": page_no, "text": chunk})

    corpus = [d["text"] for d in documents]
    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform(corpus)

    index_data = {"vectorizer": vectorizer, "matrix": matrix, "documents": documents}
    index_path.parent.mkdir(parents=True, exist_ok=True)
    with open(index_path, "wb") as f:
        pickle.dump(index_data, f)
    return index_data
