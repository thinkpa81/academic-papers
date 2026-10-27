if not __debug__:
    raise RuntimeError("Run verification with Python optimization disabled.")
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

parser = argparse.ArgumentParser(
    description="Independently recalculate preserved2024 metrics without replacing evidence."
)
parser.add_argument(
    "--working-root",
    type=Path,
    default=Path(__file__).resolve().parents[1],
    help="Temporal2024 extension directory.",
)
parser.add_argument(
    "--output-root",
    type=Path,
    help="Separate replay output directory; defaults to WORKING_ROOT/review_replay.",
)
args = parser.parse_args()
R = args.working_root.resolve()
A = R / "analysis"
E = A / "evaluation_2024_official"
OUTPUT = (args.output_root or R / "review_replay").resolve()
if OUTPUT == (R / "review").resolve():
    parser.error("--output-root must differ from preserved review evidence directory.")
OUTPUT.mkdir(parents=True, exist_ok=True)


def read(p):
    with p.open(encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


fr = read(A / "frozen_predictions_target2024.csv")
src = read(R / "source_employment/oecd_v2_4_target2024_170.csv")
out = read(E / "locked_future_predictions_and_outcomes.csv")
metrics = read(E / "locked_future_year_metrics.csv")
key = lambda r: (r["region_code"], r["industry_code"], r["target_year"])
fm, sm, om = ({key(r): r for r in rows} for rows in (fr, src, out))
assert len(fm) == len(sm) == len(om) == 170 and fm.keys() == sm.keys() == om.keys()
gate = json.loads(
    (R / "review/source_gate_independent_OECD2024.json").read_text(encoding="utf-8")
)
prov = json.loads((E / "evaluation_provenance.json").read_text(encoding="utf-8"))
assert (
    gate["approved_outcomes_sha256"]
    == sha(R / "source_employment/oecd_v2_4_target2024_170.csv")
    == prov["outcomes_sha256"]
)
assert (
    gate["approved_frozen_prediction_sha256"]["2024"]
    == sha(A / "frozen_predictions_target2024.csv")
    == prov["prediction_sha256"]["2024"]
)
assert prov["gate_sha256"] == sha(R / "review/source_gate_independent_OECD2024.json")
ys = []
weights = []
predd = {
    m: []
    for m in [
        "zero",
        "industry_mean",
        "ridge",
        "random_forest",
        "hist_gradient_boosting",
    ]
}
maxroundtrip = 0
for k, r in fm.items():
    y = 100 * math.log(
        float(sm[k]["employment"]) / float(r["origin_employment_weight"])
    )
    assert abs(y - float(om[k]["target_logpoints"])) < 1e-12
    ys.append(y)
    weights.append(float(r["origin_employment_weight"]))
    for m in predd:
        p = float(r["pred_" + m])
        d = abs(p - float(om[k]["pred_" + m]))
        assert d < 1e-12
        maxroundtrip = max(maxroundtrip, d)
        predd[m].append(p)
report = []
for m, pr in predd.items():
    errors = [abs(a - p) for a, p in zip(ys, pr)]
    row = {
        "model": m,
        "n": len(ys),
        "MAE": math.fsum(errors) / len(errors),
        "RMSE": math.sqrt(math.fsum((e * e for e in errors)) / len(errors)),
        "origin_employment_weighted_MAE": math.fsum(
            (e * w for e, w in zip(errors, weights))
        )
        / math.fsum(weights),
        "direction_accuracy": sum(((y < 0) == (p < 0) for y, p in zip(ys, pr)))
        / len(ys),
    }
    expected = [r for r in metrics if r["model"] == m and r["period"] == "2024"]
    assert len(expected) == 1
    for metric in [
        "MAE",
        "RMSE",
        "origin_employment_weighted_MAE",
        "direction_accuracy",
    ]:
        assert abs(row[metric] - float(expected[0][metric])) < 1e-10
    report.append(row)
zero = report[0]["MAE"]
ridge = report[2]["MAE"]
mean = report[1]["MAE"]
res = {
    "independent_evaluation_check": "PASS",
    "source_gate_hash": sha(R / "review/source_gate_independent_OECD2024.json"),
    "recalculation_method": "Python csv.DictReader, math.log/fsum/sqrt directly from approved frozen predictions and official target CSV, independent of scorer and produced joined outcomes.",
    "max_prediction_CSV_roundtrip_absdiff": maxroundtrip,
    "metrics": report,
    "ridge_delta_MAE_vs_zero": ridge - zero,
    "ridge_relative_MAE_reduction_vs_zero_pct": 100 * (zero - ridge) / zero,
    "ridge_relative_MAE_reduction_vs_industrymean_pct": 100 * (mean - ridge) / mean,
    "target_mean_logpoints": math.fsum(ys) / 170,
    "actual_decline_share": sum((y < 0 for y in ys)) / 170,
    "interpretation": [
        "One target period only; no inference of stable superiority or prospective performance.",
        "Zero direction_accuracy uses the scorer binary convention decline versus non-decline; it is not three-way decrease/unchanged/increase accuracy.",
        "2023H1→2024H1 target is one year, while original history has mixed observation intervals.",
    ],
    "files": {
        p.name: sha(p)
        for p in [
            E / "locked_future_year_metrics.csv",
            E / "locked_future_predictions_and_outcomes.csv",
            E / "evaluation_provenance.json",
        ]
    },
}
(OUTPUT / "performance_independent_OECD2024.json").write_text(
    json.dumps(res, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(json.dumps(res, ensure_ascii=False, indent=2))
