# /// script
# dependencies = [
#   "requests",
# ]
# ///
import os
import re
import sys
import requests
from datetime import datetime
from dataclasses import dataclass
import urllib3
from urllib3.exceptions import InsecureRequestWarning
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning, message=".*Parsing dates involving a day of month without a year.*")
urllib3.disable_warnings(InsecureRequestWarning)
README_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "README.md")

@dataclass
class Item:
    name: str
    url: str
    desc: str
    time: str

def get_project_info(repo_url):
    """从仓库URL获取项目信息"""
    headers = {"User-Agent": "add-project-script"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        resp = requests.get(repo_url, headers=headers, verify=False)
        if resp.status_code != 200:
            return None, None, None
        
        html = resp.text
        
        # 提取项目名称
        name_match = re.search(r'<title>([^/]+)/([^:]+)', html)
        if name_match:
            project_name = name_match.group(2).strip()
        else:
            project_name = repo_url.split('/')[-1]
        
        # 提取描述
        desc_match = re.search(r'<meta property="og:description" content="([^"]*)"', html)
        if desc_match:
            description = desc_match.group(1).strip()
        else:
            description = "暂无描述"
        
        # 获取releases链接
        releases_url = repo_url.rstrip('/') + '/releases'
        
        return project_name, description, releases_url
    except Exception as e:
        print(f"获取项目信息失败: {e}")
        return None, None, None

def get_latest_release_time(url):
    """获取最新发布时间"""
    headers = {"User-Agent": "add-project-script"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        resp = requests.get(url, headers=headers, verify=False)
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
    except Exception:
        pass
    return None

def format_time_mmdd(iso_time):
    """格式化时间为MM-DD格式"""
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

def add_project(repo_url):
    """添加项目到README"""
    print(f"正在解析项目: {repo_url}")
    
    # 获取项目信息
    name, desc, releases_url = get_project_info(repo_url)
    if not name:
        print("获取项目信息失败")
        return False
    
    print(f"项目名称: {name}")
    print(f"项目描述: {desc}")
    
    # 获取最新发布时间
    latest_time = get_latest_release_time(releases_url)
    time_fmt = format_time_mmdd(latest_time) if latest_time else datetime.now().strftime("%m-%d")
    
    print(f"最新发布时间: {time_fmt}")
    
    # 读取README
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 找到表格
    table_match = re.search(r"### 鸿蒙项目列表\s*\n((?:\|.*\n)+)", content)
    if not table_match:
        print("未找到项目列表表格")
        return False
    
    table = table_match.group(1)
    lines = table.strip().split("\n")
    
    # 构建新项目条目
    new_item = f"| [{name}]({repo_url}) | [Link]({releases_url}) | {desc} | {time_fmt} |"
    
    # 检查是否已存在
    for line in lines:
        if name in line and repo_url in line:
            print(f"项目 {name} 已存在于列表中")
            return False

    # 插入新项目（在第4行之后，即跳过表头和分隔线）
    lines.insert(4, new_item)
    
    # 重新组装表格
    new_table = "\n".join(lines) + "\n"
    new_content = content.replace(table, new_table)
    
    # 获取所有项目的作者链接（只匹配第一列的项目名称链接）
    author_links = set()
    for line in lines[2:]:  # 跳过表头和分隔线
        # 匹配每行第一列的链接：| [项目名](仓库链接) | [Link](...) | ...
        match = re.search(r'^\|\s*\[([^\]]+)\]\((https?://(?:github|gitee)\.com/[^/]+/[^)]+)\)', line.strip())
        if match:
            repo_url = match.group(2)
            # 提取作者URL（去掉项目名部分）
            author_url = '/'.join(repo_url.split('/')[:4])  # https://github.com/author
            author_links.add(author_url)
    
    # 生成作者链接列表
    author_list = generate_author_links(author_links)
    if not author_list:
        print("未提取到任何作者链接")
        return False

    print(f"生成的作者列表:\n{author_list}")
    # 在README中添加作者列表
    author_section = "### 鸣谢(不分先后)\n\n" + author_list + "\n"
    # 检查是否已存在作者列表
    author_section_match = re.search(r"### 鸣谢\(不分先后\)\s*\n((?:- .*\n)+)", content)
    new_content = new_content.replace(author_section_match.group(0), author_section)
    
    # 写入文件
    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(new_content)
    
    print(f"项目 {name} 已成功添加到列表中")
    return True

def get_author_info(author_url):
    """获取作者信息，返回(username, display_name, url)"""
    headers = {"User-Agent": "author-info-script"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    try:
        resp = requests.get(author_url, headers=headers, verify=False)
        if resp.status_code != 200:
            return None, None, author_url
        
        html = resp.text
        
        if "github.com" in author_url:
            # GitHub: 提取用户名和显示名
            username_match = re.search(r'github\.com/([^/]+)', author_url)
            username = username_match.group(1) if username_match else ""
            
            # 提取显示名 (GitHub)
            display_match = re.search(r'<meta property="og:title" content="([^"]*)"', html)
            if display_match:
                display_name = display_match.group(1).strip()
                # 去掉GitHub后缀
                display_name = re.sub(r'\s*·\s*GitHub.*$', '', display_name)
                display_name = re.sub(r'\s*-\s*GitHub.*$', '', display_name)
            else:
                display_name = username
            
        elif "gitee.com" in author_url:
            # Gitee: 提取用户名和显示名
            username_match = re.search(r'gitee\.com/([^/]+)', author_url)
            username = username_match.group(1) if username_match else ""
            
            # 提取显示名 (Gitee)
            display_match = re.search(r'<title>([^<]*)</title>', html)
            if display_match:
                display_name = display_match.group(1).strip()
                # 去掉Gitee后缀
                display_name = re.sub(r'\s*-\s*Gitee.*$', '', display_name)
                display_name = re.sub(r'\s*·\s*码云.*$', '', display_name)
            else:
                display_name = username
        else:
            return None, None, author_url
        
        # 如果显示名和用户名相同，只返回用户名
        if display_name.lower() == username.lower():
            return username, None, author_url
        
        return username, display_name, author_url
        
    except Exception as e:
        print(f"获取作者信息失败 {author_url}: {e}")
        # 返回从URL提取的用户名作为fallback
        username_match = re.search(r'(?:github|gitee)\.com/([^/]+)', author_url)
        username = username_match.group(1) if username_match else author_url
        return username, None, author_url

def generate_author_links(author_urls):
    """生成作者链接列表的Markdown格式"""
    author_list = []
    
    for author_url in sorted(set(author_urls)):
        _username, display_name, url = get_author_info(author_url)
        author_list.append(f"- [{display_name.replace(' - Overview', '')}]({url})")
    # 排序
    author_list.sort(key=lambda x: x.lower())
    return "\n".join(author_list)

def extract_and_generate_authors():
    """从README表格中提取作者URL并生成格式化列表"""
    with open(README_PATH, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 找到项目表格
    table_match = re.search(r"### 鸿蒙项目列表\s*\n((?:\|.*\n)+)", content)
    if not table_match:
        print("未找到项目列表表格")
        return ""
    
    table = table_match.group(1)
    lines = table.strip().split("\n")[2:]  # 跳过表头和分隔线
    
    author_urls = set()
    
    for line in lines:
        # 匹配第一列的项目链接
        match = re.search(r'^\|\s*\[([^\]]+)\]\((https?://(?:github|gitee)\.com/[^/]+/[^)]+)\)', line.strip())
        if match:
            project_url = match.group(2)
            # 提取作者URL
            author_url = '/'.join(project_url.split('/')[:4])
            author_urls.add(author_url)
    
    print(f"提取到 {len(author_urls)} 个作者URL")
    return generate_author_links(author_urls)

def main():
    if len(sys.argv) != 2:
        print("用法: python add.py <项目仓库URL>")
        print("示例: python add.py https://github.com/user/project")
        sys.exit(1)
    
    repo_url = sys.argv[1].strip()
    
    # 验证URL格式
    if not (repo_url.startswith("https://github.com/") or repo_url.startswith("https://gitee.com/")):
        print("请提供有效的GitHub或Gitee仓库URL")
        sys.exit(1)
    
    if add_project(repo_url):
        print("添加成功！")
    else:
        print("添加失败！")

if __name__ == "__main__":
    main()