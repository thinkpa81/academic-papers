#!/usr/bin/env python3
"""Check citation coverage, short-minus signs, template geometry and Word structure."""
import argparse,hashlib,json,re
from pathlib import Path
from collections import Counter
from docx import Document
from docx.oxml.ns import qn

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manuscript',type=Path,required=True);ap.add_argument('--report',type=Path,required=True)
    ap.add_argument('--code-commit');a=ap.parse_args();d=Document(a.manuscript)
    text=lambda p:''.join(p.xpath('.//w:t/text()'))
    paragraphs=d._element.xpath('.//w:p');refs={};uses=[]
    for i,p in enumerate(paragraphs):
        s=text(p);m=re.match(r'^\[(\d+)\]\s',s)
        if m:refs[int(m.group(1))]=s;continue
        for m in re.finditer(r'\[((?:\d+)(?:\s*[,~-]\s*\d+)*)\]',s):
            values=[]
            for token in m.group(1).split(','):
                pair=re.split('[~-]',token)
                values.extend(range(int(pair[0]),int(pair[1])+1)if len(pair)==2 else [int(pair[0])])
            uses.append({'paragraph':i,'citation':m.group(),'references':values,'context':s[max(0,m.start()-70):m.end()+50]})
    alltext='\n'.join(text(p)for p in paragraphs)
    numbers={n for u in uses for n in u['references']}
    badglyphs={f'U+{ord(c):04X}':alltext.count(c)for c in '\u2212\u2010\u2011\u2012\u2013\u2014\ufe63\uff0d'if c in alltext}
    geometry=[]
    for i,s in enumerate(d.sections):
        mm=lambda x:round(x/36000,4)
        v={'section':i,'width':mm(s.page_width),'height':mm(s.page_height),
           'left_effective':mm(s.left_margin+s.gutter),'right':mm(s.right_margin),
           'top':mm(s.top_margin),'bottom':mm(s.bottom_margin)}
        v['pass']=all(abs(v[k]-n)<.06 for k,n in [('width',190),('height',262),('left_effective',23),('right',20),('top',38),('bottom',22)])
        geometry.append(v)
    checks={'references_1_through_61':set(refs)==set(range(1,62)),
            'no_dangling_citations':not(numbers-set(refs)),'every_reference_used':not(set(refs)-numbers),
            'short_ascii_minus_only':not badglyphs,'native_equations_19':len(d._element.xpath('.//m:oMath'))==19,
            'tables_25':len(d.tables)==25,'figures_4':len(d.inline_shapes)==4,
            'template_geometry':all(x['pass']for x in geometry),
            'author_metadata_empty':not d.core_properties.author and not d.core_properties.last_modified_by,
            'no_author_placeholder':'Author(s): Withheld'not in alltext}
    if a.code_commit:
        checks['verified_commit_cited_once']=bool(re.fullmatch('[0-9a-f]{40}',a.code_commit)) and alltext.count(a.code_commit)==1
        checks['no_draft_commit_placeholder']='0'*40 not in alltext
    audit={'manuscript':a.manuscript.name,'sha256':hashlib.sha256(a.manuscript.read_bytes()).hexdigest(),
           'checks':checks,'passed':all(checks.values()),'reference_count':len(refs),
           'citation_groups':len(uses),'citation_instances':sum(len(x['references'])for x in uses),
           'dangling':sorted(numbers-set(refs)),'uncited':sorted(set(refs)-numbers),'non_ascii_minus':badglyphs,
           'geometry':geometry,'citation_locations':uses,
           'scope':'Structural/number matching only; substantive source checks and rendered page QA are separate.'}
    a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in audit.items()if k not in ('geometry','citation_locations')},ensure_ascii=False))
    raise SystemExit(0 if audit['passed'] else 1)
if __name__=='__main__':main()
