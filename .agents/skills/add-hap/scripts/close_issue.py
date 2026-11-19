# /// script
# dependencies = [
#   "requests",
# ]
# ///
import os
import sys

import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning

from common import github_headers

# 当前网络环境下 TLS 握手不稳定，统一关闭证书验证
urllib3.disable_warnings(InsecureRequestWarning)

REPO = "Zitann/HarmonyOS-Haps"
COMMENT = "已收录，感谢分享"


def close_issue(number: int) -> bool:
    """发表评论并关闭 issue，全部成功返回 True。"""
    api = f"https://api.github.com/repos/{REPO}/issues/{number}"
    headers = github_headers()
    # 1. 发表评论
    r1 = requests.post(
        f"{api}/comments", headers=headers, json={"body": COMMENT}, timeout=15, verify=False
    )
    if r1.status_code not in (200, 201):
        print(f"评论失败: HTTP {r1.status_code} {r1.text}")
        return False
    # 2. 关闭 issue
    r2 = requests.patch(
        api, headers=headers, json={"state": "closed"}, timeout=15, verify=False
    )
    if r2.status_code != 200:
        print(f"关闭失败: HTTP {r2.status_code} {r2.text}")
        return False
    print(f"已回复并关闭 issue #{number}")
    return True


def main():
    if not os.environ.get("GITHUB_TOKEN"):
        print("请先设置环境变量 GITHUB_TOKEN")
        sys.exit(1)
    if len(sys.argv) < 2:
        print("用法: uv run close_issue.py <issue编号> [issue编号 ...]")
        sys.exit(1)
    try:
        numbers = list(dict.fromkeys(int(arg) for arg in sys.argv[1:]))
        if any(number <= 0 for number in numbers):
            raise ValueError
    except ValueError:
        print("issue 编号必须是正整数")
        sys.exit(1)

    failed = []
    for number in numbers:
        try:
            if not close_issue(number):
                failed.append(number)
        except requests.RequestException as exc:
            print(f"处理 issue #{number} 失败: {exc}")
            failed.append(number)
    if failed:
        print(f"处理失败的 issue: {', '.join(f'#{number}' for number in failed)}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
