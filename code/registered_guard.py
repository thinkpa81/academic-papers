"""Validate evidence against reference records supplied by a trusted caller.

The registry must be supplied separately from the submitted evidence. This module
checks consistency; authentication and deployment controls remain external.
"""

from __future__ import annotations

import math
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
SNAP = ROOT / "support/model_swap_addendum/guard_snapshot"
sys.path.insert(0, str(SNAP))
from workflow_guard import load_original
from workflow_guard_v2 import validate as previous_validate

SCHEMA_ERRORS = (KeyError, TypeError, ValueError, OverflowError, AttributeError)
Check = Callable[[str, bool], None]


def close(actual: Any, expected: Any) -> bool:
    """Compare finite numeric values with the protocol's absolute tolerance."""
    if actual is None or expected is None:
        return actual is expected
    numeric = all(
        isinstance(value, (int, float)) and not isinstance(value, bool)
        for value in (actual, expected)
    )
    if numeric:
        try:
            return (
                math.isfinite(actual)
                and math.isfinite(expected)
                and math.isclose(actual, expected, rel_tol=0, abs_tol=1e-9)
            )
        except (TypeError, OverflowError, ValueError):
            return False
    return type(actual) is type(expected) and actual == expected


def coefficients_match(artifact: dict, expected: dict) -> bool:
    parameters = {
        item["feature"]: item["coefficient"] for item in artifact["parameters"]
    }
    return (
        len(parameters) == len(artifact["parameters"])
        and set(parameters) == set(expected["parameters"])
        and all(
            close(parameters[key], value)
            for key, value in expected["parameters"].items()
        )
        and close(artifact["intercept"], expected["intercept"])
    )


def explanation_matches(explanation: dict, known: dict, model: dict) -> bool:
    terms = {item["feature"]: item for item in explanation["contributions"]}
    return (
        len(terms) == len(explanation["contributions"])
        and set(terms) == set(known["terms"])
        and close(explanation["intercept_logpoints"], model["intercept"])
        and all(
            all(
                key in terms[feature] and close(terms[feature][key], value)
                for key, value in term.items()
            )
            for feature, term in known["terms"].items()
        )
    )


def check_registered_card(card: dict, registry: dict, check: Check) -> None:
    """Append stable error codes in protocol order; reject duplicate features."""
    if (
        not isinstance(registry, dict)
        or not isinstance(registry["records"], dict)
        or not isinstance(registry["models"], dict)
    ):
        raise TypeError("Registry, records and models must be JSON objects")
    model_name = card["learned_comparator"]["model"]
    key = f"{card['region_code']}:{card['industry_code']}:{card['target_year']}:{model_name}"
    known = registry["records"].get(key)
    check("unregistered_model_input", known is not None)
    if known is None:
        return
    check(
        "registered_prediction_mismatch",
        close(card["learned_comparator"]["logpoints"], known["prediction"]),
    )
    check(
        "registered_baseline_mismatch",
        close(card["default_estimate"]["logpoints"], known["baseline"]),
    )
    check(
        "registered_employment_mismatch",
        close(card["employment_input_persons"], known["employment"]),
    )
    artifact = card["model_artifact_snapshot"]
    model = registry["models"][model_name]
    identities = [
        artifact["model"],
        card["linear_explanation"]["model"],
        card["prior_validation"]["model"],
        card["validation_display"]["model"],
    ]
    check(
        "model_identity_mismatch",
        all(identity == model_name for identity in identities),
    )
    check(
        "artifact_digest_mismatch",
        artifact["artifact_sha256"] == model["artifact_sha256"],
    )
    check("registered_coefficients_mismatch", coefficients_match(artifact, model))
    check(
        "registered_explanation_mismatch",
        explanation_matches(card["linear_explanation"], known, model),
    )
    prior = card["prior_validation"]
    check(
        "registered_validation_mismatch",
        all(
            key in prior and close(prior[key], value)
            for key, value in known["validation"].items()
        ),
    )


def validate(envelope: Any, registry: Any, modules=None) -> dict:
    """Return a structured block for malformed evidence or registry records."""
    modules = modules or load_original(SNAP / "source_snapshot")
    try:
        result = previous_validate(envelope, modules)
    except (*SCHEMA_ERRORS, RecursionError) as exc:
        result = {
            "research_review_permitted": False,
            "errors": [
                {
                    "module": "I",
                    "code": "unsupported_input_structure",
                    "exception_type": type(exc).__name__,
                }
            ],
            "automatic_policy_action_allowed": False,
            "operational_prediction_permitted": False,
            "institutional_approval_granted": False,
            "human_evaluation_conducted": False,
        }
    errors = result["errors"]

    def check(code: str, ok: bool) -> None:
        if not ok:
            errors.append({"module": "R", "code": code})

    try:
        check_registered_card(envelope["card"], registry, check)
    except SCHEMA_ERRORS:
        check("registry_contract_schema_invalid", False)
    result.update(
        version="registered-workflow-3.0.0",
        status="research_review_blocked" if errors else "research_review_permitted",
        research_review_permitted=not bool(errors),
        trusted_registry_id=registry.get("registry_id")
        if isinstance(registry, dict)
        else None,
    )
    return result
