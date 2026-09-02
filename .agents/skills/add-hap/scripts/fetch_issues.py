# /// script
# dependencies = [
#   "requests",
# ]
# ///
"""拉取本仓库 issue 列表（106 号之后），检查是否有人提供 GitHub 软件仓库链接。"""
import os

from common import http_get, github_headers

REPO = "Zitann/HarmonyOS-Haps"
MIN_NUMBER = 107  # 只看 106 号之后（从 107 号开始）的 issue


def fetch_issues() -> list:
    """翻页拉取 open 状态的 issue，返回编号 >= 107 的列表（按编号升序）。"""
    page = 1
    issues = []
    while True:
        url = f"https://api.github.com/repos/{REPO}/issues?state=open&per_page=100&page={page}"
        resp = http_get(url, headers=github_headers())
        if resp is None or resp.status_code != 200:
            print(f"拉取失败: HTTP {resp.status_code if resp else '无响应'}")
            return []
        batch = resp.json()
        # issues 端点会混入 pull request，这里只保留真正的 issue
        issues.extend(i for i in batch if "pull_request" not in i)
        if len(batch) < 100:
            break
        page += 1
    return sorted(
        (i for i in issues if i["number"] >= MIN_NUMBER), key=lambda x: x["number"]
    )


def main():
    if not os.environ.get("GITHUB_TOKEN"):
        print("请先设置环境变量 GITHUB_TOKEN")
        return
    issues = fetch_issues()
    if not issues:
        print("没有找到 106 号之后的 open issue")
        return
    for i in issues:
        body = i.get("body") or ""
        preview = body[:150]
        if len(body) > 150:
            preview += "..."
        print(f"#{i['number']} [{i['state']}] {i['title']} ({i['created_at'][:10]})")
        print(f"    {preview or '(无内容)'}")


if __name__ == "__main__":
    main()
