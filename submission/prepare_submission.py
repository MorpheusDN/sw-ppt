"""Prepare reviewable M3/M4/M5 email attachments without sending or changing Git history.

Run from any directory with the project's PDF dependencies installed.
Presentation PPTX files are prepared separately with the presentation skill.
"""
from pathlib import Path
from io import BytesIO
import contextlib, hashlib, json, shutil, subprocess, sys, zipfile
from pypdf import PdfReader
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

ROOT=Path(__file__).resolve().parents[1]
READY=ROOT/'submission/ready'
BUILD=ROOT.parent/'tmp/submission-build'
DATE='2026-10-22'

def write(path,text):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding='utf-8')

def render_report(stage,source):
    folder=READY/f'M{stage}'
    md=folder/f'PROJECT-MILESTONE{stage}-2-RISC-V.md'
    text=source.read_text(encoding='utf-8')
    text=text.replace('版本 0.5　2026 年 10 月 20 日','提交整理版 0.5.1　2026 年 10 月 22 日')
    text=text.replace('安装锁定依赖并加载随包模型','安装锁定依赖并按固定版本下载、校验模型')
    text=text.replace('模型权重随包，首次安装依赖后可离线运行。','Git 与本提交包不含 ONNX 权重；首次运行由 download_models.py 下载并校验，完成后可离线推理。')
    text=text.replace('交付包含源码与构建前端、模型及版本哈希','交付包含源码与构建前端、模型恢复脚本及版本哈希')
    text=text.replace('文档、源码、模型、Memory、逐题结果','文档、源码、模型恢复脚本、Memory、逐题结果')
    if stage==4:
        text=text.replace('自动测试总计 54/54 通过。本轮真实模型测试实际执行，未以跳过代替通过。','10/20 归档记录为 54/54 通过。10/22 新克隆环境复测为 49 项通过、5 项模型测试因权重未恢复跳过，两次记录分开保留。')
        text=text.replace('Chrome 浏览器实际验证：','10/20 归档的 Chrome 浏览器验证包括：')
    else:
        text=text.replace('GitHub 推送、成员签字、课堂展示与邮件回执尚未执行，不伪造为已完成。','当前已从 GitHub main 克隆；本次仅在本地整理，未推送。成员签字、课堂展示与邮件回执以真实活动为准。')
    write(md,text)
    # Reuse the repository's established Chinese PDF styles and Markdown renderer.
    builder=(ROOT/'docs/m3/build_srs.py').read_text(encoding='utf-8')
    builder=builder.replace("if line == '<!-- PAGEBREAK -->':","if line in ('<!-- PAGEBREAK -->', '<!-- page -->'):")
    builder=builder.replace("ratios = [.19, .56, .25] if '编号' in rows[0][0] else [.18, .63, .19]", "ratios = ([.25, .15, .20, .20, .20] if count == 5 else [.25] * 4 if count == 4 else [.23, .37, .40])")
    builder=builder.replace("Milestone 3 | Software Requirements Specification | RISC-V",f'Milestone {stage} | RISC-V')
    builder=builder.replace('MILESTONE 3 | v1.0 | 2026-10-20',f'MILESTONE {stage} | 0.5.1 | {DATE}')
    scope={'__file__':str(ROOT/'docs/m3/build_srs.py'),'__name__':'submission_pdf_builder'}
    exec(compile(builder,'submission_pdf_builder','exec'),scope)
    scope['SOURCE']=md
    scope['build'](folder/f'PROJECT-MILESTONE{stage}-2-RISC-V.pdf')

def presentation_pdf(stage):
    folder=READY/f'M{stage}'
    target=folder/f'PROJECT-MILESTONE{stage}-2-RISC-V-Presentation.pdf'
    c=canvas.Canvas(str(target),pagesize=(960,540))
    c.setTitle(f'RISC-V Milestone {stage} Presentation')
    for i in range(1,11):
        image=BUILD/f'm{stage}-final-{i}.png'
        if not image.is_file():raise FileNotFoundError('Render and finalize the presentation first: '+str(image))
        c.drawImage(ImageReader(str(image)),0,0,width=960,height=540)
        c.showPage()
    c.save()
    assert len(PdfReader(target).pages)==10

def snapshot_checks():
    evidence=ROOT/'process/evidence/submission-check-2026-10-22'
    evidence.mkdir(parents=True,exist_ok=True)
    run=subprocess.run([sys.executable,'-m','unittest','discover','-s','tests','-v'],cwd=ROOT/'src',capture_output=True,text=True,encoding='utf-8',errors='replace')
    write(evidence/'unit-tests.txt',run.stdout+run.stderr)
    if run.returncode:raise RuntimeError('Unit tests failed; inspect current evidence')
    checks={'date':DATE,'command':'python -m unittest discover -s tests -v','exit_code':run.returncode,'scope':'fresh-clone local verification; archived evidence is separate','model_weights_present':all((ROOT/f'src/models/{x}/onnx/model_quantized.onnx').exists() for x in ['qa','embedding'])}
    write(evidence/'check.json',json.dumps(checks,ensure_ascii=False,indent=2))
    # Re-score existing predictions; do not call this a new model inference run.
    score=subprocess.run([sys.executable,'summarize_results.py'],cwd=ROOT/'src',capture_output=True,text=True,encoding='utf-8',errors='replace')
    write(evidence/'summary-check.txt',score.stdout+score.stderr)
    if score.returncode:raise RuntimeError('Existing experiment summary check failed')

