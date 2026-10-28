#!/usr/bin/env python3
"""Mark v2-to-v3 wording, signs, URLs and changed figure captions in red."""
from pathlib import Path
from copy import deepcopy
from difflib import SequenceMatcher
import argparse,json,re,hashlib,zipfile
from lxml import etree

W='http://schemas.openxmlformats.org/wordprocessingml/2006/main'
NS={'w':W,'m':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
q=lambda x:'{'+W+'}'+x
def text(p):return ''.join(p.xpath('.//w:t/text()',namespaces=NS))
def red(r):
    rp=r.find(q('rPr'))
    if rp is None:rp=etree.Element(q('rPr'));r.insert(0,rp)
    for c in rp.findall(q('color')):rp.remove(c)
    c=etree.Element(q('color'));c.set(q('val'),'FF0000')
    before={q(x)for x in ('rStyle','rFonts','b','bCs','i','iCs','caps','smallCaps','strike','dstrike','outline','shadow','emboss','imprint','noProof','snapToGrid','vanish','webHidden')}
    rp.insert(next((i for i,e in enumerate(rp)if e.tag not in before),len(rp)),c)

def mask(a,b):
    aa=re.findall(r'\S+|\s+',a);bb=re.findall(r'\S+|\s+',b);starts=[0]
    for t in bb:starts.append(starts[-1]+len(t))
    out=[False]*len(b)
    for kind,i,j,k,l in SequenceMatcher(None,aa,bb,autojunk=False).get_opcodes():
        if kind=='equal':continue
        if k==l:
            n=next((v for v in range(k,len(bb))if not bb[v].isspace()),None)
            if n is None:n=next((v for v in range(k-1,-1,-1)if not bb[v].isspace()),None)
            if n is not None:k,l=n,n+1
        out[starts[k]:starts[l]]=[True]*(starts[l]-starts[k])
    for kind,i,j,k,l in SequenceMatcher(None,a,b,autojunk=False).get_opcodes():
        if kind not in ('insert','replace'):continue
        for m in re.finditer(r'\S+',b):
            if m.start()<l and m.end()>k:out[m.start():m.end()]=[True]*(m.end()-m.start())
    return out

def mark(p,flags):
    pos=0
    for r in list(p.xpath('.//w:r[w:t]',namespaces=NS)):
        ts=r.findall(q('t'));rt=''.join(t.text or ''for t in ts);bits=flags[pos:pos+len(rt)];pos+=len(rt)
        if not any(bits):continue
        if all(bits):red(r);continue
        # Runs with line breaks need per-text-node partitioning so the title and
        # source summary retain their original separators.
        parent=r.getparent();at=parent.index(r);offset=0
        for child in r:
            if child.tag==q('rPr'):continue
            if child.tag!=q('t'):
                clone=deepcopy(r)
                for e in list(clone):
                    if e.tag!=q('rPr'):clone.remove(e)
                clone.append(deepcopy(child));parent.insert(at,clone);at+=1;continue
            s=child.text or '';f=bits[offset:offset+len(s)];offset+=len(s)
            if not s:continue
            cuts=[0]+[i for i in range(1,len(s))if f[i]!=f[i-1]]+[len(s)]
            for start,end in zip(cuts,cuts[1:]):
                clone=deepcopy(r)
                for e in list(clone):
                    if e.tag!=q('rPr'):clone.remove(e)
                t=deepcopy(child);t.text=s[start:end];t.set('{http://www.w3.org/XML/1998/namespace}space','preserve');clone.append(t)
                if f[start]:red(clone)
                parent.insert(at,clone);at+=1
        parent.remove(r)
    assert pos==len(flags)

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--before',type=Path,required=True);ap.add_argument('--input',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    with zipfile.ZipFile(args.before)as z:a=etree.fromstring(z.read('word/document.xml'))
    with zipfile.ZipFile(args.input)as z:original=z.read('word/document.xml');b=etree.fromstring(original)
    body_a=a.find(q('body'));body_b=b.find(q('body'));pa=body_a.findall(q('p'));pb=body_b.findall(q('p'))
    assert len(pa)==len(pb);records=[]
    for i,(old,new)in enumerate(zip(pa,pb)):
        x,y=text(old),text(new);flags=mask(x,y)
        if i in(170,177):flags=[True]*len(y)
        if any(flags):mark(new,flags);records.append({'body_paragraph':i,'red_characters':sum(flags)})
        assert text(new)==y
    ta=body_a.findall(q('tbl'));tb=body_b.findall(q('tbl'));assert len(ta)==len(tb)==25
    for ti,(at,bt)in enumerate(zip(ta,tb)):
        ac=at.xpath('.//w:tc',namespaces=NS);bc=bt.xpath('.//w:tc',namespaces=NS);assert len(ac)==len(bc)
        for ci,(old,new)in enumerate(zip(ac,bc)):
            # Join only paragraph text, adding virtual line separators in both.
            oldps=old.findall(q('p'));newps=new.findall(q('p'))
            x='\n'.join(text(p)for p in oldps);y='\n'.join(text(p)for p in newps)
            flags=mask(x,y);pos=0
            for p in newps:
                n=len(text(p));mark(p,flags[pos:pos+n]);pos+=n+1
            if any(flags):records.append({'table':ti,'cell':ci,'red_characters':sum(flags)})
    updated=etree.tostring(b,encoding='UTF-8',xml_declaration=True,standalone=True)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.input)as src,zipfile.ZipFile(args.output,'w',compression=zipfile.ZIP_DEFLATED)as dst:
        for item in src.infolist():dst.writestr(item,updated if item.filename=='word/document.xml'else src.read(item.filename))
    clean=etree.fromstring(original)
    assert [text(p)for p in clean.xpath('.//w:p',namespaces=NS)]==[text(p)for p in b.xpath('.//w:p',namespaces=NS)]
    assert [etree.tostring(e)for e in clean.xpath('.//m:oMath',namespaces=NS)]==[etree.tostring(e)for e in b.xpath('.//m:oMath',namespaces=NS)]
    with zipfile.ZipFile(args.input)as x,zipfile.ZipFile(args.output)as y:
        assert x.namelist()==y.namelist()
        for n in x.namelist():
            if n!='word/document.xml':assert x.read(n)==y.read(n)
        assert y.testzip()is None
    audit={'baseline':args.before.name,'marked_sections':len(records),'text_preserved':True,'equations_preserved':19,
           'unchanged_other_docx_entries':True,'records':records,'sha256':hashlib.sha256(args.output.read_bytes()).hexdigest()}
    args.output.with_suffix('.redline.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in audit.items()if k!='records'},ensure_ascii=False))
if __name__=='__main__':main()
