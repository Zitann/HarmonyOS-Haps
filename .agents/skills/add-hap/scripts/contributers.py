# /// script
# dependencies = [
#   "requests",
# ]
# ///
import os
import re
import sys

from common import CONTRIBUTERS_PATH, SVG_PATH, fetch_avatar


class Contributer:
    name: str
    url: str
    image: str


def get_contributers() -> list:
    """解析 CONTRIBUTING.md 中的作者列表，返回 (显示名, 主页链接) 列表。"""
    with open(CONTRIBUTERS_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    return re.findall(
        r"- \[([^\]]+)\]\((https?://(?:github|gitee|atomgit)\.com/[^)]+)\)", content
    )


def get_existing_svg_images() -> dict:
    """从现有 SVG 中提取已缓存的用户头像，键为主页链接。"""
    if not os.path.exists(SVG_PATH):
        return {}
    with open(SVG_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    matches = re.findall(
        r'<a href="([^"]+)"[^>]*><image[^>]*href="([^"]*)"[^>]*><title>([^<]*)</title>',
        content,
    )
    return {url: image for url, image, _ in matches if image.startswith("data:image")}


def get_contributer_info(contributers: list) -> list:
    """组装作者信息与头像；已存在于 SVG 中的用户复用缓存，只下载新增用户。"""
    cached_images = get_existing_svg_images()
    contributers_info = []
    for name, url in contributers:
        contributer = Contributer()
        contributer.name = name
        contributer.url = url
        if url in cached_images:
            print(f"作者: {name}, 主页: {url} (使用缓存)")
            contributer.image = cached_images[url]
        else:
            print(f"作者: {name}, 主页: {url} (下载头像)")
            contributer.image = fetch_avatar(url)
        contributers_info.append(contributer)
    return contributers_info


def generate_svg(contributers_info: list) -> str:
    size = 64  # 头像尺寸
    gap = 16  # 间距
    cols = 8  # 每行数量
    rows = (len(contributers_info) + cols - 1) // cols
    width = cols * (size + gap) + gap
    height = rows * (size + gap) + gap

    svg = [
        f'<svg width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">'
    ]
    for idx, contributer in enumerate(contributers_info):
        x = gap + (idx % cols) * (size + gap)
        y = gap + (idx // cols) * (size + gap)
        # SVG <a>标签用于跳转，<image>显示头像，<title>悬浮显示用户名
        svg.append(
            f'<a href="{contributer.url}" target="_blank">'
            f'<image x="{x}" y="{y}" width="{size}" height="{size}" href="{contributer.image}">'
            f"<title>{contributer.name}</title></image></a>"
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
    if len(sys.argv) == 3:
        add_contributer(sys.argv[1], sys.argv[2])
        print(f"已添加作者: {sys.argv[1]}, 主页: {sys.argv[2]}")
    contributers_info = get_contributer_info(get_contributers())
    with open(SVG_PATH, "w", encoding="utf-8") as f:
        f.write(generate_svg(contributers_info))
