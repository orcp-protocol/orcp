#!/usr/bin/env python3
"""
Build ORCP-v1.1.docx from ORCP-v1.1.md, mirroring the layout/formatting of
ORCP_Specification_v1.0.docx (custom centred title page, navy #2C3E50 H1 /
slate #34495E H2, Courier New 10pt code on #F4F6F7 shading, navy-header
tables with #AAAAAA borders). Reuses the v1.0 docx "chrome" (styles, theme,
numbering, settings) verbatim; regenerates only the body, header/footer text,
and core properties. No company branding (the v1.0 doc has none either).

Stdlib only. Usage: python3 build_docx.py
"""
import os, re, shutil, zipfile, html, tempfile

# Paths are resolved relative to this script (spec/tools/build_docx.py), so the
# build works from any checkout location.
SPEC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MD   = os.path.join(SPEC, "ORCP-v1.1.md")
REFDOCX = os.path.join(SPEC, "ORCP_Specification_v1.0.docx")  # chrome source
_TMP = tempfile.gettempdir()
REF  = os.path.join(_TMP, "orcp_v10_chrome")   # unzipped v1.0 docx (chrome source)
OUT  = os.path.join(SPEC, "ORCP-v1.1.docx")
BUILD= os.path.join(_TMP, "orcp_v11_build")

# Self-contained: unzip the v1.0 docx chrome if the temp dir is absent.
if not os.path.isdir(os.path.join(REF, "word")):
    if os.path.exists(REF): shutil.rmtree(REF)
    os.makedirs(REF)
    with zipfile.ZipFile(REFDOCX) as z:
        z.extractall(REF)

# ── inline parsing ──────────────────────────────────────────────────────────
INLINE = re.compile(
    r'`(?P<code>[^`]+)`'
    r'|\*\*(?P<bold>[^*]+?)\*\*'
    r'|\*(?P<ital>[^*]+?)\*'
    r'|\[(?P<ltext>[^\]]+)\]\((?P<lhref>[^)]+)\)'
)

def esc(t):
    return html.escape(t, quote=False)

_rel_links = []   # (rId, target) external hyperlink relationships

def _run(text, *, code=False, bold=False, ital=False):
    rpr = []
    if code:
        rpr.append('<w:rFonts w:ascii="Courier New" w:eastAsia="Courier New" '
                   'w:hAnsi="Courier New" w:cs="Courier New"/>'
                   '<w:shd w:val="clear" w:color="auto" w:fill="F0F0F0"/>'
                   '<w:sz w:val="20"/><w:szCs w:val="20"/>')
    if bold: rpr.append('<w:b/><w:bCs/>')
    if ital: rpr.append('<w:i/><w:iCs/>')
    rpr = f'<w:rPr>{"".join(rpr)}</w:rPr>' if rpr else ''
    return f'<w:r>{rpr}<w:t xml:space="preserve">{esc(text)}</w:t></w:r>'

def inline(text, slugs):
    """Return run/hyperlink XML for a span of markdown inline text."""
    out, i = [], 0
    for m in INLINE.finditer(text):
        if m.start() > i:
            out.append(_run(text[i:m.start()]))
        if m.group('code') is not None:
            out.append(_run(m.group('code'), code=True))
        elif m.group('bold') is not None:
            out.append(_run(m.group('bold'), bold=True))
        elif m.group('ital') is not None:
            out.append(_run(m.group('ital'), ital=True))
        else:
            txt, href = m.group('ltext'), m.group('lhref')
            inner = (f'<w:r><w:rPr><w:rStyle w:val="Hyperlink"/></w:rPr>'
                     f'<w:t xml:space="preserve">{esc(txt)}</w:t></w:r>')
            if href.startswith('#'):
                anchor = href[1:]
                if anchor in slugs:
                    out.append(f'<w:hyperlink w:anchor="{esc(anchor)}">{inner}</w:hyperlink>')
                else:
                    out.append(inner)
            else:
                rid = f'rId{1000+len(_rel_links)}'
                _rel_links.append((rid, href))
                out.append(f'<w:hyperlink r:id="{rid}">{inner}</w:hyperlink>')
        i = m.end()
    if i < len(text):
        out.append(_run(text[i:]))
    return ''.join(out) or _run('')

