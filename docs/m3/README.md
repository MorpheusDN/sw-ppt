# Milestone 3：五页 SRS

Team 2 / RISC-V，2026-10-20。正式版本：v1.0。

## 文件

- `milestone-3-srs.md`：唯一正文源文件，`<!-- PAGEBREAK -->` 固定五页分组。
- `build_srs.py`：从源文件生成 PDF；自动检查页数恰为五页。
- `../../output/pdf/PROJECT-MILESTONE3-2-RISC-V.pdf`：五页正文。
- `../../output/PROJECT-MILESTONE3-2-RISC-V.zip`：正文、构建源文件和真实过程材料。
- `../../process/reviews/2026-10-19-m3-review.md`：文档自查、修订与视觉核查记录。
- `../../process/plans/m3-iterations.md`：迭代与确认记录。

## 构建

Python 3.10+，依赖 `reportlab`、`pypdf`；默认使用 Windows 的 `C:/Windows/Fonts/simhei.ttf`。
其他环境请设置 `SRS_FONT_PATH` 为可嵌入的中文 TrueType 字体路径。字体仅用于本地构建，不拷贝字体文件进仓库。

```powershell
python -m pip install -r docs/m3/requirements.txt
python docs/m3/build_srs.py
```

可用 `--output` 指定输出路径。视觉复核可用 Poppler：

```powershell
pdftoppm -scale-to 1400 -png output/pdf/PROJECT-MILESTONE3-2-RISC-V.pdf tmp/pdfs/m3
```

过程包由 `package_m3.py` 生成；在完成文字、PDF 和过程记录修改后执行：

```powershell
python docs/m3/package_m3.py
```

ZIP 自检包括 CRC、必需文件、PDF 页数和源文件/PDF 一致性；其中包含 `MANIFEST.sha256` 和生成时 Git 历史。包内归档文档及过程材料，保留 M1/M2 的已有历史记录。

## 提交与状态

开发分支：`codex/milestone3-srs`；PR：[#14](https://github.com/lkexciting/2026---sre---RISC-V---Project/pull/14)。Git 提交归属 DylanUncle，作者名 Dylan。

2026-10-20，负责人确认文档并授权定稿、提交与合并。正文、PDF 和过程包同步更新为 v1.0。构建与验收说明见上文及 SRS 第 7 节。

## M3/M4/M5 实现补充快照

本次新增 `M3-SRS.md` / `M3-SRS.pdf`、`M3-详细附录.md` 和 `M3-模型图.md`，用于记录同步前实现的需求解释与接口。它们不替换上文 v1.0 正式需求基线，需求编号也未声称与正式基线一一相同。M4/M5 实现与实验仍须结合正式 SRS 验收；54 项自动测试通过不等于 T01–T12 全部已由团队验收。
