"""Generate prespecified controls and faults; labels never enter validators."""

from __future__ import annotations

import copy
import json

from evidence_contract import bind, digest, record_key

FAMILIES = {
    "C0_original": (True, "Observed forecast with a synthetic consistent review"),
    "C1_reordered": (True, "JSON key order changes without semantic change"),
    "C2_renewed_review": (True, "Review and caller-held current version both advance"),
    "F01_numeric_type": (False, "Prediction replaced by a numeric string"),
    "F02_horizon": (False, "Input period moved by one month"),
    "F03_arithmetic": (False, "Displayed forecast difference increased by one log point"),
    "F04_decomposition": (False, "One contribution increased without changing the forecast"),
    "F05_request_binding": (False, "Request changed while the stored review remains unchanged"),
    "F06_unverified_operation": (False, "Current snapshot represented as historically verified operation"),
    "F07_measurement_unit": (False, "Log change relabeled as percentage change"),
    "F08_stale_review": (False, "Caller-held current review version advances without renewed review"),
    "F09_coherent_forecast": (False, "Forecast and intercept jointly changed with updated internal hashes"),
    "F10_coherent_source": (False, "Source digest changed with updated internal hashes"),
    "F11_coherent_model": (False, "Model artifact digest changed with updated internal hashes"),
    "F12_coherent_validation": (False, "Validation count/summary changed while retaining arithmetic consistency"),
}


def build_cases(cards: list[dict]) -> list[dict]:
    cases = []
    for index, card in enumerate(cards):
        key = record_key(card)
        for family, (expected, description) in FAMILIES.items():
            envelope = {"card": copy.deepcopy(card)}
            bind(envelope)
            patch = {}
            c = envelope["card"]
            if family == "C1_reordered":
                envelope = json.loads(json.dumps(envelope, sort_keys=True))
            elif family == "C2_renewed_review":
                bind(envelope, 2)
                patch = {"version_key": key, "version": 2}
            elif family == "F01_numeric_type":
                c["prediction"] = str(c["prediction"])
                bind(envelope)
            elif family == "F02_horizon":
                c["input_ordinal"] += 1
                bind(envelope)
            elif family == "F03_arithmetic":
                c["delta"] += 1.0
                bind(envelope)
            elif family == "F04_decomposition":
                c["contributions"][0] += 1.0
                bind(envelope)
            elif family == "F05_request_binding":
                envelope["request"]["target_ordinal"] += 1
            elif family == "F06_unverified_operation":
                c["mode"] = "operational"
                bind(envelope)
            elif family == "F07_measurement_unit":
                c["unit"] = "percentage_change"
                bind(envelope)
            elif family == "F08_stale_review":
                patch = {"version_key": key, "version": 2}
            elif family == "F09_coherent_forecast":
                c["prediction"] += 1.0
                c["intercept"] += 1.0
                c["delta"] = c["prediction"] - c["baseline"]
                bind(envelope)
            elif family in {"F10_coherent_source", "F11_coherent_model"}:
                field = "source_sha256" if family == "F10_coherent_source" else "model_sha256"
                c[field] = digest({"altered": c[field]})
                bind(envelope)
            elif family == "F12_coherent_validation":
                c["validation_n"] += 1
                if card["validation_n"] == 0:
                    c.update(validation_mae=0.0, validation_baseline_mae=0.0, validation_delta=0.0)
                bind(envelope)
            cases.append({"case_id": f"{index:04d}:{family}", "base_id": key,
                          "dataset": card["dataset_id"], "family": family,
                          "expected_permit": expected, "description": description,
                          "envelope": envelope, "context_patch": patch})
    return cases


def context_for(case: dict, context: dict) -> dict:
    patch = case["context_patch"]
    if not patch:
        return context
    return {**context, "versions": {**context["versions"], patch["version_key"]: patch["version"]}}


def compromised_reference_cases(cards: list[dict], context: dict):
    """Boundary probe outside the trusted-reference assumption, kept separate."""
    cases, contexts = [], []
    for index, card in enumerate(cards):
        changed = copy.deepcopy(card)
        changed["prediction"] += 1.0
        changed["intercept"] += 1.0
        changed["delta"] = changed["prediction"] - changed["baseline"]
        envelope = {"card": changed}
        bind(envelope)
        key = record_key(changed)
        cases.append({"case_id": f"B{index:04d}", "dataset": card["dataset_id"], "envelope": envelope})
        contexts.append({**context, "records": {**context["records"], key: changed}})
    return cases, contexts
