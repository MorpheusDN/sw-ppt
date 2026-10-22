# RISC-V / LoCoMo Dynamic Memory Management

这是 2026 秋季学期软件需求工程课的小组项目。我们组叫 RISC-V，五个人，项目是基于 LoCoMo 数据集做对话记忆的动态管理。

## 项目大概在做什么

长程对话里用户的状态会变，比如一开始说喜欢 A，后来改主意喜欢 B 了。现有的检索方法（比如向量搜索）不知道时间先后，经常把旧状态翻出来混进回答里。我们想搞一个系统，能把对话里的信息抽成结构化记忆，然后自动判断记忆之间是什么关系，查询的时候只返回当前有效的那部分。

具体会实现四种状态关系：RETAIN（留着）、UPDATE（更新）、SUPERSEDE（替代）、CONFLICT（冲突）。后面还会做个 Web 界面用 React + ECharts 把记忆之间的关联画出来，并且和全文检索、向量 RAG 做对比评测。

## 仓库里现在有什么

docs/ 文件夹放各个里程碑的文档源文件（Markdown），转 PDF 之后按课程命名规范提交。

process/ 是课程要求的流程记录，里面分了四个子目录：
- minutes：会议纪要，用 templates 里的模板写的
- plans：迭代计划和每周任务
- templates：会议纪要模板（改了好几版，最后这个比较完整）
- screenshots：看板截图之类的证据，M2 的看板截图已经放进去了

## 分支管理

main 分支受保护，不能直接 push。平时在各自的分支上干活，比如之前搞 M1/M2 文档用了 zys 分支，搞完提 PR 合并。合并之前需要至少一个人 review。

看板地址：https://github.com/users/lkexciting/projects/1/views/1

## 技术栈（暂定）

- 数据处理：Python，用 LoCoMo 数据集
- 状态判断：基于时间推理和语义相似度，不打算上深度学习模型
- 后端：Python Web 框架，提供 API
- 前端：React + ECharts
- 评测：F1、Recall@K、状态判断准确率

## 目前进度

M1（团队工作流）已经交了。M2 提案源文件在 docs/m2/，既有过程材料在 process/。M3 五页 SRS v1.0 已确认定稿，源文件和构建说明见 [docs/m3/README.md](docs/m3/README.md)，PDF 在 output/pdf/，过程包在 output/。后续设计、实现与测试按 SRS 的需求编号和验收用例推进。

## 怎么用这个仓库

现在主要是文档和流程记录，代码还没放上来。等后面开发阶段会在根目录加 src/ 文件夹，到时候这里会更新怎么跑起来的说明。

## 交付物命名

按课程要求：PROJECT-MILESTONE[n]-[team_id]-RISC-V.pdf 和 .zip
