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

# 核心量子关键词（文章标题或URL中必须匹配至少一个，否则丢弃）
CORE_KEYWORDS = [
    "量子", "QKD", "quantum", "entanglement", "qubit", "Qubit", "纠缠",
    "quantum communication", "quantum key", "quantum network",
    "quantum cryptography", "quantum internet", "quantum teleportation",
]

# 排除的无关关键词（减少误命中）
EXCLUDE_PATTERNS = [
    r"量子力学入门", r"量子科普", r"量子力学基础",
]

# URL 黑名单模式（排除登录页、搜索页、标签页等无关链接）
URL_BLACKLIST = [
    r"/login", r"/signin", r"/register", r"/signup",
    r"/search", r"/tag/", r"/tags/", r"/category/",
    r"/author/", r"/user/", r"/profile/",
    r"/page/\d+", r"/archive/", r"/feed\.",
    r"javascript:", r"mailto:", r"tel:",
    r"\.pdf$", r"\.doc$", r"\.docx$", r"\.xls$", r"\.xlsx$",
]


def _is_blacklisted_url(url: str) -> bool:
    """检查 URL 是否在黑名单中。"""
    for pattern in URL_BLACKLIST:
        if re.search(pattern, url, re.IGNORECASE):
            return True
    return False


def _get_link_text(tag) -> str:
    """
    提取链接的标题文本。
    优先顺序：1) 标签内文本 2) title 属性 3) 父标题标签文本
    """
    # 1. 直接文本内容
    text = tag.get_text(strip=True)
    if text and text not in ("阅读更多", "更多", "More", "more", "详情", "点击查看"):
        return text

    # 2. title 属性
    title = tag.get("title", "").strip()
    if title:
        return title

    # 3. 父标题标签
    for parent_tag in ("h1", "h2", "h3", "h4", "h5"):
        parent = tag.find_parent(parent_tag)
        if parent:
            parent_text = parent.get_text(strip=True)
            if parent_text:
                return parent_text

    return text


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
    # 核心量子关键词（必须至少命中一个）
    core_pattern = re.compile("|".join(re.escape(kw) for kw in CORE_KEYWORDS), re.IGNORECASE)

    # 优先从语义容器中提取链接（article, section 等）
    priority_containers = soup.find_all(["article", "section", "main", "div"],
                                         class_=re.compile(r"news|article|post|content|list|item", re.I))

    # 收集所有候选链接（优先级容器内优先）
    candidate_tags = []
    processed = set()

    # 先处理优先级容器内的链接
    for container in priority_containers:
        for tag in container.find_all("a", href=True):
            tag_id = id(tag)
            if tag_id not in processed:
                candidate_tags.append(tag)
                processed.add(tag_id)

    # 再处理其他链接
    for tag in soup.find_all("a", href=True):
        tag_id = id(tag)
        if tag_id not in processed:
            candidate_tags.append(tag)
            processed.add(tag_id)

    for tag in candidate_tags:
        href = tag["href"].strip()

        if not href:
            continue
        if href.startswith("#") or href.startswith("javascript:"):
            continue

        full_url = urljoin(base_url, href)

        # 避免同页面内重复
        if full_url in seen_urls:
            continue

        # URL 黑名单过滤
        if _is_blacklisted_url(full_url):
            continue

        # 提取标题文本
        text = _get_link_text(tag)
        if not text:
            continue

        # 核心关键词必须命中（过滤无关文章）
        if not core_pattern.search(text) and not core_pattern.search(href):
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
