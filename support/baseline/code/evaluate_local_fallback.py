from __future__ import annotations

import argparse
import hashlib
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dump_json(value: object, path: Path) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False),
        encoding="utf-8",
    )


def write_csv(frame: pd.DataFrame, path: Path) -> None:
    frame.to_csv(path, index=False, encoding="utf-8-sig", float_format="%.15g")


def check_frame(frame: pd.DataFrame, spec: dict, split: str) -> None:
    cols = list(
        dict.fromkeys(
            spec["row_keys"]
            + [spec["outcome"], spec["weight"], spec["baseline"], spec["learned"]]
        )
    )
    missing = set(cols).difference(frame.columns)
    if missing:
        raise ValueError(f"Missing {split} columns: {sorted(missing)}")
    if frame[spec["row_keys"]].isna().any().any():
        raise ValueError(f"Missing {split} row key")
    if frame.duplicated(spec["row_keys"]).any():
        raise ValueError(f"Duplicate {split} row keys")
    if len(frame) != spec[f"expected_{split}_rows"]:
        raise ValueError(f"Unexpected {split} row count: {len(frame)}")
    if set(frame.target_year) != set(spec[f"{split}_years"]):
        raise ValueError(f"Unexpected {split} years")


def metrics(frame: pd.DataFrame, strategy: str, spec: dict) -> dict:
    truth = frame[spec["outcome"]].to_numpy(dtype=float)
    pred = frame[f"prediction_{strategy}"].to_numpy(dtype=float)
    weight = frame[spec["weight"]].to_numpy(dtype=float)
    residual = truth - pred
    baseline_loss = np.abs(truth - frame.prediction_baseline.to_numpy(dtype=float))
    ridge_loss = np.abs(truth - frame.prediction_ridge.to_numpy(dtype=float))
    adopted = int(frame[f"adopt_{strategy}"].sum())
    return {
        "strategy": strategy,
        "n": len(frame),
        "adoption_n": adopted,
        "adoption_pct": 100.0 * adopted / len(frame),
        "MAE": float(np.abs(residual).mean()),
        "RMSE": float(np.sqrt(np.square(residual).mean())),
        "wMAE": float(np.average(np.abs(residual), weights=weight)),
        "delta_MAE_vs_baseline": float((np.abs(residual) - baseline_loss).mean()),
        "delta_MAE_vs_ridge": float((np.abs(residual) - ridge_loss).mean()),
        "worse_than_baseline_n": int((np.abs(residual) > baseline_loss).sum()),
        "worse_than_baseline_pct": float(
            100.0 * (np.abs(residual) > baseline_loss).mean()
        ),
    }


def block_bootstrap(
    frame: pd.DataFrame, spec: dict
) -> tuple[pd.DataFrame, pd.DataFrame]:
    boot = spec["bootstrap"]
    clusters = sorted(frame[boot["cluster"]].unique())
    truth = frame[spec["outcome"]].to_numpy(dtype=float)
    weights = frame[spec["weight"]].to_numpy(dtype=float)
    indices = [
        np.flatnonzero(frame[boot["cluster"]].to_numpy() == cluster)
        for cluster in clusters
    ]
    group_n = np.asarray([len(index) for index in indices], dtype=float)
    group_weight = np.asarray([weights[index].sum() for index in indices])
    abs_errors = {
        strategy: np.abs(truth - frame[f"prediction_{strategy}"].to_numpy(dtype=float))
        for strategy in spec["strategies"]
    }
    group_sums = {
        strategy: np.asarray([error[index].sum() for index in indices])
        for strategy, error in abs_errors.items()
    }
    group_weighted_sums = {
        strategy: np.asarray(
            [(error[index] * weights[index]).sum() for index in indices]
        )
        for strategy, error in abs_errors.items()
    }
    rng = np.random.default_rng(boot["seed"])
    drawn = rng.integers(0, len(clusters), size=(boot["repetitions"], len(clusters)))
    counts = np.stack([np.bincount(row, minlength=len(clusters)) for row in drawn])
    replicate_rows = []
    interval_rows = []
    for strategy in spec["strategies"]:
        for reference in boot["differences_vs"]:
            if strategy == reference:
                continue
            for metric in boot["metrics"]:
                if metric == "MAE":
                    differences = group_sums[strategy] - group_sums[reference]
                    denominator = group_n
                else:
                    differences = (
                        group_weighted_sums[strategy] - group_weighted_sums[reference]
                    )
                    denominator = group_weight
                estimates = (counts @ differences) / (counts @ denominator)
                lo, hi = np.quantile(estimates, [0.025, 0.975])
                point = differences.sum() / denominator.sum()
                interval_rows.append(
                    {
                        "strategy": strategy,
                        "reference": reference,
                        "metric": metric,
                        "difference": float(point),
                        "ci_low": float(lo),
                        "ci_high": float(hi),
                        "clusters": len(clusters),
                        "repetitions": boot["repetitions"],
                        "seed": boot["seed"],
                    }
                )
                replicate_rows.extend(
                    {
                        "replicate": i + 1,
                        "strategy": strategy,
                        "reference": reference,
                        "metric": metric,
                        "difference": float(value),
                    }
                    for i, value in enumerate(estimates)
                )
    return pd.DataFrame(interval_rows), pd.DataFrame(replicate_rows)


