---
name: hb-user-manual
description: >
  为伙伴云应用模块生成面向业务人员的使用手册。当用户提到"使用手册"、"操作手册"、
  "模块使用说明"、"帮我写这个模块怎么用"、"这个模块的使用指南"、"ERP手册"时触发。
  覆盖：确定范围 → 批量采集元数据 → 用户确认表范围 → 按模板生成文档 → 用户确认本地 Markdown 后同步到飞书文档。
metadata:
  requires:
    bins: ["hac"]
---

# 伙伴云使用手册生成 Skill

## 核心原则

1. **数据驱动，不靠猜** — 字段结构、关联关系、自动化规则全部通过 API/CLI 采集，不凭经验编造。
2. **分阶段交互，关键节点等确认** — 采集完先让用户确认表范围，生成后让用户审阅修正。
3. **面向业务人员写作** — 读者是一线操作人员，不是产品经理或开发。用大白话，不用技术术语。
4. **模板分离** — 写作规范在 `references/` 目录，流程控制在本文件。

---

## 工作流程

### 阶段一：确定范围

1. 用户给出模块名称或工作区信息
2. 通过 API 拉取工作区全部表清单
3. **展示表清单，等用户确认**：哪些表纳入本次手册、哪些排除、表的文档顺序
4. 用户确认后才进入采集阶段

这一步非常重要——不要自行判断哪些表属于这个模块，让用户定。

### 阶段二：批量采集元数据

对确认范围内的每张表采集：
- 字段结构（名称、类型、必填、选项值、关联目标表）
- 自动化列表（按钮、数据触发、校验规则等）
- 审批流程（流程中心绑定到表上的流程定义和审批环节）
- 表单布局（主区字段排列、详情页标签页/子表清单）
- 打印模板、单据标题规则、字段显示条件（来自 get-table 完整配置）

表结构采集（hac CLI 优先）：
```bash
hac table list-tables --space-id <space_id>            # 表清单
hac table get-table --table-id <table_id>              # 字段结构（含选项值、关联目标表）
hac automation get --automation-id <automation_id>     # 单条自动化的节点详情（已知 ID 时）
hac table form-layout get --table-id <table_id>        # 表单布局：主区字段排列 + 详情页标签页清单
```
- `form-layout get` 的 `main_layout` 是表单主区字段的实际排列顺序，字段表按这个顺序写；`tabs.items` 是详情页的标签页清单（`sub_table` 子表 / `sub_area` 字段分组），`is_show: false` 的不写进手册。
- 完整配置要补充信息时用 `hac --format json --output-mode full table get-table`（默认精简模式最多展示 30 个字段），从中提取：
  - `print_templates`：打印模板名称（如"销售合同打印"），手册写"可打印XX"；`status` 非启用的不写。
  - `item_title`：单据标题由哪个字段生成（即列表里每条记录显示的名字）。
  - `field_view_conditions`：字段显示条件（满足某条件才显示某些字段），非空时要写进字段说明（"选择XX后才会出现"）。
  - 字段 `config.script.code`：计算字段的公式（带中文字段名，可直接读懂），用来在字段表里解释"这个值是怎么算出来的"；普通字段的 `config.script` 非空时是默认值规则。
  - `auto_number` 字段的 `config.compose`：自动编号规则（前缀 + 日期格式 + 流水位数，`cycle` 是流水重置周期），手册写清单号构成。
  - `sub_table` 字段的 `config.default_setting`：从本表发起新建子表记录时自动填的默认值（如"从订单发起退货入库，入库类型默认为退货入库"）。
  - 数值/金额字段的 `unit_suffix`（单位）、`is_percent`（百分比）、`range`（取值范围），写进字段说明。

审批流程采集（hac procedures，流程中心）：
```bash
hac procedures list-procedures --space-id <space_id>        # 工作区全部流程定义（名称、启用状态、绑定表）
hac procedures list-processes --procedure-id <id> --status agreed --limit 3   # 找已走完的样例实例
hac procedures list-process-logs --process-id <id>          # 从样例实例日志还原审批环节链
```
- `list-procedures` 按 `table_id` 把流程对应到确认范围内的表；`status: disable` 的流程不写进手册（或标注"当前未启用"）。
- hac 没有"流程定义节点图"命令（`get-run-nodes` 不可用），审批环节只能从**已完成实例的执行日志**还原：`user_task` 是人工审批环节，`workflow_task` 是审批联动的自动处理（如"采购状态=待入库"）。
- 单个实例只能还原它实际走过的路径；如果流程有条件分支，多取几个样例实例对比，仍不确定就标 `[待确认]` 问用户。
- 表上没有已完成实例时，环节信息无法采集，标 `[待补充]` 让用户口述。

自动化采集分两段：**先批量出清单（看骨架），再对重点逐条取详情（看逻辑）**。不要只跑第一段就动笔——清单只能告诉你"有这么个按钮/触发"，写不出"点了之后系统到底做了什么"。

**第一段——批量出清单**（hac 没有"按表列出自动化"的命令，必须用内置脚本）：
```bash
python3 scripts/collect_meta.py --tables "表1,表2,..." --detail --output <path>.json
```
脚本一次产出字段结构 + 每张表的自动化清单，依赖 `HB_*` 环境变量认证。
注意：脚本里的 `--detail` 只保留节点骨架（节点类型、名称、跨表写到哪张表），**不含触发条件、字段映射、写入的值、条件分支**——这些是手册要写的关键逻辑，必须靠第二段补。

