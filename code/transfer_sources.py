"""Adapt KOSIS employment and an external public macroeconomic data snapshot.

Adapters define data and measurement metadata. They do not alter the validator
or select observations based on test outcomes.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
from evidence_contract import digest, record_key
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
MACRO_SOURCE = ROOT / "raw/transfer_macrodata/macrodata.csv"
SERIES = ("realgdp", "realcons", "realinv")
UNIT = "100_log_ratio"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def make_card(*, dataset: str, entity: str, measure: str, model: str,
              target: int, step: int, source_sha: str, model_sha: str,
              input_values: dict, prediction: float, baseline: float,
              intercept: float, contributions: list[float], validation: dict) -> dict:
    return {
        "dataset_id": dataset, "entity_id": entity, "measure_id": measure,
        "model_id": model, "unit": UNIT, "mode": "retrospective",
        "source_sha256": source_sha, "model_sha256": model_sha,
        "input_sha256": digest(input_values), "input_ordinal": target - step,
        "target_ordinal": target, "step": step,
        "prediction": float(prediction), "baseline": float(baseline),
        "delta": float(prediction - baseline), "intercept": float(intercept),
        "contributions": list(map(float, contributions)),
        "validation_n": int(validation["n"]), "validation_mae": validation["mae"],
        "validation_baseline_mae": validation["baseline_mae"],
        "validation_delta": validation["delta"], "source_available": True,
        "historical_vintage_verified": False,
    }


def kosis_cards() -> tuple[list[dict], dict]:
    from run_registered_evaluation import registry

    registered = registry()
    cards = []
    source = ROOT / "raw/kosis_DT_1ES3B05J_H1_2013_2025_precision1_dom.json"
    for key, record in sorted(registered["records"].items()):
        region, industry, year, model = key.split(":")
        validation = record["validation"]
        cards.append(make_card(
            dataset="kosis_employment", entity=region, measure=industry, model=model,
            target=int(year) * 12 + 4, step=12, source_sha=sha(source),
            model_sha=registered["models"][model]["artifact_sha256"],
            input_values={"terms": record["terms"], "employment": record["employment"]},
            prediction=record["prediction"], baseline=record["baseline"],
            intercept=registered["models"][model]["intercept"],
            contributions=[term["contribution_logpoints"] for term in record["terms"].values()],
            validation={"n": validation["validation_cell_n"],
                        "mae": validation["aggregate_learned_mae"],
                        "baseline_mae": validation["aggregate_baseline_mae"],
                        "delta": validation["aggregate_mae_difference"]}))
    return cards, {"dataset_id": "kosis_employment", "step": 12, "unit": UNIT,
                   "base_forecasts": len(cards), "source_sha256": sha(source),
                   "source": "KOSIS DT_1ES3B05J, preserved KSIC11 first-half snapshot",
                   "reference_construction": "Refitted from the preserved analysis panel"}


def macro_cards(output: Path) -> tuple[list[dict], dict]:
    raw = pd.read_csv(MACRO_SOURCE)
    if len(raw) != 203 or raw.duplicated(["year", "quarter"]).any():
        raise ValueError("Unexpected macrodata shape or duplicate quarter")
    ordinal = raw.year.astype(int) * 12 + raw.quarter.astype(int) * 3
    if not np.all(np.diff(ordinal) == 3):
        raise ValueError("Nonconsecutive macrodata quarters")
    cards, prediction_rows, model_rows, split_rows = [], [], [], []
    source_sha = sha(MACRO_SOURCE)
    for series in SERIES:
        if not (raw[series] > 0).all():
            raise ValueError(f"Nonpositive source level: {series}")
        growth = 100.0 * np.log(raw[series] / raw[series].shift(1))
        panel = pd.DataFrame({"year": raw.year.astype(int), "quarter": raw.quarter.astype(int),
                              "ordinal": ordinal, "target": growth,
                              "lag1": growth.shift(1), "lag2": growth.shift(2)}).dropna()
        train = panel[panel.year <= 1989]
        validation = panel[(panel.year >= 1990) & (panel.year <= 1999)]
        development = panel[panel.year <= 1999]
        evaluation = panel[panel.year >= 2000]
        for split, frame in (("train", train), ("validation", validation), ("test", evaluation)):
            split_rows.append({"series": series, "split": split, "n": len(frame),
                               "first_ordinal": int(frame.ordinal.min()), "last_ordinal": int(frame.ordinal.max())})
        for model_name in ("ar1", "ridge_ar2_alpha1"):
            features = ["lag1"] if model_name == "ar1" else ["lag1", "lag2"]

            def fit(frame: pd.DataFrame):
                scaler = StandardScaler().fit(frame[features])
                estimator = LinearRegression() if model_name == "ar1" else Ridge(alpha=1.0)
                estimator.fit(scaler.transform(frame[features]), frame.target)
                return scaler, estimator

            train_scaler, train_model = fit(train)
            validation_predictions = train_model.predict(train_scaler.transform(validation[features]))
            vmae = float(np.mean(np.abs(validation.target.to_numpy() - validation_predictions)))
            vbmae = float(np.mean(np.abs(validation.target.to_numpy())))
            scaler, model = fit(development)
            transformed = scaler.transform(evaluation[features])
            predictions = model.predict(transformed)
            artifact = {"series": series, "model": model_name, "features": features,
                        "fit_through": "1999Q4", "intercept": float(model.intercept_),
                        "coefficients": model.coef_.tolist(), "center": scaler.mean_.tolist(),
                        "scale": scaler.scale_.tolist()}
            artifact_sha = digest(artifact)
            model_rows.append({**artifact, "sha256": artifact_sha})
            for i, row in enumerate(evaluation.itertuples()):
                contribution = (transformed[i] * model.coef_).tolist()
                inputs = {feature: float(getattr(row, feature)) for feature in features}
                card = make_card(
                    dataset="us_macrodata", entity="USA", measure=series, model=model_name,
                    target=int(row.ordinal), step=3, source_sha=source_sha, model_sha=artifact_sha,
                    input_values=inputs, prediction=float(predictions[i]), baseline=0.0,
                    intercept=float(model.intercept_), contributions=contribution,
                    validation={"n": len(validation), "mae": vmae, "baseline_mae": vbmae, "delta": vmae - vbmae})
                cards.append(card)
                prediction_rows.append({"series": series, "year": row.year, "quarter": row.quarter,
                                        "model": model_name, "actual": row.target,
                                        "prediction": float(predictions[i]), "baseline": 0.0,
                                        "reconstruction_error": float(predictions[i] - model.intercept_ - sum(contribution))})
    import json
    (output / "macro_models.json").write_text(json.dumps(model_rows, indent=2) + "\n", encoding="utf-8")
    predictions = pd.DataFrame(prediction_rows)
    predictions.to_csv(output / "macro_predictions.csv", index=False)
    pd.DataFrame(split_rows).to_csv(output / "macro_sample_counts.csv", index=False)
    metrics = predictions.groupby(["series", "model"]).apply(
        lambda x: pd.Series({"n": len(x), "mae": np.mean(abs(x.actual - x.prediction)),
                             "baseline_mae": np.mean(abs(x.actual - x.baseline))}), include_groups=False).reset_index()
    metrics.to_csv(output / "macro_forecast_diagnostics.csv", index=False)
    return cards, {"dataset_id": "us_macrodata", "step": 3, "unit": UNIT,
                   "raw_quarters": len(raw), "series": list(SERIES), "base_forecasts": len(cards),
                   "source_sha256": source_sha, "source": "statsmodels macrodata public-domain snapshot",
                   "source_commit": "d07a39609cdf57b6898bb9adb87e7821904482aa",
                   "original_acquisition": "2009-12-15 (provider documentation)",
                   "evaluation_period": "2000Q1–2009Q3", "historical_release_vintages_verified": False,
                   "purpose": "Cross-dataset technical transfer; no claim of best macroeconomic forecasting"}


def build_sources(output: Path) -> tuple[list[dict], dict, list[dict]]:
    kosis, kosis_metadata = kosis_cards()
    macro, macro_metadata = macro_cards(output)
    cards = kosis + macro
    context = {"policies": {d["dataset_id"]: {"unit": d["unit"], "step": d["step"]}
                            for d in (kosis_metadata, macro_metadata)},
               "records": {record_key(card): card for card in cards},
               "versions": {record_key(card): 1 for card in cards}}
    if len(context["records"]) != len(cards):
        raise ValueError("Duplicate forecast identity")
    return cards, context, [kosis_metadata, macro_metadata]
