#!/usr/bin/env python3
"""Coverage, held-out region fitting, and 1,000 cluster reselection draws.
Features/source vintage stay fixed in resampling. The 17-candidate linear pool
does not represent reselection of all 38 algorithms or data-cleaning rules.
"""

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from run_benchmark import (
    BASE,
    ROOT,
    SEED,
    candidates,
    ci,
    dump,
    fit,
    metrics,
    orig,
    predict,
    read,
    save,
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=ROOT / "results/diagnostics")
    ap.add_argument("--draws", type=int, default=1000)
    a = ap.parse_args()
    out = a.out.resolve()
    if out.exists():
        raise RuntimeError("Output must be new")
    out.mkdir(parents=True)
    p = read(BASE / "analysis_harmonized/results/main/analysis_panel.csv")
    source = read(BASE / "source_harmonized/kosis_ksic11_H1_2013_2025_panel.csv")
    regs = sorted(p.region_code.unique())
    cs = candidates()
    linear = cs[:11] + cs[32:]
    assert len(linear) == 17
    dump(
        {
            "B": a.draws,
            "seed": SEED,
            "pool": [c["name"] for c in linear],
            "resampling": "same sampled regions duplicated in train, validation, test; preprocessing and selection refitted",
            "fixed": "features, raw vintage, observed years; nonlinear candidates excluded",
            "prior_test_results_known": True,
        },
        out / "protocol_before_fit.json",
    )
    # Full raw reconstruction and exclusion ledger supplied by the original code.
    recon = out / "panel_reconstruction"
    recon.mkdir()
    rp, _ = orig.construct_panel(source, recon, True)
    pd.testing.assert_frame_equal(
        p, rp, check_dtype=False, check_exact=False, atol=1e-12, rtol=0
    )
    save(
        p.groupby(["split", "industry_code"]).size().reset_index(name="included_n"),
        out / "coverage_by_industry.csv",
    )
    # Held-out region: its employment excluded from peer features of all training rows.
    hold = []
    for r in regs:
        rd = out / "heldout_features" / r
        rd.mkdir(parents=True)
        q, _ = orig.construct_panel(source[source.region_code != r].copy(), rd, True)
        tr = q[q.split == "train"]
        va = q[q.split == "validation"]
        te = p[(p.split == "test") & (p.region_code == r)]
        tv = q[q.split != "test"]
        grid = []
        for c in cs[:11]:
            pp = predict(c, fit(c, tr), tr, va)
            grid.append((metrics(va, pp)["mae"], c))
        baseline = min(grid[:6], key=lambda z: z[0])[1]
        ridge = min(grid[6:], key=lambda z: z[0])[1]
        t = te.copy()
        t["heldout_baseline"] = predict(baseline, fit(baseline, tv), tv, te)
        t["heldout_ridge"] = predict(ridge, fit(ridge, tv), tv, te)
        t["selected_baseline"] = baseline["name"]
        t["selected_ridge"] = ridge["name"]
        hold.append(t)
    hold = pd.concat(hold, ignore_index=True)
    save(hold, out / "heldout_predictions.csv")
    save(
        ci(hold, ["heldout_ridge"], "heldout_baseline"), out / "heldout_comparisons.csv"
    )
    save(
        [
            {"model": n, **metrics(hold, hold[n])}
            for n in ["heldout_baseline", "heldout_ridge"]
        ],
        out / "heldout_metrics.csv",
    )
    # Explicit duplicated clusters retain region labels; no synthetic new region ID.
    byreg = {r: p[p.region_code == r] for r in regs}
    rng = np.random.default_rng(SEED)
    rows = []
    for b in range(a.draws):
        chosen = rng.choice(regs, size=len(regs), replace=True)
        d = pd.concat([byreg[r] for r in chosen], ignore_index=True)
        tr = d[d.split == "train"]
        va = d[d.split == "validation"]
        te = d[d.split == "test"]
        tv = d[d.split != "test"]
        grid = []
        for c in linear:
            pp = predict(c, fit(c, tr), tr, va)
            grid.append((metrics(va, pp)["mae"], c))
        best_base = min(grid[:6], key=lambda z: z[0])[1]
        best_ridge = min(grid[6:11], key=lambda z: z[0])[1]
        best_all = min(grid, key=lambda z: z[0])[1]
        ref = predict(best_base, fit(best_base, tv), tv, te)
        refmet = metrics(te, ref)
        row = {
            "replicate": b,
            "selected_baseline": best_base["name"],
            "selected_ridge": best_ridge["name"],
            "selected_linear17": best_all["name"],
        }
        for label, c in [("ridge5", best_ridge), ("linear17", best_all)]:
            pp = predict(c, fit(c, tv), tv, te)
            mm = metrics(te, pp)
            for metric in ["mae", "wmae"]:
                row[f"{label}_delta_{metric}"] = mm[metric] - refmet[metric]
        rows.append(row)
        if (b + 1) % 100 == 0:
            print("resampling", b + 1, flush=True)
    d = pd.DataFrame(rows)
    save(d, out / "reselection_replicates.csv")
    intervals = []
    for col in d:
        if "_delta_" in col:
            lo, hi = np.quantile(d[col], [0.025, 0.975])
            intervals.append(
                {"contrast": col, "ci_lo": float(lo), "ci_hi": float(hi), "B": len(d)}
            )
    save(intervals, out / "reselection_intervals.csv")
    freqs = []
    for col in ["selected_baseline", "selected_ridge", "selected_linear17"]:
        freqs += [
            {"pool": col, "model": m, "n": int(n), "pct": 100 * n / len(d)}
            for m, n in d[col].value_counts().items()
        ]
    save(freqs, out / "selection_frequencies.csv")
    dump(
        {"status": "complete", "draws": len(d), "heldout_n": len(hold)},
        out / "completion.json",
    )


if __name__ == "__main__":
    main()
