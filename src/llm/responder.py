"""Grounded structured response handling over supplied facts and policy evidence."""

from __future__ import annotations

import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from llm.client import GeminiClient, GeminiClientError
    from llm.prompts import build_grounded_prompt
else:
    from .client import GeminiClient, GeminiClientError
    from .prompts import build_grounded_prompt


REQUIRED_FIELDS = {"answer", "key_facts", "recommendation", "evidence", "limitations"}


def _error_response(message: str) -> dict[str, object]:
    """Return the required structure without pretending that generation succeeded."""
    return {
        "answer": "No grounded Gemini response was generated.",
        "key_facts": [],
        "recommendation": "No recommendation is available because structured generation failed.",
        "evidence": [],
        "limitations": [message],
        "status": "error",
    }


def _strip_json_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        return "\n".join(stripped.splitlines()[1:-1]).strip()
    return stripped


def _allowed_policy_ids(policy_evidence: object) -> set[str]:
    if not isinstance(policy_evidence, list):
        return set()
    return {
        str(item.get("policy_id"))
        for item in policy_evidence
        if isinstance(item, dict) and item.get("policy_id")
    }


def parse_structured_response(raw_text: str, policy_evidence: object) -> dict[str, object]:
    """Safely parse Gemini JSON and reject malformed or unsupported evidence references."""
    try:
        response = json.loads(_strip_json_fence(raw_text))
    except (TypeError, json.JSONDecodeError):
        return _error_response("Structured generation failed: Gemini did not return valid JSON.")
    if not isinstance(response, dict) or not REQUIRED_FIELDS <= response.keys():
        return _error_response("Structured generation failed: required response fields are missing.")
    if not isinstance(response["answer"], str) or not isinstance(response["recommendation"], str):
        return _error_response("Structured generation failed: response text fields have invalid types.")
    if not all(isinstance(response[field], list) for field in ("key_facts", "evidence", "limitations")):
        return _error_response("Structured generation failed: response list fields have invalid types.")

    allowed_policy_ids = _allowed_policy_ids(policy_evidence)
    validated_evidence = []
    for item in response["evidence"]:
        if not isinstance(item, dict) or not {"policy_id", "source", "reason"} <= item.keys():
            continue
        if str(item["policy_id"]) in allowed_policy_ids:
            validated_evidence.append(
                {"policy_id": str(item["policy_id"]), "source": str(item["source"]), "reason": str(item["reason"])}
            )
    response["evidence"] = validated_evidence
    response["status"] = "ok"
    return response


def respond_to_question(
    user_question: str,
    verified_facts: object,
    policy_evidence: object,
    client: GeminiClient | None = None,
) -> dict[str, object]:
    """Send supplied facts/evidence to Gemini without reading the database or calculating metrics."""
    if not isinstance(user_question, str) or not user_question.strip():
        return _error_response("A non-empty user question is required.")
    prompt = build_grounded_prompt(user_question.strip(), verified_facts, policy_evidence)
    try:
        raw_text = (client or GeminiClient()).generate_json(prompt)
    except GeminiClientError as error:
        return _error_response(str(error))
    return parse_structured_response(raw_text, policy_evidence)


def run_grounding_tests() -> bool:
    """Call Gemini with verified existing analytics and retrieved local policy evidence."""
    from src.database.connection import get_connection
    from src.analytics.sales_anomalies import analyze_sales_anomaly
    from src.analytics.stockout import analyze_stockout
    from src.rag.retriever import retrieve_policy

    scenarios = [
        ("Stock-out", "Should we take action on the Wireless Mouse at Central Store?", "stockout", "S001", "P001"),
        ("Sales spike", "How should we interpret the Smart Watch sales increase?", "anomaly", None, "P005"),
        ("Sales drop", "What happened with Wireless Earbuds sales?", "anomaly", None, "P006"),
        ("Insufficient data", "Is P015 at risk of stocking out?", "stockout", "S001", "P015"),
        ("Unrelated evidence", "What will the weather be tomorrow?", "none", None, None),
    ]
    print("STOCKSENSE AI GEMINI GROUNDING TESTS")
    print("--------------------------------------")
    passed = True
    with get_connection() as connection:
        for name, question, kind, store_id, product_id in scenarios:
            if kind == "stockout":
                facts = analyze_stockout(connection, store_id, product_id)
                evidence = retrieve_policy(question)
            elif kind == "anomaly":
                facts = analyze_sales_anomaly(connection, product_id)
                evidence = retrieve_policy(question)
            else:
                facts, evidence = {}, []
            response = respond_to_question(question, facts, evidence)
            scenario_passed = response.get("status") == "ok" and REQUIRED_FIELDS <= response.keys()
            if scenario_passed:
                supplied_ids = _allowed_policy_ids(evidence)
                scenario_passed = all(item["policy_id"] in supplied_ids for item in response["evidence"])
            passed = passed and scenario_passed
            print(f"{name}: {'PASS' if scenario_passed else 'FAIL'}")
            if not scenario_passed:
                print(f"  {response['limitations'][0]}")
    print(f"OVERALL: {'PASS' if passed else 'FAIL'}")
    return passed


if __name__ == "__main__":
    if not run_grounding_tests():
        raise SystemExit(1)
