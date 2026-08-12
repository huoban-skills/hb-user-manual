---
name: hb-user-manual
description: >
  用浏览器实际操作伙伴云系统，生成带真实截图的图文文档（Markdown + 图片目录）。
  产物按内容定形态：面向成熟工作区的模块成册手册、面向单一场景的帮助中心单篇，或两者混合。
  当用户提到"图文手册"、"带截图的使用手册"、"实测手册"、"浏览器实测写手册"、
  "配好图的操作手册"、"帮助中心文档"、"帮助文档"时触发。
metadata:
  requires:
    bins: ["hac", "python3"]
---

# 伙伴云图文使用手册生成 Skill（浏览器实测版）

## 核心原则

1. **双轨采集**：hac 管逻辑真相，负责字段配置、自动化逻辑、审批流；浏览器管界面真相，负责真实截图、交互细节、提示文案。二者冲突时以界面实测为准，并在实测笔记里标记。外部平台和纯平台功能没有 hac 兜底，**事实来源**以用户提供加界面实测为准，拿不准标 `[待确认]`；这条只约束事实从哪来，不限制截图由谁截。
2. **浏览器里能打开的都自己截**：不分伙伴云还是外部平台（阿里云、企业微信、飞书等控制台），只要页面已登录，走查和截图都由自己完成，不要让用户代截。唯一的例外是**输入账号密码**：登录动作交给用户，登录完成后继续代劳。外部平台截图前先跟用户确认哪些信息要打码（账号名、UID、密钥、实例地址等），用 `shot --mask` 处理。
3. **按需采集，省 token**：能用一条命令批量落盘的不逐表查；只对写进文档的内容深查配置，不拿全量配置层。
4. **分阶段交互**：范围和骨架让用户确认后再动手；生成后交用户审阅。
5. **面向业务人员写作**：写作规范见 [references/writing-guide.md](references/writing-guide.md)，与截图配合的走查规范见 [references/walkthrough-guide.md](references/walkthrough-guide.md)。

---

## 工作流程

### 阶段〇：环境准备

1. 涉及伙伴云工作区时验证 hac 可用：`hac table list-tables --space-id <space_id>` 试跑，401/403 停止任务让用户检查认证。

2. 启动走查浏览器：

   ```bash
   python3 scripts/browser.py start          # 默认打开 https://app.huoban.com
   ```

   首次使用（或会话失效）让用户在弹出的浏览器窗口里自行登录伙伴云；账号密码由用户输入，不代输。登录态存在持久化 profile（`~/.hb-manual-profile`），之后免登录。

   手册涉及外部平台控制台时同理：让用户先登录该平台（已在自己浏览器里登录的可直接接管那个浏览器），之后的导航和截图自己做。

3. `python3 scripts/browser.py snapshot` 确认已进入工作台（页面文本能看到工作区名）再继续。

### 阶段一：需求对齐 + 现状盘点 + 定骨架

不管写哪种文档，起点是同三件事：

1. **需求对齐**，跟用户问清：写什么（模块 / 场景清单）、给谁看、**演示环境**在哪个工作区/账号。演示环境由用户提供搭好的，本 skill 不负责搭建；场景和流程也只能来自用户，不替用户发明。
2. **现状盘点**：涉及工作区就 `hac table list-tables --space-id <space_id>` 拉表清单，展示给用户确认哪些纳入、哪些排除；确认后 `hac table +resolve-id --table <表名>` 解析成纯数字 table_id 列对照表。不落在任何工作区的内容（纯平台功能、外部平台）记下来，没有元数据可盘。
3. **定文档骨架，让用户确认后才动手**。结构单元只有一种：章节（骨架见 writing-guide「整体结构」），一个章节讲一个业务动作或场景：
   - 内容够多个章节（成熟工作区的模块）就套册头成册：判定模块类型（基础资料 / 业务流程 / 混合），标出主单据、明细表、资料表，划业务闭环，给一版章节清单。
   - 只有单个章节（单一操作、平台功能、跨平台打通）就直接成篇，不写册头；多个独立场景就是多篇，列出文档清单，每篇给篇名和一句话范围。
   - 骨架里把**可选件说清让用户定**：章节内的字段说明、审批说明；册级的「通用操作」章（放正文前）和「典型业务场景」章（放册末，跨章场景连播）。

