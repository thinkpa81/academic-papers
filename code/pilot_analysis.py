"""Participant-level descriptive analysis; empty input never generates effects."""
import argparse
import json
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

def analyze(responses, out):
    d = pd.read_csv(responses); out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    if d.empty:
        report = {'status': 'not_evaluated', 'human_participants': 0,
                  'observations': 0, 'effects_estimated': False}
        (out / 'status.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        return report
    required = ['participant_code', 'task_id', 'condition', 'order',
                'intended_action_before_gate', 'response_seconds_before_gate',
                'reason_text', 'confidence_0_100', 'evidence_trust_1_7',
                'consent_recorded', 'record_source', 'recorded_at_utc']
    if not set(required) <= set(d) or d[required].isna().any().any():
        raise ValueError('Missing source observations')
    if d.duplicated(['participant_code', 'task_id']).any(): raise ValueError('Duplicate observations')
    if not d.intended_action_before_gate.isin(['allow', 'revise']).all(): raise ValueError('Invalid judgment')
    if not d.consent_recorded.astype(str).str.lower().isin(['true', '1', 'yes']).all(): raise ValueError('Consent missing')
    if not d.record_source.eq('human_observed').all(): raise ValueError('Only actual human observations are admissible')
    for key, lower, upper in [('response_seconds_before_gate', 0, np.inf),
                              ('confidence_0_100', 0, 100), ('evidence_trust_1_7', 1, 7)]:
        d[key] = pd.to_numeric(d[key], errors='raise')
        if not np.isfinite(d[key]).all() or (d[key] < lower).any() or (d[key] > upper).any(): raise ValueError('Invalid '+key)
    if (d.response_seconds_before_gate <= 0).any() or not d.evidence_trust_1_7.mod(1).eq(0).all(): raise ValueError('Invalid time or rating')
    schedule = pd.read_csv(ROOT / 'field_study/counterbalanced_assignment.csv')
    joined = d.merge(schedule, on=['participant_code', 'task_id'], how='left',
                     suffixes=('', '_planned'), validate='one_to_one', indicator=True)
    if not joined['_merge'].eq('both').all() or not joined.condition.eq(joined.condition_planned).all() or not joined.order.eq(joined.order_planned).all():
        raise ValueError('Assignment differs from the fixed schedule')
    z = d.merge(pd.read_csv(ROOT / 'field_study/assessor_answer_key.csv'), on='task_id', validate='many_to_one')
    z['correct'] = z.intended_action_before_gate.eq(z.correct_action)
    z['confidence_brier'] = (z.confidence_0_100 / 100 - z.correct.astype(int)) ** 2
    z['false_allow'] = ((z.correct_action == 'revise') & (z.intended_action_before_gate == 'allow')).astype(int)
    z['false_hold'] = ((z.correct_action == 'allow') & (z.intended_action_before_gate == 'revise')).astype(int)
    rows = []
    for (person, condition), g in z.groupby(['participant_code', 'condition']):
        valid = g.correct_action.eq('allow'); invalid = ~valid
        rows.append({'participant_code':person, 'condition':condition, 'n':len(g),
                     'accuracy':g.correct.mean(), 'median_seconds':g.response_seconds_before_gate.median(),
                     'false_allow_rate':g.loc[invalid,'false_allow'].mean(), 'false_hold_rate':g.loc[valid,'false_hold'].mean(),
                     'confidence_brier':g.confidence_brier.mean(), 'evidence_trust':g.evidence_trust_1_7.mean()})
    s = pd.DataFrame(rows); complete = z.groupby('participant_code').size().loc[lambda x:x == 16].index
    paired = []
    for person in complete:
        g = s[s.participant_code == person].set_index('condition'); r={'participant_code':person}
        for metric in ['accuracy','median_seconds','false_allow_rate','false_hold_rate','confidence_brier','evidence_trust']:
            r[metric+'_card_minus_table'] = g.loc['card',metric] - g.loc['table',metric]
        paired.append(r)
    z.to_csv(out/'scored_observations.csv',index=False,encoding='utf-8-sig')
    s.to_csv(out/'participant_condition_summary.csv',index=False,encoding='utf-8-sig')
    if paired: pd.DataFrame(paired).to_csv(out/'paired_participant_differences.csv',index=False,encoding='utf-8-sig')
    z.groupby(['condition','issue']).agg(n=('correct','size'),accuracy=('correct','mean'),
       median_seconds=('response_seconds_before_gate','median'),evidence_trust=('evidence_trust_1_7','mean')).reset_index().to_csv(out/'task_family_summary.csv',index=False,encoding='utf-8-sig')
    report={'status':'pilot_descriptive','human_participants':int(z.participant_code.nunique()),
            'complete_participants':len(complete),'observations':len(z),'effects_estimated':bool(paired),
            'independence_unit':'participant','causal_or_population_effect_claimed':False,
            'incomplete_participants_retained_descriptively':True,
            'note':'No row-independent significance test; trust is a single exploratory item.'}
    (out/'status.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--responses',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();print(json.dumps(analyze(a.responses,a.out),ensure_ascii=False))

if __name__=='__main__':main()