# ── github-style heading slugs (match the markdown TOC anchors) ──────────────
def slugify(text):
    s = text.strip().lower()
    s = re.sub(r'[^\w\s-]', '', s)
    s = re.sub(r'\s+', '-', s)
    s = re.sub(r'-+', '-', s)
    return s

# ── block builders ──────────────────────────────────────────────────────────
def heading(text, level, bm_id, slug, page_break=False):
    style = 'Heading1' if level == 2 else 'Heading2'
    pb = '<w:pageBreakBefore/>' if page_break else ''
    return (f'<w:p><w:pPr><w:pStyle w:val="{style}"/>{pb}</w:pPr>'
            f'<w:bookmarkStart w:id="{bm_id}" w:name="{slug}"/>'
            f'<w:bookmarkEnd w:id="{bm_id}"/>'
            f'{inline(text, SLUGS)}</w:p>')

def para(text):
    return (f'<w:p><w:pPr><w:spacing w:after="160" w:line="276" '
            f'w:lineRule="auto"/></w:pPr>{inline(text, SLUGS)}</w:p>')

def hrule():
    return ('<w:p><w:pPr><w:pBdr><w:bottom w:val="single" w:sz="4" '
            'w:space="4" w:color="D5D8DC"/></w:pBdr><w:spacing w:after="160"/>'
            '</w:pPr></w:p>')

def list_item(text, marker):
    return (f'<w:p><w:pPr><w:pStyle w:val="ListParagraph"/>'
            f'<w:spacing w:after="60"/>'
            f'<w:ind w:left="420" w:hanging="300"/></w:pPr>'
            f'{_run(marker + "  ")}{inline(text, SLUGS)}</w:p>')

CODE_FILL = "F4F6F7"
def code_block(lines):
    out = []
    n = len(lines)
    for idx, ln in enumerate(lines):
        before = '120' if idx == 0 else '0'
        after  = '120' if idx == n - 1 else '0'
        out.append(
            f'<w:p><w:pPr>'
            f'<w:shd w:val="clear" w:color="auto" w:fill="{CODE_FILL}"/>'
            f'<w:spacing w:before="{before}" w:after="{after}" w:line="240" '
            f'w:lineRule="auto"/></w:pPr>'
            f'<w:r><w:rPr><w:rFonts w:ascii="Courier New" w:eastAsia="Courier New" '
            f'w:hAnsi="Courier New" w:cs="Courier New"/><w:sz w:val="20"/>'
            f'<w:szCs w:val="20"/></w:rPr>'
            f'<w:t xml:space="preserve">{esc(ln) if ln else ""}</w:t></w:r></w:p>')
    return ''.join(out)

def _split_row(line):
    line = line.strip()
    if line.startswith('|'): line = line[1:]
    if line.endswith('|'):   line = line[:-1]
    cells = re.split(r'(?<!\\)\|', line)
    return [c.strip().replace(r'\|', '|') for c in cells]