def make_report(
    summary: dict, pooled: pd.DataFrame, yearly: pd.DataFrame, intervals: pd.DataFrame
) -> str:
    p = pooled.set_index("strategy")
    lines = [
        "# 지역–산업별 검증기록에 따른 기준모형 대체 규칙의 사후 기술평가",
        "",
        "## 연구 질문과 분석 성격",
        "",
        "본 평가는 동일한 모형을 모든 지역–산업에 적용하는 대신, 이전 검증근거가 일정 조건을 충족하는 경우에만 릿지 예측을 사용하고 그 밖에서는 기준모형으로 대체하는 규칙을 비교한다. 기존 연도별 대표 모형 교체규칙과 달리, 카드에 연결된 지역–산업별 검증기록의 사용을 평가한다.",
        "평가기간의 결과를 기존 원고에서 이미 검토한 후 수행한 사후 기술평가이다. 규칙 명세 파일을 이번 추가 계산 전에 저장하였으나 외부 사전등록이나 미관찰 평가자료를 이용한 확증분석은 아니다. 사용자·정책효과는 평가하지 않았다.",
        "",
        "## 자료 및 고정 규칙",
        "",
        f"검증자료 {summary['validation_n']}행(2020~2022년), 평가자료 {summary['test_n']}행(2023~2025년)을 사용하였다. 검증 예측은 2016~2019년 훈련모형, 평가 예측은 훈련·검증기간을 합쳐 재적합한 기존 모형의 저장값이다. 기준모형은 전체 과거평균, 학습모형은 릿지 α=1,000으로 고정하였다. 이번 분석에서 모형을 다시 학습하거나 성능에 따라 후보를 교체하지 않았다.",
        "G2는 동일 지역–산업에서 유효 검증사례가 2개 이상이고 검증 MAE의 릿지−기준모형 차이가 0 이하일 때 릿지를 사용한다. G3는 최소 사례 수를 3개로 정한다. 미충족 사례는 제외하지 않고 기준모형으로 대체한다. 대체 규칙은 2020~2022년 기록만으로 고정하며 2023~2025년 실제값을 결정에 사용하지 않는다.",
        f"검증 비교에 필요한 값이 비유한인 행은 쌍 단위로 제외하고 별도 기록한다. 검증기록이 없거나 최소 사례 수를 충족하지 못하면 대체한다. 평가자료의 실제값·두 모형 예측·기준고용에 결측 또는 비유한 값이 있거나 기준고용이 양수가 아니면 행을 삭제하지 않고 분석을 중단하도록 하였다. 이번 실행에서 제외된 검증행은 {summary['excluded_validation_n']}개이다.",
        "",
        "## 전체 표본 결과",
        "",
        "| 규칙 | 평가 n | 릿지 사용 n(%) | MAE | RMSE | 고용가중 MAE | 기준 대비 ΔMAE | 전체 릿지 대비 ΔMAE |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    labels = {
        "baseline": "전체 과거평균",
        "ridge": "전체 릿지",
        "G2": "G2 대체 규칙",
        "G3": "G3 대체 규칙",
    }
    for name, row in p.iterrows():
        lines.append(
            f"| {labels[name]} | {int(row.n)} | {int(row.adoption_n)} ({row.adoption_pct:.2f}%) | {row.MAE:.6f} | {row.RMSE:.6f} | {row.wMAE:.6f} | {row.delta_MAE_vs_baseline:.6f} | {row.delta_MAE_vs_ridge:.6f} |"
        )
    lines += [
        "",
        "단위: 로그포인트. ΔMAE<0은 행에 기재한 규칙의 오차가 비교대상보다 낮음을 뜻한다. 모든 규칙은 동일한 428개 평가행으로 비교하였다.",
        "",
        f"G2와 G3의 릿지 사용률은 각각 {p.loc['G2', 'adoption_pct']:.2f}%와 {p.loc['G3', 'adoption_pct']:.2f}%였다. 전체 기준모형 대비 MAE 차이는 각각 {p.loc['G2', 'delta_MAE_vs_baseline']:.6f}, {p.loc['G3', 'delta_MAE_vs_baseline']:.6f} 로그포인트이며 전체 릿지 대비 차이는 각각 {p.loc['G2', 'delta_MAE_vs_ridge']:.6f}, {p.loc['G3', 'delta_MAE_vs_ridge']:.6f}였다. 고용가중 MAE는 G2 {p.loc['G2', 'wMAE']:.6f}, G3 {p.loc['G3', 'wMAE']:.6f}로 기준모형 {p.loc['baseline', 'wMAE']:.6f}보다 높았다. 두 규칙의 국소 검증근거에 따른 대체가 전체 릿지의 정확도를 개선한다는 결과는 얻지 못하였다.",
        "",
        "## 지역 블록 차이구간",
        "",
        "동일 지역의 산업·연도 관측을 함께 재표집하여 2,000회 백분위 구간을 계산하였다. 저장 예측과 대체 결정은 고정하였으므로 모형 적합·선정의 불확실성이나 관찰하지 않은 연도의 공통 충격을 모두 포괄하지 않는다. 다중비교 보정이나 확증적 유의성 검정은 수행하지 않았다.",
        "",
        "| 규칙 | 비교대상 | 지표 | 차이 | 95% 구간 |",
        "|---|---|---|---:|---|",
    ]
    for row in intervals.itertuples():
        if row.strategy not in ["G2", "G3"]:
            continue
        lines.append(
            f"| {row.strategy} | {labels[row.reference]} | {row.metric} | {row.difference:.6f} | [{row.ci_low:.6f}, {row.ci_high:.6f}] |"
        )
    lines += [
        "",
        "## 연도별 결과",
        "",
        "| 연도 | 규칙 | n | 릿지 사용 n | MAE | 고용가중 MAE |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for row in yearly.itertuples():
        lines.append(
            f"| {row.group_value} | {labels[row.strategy]} | {row.n} | {row.adoption_n} | {row.MAE:.6f} | {row.wMAE:.6f} |"
        )
    lines += [
        "",
        "## 해석과 한계",
        "",
        "이 비교는 이전 검증근거에 따라 예측을 대체했을 때의 손실과 사용범위만을 측정한다. 결과가 유리하더라도 해당 규칙의 일반적 최적성, 담당자의 판단품질, 자동화 편향 감소 또는 정책성과를 입증하지 않는다. 검증사례가 지역–산업별 최대 3개로 적고 같은 검증자료가 원래 모형선정에도 사용되어 국소 오차 순위가 불안정할 수 있다. 또한 검증 당시 모형과 평가 당시 재적합 모형은 학습자료가 다르므로 국소적 우위가 그대로 유지된다고 가정할 수 없다.",
        "두 규칙을 모두 보고하며 더 좋은 결과의 규칙을 최종 운영기준으로 선정하지 않았다. 과거 개정계열의 회고적 결과이므로 공표 당시 자료를 사용한 전향평가와 기관의 업무평가는 별도로 수행해야 한다.",
        "",
        "## 재현",
        "",
        "코드: `code/evaluate_local_fallback.py`. 의존성: Python, NumPy, pandas. 원자료 다운로드·모형 재학습·네트워크 접근 없이 실행한다. `--source-root`는 analysis_harmonized 폴더가 있는 v11 패키지 최상위 경로, `--output-dir`은 별도 결과 폴더, `--spec`은 이 분석의 규칙 명세 JSON 경로이다. `--spec`을 생략하면 코드의 상위 패키지 additional_analysis 폴더에서 명세를 읽는다.",
        "```bash",
        "python code/evaluate_local_fallback.py --source-root base_v11 --output-dir reproduced_fallback_new --spec additional_analysis/local_fallback_specification_release.json",
        "```",
        "입력 파일은 읽기 전용으로 처리하며 실행 전후 SHA-256 일치를 확인한다. 규칙 명세, 검증에 따른 채택결정, 평가행별 예측·손실, 집단별 결과, 지역 블록 차이구간과 반복표집값, 실행환경 및 해시를 결과 폴더에 보존한다.",
    ]
    return "\n".join(lines) + "\n"


def validate_paths(source: Path, output: Path, spec_path: Path) -> None:
    if not source.is_dir():
        raise ValueError(f"Source package directory does not exist: {source}")
    if not spec_path.is_file():
        raise ValueError(f"Rule specification does not exist: {spec_path}")
    if output.is_relative_to(source) or source.is_relative_to(output):
        raise ValueError("Source package and output directory must not overlap")
    if spec_path.is_relative_to(output):
        raise ValueError("Keep the rule specification outside the new output directory")
    if output.exists():
        if not output.is_dir():
            raise ValueError(f"Output path is not a directory: {output}")
        if any(output.iterdir()):
            raise ValueError(
                "Use a new empty output directory to preserve previous results"
            )


def validate_source_files(source: Path, spec: dict) -> None:
    required = {
        "analysis_harmonized/results/main/selection_before_test.json",
        "analysis_harmonized/results/main/validation_predictions.csv",
        "analysis_harmonized/results/main/test_predictions.csv",
    }
    if not isinstance(spec.get("source_files"), dict):
        raise ValueError("Rule specification must contain a source_files hash mapping")
    missing = required.difference(spec["source_files"])
    if missing:
        raise ValueError(
            f"Required source files are missing from the hash mapping: {sorted(missing)}"
        )
    for name in spec["source_files"]:
        relative = Path(name)
        path = (source / relative).resolve()
        if relative.is_absolute() or not path.is_relative_to(source):
            raise ValueError(
                f"Source file must remain inside the source package: {name}"
            )
        if not path.is_file():
            raise ValueError(f"Required source file does not exist: {path}")


def run(source: Path, output: Path, spec_path: Path) -> None:
    source = source.expanduser().resolve()
    output = output.expanduser().resolve()
    spec_path = spec_path.expanduser().resolve()
    validate_paths(source, output, spec_path)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    if not isinstance(spec, dict):
        raise ValueError("Rule specification must be a JSON object")
    validate_source_files(source, spec)
    before = {name: sha256(source / name) for name in spec["source_files"]}
    if before != spec["source_files"]:
        raise ValueError("Source hashes do not match the recorded specification")
    main = source / "analysis_harmonized/results/main"
    selection = json.loads((main / "selection_before_test.json").read_text())
    if (
        selection["service_default_baseline"] != spec["baseline"]
        or selection["learned_companion"] != spec["learned"]
    ):
        raise ValueError("Selected models do not match specification")
    output.mkdir(parents=True, exist_ok=True)

    validation = pd.read_csv(
        main / "validation_predictions.csv",
        encoding="utf-8-sig",
        dtype={"region_code": str, "industry_code": str},
    )
    check_frame(validation, spec, "validation")
    val_cols = [spec["outcome"], spec["baseline"], spec["learned"]]
    usable = np.isfinite(validation[val_cols].to_numpy(dtype=float)).all(axis=1)
    write_csv(validation.loc[~usable], output / "excluded_validation_rows.csv")
    complete = validation.loc[usable].copy()
    complete["baseline_absolute_error"] = np.abs(
        complete[spec["outcome"]] - complete[spec["baseline"]]
    )
    complete["ridge_absolute_error"] = np.abs(
        complete[spec["outcome"]] - complete[spec["learned"]]
    )
    keys = spec["group_keys"]
    gate = complete.groupby(keys, as_index=False, sort=True).agg(
        n_val=(spec["outcome"], "size"),
        validation_baseline_MAE=("baseline_absolute_error", "mean"),
        validation_ridge_MAE=("ridge_absolute_error", "mean"),
        validation_first_year=("target_year", "min"),
        validation_last_year=("target_year", "max"),
    )
    gate["validation_delta_MAE"] = (
        gate.validation_ridge_MAE - gate.validation_baseline_MAE
    )
    for rule in spec["rules"]:
        name = rule["id"]
        gate[f"adopt_{name}"] = (gate.n_val >= rule["minimum_validation_n"]) & (
            gate.validation_delta_MAE <= rule["max_validation_delta_mae"]
        )
    write_csv(gate, output / "validation_only_decisions_before_test_merge.csv")
    dump_json(
        {
            "saved_utc": datetime.now(timezone.utc).isoformat(),
            "specification_sha256": sha256(spec_path),
            "validation_source_sha256": sha256(main / "validation_predictions.csv"),
            "decisions_sha256": sha256(
                output / "validation_only_decisions_before_test_merge.csv"
            ),
            "test_outcomes_used_to_construct_decisions": False,
        },
        output / "decision_freeze_manifest.json",
    )

    test = pd.read_csv(
        main / "test_predictions.csv",
        encoding="utf-8-sig",
        dtype={"region_code": str, "industry_code": str},
    )
    check_frame(test, spec, "test")
    test_cols = [spec["outcome"], spec["baseline"], spec["learned"], spec["weight"]]
    if (
        not np.isfinite(test[test_cols].to_numpy(dtype=float)).all()
        or not (test[spec["weight"]] > 0).all()
    ):
        raise ValueError(
            "Incomplete or nonpositive-weight test row; no rows were dropped"
        )
    test = test.merge(gate, on=keys, how="left", validate="many_to_one", sort=False)
    test["n_val"] = test.n_val.fillna(0).astype(int)
    test["prediction_baseline"] = test[spec["baseline"]]
    test["prediction_ridge"] = test[spec["learned"]]
    test["adopt_baseline"] = False
    test["adopt_ridge"] = True
    for rule in spec["rules"]:
        name = rule["id"]
        test[f"adopt_{name}"] = (
            (test.n_val >= rule["minimum_validation_n"])
            & np.isfinite(test.validation_delta_MAE)
            & (test.validation_delta_MAE <= rule["max_validation_delta_mae"])
        )
        test[f"prediction_{name}"] = np.where(
            test[f"adopt_{name}"], test.prediction_ridge, test.prediction_baseline
        )
        test[f"decision_reason_{name}"] = np.select(
            [
                test.n_val.eq(0),
                test.n_val.lt(rule["minimum_validation_n"]),
                ~np.isfinite(test.validation_delta_MAE),
                test.validation_delta_MAE.gt(rule["max_validation_delta_mae"]),
            ],
            [
                "no_valid_local_validation",
                "too_few_local_validation_pairs",
                "unavailable_validation_difference",
                "ridge_validation_MAE_exceeds_baseline",
            ],
            default="adopt_ridge",
        )
    if (
        len(test) != spec["expected_test_rows"]
        or not (test.adopt_G3 <= test.adopt_G2).all()
    ):
        raise AssertionError("Fixed cohort or nested-rule invariant failed")
    for strategy in spec["strategies"]:
        test[f"absolute_error_{strategy}"] = np.abs(
            test[spec["outcome"]] - test[f"prediction_{strategy}"]
        )
        test[f"squared_error_{strategy}"] = np.square(
            test[spec["outcome"]] - test[f"prediction_{strategy}"]
        )
    test["employment_size"] = np.where(
        test[spec["weight"]] < 10000, "below_10000", "at_least_10000"
    )
    write_csv(test, output / "evaluation_predictions_decisions_and_losses.csv")
    write_csv(
        test[
            keys + ["n_val", "validation_delta_MAE", "adopt_G2", "adopt_G3"]
        ].drop_duplicates(),
        output / "evaluated_region_industry_decisions.csv",
    )
    pooled = pd.DataFrame(
        [metrics(test, strategy, spec) for strategy in spec["strategies"]]
    )
    write_csv(pooled, output / "pooled_metrics.csv")
    grouped = []
    for column in ["target_year", "region_code", "industry_code", "employment_size"]:
        for value, subset in test.groupby(column, sort=True):
            for strategy in spec["strategies"]:
                grouped.append(
                    {
                        "group_type": column,
                        "group_value": str(value),
                        **metrics(subset, strategy, spec),
                    }
                )
    grouped_frame = pd.DataFrame(grouped)
    write_csv(grouped_frame, output / "grouped_metrics.csv")
    yearly = grouped_frame[grouped_frame.group_type.eq("target_year")]
    write_csv(yearly, output / "yearly_metrics.csv")
    counts = test.groupby("n_val", as_index=False).agg(
        evaluation_rows=("target_year", "size")
    )
    group_counts = (
        test[keys + ["n_val"]]
        .drop_duplicates()
        .groupby("n_val", as_index=False)
        .size()
        .rename(columns={"size": "region_industry_groups"})
    )
    write_csv(
        counts.merge(group_counts, on="n_val", validate="one_to_one"),
        output / "validation_coverage_counts.csv",
    )
    reasons = pd.concat(
        [
            test.groupby(f"decision_reason_{rule['id']}", as_index=False)
            .size()
            .rename(columns={f"decision_reason_{rule['id']}": "reason", "size": "n"})
            .assign(rule=rule["id"])
            for rule in spec["rules"]
        ],
        ignore_index=True,
    )
    write_csv(reasons, output / "decision_reason_counts.csv")
    intervals, replicates = block_bootstrap(test, spec)
    write_csv(intervals, output / "region_block_intervals.csv")
    write_csv(replicates, output / "region_block_replicates.csv")
    after = {name: sha256(source / name) for name in spec["source_files"]}
    if before != after:
        raise RuntimeError("Source files changed during analysis")
    summary = {
        "analysis_id": spec["analysis_id"],
        "completed_utc": datetime.now(timezone.utc).isoformat(),
        "status": spec["status"],
        "validation_n": len(validation),
        "excluded_validation_n": int((~usable).sum()),
        "test_n": len(test),
        "test_region_n": int(test.region_code.nunique()),
        "test_region_industry_n": int(len(test[keys].drop_duplicates())),
        "pooled_metrics": pooled.to_dict(orient="records"),
        "source_hashes_unchanged": before == after,
        "source_files": after,
        "specification_sha256": sha256(spec_path),
        "code_sha256": sha256(Path(__file__)),
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
        },
        "interpretation": spec["interpretation"],
    }
    dump_json(summary, output / "local_fallback_summary.json")
    (output / "local_fallback_report_ko.md").write_text(
        make_report(summary, pooled, yearly, intervals), encoding="utf-8"
    )
    print(pooled.to_string(index=False))
    print(f"Source files unchanged: {before == after}")
    print(f"Report: {output / 'local_fallback_report_ko.md'}")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate the fixed G2/G3 local fallback rules using preserved predictions."
    )
    parser.add_argument(
        "--source-root", "--source", dest="source_root", type=Path, required=True
    )
    parser.add_argument(
        "--output-dir", "--output", dest="output_dir", type=Path, required=True
    )
    parser.add_argument(
        "--spec",
        type=Path,
        default=Path(__file__).resolve().parents[1]
        / "additional_analysis/local_fallback_specification_release.json",
    )
    args = parser.parse_args(argv)
    try:
        run(args.source_root, args.output_dir, args.spec)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
