import os
import re
import requests
from datetime import datetime

README_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "README.md")


def get_latest_release_time(url):
    headers = {"User-Agent": "update-readme-script"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    resp = requests.get(url, headers=headers)
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


def update_readme_release_times():
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    # 匹配格式: | [COPI](...) | [Link](.../releases) | ... | 时间 |
    pattern = re.compile(
        r"(\|\s*\[[^\]]+\]\([^\)]+\)\s*\|\s*\[Link\]\((https://.*?\.com/[^/\s]+/[^/\s\)]+/releases[^\)]*)\)\s*\|\s*[^\|]+\|\s*)([^\|]+)(\s*\|)"
    )

    def repl(match):
        prefix, url, old_time, suffix = match.groups()
        if not url.rstrip("/").endswith("/releases"):
            return match.group(0)
        if old_time.strip().lower() == "archived":
            return match.group(0)
        latest_time = get_latest_release_time(url)
        latest_time_fmt = (
            format_time_mmdd(latest_time) if latest_time else old_time.strip()
        )
        print(
            f"release地址: {url}，原时间: {old_time}，最新发布时间: {latest_time_fmt}"
        )
        return f"{prefix}{latest_time_fmt}{suffix}"

    new_content = pattern.sub(repl, content)

    if new_content != content:
        with open(README_PATH, "w", encoding="utf-8") as f:
            f.write(new_content)
        print("README.md 已更新。")
        # 新增：有更新时请求API
        try:
            api_url = "https://api.chuckfang.com/haps/GitHub%E4%BB%93%E5%BA%93/%E6%9C%89%E8%BD%AF%E4%BB%B6%E6%9B%B4%E6%96%B0?url=https://github.com/Zitann/HarmonyOS-Haps"
            requests.get(api_url, timeout=5)
            print("已通知API: 有软件更新")
        except Exception as e:
            print(f"通知API失败: {e}")
    else:
        print("README.md 无需更新。")


if __name__ == "__main__":
    update_readme_release_times()