def table(rows):
    header, body = rows[0], rows[2:]   # rows[1] is the |---| separator
    ncols = len(header)
    total = 9026
    w = total // ncols
    widths = [w] * ncols
    widths[-1] = total - w * (ncols - 1)
    grid = ''.join(f'<w:gridCol w:w="{x}"/>' for x in widths)

    def cell(text, width, hdr):
        shd = ('<w:shd w:val="clear" w:color="auto" w:fill="2C3E50"/>'
               if hdr else '')
        tcpr = (f'<w:tcPr><w:tcW w:w="{width}" w:type="dxa"/>'
                f'<w:tcBorders>'
                f'<w:top w:val="single" w:sz="1" w:space="0" w:color="AAAAAA"/>'
                f'<w:left w:val="single" w:sz="1" w:space="0" w:color="AAAAAA"/>'
                f'<w:bottom w:val="single" w:sz="1" w:space="0" w:color="AAAAAA"/>'
                f'<w:right w:val="single" w:sz="1" w:space="0" w:color="AAAAAA"/>'
                f'</w:tcBorders>{shd}'
                f'<w:tcMar><w:top w:w="60" w:type="dxa"/><w:left w:w="100" w:type="dxa"/>'
                f'<w:bottom w:w="60" w:type="dxa"/><w:right w:w="100" w:type="dxa"/>'
                f'</w:tcMar></w:tcPr>')
        if hdr:
            runs = (f'<w:r><w:rPr><w:b/><w:bCs/><w:color w:val="FFFFFF"/>'
                    f'<w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr>'
                    f'<w:t xml:space="preserve">{esc(text)}</w:t></w:r>')
        else:
            # size-18 body cells: wrap inline() output but force sz18 via paragraph default
            runs = inline_sized(text, 18)
        return (f'<w:tc>{tcpr}<w:p><w:pPr><w:spacing w:before="20" w:after="20"/>'
                f'</w:pPr>{runs}</w:p></w:tc>')

    def row(cells, hdr):
        trpr = '<w:trPr><w:tblHeader/></w:trPr>' if hdr else ''
        tcs = ''.join(cell(c, widths[i] if i < ncols else widths[-1], hdr)
                      for i, c in enumerate(cells[:ncols]))
        # pad short rows
        for i in range(len(cells), ncols):
            tcs += cell('', widths[i], hdr)
        return f'<w:tr>{trpr}{tcs}</w:tr>'

    tblpr = ('<w:tblPr><w:tblW w:w="9026" w:type="dxa"/><w:tblBorders>'
             '<w:top w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
             '<w:left w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
             '<w:bottom w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
             '<w:right w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
             '<w:insideH w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
             '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="auto"/>'
             '</w:tblBorders><w:tblCellMar><w:left w:w="10" w:type="dxa"/>'
             '<w:right w:w="10" w:type="dxa"/></w:tblCellMar>'
             '<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" '
             'w:firstColumn="1" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/></w:tblPr>')
    out = [f'<w:tbl>{tblpr}<w:tblGrid>{grid}</w:tblGrid>']
    out.append(row(header, True))
    for b in body:
        out.append(row(b, False))
    out.append('</w:tbl>')
    out.append('<w:p><w:pPr><w:spacing w:after="120"/></w:pPr></w:p>')  # spacer
    return ''.join(out)

def inline_sized(text, sz):
    """inline() but force a base size on plain runs (for table body cells)."""
    parts = inline(text, SLUGS)
    # inject size into plain <w:r> runs that have no <w:rPr>
    parts = parts.replace('<w:r><w:t',
        f'<w:r><w:rPr><w:color w:val="000000"/><w:sz w:val="{sz}"/>'
        f'<w:szCs w:val="{sz}"/></w:rPr><w:t')
    return parts

# ── markdown parser ─────────────────────────────────────────────────────────
def parse_body(lines):
    blocks, i, n = [], 0, len(lines)
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1; continue
        # fenced code
        if line.lstrip().startswith('```'):
            i += 1; buf = []
            while i < n and not lines[i].lstrip().startswith('```'):
                buf.append(lines[i]); i += 1
            i += 1
            blocks.append(('code', buf)); continue
        # table
        if line.lstrip().startswith('|') and i + 1 < n and re.match(
                r'^\s*\|[\s:|-]+\|\s*$', lines[i+1]):
            rows = []
            while i < n and lines[i].lstrip().startswith('|'):
                rows.append(_split_row(lines[i])); i += 1
            blocks.append(('table', rows)); continue
        # heading
        m = re.match(r'^(#{1,6})\s+(.*)$', line)
        if m:
            blocks.append(('h', len(m.group(1)), m.group(2).strip())); i += 1; continue
        # hr
        if re.match(r'^---+\s*$', line):
            blocks.append(('hr',)); i += 1; continue
        # ordered list
        m = re.match(r'^(\d+)\.\s+(.*)$', line)
        if m:
            blocks.append(('oli', m.group(1), m.group(2))); i += 1; continue
        # unordered list
        m = re.match(r'^[-*]\s+(.*)$', line)
        if m:
            blocks.append(('uli', m.group(1))); i += 1; continue
        # paragraph (gather continuation lines)
        buf = [line.rstrip()]
        i += 1
        while i < n and lines[i].strip() and not re.match(
                r'^(#{1,6}\s|```|\||[-*]\s|\d+\.\s|---+\s*$)', lines[i].lstrip()):
            buf.append(lines[i].rstrip()); i += 1
        blocks.append(('p', ' '.join(buf)))
    return blocks

