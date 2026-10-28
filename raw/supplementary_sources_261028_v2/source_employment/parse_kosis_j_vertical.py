from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import pandas as pd
from parse_kosis_employment import expand, REGIONS, RANGES, GROUPS
HERE = Path(__file__).resolve().parent

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('input', type=Path)
    ap.add_argument('--prefix', default='kosis_newJ_2025H1H2')
    a = ap.parse_args()
    dest = HERE / a.input.name
    if dest.resolve() != a.input.resolve():
        shutil.copy2(a.input, dest)
    source = json.loads(dest.read_text(encoding='utf-8'))
    grid = expand(source['rows'])
    periods = grid[0]
    measures = grid[1]
    region = ''
    rows = []
    for row in grid[2:]:
        if len(row) < 2:
            continue
        if row[0]:
            region = row[0]
        if region not in REGIONS:
            continue
        label = row[1]
        m = re.search('\\(([^()]*)\\)$', label)
        section = '_T' if label == '계' else RANGES.get(re.sub('\\s', '', m.group(1))) if m else None
        if not section:
            continue
        for i in range(2, len(periods)):
            if '취업자' not in measures[i]:
                continue
            raw = row[i]
            numeric = raw.replace(',', '')
            valid = bool(re.fullmatch('[+-]?\\d+(?:\\.\\d+)?', numeric))
            rows.append({'region_code': REGIONS[region], 'region_name_ko': region, 'period': periods[i], 'year': int(periods[i][:4]), 'section': section, 'raw_cell': raw, 'employment_persons': float(numeric) * 1000 if valid else float('nan'), 'rse_flag': row[i + 1] if i + 1 < len(row) and 'RSE' in measures[i + 1] else '', 'source_uri': source['url']})
    f = pd.DataFrame(rows)
    if f.duplicated(['region_code', 'period', 'section']).any():
        raise ValueError('Duplicate keys')
    f.to_csv(HERE / (a.prefix + '_sections.csv'), index=False, encoding='utf-8-sig')
    aggregates = []
    for (region, period), g in f.groupby(['region_code', 'period']):
        d = g.set_index('section')
        for activity, components in GROUPS.items():
            h = d.loc[components]
            complete = bool(h.employment_persons.notna().all())
            aggregates.append({'region_code': region, 'period': period, 'year': int(period[:4]), 'industry_code': activity, 'employment_persons_kosis': h.employment_persons.sum() if complete else float('nan'), 'complete_components': complete, 'missing_components': '+'.join(h[h.employment_persons.isna()].index), 'source_raw_values': '|'.join(h.raw_cell)})
    panel = pd.DataFrame(aggregates)
    panel.to_csv(HERE / (a.prefix + '_panel.csv'), index=False, encoding='utf-8-sig')
    official = pd.read_csv(HERE / 'oecd_v2_4_2022_2025_panel.csv')
    joined = panel.merge(official[['region_code', 'industry_code', 'year', 'employment_persons']], on=['region_code', 'industry_code', 'year'], how='left').rename(columns={'employment_persons': 'employment_persons_oecd'})
    joined['difference_persons'] = joined.employment_persons_oecd - joined.employment_persons_kosis
    joined.to_csv(HERE / (a.prefix + '_vs_oecd.csv'), index=False, encoding='utf-8-sig')
    summary = joined.groupby('period').agg(total=('region_code', 'size'), complete=('complete_components', 'sum'), both_numeric=('difference_persons', 'count'), exact=('difference_persons', lambda x: int(sum(x.abs() < 1e-06))), max_abs_diff=('difference_persons', lambda x: float(x.abs().max()))).reset_index()
    summary.to_csv(HERE / (a.prefix + '_summary.csv'), index=False, encoding='utf-8-sig')
    (HERE / (a.prefix + '_manifest.json')).write_text(json.dumps({'source_file': dest.name, 'source_sha256': hashlib.sha256(dest.read_bytes()).hexdigest(), 'captured_at_utc': source.get('captured_at_utc'), 'source_uri': source['url'], 'classification': 'KSIC11', 'periods': sorted(panel.period.unique()), 'model_performance_evaluated': False, 'status': 'diagnostic_only_not_training_or_test_targets'}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(summary.to_string(index=False))
if __name__ == '__main__':
    main()
