"""Verify preserved predictions and outputs without rerunning decision engines."""
import gzip
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1] / "package/academic-papers"
SOURCE = ROOT / "results/transfer_evaluation"


def main():
    execution = json.loads((SOURCE / "execution_start.json").read_text())
    compressed = []
    for name, field in (("cases_before_execution.json", "cases_sha256"),
                        ("reference_context.json", "reference_sha256")):
        data = gzip.decompress((SOURCE / (name + ".gz")).read_bytes())
        digest = hashlib.sha256(data).hexdigest()
        assert digest == execution[field]
        json.loads(data)
        compressed.append({"path": name + ".gz", "decompressed_sha256": digest,
                           "matches_execution_start_hash": True})
    results = pd.read_csv(SOURCE / "case_results.csv.gz")
    assert len(results) == 30360
    assert results.case_id.nunique() == 7590
    assert not results.duplicated(["case_id", "engine"]).any()
    paired = results.pivot(index="case_id", columns="engine", values="permitted")
    assert paired.native_registered.equals(paired.pandera_registered)
    native = results[results.engine.eq("native_registered")]
    assert native.permitted.sum() == 1518
    assert (~native.permitted).sum() == 6072
    boundary = pd.read_csv(SOURCE / "trust_boundary_results.csv")
    assert len(boundary) == 506
    assert boundary.native_permitted.all() and boundary.pandera_permitted.all()
    raw = pd.read_csv(ROOT / "raw/transfer_macrodata/macrodata.csv")
    saved = pd.read_csv(SOURCE / "macro_predictions.csv")
    assert len(raw) == 203 and len(saved) == 234
    checks = []
    for series in ("realgdp", "realcons", "realinv"):
        values = raw[series].to_numpy()
        growth = 100 * np.diff(np.log(values))
        target = growth[2:]
        features = np.column_stack([growth[1:-1], growth[:-2]])
        years = raw.year.to_numpy()[3:].astype(int)
        quarters = raw.quarter.to_numpy()[3:].astype(int)
        development, test = years <= 1999, years >= 2000
        for name, width, penalty in (("ar1", 1, 0.0), ("ridge_ar2_alpha1", 2, 1.0)):
            x, y = features[development, :width], target[development]
            center, scale = x.mean(0), x.std(0, ddof=0)
            z = (x-center)/scale
            beta = np.linalg.solve(z.T @ z + penalty*np.eye(width), z.T @ (y-y.mean()))
            prediction = y.mean() + (features[test, :width]-center)/scale @ beta
            selected = saved[saved.series.eq(series) & saved.model.eq(name)].sort_values(["year", "quarter"])
            np.testing.assert_allclose(selected.prediction, prediction, rtol=0, atol=2e-10)
            np.testing.assert_allclose(selected.actual, target[test], rtol=0, atol=2e-10)
            np.testing.assert_array_equal(selected.year, years[test])
            np.testing.assert_array_equal(selected.quarter, quarters[test])
            checks.append({"series": series, "model": name, "n": len(selected),
                           "max_absolute_prediction_difference": float(np.max(abs(selected.prediction-prediction)))})
    report = {"status": "passed", "scope": "Preserved-output audit and macro forecast recomputation only; no decision-engine rerun",
              "compressed_files": compressed, "result_rows": len(results), "distinct_inputs": 7590,
              "native_pandera_agreement": 7590, "accepted_normal": 1518, "blocked_faults": 6072,
              "joint_reference_changes_permitted": 506, "macro_recomputation": checks}
    Path(__file__).with_suffix(".json").write_text(json.dumps(report, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
