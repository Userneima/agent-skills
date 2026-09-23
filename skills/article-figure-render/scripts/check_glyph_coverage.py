#!/usr/bin/env python3
"""出图前的缺字自检：把要画的每个字用最终字体真渲染一遍，空白的就是缺字。

为什么需要它：字体缺字是**静默失败**。PIL 不会警告，不会报错，那个字就是不见了，
出来的图看着完全正常——直到有人念图上的句子才发现少了一个字。

真实事故（2026-08-18）：一批说明图里「稳」「杀」三处渲染成空白。原因是
macOS 的 PingFang.ttc 是字体集合，脚本按 index=0 载入，而 index=0 是
PingFang HK（繁体），HK / MO / TC 三个 face 都没有简体独有字形。简体要用 index=3。

用法：
    # 先看清这个字体文件里有哪几个 face，别猜 index
    check_glyph_coverage.py --font /path/PingFang.ttc --list-faces

    # 检查一个出图脚本里所有字符串字面量里的字
    check_glyph_coverage.py --font /path/PingFang.ttc --index 3 render.py

    # 或直接检查一段文字
    check_glyph_coverage.py --font /path/font.ttf --text "稳定 · 杀伤不均匀"

缺字则退出码 1，并列出缺哪个字、出现在哪几行。出图脚本应在渲染前调用它并在非零时中止。
"""
import argparse
import re
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("需要 Pillow：pip install Pillow")

LITERAL = re.compile(r"'([^'\n]*)'|\"([^\"\n]*)\"")
# 只查非 ASCII 可见字符；空格类不参与（本来就没有字形）
SKIP = set(" \t　​")


def list_faces(path):
    for idx in range(64):
        try:
            f = ImageFont.truetype(path, 32, index=idx)
        except Exception:
            break
        family, style = f.getname()
        print(f"index={idx:<3} {family} {style}")


def blank(path, index, ch, size=48):
    f = ImageFont.truetype(path, size, index=index)
    im = Image.new("L", (size * 2, size * 2), 0)
    ImageDraw.Draw(im).text((4, 4), ch, font=f, fill=255)
    return im.getbbox() is None


def collect(args):
    """返回 {char: [(file, lineno), ...]}"""
    hits = {}
    def add(ch, where):
        if ch.isascii() or ch in SKIP:
            return
        hits.setdefault(ch, [])
        if where not in hits[ch]:
            hits[ch].append(where)

    if args.text:
        for ch in args.text:
            add(ch, ("--text", 0))
    for path in args.files:
        with open(path, encoding="utf-8", errors="replace") as fh:
            for lineno, line in enumerate(fh, 1):
                # 出图脚本里真正会画出来的是字符串字面量；--all-text 则整行都算
                spans = [line] if args.all_text else [
                    m.group(1) or m.group(2) or "" for m in LITERAL.finditer(line)
                ]
                for s in spans:
                    for ch in s:
                        add(ch, (path, lineno))
    return hits


def main():
    p = argparse.ArgumentParser(description="出图前缺字自检")
    p.add_argument("files", nargs="*", help="要扫的文件（出图脚本，或纯文本稿）")
    p.add_argument("--font", required=True, help="最终出图用的字体文件路径")
    p.add_argument("--index", type=int, default=0, help="ttc 集合里的 face 序号（默认 0）")
    p.add_argument("--text", help="直接检查这段文字")
    p.add_argument("--all-text", action="store_true",
                   help="整行都算（默认只取字符串字面量，适合扫出图脚本）")
    p.add_argument("--list-faces", action="store_true", help="列出字体文件里的所有 face 后退出")
    a = p.parse_args()

    if a.list_faces:
        list_faces(a.font)
        return 0
    if not a.files and not a.text:
        p.error("给至少一个文件，或用 --text")

    try:
        font_name = " ".join(ImageFont.truetype(a.font, 32, index=a.index).getname())
    except Exception as e:
        sys.exit(f"字体载不上：{e}")

    hits = collect(a)
    missing = {ch: where for ch, where in sorted(hits.items()) if blank(a.font, a.index, ch)}

    print(f"字体：{font_name}（index={a.index}）")
    print(f"待检字符：{len(hits)} 个")
    if not missing:
        print("缺字：无 ✓")
        return 0
    print(f"缺字：{len(missing)} 个 ✗  →  {''.join(missing)}")
    for ch, where in missing.items():
        for path, lineno in where[:5]:
            print(f"  「{ch}」 {path}:{lineno}")
    print("\n这些字在当前 face 里没有字形，会被静默画成空白。换一个覆盖简体的 face"
          "（PingFang.ttc 的简体是 index=3 / 7 / 11），或换字体，不要出图。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
