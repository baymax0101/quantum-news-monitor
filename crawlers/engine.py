"""爬虫引擎：加载信息源、调度抓取、解析入库。"""

import json
import re
import time
import logging
import os
from datetime import datetime, timezone
from typing import Optional

_PROGRESS_LOG = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs", "crawl_progress.log")


def _plog(msg):
    """同时输出到控制台和进度日志文件。"""
    print(msg, flush=True)
    try:
        with open(_PROGRESS_LOG, "a", encoding="utf-8") as _f:
            _f.write(msg + "\n")
    except Exception:
        pass

from crawlers.fetcher import fetch
from crawlers.parsers.base import extract_links
from crawlers.parsers.rss_parsers import parse_rss

logger = logging.getLogger("crawler.engine")

SOURCES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sources.json")

# 合肥相关关键词（用于自动检测非合肥源中的合肥内容）
HEFEI_KEYWORDS = ["合肥", "Hefei", "hefei", "中科大", "国盾", "本源量子", "国仪量子"]


def _detect_hefei(title: str, url: str, source_region: str) -> str:
    """自动检测文章是否涉及合肥。如果来源已是 hefei 或内容涉及合肥关键词，返回 hefei。"""
    if source_region == "hefei":
        return "hefei"
    # 检查标题和 URL 中是否包含合肥关键词
    combined = f"{title} {url}"
    for kw in HEFEI_KEYWORDS:
        if kw.lower() in combined.lower():
            return "hefei"
    return source_region


def load_sources() -> list[dict]:
    """加载信息源配置，返回启用的源列表。"""
    with open(SOURCES_PATH, "r", encoding="utf-8") as f:
        sources = json.load(f)
    return [s for s in sources if s.get("enabled", True)]


def crawl_source(source: dict) -> list[dict]:
    """
    爬取单个信息源并解析。

    Args:
        source: 信息源配置字典

    Returns:
        解析后的文章列表
    """
    results = []
    name = source["name"]
    url = source.get("rss_url", source["url"])
    dimension = source["dimension"]
    source_region = source.get("region", "domestic")
    keywords = source.get("keywords")
    encoding = source.get("encoding")
    parser_type = source.get("parser", "html_generic")

    if parser_type in ("rss", "rsshub"):
        # RSS / RSSHub 源：先 fetch（有超时控制），再 parse（避免 feedparser 内部无超时卡死）
        try:
            rss_content = fetch(url, timeout=30, max_retries=1, delay=1.0)
            if rss_content is None:
                logger.warning(f"Failed to fetch RSS for {name}")
                return []
            raw_results = parse_rss(rss_content, name, source["url"], dimension)
        except Exception as e:
            logger.error(f"RSS parse error for {name}: {e}")
            return []
        for r in raw_results:
            r["region"] = _detect_hefei(r.get("title", ""), r.get("url", ""), source_region)
        return raw_results

    # HTML 源：fetch 后 extract_links
    html = fetch(url, encoding=encoding)
    if html is None:
        logger.warning(f"Failed to fetch HTML for {name}")
        return []

    try:
        links = extract_links(html, url, keywords=keywords)
    except Exception as e:
        logger.error(f"Link extraction error for {name}: {e}")
        return []

    for link in links:
        title = link["title"]
        link_url = link["url"]
        results.append({
            "title": title,
            "url": link_url,
            "summary": link.get("summary", ""),
            "source_name": name,
            "source_url": source["url"],
            "dimension": dimension,
            "region": _detect_hefei(title, link_url, source_region),
            "publish_time": "",
        })

    return results


def crawl_all(progress_callback=None) -> dict:
    """
    全量爬取所有启用的信息源。

    Args:
        progress_callback: 可选回调，签名为 (current: int, total: int, source_name: str)

    Returns:
        {"success": N, "failed": N, "new_articles": N, "total_sources": N}
    """
    from models import insert_article, start_crawl_log, finish_crawl_log, set_config

    sources = load_sources()
    total = len(sources)
    logger.info(f"Starting crawl: {total} sources")
    _plog(f"[CRAWL] Total {total} sources, starting...")

    log_id = start_crawl_log(total)
    success_count = 0
    new_articles = 0

    for i, source in enumerate(sources):
        name = source["name"]
        if progress_callback:
            progress_callback(i + 1, total, name)

        try:
            articles = crawl_source(source)

            if articles:
                inserted = 0
                for article in articles:
                    if insert_article(article):
                        inserted += 1
                new_articles += inserted
                logger.info(f"  {name}: {len(articles)} found, {inserted} new")
                _plog(f"  [{i+1}/{total}] {name}: {len(articles)} found, {inserted} new")
            else:
                logger.info(f"  {name}: 0 articles")
                _plog(f"  [{i+1}/{total}] {name}: 0 articles")

            success_count += 1

        except Exception as e:
            logger.error(f"  {name}: ERROR - {e}")
            _plog(f"  [{i+1}/{total}] {name}: ERROR - {e}")

        # 间隔避免被封
        if i < total - 1:
            time.sleep(2)

    # 更新状态
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    set_config("last_crawl_time", now)

    status = "completed" if success_count > 0 else "failed"
    finish_crawl_log(log_id, success_count, new_articles, status)

    logger.info(f"Crawl complete: {success_count}/{total} sources OK, {new_articles} new articles")
    _plog(f"\n[CRAWL] Done: {success_count}/{total} sources OK, {new_articles} new\n")

    return {
        "success": success_count,
        "failed": total - success_count,
        "new_articles": new_articles,
        "total_sources": total,
    }