def bundle(stage):
    folder=READY/f'M{stage}'
    files={}
    def add(p,name=None):
        if p.is_file():files[name or p.relative_to(ROOT).as_posix()]=p.read_bytes()
    for p in (ROOT/'process').rglob('*'):add(p)
    add(ROOT/'README.md')
    add(ROOT/'submission/prepare_submission.py')
    add(ROOT/'docs/m3/milestone-3-srs.md')
    add(ROOT/'output/pdf/PROJECT-MILESTONE3-2-RISC-V.pdf')
    if stage==3:
        for name in ['build_srs.py','requirements.txt','README.md']:add(ROOT/'docs/m3'/name)
    else:
        for p in (ROOT/'src').rglob('*'):
            if any(x in p.parts for x in ['.venv','node_modules','__pycache__','.git']):continue
            if p.suffix in ['.pyc','.onnx'] or p.name in ['.env','imported.json']:continue
            add(p)
        for name in ['run.bat','run-basic.bat']:add(ROOT/name)
        for d in [READY/'M4']+([READY/'M5'] if stage==5 else []):
            for p in d.iterdir():
                if p.suffix not in ['.zip'] and p.name != '邮件草稿.txt':add(p,f'docs/m{d.name[1:]}/{p.name}')
    history=subprocess.check_output(['git','log','-30','--format=%h %aI %an %s'],cwd=ROOT).decode('utf-8')
    files['process/submission-git-history.txt']=history.encode('utf-8')
    files['SUBMISSION-README.md']=(
        f'# RISC-V / Milestone {stage}\n\n本包根据 GitHub main 的本地克隆于 {DATE} 整理。\n'
        '仓库：https://github.com/lkexciting/2026---sre---RISC-V---Project\n\n'
        '组号 2 沿用当前仓库正式 M3。过程记录原样保留；自动化检查不是成员会议或签字。\n'
        'M3 正式基线为 docs/m3/milestone-3-srs.md，不采用新增实现快照替换基线。\n'
        '10/22 复测为 49 项通过、5 项模型测试跳过；10/20 归档结果另存。\n'
        'M4/M5 系统首次运行需安装依赖并下载固定版本模型权重；恢复脚本与哈希随包，权重不随包。\n'
        '实验数值来自已有逐题文件，本次核对汇总，未重新运行模型推理。\n'
        '自建动态标签尚需独立人工复核；当前数据结果不声称为课程官方成绩。\n'
    ).encode('utf-8')
    manifest='\n'.join(f'{hashlib.sha256(b).hexdigest()}  {n}' for n,b in sorted(files.items()))+'\n'
    files['MANIFEST.sha256']=manifest.encode('utf-8')
    target=folder/f'PROJECT-MILESTONE{stage}-2-RISC-V.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in sorted(files.items()):z.writestr(n,b)
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        for row in manifest.splitlines():
            digest,name=row.split('  ',1)
            assert hashlib.sha256(z.read(name)).hexdigest()==digest
    return {'stage':stage,'files':len(files),'zip_bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest()}

def main():
    for stage in [3,4,5]:(READY/f'M{stage}').mkdir(parents=True,exist_ok=True)
    snapshot_checks()
    shutil.copy2(ROOT/'output/pdf/PROJECT-MILESTONE3-2-RISC-V.pdf',READY/'M3/PROJECT-MILESTONE3-2-RISC-V.pdf')
    for stage,name in [(4,'M4-设计与测试报告.md'),(5,'M5-最终报告.md')]:
        render_report(stage,ROOT/f'docs/m{stage}'/name)
        presentation_pdf(stage)
    report=[]
    for stage in [3,4,5]:
        report.append(bundle(stage))
        deadline='2026-10-24 24:00' if stage<5 else '2026-11-09 24:00'
        body=f'''收件人：[填写助教邮箱]
主题：PROJECT-MILESTONE{stage}-2-RISC-V

助教老师您好：

附件为 RISC-V 团队 Milestone {stage} 的报告及过程材料。'''
        if stage>3:body+='展示 PDF 另附，完整源码、运行说明、数据与实验材料见 ZIP。'
        body+='\n项目仓库：https://github.com/lkexciting/2026---sre---RISC-V---Project\n\n请查收，谢谢。\nRISC-V 团队\n'
        write(READY/f'M{stage}/邮件草稿.txt',body)
    write(READY/'打包校验.json',json.dumps(report,ensure_ascii=False,indent=2))
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
