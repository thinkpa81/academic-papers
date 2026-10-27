#!/usr/bin/env python3
"""Recompute macro forecasts with linear algebra and audit saved case decisions.

This is a second calculation within the same research project, not an external
evaluation. It does not import the forecasting adapter or its fitted models.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path):
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    with gzip.open(path.with_suffix(path.suffix + ".gz"), "rt", encoding="utf-8") as stream:
        return json.load(stream)


def audit(source: Path) -> dict:
    raw_path = ROOT / "raw/transfer_macrodata/macrodata.csv"
    assert hashlib.sha256(raw_path.read_bytes()).hexdigest() == (
        "d93c0d3a7a77ef83c3af14e46032bb1d02ae3a512b22ab94159a8ca226fcf708")
    raw = pd.read_csv(raw_path)
    saved = pd.read_csv(source / "macro_predictions.csv")
    assert len(raw) == 203 and len(saved) == 234
    model_checks = []
    for series in ("realgdp", "realcons", "realinv"):
        values = raw[series].to_numpy()
        growth = 100 * (np.log(values[1:]) - np.log(values[:-1]))
        # Raw row 3 is the first target with two preceding growth observations.
        targets = growth[2:]
        predictors = np.column_stack([growth[1:-1], growth[:-2]])
        years = raw.year.to_numpy()[3:].astype(int)
        quarters = raw.quarter.to_numpy()[3:].astype(int)
        development, test = years <= 1999, years >= 2000
        assert (development.sum(), test.sum()) == (161, 39)
        assert (years[test][0], quarters[test][0]) == (2000, 1)
        assert (years[test][-1], quarters[test][-1]) == (2009, 3)
        for name, width, penalty in (("ar1", 1, 0.0), ("ridge_ar2_alpha1", 2, 1.0)):
            x, y = predictors[development, :width], targets[development]
            center, scale = x.mean(axis=0), x.std(axis=0, ddof=0)
            z = (x - center) / scale
            coefficients = np.linalg.solve(z.T @ z + penalty * np.eye(width), z.T @ (y - y.mean()))
            prediction = y.mean() + ((predictors[test, :width] - center) / scale) @ coefficients
            selected = saved[(saved.series == series) & (saved.model == name)].sort_values(["year", "quarter"])
            np.testing.assert_array_equal(selected.year, years[test])
            np.testing.assert_array_equal(selected.quarter, quarters[test])
            np.testing.assert_allclose(selected.actual, targets[test], rtol=0, atol=2e-10)
            np.testing.assert_allclose(selected.prediction, prediction, rtol=0, atol=2e-10)
            model_checks.append({"series": series, "model": name, "n": len(selected),
                                 "max_prediction_difference": float(np.max(abs(selected.prediction - prediction))),
                                 "mae_recalculated": float(np.mean(abs(targets[test] - prediction)))})

    result_path = source / "case_results.csv"
    if not result_path.exists():
        result_path = result_path.with_suffix(".csv.gz")
    results = pd.read_csv(result_path)
    assert len(results) == 30360
    assert not results.duplicated(["case_id", "engine"]).any()
    for (dataset, engine), frame in results.groupby(["dataset", "engine"]):
        bases = 272 if dataset == "kosis_employment" else 234
        assert frame.base_id.nunique() == bases
        assert frame.family.nunique() == 15
        assert len(frame) == bases * 15
        assert frame.expected_permit.sum() == bases * 3
    paired = results.pivot(index="case_id", columns="engine", values="permitted")
    assert paired.native_registered.equals(paired.pandera_registered)

    # Validate single-row versus bulk attribution for every family and dataset.
    from evidence_contract import validate_pandera
    from transfer_cases import context_for
    context = load_json(source / "reference_context.json")
    cases = load_json(source / "cases_before_execution.json")
    lookup = {case["case_id"]: case for case in cases}
    selection = results[results.engine == "pandera_registered"].groupby(["dataset", "family"]).first()
    for row in selection.itertuples():
        case = lookup[row.case_id]
        decision = validate_pandera(case["envelope"], context_for(case, context), registered=True)
        assert decision.permitted == row.permitted
    protocol = json.loads((source / "protocol_before_execution.json").read_text(encoding="utf-8"))
    for name, expected in protocol["code_sha256"].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected
    return {"status": "passed", "calculation": "NumPy centered normal equations; no forecasting adapter imported",
            "independent_external_evaluator": False, "model_checks": model_checks,
            "decisions_checked": len(results), "single_row_batch_checks": len(selection),
            "frozen_analysis_code_verified": True}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    args = parser.parse_args()
    report = audit(args.source)
    (args.source / "numerical_audit.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
