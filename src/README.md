# 本地模型版运行说明

Python 3.12 推荐。双击项目根目录 run.bat，脚本在 src/.venv 安装 requirements-models.txt，并按固定 revision 下载、校验 MiniLM 和 DistilBERT ONNX 权重（Git 不含权重）。首次安装依赖和恢复模型需要网络，之后推理离线。没有模型依赖时可运行根目录 run-basic.bat，提供词法和规则演示。

```powershell
python -m pip install -r requirements-models.txt
python download_models.py
python server.py --data data/project-conversations.json --vector-model models/embedding --qa-model models/qa
```

打开 http://127.0.0.1:8765 。默认真实数据为团队自主选择的六段，选择及 4＋2 划分已记录。当前阶段、历史状态和来源图可使用快捷示例。一般英文问题勾选“通用问答”并选 Vector RAG；历史状态问题应明确日期。Full Text 会处理完整历史的全部重叠窗口，CPU 查询较慢。

模型不能综合多跳或完整列表，未知时间和计划可能导致动态方法拒答。Full Text 为全文窗口抽取式 QA，不是长上下文生成式 LLM。具体失败与数字见 docs/m5；没有以词法替代真实向量。

```powershell
python prepare_data.py
python prepare_dynamic.py
python -m unittest discover -s tests -v
python run_benchmarks.py
python summarize_results.py
```

动态诊断的预测和评分另见 docs/m5/M5-实验协议与复现.md。results/memory.locomo-six.json 是 10207 条记忆导出；原始输入、问题和黄金评分文件分别保存，gold 不传入预测模块。

修改前端时进入 frontend 执行 npm ci、npm run build；构建产物位于 web。默认运行已有产物，不使用 CDN。模型和第三方代码来源、权重 revision、文件哈希及许可证保留在 models 和 frontend/licenses。