# ── pre-scan headings for slugs ─────────────────────────────────────────────
def collect_slugs(blocks):
    slugs = set()
    for b in blocks:
        if b[0] == 'h':
            slugs.add(slugify(b[2]))
    return slugs

# ── title page (mirrors v1.0, values updated to v1.1) ───────────────────────
def title_page():
    def c(text, *, sz, color, bold=False, ital=False, after=None, before=None):
        sp = ''
        if before: sp += f'<w:spacing w:before="{before}"'
        if after:  sp = f'<w:spacing w:after="{after}"' if not before else sp + f' w:after="{after}"'
        if sp and not sp.endswith('/>'): sp += '/>'
        b = '<w:b/><w:bCs/>' if bold else ''
        it = '<w:i/><w:iCs/>' if ital else ''
        szx = f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>' if sz else ''
        return (f'<w:p><w:pPr>{sp}<w:jc w:val="center"/></w:pPr>'
                f'<w:r><w:rPr>{b}{it}<w:color w:val="{color}"/>{szx}</w:rPr>'
                f'<w:t xml:space="preserve">{esc(text)}</w:t></w:r></w:p>')
    p = []
    p.append('<w:p><w:pPr><w:spacing w:before="2500"/></w:pPr></w:p>')
    p.append(c('ORCP', sz=72, color='2C3E50', bold=True, after=300))
    p.append(c('Open Robot Control Protocol', sz=36, color='34495E', after=200))
    p.append(c('Specification', sz=30, color='7F8C8D', after=800))
    p.append(c('Version 1.1', sz=26, color='2C3E50', bold=True))
    p.append(c('June 2026', sz=None, color='7F8C8D'))
    # tagline
    p.append('<w:p><w:pPr><w:spacing w:before="1500"/><w:jc w:val="center"/></w:pPr>'
             '<w:r><w:rPr><w:i/><w:iCs/><w:color w:val="7F8C8D"/></w:rPr>'
             '<w:t>A simple, safe, transport-agnostic</w:t></w:r>'
             '<w:r><w:rPr><w:i/><w:iCs/><w:color w:val="7F8C8D"/></w:rPr><w:br/></w:r>'
             '<w:r><w:rPr><w:i/><w:iCs/><w:color w:val="7F8C8D"/></w:rPr>'
             '<w:t>protocol for robot control.</w:t></w:r></w:p>')
    p.append(c('This specification is released under the MIT License.',
               sz=18, color='95A5A6', before=1500))
    p.append(c('You are free to implement, modify, and distribute implementations',
               sz=18, color='95A5A6'))
    p.append(c('of this protocol without restriction.', sz=18, color='95A5A6'))
    # title-page section break (no header/footer on this page)
    p.append('<w:p><w:pPr><w:sectPr><w:pgSz w:w="11906" w:h="16838"/>'
             '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" '
             'w:header="708" w:footer="708" w:gutter="0"/><w:cols w:space="720"/>'
             '<w:docGrid w:linePitch="360"/></w:sectPr></w:pPr></w:p>')
    return ''.join(p)

BODY_SECTPR = ('<w:sectPr><w:headerReference w:type="default" r:id="rId7"/>'
               '<w:footerReference w:type="default" r:id="rId8"/>'
               '<w:pgSz w:w="11906" w:h="16838"/>'
               '<w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" '
               'w:header="708" w:footer="708" w:gutter="0"/><w:cols w:space="720"/>'
               '<w:docGrid w:linePitch="360"/></w:sectPr>')

DOC_OPEN = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" '
            'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
            'xmlns:o="urn:schemas-microsoft-com:office:office" '
            'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
            'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
            'xmlns:v="urn:schemas-microsoft-com:vml" '
            'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
            'xmlns:w10="urn:schemas-microsoft-com:office:word" '
            'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
            'xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" '
            'xmlns:w15="http://schemas.microsoft.com/office/word/2012/wordml" '
            'mc:Ignorable="w14 w15"><w:body>')
