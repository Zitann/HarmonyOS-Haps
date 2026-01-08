# /// script
# dependencies = [
#   "requests",
# ]
# ///
import os
import re
import requests
import warnings
import urllib3
from urllib3.exceptions import InsecureRequestWarning
from datetime import datetime
from dataclasses import dataclass

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
    time_dt: datetime | None = None


def get_remote_time(url):
    headers = {"User-Agent": "update-readme-script"}
    if "github.com" in url:
        token = os.environ.get("GITHUB_TOKEN")
        headers_auth = headers.copy()
        headers_auth["Authorization"] = f"Bearer {token}"
        resp = requests.get(url, headers=headers_auth, verify=False)
        if resp.status_code == 200:
            m = re.search(r'<relative-time[^>]+datetime="([^"]+)"', resp.text)
            if m:
                return datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%SZ")
        return None
    if "gitee.com" in url:
        resp = requests.get(url, headers=headers, verify=False)
        if resp.status_code == 200:
            m = re.search(
                r"<div class=['\"]release-time['\"][^>]*data-commit-date=['\"]([^'\"]+)['\"]",
                resp.text,
            )
            if m:
                return datetime.strptime(m.group(1).split(" +")[0], "%Y-%m-%d %H:%M:%S")
        return None
    if "atomgit.com" in url:
        url_clean = url.replace("/tags?tab=release", "")
        resp = requests.get(url_clean, headers=headers, verify=False)
        if resp.status_code == 200:
            m = re.search(r"type:\s*'PROJECT',\s*id:\s*'(\d+)'", resp.text)
            pid = m.group(1) if m else None
            if pid:
                api = f"https://atomgit.com/api/v3/projects/{pid}?_input_charset=utf-8"
                resp2 = requests.get(api, headers=headers, verify=False)
                if resp2.status_code == 200:
                    data = resp2.json()
                    return datetime.strptime(data["last_activity_at"], "%Y-%m-%dT%H:%M:%S%z")
            else:
                print(f"无法从AtomGit链接中获取项目ID: {url_clean}")
        return None
    print(f"不支持的链接: {url}")
    return None


def parse_old_time_str(s: str):
    s = s.strip()
    now_year = datetime.now().year
    if s in ("archived", "updating", "close-source"):
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except Exception:
        pass
    try:
        return datetime.strptime(f"{now_year}-{s}", "%Y-%m-%d")
    except Exception:
        return None


def format_display_time(dt: datetime):
    if dt is None:
        return ""
    if getattr(dt, "tzinfo", None):
        try:
            dt = dt.astimezone().replace(tzinfo=None)
        except Exception:
            dt = dt.replace(tzinfo=None)
    now_year = datetime.now().year
    if dt.year == now_year:
        return dt.strftime("%m-%d")
    return dt.strftime("%Y-%m-%d")


def update(section_title):
    updated = []
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    m = re.search(rf"### {re.escape(section_title)}\s*\n((?:\|.*\n)+)", content)
    if not m:
        return []
    table = m.group(1)
    header_lines = table.split("\n")[0:2]
    data_lines = table.strip().split("\n")[2:]
    items = []
    for line in data_lines:
        cols = line.split("|")
        if len(cols) < 5:
            continue
        item = Item(name=cols[1].strip(), url=cols[2].strip(), desc=cols[3].strip(), time=cols[4].strip())
        old_time = item.time
        if old_time == "已归档":
            print(f"项目: {item.name}，已归档，跳过")
            item.time_dt = None
        elif old_time == "更新中":
            print(f"项目: {item.name}，正在更新中，跳过")
            item.time_dt = None
        elif old_time == "闭源":
            print(f"项目: {item.name}，闭源，跳过")
            item.time_dt = None
        elif old_time == "无release":
            print(f"项目: {item.name}，无release，跳过")
            item.time_dt = None
        else:
            old_dt = parse_old_time_str(old_time)
            link = item.url.replace("[Link](", "").replace(")", "")
            latest = get_remote_time(link)
            if latest and getattr(latest, "tzinfo", None):
                try:
                    latest = latest.astimezone().replace(tzinfo=None)
                except Exception:
                    latest = latest.replace(tzinfo=None)
            print(
                f"项目: {item.name.split('(')[0].strip()}，原时间: {old_time}，最新发布时间: {format_display_time(latest) if latest else '无'}"
            )
            if latest and (old_dt is None or latest.date() != old_dt.date()):
                item.time_dt = latest
                updated.append(item.name)
            else:
                item.time_dt = old_dt
        items.append(item)
    items.sort(
        key=lambda x: (
            datetime.min
            if x.time in ("已归档", "闭源")
            else (datetime.max if x.time == "更新中" else (x.time_dt or datetime.min))
        ),
        reverse=True,
    )
    new_lines = header_lines[:]
    for it in items:
        if it.time in ("已归档", "更新中", "闭源", "无release"):
            disp = it.time
        else:
            disp = format_display_time(it.time_dt) if it.time_dt else it.time
        new_lines.append(f"| {it.name} | {it.url} | {it.desc} | {disp} |")
    new_table = "\n".join(new_lines) + "\n"
    new_content = content.replace(table, new_table)
    if new_content != content:
        with open(README_PATH, "w", encoding="utf-8") as f:
            f.write(new_content)
        return updated
    return []


def report(updated_apps):
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
    for t in update_title:
        updated_apps.extend(update(t))
    if updated_apps:
        print("README已更新")
        report(updated_apps)
        apps_str = ", ".join([app.split("(")[0][1:-1] for app in updated_apps])
        with open(".apps_str.txt", "w", encoding="utf-8") as f:
            f.write(apps_str)
    else:
        print("README无需更新")