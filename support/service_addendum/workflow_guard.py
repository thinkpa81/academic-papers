"""Research-only workflow consistency extension to the pinned KITS prototype.

This adds explicit inter-record invariants. SHA-256 here detects inconsistent
copies, not authenticity. ``current_state`` must be supplied by a trusted caller.
Neither successful validation nor any receipt is institutional approval.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path

VERSION = "workflow-consistency-1.1.0"


def canonical_hash(obj):
    return hashlib.sha256(
        json.dumps(
            obj,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        ).encode()
    ).hexdigest()


def card_hash(card):
    return canonical_hash(
        {
            k: v
            for k, v in card.items()
            if k not in {"decision_basis_sha256", "historical_outcome_audit"}
        }
    )


def load_original(source_root):
    root = Path(source_root)
    paths = {
        "service": root / "base_v11/extensions/revision_v9/service/build_service.py",
        "gate": root / "base_v11/service_time_controls/source_gate.py",
    }
    modules = {}
    for name, path in paths.items():
        spec = importlib.util.spec_from_file_location("kits_original_" + name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        modules[name] = module
    return modules


def validate(
    envelope, modules, enabled=("T", "I", "S", "L"), original=False, flat=False
):
    errors = []
    gate_result = None
    required = ("card", "request", "review") + (
        ("receipt", "current_state") if "L" in enabled and not original else ()
    )
    malformed = not isinstance(envelope, dict) or any(
        not isinstance(envelope.get(k), dict) for k in required
    )
    if malformed:
        return {
            "version": VERSION,
            "status": "research_review_blocked",
            "research_review_permitted": False,
            "evaluation_order": "flat_predicate_list" if flat else "module_trace",
            "errors": [{"module": "I", "code": "top_level_workflow_schema_invalid"}],
            "source_gate": None,
            "automatic_policy_action_allowed": False,
            "operational_prediction_permitted": False,
            "institutional_approval_granted": False,
            "human_evaluation_conducted": False,
            "interpretation": "Malformed workflow envelope; structured research-review block, no institutional action.",
        }
    card, request, review = (envelope[k] for k in ("card", "request", "review"))

    def check(module, code, condition):
        if module in enabled and not condition:
            errors.append({"module": module, "code": code})

    if "T" in enabled:
        try:
            gate_result = modules["gate"].evaluate_source_gate(request)
            check(
                "T",
                "source_metadata_ineligible",
                request["role"] == "retrospective_diagnostic"
                or gate_result["metadata_eligible_for_requested_cutoff"],
            )
        except (ValueError, KeyError, TypeError) as exc:
            errors.append(
                {"module": "T", "code": "source_schema_invalid", "detail": str(exc)}
            )

    if "I" in enabled:
        for name, fn, obj in [
            ("card", modules["service"].validate_card, card),
            ("review", modules["service"].validate_review, review),
        ]:
            try:
                fn(obj)
            except (ValueError, KeyError, TypeError) as exc:
                errors.append(
                    {"module": "I", "code": name + "_invalid", "detail": str(exc)}
                )
        if not original:
            check(
                "I",
                "warnings_must_be_true_boolean",
                review.get("warnings_acknowledged") is True,
            )
            for key in ("reviewer_role", "reason_for_review", "evidence_sha256"):
                value = review.get(key)
                check(
                    "I",
                    "nonblank_review_" + key,
                    isinstance(value, str) and bool(value.strip()),
                )
            refs = review.get("reference_materials")
            check(
                "I",
                "reference_materials_must_be_nonempty_list",
                isinstance(refs, list)
                and bool(refs)
                and all(isinstance(x, str) and bool(x.strip()) for x in refs),
            )

    if "S" in enabled and not original:
        try:
            a, b = (
                card["default_estimate"]["logpoints"],
                card["learned_comparator"]["logpoints"],
            )
            d = card["relative_deviation"]
            nums = [
                a,
                b,
                d["logpoints"],
                d["tolerance_logpoints"],
                card["employment_input_persons"],
            ]
            numeric = all(
                isinstance(x, (int, float))
                and not isinstance(x, bool)
                and math.isfinite(x)
                for x in nums
            )
            check("S", "finite_numeric_fields", numeric)
            if numeric:
                check(
                    "S",
                    "positive_input_employment",
                    card["employment_input_persons"] > 0,
                )
                check("S", "fixed_display_tolerance", d["tolerance_logpoints"] == 0.5)
                check(
                    "S",
                    "relative_deviation_arithmetic",
                    math.isclose(d["logpoints"], b - a, abs_tol=1e-10, rel_tol=0),
                )
                check(
                    "S",
                    "relative_deviation_label",
                    d["class"] == modules["service"].band(d["logpoints"]),
                )
                check(
                    "S",
                    "learned_direction_label",
                    card["learned_comparator"]["direction"]
                    == modules["service"].direction(b),
                )
                default = card["default_estimate"]
                check(
                    "S",
                    "baseline_raw_direction",
                    default.get("raw_direction_for_statistical_audit")
                    == modules["service"].direction(a),
                )
                check(
                    "S",
                    "constant_baseline_direction_suppressed",
                    default.get("direction_label_displayed") is False,
                )
                if "direction" in default:
                    check(
                        "S",
                        "baseline_extra_direction_consistency",
                        default["direction"] == modules["service"].direction(a),
                    )
                ex = card["linear_explanation"]
                parts = [ex["intercept_logpoints"], ex["reconstructed_logpoints"]] + [
                    v["contribution_logpoints"] for v in ex["contributions"]
                ]
                finite_parts = all(
                    isinstance(x, (int, float))
                    and not isinstance(x, bool)
                    and math.isfinite(x)
                    for x in parts
                )
                check("S", "finite_explanation", finite_parts)
                if finite_parts:
                    total = parts[0] + sum(parts[2:])
                    check(
                        "S",
                        "linear_explanation_arithmetic",
                        math.isclose(total, b, abs_tol=1e-10, rel_tol=0)
                        and math.isclose(parts[1], b, abs_tol=1e-10, rel_tol=0),
                    )
            v = card["prior_validation"]
            n = v["validation_year_n"]
            check(
                "S",
                "validation_count_integer_nonnegative",
                isinstance(n, int) and not isinstance(n, bool) and n >= 0,
            )
            mae_keys = [
                "aggregate_baseline_mae",
                "aggregate_learned_mae",
                "aggregate_mae_difference",
            ]
            if n == 0:
                check(
                    "S",
                    "zero_validation_has_no_aggregate_mae",
                    all(v[k] is None for k in mae_keys),
                )
            elif isinstance(n, int) and n > 0:
                ms = [v[k] for k in mae_keys]
                good = all(
                    isinstance(x, (int, float))
                    and not isinstance(x, bool)
                    and math.isfinite(x)
                    for x in ms
                )
                check("S", "positive_validation_has_mae", good)
                if good:
                    check(
                        "S",
                        "validation_mae_arithmetic",
                        ms[0] >= 0
                        and ms[1] >= 0
                        and math.isclose(
                            ms[2], ms[1] - ms[0], abs_tol=1e-10, rel_tol=0
                        ),
                    )
        except (ValueError, KeyError, TypeError) as exc:
            errors.append(
                {
                    "module": "S",
                    "code": "card_semantic_schema_invalid",
                    "detail": str(exc),
                }
            )

    if "L" in enabled and not original:
        try:
            h = card["decision_basis_sha256"]
            rh = canonical_hash(request)
            receipt, state = envelope["receipt"], envelope["current_state"]
            check("L", "review_card_binding", review["evidence_sha256"] == h)
            check("L", "receipt_card_binding", receipt["card_sha256"] == h)
            check("L", "receipt_request_binding", receipt["request_sha256"] == rh)
            check("L", "current_card_binding", state["card_sha256"] == h)
            check("L", "current_request_binding", state["request_sha256"] == rh)
            check(
                "L",
                "request_card_target_year",
                card["target_year"] == int(request["target_refperiod"][:4]),
            )
            check(
                "L",
                "request_card_input_year",
                all(
                    card["input_year"] == int(s["source_refperiod"][:4])
                    for s in request["sources"]
                ),
            )
            check(
                "L",
                "request_card_source_vintage",
                all(
                    card["data_timing"]["input_source_vintage"] == s["vintage_date"]
                    for s in request["sources"]
                ),
            )
            if request["role"] == "operational_prediction":
                check(
                    "L",
                    "historical_vintage_card_claim",
                    card["data_timing"]["historical_vintage_verified"] is True,
                )
        except (ValueError, KeyError, TypeError) as exc:
            errors.append(
                {
                    "module": "L",
                    "code": "workflow_binding_schema_invalid",
                    "detail": str(exc),
                }
            )

    permitted = not errors
    return {
        "version": VERSION,
        "status": "research_review_complete"
        if permitted
        else "research_review_blocked",
        "research_review_permitted": permitted,
        "evaluation_order": "flat_predicate_list" if flat else "module_trace",
        "errors": errors,
        "source_gate": gate_result,
        "automatic_policy_action_allowed": False,
        "operational_prediction_permitted": False,
        "institutional_approval_granted": False,
        "human_evaluation_conducted": False,
        "interpretation": "Technical consistency only; current_state is trusted caller state. Hashes do not authenticate authors or prove provenance.",
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-root", required=True, type=Path)
    ap.add_argument("--envelope", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    result = validate(
        json.loads(args.envelope.read_text(encoding="utf-8")),
        load_original(args.source_root),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {"status": result["status"], "output": str(args.output)}, ensure_ascii=False
        )
    )


if __name__ == "__main__":
    main()