### 阶段二：轻采集（全部落盘，不进上下文）

只跑清单级命令，输出全部重定向到采集目录，AI 不读原始 JSON：

```bash
hac table er-diagram-collect --space <space_id> --output <采集目录>/facts.json   # 全区表、字段、关系、记录数
# 对范围内每张表（工作区级 automation 搜索会漏快捷按钮和旧版 workflow，必须按表逐个查）：
hac automation list --table-id <tid> --space-id <space_id> > <采集目录>/automation-<tid>.json
hac table form-layout get --table-id <tid> > <采集目录>/layout-<tid>.json
hac procedures list-procedures --space-id <space_id> > <采集目录>/procedures.json
# 落盘后核一眼，0 字节的是采失败了（hac 把错误写 stderr，重定向只留空文件）
wc -c <采集目录>/*.json
```

**采多少由骨架决定，不一律跑全套**：

- 要写字段表的表，四条命令全跑。
- 只需核对演示环境搭了什么的，跑 `er-diagram-collect` 加涉及表的 `automation list`。
- 要讲表单填写才补 `form-layout`，要讲审批才补 `procedures`。
- 内容不落在任何工作区的，记一句"无可采集的工作区"，直接进阶段三。

然后逐章跑摘要脚本，拿紧凑摘要包（一张 40 字段的表约 1.5k token）：

```bash
python3 scripts/digest.py --dir <采集目录> --tables "本章的表,逗号分隔"
```

摘要包含：字段表（按表单主区布局排序、含分组/选项/关联目标/填写提示）、详情页标签页、启用的自动化清单（workflow 类自带触发和执行描述）。把摘要要点展示给用户确认后进循环。

### 阶段三：逐章/逐篇循环（深查 → 走查 → 写作）

按阶段一确认的骨架推进，成册的逐章、单篇的逐篇，每个单元一个闭环：

1. **读本单元摘要包**（digest.py 输出；无可采集工作区的单元跳过）。
2. **按需深查**，只查本单元要写的内容：
   - 重点自动化（会点的按钮、改状态/金额的触发、发通知起审批的）：
     `hac --output-mode purpose automation get --automation-id <id>`（流程/分支/写哪张表的业务投影）；要具体写入值才用 `--output-mode full`。看不懂节点含义用 `hac automation docs` 按 key 切片取。
   - 审批流（procedures.json 里绑定到本单元表的启用流程）：`hac procedures get-procedure --procedure-id <id>` 拿版本 → `hac procedures get-procedure-version` 直读流程图环节。
   - 零散配置（计算公式、自动编号规则、字段显示条件、打印模板）：仅对需要向读者解释的字段跑 `hac --output-mode full table get-table --table-id <id>` / `hac table list-print-templates --table-id <id>` 提取。
   - 字段类型名以 `hac table field-config list-types` 为准，不凭印象写。
3. **浏览器走查 + 截图**，全按 [references/walkthrough-guide.md](references/walkthrough-guide.md) 执行：先从摘要包推导本单元的截图点位清单，再按「看 → 动 → 看 → 截」循环走查。截图存 `<产出目录>/images/`，界面观察记 `notes.md`，落的演示数据登记 `demo-data.md`。
4. **写本单元 Markdown**：规范全按 [references/writing-guide.md](references/writing-guide.md)，含配图规范。图放进它对应的步骤条目里（列表项下缩进 4 空格），用相对路径引用。
5. **渲染 HTML 预览**：`python3 scripts/render.py <文档.md>`，同目录出同名 .html。md 是源文件，人工修改改 md，改完重跑一次；html 只当预览不手改。

一个单元写完再进下一个；上一单元的深查 JSON 和走查细节不带进下一单元上下文。

### 阶段四：自检 + 交付

生成后对照清单逐项自检，能机检的错不留给用户：

