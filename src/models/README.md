# 模型来源与版本

embedding：Xenova/all-MiniLM-L6-v2 的 ONNX int8 版本，上游为 sentence-transformers/all-MiniLM-L6-v2。

qa：Xenova/distilbert-base-cased-distilled-squad 的 ONNX int8 版本，上游为 distilbert/distilbert-base-cased-distilled-squad，由 Hugging Face 发布，微调自 SQuAD v1.1。

模型卡与文件保持下载原字节，未微调、未改变权重。各目录 model-manifest.json 记录仓库、revision 和实际文件 SHA-256。网络下载通过 hf-mirror.com 的固定 revision 镜像路径取得，来源标识仍指向上游仓库；运行时不下载。

原始模型卡声明 Apache-2.0，许可证全文保留为 Apache-2.0.txt。Xenova ONNX 转换来源和说明随目录 README.md 保留。数据集另按 data/locomo/LICENSE.txt 的 CC BY-NC 4.0 使用。

- https://huggingface.co/Xenova/all-MiniLM-L6-v2
- https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
- https://huggingface.co/Xenova/distilbert-base-cased-distilled-squad
- https://huggingface.co/distilbert/distilbert-base-cased-distilled-squad

本包作者只编写接入与实验代码，不声称训练了上述模型。本地回答是单跨度抽取，不能当作通用生成式 LLM。

## 从 GitHub 克隆后恢复

Git 忽略 `*.onnx` 权重；模型卡、tokenizer、固定 revision 与 SHA-256 清单保留。首次联网运行根目录 `run.bat` 会执行 `download_models.py` 恢复并校验，已恢复后推理离线。也可在 src 目录手动运行 `python download_models.py`。交付 ZIP 的 MANIFEST 包含权重，不能直接当作当前 Git 文件清单。
