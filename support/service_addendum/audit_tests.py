"""Additional review cases, separate from the author's frozen evaluation.

A-cases operationalize prose cases specified before reading revised code.
E-cases are exploratory robustness probes written after code inspection.
An exception is recorded as a robustness defect, never counted as permission.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

from run_technical_evaluation import bind, prediction
from workflow_guard import canonical_hash, card_hash, load_original, validate


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source-root", required=True, type=Path)
    ap.add_argument("--frozen-cases", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    args = ap.parse_args()
    spec = json.loads(args.frozen_cases.read_text(encoding="utf-8"))
    base = next(c["fixture"] for c in spec["cases"] if c["case_id"] == "N01")
    modules = load_original(args.source_root)
    cases = []

    def add(
        cid,
        description,
        fn,
        expected_block,
        note="pre-implementation prose specification",
    ):
        env = copy.deepcopy(base)
        fn(env)
        cases.append((cid, description, env, expected_block, note))

    def stale_review(x):
        old = x["review"]["evidence_sha256"]
        prediction(x, 1.0)
        bind(x)
        x["review"]["evidence_sha256"] = old

    add(
        "A01",
        "Previous valid review hash with updated coherent current card",
        stale_review,
        True,
    )
    add(
        "A02",
        "Arbitrary well-formed nonempty review hash",
        lambda x: x["review"].update(evidence_sha256="a" * 64),
        True,
    )

    def old_request_receipt(x):
        x["request"]["intended_decision_date"] = "2024-12-30"
        x["current_state"]["request_sha256"] = canonical_hash(x["request"])

    add(
        "A03",
        "Previous request receipt reused with same card",
        old_request_receipt,
        True,
    )

    def changed_card_old_bindings(x):
        prediction(x, 1.0)
        x["card"]["decision_basis_sha256"] = card_hash(x["card"])

    add(
        "A04",
        "Rehashed coherent current card with old receipt and review",
        changed_card_old_bindings,
        True,
    )
    add(
        "A05",
        "Still-eligible publication date edited without fresh receipt",
        lambda x: x["request"]["sources"][0].update(release_date="2024-10-07"),
        True,
    )

    def bad_delta(x):
        x["card"]["relative_deviation"]["logpoints"] = 20.0
        bind(x)

    add("A06", "Rehashed numeric relative-deviation inconsistency", bad_delta, True)
    add(
        "A07",
        "String false used as acknowledgement",
        lambda x: x["review"].update(warnings_acknowledged="false"),
        True,
    )

    def bad_boolean(x):
        x["card"]["learned_comparator"]["logpoints"] = True
        bind(x)

    add("A08a", "Boolean prediction", bad_boolean, True)
    add(
        "A08b",
        "Nonfinite prediction",
        lambda x: x["card"]["learned_comparator"].update(logpoints=float("inf")),
        True,
    )

    def equal_cutoff(x):
        x["request"]["sources"][0].update(
            release_date="2024-12-31", vintage_date="2024-12-31"
        )
        x["card"]["data_timing"]["input_source_vintage"] = "2024-12-31"
        bind(x)

    add("A09", "Release and vintage exactly equal cutoff", equal_cutoff, False)

    def target_past(x, retrospective=False):
        x["request"]["target_refperiod"] = "2024-04"
        x["request"]["sources"][0].update(
            source_refperiod="2023-04", previous_refperiod="2022-04"
        )
        x["card"].update(target_year=2024, input_year=2023)
        if retrospective:
            x["request"]["role"] = "retrospective_diagnostic"
        bind(x)

    add("A10a", "Past target in operational-cutoff request", target_past, True)
    add(
        "A10b",
        "Same past target in retrospective request",
        lambda x: target_past(x, True),
        False,
    )
    add(
        "A11",
        "Historical outcome audit changed only",
        lambda x: x["card"]["historical_outcome_audit"].update(observed_logpoints=0.0),
        False,
    )
    add(
        "A12",
        "JSON object keys reversed only",
        lambda x: x.update(card=dict(reversed(list(x["card"].items())))),
        False,
    )

    def wrong_default_direction(x):
        x["card"]["default_estimate"]["direction"] = "감소"
        bind(x)

    exploratory = "exploratory code-review probe; not a frozen primary case"
    add(
        "E01",
        "Wrong baseline direction label with coherent numeric values",
        wrong_default_direction,
        True,
        exploratory,
    )
    add("E02", "Missing top-level review", lambda x: x.pop("review"), True, exploratory)
    add("E03", "Review is null", lambda x: x.update(review=None), True, exploratory)
    add("E04", "Card is null", lambda x: x.update(card=None), True, exploratory)

    rows = []
    for cid, desc, env, expected_block, note in cases:
        try:
            result = validate(env, modules)
            blocked = not result["research_review_permitted"]
            rows.append(
                dict(
                    case_id=cid,
                    description=desc,
                    expected_block=expected_block,
                    observed_block=blocked,
                    matches_expectation=blocked == expected_block,
                    exception=None,
                    codes=[e["code"] for e in result["errors"]],
                    note=note,
                )
            )
        except Exception as exc:
            rows.append(
                dict(
                    case_id=cid,
                    description=desc,
                    expected_block=expected_block,
                    observed_block=None,
                    matches_expectation=False,
                    exception=type(exc).__name__ + ": " + str(exc),
                    codes=[],
                    note=note,
                )
            )
    result = {
        "status": "PASS" if all(r["matches_expectation"] for r in rows) else "FAIL",
        "scope": "Additional code review, not external validation or user evaluation. A-cases were specified in prose before revised implementation inspection; E-cases are exploratory. Exceptions imply missing structured diagnostic response, not observed permission.",
        "source_frozen_cases_sha256": hashlib.sha256(
            args.frozen_cases.read_bytes()
        ).hexdigest(),
        "workflow_guard_sha256": hashlib.sha256(
            Path(__file__).with_name("workflow_guard.py").read_bytes()
        ).hexdigest(),
        "rows": rows,
        "specified_case_count": sum(r["case_id"].startswith("A") for r in rows),
        "specified_matches": sum(
            r["case_id"].startswith("A") and r["matches_expectation"] for r in rows
        ),
        "exploratory_case_count": sum(r["case_id"].startswith("E") for r in rows),
        "exploratory_matches": sum(
            r["case_id"].startswith("E") and r["matches_expectation"] for r in rows
        ),
    }
    if args.output.exists():
        raise RuntimeError(
            "Audit output exists; choose a new path to preserve prior findings."
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps({k: v for k, v in result.items() if k != "rows"}, ensure_ascii=False)
    )
    for row in rows:
        if not row["matches_expectation"]:
            print(json.dumps(row, ensure_ascii=False))
    if result["status"] != "PASS":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
