# /// script
# dependencies = [
#   "requests",
# ]
# ///
import os
import re
import base64
from datetime import datetime
from time import sleep
from urllib.parse import quote

import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# 当前网络环境下 TLS 握手不稳定，统一关闭证书验证
urllib3.disable_warnings(InsecureRequestWarning)

# scripts -> add-hap -> skills -> .agents -> 仓库根目录
ROOT_DIR = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
)
CONTRIBUTERS_PATH = os.path.join(ROOT_DIR, "CONTRIBUTING.md")
SVG_PATH = os.path.join(ROOT_DIR, "assets", "contributers.svg")

UA_HEADERS = {"User-Agent": "harmonyos-haps-script"}

# README 时间列中无需联网查询的特殊状态（沉底显示）
SKIP_STATES = ("已归档", "闭源", "无release")

REPO_URL = "https://github.com/Zitann/HarmonyOS-Haps"

def http_get(url: str, headers: dict = None, timeout: int = 15, retries: int = 3):
    """带 UA、超时和有限重试的 GET 请求，失败时返回 None。"""
    merged = {**UA_HEADERS, **(headers or {})}
    for attempt in range(retries):
        try:
            return requests.get(url, headers=merged, timeout=timeout, verify=False)
        except requests.RequestException as e:
            print(f"请求失败({attempt + 1}/{retries}): {url} - {e}")
            sleep(5)
    return None


def github_headers() -> dict:
    token = os.environ.get("GITHUB_TOKEN")
    return {
        "Accept": "application/vnd.github.v3+json",
        "Authorization": f"Bearer {token}",
    }


def image_to_base64(url: str) -> str:
    """下载图片并转为 data URI，失败返回空字符串。"""
    resp = http_get(url)
    if resp is not None and resp.status_code == 200:
        return "data:image/png;base64," + base64.b64encode(resp.content).decode("utf-8")
    return ""


def fetch_avatar(home_url: str) -> str:
    """按平台获取用户头像的 data URI，失败返回空字符串。"""
    if "github.com" in home_url:
        api_url = home_url.replace("https://github.com/", "https://api.github.com/users/")
        headers = github_headers()
        extract = lambda data: data.get("avatar_url", "")
    elif "gitee.com" in home_url:
        api_url = home_url.replace("https://gitee.com/", "https://gitee.com/api/v5/users/")
        headers = {}
        extract = lambda data: data.get("avatar_url", "")
    elif "atomgit.com" in home_url:
        api_url = home_url.replace(
            "https://atomgit.com/", "https://atomgit.com/api/user/v1/un/detail?path="
        )
        headers = {}
        extract = lambda data: "https://file.atomgit.com/" + data.get("photo", "")
    else:
        print(f"不支持的平台: {home_url}")
        return ""

    resp = http_get(api_url, headers=headers)
    if resp is None or resp.status_code != 200:
        return ""
    avatar_url = extract(resp.json())
    return image_to_base64(avatar_url) if avatar_url else ""


def send_broadcast(text: str) -> bool:
    """向 REPO_URL 的订阅者广播一条纯文本消息（openBroadcast 接口）。
    缺失时打印提示并跳过；失败不抛异常，返回是否发送成功。
    """
    union_id = os.environ.get("BROADCAST_UNION_ID")
    channel_id = os.environ.get("BROADCAST_CHANNEL_ID")
    if not union_id or not channel_id:
        print("缺少 BROADCAST_UNION_ID / BROADCAST_CHANNEL_ID，跳过广播通知")
        return False

    encoded_url = quote(quote(REPO_URL, safe=""), safe="")
    api_url = (
        "http://api.chuckfang.com:12580/subscribe/openBroadcast"
        f"?unionId={union_id}&channelId={channel_id}&url={encoded_url}"
    )
    try:
        resp = requests.post(
            api_url,
            data=text.encode("utf-8"),
            headers={"Content-Type": "text/plain"},
            timeout=5,
        )
        data = resp.json()
        if resp.status_code == 200 and data.get("status") == 200:
            return True
        print(f"通知API返回异常: {resp.status_code} {data}")
        return False
    except Exception as e:
        print(f"通知API失败: {e}")
        return False


