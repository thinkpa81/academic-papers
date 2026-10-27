if not __debug__:
    raise RuntimeError("Run verification with Python optimization disabled.")
import argparse
import hashlib
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import scipy
import sklearn
from threadpoolctl import threadpool_limits

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--source-root", type=Path, required=True)
parser.add_argument("--output-root", type=Path, default=Path(__file__).resolve().parent)
a = parser.parse_args()
src = a.source_root.resolve()
out = a.output_root.resolve()
out.mkdir(parents=True, exist_ok=True)
if src == out or src in out.parents:
    parser.error("Keep output outside original source-root")
threadpool_limits(2)


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def write(name, obj):
    (out / name).write_text(
        json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8"
    )


dpath = out / "freeze_design_before_new_outcomes.json"
design = json.loads(dpath.read_text(encoding="utf-8"))
expected_sha = (
    (out / "freeze_design_before_new_outcomes.sha256")
    .read_text(encoding="utf-8")
    .split()[0]
)
assert sha(dpath) == expected_sha, "Frozen design hash mismatch"
for relative, meta in design["original_source_files"].items():
    assert sha(src / relative) == meta["sha256"], f"Original input changed: {relative}"
NUM = design["features_numeric"]
CAT = design["features_categorical"]
FEATURES = NUM + CAT
KEYS = ["region_code", "industry_code", "target_year"]
META = [
    "origin_year",
    "region_name_ko",
    "policy_region_5plus3",
    "industry_name_oecd",
    "origin_employment_weight",
]
columns = FEATURES + ["target_year"] + META
frame = pd.read_csv(src / "analysis/panel_all_rows_with_flags.csv", usecols=columns)
future = (
    frame.loc[frame.origin_year.eq(2023)]
    .copy()
    .sort_values(KEYS)
    .reset_index(drop=True)
)
assert len(future) == 170 and future.target_year.eq(2024).all()
assert future.region_code.nunique() == 17 and future.industry_code.nunique() == 10
assert not future.duplicated(KEYS).any()
if future[FEATURES + ["origin_employment_weight"]].isna().any().any():
    missing = future[FEATURES + ["origin_employment_weight"]].isna().sum()
    write(
        "prediction_status_2024.json",
        {
            "status": "HOLD_missing_original_2023_inputs",
            "missing_by_feature": missing[missing.gt(0)].astype(int).to_dict(),
            "new_outcomes_used": False,
        },
    )
    raise SystemExit(2)
assert np.isfinite(future[NUM].to_numpy()).all()
assert future.origin_employment_weight.gt(0).all()
assert future.origin_year.lt(future.target_year).all()
assert "target" not in future and "employment_tp1" not in future
inputs = out / "frozen_inputs_origin2023_for_target2024.csv"
future.to_csv(inputs, index=False, encoding="utf-8-sig")
train = pd.read_csv(src / "analysis/main/training_design.csv")
assert len(train) == 1610 and train.target_year.max() == 2020
industry_means = train.groupby("industry_code").target.mean()
industry_means.rename("frozen_mean_target_through2020").reset_index().to_csv(
    out / "frozen_industry_mean_baseline.csv", index=False, encoding="utf-8-sig"
)
preds = future[KEYS + META].copy()
preds["pred_zero"] = 0.0
preds["pred_industry_mean"] = future.industry_code.map(industry_means)
assert preds.pred_industry_mean.notna().all()
model_info = {}
for name in ["ridge", "random_forest", "hist_gradient_boosting"]:
    path = src / "analysis/main" / ("model_" + name + ".joblib")
    m = joblib.load(path)
    if name == "ridge":
        assert m.named_steps["model"].alpha == 100
    yp = m.predict(future[FEATURES])
    assert np.isfinite(yp).all()
    preds["pred_" + name] = yp
    model_info[name] = {
        "sha256": sha(path),
        "parameters": m.named_steps["model"].get_params(deep=False),
        "fitted_target_years": [2011, 2020],
        "refitted": False,
    }
ppath = out / "frozen_predictions_target2024.csv"
preds.to_csv(ppath, index=False, encoding="utf-8-sig")
write("frozen_model_details.json", model_info)
write(
    "prediction_status_2024.json",
    {
        "status": "FROZEN_predictions_only",
        "frozen_utc": now(),
        "n": len(preds),
        "target_year": 2024,
        "origin_year": 2023,
        "source_snapshot_date": "2026-09-17",
        "fitted_target_year_max": 2020,
        "new_outcomes_used": False,
        "new_outcomes_loaded": False,
        "outcome_file_loaded": None,
        "scoring_permitted": False,
        "source_gate_status": "HOLD_pending_official_new_data_and_overlap_checks",
        "models": [
            "zero",
            "industry_mean",
            "ridge",
            "random_forest",
            "hist_gradient_boosting",
        ],
        "data_inclusion_independent_of_loss": True,
        "original_source_hash_checks": "PASS",
    },
)
files = [
    dpath,
    out / "freeze_design_before_new_outcomes.sha256",
    inputs,
    out / "frozen_industry_mean_baseline.csv",
    ppath,
    out / "frozen_model_details.json",
    Path(__file__).resolve(),
]
write(
    "frozen_prediction_manifest_before_new_outcomes.json",
    {
        "frozen_utc": now(),
        "status": "Predictions committed before loading new outcomes",
        "files": {p.name: {"sha256": sha(p), "bytes": p.stat().st_size} for p in files},
    },
)
write(
    "prediction_environment.json",
    {
        "completed_utc": now(),
        "python": sys.version,
        "executable": sys.executable,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
        "scipy": scipy.__version__,
        "sklearn": sklearn.__version__,
        "joblib": joblib.__version__,
        "thread_limit": 2,
    },
)
print(
    json.dumps(
        {
            "status": "FROZEN",
            "n": len(preds),
            "new_outcomes_loaded": False,
            "predictions_sha256": sha(ppath),
            "design_sha256": sha(dpath),
        },
        ensure_ascii=False,
    )
)
