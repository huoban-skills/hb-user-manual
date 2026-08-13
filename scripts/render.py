#!/usr/bin/env python3
"""把手册 Markdown 渲染成 Linear 浅色皮肤的 HTML 预览（零依赖，图片走相对路径）。

用法：
  python3 render.py <文档.md> [输出.html]      # 省略输出则同名 .html

Markdown 约定（与 writing-guide 一致，只认这些）：
  # 标题            册头/篇名；紧随其后的第一段渲染为导语，自动插目录
  ## 一、章节名      二级章节，自动进目录
  ### 1.1 小节名     三级小节，编号渲染为主题色
  #### 问题？        「常见问题」下的一条，渲染成可折叠块
  1. 步骤            有序列表；紧跟其后缩进 4 空格的图片/文字挂进这一条
      ![图 1-1：说明](images/1-1-x.png)
  - 要点             无序列表；「注意事项」标题下的自动渲染成琥珀提示框
  | 表头 | ... |     表格
  ```                代码块
  > 引用
  行内：**粗**、`代码`、[文字](链接)、[待确认] [待补充] 自动高亮
"""

from __future__ import annotations

import html as ihtml
import re
import sys
from pathlib import Path

CSS = """
:root{
  --brand:#5E6AD2; --brand-weak:#EEEFFB; --brand-line:#C9CDF0;
  --bg:#FCFCFD; --card:#FFFFFF; --sunken:#F6F6F8;
  --ink:#0F1015; --ink-2:#484B54; --ink-3:#8A8F98;
  --line:#E9EAEC; --warn:#D4900C; --warn-bg:#FBF3E2;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.8 "Inter",-apple-system,BlinkMacSystemFont,"PingFang SC","Hiragino Sans GB","Microsoft YaHei",sans-serif;
  -webkit-font-smoothing:antialiased}
.page{max-width:860px;margin:0 auto;padding:56px 32px 96px}
h1{font-size:26px;font-weight:600;letter-spacing:-.3px;line-height:1.35;margin:0 0 10px}
p.intro{color:var(--ink-3);margin:0 0 40px}
h2{font-size:20px;font-weight:600;letter-spacing:-.2px;line-height:1.35;margin:56px 0 16px}
h3{font-size:15px;font-weight:650;margin:34px 0 12px}
h3 .sn{color:var(--brand);font-weight:650;margin-right:7px}
nav.toc{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:18px 24px;margin:0 0 8px}
nav.toc .toc-title{font-size:12px;font-weight:600;letter-spacing:.5px;text-transform:uppercase;color:var(--ink-3);margin-bottom:10px}
nav.toc ol{margin:0;padding-left:20px}
nav.toc li{margin:3px 0}
nav.toc a{color:var(--ink-2);text-decoration:none}
nav.toc a:hover{color:var(--brand)}
ol.steps{padding-left:24px;margin:12px 0}
ol.steps>li{margin:8px 0}
ol.steps>li::marker{color:var(--brand);font-weight:650}
figure{margin:18px 0 26px}
ol.steps figure{margin:12px 0 20px}
figure img{max-width:100%;max-height:620px;width:auto;border:1px solid var(--line);border-radius:8px;
  box-shadow:0 1px 3px rgba(15,16,21,.05);display:block}
figure.tall img{max-height:420px}
figcaption{color:var(--ink-3);font-size:13px;margin-top:9px}
table{width:100%;border-collapse:collapse;font-size:13.5px;margin:14px 0 22px}
th{color:var(--ink-3);font-weight:650;font-size:12px;letter-spacing:.4px;text-align:left;
  border-bottom:1px solid var(--ink-3);padding:0 16px 9px 0}
td{border:0;border-bottom:1px solid var(--line);padding:11px 16px 11px 0;text-align:left;vertical-align:top}
td:first-child{font-weight:650;color:var(--ink-2);white-space:nowrap}
.notice{background:var(--warn-bg);border:1px solid var(--warn-bg);border-left:2px solid var(--warn);
  border-radius:8px;padding:14px 20px;margin:14px 0}
.notice ul{margin:0;padding-left:18px}
.notice li{margin:4px 0}
details.faq{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 20px;margin:10px 0}
details.faq summary{font-weight:650;cursor:pointer;color:var(--ink)}
details.faq summary::marker{color:var(--brand)}
details.faq[open] summary{margin-bottom:8px}
blockquote{margin:12px 0;padding:10px 16px;color:var(--ink-2);border-left:2px solid var(--brand-line);
  background:var(--brand-weak);border-radius:0 8px 8px 0}
code{font-family:ui-monospace,SFMono-Regular,"SF Mono",Menlo,Consolas,monospace;font-size:.92em;
  background:var(--sunken);border:1px solid var(--line);border-radius:4px;padding:1px 5px}
pre{background:var(--sunken);border:1px solid var(--line);border-radius:8px;padding:14px 16px;
  overflow-x:auto;font-size:12.5px;line-height:1.7}
pre code{background:none;border:0;padding:0}
.todo{color:var(--warn);font-weight:650}
a{color:var(--brand)}
@media print{body{background:#fff}.page{padding:0}details.faq{break-inside:avoid}figure{break-inside:avoid}}
"""

