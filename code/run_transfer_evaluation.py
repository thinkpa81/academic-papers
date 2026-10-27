#!/usr/bin/env python3
"""Compare validation configurations and transfer them to public macrodata."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path

import pandas as pd
from evidence_contract import (
    SCHEMA,
    validate_native,
    validate_pandera_batch,
    validate_structure,
)
from transfer_cases import (
    FAMILIES,
    build_cases,
    compromised_reference_cases,
    context_for,
)
from transfer_sources import build_sources

ROOT = Path(__file__).resolve().parents[1]


def save(value, path: Path) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(output: Path) -> None:
    output.mkdir(parents=True, exist_ok=False)
    code_paths = [ROOT / "code" / name for name in (
        "evidence_contract.py", "transfer_sources.py", "transfer_cases.py", "run_transfer_evaluation.py")]
    protocol = {
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "status": "recorded_before_fit_and_case_evaluation", "version": 1,
        "protocol_type": "retrospective technical extension, not independently preregistered",
        "human_participants": 0, "external_evaluator": False,
        "external_data": "US macrodata: real GDP, consumption, investment",
        "external_split": {"train_end": "1989Q4", "validation": "1990Q1–1999Q4", "test": "2000Q1–2009Q3"},
        "models": ["AR(1) OLS", "standardized AR(2) ridge alpha=1"],
        "model_selection": "none; both fixed configurations retained",
        "comparison": {
            "json_schema": "Typed nested schema only; a deliberately limited configuration, not a capability limit",
            "pandera_local": "Schema plus domain rules/internal relationships; no current versions or registry comparison",
            "pandera_registered": "Same input plus caller-held current versions and reference registry",
            "native_registered": "Direct implementation with the same rules and reference information as pandera_registered"},
        "case_families": FAMILIES,
        "reference_boundary": "Jointly changing submitted and trusted reference data is outside assumptions; report separately",
        "code_sha256": {str(p.relative_to(ROOT)): sha(p) for p in code_paths},
        "dependencies": {name: version(name) for name in ("numpy", "pandas", "scikit-learn", "pandera", "jsonschema")},
        "python": sys.version,
    }
    save(protocol, output / "protocol_before_execution.json")
    save(SCHEMA, output / "envelope.schema.json")
    cards, context, source_metadata = build_sources(output)
    save(source_metadata, output / "data_provenance.json")
    save(context, output / "reference_context.json")
    cases = build_cases(cards)
    save(cases, output / "cases_before_execution.json")
    save({"utc": datetime.now(timezone.utc).isoformat(),
          "cases_sha256": sha(output / "cases_before_execution.json"),
          "reference_sha256": sha(output / "reference_context.json"),
          "code_sha256": protocol["code_sha256"]}, output / "execution_start.json")
    envelopes = [c["envelope"] for c in cases]
    contexts = [context_for(c, context) for c in cases]
    engines = {
        "json_schema": [validate_structure(e) for e in envelopes],
        "native_registered": [validate_native(e, ctx) for e, ctx in zip(envelopes, contexts)],
        "pandera_local": validate_pandera_batch(envelopes, contexts, registered=False),
        "pandera_registered": validate_pandera_batch(envelopes, contexts, registered=True),
    }
    rows = []
    for engine, decisions in engines.items():
        for case, decision in zip(cases, decisions):
            rows.append({"case_id": case["case_id"], "base_id": case["base_id"],
                         "dataset": case["dataset"], "family": case["family"], "engine": engine,
                         "expected_permit": case["expected_permit"], "permitted": decision.permitted,
                         "matches": decision.permitted == case["expected_permit"],
                         "errors": ";".join(decision.errors)})
    results = pd.DataFrame(rows)
    results.to_csv(output / "case_results.csv", index=False)
    groups = results.groupby(["dataset", "engine", "family"], sort=True).agg(
        n=("case_id", "size"), permitted=("permitted", "sum"), matching=("matches", "sum")).reset_index()
    groups.to_csv(output / "results_by_family.csv", index=False)
    summary = []
    for (dataset, engine), group in results.groupby(["dataset", "engine"], sort=True):
        normal, fault = group[group.expected_permit], group[~group.expected_permit]
        summary.append({"dataset": dataset, "engine": engine,
                        "normal_n": len(normal), "normal_accepted": int(normal.permitted.sum()),
                        "fault_n": len(fault), "fault_blocked": int((~fault.permitted).sum())})
    pd.DataFrame(summary).to_csv(output / "comparison_summary.csv", index=False)
    paired = results.pivot(index="case_id", columns="engine", values="permitted")
    agreement = int((paired.native_registered == paired.pandera_registered).sum())
    boundary, boundary_contexts = compromised_reference_cases(cards, context)
    boundary_native = [validate_native(c["envelope"], ctx) for c, ctx in zip(boundary, boundary_contexts)]
    boundary_pandera = validate_pandera_batch([c["envelope"] for c in boundary], boundary_contexts, registered=True)
    boundary_rows = [{"case_id": c["case_id"], "dataset": c["dataset"],
                      "native_permitted": n.permitted, "pandera_permitted": p.permitted,
                      "scope": "trusted_reference_assumption_violated"}
                     for c, n, p in zip(boundary, boundary_native, boundary_pandera)]
    pd.DataFrame(boundary_rows).to_csv(output / "trust_boundary_results.csv", index=False)
    unchanged = all(sha(path) == protocol["code_sha256"][str(path.relative_to(ROOT))] for path in code_paths)
    report = {"completed_utc": datetime.now(timezone.utc).isoformat(),
              "base_forecasts": len(cards), "cases_per_engine": len(cases),
              "engine_decisions": len(results), "case_families": len(FAMILIES),
              "matched_information_engine_agreement": agreement,
              "native_unexpected": int((~results[results.engine == "native_registered"].matches).sum()),
              "pandera_registered_unexpected": int((~results[results.engine == "pandera_registered"].matches).sum()),
              "boundary_cases": len(boundary), "boundary_native_permitted": sum(d.permitted for d in boundary_native),
              "boundary_pandera_permitted": sum(d.permitted for d in boundary_pandera),
              "code_unchanged_during_fit_and_evaluation": unchanged,
              "human_participants": 0, "independent_external_evaluation": False,
              "interpretation": "Same-information comparison and cross-data technical transfer; not tool superiority or human effectiveness",
              "summary": summary}
    save(report, output / "summary.json")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not unchanged or report["native_unexpected"] or report["pandera_registered_unexpected"] or agreement != len(cases):
        raise SystemExit("Unexpected outcomes were retained; inspect this run before making any correction")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    run(parser.parse_args().out.resolve())
