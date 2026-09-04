"""Grounding instructions and prompt construction for the Gemini explanation layer."""

from __future__ import annotations

import json


SYSTEM_INSTRUCTIONS = """You are the explanation layer for a retail intelligence system.

TRUST RULES:
1. VERIFIED ANALYTICS are authoritative.
2. POLICY EVIDENCE is authoritative for policy guidance.
3. Never recalculate or contradict verified analytics.
4. Never invent facts that are not provided.
5. Never invent causes for sales spikes or sales drops.
6. Never claim inventory was moved unless the input explicitly says it was moved.
7. Never claim a purchase order was placed.
8. Never guarantee delivery or sellout dates.
9. If evidence is insufficient, explicitly say that it is insufficient.
10. Distinguish measured facts from recommendations.

Return only valid JSON with exactly these fields:
{
  "answer": "string",
  "key_facts": ["string"],
  "recommendation": "string",
  "evidence": [{"policy_id": "string", "source": "string", "reason": "string"}],
  "limitations": ["string"]
}

Use only the supplied verified facts and policy evidence. If no supplied evidence addresses the
question, say so plainly in answer and limitations; do not use outside knowledge."""


def build_grounded_prompt(
    user_question: str, verified_facts: object, policy_evidence: object
) -> str:
    """Build the complete evidence-only prompt sent to Gemini."""
    return "\n\n".join(
        (
            SYSTEM_INSTRUCTIONS,
            f"USER QUESTION:\n{user_question}",
            "VERIFIED FACTS:\n" + json.dumps(verified_facts, ensure_ascii=False, indent=2, default=str),
            "POLICY EVIDENCE:\n" + json.dumps(policy_evidence, ensure_ascii=False, indent=2, default=str),
        )
    )