TOC_JS = """
const toc=document.getElementById('toc');
if(toc){document.querySelectorAll('h2[id]').forEach(h=>{
  const li=document.createElement('li');
  li.innerHTML='<a href="#'+h.id+'">'+h.textContent+'</a>';
  toc.appendChild(li);});
  if(!toc.children.length)toc.closest('nav').remove();}
"""

IMG_RE = re.compile(r"^\s*!\[([^\]]*)\]\(([^)]+)\)\s*$")


def inline(text: str) -> str:
    """行内标记：链接、粗体、行内代码、[待确认] 高亮。"""
    out, codes = text, []

    def stash(m):
        codes.append(m.group(1))
        return f"\x00{len(codes) - 1}\x00"

    out = re.sub(r"`([^`]+)`", stash, out)
    out = ihtml.escape(out, quote=False)
    out = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank">\1</a>', out)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(\[待确认\]|\[待补充\])", r'<span class="todo">\1</span>', out)
    for i, c in enumerate(codes):
        out = out.replace(f"\x00{i}\x00", f"<code>{ihtml.escape(c)}</code>")
    return out


def is_tall(src: str, base: Path) -> bool:
    """竖图（高>宽）限得更矮，避免撑版。读 PNG 头拿宽高，不依赖图像库。"""
    p = base / src
    try:
        data = p.read_bytes()
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            w = int.from_bytes(data[16:20], "big")
            h = int.from_bytes(data[20:24], "big")
            return h > w
    except Exception:
        pass
    return False


def table_html(rows) -> str:
    if len(rows) >= 2 and set("".join(rows[1])) <= set("-: "):
        head, body = rows[0], rows[2:]
    else:
        head, body = rows[0], rows[1:]
    cells = "".join(f"<th>{inline(c)}</th>" for c in head)
    out = [f"<table><thead><tr>{cells}</tr></thead><tbody>"]
    for r in body:
        out.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def figure_html(alt: str, src: str, base: Path) -> str:
    cls = ' class="tall"' if is_tall(src, base) else ""
    return (f'<figure{cls}><img src="{src}" alt="{ihtml.escape(alt)}">'
            f"<figcaption>{inline(alt)}</figcaption></figure>")


