# /// script
# dependencies = [
#   "requests",
#   "pyyaml",
# ]
# ///
"""更新 apps.yaml 中各应用的最新 release/commit 时间，并重新生成 README.md。"""
import os
import re
import sys

import requests

from common import (
    get_remote_time,
    get_latest_commit_time,
    format_display_time,
    SKIP_STATES,
)
from generate_readme import APPS_YAML, README, parse_time_str, generate

REPO_URL = "https://github.com/Zitann/HarmonyOS-Haps"


def rewrite_times(updates: list) -> bool:
    """按 (分类, 名称, 新时间) 列表改写 apps.yaml 中对应 time 行，返回是否有改动。"""
    content = APPS_YAML.read_text(encoding="utf-8")
    lines = content.splitlines()
    targets = {(cat, name): new_time for cat, name, new_time in updates}
    changed = False
    out = []
    cur_cat = None
    cur_name = None
    for line in lines:
        # 分类行：恰好 2 空格缩进，如 "  一次开发，多端部署:"
        m = re.match(r"^ {2}([^ ].*?):\s*$", line)
        if m:
            cur_cat = m.group(1).strip()
            cur_name = None
            out.append(line)
            continue
        # 列表项行：恰好 4 空格 + "- name: xxx"
        m = re.match(r"^ {4}- name: (.*)$", line)
        if m:
            cur_name = m.group(1).strip()
            out.append(line)
            continue
        # time 字段行：恰好 6 空格，如 "      time: 09-02"
        m = re.match(r"^ {6}time: (.*)$", line)
        if m and cur_cat is not None and cur_name is not None:
            key = (cur_cat, cur_name)
            if key in targets and targets[key] != m.group(1).strip():
                out.append(f"      time: {targets[key]}")
                changed = True
                continue
        out.append(line)
    if changed:
        APPS_YAML.write_text("\n".join(out) + "\n", encoding="utf-8")
    return changed


def _time_to_str(v):
    """yaml 可能把 time 值解析成 date/datetime，统一转为展示字符串。"""
    from datetime import datetime as _dt

    if isinstance(v, (_dt, type(_dt.now().date()))):
        # date/datetime 对象按展示规则还原：今年 -> MM-DD，跨年 -> YYYY-MM-DD
        if hasattr(v, "date"):
            v = v.date()
        if v.year == _dt.now().year:
            return v.strftime("%m-%d")
        return v.strftime("%Y-%m-%d")
    return str(v)


def collect_updates() -> list:
    """遍历 apps.yaml 查询各应用最新时间，返回 [(分类, 名称, 新时间字符串), ...]。"""
    import yaml

    with open(APPS_YAML, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    cats = data.get("categories") or {}

    updates = []
    for cat, apps in cats.items():
        for app in apps or []:
            name = app.get("name", "")
            old_time = _time_to_str(app.get("time", ""))
            if old_time in SKIP_STATES:
                print(f"项目: {name}，状态特殊，跳过")
                continue
            old_dt = parse_time_str(old_time) if old_time else None
            url = app.get("url", "")
            print(f"项目: {name}，当前时间: {old_time}")

            latest = get_remote_time(url)  # 最新 release 时间
            source = "release"
            if latest is None:
                # 无 release 时用默认分支最新 commit 时间兜底
                latest = get_latest_commit_time(url)
                source = "commit"
            if latest is None:
                print(f"  查询失败，保持原时间")
                continue
            new_time = format_display_time(latest)
            # 仅当日期真正变化时才记录更新
            if old_dt is None or latest.date() != old_dt.date():
                print(f"  最新{source}时间: {new_time}")
                updates.append((cat, name, new_time))
            else:
                print(f"  时间未变化: {new_time}")
    return updates


def report(updated_apps: list):
    """通过 MeoW Push API 推送更新通知，失败不阻断主流程。"""
    apps_str = ", ".join(updated_apps)
    msg = f"本次更新 {len(updated_apps)} 个应用：{apps_str}，点击查看详情"

    try:
        resp = requests.post(
            "https://api.chuckfang.com/github",
            json={
                "title": "HarmonyOS-Haps更新",
                "msg": msg,
                "url": REPO_URL,
                "imgUrl": "https://cdn.nlark.com/yuque/0/2026/svg/39012018/1786611479438-8b896944-d79f-451c-9f90-1d4709b88af8.svg",
            },
            timeout=5,
        )
        data = resp.json()
        if resp.status_code == 200 and data.get("status") == 200:
            print(f"已推送更新通知，更新应用: {apps_str}")
        else:
            print(f"通知API返回异常: {resp.status_code} {data}")
    except Exception as e:
        print(f"通知API失败: {e}")


def main():
    if not os.environ.get("GITHUB_TOKEN"):
        print("请先设置环境变量 GITHUB_TOKEN")
        sys.exit(1)

    updates = collect_updates()
    if not updates:
        print("README 无需更新")
        return

    # 改写 apps.yaml 中的 time 字段
    rewrite_times(updates)
    # 重新生成 README（内部会按时间倒序排序）
    new_content = generate()
    with open(README, "w", encoding="utf-8") as f:
        f.write(new_content)

    updated_names = [name for _, name, _ in updates]
    print("README 已更新")
    report(updated_names)
    with open(".apps_str.txt", "w", encoding="utf-8") as f:
        f.write(", ".join(updated_names))


if __name__ == "__main__":
    main()
