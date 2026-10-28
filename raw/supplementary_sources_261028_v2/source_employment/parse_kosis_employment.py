import argparse
import hashlib
import json
import math
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
import pandas as pd
HERE = Path(__file__).resolve().parent
REGIONS = {'서울특별시': 'KR011', '인천광역시': 'KR012', '경기도': 'KR013', '부산광역시': 'KR021', '울산광역시': 'KR022', '경상남도': 'KR023', '대구광역시': 'KR031', '경상북도': 'KR032', '광주광역시': 'KR041', '전라북도': 'KR042', '전북특별자치도': 'KR042', '전라남도': 'KR043', '대전광역시': 'KR051', '충청북도': 'KR052', '충청남도': 'KR053', '세종특별자치시': 'KR054', '강원도': 'KR061', '강원특별자치도': 'KR061', '제주특별자치도': 'KR071'}
RANGES = {'01~03': 'A', '05~08': 'B', '10~34': 'C', '35': 'D', '36~39': 'E', '41~42': 'F', '45~47': 'G', '49~52': 'H', '55~56': 'I', '58~63': 'J', '64~66': 'K', '68': 'L', '70~73': 'M', '74~76': 'N', '84': 'O', '85': 'P', '86~87': 'Q', '90~91': 'R', '94~96': 'S', '97~98': 'T', '99': 'U'}
GROUPS = {'A': ['A'], 'BTE': ['B', 'C', 'D', 'E'], 'F': ['F'], 'GTI': ['G', 'H', 'I'], 'J': ['J'], 'K': ['K'], 'L': ['L'], 'M_N': ['M', 'N'], 'OTQ': ['O', 'P', 'Q'], 'RTU': ['R', 'S', 'T', 'U'], '_T': ['_T']}

def clean(s):
    return re.sub('\\s+', ' ', s.replace('\xa0', ' ')).strip()

def expand(rows):
    grid = []
    occupied = {}
    for ri, row in enumerate(rows):
        line = {c: v for (r, c), v in occupied.items() if r == ri}
        ci = 0
        for cell in row:
            while ci in line:
                ci += 1
            for dr in range(cell.get('rs', 1)):
                for dc in range(cell.get('cs', 1)):
                    if dr == 0:
                        line[ci + dc] = clean(cell['text'])
                    else:
                        occupied[ri + dr, ci + dc] = clean(cell['text'])
            ci += cell.get('cs', 1)
        grid.append([line.get(i, '') for i in range(max(line, default=-1) + 1)])
    return grid

