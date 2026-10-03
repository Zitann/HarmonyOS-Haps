# /// script
# dependencies = [
#   "requests",
# ]
# ///
import math
import os
import re
import sys
from xml.sax.saxutils import escape

from common import (
    AVATAR_SIZE,
    CONTRIBUTERS_PATH,
    SVG_PATH,
    cache_key,
    fetch_avatar,
)


class Contributer:
    name: str
    url: str
    image: str


# 头像墙布局：单元格 = 圆形头像 + 下方名字，整体保持接近一屏可读的宽度
AVATAR = 56  # 头像边长
CELL_W = 82  # 单元格宽度（含左右留白）
CELL_H = 82  # 单元格高度（头像 + 名字）
COLS = 9  # 每行数量
MARGIN = 16  # 画布四周留白
NAME_SIZE = 12  # 名字字号
NAME_MAX_W = CELL_W - 8  # 名字可用宽度，超出则省略


def get_contributers() -> list:
    """解析 CONTRIBUTING.md 中的作者列表，返回 (显示名, 主页链接) 列表。"""
    with open(CONTRIBUTERS_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    return re.findall(
        r"- \[([^\]]+)\]\((https?://(?:github|gitee|atomgit)\.com/[^)]+)\)", content
    )


def get_existing_svg_images() -> dict:
    """从现有 SVG 中提取已缓存的用户头像，键为 cache_key。"""
    if not os.path.exists(SVG_PATH):
        return {}
    with open(SVG_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    cached = {}
    for url, body in re.findall(r'<a href="([^"]+)"[^>]*>(.*?)</a>', content, re.DOTALL):
        for tag in re.findall(r"<image[^>]*/>", body):
            size_m = re.search(r'data-size="(\d+)"', tag)
            href_m = re.search(r'href="(data:image[^"]*)"', tag)
            if size_m and href_m and int(size_m.group(1)) == AVATAR_SIZE:
                cached[cache_key(url, AVATAR_SIZE)] = href_m.group(1)
    return cached


def get_contributer_info(contributers: list, no_cache: bool = False) -> list:
    """组装作者信息与头像；已存在于 SVG 中的用户复用缓存，只下载新增用户。"""
    cached_images = {} if no_cache else get_existing_svg_images()
    contributers_info = []
    for name, url in contributers:
        contributer = Contributer()
        contributer.name = name
        contributer.url = url
        key = cache_key(url, AVATAR_SIZE)
        if key in cached_images:
            print(f"作者: {name}, 主页: {url} (使用缓存)")
            contributer.image = cached_images[key]
        else:
            print(f"作者: {name}, 主页: {url} (下载头像 {AVATAR_SIZE}px)")
            contributer.image = fetch_avatar(url, AVATAR_SIZE)
        contributers_info.append(contributer)
    return contributers_info


def char_width(ch: str, font_size: int) -> float:
    """粗略估算字符渲染宽度：CJK 及全角符号按一个字宽，其余按 0.55 倍。"""
    return font_size if ord(ch) > 0x2E80 else font_size * 0.55


def ellipsize(text: str, font_size: int, max_width: float) -> str:
    """超出宽度时截断并加省略号，完整名字仍保留在 <title> 中。"""
    if sum(char_width(c, font_size) for c in text) <= max_width:
        return text
    budget = max_width - font_size * 0.6
    out = ""
    used = 0.0
    for ch in text:
        w = char_width(ch, font_size)
        if used + w > budget:
            break
        out += ch
        used += w
    return out + "…"


def generate_svg(contributers_info: list) -> str:
    """生成圆形头像墙：每人一个圆形头像 + 名字，链接指向其主页。"""
    rows = math.ceil(len(contributers_info) / COLS) if contributers_info else 0
    width = COLS * CELL_W + MARGIN * 2
    height = rows * CELL_H + MARGIN * 2
    r = AVATAR / 2

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="项目贡献者">',
        "<defs>",
    ]

    for idx in range(len(contributers_info)):
        col = idx % COLS
        row = idx // COLS
        cx = MARGIN + col * CELL_W + CELL_W / 2
        cy = MARGIN + row * CELL_H + 6 + r
        svg.append(
            f'<clipPath id="c{idx}"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath>'
        )
    svg.append("</defs>")

    for idx, contributer in enumerate(contributers_info):
        col = idx % COLS
        row = idx // COLS
        cx = MARGIN + col * CELL_W + CELL_W / 2
        cy = MARGIN + row * CELL_H + 6 + r
        label = escape(ellipsize(contributer.name, NAME_SIZE, NAME_MAX_W))
        image_attrs = (
            f' clip-path="url(#c{idx})" data-size="{AVATAR_SIZE}"' if contributer.image else ""
        )
        svg.append(
            f'<a href="{escape(contributer.url)}" target="_blank">'
            # 底色圆兼作头像下载失败时的占位，正常情况下被图片完全遮住
            f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#f6f8fa"/>'
            f'<image x="{cx - r}" y="{cy - r}" width="{AVATAR}" height="{AVATAR}"'
            f' href="{contributer.image}"{image_attrs}/>'
            f'<text x="{cx}" y="{cy + r + 15}" text-anchor="middle"'
            f' font-size="{NAME_SIZE}" fill="#57606a"'
            ' font-family="-apple-system,BlinkMacSystemFont,\'Segoe UI\',Helvetica,Arial,sans-serif">'
            f"{label}</text>"
            f"<title>{escape(contributer.name)}</title>"
            f"</a>"
        )

    svg.append("</svg>")
    return "\n".join(svg)


def add_contributer(name: str, url: str):
    """向 CONTRIBUTING.md 添加作者并按显示名排序。"""
    contributers = get_contributers()
    contributers.append((name, url))
    contributers.sort(key=lambda x: x[0])
    with open(CONTRIBUTERS_PATH, "w", encoding="utf-8") as f:
        for contributer in contributers:
            f.write(f"- [{contributer[0]}]({contributer[1]})\n")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] != "--no-cache":
        add_contributer(sys.argv[1], sys.argv[2])
        print(f"已添加作者: {sys.argv[1]}, 主页: {sys.argv[2]}")
    no_cache = "--no-cache" in sys.argv
    if no_cache:
        print("已启用 --no-cache，强制重新下载所有头像")
    contributers_info = get_contributer_info(get_contributers(), no_cache=no_cache)
    with open(SVG_PATH, "w", encoding="utf-8") as f:
        f.write(generate_svg(contributers_info))
