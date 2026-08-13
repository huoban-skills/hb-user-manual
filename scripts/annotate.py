"""给截图打码、标红框、裁剪，位置按百分比给。

browser.py 的 --mask / --highlight 靠 CSS selector，控制台类 SPA（阿里云、
腾讯云等）的 class 是随机哈希，选择器匹配不上，这时改用本脚本按比例坐标画。

位置一律用百分比（相对成图宽高），换分辨率不用改。**先叠网格量准再画**，
凭肉眼估比例基本每次都偏。

    # 1. 先看坐标：叠一层百分比网格，读出目标位置
    python3 scripts/annotate.py shot.png --grid

    # 2. 再标：裁掉页面上下无关部分，框住要点的地方，遮掉敏感值
    python3 scripts/annotate.py shot.png --crop 10,80 --box 2,30,55,38 --fill 22,32,53,36

顺序固定是「打码 → 裁剪 → 画框」，框的百分比按**裁剪后**的成图算。
原图自动备份成 <图名>.orig.png，标错了可以重来。
"""
import os
import sys

from PIL import Image, ImageDraw

RED = "#E1251B"
MASK = "#DDDDDD"


def _pct(box, w, h):
    x0, y0, x1, y1 = box
    return [x0 / 100 * w, y0 / 100 * h, x1 / 100 * w, y1 / 100 * h]


def annotate(path, boxes=(), fills=(), crop=None):
    orig = path + ".orig.png"
    if not os.path.exists(orig):
        Image.open(path).save(orig)
    im = Image.open(orig).convert("RGB")
    w, h = im.size

    d = ImageDraw.Draw(im)
    for f in fills:
        d.rectangle(_pct(f, w, h), fill=MASK)

    if crop:
        im = im.crop((0, int(crop[0] / 100 * h), w, int(crop[1] / 100 * h)))

    w, h = im.size
    d = ImageDraw.Draw(im)
    for b in boxes:
        d.rectangle(_pct(b, w, h), outline=RED, width=max(2, w // 500))
    im.save(path)
    return im.size


def grid(path, out=None):
    """叠一层百分比网格，用来量目标位置。不覆盖原图。"""
    im = Image.open(path).convert("RGB")
    im = im.resize((900, int(im.height * 900 / im.width)))
    d = ImageDraw.Draw(im)
    w, h = im.size
    for i in range(1, 20):
        x = w * i / 20
        d.line([(x, 0), (x, h)], fill="#00A0FF")
        d.text((x + 2, 4), str(i * 5), fill="#0080D0")
        y = h * i / 20
        d.line([(0, y), (w, y)], fill="#FF9000")
        d.text((3, y + 2), str(i * 5), fill="#D06000")
    out = out or path.rsplit(".", 1)[0] + ".grid.png"
    im.save(out)
    return out


def _nums(v):
    return tuple(float(x) for x in v.split(","))


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    path, boxes, fills, crop = args[0], [], [], None
    i = 1
    while i < len(args):
        if args[i] == "--grid":
            print(grid(path))
            sys.exit()
        if args[i] == "--box":
            boxes.append(_nums(args[i + 1])); i += 2
        elif args[i] == "--fill":
            fills.append(_nums(args[i + 1])); i += 2
        elif args[i] == "--crop":
            crop = _nums(args[i + 1]); i += 2
        else:
            i += 1
    print(path, annotate(path, boxes, fills, crop))
