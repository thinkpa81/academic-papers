if not __debug__:
    raise RuntimeError('Run verification with Python optimization disabled.')
from pathlib import Path
import csv
import datetime
import hashlib
import json
import re
B = Path(__file__).parent
intervals = {2013: (14, 20, 21, 5, 6), 2014: (13, 19, 20, 5, 9), 2015: (12, 18, 22, 5, 11), 2016: (10, 16, 20, 5, 6), 2017: (9, 15, 18, 5, 10), 2018: (15, 21, 23, 5, 9), 2019: (14, 20, 22, 5, 8), 2020: (12, 18, 19, 5, 8), 2021: (11, 17, 19, 5, 4), 2022: (10, 16, 19, 5, 4), 2023: (9, 15, 19, 5, 4), 2024: (14, 20, 23, 5, 8), 2025: (13, 19, 22, 5, 7)}
rows = []
for y, (a, z, s, m, d) in intervals.items():
    h = (B / f'{y}_H1_page.html').read_text(encoding='utf-8')
    release = re.search('게시일.*?(\\d{4}-\\d{2}-\\d{2})', h, re.S)[1]
    mf = json.loads((B / f'{y}_source_manifest.json').read_text(encoding='utf-8'))
    txt = (B / f'{y}_H1_industry_occupation.txt').read_text(errors='replace', encoding='utf-8')
    cls = 'KSIC9' if y <= 2017 else 'KSIC10' if y <= 2024 else 'KSIC11'
    assert '제' + cls.replace('KSIC', '') + '차' in txt
    p = next((i for i, t in enumerate(txt.split('\x0c'), 1) if '조사대상기간' in t))
    row = {'year': y, 'reference_period': f'{y}-H1 (April reference week)', 'reference_start': f'{y}-04-{a:02d}', 'reference_end': f'{y}-04-{z:02d}', 'survey_fieldwork_start': f'{y}-04-{s:02d}', 'survey_fieldwork_end': f'{y}-{m:02d}-{d:02d}', 'release_date': release, 'classification_in_release': cls, 'source_url': mf['source_url'], 'pdf_url': mf['pdf_url'], 'pdf_reference_period_page': p, 'verified_scope': 'Official release-page date; downloaded report reference week and industrial classification; not immutable original-release cell values', 'source_status': '원문 확인', 'released_by_year_end': release <= f'{y}-12-31', 'current_KOSIS_cell_vintage_as_of_origin_verified': False, 'pdf_sha256': mf['pdf_sha256']}
    rows.append(row)
with (B / 'release_calendar_H1_2013_2025.csv').open('w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0]))
    w.writeheader()
    w.writerows(rows)
(B / 'release_calendar_H1_2013_2025.json').write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
origin = []
for r in rows[:-1]:
    y = r['year']
    target = rows[y - 2013 + 1]
    cut = datetime.date(y, 12, 31)
    origin.append({'input_year': y, 'design_forecast_origin': str(cut), 'target_year': y + 1, 'input_report_release': r['release_date'], 'reference_change': 'April t to April t+1: approximately 12 months', 'observation_horizon_days_to_target_week_start': (datetime.date.fromisoformat(target['reference_start']) - cut).days, 'observation_horizon_days_to_target_week_end': (datetime.date.fromisoformat(target['reference_end']) - cut).days, 'result_release_date': target['release_date'], 'days_until_target_report_release': (datetime.date.fromisoformat(target['release_date']) - cut).days, 'real_time_vintage_gate': 'HOLD: current reclassified/backcast KOSIS vintage is not verified as available at this historical origin'})
with (B / 'year_end_origin_design.csv').open('w', encoding='utf-8-sig', newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(origin[0]))
    w.writeheader()
    w.writerows(origin)
summary = {'scope': 'Official H1 release chronology and classification history; not a forecast performance audit', 'years_verified': list(range(2013, 2026)), 'all_H1_reports_released_by_same_year_Dec31': True, 'historical_cell_vintages_reconstructed': False, 'real_time_forecasting_claim_permitted': False, 'current_vintage_pseudo_out_of_sample_claim_permitted': 'yes if same classification/season, temporal splits and availability assumptions are explicit', 'OECD_covariate_vintage_reconstructed': False, 'recommendation': 'Use employment-only derived predictors for current-vintage H1-to-H1 robustness; separate release scheduling from historic-vintage validation; no human/policy evaluation implied', 'classification_backcast_note_2025H1': '2017-2024H1, report 2025-10-28 p2', 'classification_backcast_note_2025H2': '2013-2024H1, report 2026-04-23 p2 visually inspected', 'exact_KSIC11_backcast_first_publication_date': 'not established; dated reports prove the corresponding scope was publicly described by those dates', 'prior_2013_2017_KSIC10_backcast': '2018H1 report p2 documents 2013-2017H1 revision; contemporaneous 2013-2017H1 releases used KSIC9'}
(B / 'availability_gate_summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
print(json.dumps({'years': len(rows), 'origin_scenarios': len(origin), 'min_days_to_target': min((x['observation_horizon_days_to_target_week_start'] for x in origin)), 'max_days_to_target': max((x['observation_horizon_days_to_target_week_end'] for x in origin))}, ensure_ascii=False))
