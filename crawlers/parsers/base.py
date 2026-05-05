"""通用 HTML 解析器：提取页面链接，关键词过滤。"""

import re
import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup

logger = logging.getLogger("crawler.parsers.base")

# 量子通信核心关键词（中英文）
DEFAULT_KEYWORDS = [
    "量子", "QKD", "quantum", "Quantum", "QUANTUM",
    "量子通信", "量子密钥", "量子网络", "量子加密",
    "quantum communication", "quantum key", "quantum network",
    "quantum cryptography", "quantum internet",
    "Qubit", "qubit", "entanglement", "纠缠",
    "量子隐形传态", "quantum teleportation",
]

# 排除的无关关键词（减少误命中）
EXCLUDE_PATTERNS = [
    r"量子力学入门", r"量子科普", r"量子力学基础",
]


def extract_links(
    html: str,
    base_url: str,
    keywords: list[str] | None = None,
    limit: int = 50,
) -> list[dict]:
    """
    从 HTML 页面提取包含关键词的链接。

    Args:
        html: 页面 HTML 文本
        base_url: 用于拼接相对链接的基础 URL
        keywords: 自定义关键词列表，默认用 DEFAULT_KEYWORDS
        limit: 最大返回条目数

    Returns:
        [{"title": "...", "url": "...", "summary": "..."}, ...]
    """
    if keywords is None:
        keywords = DEFAULT_KEYWORDS

    soup = BeautifulSoup(html, "lxml")
    results = []
    seen_urls = set()

    # 构建关键词正则（忽略大小写）
    pattern = re.compile("|".join(re.escape(kw) for kw in keywords), re.IGNORECASE)

    for tag in soup.find_all("a", href=True):
        text = tag.get_text(strip=True)
        href = tag["href"].strip()

        if not text or not href:
            continue
        if href.startswith("#") or href.startswith("javascript:"):
            continue

        full_url = urljoin(base_url, href)

        # 避免同页面内重复
        if full_url in seen_urls:
            continue

        # 关键词匹配（在文本或 href 中）
        match = pattern.search(text) or pattern.search(href)
        if not match:
            continue

        # 排除无关模式
        skip = False
        for exc in EXCLUDE_PATTERNS:
            if re.search(exc, text):
                skip = True
                break
        if skip:
            continue

        seen_urls.add(full_url)
        results.append({
            "title": text[:200],
            "url": full_url,
            "summary": "",
        })

        if len(results) >= limit:
            break

    return results


def extract_text(html: str, max_chars: int = 300) -> str:
    """提取页面正文文本（前 max_chars 个字符做摘要）。"""
    soup = BeautifulSoup(html, "lxml")
    # 移除 script 和 style
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    # 压缩空白
    text = re.sub(r"\s+", " ", text)
    return text[:max_chars]
