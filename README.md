# hb-user-manual

伙伴云图文手册生成 Skill（浏览器实测版）：用浏览器实际操作伙伴云系统，走查截图并撰写图文文档，产物为 Markdown + 图片目录。

- 两种产物二选一：**使用手册**（面向业务操作者，讲"我该做什么"）、**配置手册**（面向管理员，讲"在哪配的、为什么、改了影响什么"），一次任务只出一本
- 双轨采集：hac 管逻辑真相（字段、自动化、审批流），Playwright 驱动的浏览器管界面真相（截图、交互细节）
- 使用手册形态唯一成册；业务流程章开篇配 `scripts/flow.py` 渲染的业务流程图
- 截图规范：标注框非必要不画、多框自动标 ①②③ 序号、脱敏合并模糊带且不遮系统文字
- 产物：Markdown（源文件）+ 同名 HTML 预览（`scripts/render.py` 零 token 渲染，Linear 浅色皮肤）
- 入口：`SKILL.md`；术语 `CONTEXT.md`；使用手册规范 `references/writing-guide.md`；配置手册规范 `references/config-writing-guide.md`；走查规范 `references/walkthrough-guide.md`

依赖：`hac`（伙伴云官方 CLI）、`python3` + playwright（chromium）。
