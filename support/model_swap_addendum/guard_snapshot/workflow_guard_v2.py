"""Versioned additive research guard, preserving workflow_guard.py unchanged.

Added after the frozen 88-case audit. This is a formative repair, not validation
on an untouched test set. Rules never refer to fixture identifiers.
"""

from __future__ import annotations

import math
import re

from workflow_guard import validate as validate_v1

VERSION = "workflow-consistency-2.0.0"


def validate(envelope, modules, **kwargs):
    extra = []

    def problem(module, code, path=""):
        extra.append({"module": module, "code": code, "path": path})

    def numeric_walk(obj, path=""):
        if isinstance(obj, dict):
            for k, v in obj.items():
                numeric_walk(v, path + "." + str(k))
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                numeric_walk(v, path + "[" + str(i) + "]")
        elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
            try:
                finite = math.isfinite(obj)
            except (OverflowError, ValueError, TypeError):
                finite = False
            if not finite:
                problem("S", "number_outside_supported_finite_domain", path)

    numeric_walk(envelope)
    if extra:
        result = {
            "status": "research_review_blocked",
            "research_review_permitted": False,
            "evaluation_order": "additive_schema_contract_then_v1",
            "errors": [],
            "source_gate": None,
            "automatic_policy_action_allowed": False,
            "operational_prediction_permitted": False,
            "institutional_approval_granted": False,
            "human_evaluation_conducted": False,
        }
    else:
        result = validate_v1(envelope, modules, **kwargs)
    if (
        isinstance(envelope, dict)
        and isinstance(envelope.get("card"), dict)
        and isinstance(envelope.get("request"), dict)
    ):
        c = envelope["card"]
        r = envelope["request"]
        if c.get("schema_version") != "1.1.0":
            problem("I", "unsupported_card_schema_version")
        if c.get("human_evaluation_conducted") is not False:
            problem("I", "unsubstantiated_human_evaluation_claim")
        timing = c.get("data_timing")
        if not isinstance(timing, dict):
            problem("I", "data_timing_schema_invalid")
        elif timing.get("operational_prediction_permitted") is not False:
            problem("I", "nested_operational_permission_not_supported")
        prior = c.get("prior_validation")
        display = c.get("validation_display")
        if not isinstance(prior, dict) or not isinstance(display, dict):
            problem("S", "validation_display_schema_invalid")
        else:
            n = display.get("validation_year_n")
            if (
                not isinstance(n, int)
                or isinstance(n, bool)
                or n != prior.get("validation_year_n")
            ):
                problem("S", "validation_display_count_disagrees")
            a = display.get("mae_difference")
            b = prior.get("aggregate_mae_difference")
            same = a is None and b is None
            if not same and all(
                isinstance(x, (int, float)) and not isinstance(x, bool) for x in (a, b)
            ):
                try:
                    same = (
                        math.isfinite(a)
                        and math.isfinite(b)
                        and math.isclose(a, b, abs_tol=1e-10, rel_tol=0)
                    )
                except (OverflowError, ValueError, TypeError):
                    same = False
            if not same:
                problem("S", "validation_display_mae_disagrees")
            if display.get("direction_percentage_displayed") is not False:
                problem("S", "small_sample_direction_percentage_not_supported")
        sources = r.get("sources")
        if isinstance(sources, list):
            target = r.get("target_refperiod")

            def month_index(s):
                if not isinstance(s, str) or not re.fullmatch(r"\d{4}-\d{2}", s):
                    return None
                y, m = map(int, s.split("-"))
                return y * 12 + m if 1 <= m <= 12 else None

            target_index = month_index(target)
            for s in sources:
                if not isinstance(s, dict):
                    continue
                source_index = month_index(s.get("source_refperiod"))
                if (
                    target_index is None
                    or source_index is None
                    or target_index - source_index != 12
                ):
                    problem("T", "forecast_horizon_must_equal_12_months")
            transition = (
                timing.get("classification_transition")
                if isinstance(timing, dict)
                else None
            )
            if not isinstance(transition, dict):
                problem("T", "classification_display_schema_invalid")
            else:

                def code(x):
                    m = (
                        re.match(r"^(KSIC\d+)(?:_|$)", x)
                        if isinstance(x, str)
                        else None
                    )
                    return m.group(1) if m else None

                inp = code(transition.get("input_basis"))
                target_code = code(transition.get("target_basis"))
                classes = [
                    s.get("classification")
                    for s in sources
                    if isinstance(s, dict) and s.get("classification") is not None
                ]
                if (
                    inp is None
                    or target_code is None
                    or any(v != inp or v != target_code for v in classes)
                ):
                    problem("T", "classification_display_disagrees_with_sources")
    result["version"] = VERSION
    result["errors"] = result["errors"] + extra
    if result["errors"]:
        result["research_review_permitted"] = False
        result["status"] = "research_review_blocked"
    result["interpretation"] = (
        "Research consistency only. V2 adds finite-representation, displayed-evidence, schema and 12-month-horizon contracts after internal audit. No operational authority or human evaluation."
    )
    return result
