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


def get_github_time(url):
    token = os.environ.get("GITHUB_TOKEN")
    headers = {"User-Agent": "update-readme-script", "Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers, verify=False)
    if resp.status_code == 200:
        html = resp.text
        # Github: <relative-time ... datetime="...">
        m = re.search(r'<relative-time[^>]+datetime="([^"]+)"', html)
        if m:
            dt = datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%SZ")
            return dt.strftime("%m-%d")
    return None


def get_gitee_time(url):
    headers = {"User-Agent": "update-readme-script"}
    resp = requests.get(url, headers=headers, verify=False)
    if resp.status_code == 200:
        html = resp.text
        # Gitee: <div class='release-time' data-commit-date='2025-04-03 08:47:52 +0800'>
        m = re.search(
            r"<div class=['\"]release-time['\"][^>]*data-commit-date=['\"]([^'\"]+)['\"]",
            html,
        )
        if m:
            dt = datetime.strptime(m.group(1).split(" +")[0], "%Y-%m-%d %H:%M:%S")
            return dt.strftime("%m-%d")
    return None


def get_atomgit_time(url):
    headers = {"User-Agent": "update-readme-script"}
    url = url.replace("/tags?tab=release", "")
    resp = requests.get(url, headers=headers, verify=False)
    if resp.status_code == 200:
        html = resp.text
        m = re.search(r"type:\s*'PROJECT',\s*id:\s*'(\d+)'", html)
        id = m.group(1) if m else None
        if id:
            url = f"https://atomgit.com/api/v3/projects/{id}?_input_charset=utf-8"
            resp = requests.get(url, headers=headers, verify=False)
            if resp.status_code == 200:
                data = resp.json()
                # 2025-08-03T23:05:59+08:00
                dt = datetime.strptime(data["last_activity_at"], "%Y-%m-%dT%H:%M:%S%z")
                return dt.strftime("%m-%d")
        else:
            print(f"无法从AtomGit链接中获取项目ID: {url}")
            return None
    return None


def get_latest_release_time(url):
    if "github.com" in url:
        return get_github_time(url)
    elif "gitee.com" in url:
        return get_gitee_time(url)
    elif "atomgit.com" in url:
        return get_atomgit_time(url)
    else:
        print(f"不支持的链接: {url}")
    return None


def update(title):
    updated_apps = []
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    table_match = re.search(rf"### {re.escape(title)}\s*\n((?:\|.*\n)+)", content)
    table = table_match.group(1)
    title = table.split("\n")[0:2]
    lines = table.strip().split("\n")[2:]
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
            old_time = item.time
            if item.time == "archived":
                print(f"项目: {item.name}，已归档")
            else:
                latest_time = get_latest_release_time(
                    item.url.replace("[Link](", "").replace(")", "")
                )
                print(
                    f"项目: {item.name.split('(')[0].strip()}，原时间: {item.time}，最新发布时间: {latest_time}"
                )
                if latest_time and latest_time != old_time:
                    item.time = latest_time
                    updated_apps.append(item.name)
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
        return updated_apps
    else:
        return []


def report(updated_apps):
    """报告更新状态"""
    # 每一个都执行split('(')[0][1:-1] 并连接成字符串
    apps_str = ", ".join([app.split("(")[0][1:-1] for app in updated_apps])
    try:
        api_url = f"https://api.chuckfang.com/github/GitHub更新{apps_str}?url=https://github.com/Zitann/HarmonyOS-Haps"
        requests.get(api_url, timeout=5)
        print(f"已通知API: 有软件更新，更新应用: {apps_str}")
    except Exception as e:
        print(f"通知API失败: {e}")


if __name__ == "__main__":
    update_title = ["一次开发，多端部署", "鸿蒙手机/平板", "鸿蒙电脑"]
    updated_apps = []
    for title in update_title:
        updated_apps.extend(update(title))
    if updated_apps:
        print("README已更新")
        report(updated_apps)
        apps_str = ", ".join([app.split("(")[0][1:-1] for app in updated_apps])
        with open(".apps_str.txt", "w", encoding="utf-8") as f:
            f.write(apps_str)
    else:
        print("README无需更新")
