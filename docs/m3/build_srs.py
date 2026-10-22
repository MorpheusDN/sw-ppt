"""Build the five-page SRS from its Markdown source. Requires reportlab/pypdf.

Usage: python docs/m3/build_srs.py
Optional: --output /absolute/path.pdf
"""
from pathlib import Path
import argparse
import html
import os
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path(__file__).with_name('milestone-3-srs.md')
DEFAULT_OUTPUT = ROOT / 'output/pdf/PROJECT-MILESTONE3-2-RISC-V.pdf'


def inline(text):
    text = html.escape(text)
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    return re.sub(r'`([^`]+)`', r'<font color="#334155">\1</font>', text)


def build(output):
    font_path = os.environ.get('SRS_FONT_PATH', 'C:/Windows/Fonts/simhei.ttf')
    if not Path(font_path).is_file():
        raise SystemExit('Set SRS_FONT_PATH to a Chinese TrueType font, e.g. SimHei.')
    pdfmetrics.registerFont(TTFont('SRS', font_path))
    pdfmetrics.registerFontFamily('SRS', normal='SRS', bold='SRS', italic='SRS', boldItalic='SRS')
    body = ParagraphStyle('body', fontName='SRS', fontSize=9.5, leading=14.2,
                          textColor=colors.HexColor('#243247'), spaceAfter=7, wordWrap='CJK')
    cell = ParagraphStyle('cell', parent=body, fontSize=8.5, leading=12, spaceAfter=0)
    header = ParagraphStyle('header', parent=cell, textColor=colors.white)
    title = ParagraphStyle('title', parent=body, fontSize=21, leading=28, spaceAfter=11,
                           textColor=colors.HexColor('#163455'))
    section = ParagraphStyle('section', parent=body, fontSize=12, leading=18,
                             spaceBefore=6, spaceAfter=8, textColor=colors.HexColor('#163455'))
    output.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(output), pagesize=A4, leftMargin=38, rightMargin=38,
                            topMargin=42, bottomMargin=38,
                            title='Milestone 3 | Software Requirements Specification | RISC-V',
                            author='Team 2 / RISC-V')
    story = []
    lines = SOURCE.read_text(encoding='utf-8').splitlines()
    index = 0
    while index < len(lines):
        line = lines[index].strip()
        if not line:
            index += 1
            continue
        if line == '<!-- PAGEBREAK -->':
            story.append(PageBreak())
        elif line.startswith('# '):
            story.append(Paragraph(inline(line[2:]), title))
        elif line.startswith('## '):
            story.append(Paragraph(inline(line[3:]), section))
        elif line.startswith('|'):
            rows = []
            while index < len(lines) and lines[index].strip().startswith('|'):
                cells = [x.strip() for x in lines[index].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?', x) for x in cells):
                    rows.append(cells)
                index += 1
            count = len(rows[0])
            if count == 2:
                widths = [doc.width * .23, doc.width * .77]
            else:
                # Functional requirements need room for behavior and errors;
                # test tables use a narrower traceability column.
                ratios = [.19, .56, .25] if '编号' in rows[0][0] else [.18, .63, .19]
                widths = [doc.width * r for r in ratios]
            data = [[Paragraph(inline(value), header if r == 0 else cell)
                     for value in row] for r, row in enumerate(rows)]
            table = Table(data, colWidths=widths, repeatRows=1, hAlign='LEFT')
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#163455')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f1f5fa'), colors.white]),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 6),
                ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
                ('LINEBELOW', (0, 0), (-1, 0), .5, colors.HexColor('#163455')),
                ('LINEBELOW', (0, 1), (-1, -1), .3, colors.HexColor('#d5dfeb')),
            ]))
            story.extend([table, Spacer(1, 8)])
            continue
        else:
            paragraph = [line]
            while index + 1 < len(lines) and lines[index + 1].strip() and not lines[index + 1].strip().startswith(('#', '|', '<!--')):
                index += 1
                paragraph.append(lines[index].strip())
            story.append(Paragraph(inline(' '.join(paragraph)), body))
        index += 1

    def furniture(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor('#d5dfeb'))
        canvas.line(38, A4[1] - 29, A4[0] - 38, A4[1] - 29)
        canvas.setFont('SRS', 8)
        canvas.setFillColor(colors.HexColor('#61738b'))
        canvas.drawString(38, A4[1] - 22, 'RISC-V / TEAM 2     SOFTWARE REQUIREMENTS ENGINEERING')
        canvas.drawString(38, 22, 'MILESTONE 3 | v1.0 | 2026-10-20')
        canvas.drawRightString(A4[0] - 38, 22, f'{document.page} / 5')
        canvas.restoreState()

    doc.build(story, onFirstPage=furniture, onLaterPages=furniture)
    reader = PdfReader(str(output))
    if len(reader.pages) != 5:
        raise SystemExit(f'Expected exactly 5 pages, got {len(reader.pages)}: {output}')
    for number, page in enumerate(reader.pages, 1):
        print(f'Page {number}: {len(page.extract_text())} text characters')
    print(output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    build(parser.parse_args().output)
