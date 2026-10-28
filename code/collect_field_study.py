"""Run the pilot locally with real participants; no network service is deployed."""
import argparse
import csv
import html
import json
import secrets
import time
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs
from pilot_materials import FIELDS

ROOT=Path(__file__).resolve().parents[1]
STYLE='''body{font-family:Arial,"Malgun Gothic",sans-serif;color:#172833;background:#f4f6f7;margin:0}main{max-width:900px;margin:28px auto;background:white;padding:32px}h1{font-size:25px}h2{font-size:17px}p{line-height:1.6}table{width:100%;border-collapse:collapse}td{padding:8px;border-bottom:1px solid #dbe1e5}td:first-child{width:45%;color:#425665}.cards{display:grid;grid-template-columns:1fr 1fr;gap:16px}.card{border:1px solid #bacbd5;padding:14px}.card h2{margin-top:0}input,select,textarea{padding:9px;font-size:16px;margin:8px 0}textarea{width:95%}button{padding:12px 24px;background:#234f65;color:white;border:0;font-size:16px;cursor:pointer}label{display:block;margin-top:12px}.note{color:#526775;font-size:14px}'''

def stimulus(task,condition):
    esc=html.escape
    if condition=='table':
        return '<table>'+''.join('<tr><td>'+esc(g['title']+' / '+label)+'</td><td>'+esc(value)+'</td></tr>'
            for g in task['groups'] for label,value in g['items'])+'</table>'
    if condition!='card':raise ValueError('Unknown condition')
    return '<div class="cards">'+''.join('<section class="card"><h2>'+esc(g['title'])+'</h2><table>'+''.join(
        '<tr><td>'+esc(label)+'</td><td>'+esc(value)+'</td></tr>' for label,value in g['items'])+'</table></section>'
        for g in task['groups'])+'</div>'

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--records',type=Path,required=True);p.add_argument('--port',type=int,default=8765)
    args=p.parse_args();args.records.mkdir(parents=True,exist_ok=True);path=args.records/'responses.csv'
    if not path.exists():
        with path.open('w',encoding='utf-8-sig',newline='') as f:csv.DictWriter(f,fieldnames=FIELDS).writeheader()
    tasks={x['task_id']:x for x in json.loads((ROOT/'field_study/tasks.json').read_text())}
    schedule=list(csv.DictReader((ROOT/'field_study/counterbalanced_assignment.csv').open(encoding='utf-8-sig')))
    sessions={}
    def observed():
        with path.open(encoding='utf-8-sig') as f:return list(csv.DictReader(f))
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def page(self,body,status=200):
            data=('<!doctype html><html lang="ko"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>지역고용 근거 검토 과업</title><style>'+STYLE+'</style><main>'+body+'</main></html>').encode()
            self.send_response(status);self.send_header('Content-Type','text/html; charset=utf-8')
            self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
        def do_GET(self):
            self.page('<h1>지역고용 근거 검토 과업</h1><p>진행자에게 받은 참여자 코드를 입력하십시오. 실명은 입력하지 않습니다. 한 번에 한 명씩 진행합니다.</p><form method="post" action="/start"><label>참여자 코드 <input name="person" pattern="P0[1-8]" required placeholder="P01"></label><label><input type="checkbox" name="consent" value="yes" required>연구 안내를 받았으며 참여에 동의합니다.</label><button>시작 준비</button></form>')
        def ready(self,token):
            s=sessions[token];done={(x['participant_code'],x['task_id']) for x in observed()}
            remaining=[r for r in schedule if r['participant_code']==s['person'] and (r['participant_code'],r['task_id']) not in done]
            remaining.sort(key=lambda r:int(r['order']))
            if not remaining:
                self.page('<h1>과업이 종료되었습니다</h1><p>응답이 저장되었습니다. 진행자에게 알려 주십시오.</p>');return
            s['assignment']=remaining[0]
            for key in ['started','judgment','seconds']:s.pop(key,None)
            self.page('<h1>과업 '+remaining[0]['order']+' / 16</h1><p>준비되면 시작하십시오. 자료를 확인하고 처음 판단을 제출할 때까지의 시간을 기록합니다. 정답은 종료 전 공개하지 않습니다.</p><form method="post" action="/task"><input type="hidden" name="token" value="'+token+'"><button>과업 시작</button></form>')
        def do_POST(self):
            try:
                length=int(self.headers.get('Content-Length','0'))
                if not 0<length<30000:raise ValueError('Invalid request')
                d={k:v[0] for k,v in parse_qs(self.rfile.read(length).decode()).items()}
                if self.path=='/start':
                    person=d.get('person','').strip().upper()
                    if person not in {r['participant_code'] for r in schedule} or d.get('consent')!='yes':raise ValueError('참여자 코드와 동의를 확인하십시오.')
                    if any(s['person']==person for s in sessions.values()):raise ValueError('진행 중인 코드입니다. 원래 화면에서 계속하십시오.')
                    token=secrets.token_urlsafe(24);sessions[token]={'person':person};self.ready(token);return
                token=d.get('token');s=sessions.get(token)
                if not s:raise ValueError('세션을 확인하십시오.')
                row=s['assignment'];task=tasks[row['task_id']]
                hidden='<input type="hidden" name="token" value="'+token+'">'
                if self.path=='/task':
                    if 'started' in s:raise ValueError('이미 시작한 과업입니다.')
                    s['started']=time.monotonic()
                    self.page('<h1>과업 '+row['order']+' / 16</h1><p class="note">근거 판본, 검증사례 수와 등록 모형계수를 확인하십시오. 실제 정책 결정과 별개의 연구용 검토입니다.</p>'+stimulus(task,row['condition'])+'<h2>'+html.escape(task['question'])+'</h2><form method="post" action="/judge">'+hidden+'<label>판단 <select name="action" required><option value="">선택</option><option value="allow">연구용 검토 완료</option><option value="revise">보완 후 재검토</option></select></label><button>판단 제출</button></form>');return
                if self.path=='/judge':
                    if 'started' not in s or 'judgment' in s or d.get('action') not in ['allow','revise']:raise ValueError('판단 제출 상태를 확인하십시오.')
                    s['judgment']=d['action'];s['seconds']=round(time.monotonic()-s['started'],3)
                    # Append the initial judgment immediately to retain abandoned follow-ups.
                    with (args.records/'judgments.jsonl').open('a',encoding='utf-8') as f:
                        f.write(json.dumps({**row,'action':s['judgment'],'seconds':s['seconds'],
                           'record_source':'human_observed','recorded_at_utc':datetime.now(timezone.utc).isoformat()},ensure_ascii=False)+'\n')
                    self.page('<h1>판단 근거 기록</h1><p>최초 판단과 시간이 기록되었습니다. 아래 응답은 판단시간에 포함되지 않습니다.</p>'+stimulus(task,row['condition'])+'<form method="post" action="/answer">'+hidden+'<label>판단 근거와 다음 조치<textarea name="reason" rows="2" required></textarea></label><label>이 판단이 맞을 가능성 0~100% <input name="confidence" type="number" min="0" max="100" required></label><label>제시된 근거의 신뢰성 1 매우 낮음~7 매우 높음 <input name="trust" type="number" min="1" max="7" required></label><button>응답 저장</button></form>');return
                if self.path!='/answer' or 'judgment' not in s:raise ValueError('판단 제출 상태를 확인하십시오.')
                reason=d.get('reason','').strip();confidence=float(d.get('confidence','nan'));trust=int(d.get('trust','0'))
                if not reason or not 0<=confidence<=100 or not 1<=trust<=7:raise ValueError('모든 응답을 확인하십시오.')
                if (row['participant_code'],row['task_id']) in {(x['participant_code'],x['task_id']) for x in observed()}:raise ValueError('이미 저장된 과업입니다.')
                record={**row,'intended_action_before_gate':s['judgment'],'response_seconds_before_gate':s['seconds'],
                        'reason_text':reason,'confidence_0_100':confidence,'evidence_trust_1_7':trust,'consent_recorded':True,
                        'record_source':'human_observed','recorded_at_utc':datetime.now(timezone.utc).isoformat()}
                with path.open('a',encoding='utf-8',newline='') as f:
                    csv.DictWriter(f,fieldnames=FIELDS).writerow(record);f.flush()
                self.ready(token)
            except (ValueError,KeyError) as e:self.page('<h1>입력을 확인하십시오</h1><p>'+html.escape(str(e))+'</p><p>뒤로 가기로 기존 화면을 복구하거나 진행자에게 알려 주십시오.</p>',400)
    print(f'Open http://127.0.0.1:{args.port} on this computer. Records: {path}',flush=True)
    HTTPServer(('127.0.0.1',args.port),Handler).serve_forever()

if __name__=='__main__':main()
