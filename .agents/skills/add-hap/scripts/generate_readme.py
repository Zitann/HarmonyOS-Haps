# /// script
# dependencies = [
#   "requests",
#   "pyyaml",
# ]
# ///
"""从 apps.yaml 生成 README.md 的三个分类表格区域。

apps.yaml 是唯一应用数据源；README.md 中三个分类表格区由此脚本渲染，
其它文案区（目录/声明/安装工具/反馈/鸣谢等）保持手工维护不动。
"""
import re
import sys
from datetime import datetime
from pathlib import Path

import yaml

# scripts -> add-hap -> skills -> .agents -> 仓库根目录
ROOT = Path(__file__).resolve().parents[4]
APPS_YAML = ROOT / "apps.yaml"
README = ROOT / "README.md"

# 分类顺序与 README 中的标题一致
CATEGORIES = ["一次开发，多端部署", "鸿蒙手机/平板", "鸿蒙电脑"]

SKIP_STATES = ("已归档", "闭源", "无release")  # 时间列的特殊状态（沉底）


def parse_time_str(s: str):
    """解析时间列为 datetime；MM-DD 视为今年。无法解析返回 None。"""
    s = s.strip()
    if s in SKIP_STATES:
        return None
    for fmt in ("%Y-%m-%d",):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            pass
    try:
        return datetime.strptime(f"{datetime.now().year}-{s}", "%Y-%m-%d")
    except ValueError:
        return None


def sort_key(app):
    """有日期按日期倒序在前，特殊状态/无法解析沉底（保持原顺序）。"""
    dt = parse_time_str(app.get("time", ""))
    if dt is None:
        # 沉底：用一个远小于任何日期的哨兵，且保持原相对顺序
        return (1, 0)
    return (0, -dt.toordinal())


def render_table(apps: list) -> str:
    """渲染某个分类的完整 markdown 表格（含标题行、分隔行、数据行）。"""
    header = "| 软件     | 下载链接            | 描述                                                         | 更新                                                 |"
    sep = "| ------------------- | ------------------------------------------------------------ | ------------------------------------------------------------ | ------------------------------------------------------------ |"
    lines = [header, sep]
    for app in apps:
        name = app["name"]
        url = app["url"]
        link = app.get("link") or f"{url}/releases"
        desc = app["desc"]
        time = app["time"]
        lines.append(
            f"| [{name}]({url}) | [Link]({link}) | {desc} | {time} |"
        )
    return "\n".join(lines) + "\n"


def render_section(title: str, apps: list) -> str:
    """渲染一个分类区块：### 标题 + 空行 + 表格。"""
    return f"### {title}\n\n{render_table(apps)}"


def _normalize_time(v):
    """time 字段兼容字符串与 yaml 自动解析出的 date。
    date 按展示规则还原：今年 -> MM-DD，跨年 -> YYYY-MM-DD。"""
    if isinstance(v, datetime):
        v = v.date()
    if hasattr(v, "year"):  # datetime.date
        if v.year == datetime.now().year:
            return v.strftime("%m-%d")
        return v.strftime("%Y-%m-%d")
    return str(v)


def load_apps():
    """读取 apps.yaml，返回 (分类名 -> 应用列表) 的有序 dict。"""
    with open(APPS_YAML, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    cats = data.get("categories") or {}
    result = {}
    for cat in CATEGORIES:
        if cat in cats:
            apps = []
            for item in cats[cat]:
                app = dict(item)
                app["time"] = _normalize_time(app.get("time", ""))
                apps.append(app)
            result[cat] = apps
        else:
            print(f"警告: apps.yaml 缺少分类 {cat}")
            result[cat] = []
    return result


def generate() -> str:
    """生成 README 全文，返回新内容。"""
    apps = load_apps()
    with open(README, "r", encoding="utf-8") as f:
        content = f.read()

    # 三个分类区：从 "### 一次开发，多端部署" 到 "### 反馈" 之前
    start_marker = f"### {CATEGORIES[0]}"
    end_marker = "### 反馈"
    start = content.find(start_marker)
    end = content.find(end_marker)
    if start == -1 or end == -1 or end <= start:
        print("错误: README.md 中找不到分类区域边界")
        sys.exit(1)

    sections = []
    for cat in CATEGORIES:
        app_list = sorted(apps.get(cat, []), key=sort_key)
        sections.append(render_section(cat, app_list))

    new_block = "\n".join(sections) + "\n"
    new_content = content[:start] + new_block + content[end:]
    return new_content


def main():
    new_content = generate()
    with open(README, "w", encoding="utf-8") as f:
        f.write(new_content)
    apps = load_apps()
    print("README.md 已生成")
    for cat in CATEGORIES:
        print(f"  {cat}: {len(apps.get(cat, []))} 个应用")


if __name__ == "__main__":
    main()
