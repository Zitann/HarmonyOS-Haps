# /// script
# dependencies = [
#   "requests",
# ]
# ///
from datetime import datetime
from dataclasses import dataclass

import requests

from common import (
    read_table,
    write_table,
    split_row,
    get_remote_time,
    format_display_time,
    parse_old_time_str,
    SKIP_STATES,
    README_PATH,
)


@dataclass
class Item:
    name: str
    url: str
    desc: str
    time: str
    time_dt: datetime = None


def sort_key(item: Item):
    """“更新中”置顶，“已归档/闭源/无release”沉底，其余按日期倒序。"""
    if item.time == "更新中":
        return datetime.max
    if item.time_dt:
        return item.time_dt
    return datetime.min


def update(section_title: str) -> list:
    """刷新某个分类表格中各行的最新 release 时间并重排，返回有更新的行名列表。"""
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    result = read_table(content, section_title)
    if not result:
        return []
    header_lines, data_lines, old_table = result

    items = []
    updated = []
    for line in data_lines:
        cols = split_row(line)
        if cols is None:
            continue
        item = Item(name=cols[0], url=cols[1], desc=cols[2], time=cols[3])

        if item.time in SKIP_STATES:
            print(f"项目: {item.name}，{item.time}，跳过")
        else:
            old_dt = parse_old_time_str(item.time)
            link = item.url.removeprefix("[Link](").removesuffix(")")
            latest = get_remote_time(link)
            print(
                f"项目: {item.name.split('(')[0].strip()}，原时间: {item.time}，"
                f"最新发布时间: {format_display_time(latest) if latest else '无'}"
            )
            if latest and (old_dt is None or latest.date() != old_dt.date()):
                item.time_dt = latest
                updated.append(item.name)
            else:
                item.time_dt = old_dt
        items.append(item)

    items.sort(key=sort_key, reverse=True)

    new_lines = []
    for it in items:
        if it.time in SKIP_STATES:
            disp = it.time
        else:
            disp = format_display_time(it.time_dt) if it.time_dt else it.time
        new_lines.append(f"| {it.name} | {it.url} | {it.desc} | {disp} |")

    new_content = write_table(content, old_table, header_lines, new_lines)
    if new_content != content:
        with open(README_PATH, "w", encoding="utf-8") as f:
            f.write(new_content)
        return updated
    return []


def report(updated_apps: list):
    apps_str = ", ".join(app.split("(")[0][1:-1] for app in updated_apps)
    try:
        api_url = f"https://api.chuckfang.com/github/GitHub更新{apps_str}?url=https://github.com/Zitann/HarmonyOS-Haps"
        requests.get(api_url, timeout=5)
        print(f"已通知API: 有软件更新，更新应用: {apps_str}")
    except Exception as e:
        print(f"通知API失败: {e}")


if __name__ == "__main__":
    update_titles = ["一次开发，多端部署", "鸿蒙手机/平板", "鸿蒙电脑"]
    updated_apps = []
    for title in update_titles:
        updated_apps.extend(update(title))
    if updated_apps:
        print("README已更新")
        report(updated_apps)
        apps_str = ", ".join(app.split("(")[0][1:-1] for app in updated_apps)
        with open(".apps_str.txt", "w", encoding="utf-8") as f:
            f.write(apps_str)
    else:
        print("README无需更新")
