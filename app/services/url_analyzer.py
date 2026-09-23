# src/resume_agent/services/url_analyzer.py

import httpx
import json
import re
from urllib.parse import urlparse

from app.services.llm_service import get_llm

try:
    import trafilatura
except ImportError:
    trafilatura = None

from bs4 import BeautifulSoup


async def fetch_page_content(url: str) -> dict:
    """抓取网页主要内容"""
    async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        resp = await client.get(url, headers=headers)
        resp.raise_for_status()
        html = resp.text

    title = ""
    text = ""

    # 优先用 trafilatura 提取正文
    if trafilatura:
        text = trafilatura.extract(html, include_comments=False, include_tables=False) or ""
        metadata = trafilatura.extract_metadata(html)
        title = metadata.title if metadata else ""

    # 兜底用 BeautifulSoup
    if not text:
        soup = BeautifulSoup(html, "lxml")
        title = soup.title.string.strip() if soup.title else ""
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n", strip=True)

    # 限制长度
    text = text[:8000]
    return {"title": title, "text": text, "url": url}


def is_github_url(url: str) -> bool:
    return "github.com" in urlparse(url).netloc.lower()


async def analyze_url_to_project(url: str) -> dict:
    """
    分析网址，返回结构化的项目经验
    """
    llm = get_llm()

    if is_github_url(url):
        # GitHub 仓库特殊处理
        # 简单提取 owner/repo
        match = re.search(r"github\.com/([^/]+)/([^/]+)", url)
        if match:
            owner, repo = match.group(1), match.group(2)
            # 这里可以调用更详细的 GitHub API，暂时先用页面抓取 + LLM
            content = await fetch_page_content(url)
            source_type = "github"
        else:
            content = await fetch_page_content(url)
            source_type = "github"
    else:
        content = await fetch_page_content(url)
        source_type = "website"

    prompt = f"""你是专业的简历项目经历整理专家。请根据下面提供的网页/仓库内容，整理成规范的项目经验。

网址：{url}
标题：{content.get("title", "")}
内容：
{content.get("text", "")[:6000]}

请输出严格的 JSON 格式（不要 markdown，不要解释）：
{{
  "name": "项目名称",
  "description": "一句话项目描述（50字以内）",
  "period": "如果能推断时间就写，否则留空字符串",
  "highlights": [
    "技术亮点或成果1",
    "技术亮点或成果2",
    "技术亮点或成果3"
  ],
  "technologies": ["用到的技术1", "技术2"],
  "url": "{url}",
  "source_type": "{source_type}"
}}

要求：
1. 只基于提供的内容，不要编造
2. highlights 尽量具体、有技术含量或成果导向
3. 如果是代码仓库，重点提取技术栈和核心功能
4. 如果是普通网页，重点提取业务价值和实现要点
"""

    response = llm.invoke(prompt)
    result_text = response.content.strip()

    # 清理代码块
    if "```" in result_text:
        result_text = result_text.split("```")[1]
        if result_text.startswith("json"):
            result_text = result_text[4:]
    result_text = result_text.strip()

    try:
        data = json.loads(result_text)
        data["url"] = url
        return data
    except Exception:
        # 兜底
        return {
            "name": content.get("title") or "未命名项目",
            "description": content.get("text", "")[:100],
            "period": "",
            "highlights": [],
            "technologies": [],
            "url": url,
            "source_type": source_type
        }