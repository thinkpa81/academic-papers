if not __debug__:
    raise RuntimeError('Run verification with Python optimization disabled.')
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
KEYS = ['REF_AREA', 'MEASURE', 'AGE', 'SEX', 'UNIT_MEASURE', 'TIME_PERIOD']
MEASURES = ['LF_RATE', 'UNE_RATE']

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def decode_csv(path):
    data = pd.read_csv(path)
    decoded = pd.DataFrame()
    for column in data:
        key = column.split(':', 1)[0]
        decoded[key] = data[column].map(lambda value: value.split(': ', 1)[0] if isinstance(value, str) and ': ' in value else value)
    for column in ['TIME_PERIOD', 'OBS_VALUE', 'UNIT_MULT', 'DECIMALS']:
        decoded[column] = pd.to_numeric(decoded[column])
    return decoded

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--old-file', type=Path, required=True)
    parser.add_argument('--new-file', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    old_all, new_all = (decode_csv(args.old_file), decode_csv(args.new_file))

    def wanted(frame):
        return frame[frame.TERRITORIAL_LEVEL.eq('TL3') & frame.COUNTRY.eq('KOR') & frame.AGE.eq('Y15T64') & frame.SEX.eq('_T') & frame.MEASURE.isin(MEASURES)].copy()
    old = wanted(old_all)
    new = wanted(new_all)
    for frame in [old, new]:
        assert not frame.duplicated(KEYS).any(), 'Duplicate source keys'
        assert frame.FREQ.eq('A').all() and frame.UNIT_MULT.eq(0).all()
        assert set(frame[frame.MEASURE.eq('UNE_RATE')].UNIT_MEASURE) == {'PT_LF_SUB'}
        assert set(frame[frame.MEASURE.eq('LF_RATE')].UNIT_MEASURE) == {'PT_POP_SUB'}
    assert new.REF_AREA.nunique() == 17
    old_overlap = old[old.TIME_PERIOD.isin([2022, 2023])].copy()
    new_overlap = new[new.TIME_PERIOD.isin([2022, 2023])].copy()
    assert set(new.REF_AREA) == set(old_overlap.REF_AREA)
    old_overlap.sort_values(KEYS).to_csv(out / 'old_oecd_overlap_2022_2023.csv', index=False, encoding='utf-8-sig')
    normalized = new[new.TIME_PERIOD.between(2022, 2024)].sort_values(KEYS)
    normalized.to_csv(out / 'normalized_oecd_y15t64_2022_2024.csv', index=False, encoding='utf-8-sig')
    overlap = old_overlap[KEYS + ['OBS_VALUE']].merge(new_overlap[KEYS + ['OBS_VALUE']], on=KEYS, how='outer', validate='one_to_one', suffixes=('_old', '_new'), indicator=True)
    overlap['new_minus_old'] = overlap.OBS_VALUE_new - overlap.OBS_VALUE_old
    overlap['exact_match'] = np.isclose(overlap.OBS_VALUE_new, overlap.OBS_VALUE_old, atol=1e-08, rtol=1e-10)
    overlap.sort_values(KEYS).to_csv(out / 'overlap_2022_2023_comparison.csv', index=False, encoding='utf-8-sig')
    by_measure = []
    for measure, group in overlap.groupby('MEASURE'):
        by_measure.append({'measure': measure, 'n': len(group), 'exact_matches': int(group.exact_match.sum()), 'different': int((~group.exact_match).sum()), 'max_abs_difference': float(group.new_minus_old.abs().max())})
    future = new[new.TIME_PERIOD.eq(2025)].groupby('MEASURE').agg(regions=('REF_AREA', 'nunique'), rows=('OBS_VALUE', 'size')).reset_index().to_dict('records')
    exact = bool(overlap.exact_match.all())
    result = {'reviewed_utc': datetime.now(timezone.utc).isoformat(), 'scope': 'Source acquisition and definition/overlap review only. No model fitting, prediction updating, or outcome scoring.', 'status': 'REQUIRES_SURVEY_PERIOD_REVIEW' if exact else 'HOLD_2025_INPUT_BRIDGE_REQUIRED', 'old_raw_sha256': sha(args.old_file), 'raw_sha256': sha(args.new_file), 'raw_rows': len(new_all), 'raw_years': sorted(new_all.TIME_PERIOD.unique().tolist()), 'normalized_2022_2024_rows': len(normalized), 'new_2024_rows': int(normalized.TIME_PERIOD.eq(2024).sum()), '2024_regions': int(normalized[normalized.TIME_PERIOD.eq(2024)].REF_AREA.nunique()), 'overlap_rows': len(overlap), 'overlap_exact_matches': int(overlap.exact_match.sum()), 'overlap_differences': int((~overlap.exact_match).sum()), 'overlap_missing_old_or_new': int(overlap._merge.ne('both').sum()), 'maximum_absolute_difference_pct_points': float(overlap.new_minus_old.abs().max()), 'by_measure': by_measure, 'definition_codes_match': True, 'annualisation_and_country_survey_bridge_confirmed': False, 'future_2025_availability_only': future, 'scoring_authorized': False}
    (out / 'source_gate_HOLD.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False, indent=2))
if __name__ == '__main__':
    main()
