"""Discovery and loading helpers for the committed policy documents."""

from __future__ import annotations

import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
POLICY_DIRECTORY = PROJECT_ROOT / "data" / "policies"
POLICY_ID_PATTERN = re.compile(r"^POLICY ID:\s*(.+?)\s*$", re.MULTILINE)


def discover_policy_files(policy_directory: Path = POLICY_DIRECTORY) -> list[Path]:
    """Return policy text files in a stable order, or an empty list if absent."""
    if not policy_directory.is_dir():
        return []
    return sorted(policy_directory.glob("*.txt"), key=lambda path: path.name)


def load_policy_documents(policy_directory: Path = POLICY_DIRECTORY) -> list[dict[str, str]]:
    """Load existing policy documents with source metadata; skip unreadable files."""
    documents: list[dict[str, str]] = []
    for path in discover_policy_files(policy_directory):
        try:
            text = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if not text:
            continue
        match = POLICY_ID_PATTERN.search(text)
        documents.append(
            {
                "document_name": path.name,
                "policy_id": match.group(1) if match else "UNKNOWN",
                "text": text,
            }
        )
    return documents
