from pathlib import Path
import hashlib
import json
import pandas as pd
HERE = Path(__file__).resolve().parent
ACTIVITIES = ['A', 'BTE', 'F', 'GTI', 'J', 'K', 'L', 'M_N', 'OTQ', 'RTU']
REGIONS = ['KR011', 'KR012', 'KR013', 'KR021', 'KR022', 'KR023', 'KR031', 'KR032', 'KR041', 'KR042', 'KR043', 'KR051', 'KR052', 'KR053', 'KR054', 'KR061', 'KR071']

def main():
    source = HERE / 'oecd_korea_emp_2_4_latest.csv'
    raw = pd.read_csv(source, low_memory=False)
    mask = (raw.MEASURE == 'EMP') & (raw.FREQ == 'A') & (raw.TERRITORIAL_LEVEL == 'TL3') & (raw.UNIT_MEASURE == 'PS') & (raw.UNIT_MULT == 0) & raw.REF_AREA.isin(REGIONS) & raw.ACTIVITY.isin(ACTIVITIES + ['_T'])
    f = raw.loc[mask].copy()
    if f.duplicated(['REF_AREA', 'ACTIVITY', 'TIME_PERIOD']).any():
        raise ValueError('Duplicate source keys')
    target = f[(f.TIME_PERIOD == 2024) & f.ACTIVITY.isin(ACTIVITIES)][['REF_AREA', 'ACTIVITY', 'TIME_PERIOD', 'OBS_VALUE']].rename(columns={'REF_AREA': 'region_code', 'ACTIVITY': 'industry_code', 'TIME_PERIOD': 'target_year', 'OBS_VALUE': 'employment'}).sort_values(['region_code', 'industry_code'])
    expected = {(r, a) for r in REGIONS for a in ACTIVITIES}
    if set(zip(target.region_code, target.industry_code)) != expected:
        raise ValueError('2024 coverage is not17x10')
    if target.employment.isna().any() or (target.employment <= 0).any():
        raise ValueError('Nonpositive/missing2024 target')
    path = HERE / 'oecd_v2_4_target2024_170.csv'
    target.to_csv(path, index=False, encoding='utf-8-sig')
    rows = []
    for year in [2022, 2023, 2024, 2025]:
        for region in REGIONS:
            g = f[(f.TIME_PERIOD == year) & (f.REF_AREA == region)].set_index('ACTIVITY')
            missing = [a for a in ACTIVITIES if a not in g.index or pd.isna(g.at[a, 'OBS_VALUE'])]
            total = float(g.at['_T', 'OBS_VALUE']) if '_T' in g.index else None
            subtotal = float(g[g.index.isin(ACTIVITIES)].OBS_VALUE.sum())
            difference = None if total is None else total - subtotal
            alert = bool(missing or total is None or abs(difference) > 1100)
            rows.append({'year': year, 'region_code': region, 'available_industry_cells': 10 - len(missing), 'missing_industries': '+'.join(missing), 'total_persons': total, 'available_industry_sum_persons': subtotal, 'total_minus_available_sum_persons': difference, 'reconciliation_alert': alert, 'diagnostic_rounding_tolerance_persons': 1100, 'diagnostic_scope': 'not a population estimate or correction; no missing imputation'})
    checks = pd.DataFrame(rows)
    checks.to_csv(HERE / 'oecd_v2_4_coverage_total_checks.csv', index=False, encoding='utf-8-sig')
    checks[(checks.year == 2025) & checks.reconciliation_alert].to_csv(HERE / 'oecd_v2_4_2025_source_anomalies.csv', index=False, encoding='utf-8-sig')
    output = {'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'target_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'target_rows': len(target), 'exact_filter': {'MEASURE': 'EMP', 'FREQ': 'A', 'TERRITORIAL_LEVEL': 'TL3', 'UNIT_MEASURE': 'PS', 'UNIT_MULT': 0}, 'target_reference_period': '2024H1 independently reconciled with KOSIS KSIC10', '2025_status': 'HOLD: missing Seoul A and anomalous Seoul total; do not substitute or impute', 'model_performance_evaluated': False}
    (HERE / 'normalization_checks.json').write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(output, ensure_ascii=False, indent=2))
if __name__ == '__main__':
    main()
