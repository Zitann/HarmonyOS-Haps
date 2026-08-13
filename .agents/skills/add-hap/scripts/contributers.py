# /// script
# dependencies = [
#   "requests",
# ]
# ///
import os
import re
import requests
import base64
import sys
from time import sleep

ROOT_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
CONTRIBUTERS_PATH = os.path.join(ROOT_DIR, "CONTRIBUTING.md")
SVG_PATH = os.path.join(ROOT_DIR, "assets", "contributers.svg")


class Contributer:
    name: str
    url: str
    image: str


def get_github_avatar_base64(url: str) -> str:
    token = os.environ.get("GITHUB_TOKEN")
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {token}",
    }
    info_url = url.replace("https://github.com/", "https://api.github.com/users/")
    response = requests.get(info_url, headers=headers, timeout=15)
    if response.status_code == 200:
        avatar_url = response.json().get("avatar_url", "")
        if avatar_url:
            img_response = requests.get(avatar_url, timeout=15)
            if img_response.status_code == 200:
                return "data:image/png;base64," + base64.b64encode(
                    img_response.content
                ).decode("utf-8")
        return ""
    return ""


def get_gitee_avatar_base64(url: str) -> str:
    headers = {"User-Agent": "update-readme-script"}
    info_url = url.replace("https://gitee.com/", "https://gitee.com/api/v5/users/")
    response = requests.get(info_url, headers=headers, timeout=15)
    if response.status_code == 200:
        avatar_url = response.json().get("avatar_url", "")
        if avatar_url:
            img_response = requests.get(avatar_url, timeout=15)
            if img_response.status_code == 200:
                return "data:image/png;base64," + base64.b64encode(
                    img_response.content
                ).decode("utf-8")
        return ""
    return ""


def get_atomgit_avatar_base64(url: str) -> str:
    headers = {"User-Agent": "update-readme-script"}
    info_url = url.replace(
        "https://atomgit.com/", "https://atomgit.com/api/user/v1/un/detail?path="
    )
    response = requests.get(info_url, headers=headers, timeout=15)
    if response.status_code == 200:
        avatar_url = "https://file.atomgit.com/" + response.json().get("photo", "")
        if avatar_url:
            img_response = requests.get(avatar_url, timeout=15)
            if img_response.status_code == 200:
                return "data:image/png;base64," + base64.b64encode(
                    img_response.content
                ).decode("utf-8")
        return ""
    return ""


def get_contributers():
    with open(CONTRIBUTERS_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # 匹配所有作者链接
    matches = re.findall(
        r"- \[([^\]]+)\]\((https?://(?:github|gitee|atomgit)\.com/[^)]+)\)", content
    )
    return matches


def get_existing_svg_images() -> dict:
    """从现有 SVG 中提取已缓存的用户头像，键为主页链接"""
    if not os.path.exists(SVG_PATH):
        return {}
    with open(SVG_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    matches = re.findall(
        r'<a href="([^"]+)"[^>]*><image[^>]*href="([^"]*)"[^>]*><title>([^<]*)</title>',
        content,
    )
    return {
        url: image for url, image, _ in matches if image.startswith("data:image")
    }


def get_contributer_info(contributers):
    cached_images = get_existing_svg_images()
    contributers_info = []
    for name, url in contributers:
        contributer = Contributer()
        contributer.name = name
        contributer.url = url
        # 已存在于 SVG 中的用户直接复用缓存头像，只下载新增用户
        if url in cached_images:
            print(f"作者: {name}, 主页: {url} (使用缓存)")
            contributer.image = cached_images[url]
            contributers_info.append(contributer)
            continue
        print(f"作者: {name}, 主页: {url} (下载头像)")
        while True:
            try:
                if "github.com" in url:
                    contributer.image = get_github_avatar_base64(url)
                elif "gitee.com" in url:
                    contributer.image = get_gitee_avatar_base64(url)
                elif "atomgit.com" in url:
                    contributer.image = get_atomgit_avatar_base64(url)
                break
            except requests.RequestException:
                sleep(5)
        contributers_info.append(contributer)
    return contributers_info


def generate_svg(contributers_info):
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
    contributers = get_contributers()
    contributers.append((name, url))
    contributers.sort(key=lambda x: x[0])
    with open(CONTRIBUTERS_PATH, "w", encoding="utf-8") as f:
        for contributer in contributers:
            f.write(f"- [{contributer[0]}]({contributer[1]})\n")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        name = sys.argv[1]
        url = sys.argv[2]
        add_contributer(name, url)
        print(f"已添加作者: {name}, 主页: {url}")
    contributers = get_contributers()
    contributers_info = get_contributer_info(contributers)
    svg_code = generate_svg(contributers_info)
    with open(
        SVG_PATH,
        "w",
        encoding="utf-8",
    ) as f:
        f.write(svg_code)