def normalize_dt(dt: datetime) -> datetime:
    """带时区的时间统一转为本地 naive 时间。"""
    if dt is not None and dt.tzinfo is not None:
        return dt.astimezone().replace(tzinfo=None)
    return dt


def format_display_time(dt: datetime) -> str:
    """今年显示 MM-DD，跨年显示 YYYY-MM-DD，空值返回空串。"""
    dt = normalize_dt(dt)
    if dt is None:
        return ""
    if dt.year == datetime.now().year:
        return dt.strftime("%m-%d")
    return dt.strftime("%Y-%m-%d")


def get_remote_time(url: str):
    """获取仓库最新 release 的发布时间。GitHub/Gitee 走官方 API，AtomGit 抓页面兜底。"""
    if "github.com" in url:
        m = re.search(r"github\.com/([^/]+/[^/]+)", url)
        if not m:
            return None
        api_url = f"https://api.github.com/repos/{m.group(1)}/releases/latest"
        resp = http_get(api_url, headers=github_headers())
        if resp is not None and resp.status_code == 200:
            published = resp.json().get("published_at")
            if published:
                return datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ")
        return None
    if "gitee.com" in url:
        m = re.search(r"gitee\.com/([^/]+/[^/]+)", url)
        if not m:
            return None
        api_url = f"https://gitee.com/api/v5/repos/{m.group(1)}/releases/latest"
        resp = http_get(api_url)
        if resp is not None and resp.status_code == 200:
            created = resp.json().get("created_at")
            if created:
                return normalize_dt(
                    datetime.strptime(created, "%Y-%m-%dT%H:%M:%S%z")
                )
        return None
    if "atomgit.com" in url:
        url_clean = url.replace("/tags?tab=release", "")
        resp = http_get(url_clean)
        if resp is not None and resp.status_code == 200:
            m = re.search(r"type:\s*'PROJECT',\s*id:\s*'(\d+)'", resp.text)
            if m:
                api = f"https://atomgit.com/api/v3/projects/{m.group(1)}?_input_charset=utf-8"
                resp2 = http_get(api)
                if resp2 is not None and resp2.status_code == 200:
                    return normalize_dt(
                        datetime.strptime(
                            resp2.json()["last_activity_at"], "%Y-%m-%dT%H:%M:%S%z"
                        )
                    )
            else:
                print(f"无法从AtomGit链接中获取项目ID: {url_clean}")
        return None
    print(f"不支持的链接: {url}")
    return None


def get_latest_commit_time(repo_url: str):
    """获取默认分支最新 commit 时间，用于无 release 的项目。"""
    if "github.com" in repo_url:
        m = re.search(r"github\.com/([^/]+/[^/]+)", repo_url)
        if not m:
            return None
        api = f"https://api.github.com/repos/{m.group(1)}/commits?per_page=1"
        resp = http_get(api, headers=github_headers())
        if resp is None or resp.status_code != 200:
            return None
        data = resp.json()
        if data:
            return datetime.strptime(
                data[0]["commit"]["committer"]["date"], "%Y-%m-%dT%H:%M:%SZ"
            )
        return None
    if "gitee.com" in repo_url:
        m = re.search(r"gitee\.com/([^/]+/[^/]+)", repo_url)
        if not m:
            return None
        api = f"https://gitee.com/api/v5/repos/{m.group(1)}/commits?per_page=1"
        resp = http_get(api)
        if resp is None or resp.status_code != 200:
            return None
        data = resp.json()
        if data:
            return normalize_dt(
                datetime.strptime(
                    data[0]["commit"]["committer"]["date"], "%Y-%m-%dT%H:%M:%S%z"
                )
            )
        return None
    return None
