"""给截图模糊脱敏、不可逆遮挡、标红框和裁剪，位置按百分比给。

browser.py 的 --mask / --highlight 靠 CSS selector，控制台类 SPA（阿里云、
腾讯云等）的 class 是随机哈希，选择器匹配不上，这时改用本脚本按比例坐标画。

**必须先量再画**：凭肉眼估比例基本每次都偏。没跑过 --grid 就画框会直接报错。

    # 1. 量：带上最终要用的 --crop，出一张带百分比网格的图，从上面读坐标
    python3 scripts/annotate.py shot.png --crop 10,75 --grid

    # 2. 画：普通敏感文字用 --blur；密钥、令牌等秘密才用 --fill
    python3 scripts/annotate.py shot.png --crop 10,75 \
      --box 14,36,73,44 --blur 10,20,45,28 --fill 85,0,100,7

`--blur` 坐标应贴合敏感字符本身，只留极小余量；不要框整个输入框或整格单元格。
单行值只框字形高度，多行值按实际渲染行重复写多个窄 `--blur`；相邻字段、相邻记录
也分别框选。选区与字段名、列名、提示文案之间必须保留清晰空隙，空值不打码。
原尺寸复看若只在下沿或末尾漏出笔画，只向下或向末尾补选区，不要向字段名方向扩大。
`--blur-radius` 只调模糊强度，不能弥补选区过大或错位。

所有百分比都相对**裁剪后的成图**，量到什么就填什么，不用换算。
原图自动备份成 <图名>.orig.png，标错了重跑即可。交付前清掉 .orig.png 和 .grid.png。
"""
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

RED = "#E1251B"
MASK = "#DDDDDD"


def _stem(path):
    return path.rsplit(".", 1)[0]


def _load(path, crop):
    """取原图（首次调用时备份），按 crop 裁到最终尺寸。"""
    orig = path + ".orig.png"
    if not os.path.exists(orig):
        Image.open(path).save(orig)
    im = Image.open(orig).convert("RGB")
    if crop:
        w, h = im.size
        im = im.crop((0, int(crop[0] / 100 * h), w, int(crop[1] / 100 * h)))
    return im


def _rect(box, w, h):
    x0, y0, x1, y1 = box
    return [x0 / 100 * w, y0 / 100 * h, x1 / 100 * w, y1 / 100 * h]


def grid(path, crop):
    """出一张带百分比网格的图用来量，并记下这次量的是哪种裁剪。"""
    im = _load(path, crop)
    im = im.resize((900, int(im.height * 900 / im.width)))
    d = ImageDraw.Draw(im)
    w, h = im.size
    for i in range(1, 20):
        x, y = w * i / 20, h * i / 20
        d.line([(x, 0), (x, h)], fill="#00A0FF")
        d.text((x + 2, 4), str(i * 5), fill="#0080D0")
        d.line([(0, y), (w, y)], fill="#FF9000")
        d.text((3, y + 2), str(i * 5), fill="#D06000")
    out = _stem(path) + ".grid.png"
    im.save(out)
    with open(_stem(path) + ".grid.json", "w") as f:
        json.dump({"crop": crop}, f)
    return out


def annotate(path, boxes, fills, blurs, crop, blur_radius=None):
    im = _load(path, crop)
    w, h = im.size
    radius = blur_radius if blur_radius is not None else max(10, round(w / 90))
    for b in blurs:
        rect = tuple(int(v) for v in _rect(b, w, h))
        region = im.crop(rect).filter(ImageFilter.GaussianBlur(radius=radius))
        im.paste(region, rect)
    d = ImageDraw.Draw(im)
    for f in fills:
        d.rectangle(_rect(f, w, h), fill=MASK)
    for b in boxes:
        d.rectangle(_rect(b, w, h), outline=RED, width=max(2, w // 500))
    im.save(path)
    return im.size


def check_measured(path, crop):
    """没量过就不许画：坐标靠估必偏，这条是硬约束。"""
    meta = _stem(path) + ".grid.json"
    if not os.path.exists(meta):
        sys.exit(
            f"× 还没量过 {os.path.basename(path)}，不能直接画框。\n"
            f"  先跑：annotate.py {path}"
            + (f" --crop {crop[0]:g},{crop[1]:g}" if crop else "")
            + " --grid\n  从网格图上读出坐标，再回来画。"
        )
    with open(meta) as f:
        measured = json.load(f).get("crop")
    if (measured or None) != (list(crop) if crop else None):
        sys.exit(
            f"× --crop 和量的时候不一致（量的是 {measured}，现在是 "
            f"{list(crop) if crop else None}）。\n"
            f"  裁剪一变，百分比就全错位了。用同样的 --crop 重新 --grid。"
        )


def _nums(v):
    return tuple(float(x) for x in v.split(","))


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    path, boxes, fills, blurs, crop, blur_radius, want_grid = (
        args[0], [], [], [], None, None, False
    )
    i = 1
    while i < len(args):
        if args[i] == "--grid":
            want_grid = True; i += 1
        elif args[i] == "--box":
            boxes.append(_nums(args[i + 1])); i += 2
        elif args[i] == "--fill":
            fills.append(_nums(args[i + 1])); i += 2
        elif args[i] == "--blur":
            blurs.append(_nums(args[i + 1])); i += 2
        elif args[i] == "--blur-radius":
            blur_radius = float(args[i + 1]); i += 2
        elif args[i] == "--crop":
            crop = _nums(args[i + 1]); i += 2
        else:
            i += 1

    if want_grid:
        print(grid(path, crop))
    else:
        if boxes or fills or blurs:
            check_measured(path, crop)
        print(path, annotate(path, boxes, fills, blurs, crop, blur_radius))
