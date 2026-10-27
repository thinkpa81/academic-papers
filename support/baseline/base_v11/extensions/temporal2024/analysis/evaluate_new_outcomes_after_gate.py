if not __debug__:
    raise RuntimeError("Run verification with Python optimization disabled.")
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--gate-json", type=Path, required=True)
p.add_argument(
    "--outcomes-csv",
    type=Path,
    required=True,
    help="Approved tidy data: region_code,industry_code,target_year,employment; persons.",
)
p.add_argument("--frozen-root", type=Path, default=Path(__file__).resolve().parent)
p.add_argument("--output-root", type=Path, required=True)
a = p.parse_args()
frozen = a.frozen_root.resolve()
out = a.output_root.resolve()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
    )


gate = json.loads(a.gate_json.read_text(encoding="utf-8"))
assert gate.get("status") == "PASS", (
    "No outcome loading/scoring without documented source gate PASS"
)
assert gate.get("eligibility_decided_without_prediction_losses") is True
assert gate.get("decision_utc") and gate.get("official_source_identifiers")
required = [
    "official_source_verified",
    "geography17_matched",
    "industry10_matched",
    "employment_unit_matched",
    "observation_reference_time_compatible",
    "historical_overlap_review_passed",
    "labour_covariates_required_for_used_origins_matched",
    "no_unresolved_series_break",
    "no_loss_based_exclusions",
]
for k in required:
    c = gate.get("checks", {}).get(k, {})
    assert c.get("status") == "PASS" and c.get("evidence"), (
        f"Missing documented gate check: {k}"
    )
assert sha(a.outcomes_csv) == gate.get("approved_outcomes_sha256"), (
    "Approved outcome file changed"
)
years = gate.get("eligible_target_years", [])
assert years and set(years).issubset({2024, 2025}) and (len(set(years)) == len(years))
design = frozen / "freeze_design_before_new_outcomes.json"
assert (
    sha(design)
    == (frozen / "freeze_design_before_new_outcomes.sha256")
    .read_text(encoding="utf-8")
    .split()[0]
)
keys = ["region_code", "industry_code", "target_year"]
locked = {}
for year in years:
    pp = frozen / f"frozen_predictions_target{year}.csv"
    expected = gate.get("approved_frozen_prediction_sha256", {}).get(str(year))
    assert pp.is_file() and expected and (sha(pp) == expected), (
        f"Prediction file unavailable/changed: {year}"
    )
    if year == 2024:
        manifest = json.loads(
            (frozen / "frozen_prediction_manifest_before_new_outcomes.json").read_text(
                encoding="utf-8"
            )
        )
        assert sha(pp) == manifest["files"][pp.name]["sha256"]
    else:
        manifest_path = frozen / "frozen_prediction_manifest_target2025.json"
        assert manifest_path.is_file(), (
            "2025 predictions must be independently frozen before target2025 scoring"
        )
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest.get("target2025_outcomes_loaded") is False
        assert sha(pp) == manifest["files"][pp.name]["sha256"]
    locked[year] = pd.read_csv(pp)
    for col in ["target", "employment_tp1", "actual_employment"]:
        assert col not in locked[year], (
            f"Outcome leaked into frozen prediction artifact: {col}"
        )
    assert len(locked[year]) == 170 and (not locked[year].duplicated(keys).any())
    assert (
        locked[year].target_year.eq(year).all()
        and locked[year].origin_year.eq(year - 1).all()
    )
    assert (
        locked[year].region_code.nunique() == 17
        and locked[year].industry_code.nunique() == 10
    )
actual = pd.read_csv(a.outcomes_csv, usecols=keys + ["employment"])
assert not actual.duplicated(keys).any(), "Duplicate outcome keys"
assert set(actual.target_year.unique()).issubset(set(years)), (
    "Outcome file must contain only already eligible target years"
)
assert actual.employment.gt(0).all() and np.isfinite(actual.employment).all(), (
    "No automatic zero/nonfinite outcome exclusion"
)
frames = []
metricrows = []
models = ["zero", "industry_mean", "ridge", "random_forest", "hist_gradient_boosting"]


def metrics(frame, name, period):
    y = frame.target_logpoints.to_numpy()
    pred = frame["pred_" + name].to_numpy()
    err = np.abs(y - pred)
    return {
        "period": str(period),
        "model": name,
        "n": len(frame),
        "MAE": float(err.mean()),
        "RMSE": float(np.sqrt(np.square(y - pred).mean())),
        "origin_employment_weighted_MAE": float(
            np.average(err, weights=frame.origin_employment_weight)
        ),
        "direction_accuracy": float(np.mean((y < 0) == (pred < 0))),
        "mean_actual": float(y.mean()),
        "mean_prediction": float(pred.mean()),
        "actual_decline_share": float(np.mean(y < 0)),
        "inference": "descriptive held-future-year evaluation; no DM p-value",
    }


for year, pr in locked.items():
    act = actual[actual.target_year.eq(year)]
    assert len(act) == 170 and set(map(tuple, act[keys].to_numpy())) == set(
        map(tuple, pr[keys].to_numpy())
    ), "Incomplete or incompatible 170-cell coverage; no loss-based selection"
    f = pr.merge(act, on=keys, validate="one_to_one")
    f["target_logpoints"] = 100 * np.log(f.employment / f.origin_employment_weight)
    for m in models:
        metricrows.append(metrics(f, m, year))
    frames.append(f)
combined = pd.concat(frames, ignore_index=True)
for m in models:
    metricrows.append(metrics(combined, m, "pooled_equal_cells"))
metrics_frame = pd.DataFrame(metricrows)
if len(years) == 2:
    for m in models:
        r = metrics_frame[
            metrics_frame.model.eq(m)
            & metrics_frame.period.isin([str(y) for y in years])
        ]
        rec = {
            "period": "equal_year_mean",
            "model": m,
            "n": len(combined),
            "inference": "average of two annual metrics, not a new independent experiment",
        }
        for col in [
            "MAE",
            "RMSE",
            "origin_employment_weighted_MAE",
            "direction_accuracy",
            "mean_actual",
            "mean_prediction",
            "actual_decline_share",
        ]:
            rec[col] = float(r[col].mean())
        metricrows.append(rec)
metrics_frame = pd.DataFrame(metricrows)
zero = metrics_frame[metrics_frame.model.eq("zero")].set_index("period").MAE
metrics_frame["delta_MAE_vs_zero"] = metrics_frame.MAE - metrics_frame.period.map(zero)
out.mkdir(parents=True, exist_ok=True)
combined.to_csv(
    out / "locked_future_predictions_and_outcomes.csv",
    index=False,
    encoding="utf-8-sig",
)
metrics_frame.to_csv(
    out / "locked_future_year_metrics.csv", index=False, encoding="utf-8-sig"
)
write(
    out / "evaluation_provenance.json",
    {
        "evaluated_utc": datetime.now(timezone.utc).isoformat(),
        "gate_sha256": sha(a.gate_json),
        "outcomes_sha256": sha(a.outcomes_csv),
        "design_sha256": sha(design),
        "prediction_sha256": gate["approved_frozen_prediction_sha256"],
        "eligible_years_predefined_by_gate": years,
        "refit": False,
        "tuning": False,
        "new_loss_based_exclusion": False,
        "inferential_pvalues": False,
        "script_sha256": sha(Path(__file__)),
    },
)
print(
    json.dumps(
        {
            "status": "SCORED_after_gate",
            "target_years": years,
            "rows": len(combined),
            "models": models,
        },
        ensure_ascii=False,
    )
)
