"""Deterministic paragraph chunking for local policy documents."""

from __future__ import annotations

import re


PARAGRAPH_BREAK = re.compile(r"\n\s*\n")


def chunk_document(document: dict[str, str], max_characters: int = 420) -> list[dict[str, object]]:
    """Split one policy into ordered, readable chunks while retaining its metadata."""
    paragraphs = [paragraph.strip() for paragraph in PARAGRAPH_BREAK.split(document["text"]) if paragraph.strip()]
    chunks: list[dict[str, object]] = []
    current: list[str] = []
    current_length = 0
    for paragraph in paragraphs:
        separator = 2 if current else 0
        if current and current_length + separator + len(paragraph) > max_characters:
            chunks.append(_make_chunk(document, len(chunks), "\n\n".join(current)))
            current, current_length = [], 0
        current.append(paragraph)
        current_length += separator + len(paragraph)
    if current:
        chunks.append(_make_chunk(document, len(chunks), "\n\n".join(current)))
    return chunks


def _make_chunk(document: dict[str, str], index: int, text: str) -> dict[str, object]:
    return {
        "chunk_id": f"{document['document_name']}:{index}",
        "chunk_index": index,
        "document_name": document["document_name"],
        "policy_id": document["policy_id"],
        "text": text,
    }


def chunk_documents(documents: list[dict[str, str]], max_characters: int = 420) -> list[dict[str, object]]:
    """Chunk a document collection in stable document order."""
    chunks: list[dict[str, object]] = []
    for document in documents:
        chunks.extend(chunk_document(document, max_characters=max_characters))
    return chunks
