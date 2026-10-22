"""Build and verify the M3 submission ZIP (run after building the PDF)."""
from pathlib import Path
import hashlib
import re
import subprocess
import zipfile
from io import BytesIO
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[2]
PDF = ROOT / 'output/pdf/PROJECT-MILESTONE3-2-RISC-V.pdf'
DEST = ROOT / 'output/PROJECT-MILESTONE3-2-RISC-V.zip'


def normalized(text):
    return re.sub(r'\s+', '', text.replace('**', '').replace('`', ''))


def verify_pdf():
    reader = PdfReader(str(PDF))
    assert len(reader.pages) == 5, 'PDF must contain exactly five pages'
    pages = (ROOT / 'docs/m3/milestone-3-srs.md').read_text(encoding='utf-8').split('<!-- PAGEBREAK -->')
    assert len(pages) == 5
    for number, (source, page) in enumerate(zip(pages, reader.pages), 1):
        actual = normalized(page.extract_text())
        for line in source.splitlines():
            line = line.strip()
            if not line:
                continue
            chunks = line.strip('|').split('|') if line.startswith('|') else [line.lstrip('# ')]
            for chunk in chunks:
                if re.fullmatch(r'\s*:?-+:?\s*', chunk):
                    continue
                assert normalized(chunk) in actual, f'Source/PDF mismatch, page {number}: {chunk[:80]}'


def main():
    verify_pdf()
    files = sorted(p for folder in ('docs/m3', 'process') for p in (ROOT / folder).rglob('*')
                   if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
    files += [PDF, ROOT / 'README.md']
    manifest = []
    with zipfile.ZipFile(DEST, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            name = path.relative_to(ROOT).as_posix()
            data = path.read_bytes()
            archive.writestr(name, data)
            manifest.append(f'{hashlib.sha256(data).hexdigest()}  {name}')
        history = subprocess.check_output(
            ['git', 'log', '-12', '--format=%h %aI %an <%ae> %s'], cwd=ROOT).decode('utf-8')
        archive.writestr('process/m3-git-history.txt', history.encode('utf-8'))
        manifest.append(f"{hashlib.sha256(history.encode('utf-8')).hexdigest()}  process/m3-git-history.txt")
        archive.writestr('MANIFEST.sha256', '\n'.join(manifest) + '\n')
    with zipfile.ZipFile(DEST) as archive:
        assert archive.testzip() is None
        assert len(PdfReader(BytesIO(archive.read(PDF.relative_to(ROOT).as_posix()))).pages) == 5
        for entry in archive.read('MANIFEST.sha256').decode('utf-8').splitlines():
            digest, name = entry.split('  ', 1)
            assert hashlib.sha256(archive.read(name)).hexdigest() == digest
        print(f'ZIP verified: {len(archive.namelist())} entries; PDF=5 pages; SHA256 entries verified.')
    print(DEST)


if __name__ == '__main__':
    main()