DOC_CLOSE = '</w:body></w:document>'

# ── main ────────────────────────────────────────────────────────────────────
md = open(MD, encoding='utf-8').read().split('\n')
# drop YAML/front-matter: everything up to and including the first '---' line
first_hr = next(i for i, l in enumerate(md) if re.match(r'^---+\s*$', l))
body_lines = md[first_hr+1:]
blocks = parse_body(body_lines)
SLUGS = collect_slugs(blocks)

bm = 0
h1_seen = False   # first major section follows the title-page break; rest get their own page
parts = [DOC_OPEN, title_page()]
for b in blocks:
    if b[0] == 'h':
        page_break = (b[1] == 2 and h1_seen)
        parts.append(heading(b[2], b[1], bm, slugify(b[2]), page_break)); bm += 1
        if b[1] == 2:
            h1_seen = True
    elif b[0] == 'p':
        parts.append(para(b[1]))
    elif b[0] == 'code':
        parts.append(code_block(b[1]))
    elif b[0] == 'table':
        parts.append(table(b[1]))
    elif b[0] == 'hr':
        parts.append(hrule())
    elif b[0] == 'oli':
        parts.append(list_item(b[2], b[1] + '.'))
    elif b[0] == 'uli':
        parts.append(list_item(b[1], '•'))
parts.append(BODY_SECTPR)
parts.append(DOC_CLOSE)
document_xml = ''.join(parts)

# ── assemble package ────────────────────────────────────────────────────────
if os.path.exists(BUILD): shutil.rmtree(BUILD)
shutil.copytree(REF, BUILD)

with open(os.path.join(BUILD, 'word/document.xml'), 'w', encoding='utf-8') as f:
    f.write(document_xml)

# header/footer: v1.0 -> v1.1
for fn in ('header1.xml', 'footer1.xml'):
    p = os.path.join(BUILD, 'word', fn)
    t = open(p, encoding='utf-8').read().replace('v1.0', 'v1.1')
    open(p, 'w', encoding='utf-8').write(t)

# append external hyperlink relationships
rels_p = os.path.join(BUILD, 'word/_rels/document.xml.rels')
rels = open(rels_p, encoding='utf-8').read()
extra = ''.join(
    f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/'
    f'officeDocument/2006/relationships/hyperlink" Target="{esc(tgt)}" '
    f'TargetMode="External"/>' for rid, tgt in _rel_links)
rels = rels.replace('</Relationships>', extra + '</Relationships>')
open(rels_p, 'w', encoding='utf-8').write(rels)

# core properties
core_p = os.path.join(BUILD, 'docProps/core.xml')
core = open(core_p, encoding='utf-8').read()
core = re.sub(r'<dc:title>.*?</dc:title>',
              '<dc:title>ORCP — Open Robot Control Protocol, Specification v1.1</dc:title>',
              core)
if '<dc:title>' not in core:
    core = core.replace('</cp:coreProperties>',
        '<dc:title>ORCP — Open Robot Control Protocol, Specification v1.1</dc:title>'
        '</cp:coreProperties>')
core = re.sub(r'<cp:revision>.*?</cp:revision>', '<cp:revision>11</cp:revision>', core)
open(core_p, 'w', encoding='utf-8').write(core)

# zip
if os.path.exists(OUT): os.remove(OUT)
with zipfile.ZipFile(OUT, 'w', zipfile.ZIP_DEFLATED) as z:
    # [Content_Types].xml first is conventional
    ct = os.path.join(BUILD, '[Content_Types].xml')
    z.write(ct, '[Content_Types].xml')
    for root, _, files in os.walk(BUILD):
        for fn in files:
            full = os.path.join(root, fn)
            arc = os.path.relpath(full, BUILD)
            if arc == '[Content_Types].xml': continue
            z.write(full, arc)

print(f"wrote {OUT}")
print(f"  blocks: {len(blocks)}  headings: {bm}  ext-links: {len(_rel_links)}")