**第二段——对重点自动化逐条取完整详情**：
```bash
hac automation get --automation-id <automation_id>     # 单条自动化的完整节点配置
```
- 不必逐条全查，只深查**影响业务状态或用户能感知**的自动化：业务人员会点的按钮、改单据状态/库存/金额的数据触发、发通知或起审批的触发。纯内部技术性的（如同步缓存、刷冗余字段）可略过。
- `hac automation get` 返回完整节点配置：触发条件、每个节点写/改了哪些字段、值怎么算、条件分支。看不懂业务含义时，配合 `hb-automation-design` skill 把这条自动化的逻辑翻译成业务语言，再写进手册（如"点「确认收货」后，系统把入库状态改成已入库，并按收货数量回写库存"）。
- 节点配置里有不确定的业务判断，标 `[待确认]` 问用户，不要猜。

采集完展示摘要（每张表的字段数、关联关系、自动化清单 + 已深查的重点自动化逻辑），让用户确认是否完整。

### 阶段三：按模板生成文档

读取 [references/writing-guide.md](references/writing-guide.md) 获取写作规范，生成手册。

生成后交给用户审阅，标注 `[待确认]` 和 `[待补充]` 的地方需要用户校正。

### 阶段四：用户确认后同步到飞书文档

当用户明确确认本地 Markdown 内容没问题，并要求同步到飞书时，执行以下流程。没有确认前不要创建或覆盖飞书文档。

1. 确认目标方式：
   - 用户要新建文档：用 Markdown 文件标题创建新的飞书云文档。
   - 用户给了已有文档 URL：先问清楚是覆盖全文还是追加到末尾。
2. 检查飞书依赖：
   ```bash
   command -v lark-cli
   lark-cli --version
   ```
   如果没有 `lark-cli`，或版本不支持 `docs --api-version v2`，先安装/升级：
   ```bash
   npm install -g @larksuite/cli@latest
   npx skills add larksuite/cli -g -y
   ```
   安装依赖会联网并写全局目录；在受限环境里按当前 Agent 的权限机制请求用户批准。
3. 读取飞书写入规则：
   - 如果本机有 `lark-shared` / `lark-doc` skill，先读取对应 `SKILL.md`，按其中认证和 v2 文档规则执行。
   - `docs +create`、`docs +fetch`、`docs +update` 使用 `--api-version v2`。
4. 授权：
   - 创建或更新文档优先用用户身份：`--as user`。
   - 遇到 `need_user_authorization`、keychain 或 scope 问题时，发起 docs 域授权：
     ```bash
     lark-cli auth login --domain docs
     ```
   - 把终端返回的飞书授权链接和验证码发给用户，等用户完成授权后再继续。
5. 新建文档：
   - `--content @file` 只能引用当前工作目录内的相对路径。先切到 Markdown 所在目录，再执行：
     ```bash
     lark-cli docs +create --api-version v2 --doc-format markdown --content @./<文件名>.md --as user
     ```
   - 记录返回的 `document_id` 和 `url`。
6. 复核：
   ```bash
   lark-cli docs +fetch --api-version v2 --doc <document_id> --detail simple --as user
   ```
   确认标题、正文、表格已导入，再把飞书文档链接发给用户。

---

## 数据采集优先级

1. **表清单 / 字段结构 / 审批流程优先走 hac CLI** — `hac table list-tables`、`hac table get-table`；单条自动化详情用 `hac automation get`；审批流程用 `hac procedures list-procedures / list-processes / list-process-logs`（Python 脚本不覆盖流程中心，审批只有 hac 这一条路）
2. **自动化采集两段式** — 第一段「按表列清单」只能走 `scripts/collect_meta.py`（hac 的 automation 模块只有 create/update/verify/get，没有 list 命令；脚本读 `HB_*` 环境变量认证，只产出节点骨架）；第二段「重点自动化取完整逻辑」走 `hac automation get --automation-id`，配合 `hb-automation-design` 翻译成业务语言。光有第一段写不出"按钮点完发生了什么"
3. **hac 认证失败/未安装时，全程退回 `scripts/collect_meta.py`** — 它同时覆盖表清单、字段结构和自动化采集
4. **以上都不通，再考虑其他 huoban 类 skill**（`huoban-table`、`huoban-automation`、`huoban-workspace`，配合 `hb-automation-design` 分析自动化逻辑）逐表手动采集

每次采集前先试一下 `hac table list-tables`，能跑通就让 hac 承担表结构部分。

## CLI 使用铁律

1. `table_id` / `space_id` 必须是纯数字 ID，禁止传中文名。需要 ID 时先用 `hac table +resolve-id --table <表名>` 解析。
2. 执行 CLI 禁止 `2>&1`，stdout 是数据，stderr 是 token 统计。
3. 认证失败（401/403）→ 停止任务，告知用户检查认证配置。

---

## 输出规范

- 格式：Markdown
- 文件命名：`<模块名>.md`（如 `ERP销售管理.md`）
- 文档一级标题只写模块名：`# <模块名>`，不要追加"使用手册"四个字
- 章节标题用 `##`，子表用 `###`
- 字段说明用表格
- 流程用文本箭头 `→`
