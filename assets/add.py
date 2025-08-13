# /// script
# dependencies = [
#   "requests",
# ]
# ///
import os
import re
import sys
import requests
from datetime import datetime
from dataclasses import dataclass
import urllib3
from urllib3.exceptions import InsecureRequestWarning
import warnings
from update_readme import get_latest_release_time

warnings.filterwarnings(
    "ignore",
    category=DeprecationWarning,
    message=".*Parsing dates involving a day of month without a year.*",
)
urllib3.disable_warnings(InsecureRequestWarning)
README_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "README.md")


@dataclass
class Item:
    name: str
    url: str
    desc: str
    time: str


def add_project(repo_url, name, desc, platform):
    """添加项目到README"""
    print(f"正在解析项目: {repo_url}")

    print(f"项目名称: {name}")
    print(f"项目描述: {desc}")
    releases_url = f"{repo_url}/releases"

    # 获取最新发布时间
    latest_time = get_latest_release_time(releases_url)

    print(f"最新发布时间: {latest_time}")

    # 读取README
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # 找到表格
    table_match = re.search(rf"### {platform}\s*\n((?:\|.*\n)+)", content)
    if not table_match:
        print("未找到项目列表表格")
        return False

    table = table_match.group(1)
    lines = table.strip().split("\n")

    # 构建新项目条目
    new_item = (
        f"| [{name}]({repo_url}) | [Link]({releases_url}) | {desc} | {latest_time} |"
    )

    # 检查是否已存在
    for line in lines:
        if name in line and repo_url in line:
            print(f"项目 {name} 已存在于列表中")
            return False

    lines.insert(2, new_item)

    # 重新组装表格
    new_table = "\n".join(lines) + "\n"
    new_content = content.replace(table, new_table)

    # 写入文件
    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"项目 {name} 已成功添加到列表中")
    return True


def main():
    if len(sys.argv) != 5:
        print("用法: python add.py <项目仓库URL> <项目名称> <项目描述>")
        sys.exit(1)
    repo_url = sys.argv[1].strip()
    name = sys.argv[2].strip()
    desc = sys.argv[3].strip()
    platform = sys.argv[4].strip()

    # 验证URL格式
    if not (
        repo_url.startswith("https://github.com/")
        or repo_url.startswith("https://gitee.com/")
    ):
        print("请提供有效的GitHub或Gitee仓库URL")
        sys.exit(1)

    if add_project(repo_url, name, desc, platform):
        print("添加成功！")
    else:
        print("添加失败！")


if __name__ == "__main__":
    main()
