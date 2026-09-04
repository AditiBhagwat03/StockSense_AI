"""Transparent local retrieval over policy-document chunks; no embeddings or APIs."""

from __future__ import annotations

import re
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from rag.chunker import chunk_documents
    from rag.documents import load_policy_documents
else:
    from .chunker import chunk_documents
    from .documents import load_policy_documents


TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "between", "do", "for", "how", "if", "in",
    "is", "it", "of", "on", "or", "should", "the", "to", "we", "what", "when", "with",
}


def tokenize(text: str) -> set[str]:
    """Normalize text into simple, deterministic tokens for transparent scoring."""
    tokens = set()
    for token in TOKEN_PATTERN.findall(text.lower()):
        if token in STOP_WORDS or len(token) < 3:
            continue
        if token.endswith("ies") and len(token) > 4:
            token = token[:-3] + "y"
        elif token.endswith("ing") and len(token) > 5:
            token = token[:-3]
        elif token.endswith("ed") and len(token) > 4:
            token = token[:-2]
        elif token.endswith("s") and len(token) > 4:
            token = token[:-1]
        tokens.add(token)
    return tokens


class PolicyRetriever:
    """A reusable in-memory index of the local, authoritative policy chunks."""

    def __init__(self, chunks: list[dict[str, object]] | None = None) -> None:
        self.chunks = chunks if chunks is not None else chunk_documents(load_policy_documents())
        self._document_frequency: dict[str, set[str]] = {}
        for chunk in self.chunks:
            searchable_text = f"{chunk['document_name']} {chunk['policy_id']} {chunk['text']}"
            for token in tokenize(searchable_text):
                self._document_frequency.setdefault(token, set()).add(str(chunk["document_name"]))

    def _term_weight(self, token: str) -> float:
        """Give distinctive policy terms more influence than generic shared terms."""
        return 1 / len(self._document_frequency.get(token, set()) or {"unseen"})

    def search(self, query: str, limit: int = 5, min_score: float = 0.15) -> list[dict[str, object]]:
        """Return ranked matching chunks, or an explicit empty list when no match exists."""
        query_tokens = tokenize(query)
        if not query_tokens or limit <= 0:
            return []
        query_weight = sum(self._term_weight(token) for token in query_tokens)
        query_words = TOKEN_PATTERN.findall(query.lower())
        query_phrases = {f"{left} {right}" for left, right in zip(query_words, query_words[1:])}
        results: list[dict[str, object]] = []
        for chunk in self.chunks:
            searchable_text = f"{chunk['document_name']} {chunk['policy_id']} {chunk['text']}"
            matches = query_tokens & tokenize(searchable_text)
            normalized_chunk = " ".join(TOKEN_PATTERN.findall(searchable_text.lower()))
            phrase_bonus = 0.2 * sum(phrase in normalized_chunk for phrase in query_phrases)
            score = min(1.0, sum(self._term_weight(token) for token in matches) / query_weight + phrase_bonus)
            if score >= min_score:
                results.append(
                    {
                        "text": chunk["text"],
                        "source_document": chunk["document_name"],
                        "policy_id": chunk["policy_id"],
                        "relevance_score": round(score, 4),
                        "matched_terms": sorted(matches),
                    }
                )
        return sorted(
            results,
            key=lambda result: (-result["relevance_score"], result["source_document"], result["text"]),
        )[:limit]


def retrieve_policy(query: str, limit: int = 5) -> list[dict[str, object]]:
    """Convenience function for one local policy retrieval request."""
    return PolicyRetriever().search(query, limit=limit)


def run_validation() -> bool:
    """Verify known policy coverage using the actual local policy text."""
    retriever = PolicyRetriever()
    tests = [
        ("How is stock-out risk calculated?", {"INV-001", "STO-001"}),
        ("When should inventory be considered overstocked?", {"OVS-001"}),
        ("How should a sales spike be classified?", {"ANM-001"}),
        ("What is the replenishment policy?", {"REP-001"}),
        ("When should we consider moving inventory between stores?", {"REL-001"}),
        ("What should we do if supplier lead time is longer than stock coverage?", {"STO-001", "REP-001"}),
    ]
    print("STOCKSENSE AI POLICY RETRIEVAL VALIDATION")
    print("-------------------------------------------")
    passed = True
    for query, expected_policy_ids in tests:
        result_ids = {result["policy_id"] for result in retriever.search(query)}
        matched = bool(result_ids & expected_policy_ids)
        passed = passed and matched
        print(f"{query}: {'PASS' if matched else 'FAIL'} ({', '.join(sorted(result_ids)) or 'no match'})")
    no_match = retriever.search("Completely unrelated question about weather")
    no_match_passed = not no_match
    passed = passed and no_match_passed
    print(f"Unrelated weather question: {'PASS' if no_match_passed else 'FAIL'}")
    print(f"OVERALL: {'PASS' if passed else 'FAIL'}")
    return passed


if __name__ == "__main__":
    if not run_validation():
        raise SystemExit(1)
