# /// script
# dependencies = [
#   "requests",
# ]
# ///
import sys

from common import (
    read_table,
    write_table,
    split_row,
    get_project_time,
    format_display_time,
    parse_old_time_str,
    SKIP_STATES,
    README_PATH,
)


def make_row(name: str, repo_url: str, desc: str, time_str: str) -> str:
    return f"| [{name}]({repo_url}) | [Link]({repo_url}/releases) | {desc} | {time_str} |"


def find_insert_index(data_lines: list, new_dt) -> int:
    """找到新行的插入下标。表格顺序与 update.py 排序一致：
    “更新中”固定最前，其后正常日期倒序，“已归档/闭源/无release”沉底。
    新行插入到日期比它旧的行之前、沉底区之前。"""
    for i, line in enumerate(data_lines):
        cols = split_row(line)
        if cols is None:
            continue
        state = cols[3]
        if state == "更新中":  # 固定置顶区，跳过
            continue
        if state in SKIP_STATES:  # 沉底区，插到它前面
            return i
        old_dt = parse_old_time_str(state)
        if old_dt is None or (new_dt and new_dt > old_dt):
            return i
    return len(data_lines)


def add_project(repo_url: str, name: str, desc: str, platform: str) -> bool:
    """添加项目到 README 对应分类表格，已存在或找不到表格时返回 False。"""
    print(f"正在解析项目: {repo_url}")
    print(f"项目名称: {name}")
    print(f"项目描述: {desc}")

    latest_dt = get_project_time(repo_url)
    latest_time = format_display_time(latest_dt)
    if not latest_time:
        print("警告: 未能获取 release 或 commit 时间")
        latest_time = "无release"
    print(f"最新发布时间: {latest_time}")

    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()

    result = read_table(content, platform)
    if not result:
        print(f"未找到分类表格: {platform}")
        return False
    header_lines, data_lines, old_table = result

    if any(repo_url in line for line in data_lines):
        print(f"项目 {name} 已存在于列表中")
        return False

    new_row = make_row(name, repo_url, desc, latest_time)
    index = find_insert_index(data_lines, latest_dt)
    data_lines.insert(index, new_row)

    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(write_table(content, old_table, header_lines, data_lines))

    print(f"项目 {name} 已成功添加到列表第 {index + 1} 位")
    return True


def main():
    if len(sys.argv) != 5:
        print("用法: python add.py <项目仓库URL> <项目名称> <项目描述> <平台>")
        sys.exit(1)
    repo_url, name, desc, platform = (arg.strip() for arg in sys.argv[1:5])

    if not repo_url.startswith(("https://github.com/", "https://gitee.com/")):
        print("请提供有效的GitHub或Gitee仓库URL")
        sys.exit(1)

    print("添加成功！" if add_project(repo_url, name, desc, platform) else "添加失败！")


if __name__ == "__main__":
    main()
