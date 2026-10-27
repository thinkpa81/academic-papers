#!/usr/bin/env python3
"""Analyze collected pilot records. Empty inputs yield no invented estimates."""

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--responses", type=Path, required=True)
    a.add_argument("--out", type=Path, required=True)
    x = a.parse_args()
    d = pd.read_csv(x.responses)
    x.out.mkdir(parents=True, exist_ok=True)
    if d.empty:
        (x.out / "status.json").write_text(
            json.dumps(
                {
                    "status": "not_evaluated",
                    "human_participants": 0,
                    "observations": 0,
                    "effects_estimated": False,
                },
                indent=2,
            )
        )
        print("No observations; no effects estimated.")
        return
    required = [
        "participant_code",
        "task_id",
        "condition",
        "intended_action_before_gate",
        "response_seconds_before_gate",
        "consent_recorded",
    ]
    if d[required].isna().any().any():
        raise ValueError(
            "Missing required observations; resolve against source records"
        )
    if d.duplicated(["participant_code", "task_id"]).any():
        raise ValueError("Duplicate participant-task observations")
    if not d.intended_action_before_gate.isin(["allow", "revise"]).all():
        raise ValueError("Actions must be allow/revise")
    if not d.consent_recorded.astype(str).str.lower().isin(["true", "1", "yes"]).all():
        raise ValueError("Consent record missing")
    if (d.response_seconds_before_gate <= 0).any():
        raise ValueError("Response times must be positive")
    schedule = pd.read_csv(ROOT / "field_study/counterbalanced_assignment.csv")
    assignment = d.merge(
        schedule,
        on=["participant_code", "task_id"],
        suffixes=("", "_planned"),
        validate="one_to_one",
    )
    if (
        len(assignment) != len(d)
        or not (assignment.condition == assignment.condition_planned).all()
    ):
        raise ValueError(
            "Observed condition differs from planned assignment; document protocol deviation before analysis"
        )
    key = pd.read_csv(ROOT / "field_study/assessor_answer_key.csv")
    z = d.merge(key, on="task_id", validate="many_to_one")
    z["correct"] = z.intended_action_before_gate == z.correct_action
    z.groupby(["participant_code", "condition"]).agg(
        n=("correct", "size"),
        accuracy=("correct", "mean"),
        median_seconds=("response_seconds_before_gate", "median"),
    ).reset_index().to_csv(
        x.out / "participant_condition_summary.csv", index=False, encoding="utf-8-sig"
    )
    z.to_csv(x.out / "scored_observations.csv", index=False, encoding="utf-8-sig")
    (x.out / "status.json").write_text(
        json.dumps(
            {
                "status": "pilot_descriptive",
                "human_participants": int(z.participant_code.nunique()),
                "observations": len(z),
                "independence_unit": "participant; repeated tasks retained",
                "causal_effect_claimed": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
