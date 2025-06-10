# /// script
# dependencies = [
#   "requests",
# ]
# ///
import os
import re
import requests
from datetime import datetime
from dataclasses import dataclass
import urllib3
from urllib3.exceptions import InsecureRequestWarning
import warnings
from datetime import datetime

warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*Parsing dates involving a day of month without a year.*")
urllib3.disable_warnings(InsecureRequestWarning)
README_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "README.md")


@dataclass
class Item:
    name: str
    url: str
    desc: str
    time: str


def get_latest_release_time(url):
    headers = {"User-Agent": "update-readme-script"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.get(url, headers=headers, verify=False)
    if resp.status_code == 200:
        html = resp.text
        # Github: <relative-time ... datetime="...">
        m = re.search(r'<relative-time[^>]+datetime="([^"]+)"', html)
        if m:
            return m.group(1)
        # Gitee: <div class='release-time' data-commit-date='2025-04-03 08:47:52 +0800'>
        m2 = re.search(
            r"<div class=['\"]release-time['\"][^>]*data-commit-date=['\"]([^'\"]+)['\"]",
            html,
        )
        if m2:
            return m2.group(1)
    return None


def format_time_mmdd(iso_time):
    if not iso_time:
        return ""
    try:
        # Github: 2024-06-01T12:34:56Z
        if "T" in iso_time and iso_time.endswith("Z"):
            dt = datetime.strptime(iso_time, "%Y-%m-%dT%H:%M:%SZ")
        # Gitee: 2025-04-03 08:47:52 +0800
        elif "+" in iso_time and "-" in iso_time and ":" in iso_time:
            dt = datetime.strptime(iso_time.split(" +")[0], "%Y-%m-%d %H:%M:%S")
        else:
            dt = datetime.fromisoformat(iso_time)
        return dt.strftime("%m-%d")
    except Exception:
        return ""


def update():
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    table_match = re.search(r"### 鸿蒙项目列表\s*\n((?:\|.*\n)+)", content)
    table = table_match.group(1)
    title = table.split("\n")[0:4]
    lines = table.strip().split("\n")[4:]
    items = []
    for line in lines:
        cols = line.split("|")
        if len(cols) >= 5:
            item = Item(
                name=cols[1].strip(),
                url=cols[2].strip(),
                desc=cols[3].strip(),
                time=cols[4].strip(),
            )
            if item.time == "archived":
                print(f"项目: {item.name}，已归档")
            else:
                latest_time = get_latest_release_time(
                    item.url.replace("[Link](", "").replace(")", "")
                )
                latest_time_fmt = (
                    format_time_mmdd(latest_time) if latest_time else item.time
                )
                print(
                    f"项目: {item.name}，原时间: {item.time}，最新发布时间: {latest_time_fmt}"
                )
                item.time = latest_time_fmt
            items.append(item)
    items.sort(
        key=lambda x: (
            datetime.strptime(x.time, "%m-%d") if x.time != "archived" else datetime.min
        ),
        reverse=True,
    )
    new_table = title
    for item in items:
        new_table.append(f"| {item.name} | {item.url} | {item.desc} | {item.time} |")
    new_table = "\n".join(new_table) + "\n"
    new_content = content.replace(table, new_table)
    if new_content != content:
        with open(README_PATH, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("README.md 已更新。")
        try:
            api_url = "https://api.chuckfang.com/haps/GitHub%E4%BB%93%E5%BA%93/%E6%9C%89%E8%BD%AF%E4%BB%B6%E6%9B%B4%E6%96%B0?url=https://github.com/Zitann/HarmonyOS-Haps"
            requests.get(api_url, timeout=5)
            print("已通知API: 有软件更新")
        except Exception as e:
            print(f"通知API失败: {e}")
    else:
        print("README.md 无需更新。")


if __name__ == "__main__":
    update()
