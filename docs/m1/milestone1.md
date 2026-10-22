# Milestone 1: Team Workflow
**Team Name**: RISC-V  
**Course**: Software Requirements Engineering (2026)  
**Date**: October 9, 2026

---

## 1. Team Name
- **名称**: RISC-V

## 2. Team Roles and Responsibilities
| 成员   | 角色                         | 职责                                                       | 例子                                                         |
| ------ | ---------------------------- | ---------------------------------------------------------- | ------------------------------------------------------------ |
| 周一烁 | Project Manager (PM)         | 统筹进度、分配任务、风险管控                               | 每周六创建 GitHub Issue 列出下周行动项；用 Notion 看板跟踪里程碑 |
| 米冬妮 | Git Master                   | 仓库权限管理、分支策略、CI 检查                            | 配置 `main` 分支保护，要求所有更新通过 Pull Request；制定 commit 规范 |
| 周卓然 | Requirements & Memory Schema | 需求分析、Memory JSON 字段设计                             | 定义 `memory_id`, `entity`, `state` 等字段；编写 SRS 初稿    |
| 蒋恺家 | Retrieval & State Logic      | 检索算法、状态关系判断（RETAIN/UPDATE/SUPERSEDE/CONFLICT） | 实现基于时间推理的 Memory 更新逻辑；编写单元测试             |
| 狄毓灵 | Frontend & Visualization     | Web 界面、记忆可视化、证据展示                             | 用 React 展示结构化 Memory 及其原始对话片段；集成 ECharts 关系图 |

## 3. Project Management Strategy

### 3.1 Communication & Meetings
- **Weekly Meeting**: 每周六 20:00–21:00
- **Arranger**: 周一烁
- **Minutes Recorder**: 米冬妮
- **Example Agenda**:
  - 20:00–20:10 回顾本周完成项
  - 20:10–20:30 讨论 M3 SRS 草稿中的状态关系定义
  - 20:30–20:50 分配下周任务
  - 20:50–21:00 风险 buffer 检查

### 3.2 Meeting Minutes Template

> 会议纪要模板如下，每次会议后按此格式填写并存入 `process/minutes/`：

| 字段         | 填写说明                       | 例子                                                         |
| ------------ | ------------------------------ | ------------------------------------------------------------ |
| Attendees    | 列出实际参与成员               | 周一烁, 米冬妮, 周卓然, 蒋恺家, 狄毓灵                       |
| Absent       | 列出缺席成员                   | 无                                                           |
| Agenda       | 本次会议主题                   | M1 文档评审                                                  |
| Decisions    | 关键决策逐条列出               | 1. 采用 DimMem 三路检索作为 baseline；2. Memory JSON 字段扩展至 12 个 |
| Action Items | 表格：任务 / 负责人 / 截止日期 | 完成 M1 PDF 终稿 / 周一烁 / 10-09                            |

### 3.3 Tools
- **Version Control**: Git + GitHub 
- **Documentation**: Markdown → PDF
- **Project Management**: Notion+ GitHub Projects
- **Communication**: 微信群+ 腾讯会议

## 4. Plan / Timeline (with Buffers & Iterations)

**核心要求**：每个里程碑至少 2 轮迭代，且计划中包含 buffer。

| 里程碑           | 迭代   | 行动项                                    | 开始  | 结束  | Buffer            |
| ---------------- | ------ | ----------------------------------------- | ----- | ----- | ----------------- |
| M1 Team Workflow | Iter 1 | 起草团队规则、角色分配、初版计划          | 09/25 | 09/28 | 09/29–09/30 (2天) |
|                  | Iter 2 | 评审规则、修改文档、定稿 PDF、打包 ZIP    | 10/01 | 10/05 | 10/06–10/08 (3天) |
| M2 Proposal      | Iter 1 | 撰写愿景、范围、功能路线图、初版 slides   | 09/29 | 10/03 | 10/04–10/05 (2天) |
|                  | Iter 2 | 内部预演、修改提案、生成 PDF              | 10/06 | 10/08 | 10/09 (1天)       |
| M3 SRS           | Iter 1 | 需求规格草稿（Memory 字段、状态关系定义） | 10/11 | 10/12 | 10/13 (1天)       |
|                  | Iter 2 | 组内评审、修改、最终版 SRS PDF            | 10/14 | 10/16 | 10/17 (1天)       |
| M4 Mid-term      | Iter 1 | 系统设计、核心编码、初步测试、展示草稿    | 10/18 | 10/19 | 10/20(1天)        |
|                  | Iter 2 | 集成测试、Bug 修复、展示排练、终版 PDF    | 10/21 | 10/23 | 10/24(1天)        |
| M5 Final         | Iter 1 | 完整系统测试、实验分析、报告草稿          | 10/25 | 11/1  | 11/ 2(1天)        |
|                  | Iter 2 | 最终评测、报告定稿、展示排练、提交 ZIP    | 11/3  | 11/8  | 11/9 (1天)        |

## 5. Version Control Setup

### 5.1 Repository
- **URL**: https://github.com/lkexciting/2026---sre---RISC-V---Project（private）
- **Members**: 5 人全部邀请为 Collaborator，权限设为 `Write`
- **Access Control**:
  - `main` 分支：仅允许通过 Pull Request 合并，需至少 1 名成员 review
  - `dev` 分支：开发主分支，允许直接 push
  - `docs` 分支：文档专用，用于 M1/M2/M3 文档迭代

### 5.2 Commit Conventions
格式：`<type>(<scope>): <subject>`

| type     | 含义      | 样例                                                   |
| -------- | --------- | ------------------------------------------------------ |
| feat     | 新功能    | `feat(memory): implement JSON export with state field` |
| fix      | 修复      | `fix(retrieval): correct timestamp parsing`            |
| docs     | 文档      | `docs(m1): add team roles and responsibilities`        |
| style    | 格式      | `style(web): format React components`                  |
| refactor | 重构      | `refactor(retrieval): simplify state logic`            |
| test     | 测试      | `test(memory): add unit tests for state update`        |
| chore    | 构建/依赖 | `chore(git): update branch protection rules`           |

### 5.3 Version Tag
- `v0.1-m1-draft`（M1 初稿）
- `v0.2-m1-final`（M1 最终版）
- `v1.0-m2-proposal`（M2 提案）

### 5.4 Tracking Start
- 从第一个交付物初稿开始，所有更改均通过 Git 跟踪。

## 6. Process Folder Structure (in Repo)

仓库内需建立 `process/` 文件夹，结构如下：

process/

├── minutes/

│   ├── 2026-09-26-weekly.md

│   └── 2026-10-03-weekly.md

├── plans/

│   ├── milestone-timeline.md

│   └── weekly-action-items.md

├── templates/

│   └── meeting-minutes-template.md

└── screenshots/

├── github-repo-setup.png

└── notion-board.png