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

采集脚本：`scripts/collect_meta.py`
```bash
python3 scripts/collect_meta.py --tables "表1,表2,..." --detail --output <path>.json
```

采集完展示摘要（每张表的字段数、关联关系、自动化），让用户确认是否完整。

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

1. **优先走 hac CLI** — 表结构用 `hac table get-table`，自动化用 `hac automation get`，表清单用 `hac table list-tables`
2. **hac 不可用时（认证失败/未安装），退回 `scripts/collect_meta.py`** — 使用本 skill 内置的 Huoban automation API 客户端，读取环境变量认证后批量采集
3. **以上都不通，再考虑其他 hb/huoban 类 skill**（hb-button、hb-call、hb-data-trigger、huoban-table 等）逐表手动采集

不要跳过 hac 直接用备选方案。每次采集前先试一下 `hac table list-tables`，能跑通就用 hac。

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
