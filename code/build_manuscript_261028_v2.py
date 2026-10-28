"""Rebuild the 261028_v2 manuscript without changing model results or equations."""
from pathlib import Path
import argparse, copy, hashlib, json, re, zipfile, io
from lxml import etree
from docx import Document
from docx.shared import Inches
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / 'support/manuscript/revision_261028_v2.json'

def set_text(p, text):
    if p._p.xpath('.//m:oMath'):
        raise ValueError('Refusing to flatten a paragraph containing an equation')
    rp = copy.deepcopy(p.runs[0]._r.rPr) if p.runs and p.runs[0]._r.rPr is not None else None
    p.clear()
    r = p.add_run(text)
    if rp is not None:
        r._r.insert(0, rp)

def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, default=ROOT/'generated/00_최종논문_261028_v2.docx')
    args = ap.parse_args()
    spec = json.loads(SPEC.read_text(encoding='utf-8'))
    src = ROOT / spec['source']
    assert hashlib.sha256(src.read_bytes()).hexdigest() == spec['source_sha256'], 'Unexpected source'
    doc = Document(src)
    equations_before = [etree.tostring(e) for e in doc._element.xpath('.//m:oMath')]
    for item in spec['paragraphs']:
        p = doc.paragraphs[item['index']]
        assert p.text == item['before'], f"Source paragraph changed: {item['index']}"
        set_text(p, item['after'])
    for item in spec['cells']:
        c = doc.tables[item['table']].cell(item['row'], item['column'])
        assert c.text == item['before'], f"Source table cell changed: {item}"
        assert len(c.paragraphs) == 1
        set_text(c.paragraphs[0], item['after'])
    # Use the font's portable English family name; preserve all equation runs.
    for root in [doc._element, doc.styles.element]:
        for e in root.xpath('.//w:rFonts'):
            for key in ['ascii','hAnsi','eastAsia','cs']:
                if e.get(qn('w:'+key)) == '나눔명조':
                    e.set(qn('w:'+key), 'NanumMyeongjo')
    for item in spec['figures']:
        shape = doc.inline_shapes[item['index']]
        img = ROOT / item['path']
        rid = shape._inline.xpath('.//a:blip')[0].get(qn('r:embed'))
        doc.part.related_parts[rid]._blob = img.read_bytes()
        w,h = Image.open(img).size
        width = min(Inches(5.90), Inches(item.get('max_height',7.10))*w/h)
        height = width*h/w
        shape.width, shape.height = int(width), int(height)
        ext = shape._inline.xpath('.//a:xfrm/a:ext')
        for e in ext:
            e.set('cx',str(int(width)));e.set('cy',str(int(height)))
    # Keep diagrams with their captions, not with the preceding section paragraph.
    for p in doc.paragraphs:
        if p._p.xpath('.//w:drawing'):
            p.paragraph_format.keep_with_next = True
    # Title stays in the source Title style, with no decorative border.
    for p in doc.paragraphs:
        if p.style.name == 'Title':
            for e in p._p.xpath('./w:pPr/w:pBdr'):
                e.getparent().remove(e)
    # Remove author-editing highlights from the clean submission copy.
    for e in doc._element.xpath('.//w:highlight'):
        e.getparent().remove(e)
    for e in doc._element.xpath('.//w:color'):
        e.set(qn('w:val'),'000000')
        for k in ['themeColor','themeTint','themeShade']:
            e.attrib.pop(qn('w:'+k),None)
    # Long identifiers read more clearly without stretched inter-word spaces.
    for i in list(range(257,319)) + [111,380,383,392]:
        doc.paragraphs[i].alignment = WD_ALIGN_PARAGRAPH.LEFT
    for i in range(257,319):
        doc.paragraphs[i].paragraph_format.space_after = Pt(2)
    # Use native Word superscripts instead of font-dependent Unicode exponents.
    trans=str.maketrans('⁰¹²³⁴⁵⁶⁷⁸⁹⁻','0123456789−')
    for p in doc.paragraphs:
        if p._p.xpath('.//m:oMath'):
            continue
        for r in list(p.runs):
            if not re.search(r'10[⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+',r.text):
                continue
            chunks=re.split(r'(10)([⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+)',r.text)
            prev=r._r
            for j,chunk in enumerate(chunks):
                if not chunk: continue
                new=OxmlElement('w:r')
                if r._r.rPr is not None:new.append(copy.deepcopy(r._r.rPr))
                if j%3==2:
                    rp=new.find(qn('w:rPr'))
                    if rp is None:rp=OxmlElement('w:rPr');new.insert(0,rp)
                    va=OxmlElement('w:vertAlign');va.set(qn('w:val'),'superscript');rp.append(va)
                    chunk=chunk.translate(trans)
                t=OxmlElement('w:t');t.set('{http://www.w3.org/XML/1998/namespace}space','preserve');t.text=chunk;new.append(t)
                prev.addnext(new);prev=new
            r._r.getparent().remove(r._r)
    equations_after = [etree.tostring(e) for e in doc._element.xpath('.//m:oMath')]
    assert equations_before == equations_after, 'Equation XML changed'
    args.output.parent.mkdir(parents=True,exist_ok=True)
    doc.save(args.output)
    # Fix ZIP timestamps/order for a byte-identical rebuild under the same dependencies.
    buf=io.BytesIO()
    with zipfile.ZipFile(args.output) as srczip, zipfile.ZipFile(buf,'w',compression=zipfile.ZIP_DEFLATED) as dstzip:
        for name in sorted(srczip.namelist()):
            info=zipfile.ZipInfo(name,date_time=(2026,10,28,0,0,0))
            info.compress_type=zipfile.ZIP_DEFLATED
            dstzip.writestr(info,srczip.read(name))
    args.output.write_bytes(buf.getvalue())
    audit={'source_sha256':spec['source_sha256'],'paragraph_changes':len(spec['paragraphs']),
           'cell_changes':len(spec['cells']),'equations_preserved':len(equations_after),
           'tables':len(doc.tables),'figures':len(doc.inline_shapes),
           'output_sha256':hashlib.sha256(args.output.read_bytes()).hexdigest()}
    args.output.with_suffix('.build.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(audit,ensure_ascii=False))

if __name__ == '__main__':
    main()