- 流程走通：每个操作流程在浏览器里从头到尾走通过，不是照口述或配置誊写。
- 写了字段表的单元：字段覆盖完整（系统过程字段除外）、顺序对齐 form-layout 主区。
- 章节完整：每个二级章节/每篇文档有"注意事项"和"常见问题"。
- 无技术术语：正文无 trigger / automation / 数据触发 / config / API 等黑话。
- 自动化落地："点了之后发生什么"写进了对应位置。
- **每个操作步骤序列有对应截图，图文一致**（回看截图核对文字描述）。
- **截图无真实客户敏感数据**（走查时优先用演示数据入图）。
- 图片引用无死链：每个 `![](images/…)` 都能在 images/ 里找到，且都是相对路径。
- 演示数据已按 demo-data.md 清理。

自检通过后交用户审阅，`[待确认]` `[待补充]` 处需用户校正。

---

## 内置脚本

**digest.py**：读采集目录的落盘文件（facts.json / automation-*.json / layout-*.json），输出章节摘要包 Markdown。AI 只读它的输出，不读原始 JSON。

```bash
python3 scripts/digest.py --dir <采集目录> --tables "表名A,表名B"   # 表名或 table_id 混用均可
```

**render.py**：Markdown → Linear 浅色皮肤 HTML 预览，零依赖零 token。md 的写法约定（缩进图片挂步骤、#### 问句渲染成折叠块、注意事项标题下的列表渲染成提示框）见脚本头注释。

```bash
python3 scripts/render.py <文档.md>    # 同目录出同名 .html
```

**browser.py**：浏览器走查驱动。

`scripts/browser.py`，每个子命令独立执行，浏览器窗口跨命令常驻：

| 命令                                                              | 用途                                                 |
| ----------------------------------------------------------------- | ---------------------------------------------------- |
| `start [--url U]`                                                 | 启动浏览器（持久化登录态），已在运行则跳过           |
| `status` / `page --index N`                                       | 列出页面 / 切换活动页面（点链接可能开新标签，操作后先 status 看落点） |
| `goto --url U`                                                    | 打开页面                                             |
| `snapshot [--max-chars N]`                                        | 页面文本 + 可交互元素编号清单（操作前后都要看）      |
| `click (--index N \| --text T \| --selector S \| --at X,Y)`       | 点击；`--at` 用于菜单项等非标准可点元素              |
| `type --text T [--enter]` / `fill --selector S --value V`         | 输入                                                 |
| `press --keys K` / `scroll --dy N`                                | 按键 / 滚动                                          |
| `wait (--ms N \| --selector S \| --text T)`                       | 等待（SPA 内容没出来时用）                           |
| `shot --path P [--selector S] [--highlight S] [--mask S] [--full-page]` | 截图；`--highlight` 标红框，`--mask` 打码密钥等敏感值 |
| `shot --prep JS --prep-hover S --prep-mouse "x,y;…" --prep-after JS` | 截瞬时界面：下拉/二级菜单在两次调用间会关，要在同一次调用里先摆好再截 |
| `eval --js "..."`                                                 | 调试逃生口                                           |
| `stop`                                                            | 关闭浏览器                                           |

## CLI 铁律

1. `table_id` / `space_id` 必须纯数字，需要 ID 先 `hac table +resolve-id`。
2. 执行 hac 禁止 `2>&1`：stdout 是数据，stderr 是 token 统计。
3. 认证失败（401/403）→ 停止任务，告知用户检查认证配置。
4. 浏览器操作报"连不上浏览器"时重新 `start`；页面内容和预期对不上时先 `snapshot` 看清现状再决定，不盲点。

## 输出规范

一个需求一个目录，成册和单篇可并存：

```
<模块名或主题>/
├── <模块名>.md      # 成册手册（有才出）；源文件，人工修改改这份
├── <模块名>.html    # 预览产物，scripts/render.py 从 md 渲染，改完 md 重跑
├── <篇名A>.md       # 单篇文档，篇名用读者要做的事命名（如「如何设置到期提醒」）
├── <篇名A>.html
├── images/          # 截图，<章节号或篇序号>-<序号>-<短说明>.png
├── notes.md         # 实测笔记（交付时可删）
└── demo-data.md     # 演示数据登记（清理完可删）
```

- 手册标题只写模块名，不追加"使用手册"。
- 流程用文本箭头 `→`，字段说明用表格。
