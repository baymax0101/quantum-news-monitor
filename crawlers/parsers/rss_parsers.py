"""RSS/Atom 解析器：处理结构化信息源（Nature, Science, arXiv 等）。"""

import logging

import feedparser

logger = logging.getLogger("crawler.parsers.rss")


def parse_rss(
    feed_content: str,
    source_name: str,
    source_url: str,
    dimension: str,
    max_entries: int = 30,
) -> list[dict]:
    """
    解析 RSS/Atom feed 内容。

    Args:
        feed_content: RSS XML 文本（或 URL，feedparser 两种都支持）
        source_name: 信息源名称
        source_url: 信息源主页
        dimension: policy/industry/research
        max_entries: 最大返回数

    Returns:
        [{"title":..., "url":..., "summary":..., "publish_time":..., ...}, ...]
    """
    feed = feedparser.parse(feed_content)
    results = []

    for entry in feed.entries[:max_entries]:
        title = entry.get("title", "").strip()
        link = entry.get("link", "")
        summary = entry.get("summary", "") or entry.get("description", "")
        # 清理 HTML 标签做纯文本摘要
        from bs4 import BeautifulSoup

        if summary:
            summary = BeautifulSoup(summary, "html.parser").get_text(" ", strip=True)[:300]

        published = ""
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            import time

            published = time.strftime("%Y-%m-%d", entry.published_parsed)
        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
            import time

            published = time.strftime("%Y-%m-%d", entry.updated_parsed)

        if title and link:
            results.append(
                {
                    "title": title,
                    "url": link,
                    "summary": summary,
                    "source_name": source_name,
                    "source_url": source_url,
                    "dimension": dimension,
                    "publish_time": published,
                }
            )

    return results
