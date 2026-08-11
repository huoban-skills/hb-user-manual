# hb-user-manual

伙伴云图文使用手册生成 Skill（浏览器实测版）：用浏览器实际操作伙伴云系统，走查截图并撰写图文文档，产物为 Markdown + 图片目录。

- 双轨采集：hac 管逻辑真相（字段、自动化、审批流），Playwright 驱动的浏览器管界面真相（截图、交互细节）
- 结构单元只有「章节」：多章套册头成模块手册，单章直接成篇（帮助中心单篇）
- 截图规范：每张图有红框引导、图文交错、密钥自动打码
- 入口：`SKILL.md`；写作规范 `references/writing-guide.md`；走查规范 `references/walkthrough-guide.md`

依赖：`hac`（伙伴云官方 CLI）、`python3` + playwright（chromium）。