def parse(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    grid = expand(data['rows'])
    heads = grid[:3]
    if len({len(x) for x in heads}) != 1:
        raise ValueError('header widths differ')
    columns = []
    for ci in range(1, len(heads[0])):
        period, industry, measure = (x[ci] for x in heads)
        match = re.search('\\(([^()]*)\\)$', industry)
        section = '_T' if industry == '계' else RANGES.get(re.sub('\\s', '', match.group(1))) if match else None
        if section and '취업자' in measure:
            columns.append((ci, period, industry, section))
    result = []
    for row in grid[3:]:
        if not row or row[0] not in REGIONS:
            continue
        if len(row) != len(heads[0]):
            raise ValueError(f'row width mismatch: {row[0]}')
        for ci, period, industry, section in columns:
            raw = row[ci]
            number = raw.replace(',', '')
            valid = bool(re.fullmatch('[+-]?\\d+(?:\\.\\d+)?', number))
            value = float(number) if valid else float('nan')
            decimals = len(number.split('.')[1]) if valid and '.' in number else 0 if valid else None
            rse = row[ci + 1] if ci + 1 < len(row) and heads[1][ci + 1] == industry and ('RSE' in heads[2][ci + 1]) else ''
            result.append({'source_table': data['source'], 'region_code': REGIONS[row[0]], 'region_name_ko': row[0], 'period': period, 'year': int(period[:4]), 'half': 1 if period.endswith('1/2') else 2, 'section': section, 'industry_label': industry, 'raw_cell': raw, 'employment_thousands': value, 'employment_persons': value * 1000, 'decimal_places_displayed': decimals, 'rse_flag': rse, 'missing_symbol': raw if not valid else '', 'source_uri': data['url']})
    f = pd.DataFrame(result)
    if f.duplicated(['region_code', 'period', 'section']).any():
        raise ValueError('duplicated broad-sector keys')
    rows = []
    for (rc, period), g in f.groupby(['region_code', 'period'], sort=True):
        d = g.set_index('section')
        for industry, components in GROUPS.items():
            if any((c not in d.index for c in components)):
                raise ValueError(f'missing component columns {industry}')
            h = d.loc[components]
            complete = bool(h.employment_persons.notna().all())
            rows.append({'region_code': rc, 'region_name_ko': g.iloc[0].region_name_ko, 'period': period, 'year': int(period[:4]), 'half': g.iloc[0]['half'], 'industry_code': industry, 'employment_persons': float(h.employment_persons.sum()) if complete else float('nan'), 'complete_components': complete, 'components': '+'.join(components), 'missing_components': '+'.join(h[h.employment_persons.isna()].index), 'source_raw_values': '|'.join(h.raw_cell), 'rse_any_star': bool((h.rse_flag == '*').any()), 'display_rounding_halfwidth_persons': sum((500 * 10 ** (-int(x)) for x in h.decimal_places_displayed.dropna())) if complete else float('nan'), 'source_table': data['source'], 'source_uri': data['url']})
    return (f, pd.DataFrame(rows))

def main():
    a = argparse.ArgumentParser()
    a.add_argument('input', type=Path)
    a.add_argument('--prefix', required=True)
    args = a.parse_args()
    destination = HERE / args.input.name
    if args.input.resolve() != destination.resolve():
        shutil.copy2(args.input, destination)
    components, panel = parse(destination)
    components.to_csv(HERE / (args.prefix + '_sections.csv'), index=False, encoding='utf-8-sig')
    panel.to_csv(HERE / (args.prefix + '_panel.csv'), index=False, encoding='utf-8-sig')
    overlap = pd.read_csv(HERE / 'old_oecd_overlap_2022_2023.csv')
    m = panel.merge(overlap[['region_code', 'industry_code', 'year', 'employment_persons']], on=['region_code', 'industry_code', 'year'], suffixes=('_kosis', '_old_oecd'), how='inner')
    m['difference_persons'] = m.employment_persons_kosis - m.employment_persons_old_oecd
    m['within_display_rounding'] = m.difference_persons.abs() <= m.display_rounding_halfwidth_persons + 1e-06
    m.to_csv(HERE / (args.prefix + '_overlap_checks.csv'), index=False, encoding='utf-8-sig')
    summary = {'captured_source_file': destination.name, 'source_sha256': hashlib.sha256(destination.read_bytes()).hexdigest(), 'source_bytes': destination.stat().st_size, 'capture_file_mtime_utc': datetime.fromtimestamp(destination.stat().st_mtime, timezone.utc).isoformat(), 'capture_time_basis': 'Local source capture file modification time; no separate CSV download occurred', 'parsed_utc': datetime.now(timezone.utc).isoformat(), 'acquisition': 'Official KOSIS rendered table DOM captured through authorized browser; not a downloaded CSV/XLS', 'regions': panel.region_code.nunique(), 'periods': sorted(panel.period.unique()), 'panel_rows': len(panel), 'complete_rows': int(panel.complete_components.sum()), 'incomplete_rows': int((~panel.complete_components).sum()), 'overlap_rows': len(m), 'overlap_complete_rows': int(m.complete_components.sum()), 'overlap_within_display_rounding': int(m.within_display_rounding.sum()), 'max_abs_difference_persons': float(m.difference_persons.abs().max()) if len(m) else None, 'missing_value_rule': 'non-numeric cells are missing; never coerced to zero', 'classification': ('KSIC10 table S' if 'DT_1ES3B05S' in components.iloc[0].source_table else 'KSIC11 table J' if 'DT_1ES3B05J' in components.iloc[0].source_table else 'unverified table') + '; broad-sector aggregation using explicit 21-section labels', 'age_scope': 'National Regional Employment Survey metadata to be retained separately; not assumed to equal 15–64 labour covariates', 'reference_period': 'H1/H2 as rendered; annual label does not establish October', 'model_performance_evaluated': False}
    (HERE / (args.prefix + '_manifest.json')).write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if len(m):
        print(m.groupby(['year', 'industry_code']).agg(n=('region_code', 'size'), complete=('complete_components', 'sum'), within_rounding=('within_display_rounding', 'sum'), max_diff=('difference_persons', lambda x: x.abs().max())).to_string())
if __name__ == '__main__':
    main()
