"""Portable checks for retrospective forecast evidence.

The caller supplies the reference registry and current review versions separately
from the submitted envelope. This module does not authenticate that caller.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any

import pandas as pd
import pandera.pandas as pa
from jsonschema import Draft202012Validator

TOLERANCE = 1e-9
IDENTITY = ("dataset_id", "entity_id", "measure_id", "model_id", "target_ordinal")
TEXT_FIELDS = ("dataset_id", "entity_id", "measure_id", "model_id", "unit", "mode")
DIGEST_FIELDS = ("source_sha256", "model_sha256", "input_sha256")
INTEGER_FIELDS = ("input_ordinal", "target_ordinal", "step", "validation_n")
NUMBER_FIELDS = ("prediction", "baseline", "delta", "intercept")
NULLABLE_FIELDS = ("validation_mae", "validation_baseline_mae", "validation_delta")
BOOLEAN_FIELDS = ("source_available", "historical_vintage_verified")
REFERENCE_FIELDS = (*TEXT_FIELDS, *DIGEST_FIELDS, *INTEGER_FIELDS,
                    *NUMBER_FIELDS, *NULLABLE_FIELDS, *BOOLEAN_FIELDS, "contributions")


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False)


def digest(value: Any) -> str:
    return hashlib.sha256(canonical(value).encode("utf-8")).hexdigest()


def record_key(card: dict) -> str:
    return canonical([card[field] for field in IDENTITY])


def bind(envelope: dict, review_version: int = 1) -> None:
    """Record a synthetic review; never represents an observed human action."""
    card = envelope["card"]
    envelope["request"] = {field: card[field] for field in IDENTITY}
    envelope["review"] = {
        "evidence_sha256": digest(card),
        "request_sha256": digest(envelope["request"]),
        "version": review_version,
        "reviewer": "synthetic-reviewer",
        "reason": "Technical evaluation fixture",
    }


def equivalent(actual: Any, expected: Any) -> bool:
    if actual is None or expected is None:
        return actual is expected
    if isinstance(actual, bool) or isinstance(expected, bool):
        return type(actual) is type(expected) and actual == expected
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        return math.isfinite(actual) and math.isfinite(expected) and math.isclose(
            actual, expected, rel_tol=0.0, abs_tol=TOLERANCE)
    if isinstance(actual, list) and isinstance(expected, list):
        return len(actual) == len(expected) and all(
            equivalent(a, b) for a, b in zip(actual, expected))
    return type(actual) is type(expected) and actual == expected


def _schema() -> dict:
    number = {"type": "number", "minimum": -1e20, "maximum": 1e20}
    properties = {field: {"type": "string", "minLength": 1} for field in TEXT_FIELDS}
    properties.update({field: {"type": "string", "pattern": "^[0-9a-f]{64}$"}
                       for field in DIGEST_FIELDS})
    properties.update({field: {"type": "integer", "minimum": 0} for field in INTEGER_FIELDS})
    properties.update({field: number for field in NUMBER_FIELDS})
    properties.update({field: {"anyOf": [number, {"type": "null"}]} for field in NULLABLE_FIELDS})
    properties.update({field: {"type": "boolean"} for field in BOOLEAN_FIELDS})
    properties["contributions"] = {"type": "array", "minItems": 1, "items": number}
    properties["mode"] = {"enum": ["retrospective", "operational"]}
    card = {"type": "object", "required": list(properties),
            "properties": properties, "additionalProperties": False}
    request = {"type": "object", "required": list(IDENTITY),
               "properties": {field: properties[field] for field in IDENTITY},
               "additionalProperties": False}
    review = {"type": "object", "required": ["evidence_sha256", "request_sha256", "version", "reviewer", "reason"],
              "properties": {
                  "evidence_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                  "request_sha256": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
                  "version": {"type": "integer", "minimum": 1},
                  "reviewer": {"type": "string", "minLength": 1},
                  "reason": {"type": "string", "minLength": 1}}, "additionalProperties": False}
    return {"$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object", "required": ["card", "request", "review"],
            "properties": {"card": card, "request": request, "review": review},
            "additionalProperties": False}


SCHEMA = _schema()
Draft202012Validator.check_schema(SCHEMA)
STRUCTURE = Draft202012Validator(SCHEMA)


@dataclass(frozen=True)
class Decision:
    permitted: bool
    errors: tuple[str, ...] = ()


def validate_structure(envelope: Any) -> Decision:
    try:
        canonical(envelope)
        errors = tuple(sorted({"schema:" + "/".join(map(str, e.absolute_path))
                               for e in STRUCTURE.iter_errors(envelope)}))
    except (TypeError, ValueError, RecursionError):
        errors = ("non_json_value",)
    return Decision(not errors, errors)


def validate_native(envelope: Any, context: dict) -> Decision:
    """Direct implementation of the declared common review requirements."""
    shape = validate_structure(envelope)
    if not shape.permitted:
        return shape
    card, request, review = (envelope[k] for k in ("card", "request", "review"))
    key = record_key(card)
    policy = context["policies"].get(card["dataset_id"])
    reference = context["records"].get(key)
    errors = []

    def check(name: str, condition: bool) -> None:
        if not condition:
            errors.append(name)

    check("dataset_policy", policy is not None)
    if policy is None:
        return Decision(False, tuple(errors))
    check("unit", card["unit"] == policy["unit"])
    check("horizon", card["step"] == policy["step"]
          and card["target_ordinal"] - card["input_ordinal"] == policy["step"])
    check("eligibility", card["source_available"] and
          (card["mode"] == "retrospective" or card["historical_vintage_verified"]))
    check("arithmetic", equivalent(card["delta"], card["prediction"] - card["baseline"]))
    check("decomposition", equivalent(card["prediction"], card["intercept"] + sum(card["contributions"])))
    no_validation = card["validation_n"] == 0
    values = [card[f] for f in NULLABLE_FIELDS]
    check("validation", (no_validation and all(v is None for v in values)) or
          (not no_validation and all(v is not None for v in values)
           and card["validation_mae"] >= 0 and card["validation_baseline_mae"] >= 0
           and equivalent(card["validation_delta"], card["validation_mae"] - card["validation_baseline_mae"])))
    check("request_identity", all(card[f] == request[f] for f in IDENTITY))
    check("evidence_binding", review["evidence_sha256"] == digest(card))
    check("request_binding", review["request_sha256"] == digest(request))
    check("current_review", review["version"] == context["versions"].get(key))
    check("reference_exists", reference is not None)
    if reference is not None:
        for field in REFERENCE_FIELDS:
            check("reference:" + field, equivalent(card[field], reference[field]))
    return Decision(not errors, tuple(errors))


def _row(envelope: dict, context: dict) -> dict:
    """Expose raw values and arithmetic operands to the external validator."""
    card, request, review = (envelope[k] for k in ("card", "request", "review"))
    key = record_key(card)
    policy = context["policies"].get(card["dataset_id"], {})
    reference = context["records"].get(key)
    row = {f: card[f] for f in REFERENCE_FIELDS}
    row.update({"contribution_sum": sum(card["contributions"]),
                "expected_unit": policy.get("unit", "<unregistered>"),
                "expected_step": policy.get("step", -1),
                "reference_exists": reference is not None,
                "current_version": context["versions"].get(key, -1),
                "review_version": review["version"],
                "review_card_sha": review["evidence_sha256"],
                "computed_card_sha": digest(card),
                "review_request_sha": review["request_sha256"],
                "computed_request_sha": digest(request)})
    row.update({"request_" + f: request[f] for f in IDENTITY})
    row.update({"reference_" + f: reference[f] if reference is not None else None
                for f in REFERENCE_FIELDS})
    return row


def _equal_columns(frame: pd.DataFrame, a: str, b: str) -> pd.Series:
    return frame.apply(lambda row: equivalent(row[a], row[b]), axis=1)


def _validation_consistency(frame: pd.DataFrame) -> pd.Series:
    def valid(row: pd.Series) -> bool:
        if row.validation_n == 0:
            return all(row[f] is None for f in NULLABLE_FIELDS)
        return all(row[f] is not None for f in NULLABLE_FIELDS) and (
            row.validation_mae >= 0 and row.validation_baseline_mae >= 0
            and abs(row.validation_delta - (row.validation_mae - row.validation_baseline_mae)) <= TOLERANCE)
    return frame.apply(valid, axis=1)


def _pandera_schema(registered: bool) -> pa.DataFrameSchema:
    checks = [
        pa.Check(lambda d: d.unit == d.expected_unit, name="unit", ignore_na=False),
        pa.Check(lambda d: (d.step == d.expected_step) &
                 (d.target_ordinal - d.input_ordinal == d.expected_step), name="horizon", ignore_na=False),
        pa.Check(lambda d: d.source_available &
                 ((d["mode"] == "retrospective") | d.historical_vintage_verified), name="eligibility", ignore_na=False),
        pa.Check(lambda d: abs(d.delta - (d.prediction - d.baseline)) <= TOLERANCE,
                 name="arithmetic", ignore_na=False),
        pa.Check(lambda d: abs(d.prediction - (d.intercept + d.contribution_sum)) <= TOLERANCE,
                 name="decomposition", ignore_na=False),
        pa.Check(_validation_consistency, name="validation", ignore_na=False),
        pa.Check(lambda d: d.review_card_sha == d.computed_card_sha, name="evidence_binding", ignore_na=False),
        pa.Check(lambda d: d.review_request_sha == d.computed_request_sha, name="request_binding", ignore_na=False),
    ]
    for field in IDENTITY:
        checks.append(pa.Check(lambda d, f=field: d[f] == d["request_" + f],
                               name="request_" + field, ignore_na=False))
    if registered:
        checks.extend([
            pa.Check(lambda d: d.review_version == d.current_version, name="current_review", ignore_na=False),
            pa.Check(lambda d: d.reference_exists, name="reference_exists", ignore_na=False),
        ])
        for field in REFERENCE_FIELDS:
            checks.append(pa.Check(lambda d, f=field: _equal_columns(d, f, "reference_" + f),
                                   name="reference_" + field, ignore_na=False))
    # JSON Schema performs strict nested types before Pandera receives a row.
    # No native-validator verdict or expected case label is passed to Pandera.
    return pa.DataFrameSchema(checks=checks, strict=False, coerce=False)


LOCAL_SCHEMA = _pandera_schema(False)
REGISTERED_SCHEMA = _pandera_schema(True)


def validate_pandera(envelope: Any, context: dict, *, registered: bool) -> Decision:
    shape = validate_structure(envelope)
    if not shape.permitted:
        return shape
    row = _row(envelope, context)
    # Object dtype preserves the semantic distinction between None and NaN.
    frame = pd.DataFrame([row], dtype=object)
    try:
        (REGISTERED_SCHEMA if registered else LOCAL_SCHEMA).validate(frame, lazy=True)
    except pa.errors.SchemaErrors as exc:
        failures = tuple(sorted(map(str, exc.failure_cases["check"].unique())))
        return Decision(False, failures)
    return Decision(True)


def validate_pandera_batch(envelopes: list, contexts: list, *, registered: bool) -> list[Decision]:
    """Validate a batch without treating an invalid row as failure of every row."""
    decisions = [validate_structure(e) for e in envelopes]
    positions = [i for i, d in enumerate(decisions) if d.permitted]
    rows = [_row(envelopes[i], contexts[i]) for i in positions]
    if not rows:
        return decisions
    frame = pd.DataFrame(rows, index=positions, dtype=object)
    try:
        (REGISTERED_SCHEMA if registered else LOCAL_SCHEMA).validate(frame, lazy=True)
    except pa.errors.SchemaErrors as exc:
        failures: dict[int, set[str]] = {}
        for row in exc.failure_cases.itertuples():
            if pd.isna(row.index) or int(row.index) not in positions:
                raise RuntimeError("Non-row Pandera error; cannot assign a case verdict") from exc
            failures.setdefault(int(row.index), set()).add(str(row.check))
        for position, errors in failures.items():
            decisions[position] = Decision(False, tuple(sorted(errors)))
    return decisions
