"""Prepare a balanced eight-person pilot without participant observations."""
import csv
import hashlib
import json
import random
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIELDS = ['participant_code', 'task_id', 'condition', 'order',
          'intended_action_before_gate', 'response_seconds_before_gate',
          'reason_text', 'confidence_0_100', 'evidence_trust_1_7',
          'consent_recorded', 'record_source', 'recorded_at_utc']

def write_csv(path, rows, fields=None):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields or list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

def main():
    out = ROOT / 'field_study'
    out.mkdir(exist_ok=True)
    response = out / 'responses_EMPTY.csv'
    if response.exists() and len(list(csv.DictReader(response.open(encoding='utf-8-sig')))):
        raise ValueError('Refusing to overwrite collected observations')
    src = ROOT / 'support/model_swap_addendum/frozen/protocol_and_cases.json'
    controls = [c for c in json.loads(src.read_text())['cases']
                if c['scope'] == 'coherent_control' and c['model'] == 'ridge_alpha1000']
    controls.sort(key=lambda c: c['case_id'])
    random.Random(20261028).shuffle(controls)
    tasks, answers, provenance = [], [], []
    issues = ['consistent', 'stale_review', 'validation_mismatch', 'coefficient_mismatch']
    for i, case in enumerate(controls[:16]):
        card = case['fixture']['card']; kind = i // 4
        n = card['prior_validation']['validation_year_n']
        coef = next(v['coefficient'] for v in card['model_artifact_snapshot']['parameters']
                    if v['feature'] == 'num__own_growth')
        prediction = card['learned_comparator']['logpoints']
        baseline = card['default_estimate']['logpoints']
        delta = card['prior_validation']['aggregate_mae_difference']
        groups = [
            {'title': '예측 대상과 비교', 'items': [
                ['지역과 산업', card['region_name'] + ' / ' + card['industry_code']],
                ['입력과 목표', '2024년 상반기 → 2025년 상반기'],
                ['기준 예측', f'{baseline:+.3f} 로그포인트'],
                ['릿지 예측', f'{prediction:+.3f} 로그포인트'],
                ['예측편차', f'{prediction-baseline:+.3f} 로그포인트']]},
            {'title': '검증근거', 'items': [
                ['검증기간', '2020~2022년 가용 관측'],
                ['화면의 검증사례 수', str(n + (1 if kind == 2 else 0))],
                ['등록자료의 검증사례 수', str(n)],
                ['검증 MAE 차이', '산출 불가' if delta is None else f'{delta:+.3f} 로그포인트']]},
            {'title': '근거 판본과 모형 대조', 'items': [
                ['현재 근거 판본', 'R02'],
                ['검토기록이 참조한 판본', 'R01' if kind == 1 else 'R02'],
                ['제출된 최근 변동 계수', f'{coef + (0.5 if kind == 3 else 0):+.6f}'],
                ['등록된 최근 변동 계수', f'{coef:+.6f}']]},
            {'title': '이용 범위', 'items': [
                ['자료', '2026년 9월 확보한 개정 KOSIS 집계자료'],
                ['검토 목적', '과거 예측에 대한 연구용 검토'],
                ['운영 예측과 정책 자동조치', '허용하지 않음'],
                ['해석', '순고용변동은 채용·훈련 수요와 구분하여 검토']]}]
        task_id = f'T{i+1:02d}'
        tasks.append({'task_id': task_id, 'groups': groups,
                      'question': '제시된 근거의 일치 여부를 확인했을 때 연구용 검토를 완료할 수 있습니까?',
                      'source': '실제 예측 수치에 실험용 검토 판본과 일부 결함을 구성한 과업'})
        answers.append({'task_id': task_id, 'issue': issues[kind],
                        'correct_action': 'allow' if kind == 0 else 'revise',
                        'critical_evidence': ['판본·사례 수·모형계수 일치', 'R01과 R02 불일치',
                                              '화면과 등록자료의 사례 수 불일치', '제출계수와 등록계수 불일치'][kind],
                        'follow_up': '연구용 검토 완료' if kind == 0 else '근거를 보완하고 현재 판본으로 재검토'})
        provenance.append({'task_id': task_id, 'source_case_id': case['case_id'],
                           'prediction': prediction, 'baseline': baseline,
                           'source_validation_n': n, 'source_coefficient': coef,
                           'synthetic_change': issues[kind], 'human_observation': False})
    assignments = []
    for p in range(8):
        order = list(range(16)); random.Random(20261028 + p).shuffle(order)
        for position, i in enumerate(order, 1):
            assignments.append({'participant_code': f'P{p+1:02d}', 'order': position,
                                'task_id': tasks[i]['task_id'],
                                'condition': 'table' if (i % 4 + p) % 4 < 2 else 'card'})
    (out / 'tasks.json').write_text(json.dumps(tasks, ensure_ascii=False, indent=2), encoding='utf-8')
    (out / 'task_provenance.json').write_text(json.dumps(provenance, ensure_ascii=False, indent=2), encoding='utf-8')
    write_csv(out / 'assessor_answer_key.csv', answers)
    write_csv(out / 'counterbalanced_assignment.csv', assignments)
    write_csv(response, [], FIELDS)
    write_csv(out / 'ratings_EMPTY.csv', [], ['participant_code', 'task_id', 'rater_id', 'evidence_score_0_2'])
    report = {'planned_participants': 8, 'tasks': 16, 'planned_assignments': 128,
              'actual_participants': 0, 'actual_observations': 0,
              'conditions': ['table', 'card'], 'source_sha256': hashlib.sha256(src.read_bytes()).hexdigest(),
              'purpose': 'exploratory usability pilot; not a powered confirmatory study',
              'generated_responses': False}
    (out / 'preparation_status.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))

if __name__ == '__main__': main()
