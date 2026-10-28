"""Software fixtures only. Temporary test records are never research observations."""
import csv
import json
import sys
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'code'))
from collect_field_study import stimulus
from pilot_analysis import analyze

class Cells(HTMLParser):
    def __init__(self):super().__init__();self.cells=[];self.in_td=False
    def handle_starttag(self,tag,attrs):
        if tag=='td':self.in_td=True;self.cells.append('')
    def handle_endtag(self,tag):
        if tag=='td':self.in_td=False
    def handle_data(self,data):
        if self.in_td:self.cells[-1]+=data

class PilotTests(unittest.TestCase):
    def test_assignment_balance(self):
        s=pd.read_csv(ROOT/'field_study/counterbalanced_assignment.csv')
        k=pd.read_csv(ROOT/'field_study/assessor_answer_key.csv')
        z=s.merge(k,on='task_id')
        self.assertEqual(len(s),128)
        self.assertEqual(s.participant_code.nunique(),8)
        self.assertTrue(z.groupby(['participant_code','condition','issue']).size().eq(2).all())
        self.assertTrue(s.groupby(['task_id','condition']).size().eq(4).all())
        self.assertFalse(s.duplicated(['participant_code','task_id']).any())
    def test_display_values_equivalent_and_no_answer_labels(self):
        for task in json.loads((ROOT/'field_study/tasks.json').read_text()):
            a,b=Cells(),Cells();a.feed(stimulus(task,'table'));b.feed(stimulus(task,'card'))
            self.assertEqual(a.cells[1::2],b.cells[1::2]);self.assertEqual(len(a.cells),34)
            self.assertNotIn('correct_action',stimulus(task,'card'))
            self.assertNotIn('mismatch',stimulus(task,'table'))
    def test_numeric_source_binding(self):
        source=json.loads((ROOT/'support/model_swap_addendum/frozen/protocol_and_cases.json').read_text())
        cases={c['case_id']:c['fixture']['card'] for c in source['cases']}
        for record in json.loads((ROOT/'field_study/task_provenance.json').read_text()):
            card=cases[record['source_case_id']]
            self.assertEqual(record['prediction'],card['learned_comparator']['logpoints'])
            self.assertEqual(record['baseline'],card['default_estimate']['logpoints'])
            self.assertEqual(record['source_validation_n'],card['prior_validation']['validation_year_n'])
    def test_empty_has_no_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            r=analyze(ROOT/'field_study/responses_EMPTY.csv',Path(tmp)/'out')
            self.assertEqual(r['status'],'not_evaluated');self.assertFalse(r['effects_estimated'])
    def fixture(self):
        # Test-only values; used solely inside TemporaryDirectory.
        s=pd.read_csv(ROOT/'field_study/counterbalanced_assignment.csv')
        s=s[s.participant_code.eq('P01')].copy()
        keys=pd.read_csv(ROOT/'field_study/assessor_answer_key.csv').set_index('task_id')
        s['intended_action_before_gate']=s.task_id.map(keys.correct_action)
        s['response_seconds_before_gate']=10.;s['reason_text']='SOFTWARE TEST FIXTURE'
        s['confidence_0_100']=80;s['evidence_trust_1_7']=4;s['consent_recorded']=True
        s['record_source']='human_observed';s['recorded_at_utc']='2000-01-01T00:00:00Z'
        return s
    def test_pairing_without_pseudoreplication(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);self.fixture().to_csv(tmp/'TEST.csv',index=False)
            r=analyze(tmp/'TEST.csv',tmp/'out')
            self.assertEqual(r['complete_participants'],1);self.assertEqual(r['observations'],16)
            z=pd.read_csv(tmp/'out/paired_participant_differences.csv')
            self.assertEqual(len(z),1);self.assertEqual(z.accuracy_card_minus_table.iloc[0],0)
    def test_reject_synthetic_and_nonfinite_records(self):
        for change in ['source','time','duplicate','condition']:
            with tempfile.TemporaryDirectory() as tmp:
                tmp=Path(tmp);s=self.fixture()
                if change=='source':s['record_source']='software_test'
                elif change=='time':s['response_seconds_before_gate']=float('inf')
                elif change=='duplicate':s=pd.concat([s,s.iloc[:1]])
                else:s.loc[s.index[0],'condition']='unknown'
                s.to_csv(tmp/'TEST.csv',index=False)
                with self.assertRaises(ValueError):analyze(tmp/'TEST.csv',tmp/'out')

if __name__=='__main__':unittest.main()