def render(md: str, base: Path) -> str:
    lines = md.splitlines()
    out: list[str] = []
    i, n = 0, len(lines)
    section = ""          # 当前二/三级标题，用来判断注意事项、常见问题
    faq_open = False
    h2_count = 0

    def close_faq():
        nonlocal faq_open
        if faq_open:
            out.append("</details>")
            faq_open = False

    while i < n:
        line = lines[i]

        if not line.strip():
            i += 1
            continue

        # 代码块
        if line.startswith("```"):
            i += 1
            buf = []
            while i < n and not lines[i].startswith("```"):
                buf.append(lines[i])
                i += 1
            i += 1
            out.append("<pre><code>" + ihtml.escape("\n".join(buf)) + "</code></pre>")
            continue

        # 标题
        m = re.match(r"^(#{1,4})\s+(.*)$", line)
        if m:
            level, title = len(m.group(1)), m.group(2).strip()
            if level == 1:
                close_faq()
                out.append(f"<h1>{inline(title)}</h1>")
                i += 1
                while i < n and not lines[i].strip():
                    i += 1
                if i < n and not lines[i].startswith("#"):
                    out.append(f'<p class="intro">{inline(lines[i].strip())}</p>')
                    i += 1
                out.append('<nav class="toc"><div class="toc-title">目录</div><ol id="toc"></ol></nav>')
                continue
            if level == 2:
                close_faq()
                section = title
                h2_count += 1
                out.append(f'<h2 id="ch{h2_count}">{inline(title)}</h2>')
            elif level == 3:
                close_faq()
                section = title
                sn = re.match(r"^([\d.]+)\s+(.*)$", title)
                if sn:
                    out.append(f'<h3><span class="sn">{sn.group(1)}</span>{inline(sn.group(2))}</h3>')
                else:
                    out.append(f"<h3>{inline(title)}</h3>")
            else:  # #### 常见问题条目
                close_faq()
                out.append(f'<details class="faq"><summary>{inline(title)}</summary>')
                faq_open = True
            i += 1
            continue

        # 表格
        if line.lstrip().startswith("|"):
            rows = []
            while i < n and lines[i].lstrip().startswith("|"):
                rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            out.append(table_html(rows))
            continue

        # 有序列表（缩进 4 空格的图片/表格/代码块/段落挂进对应条目）
        if re.match(r"^\d+\.\s+", line):
            out.append('<ol class="steps">')
            while i < n:
                m2 = re.match(r"^\d+\.\s+(.*)$", lines[i])
                if not m2:
                    break
                item = [f"<li>{inline(m2.group(1))}"]
                i += 1
                while i < n:
                    # 空行不代表条目结束：往后看还有缩进内容就继续挂
                    if not lines[i].strip():
                        j = i + 1
                        while j < n and not lines[j].strip():
                            j += 1
                        if j < n and lines[j].startswith("    "):
                            i = j
                            continue
                        i = j
                        break
                    if not lines[i].startswith("    "):
                        break
                    body = lines[i][4:]
                    if body.startswith("```"):
                        i += 1
                        buf = []
                        while i < n and not lines[i].strip().startswith("```"):
                            buf.append(lines[i][4:] if lines[i].startswith("    ") else lines[i])
                            i += 1
                        i += 1
                        item.append("<pre><code>" + ihtml.escape("\n".join(buf)) + "</code></pre>")
                        continue
                    if body.lstrip().startswith("|"):
                        rows = []
                        while i < n and lines[i].strip().startswith("|"):
                            rows.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                            i += 1
                        item.append(table_html(rows))
                        continue
                    im = IMG_RE.match(lines[i])
                    if im:
                        item.append(figure_html(im.group(1), im.group(2), base))
                    else:
                        item.append(f"<p>{inline(lines[i].strip())}</p>")
                    i += 1
                item.append("</li>")
                out.append("".join(item))
            out.append("</ol>")
            continue

        # 无序列表（注意事项标题下的渲染成提示框）
        if re.match(r"^[-*]\s+", line):
            items = []
            while i < n and re.match(r"^[-*]\s+", lines[i]):
                items.append("<li>" + inline(re.sub(r"^[-*]\s+", "", lines[i])) + "</li>")
                i += 1
            ul = "<ul>" + "".join(items) + "</ul>"
            out.append(f'<div class="notice">{ul}</div>' if "注意事项" in section else ul)
            continue

        # 独立成行的图片
        im = IMG_RE.match(line)
        if im:
            out.append(figure_html(im.group(1), im.group(2), base))
            i += 1
            continue

        # 引用
        if line.startswith(">"):
            buf = []
            while i < n and lines[i].startswith(">"):
                buf.append(lines[i].lstrip("> ").rstrip())
                i += 1
            out.append("<blockquote>" + inline(" ".join(buf)) + "</blockquote>")
            continue

        # 普通段落
        out.append(f"<p>{inline(line.strip())}</p>")
        i += 1

    close_faq()
    title = re.search(r"^#\s+(.*)$", md, re.M)
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{ihtml.escape(title.group(1).strip()) if title else "使用手册"}</title>
<style>{CSS}</style>
</head>
<body>
<div class="page">
{chr(10).join(out)}
</div>
<script>{TOC_JS}</script>
</body>
</html>
"""


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    src = Path(sys.argv[1])
    dst = Path(sys.argv[2]) if len(sys.argv) > 2 else src.with_suffix(".html")
    dst.write_text(render(src.read_text(encoding="utf-8"), src.parent), encoding="utf-8")
    print(f"已渲染：{dst}")


if __name__ == "__main__":
    main()
