# 量子通信信息监测平台 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 构建一个 Python + Flask Web 应用，从 25+ 权威媒体定时爬取量子通信信息，按政策/产业/科研三维度分类存储，通过 Web 界面生成带统计图表的 HTML 报告。

**Architecture:** Flask 单体应用 + SQLite 本地数据库 + APScheduler 内嵌调度。爬虫模块通过 requests + BeautifulSoup 抓取信息源，通用关键词解析器做兜底，RSS 解析器处理结构化源。前端纯 HTML/CSS/JS + ECharts CDN，无框架依赖。

**Tech Stack:** Python 3.12, uv, Flask 3.x, requests, BeautifulSoup4, APScheduler 3.x, feedparser, SQLite, Jinja2, ECharts (CDN)

---

## 文件结构

```
D:\workproject\summary\
├── pyproject.toml              # 项目配置、依赖声明
├── app.py                      # Flask 入口：工厂函数、路由注册、启动
├── models.py                   # SQLite 数据模型：建表、CRUD 函数
├── sources.json                # 信息源配置（25+ 源，三维度）
├── scheduler.py                # APScheduler 管理：Job 创建/更新/暂停
├── reporter.py                 # 报告生成：查询聚合 + Jinja2 渲染
├── crawlers/
│   ├── __init__.py             # 空文件
│   ├── engine.py               # 爬取引擎：遍历源、去重入库、日志
│   ├── fetcher.py              # HTTP 请求：超时、重试、UA 伪装
│   └── parsers/
│       ├── __init__.py         # 空文件
│       ├── base.py             # 通用解析器：关键词过滤提取链接
│       ├── rss_parsers.py      # RSS/Atom 解析器（Nature, Science, arXiv）
│       └── html_parsers.py     # HTML 页面解析器集合
├── templates/
│   ├── base.html               # 基础布局（导航 + 内容区）
│   ├── dashboard.html          # 仪表盘：概览卡片 + 报告生成 + 日志
│   ├── crawl.html              # 爬取管理：信息源列表 + 启用/禁用
│   ├── settings.html           # 设置：频率/时间/开关
│   └── report.html             # HTML 报告模板：三维度 + ECharts
├── static/
│   ├── css/
│   │   └── style.css           # 全局样式
│   └── js/
│       └── app.js              # 前端交互：API 调用、图表、日期选择器
├── data/                       # 运行时生成，存放 quantum_news.db
├── logs/                       # 运行时生成，存放 crawler.log
└── reports/                    # 运行时生成，存放 HTML 报告
```

---

### Task 1: 项目骨架 — pyproject.toml 与目录结构

**Files:**
- Create: `D:\workproject\summary\pyproject.toml`
- Create: `D:\workproject\summary\crawlers\__init__.py`
- Create: `D:\workproject\summary\crawlers\parsers\__init__.py`

- [ ] **Step 1: 创建 pyproject.toml**

```toml
[project]
name = "quantum-news-monitor"
version = "0.1.0"
description = "量子通信信息监测平台 - 定时爬取、分类存储、报告生成"
requires-python = ">=3.12"
dependencies = [
    "flask>=3.0",
    "requests>=2.31",
    "beautifulsoup4>=4.12",
    "apscheduler>=3.10",
    "feedparser>=6.0",
    "lxml>=5.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "ruff>=0.5",
]
```

- [ ] **Step 2: 创建空 __init__.py 文件**

```bash
mkdir -p D:\workproject\summary\crawlers\parsers
type nul > D:\workproject\summary\crawlers\__init__.py
type nul > D:\workproject\summary\crawlers\parsers\__init__.py
mkdir -p D:\workproject\summary\templates
mkdir -p D:\workproject\summary\static\css
mkdir -p D:\workproject\summary\static\js
mkdir -p D:\workproject\summary\data
mkdir -p D:\workproject\summary\logs
mkdir -p D:\workproject\summary\reports
```

- [ ] **Step 3: 安装依赖**

```bash
cd D:\workproject\summary
uv sync
```

- [ ] **Step 4: 验证目录结构**

Run: `ls -R D:\workproject\summary`
Expected: 所有目录和 pyproject.toml 存在，uv.lock 已生成

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml uv.lock crawlers/ templates/ static/ data/ logs/ reports/
git commit -m "chore: initialize project skeleton with uv and pyproject.toml"
```

---

### Task 2: 数据模型 — models.py

**Files:**
- Create: `D:\workproject\summary\models.py`

- [ ] **Step 1: 编写 models.py**

```python
"""SQLite 数据库模型：建表与 CRUD 操作。"""

import sqlite3
import os
from datetime import datetime, timezone

DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
DB_PATH = os.path.join(DB_DIR, "quantum_news.db")


def _ensure_dir():
    os.makedirs(DB_DIR, exist_ok=True)


def get_connection() -> sqlite3.Connection:
    _ensure_dir()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """创建所有表并初始化默认配置。"""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            summary TEXT DEFAULT '',
            url TEXT NOT NULL UNIQUE,
            source_name TEXT NOT NULL,
            source_url TEXT DEFAULT '',
            dimension TEXT NOT NULL CHECK(dimension IN ('policy','industry','research')),
            publish_time TEXT DEFAULT '',
            crawl_time TEXT NOT NULL,
            is_valid INTEGER DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS crawl_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            start_time TEXT NOT NULL,
            end_time TEXT,
            total_sources INTEGER DEFAULT 0,
            success_count INTEGER DEFAULT 0,
            new_articles INTEGER DEFAULT 0,
            status TEXT DEFAULT 'running' CHECK(status IN ('running','completed','failed'))
        );

        CREATE INDEX IF NOT EXISTS idx_articles_dimension ON articles(dimension);
        CREATE INDEX IF NOT EXISTS idx_articles_publish_time ON articles(publish_time);
        CREATE INDEX IF NOT EXISTS idx_articles_crawl_time ON articles(crawl_time);
    """)
    # 初始化默认配置
    defaults = {
        "crawl_frequency": "daily",
        "crawl_hour": "8",
        "last_crawl_time": "",
        "auto_crawl_enabled": "true",
    }
    for k, v in defaults.items():
        conn.execute(
            "INSERT OR IGNORE INTO config (key, value) VALUES (?, ?)", (k, v)
        )
    conn.commit()
    conn.close()


# --- Articles CRUD ---

def insert_article(article: dict) -> bool:
    """插入文章，url 重复时忽略。返回 True 表示新增。"""
    conn = get_connection()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    try:
        conn.execute(
            """INSERT OR IGNORE INTO articles
               (title, summary, url, source_name, source_url, dimension, publish_time, crawl_time)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                article.get("title", ""),
                article.get("summary", ""),
                article.get("url", ""),
                article.get("source_name", ""),
                article.get("source_url", ""),
                article.get("dimension", ""),
                article.get("publish_time", ""),
                now,
            ),
        )
        inserted = conn.total_changes > 0
        conn.commit()
        return inserted
    finally:
        conn.close()


def get_articles_by_date_range(start_date: str, end_date: str) -> list[dict]:
    """按发布时间范围查询文章。"""
    conn = get_connection()
    rows = conn.execute(
        """SELECT * FROM articles
           WHERE publish_time >= ? AND publish_time <= ?
           ORDER BY dimension, publish_time DESC""",
        (start_date, end_date),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_article_counts() -> dict:
    """返回各维度文章计数。"""
    conn = get_connection()
    total = conn.execute("SELECT COUNT(*) as cnt FROM articles").fetchone()["cnt"]
    policy = conn.execute(
        "SELECT COUNT(*) as cnt FROM articles WHERE dimension='policy'"
    ).fetchone()["cnt"]
    industry = conn.execute(
        "SELECT COUNT(*) as cnt FROM articles WHERE dimension='industry'"
    ).fetchone()["cnt"]
    research = conn.execute(
        "SELECT COUNT(*) as cnt FROM articles WHERE dimension='research'"
    ).fetchone()["cnt"]
    conn.close()
    return {"total": total, "policy": policy, "industry": industry, "research": research}


# --- Config CRUD ---

def get_config(key: str) -> str | None:
    conn = get_connection()
    row = conn.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else None


def set_config(key: str, value: str):
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)", (key, value)
    )
    conn.commit()
    conn.close()


def get_all_config() -> dict:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM config").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


# --- Crawl Log CRUD ---

def start_crawl_log(total_sources: int) -> int:
    conn = get_connection()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    cur = conn.execute(
        """INSERT INTO crawl_log (start_time, total_sources, status)
           VALUES (?, ?, 'running')""",
        (now, total_sources),
    )
    conn.commit()
    log_id = cur.lastrowid
    conn.close()
    return log_id


def finish_crawl_log(log_id: int, success_count: int, new_articles: int, status: str = "completed"):
    conn = get_connection()
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    conn.execute(
        """UPDATE crawl_log SET end_time=?, success_count=?, new_articles=?, status=?
           WHERE id=?""",
        (now, success_count, new_articles, status, log_id),
    )
    conn.commit()
    conn.close()


def get_recent_crawl_logs(limit: int = 10) -> list[dict]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM crawl_log ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
```

- [ ] **Step 2: 验证数据库初始化**

```bash
cd D:\workproject\summary
uv run python -c "from models import init_db; init_db(); print('DB initialized OK')"
```
Expected: `DB initialized OK`

- [ ] **Step 3: 验证 CRUD 操作**

```bash
uv run python -c "
from models import init_db, insert_article, get_article_counts
init_db()
inserted = insert_article({
    'title': '测试文章', 'summary': '摘要', 'url': 'https://test.com/1',
    'source_name': '测试源', 'dimension': 'policy', 'publish_time': '2026-05-01'
})
print(f'Inserted: {inserted}')
print(f'Counts: {get_article_counts()}')
"
```
Expected: `Inserted: True`, Counts 中 total >= 1

- [ ] **Step 4: Commit**

```bash
git add models.py
git commit -m "feat: add SQLite data models with articles, config, and crawl_log tables"
```

---

### Task 3: HTTP 请求封装 — crawlers/fetcher.py

**Files:**
- Create: `D:\workproject\summary\crawlers\fetcher.py`

- [ ] **Step 1: 编写 fetcher.py**

```python
"""HTTP 请求封装：超时、重试、UA 伪装。"""

import time
import logging
import requests
from typing import Optional

logger = logging.getLogger("crawler.fetcher")


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]

HEADERS_TEMPLATE = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate",
}


def fetch(
    url: str,
    encoding: Optional[str] = None,
    timeout: int = 30,
    max_retries: int = 2,
    delay: float = 2.0,
) -> Optional[str]:
    """
    请求 URL 并返回文本内容。

    Args:
        url: 目标 URL
        encoding: 强制编码（如 'utf-8', 'gbk'），None 则自动检测
        timeout: 请求超时秒数
        max_retries: 最大重试次数
        delay: 重试间隔秒数

    Returns:
        成功返回页面文本，失败返回 None
    """
    import random

    for attempt in range(max_retries + 1):
        headers = {
            **HEADERS_TEMPLATE,
            "User-Agent": random.choice(USER_AGENTS),
        }
        try:
            resp = requests.get(
                url,
                headers=headers,
                timeout=timeout,
                allow_redirects=True,
            )
            resp.raise_for_status()

            if encoding:
                resp.encoding = encoding
            elif resp.apparent_encoding:
                resp.encoding = resp.apparent_encoding

            return resp.text

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching {url} (attempt {attempt + 1}/{max_retries + 1})")
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "unknown"
            logger.warning(f"HTTP {status} fetching {url} (attempt {attempt + 1}/{max_retries + 1})")
            if status == 404:
                return None  # 404 不重试
        except requests.exceptions.ConnectionError:
            logger.warning(f"Connection error fetching {url} (attempt {attempt + 1}/{max_retries + 1})")
        except Exception as e:
            logger.warning(f"Error fetching {url}: {e} (attempt {attempt + 1}/{max_retries + 1})")

        if attempt < max_retries:
            time.sleep(delay * (attempt + 1))

    logger.error(f"Failed to fetch {url} after {max_retries + 1} attempts")
    return None
```

- [ ] **Step 2: 验证 fetcher 能正常请求**

```bash
cd D:\workproject\summary
uv run python -c "
from crawlers.fetcher import fetch
html = fetch('https://httpbin.org/html', timeout=10)
assert html is not None
print(f'Fetched {len(html)} chars OK')
"
```
Expected: `Fetched ... chars OK`

- [ ] **Step 3: Commit**

```bash
git add crawlers/fetcher.py
git commit -m "feat: add HTTP fetcher with retry, timeout, and UA rotation"
```

---

### Task 4: 通用 HTML 解析器 — crawlers/parsers/base.py

**Files:**
- Create: `D:\workproject\summary\crawlers\parsers\base.py`

- [ ] **Step 1: 编写 base.py**

```python
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
```

- [ ] **Step 2: 验证解析器**

```bash
cd D:\workproject\summary
uv run python -c "
from crawlers.parsers.base import extract_links
html = '<a href=\"https://example.com/qkd\">量子密钥分发技术突破</a><a href=\"https://example.com/other\">普通新闻</a>'
results = extract_links(html, 'https://example.com/')
assert len(results) == 1
assert results[0]['title'] == '量子密钥分发技术突破'
print('Parser test OK')
"
```
Expected: `Parser test OK`

- [ ] **Step 3: Commit**

```bash
git add crawlers/parsers/base.py
git commit -m "feat: add generic HTML parser with keyword filtering"
```

---

### Task 5: RSS 解析器 — crawlers/parsers/rss_parsers.py

**Files:**
- Create: `D:\workproject\summary\crawlers\parsers\rss_parsers.py`

- [ ] **Step 1: 编写 rss_parsers.py**

```python
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
            results.append({
                "title": title,
                "url": link,
                "summary": summary,
                "source_name": source_name,
                "source_url": source_url,
                "dimension": dimension,
                "publish_time": published,
            })

    return results
```

- [ ] **Step 2: 验证 RSS 解析器**

```bash
cd D:\workproject\summary
uv run python -c "
from crawlers.parsers.rss_parsers import parse_rss
# 用 arXiv 的 RSS feed 做测试
rss_xml = '''<?xml version=\"1.0\"?>
<rss version=\"2.0\"><channel>
<item><title>Test Quantum Paper</title><link>https://arxiv.org/abs/2605.00001</link>
<description>This is a test summary about quantum communication.</description>
<pubDate>Mon, 05 May 2026 00:00:00 GMT</pubDate></item>
</channel></rss>'''
results = parse_rss(rss_xml, 'arXiv', 'https://arxiv.org/', 'research')
assert len(results) == 1
assert 'Test Quantum Paper' in results[0]['title']
print('RSS parser test OK')
"
```
Expected: `RSS parser test OK`

- [ ] **Step 3: Commit**

```bash
git add crawlers/parsers/rss_parsers.py
git commit -m "feat: add RSS/Atom feed parser for structured sources"
```

---

### Task 6: 信息源配置 — sources.json

**Files:**
- Create: `D:\workproject\summary\sources.json`

- [ ] **Step 1: 编写 sources.json**

```json
[
  {
    "name": "中华人民共和国外交部",
    "url": "https://www.mfa.gov.cn/",
    "dimension": "policy",
    "parser": "html_generic",
    "enabled": true,
    "keywords": ["量子", "量子通信", "QKD"],
    "encoding": "utf-8"
  },
  {
    "name": "国务院新闻办公室",
    "url": "http://www.scio.gov.cn/",
    "dimension": "policy",
    "parser": "html_generic",
    "enabled": true,
    "keywords": ["量子", "量子科技"],
    "encoding": "utf-8"
  },
  {
    "name": "科学技术部",
    "url": "https://www.most.gov.cn/",
    "dimension": "policy",
    "parser": "html_generic",
    "enabled": true,
    "keywords": ["量子", "量子通信", "未来产业"],
    "encoding": "utf-8"
  },
  {
    "name": "工业和信息化部",
    "url": "https://www.miit.gov.cn/",
    "dimension": "policy",
    "parser": "html_generic",
    "enabled": true,
    "keywords": ["量子通信", "量子安全", "量子产业"],
    "encoding": "utf-8"
  },
  {
    "name": "安徽省人民政府",
    "url": "https://www.ah.gov.cn/",
    "dimension": "policy",
    "parser": "html_generic",
    "enabled": true,
    "keywords": ["量子", "量子产业", "量子通信", "量子信息"],
    "encoding": "utf-8"
  },
  {
    "name": "新华网（政策）",
    "url": "http://politics.news.cn/",
    "dimension": "policy",
    "parser": "html_generic",
    "enabled": true,
    "keywords": ["量子", "量子科技", "量子通信"],
    "encoding": "utf-8"
  },
  {
    "name": "合肥日报",
    "url": "https://newspaper.hf365.com/hfrb/",
    "dimension": "policy",
    "parser": "html_generic",
    "enabled": true,
    "keywords": ["量子", "量子产业", "量子政策"],
    "encoding": "utf-8"
  },
  {
    "name": "欧盟量子旗舰计划",
    "url": "https://quantum-flagship.eu/",
    "dimension": "policy",
    "parser": "html_generic",
    "enabled": true,
    "keywords": ["quantum", "QKD", "quantum communication"],
    "encoding": "utf-8"
  },
  {
    "name": "科技日报",
    "url": "https://www.stdaily.com.cn/",
    "dimension": "industry",
    "parser": "html_generic",
    "enabled": true,
    "keywords": ["量子", "量子通信", "量子产业", "量子计算"],
    "encoding": "utf-8"
  },
  {
    "name": "中国电子报",
    "url": "https://www.cena.com.cn/",
    "dimension": "industry",
    "parser": "html_generic",
    "enabled": true,
    "keywords": ["量子", "量子安全", "量子通信"],
    "encoding": "utf-8"
  },
  {
    "name": "通信信息报（C114）",
    "url": "https://www.c114.com/",
    "dimension": "industry",
    "parser": "html_generic",
    "enabled": true,
    "keywords": ["量子", "量子通信", "量子城域网", "量子密信"],
    "encoding": "utf-8"
  },
  {
    "name": "安徽发布",
    "url": "https://www.ah.gov.cn/ahfb/",
    "dimension": "industry",
    "parser": "html_generic",
    "enabled": true,
    "keywords": ["量子", "量子产业", "量子大会"],
    "encoding": "utf-8"
  },
  {
    "name": "量子位（QbitAI）",
    "url": "https://www.qbitai.com/",
    "dimension": "industry",
    "parser": "html_generic",
    "enabled": true,
    "keywords": ["量子", "量子通信", "量子计算", "融资"],
    "encoding": "utf-8"
  },
  {
    "name": "中新网",
    "url": "https://www.chinanews.com/",
    "dimension": "industry",
    "parser": "html_generic",
    "enabled": true,
    "keywords": ["量子", "量子通信", "量子科技"],
    "encoding": "utf-8"
  },
  {
    "name": "人民网",
    "url": "https://www.people.com.cn/",
    "dimension": "industry",
    "parser": "html_generic",
    "enabled": true,
    "keywords": ["量子", "量子通信", "量子科技"],
    "encoding": "utf-8"
  },
  {
    "name": "The Quantum Insider",
    "url": "https://thequantuminsider.com/",
    "dimension": "industry",
    "parser": "html_generic",
    "enabled": true,
    "keywords": ["quantum", "QKD", "quantum communication", "quantum network"],
    "encoding": "utf-8"
  },
  {
    "name": "Quantum Daily",
    "url": "https://quantumdaily.com/",
    "dimension": "industry",
    "parser": "html_generic",
    "enabled": true,
    "keywords": ["quantum", "QKD", "quantum communication"],
    "encoding": "utf-8"
  },
  {
    "name": "中国科学院",
    "url": "https://www.cas.cn/",
    "dimension": "research",
    "parser": "html_generic",
    "enabled": true,
    "keywords": ["量子", "量子通信", "量子计算", "量子信息"],
    "encoding": "utf-8"
  },
  {
    "name": "中科院量子信息与量子科技创新研究院",
    "url": "http://www.qiis.ac.cn/",
    "dimension": "research",
    "parser": "html_generic",
    "enabled": true,
    "keywords": ["量子", "量子通信", "量子计算", "量子模拟"],
    "encoding": "utf-8"
  },
  {
    "name": "中国科学技术大学",
    "url": "https://www.ustc.edu.cn/",
    "dimension": "research",
    "parser": "html_generic",
    "enabled": true,
    "keywords": ["量子", "量子通信", "量子信息", "潘建伟"],
    "encoding": "utf-8"
  },
  {
    "name": "Nature News",
    "url": "https://www.nature.com/news",
    "dimension": "research",
    "parser": "rss",
    "enabled": true,
    "keywords": ["quantum", "physics"],
    "encoding": "utf-8",
    "rss_url": "https://www.nature.com/nature.rss"
  },
  {
    "name": "Science News",
    "url": "https://www.science.org/news",
    "dimension": "research",
    "parser": "rss",
    "enabled": true,
    "keywords": ["quantum", "physics"],
    "encoding": "utf-8",
    "rss_url": "https://www.science.org/rss/news_current.xml"
  },
  {
    "name": "arXiv (quant-ph)",
    "url": "https://arxiv.org/",
    "dimension": "research",
    "parser": "rss",
    "enabled": true,
    "keywords": ["quantum"],
    "encoding": "utf-8",
    "rss_url": "https://rss.arxiv.org/rss/quant-ph"
  },
  {
    "name": "New Scientist",
    "url": "https://www.newscientist.com/",
    "dimension": "research",
    "parser": "html_generic",
    "enabled": true,
    "keywords": ["quantum", "quantum communication", "QKD", "entanglement"],
    "encoding": "utf-8"
  },
  {
    "name": "美国参议院官网",
    "url": "https://www.senate.gov/",
    "dimension": "policy",
    "parser": "html_generic",
    "enabled": true,
    "keywords": ["quantum", "quantum computing", "quantum information"],
    "encoding": "utf-8"
  }
]
```

- [ ] **Step 2: 验证 JSON 格式正确**

```bash
cd D:\workproject\summary
uv run python -c "import json; data=json.load(open('sources.json','r',encoding='utf-8')); print(f'{len(data)} sources loaded OK')"
```
Expected: `25 sources loaded OK`

- [ ] **Step 3: Commit**

```bash
git add sources.json
git commit -m "feat: add 25 information sources across policy/industry/research dimensions"
```

---

### Task 7: 爬虫引擎 — crawlers/engine.py

**Files:**
- Create: `D:\workproject\summary\crawlers\engine.py`

- [ ] **Step 1: 编写 engine.py**

```python
"""爬虫引擎：加载信息源、调度抓取、解析入库。"""

import json
import time
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from crawlers.fetcher import fetch
from crawlers.parsers.base import extract_links
from crawlers.parsers.rss_parsers import parse_rss

logger = logging.getLogger("crawler.engine")

SOURCES_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "sources.json")


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
    keywords = source.get("keywords")
    encoding = source.get("encoding")
    parser_type = source.get("parser", "html_generic")

    if parser_type == "rss":
        # RSS 源：直接传入 url（feedparser 可处理 URL 或 XML 字符串）
        try:
            results = parse_rss(url, name, source["url"], dimension)
        except Exception as e:
            logger.error(f"RSS parse error for {name}: {e}")
            return []
    else:
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
            results.append({
                "title": link["title"],
                "url": link["url"],
                "summary": link.get("summary", ""),
                "source_name": name,
                "source_url": source["url"],
                "dimension": dimension,
                "publish_time": "",  # 通用解析器无法可靠提取时间
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
            else:
                logger.info(f"  {name}: 0 articles")
            
            success_count += 1
            
        except Exception as e:
            logger.error(f"  {name}: ERROR - {e}")
        
        # 间隔避免被封
        if i < total - 1:
            time.sleep(2)
    
    # 更新状态
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
    set_config("last_crawl_time", now)
    
    status = "completed" if success_count > 0 else "failed"
    finish_crawl_log(log_id, success_count, new_articles, status)
    
    logger.info(f"Crawl complete: {success_count}/{total} sources OK, {new_articles} new articles")
    
    return {
        "success": success_count,
        "failed": total - success_count,
        "new_articles": new_articles,
        "total_sources": total,
    }
```

- [ ] **Step 2: 初始化日志配置**

在 `app.py` 创建前先不用验证完整流程。我们先确保模块可导入：

```bash
cd D:\workproject\summary
uv run python -c "
from crawlers.engine import load_sources, crawl_source
sources = load_sources()
print(f'{len(sources)} enabled sources')
# 测试解析一个源（不实际请求）
src = {'name': 'test', 'url': 'https://example.com', 'dimension': 'research', 'parser': 'html_generic', 'keywords': ['test']}
"
```
Expected: 至少输出已启用的源数量

- [ ] **Step 3: Commit**

```bash
git add crawlers/engine.py
git commit -m "feat: add crawl engine with source iteration, dedup, and progress tracking"
```

---

### Task 8: Flask 应用入口 — app.py

**Files:**
- Create: `D:\workproject\summary\app.py`

- [ ] **Step 1: 编写 app.py**

```python
"""Flask 应用入口：路由、API、调度器启动。"""

import os
import logging
import threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory

from models import init_db, get_article_counts, get_recent_crawl_logs, get_all_config, set_config
from crawlers.engine import crawl_all
from scheduler import init_scheduler
from reporter import generate_report, list_reports

# --- 应用工厂 ---

def create_app() -> Flask:
    app = Flask(__name__)

    # 日志配置
    log_dir = os.path.join(os.path.dirname(__file__), "logs")
    os.makedirs(log_dir, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(os.path.join(log_dir, "crawler.log"), encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )

    # 初始化数据库
    init_db()

    # 初始化调度器
    init_scheduler(app)

    # --- 页面路由 ---

    @app.route("/")
    def dashboard():
        counts = get_article_counts()
        logs = get_recent_crawl_logs(10)
        config = get_all_config()
        return render_template(
            "dashboard.html",
            counts=counts,
            logs=logs,
            last_crawl=config.get("last_crawl_time", "尚未爬取"),
        )

    @app.route("/crawl")
    def crawl_page():
        import json
        sources_path = os.path.join(os.path.dirname(__file__), "sources.json")
        with open(sources_path, "r", encoding="utf-8") as f:
            sources = json.load(f)
        return render_template("crawl.html", sources=sources)

    @app.route("/settings")
    def settings_page():
        config = get_all_config()
        return render_template("settings.html", config=config)

    # --- 报告文件访问 ---

    @app.route("/reports/<path:filename>")
    def serve_report(filename):
        reports_dir = os.path.join(os.path.dirname(__file__), "reports")
        return send_from_directory(reports_dir, filename)

    # --- API 路由 ---

    @app.route("/api/crawl/trigger", methods=["POST"])
    def api_crawl_trigger():
        """手动触发爬取（在后台线程执行）。"""
        def _run():
            crawl_all()
        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return jsonify({"status": "started", "message": "爬取任务已启动"})

    @app.route("/api/crawl/status")
    def api_crawl_status():
        config = get_all_config()
        logs = get_recent_crawl_logs(1)
        latest = logs[0] if logs else None
        return jsonify({
            "last_crawl_time": config.get("last_crawl_time", ""),
            "latest_log": latest,
        })

    @app.route("/api/schedule", methods=["GET"])
    def api_get_schedule():
        config = get_all_config()
        return jsonify({
            "frequency": config.get("crawl_frequency", "daily"),
            "hour": config.get("crawl_hour", "8"),
            "auto_crawl_enabled": config.get("auto_crawl_enabled", "true"),
        })

    @app.route("/api/schedule", methods=["PUT"])
    def api_update_schedule():
        data = request.get_json()
        from scheduler import update_schedule
        update_schedule(app, data)
        return jsonify({"status": "ok"})

    @app.route("/api/report/generate", methods=["POST"])
    def api_generate_report():
        data = request.get_json()
        start_date = data.get("start_date", "")
        end_date = data.get("end_date", "")
        if not start_date or not end_date:
            return jsonify({"error": "请提供开始和结束日期"}), 400
        try:
            filename = generate_report(start_date, end_date)
            return jsonify({"status": "ok", "filename": filename})
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/report/list")
    def api_list_reports():
        return jsonify({"reports": list_reports()})

    @app.route("/api/stats")
    def api_stats():
        counts = get_article_counts()
        return jsonify(counts)

    return app


# --- 启动入口 ---

if __name__ == "__main__":
    app = create_app()
    print("\n" + "=" * 50)
    print("  量子通信信息监测平台")
    print("  访问地址: http://127.0.0.1:5000")
    print("=" * 50 + "\n")
    app.run(host="127.0.0.1", port=5000, debug=True)
```

- [ ] **Step 2: 验证应用可启动（模板尚未创建，预期报模板找不到错误）**

```bash
cd D:\workproject\summary
timeout 3 uv run python app.py 2>&1 || true
```
Expected: 报 `TemplateNotFound` 错误（正常，因为模板还没创建）

- [ ] **Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add Flask app entry point with routes, APIs, and scheduler init"
```

---

### Task 9: 调度模块 — scheduler.py

**Files:**
- Create: `D:\workproject\summary\scheduler.py`

- [ ] **Step 1: 编写 scheduler.py**

```python
"""APScheduler 调度管理：Job 创建、更新、暂停。"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from models import get_config, set_config

logger = logging.getLogger("scheduler")

_scheduler: BackgroundScheduler | None = None


def _crawl_job():
    """调度器触发的爬取任务。"""
    from crawlers.engine import crawl_all
    logger.info("Scheduled crawl triggered")
    try:
        result = crawl_all()
        logger.info(f"Scheduled crawl done: {result}")
    except Exception as e:
        logger.error(f"Scheduled crawl failed: {e}")


def init_scheduler(app):
    """初始化调度器，从 config 读取频率并注册 Job。"""
    global _scheduler
    
    _scheduler = BackgroundScheduler(daemon=True)
    
    freq = get_config("crawl_frequency") or "daily"
    hour = int(get_config("crawl_hour") or "8")
    enabled = get_config("auto_crawl_enabled") or "true"
    
    if enabled == "true" and freq != "manual":
        _add_job(freq, hour)
    
    _scheduler.start()
    logger.info(f"Scheduler started (frequency={freq}, hour={hour}, enabled={enabled})")


def _add_job(frequency: str, hour: int):
    """根据频率添加 Job。"""
    global _scheduler
    
    # 先移除旧 Job
    try:
        _scheduler.remove_job("crawl_job")
    except Exception:
        pass
    
    if frequency == "daily":
        _scheduler.add_job(
            _crawl_job,
            "cron",
            hour=hour,
            minute=0,
            id="crawl_job",
            max_instances=1,
            replace_existing=True,
        )
        logger.info(f"Job added: daily at {hour}:00")
        
    elif frequency == "6h":
        _scheduler.add_job(
            _crawl_job,
            "interval",
            hours=6,
            id="crawl_job",
            max_instances=1,
            replace_existing=True,
        )
        logger.info("Job added: every 6 hours")
        
    elif frequency == "12h":
        _scheduler.add_job(
            _crawl_job,
            "interval",
            hours=12,
            id="crawl_job",
            max_instances=1,
            replace_existing=True,
        )
        logger.info("Job added: every 12 hours")


def update_schedule(app, data: dict):
    """更新调度配置并重建 Job。"""
    frequency = data.get("frequency")
    hour = data.get("hour")
    enabled = data.get("auto_crawl_enabled")
    
    if frequency:
        set_config("crawl_frequency", frequency)
    if hour is not None:
        set_config("crawl_hour", str(hour))
    if enabled is not None:
        set_config("auto_crawl_enabled", str(enabled).lower())
    
    # 重新读取配置
    freq = frequency or get_config("crawl_frequency")
    hr = int(hour) if hour is not None else int(get_config("crawl_hour") or "8")
    enb = enabled if enabled is not None else (get_config("auto_crawl_enabled") == "true")
    
    if enb and freq != "manual":
        _add_job(freq, hr)
    else:
        try:
            _scheduler.remove_job("crawl_job")
            logger.info("Crawl job removed (paused/manual)")
        except Exception:
            pass
    
    logger.info(f"Schedule updated: freq={freq}, hour={hr}, enabled={enb}")
```

- [ ] **Step 2: 验证调度器可初始化**

```bash
cd D:\workproject\summary
uv run python -c "
from models import init_db; init_db()
from scheduler import init_scheduler
# 不能直接传 app，这里只测导入和基本逻辑
print('scheduler module OK')
"
```
Expected: `scheduler module OK`

- [ ] **Step 3: Commit**

```bash
git add scheduler.py
git commit -m "feat: add APScheduler integration with dynamic frequency control"
```

---

### Task 10: 报告生成 — reporter.py

**Files:**
- Create: `D:\workproject\summary\reporter.py`

- [ ] **Step 1: 编写 reporter.py**

```python
"""报告生成：数据聚合 + Jinja2 渲染 + ECharts 配置注入。"""

import os
import json
from datetime import datetime
from collections import defaultdict, Counter
from flask import render_template

from models import get_articles_by_date_range

REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")


def _ensure_reports_dir():
    os.makedirs(REPORTS_DIR, exist_ok=True)


def _build_chart_data(articles: list[dict], start_date: str, end_date: str) -> dict:
    """根据文章列表构建 ECharts 所需的结构化数据。"""
    
    # 1. 每日信息量（折线图）
    from datetime import timedelta
    daily_counts = defaultdict(lambda: {"policy": 0, "industry": 0, "research": 0})
    
    for a in articles:
        pt = a.get("publish_time", "")[:10]  # 取 YYYY-MM-DD
        if pt:
            daily_counts[pt][a.get("dimension", "research")] += 1
    
    # 补全日期范围内的所有天
    sd = datetime.strptime(start_date, "%Y-%m-%d")
    ed = datetime.strptime(end_date, "%Y-%m-%d")
    all_dates = []
    policy_series = []
    industry_series = []
    research_series = []
    
    d = sd
    while d <= ed:
        ds = d.strftime("%Y-%m-%d")
        all_dates.append(ds)
        policy_series.append(daily_counts[ds]["policy"])
        industry_series.append(daily_counts[ds]["industry"])
        research_series.append(daily_counts[ds]["research"])
        d += timedelta(days=1)
    
    # 2. 维度分布（环形图）
    dim_counts = Counter(a.get("dimension") for a in articles)
    
    # 3. 来源 Top10（横向柱状图）
    source_counts = Counter(a.get("source_name") for a in articles)
    top_sources = source_counts.most_common(10)
    
    return {
        "line_dates": json.dumps(all_dates, ensure_ascii=False),
        "line_policy": json.dumps(policy_series),
        "line_industry": json.dumps(industry_series),
        "line_research": json.dumps(research_series),
        "pie_data": json.dumps([
            {"name": "政策动态", "value": dim_counts.get("policy", 0)},
            {"name": "产业进展", "value": dim_counts.get("industry", 0)},
            {"name": "科研成果", "value": dim_counts.get("research", 0)},
        ], ensure_ascii=False),
        "bar_sources": json.dumps([s[0] for s in reversed(top_sources)], ensure_ascii=False),
        "bar_counts": json.dumps([s[1] for s in reversed(top_sources)]),
    }


def generate_report(start_date: str, end_date: str) -> str:
    """
    生成 HTML 报告并保存到文件。

    Args:
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)

    Returns:
        报告文件名
    """
    _ensure_reports_dir()
    
    articles = get_articles_by_date_range(start_date, end_date)
    
    # 按维度分组
    policy_articles = [a for a in articles if a["dimension"] == "policy"]
    industry_articles = [a for a in articles if a["dimension"] == "industry"]
    research_articles = [a for a in articles if a["dimension"] == "research"]
    
    chart_data = _build_chart_data(articles, start_date, end_date)
    
    # 收集涉及的信息源
    sources_set = set()
    for a in articles:
        if a.get("source_name"):
            sources_set.add(a["source_name"])
    
    html = render_template(
        "report.html",
        start_date=start_date,
        end_date=end_date,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        total=len(articles),
        policy_count=len(policy_articles),
        industry_count=len(industry_articles),
        research_count=len(research_articles),
        policy_articles=policy_articles,
        industry_articles=industry_articles,
        research_articles=research_articles,
        sources=sorted(sources_set),
        **chart_data,
    )
    
    filename = f"{start_date}_{end_date}.html"
    filepath = os.path.join(REPORTS_DIR, filename)
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    
    return filename


def list_reports() -> list[dict]:
    """列出已生成的报告文件。"""
    _ensure_reports_dir()
    reports = []
    for f in os.listdir(REPORTS_DIR):
        if f.endswith(".html"):
            fpath = os.path.join(REPORTS_DIR, f)
            mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
            reports.append({
                "filename": f,
                "created": mtime.strftime("%Y-%m-%d %H:%M"),
                "size": os.path.getsize(fpath),
            })
    reports.sort(key=lambda r: r["created"], reverse=True)
    return reports
```

- [ ] **Step 2: 验证模块可导入**

```bash
cd D:\workproject\summary
uv run python -c "
from reporter import list_reports
print(f'Module OK, reports: {list_reports()}')
"
```
Expected: `Module OK, reports: []`

- [ ] **Step 3: Commit**

```bash
git add reporter.py
git commit -m "feat: add report generation with data aggregation and chart configuration"
```

---

### Task 11: 前端基础模板 — templates/base.html

**Files:**
- Create: `D:\workproject\summary\templates\base.html`

- [ ] **Step 1: 编写 base.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}量子通信信息监测平台{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    {% block head_extra %}{% endblock %}
</head>
<body>
    <nav class="top-nav">
        <div class="nav-inner">
            <a href="/" class="nav-brand">🔬 量子通信信息监测平台</a>
            <div class="nav-links">
                <a href="/crawl" class="nav-link {% if request.path == '/crawl' %}active{% endif %}">爬取管理</a>
                <a href="/settings" class="nav-link {% if request.path == '/settings' %}active{% endif %}">设置</a>
            </div>
        </div>
    </nav>

    <main class="main-content">
        {% block content %}{% endblock %}
    </main>

    <div id="toast" class="toast" style="display:none;"></div>
    
    {% block scripts %}{% endblock %}
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add templates/base.html
git commit -m "feat: add base HTML template with navigation layout"
```

---

### Task 12: 全局样式 — static/css/style.css

**Files:**
- Create: `D:\workproject\summary\static\css\style.css`

- [ ] **Step 1: 编写 style.css**

```css
/* === Reset & Base === */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
    --primary: #2563eb;
    --primary-hover: #1d4ed8;
    --success: #16a34a;
    --warning: #f59e0b;
    --danger: #dc2626;
    --bg: #f8fafc;
    --card-bg: #ffffff;
    --text: #1e293b;
    --text-secondary: #64748b;
    --border: #e2e8f0;
    --radius: 10px;
    --shadow: 0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06);
}

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
    font-size: 16px;
    line-height: 1.6;
    color: var(--text);
    background: var(--bg);
    min-height: 100vh;
}

/* === Navigation === */
.top-nav {
    background: var(--card-bg);
    border-bottom: 1px solid var(--border);
    padding: 0 24px;
    position: sticky; top: 0; z-index: 100;
    box-shadow: var(--shadow);
}
.nav-inner {
    max-width: 1200px; margin: 0 auto;
    display: flex; align-items: center; justify-content: space-between;
    height: 56px;
}
.nav-brand {
    font-size: 20px; font-weight: 700; color: var(--text);
    text-decoration: none;
}
.nav-links { display: flex; gap: 8px; }
.nav-link {
    padding: 6px 16px; border-radius: 6px;
    text-decoration: none; color: var(--text-secondary);
    font-size: 15px; transition: all 0.2s;
}
.nav-link:hover { background: var(--bg); color: var(--text); }
.nav-link.active { background: var(--primary); color: #fff; }

/* === Main Content === */
.main-content {
    max-width: 1200px; margin: 24px auto; padding: 0 24px;
}

/* === Cards === */
.card {
    background: var(--card-bg); border-radius: var(--radius);
    padding: 24px; margin-bottom: 20px;
    box-shadow: var(--shadow); border: 1px solid var(--border);
}
.card-title {
    font-size: 18px; font-weight: 600; margin-bottom: 16px;
    color: var(--text);
}

/* === Stat Cards Row === */
.stats-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px; margin-bottom: 20px;
}
.stat-card {
    background: var(--card-bg); border-radius: var(--radius);
    padding: 20px; text-align: center;
    box-shadow: var(--shadow); border: 1px solid var(--border);
}
.stat-number { font-size: 36px; font-weight: 700; color: var(--primary); }
.stat-label { font-size: 14px; color: var(--text-secondary); margin-top: 4px; }
.stat-card.dim-policy .stat-number { color: #dc2626; }
.stat-card.dim-industry .stat-number { color: #2563eb; }
.stat-card.dim-research .stat-number { color: #16a34a; }

/* === Buttons === */
.btn {
    display: inline-block; padding: 10px 20px; border-radius: 8px;
    font-size: 15px; font-weight: 500; border: none; cursor: pointer;
    transition: all 0.2s; text-decoration: none; line-height: 1.5;
}
.btn-primary { background: var(--primary); color: #fff; }
.btn-primary:hover { background: var(--primary-hover); }
.btn-secondary { background: var(--bg); color: var(--text); border: 1px solid var(--border); }
.btn-secondary:hover { background: var(--border); }
.btn-danger { background: var(--danger); color: #fff; }
.btn-danger:hover { opacity: 0.9; }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }

/* === Forms === */
.form-group { margin-bottom: 16px; }
.form-label { display: block; font-weight: 500; margin-bottom: 6px; font-size: 15px; }
.form-input, .form-select {
    width: 100%; padding: 10px 14px; border: 1px solid var(--border);
    border-radius: 8px; font-size: 15px; font-family: inherit;
    background: var(--card-bg); color: var(--text);
    transition: border-color 0.2s;
}
.form-input:focus, .form-select:focus {
    outline: none; border-color: var(--primary);
    box-shadow: 0 0 0 3px rgba(37,99,235,0.1);
}
.form-row { display: flex; gap: 16px; align-items: end; }

/* === Tables === */
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; }
th, td { padding: 12px 16px; text-align: left; border-bottom: 1px solid var(--border); }
th { font-weight: 600; font-size: 14px; color: var(--text-secondary); background: var(--bg); }
td { font-size: 15px; }

/* === Toggle Switch === */
.toggle { position: relative; display: inline-block; width: 48px; height: 26px; }
.toggle input { opacity: 0; width: 0; height: 0; }
.toggle-slider {
    position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0;
    background: #cbd5e1; border-radius: 26px; transition: 0.3s;
}
.toggle-slider::before {
    content: ""; position: absolute; height: 20px; width: 20px;
    left: 3px; bottom: 3px; background: white; border-radius: 50%; transition: 0.3s;
}
.toggle input:checked + .toggle-slider { background: var(--success); }
.toggle input:checked + .toggle-slider::before { transform: translateX(22px); }

/* === Tags === */
.tag {
    display: inline-block; padding: 2px 10px; border-radius: 12px;
    font-size: 13px; font-weight: 500;
}
.tag-policy { background: #fee2e2; color: #dc2626; }
.tag-industry { background: #dbeafe; color: #2563eb; }
.tag-research { background: #dcfce7; color: #16a34a; }

/* === Toast === */
.toast {
    position: fixed; bottom: 24px; right: 24px;
    padding: 12px 24px; border-radius: 8px; color: #fff;
    font-size: 15px; z-index: 999;
    box-shadow: 0 4px 12px rgba(0,0,0,0.2);
}
.toast.success { background: var(--success); }
.toast.error { background: var(--danger); }
.toast.info { background: var(--primary); }

/* === Log List === */
.log-list { list-style: none; }
.log-item {
    padding: 10px 0; border-bottom: 1px solid var(--border);
    font-size: 14px; color: var(--text-secondary);
}
.log-item:last-child { border-bottom: none; }
.log-item .log-time { font-weight: 500; color: var(--text); margin-right: 12px; }
.log-item .log-status { font-weight: 600; }
.log-item .log-status.completed { color: var(--success); }
.log-item .log-status.running { color: var(--warning); }
.log-item .log-status.failed { color: var(--danger); }

/* === Responsive === */
@media (max-width: 900px) {
    .stats-row { grid-template-columns: repeat(2, 1fr); }
    .form-row { flex-direction: column; }
}
@media (max-width: 600px) {
    .stats-row { grid-template-columns: 1fr; }
    .nav-brand { font-size: 16px; }
    .main-content { padding: 0 12px; }
}

/* === Print (for reports) === */
@media print {
    .top-nav, .btn, #toast { display: none; }
    .main-content { max-width: none; margin: 0; padding: 0; }
    .card { box-shadow: none; border: none; break-inside: avoid; }
    body { background: #fff; }
}
```

- [ ] **Step 2: Commit**

```bash
git add static/css/style.css
git commit -m "feat: add global stylesheet with card layout, nav, and responsive design"
```

---

### Task 13: 仪表盘页面 — templates/dashboard.html

**Files:**
- Create: `D:\workproject\summary\templates\dashboard.html`
- Create: `D:\workproject\summary\static\js\app.js`

- [ ] **Step 1: 编写 dashboard.html**

```html
{% extends "base.html" %}
{% block title %}仪表盘 - 量子通信信息监测平台{% endblock %}

{% block content %}
<!-- Stats Row -->
<div class="stats-row">
    <div class="stat-card">
        <div class="stat-number">{{ counts.total }}</div>
        <div class="stat-label">总信息量</div>
    </div>
    <div class="stat-card dim-policy">
        <div class="stat-number">{{ counts.policy }}</div>
        <div class="stat-label">📋 政策动态</div>
    </div>
    <div class="stat-card dim-industry">
        <div class="stat-number">{{ counts.industry }}</div>
        <div class="stat-label">🏭 产业进展</div>
    </div>
    <div class="stat-card dim-research">
        <div class="stat-number">{{ counts.research }}</div>
        <div class="stat-label">🔬 科研成果</div>
    </div>
</div>

<!-- Crawl Trigger -->
<div class="card" style="display:flex;align-items:center;justify-content:space-between;">
    <div>
        <span style="font-weight:600;">爬取控制</span>
        <span style="color:var(--text-secondary);margin-left:12px;font-size:14px;" id="last-crawl-info">
            上次爬取：{{ last_crawl if last_crawl != '尚未爬取' else last_crawl else '尚未爬取' }}
        </span>
    </div>
    <button class="btn btn-primary" id="btn-crawl" onclick="triggerCrawl()">立即爬取</button>
</div>

<!-- Report Generator -->
<div class="card">
    <div class="card-title">📄 生成报告</div>
    <div class="form-row">
        <div class="form-group" style="flex:1;">
            <label class="form-label">开始日期</label>
            <input type="date" class="form-input" id="report-start">
        </div>
        <div class="form-group" style="flex:1;">
            <label class="form-label">结束日期</label>
            <input type="date" class="form-input" id="report-end">
        </div>
        <div class="form-group">
            <button class="btn btn-primary" onclick="generateReport()">生成报告</button>
            <button class="btn btn-secondary" onclick="listReports()" style="margin-left:8px;">预览最近报告</button>
        </div>
    </div>
</div>

<!-- Recent Logs -->
<div class="card">
    <div class="card-title">📝 最近爬取日志</div>
    {% if logs %}
    <ul class="log-list">
    {% for log in logs %}
    <li class="log-item">
        <span class="log-time">{{ log.start_time[:16] }}</span>
        <span class="log-status {{ log.status }}">{{ log.status }}</span>
        <span>新增 {{ log.new_articles }} 条 · 成功 {{ log.success_count }}/{{ log.total_sources }} 源</span>
    </li>
    {% endfor %}
    </ul>
    {% else %}
    <p style="color:var(--text-secondary);">暂无爬取记录</p>
    {% endif %}
</div>
{% endblock %}

{% block scripts %}
<script src="{{ url_for('static', filename='js/app.js') }}"></script>
{% endblock %}
```

- [ ] **Step 2: 编写 app.js**

```javascript
/* 量子通信信息监测平台 - 前端交互 */

// Toast 通知
function showToast(msg, type = 'info') {
    const toast = document.getElementById('toast');
    toast.textContent = msg;
    toast.className = 'toast ' + type;
    toast.style.display = 'block';
    setTimeout(() => { toast.style.display = 'none'; }, 3000);
}

// 触发爬取
async function triggerCrawl() {
    const btn = document.getElementById('btn-crawl');
    btn.disabled = true;
    btn.textContent = '爬取中...';
    
    try {
        const resp = await fetch('/api/crawl/trigger', { method: 'POST' });
        const data = await resp.json();
        showToast(data.message || '爬取任务已启动', 'success');
        
        // 轮询状态
        pollCrawlStatus();
    } catch (e) {
        showToast('启动爬取失败: ' + e.message, 'error');
        btn.disabled = false;
        btn.textContent = '立即爬取';
    }
}

// 轮询爬取状态
let pollTimer = null;
async function pollCrawlStatus() {
    const btn = document.getElementById('btn-crawl');
    let attempts = 0;
    const maxAttempts = 60; // 最多轮询 5 分钟
    
    if (pollTimer) clearInterval(pollTimer);
    
    pollTimer = setInterval(async () => {
        attempts++;
        try {
            const resp = await fetch('/api/crawl/status');
            const data = await resp.json();
            const log = data.latest_log;
            
            if (log && log.status !== 'running') {
                clearInterval(pollTimer);
                btn.disabled = false;
                btn.textContent = '立即爬取';
                showToast(`爬取完成：新增 ${log.new_articles} 条`, 'success');
                // 刷新页面更新数据
                setTimeout(() => location.reload(), 1500);
            } else if (attempts >= maxAttempts) {
                clearInterval(pollTimer);
                btn.disabled = false;
                btn.textContent = '立即爬取';
                showToast('爬取超时，请稍后刷新查看', 'warning');
            } else {
                btn.textContent = `爬取中 (${attempts * 5}s)...`;
            }
        } catch (e) {
            clearInterval(pollTimer);
            btn.disabled = false;
            btn.textContent = '立即爬取';
        }
    }, 5000);
}

// 生成报告
async function generateReport() {
    const start = document.getElementById('report-start').value;
    const end = document.getElementById('report-end').value;
    
    if (!start || !end) {
        showToast('请选择开始和结束日期', 'warning');
        return;
    }
    
    try {
        const resp = await fetch('/api/report/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ start_date: start, end_date: end })
        });
        const data = await resp.json();
        
        if (data.error) {
            showToast(data.error, 'error');
            return;
        }
        
        showToast('报告已生成', 'success');
        window.open('/reports/' + data.filename, '_blank');
    } catch (e) {
        showToast('生成报告失败: ' + e.message, 'error');
    }
}

// 列出报告
async function listReports() {
    const resp = await fetch('/api/report/list');
    const data = await resp.json();
    
    if (data.reports.length === 0) {
        showToast('暂无已生成的报告', 'info');
        return;
    }
    
    // 打开最新报告
    window.open('/reports/' + data.reports[0].filename, '_blank');
}

// 设置默认日期（最近 7 天）
(function() {
    const today = new Date();
    const weekAgo = new Date(today);
    weekAgo.setDate(today.getDate() - 7);
    
    document.getElementById('report-start').value = weekAgo.toISOString().split('T')[0];
    document.getElementById('report-end').value = today.toISOString().split('T')[0];
})();
```

- [ ] **Step 3: 验证应用可启动并渲染仪表盘**

```bash
cd D:\workproject\summary
start /B uv run python app.py
timeout 3
curl -s http://127.0.0.1:5000/ | head -20
```
Expected: 返回 HTML 内容包含 "量子通信信息监测平台"

- [ ] **Step 4: Commit**

```bash
git add templates/dashboard.html static/js/app.js
git commit -m "feat: add dashboard with stats cards, crawl trigger, and report generator"
```

---

### Task 14: 爬取管理页面 — templates/crawl.html

**Files:**
- Create: `D:\workproject\summary\templates\crawl.html`

- [ ] **Step 1: 编写 crawl.html**

```html
{% extends "base.html" %}
{% block title %}爬取管理 - 量子通信信息监测平台{% endblock %}

{% block content %}
<div class="card">
    <div class="card-title" style="display:flex;justify-content:space-between;align-items:center;">
        <span>📡 信息源管理</span>
        <div style="display:flex;gap:8px;">
            <select class="form-select" id="filter-dimension" onchange="filterSources()" style="width:auto;">
                <option value="all">全部维度</option>
                <option value="policy">政策动态</option>
                <option value="industry">产业进展</option>
                <option value="research">科研成果</option>
            </select>
            <select class="form-select" id="filter-status" onchange="filterSources()" style="width:auto;">
                <option value="all">全部状态</option>
                <option value="enabled">已启用</option>
                <option value="disabled">已禁用</option>
            </select>
        </div>
    </div>
    
    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>信息源</th>
                    <th>维度</th>
                    <th>URL</th>
                    <th>解析类型</th>
                    <th>状态</th>
                </tr>
            </thead>
            <tbody id="sources-tbody">
                {% for src in sources %}
                <tr data-dimension="{{ src.dimension }}" data-enabled="{{ src.enabled|lower }}">
                    <td><strong>{{ src.name }}</strong></td>
                    <td>
                        {% if src.dimension == 'policy' %}
                        <span class="tag tag-policy">政策</span>
                        {% elif src.dimension == 'industry' %}
                        <span class="tag tag-industry">产业</span>
                        {% else %}
                        <span class="tag tag-research">科研</span>
                        {% endif %}
                    </td>
                    <td style="max-width:300px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">
                        <a href="{{ src.url }}" target="_blank" style="color:var(--text-secondary);">{{ src.url }}</a>
                    </td>
                    <td style="color:var(--text-secondary);">
                        {{ src.parser }}{% if src.rss_url %} (RSS){% endif %}
                    </td>
                    <td>
                        <label class="toggle">
                            <input type="checkbox" {% if src.enabled %}checked{% endif %} disabled>
                            <span class="toggle-slider"></span>
                        </label>
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
function filterSources() {
    const dim = document.getElementById('filter-dimension').value;
    const status = document.getElementById('filter-status').value;
    const rows = document.querySelectorAll('#sources-tbody tr');
    
    rows.forEach(row => {
        const rowDim = row.dataset.dimension;
        const rowEnabled = row.dataset.enabled;
        
        let show = true;
        if (dim !== 'all' && rowDim !== dim) show = false;
        if (status === 'enabled' && rowEnabled !== 'true') show = false;
        if (status === 'disabled' && rowEnabled !== 'false') show = false;
        
        row.style.display = show ? '' : 'none';
    });
}
</script>
{% endblock %}
```

- [ ] **Step 2: Commit**

```bash
git add templates/crawl.html
git commit -m "feat: add crawl management page with source list and dimension filter"
```

---

### Task 15: 设置页面 — templates/settings.html

**Files:**
- Create: `D:\workproject\summary\templates\settings.html`

- [ ] **Step 1: 编写 settings.html**

```html
{% extends "base.html" %}
{% block title %}设置 - 量子通信信息监测平台{% endblock %}

{% block content %}
<div class="card">
    <div class="card-title">⚙️ 爬取设置</div>
    
    <div class="form-group">
        <label class="form-label">自动爬取</label>
        <label class="toggle" style="vertical-align:middle;">
            <input type="checkbox" id="auto-crawl" {% if config.auto_crawl_enabled == 'true' %}checked{% endif %} onchange="saveSettings()">
            <span class="toggle-slider"></span>
        </label>
        <span style="margin-left:8px;color:var(--text-secondary);font-size:14px;" id="auto-status">
            {{ '已启用' if config.auto_crawl_enabled == 'true' else '已暂停' }}
        </span>
    </div>
    
    <div class="form-group">
        <label class="form-label">爬取频率</label>
        <select class="form-select" id="crawl-frequency" onchange="onFrequencyChange(); saveSettings();" style="max-width:200px;">
            <option value="daily" {% if config.crawl_frequency == 'daily' %}selected{% endif %}>每天一次</option>
            <option value="6h" {% if config.crawl_frequency == '6h' %}selected{% endif %}>每 6 小时</option>
            <option value="12h" {% if config.crawl_frequency == '12h' %}selected{% endif %}>每 12 小时</option>
            <option value="manual" {% if config.crawl_frequency == 'manual' %}selected{% endif %}>手动触发</option>
        </select>
    </div>
    
    <div class="form-group" id="hour-group" style="{% if config.crawl_frequency != 'daily' %}display:none;{% endif %}">
        <label class="form-label">每天执行时间</label>
        <select class="form-select" id="crawl-hour" onchange="saveSettings()" style="max-width:200px;">
            {% for h in range(24) %}
            <option value="{{ h }}" {% if config.crawl_hour == h|string %}selected{% endif %}>{{ "%02d"|format(h) }}:00</option>
            {% endfor %}
        </select>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
function onFrequencyChange() {
    const freq = document.getElementById('crawl-frequency').value;
    document.getElementById('hour-group').style.display = (freq === 'daily') ? '' : 'none';
}

async function saveSettings() {
    const autoCrawl = document.getElementById('auto-crawl').checked;
    const frequency = document.getElementById('crawl-frequency').value;
    const hour = parseInt(document.getElementById('crawl-hour').value);
    
    // 更新界面文字
    document.getElementById('auto-status').textContent = autoCrawl ? '已启用' : '已暂停';
    
    try {
        await fetch('/api/schedule', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                auto_crawl_enabled: autoCrawl,
                frequency: frequency,
                hour: hour
            })
        });
        showToast('设置已保存', 'success');
    } catch (e) {
        showToast('保存失败: ' + e.message, 'error');
    }
}

// Toast (复用)
function showToast(msg, type) {
    const toast = document.getElementById('toast');
    if (!toast) return;
    toast.textContent = msg;
    toast.className = 'toast ' + (type || 'info');
    toast.style.display = 'block';
    setTimeout(() => { toast.style.display = 'none'; }, 3000);
}
</script>
{% endblock %}
```

- [ ] **Step 2: Commit**

```bash
git add templates/settings.html
git commit -m "feat: add settings page with frequency, hour, and auto-crawl toggle"
```

---

### Task 16: 报告模板 — templates/report.html

**Files:**
- Create: `D:\workproject\summary\templates\report.html`

- [ ] **Step 1: 编写 report.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>量子通信信息监测报告 {{ start_date }} ~ {{ end_date }}</title>
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
    <style>
        .report-header { text-align: center; padding: 40px 0 20px; }
        .report-header h1 { font-size: 28px; margin-bottom: 8px; }
        .report-header .meta { color: var(--text-secondary); font-size: 15px; }
        .chart-container { width: 100%; height: 350px; margin-bottom: 24px; }
        .article-card {
            padding: 14px 0; border-bottom: 1px solid var(--border);
        }
        .article-card:last-child { border-bottom: none; }
        .article-title { font-size: 16px; font-weight: 600; margin-bottom: 4px; }
        .article-title a { color: var(--text); text-decoration: none; }
        .article-title a:hover { color: var(--primary); }
        .article-meta { font-size: 14px; color: var(--text-secondary); }
        .article-summary { font-size: 14px; color: var(--text-secondary); margin-top: 4px; }
        .dim-section { margin-bottom: 32px; }
        .dim-section h2 { font-size: 22px; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 3px solid; }
        .dim-section.policy h2 { color: #dc2626; border-color: #dc2626; }
        .dim-section.industry h2 { color: #2563eb; border-color: #2563eb; }
        .dim-section.research h2 { color: #16a34a; border-color: #16a34a; }
        .no-data { text-align: center; color: var(--text-secondary); padding: 40px; }
        .appendix { margin-top: 40px; padding-top: 20px; border-top: 2px solid var(--border); }
        .appendix h3 { font-size: 16px; color: var(--text-secondary); }
        .appendix ul { list-style: none; padding: 0; }
        .appendix li { display: inline-block; margin: 4px 12px; font-size: 14px; color: var(--text-secondary); }
    </style>
</head>
<body>
    <div class="main-content">
        <!-- Header -->
        <div class="report-header">
            <h1>量子通信信息监测报告</h1>
            <p class="meta">{{ start_date }} 至 {{ end_date }} &nbsp;|&nbsp; 生成时间：{{ generated_at }}</p>
        </div>
        
        <!-- Overview -->
        <div class="card">
            <div class="card-title">📊 概览</div>
            <div class="stats-row" style="margin-bottom:24px;">
                <div class="stat-card"><div class="stat-number">{{ total }}</div><div class="stat-label">信息总量</div></div>
                <div class="stat-card dim-policy"><div class="stat-number">{{ policy_count }}</div><div class="stat-label">政策动态</div></div>
                <div class="stat-card dim-industry"><div class="stat-number">{{ industry_count }}</div><div class="stat-label">产业进展</div></div>
                <div class="stat-card dim-research"><div class="stat-number">{{ research_count }}</div><div class="stat-label">科研成果</div></div>
            </div>
            
            {% if total > 0 %}
            <!-- Line Chart: Daily Counts -->
            <div class="chart-container" id="line-chart"></div>
            
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:20px;">
                <!-- Pie Chart: Dimension Distribution -->
                <div class="chart-container" id="pie-chart"></div>
                <!-- Bar Chart: Top Sources -->
                <div class="chart-container" id="bar-chart"></div>
            </div>
            {% else %}
            <div class="no-data">该时间段暂无数据</div>
            {% endif %}
        </div>
        
        {% if total > 0 %}
        <!-- Policy Section -->
        <div class="card dim-section policy">
            <h2>🔴 一、政策动态 ({{ policy_count }})</h2>
            {% if policy_articles %}
                {% for a in policy_articles %}
                <div class="article-card">
                    <div class="article-title">
                        <a href="{{ a.url }}" target="_blank">{{ a.title }}</a>
                    </div>
                    {% if a.summary %}<div class="article-summary">{{ a.summary[:200] }}</div>{% endif %}
                    <div class="article-meta">
                        来源：{{ a.source_name }} &nbsp;|&nbsp; {{ a.publish_time if a.publish_time else '未知时间' }}
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <div class="no-data">该维度下暂无数据</div>
            {% endif %}
        </div>
        
        <!-- Industry Section -->
        <div class="card dim-section industry">
            <h2>🔵 二、产业进展 ({{ industry_count }})</h2>
            {% if industry_articles %}
                {% for a in industry_articles %}
                <div class="article-card">
                    <div class="article-title">
                        <a href="{{ a.url }}" target="_blank">{{ a.title }}</a>
                    </div>
                    {% if a.summary %}<div class="article-summary">{{ a.summary[:200] }}</div>{% endif %}
                    <div class="article-meta">
                        来源：{{ a.source_name }} &nbsp;|&nbsp; {{ a.publish_time if a.publish_time else '未知时间' }}
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <div class="no-data">该维度下暂无数据</div>
            {% endif %}
        </div>
        
        <!-- Research Section -->
        <div class="card dim-section research">
            <h2>🟢 三、科研成果 ({{ research_count }})</h2>
            {% if research_articles %}
                {% for a in research_articles %}
                <div class="article-card">
                    <div class="article-title">
                        <a href="{{ a.url }}" target="_blank">{{ a.title }}</a>
                    </div>
                    {% if a.summary %}<div class="article-summary">{{ a.summary[:200] }}</div>{% endif %}
                    <div class="article-meta">
                        来源：{{ a.source_name }} &nbsp;|&nbsp; {{ a.publish_time if a.publish_time else '未知时间' }}
                    </div>
                </div>
                {% endfor %}
            {% else %}
                <div class="no-data">该维度下暂无数据</div>
            {% endif %}
        </div>
        {% endif %}
        
        <!-- Appendix -->
        <div class="appendix">
            <h3>📎 本报告涉及信息源</h3>
            <ul>
                {% for s in sources %}
                <li>{{ s }}</li>
                {% endfor %}
            </ul>
        </div>
    </div>
    
    {% if total > 0 %}
    <script>
    // Line Chart
    (function(){
        var chart = echarts.init(document.getElementById('line-chart'));
        chart.setOption({
            title: { text: '每日信息量趋势', left: 'center', textStyle: { fontSize: 16 } },
            tooltip: { trigger: 'axis' },
            legend: { bottom: 0, data: ['政策动态', '产业进展', '科研成果'] },
            grid: { left: '3%', right: '4%', bottom: '15%', containLabel: true },
            xAxis: { type: 'category', data: {{ line_dates|safe }} },
            yAxis: { type: 'value', minInterval: 1 },
            series: [
                { name: '政策动态', type: 'line', data: {{ line_policy|safe }}, color: '#dc2626', smooth: true },
                { name: '产业进展', type: 'line', data: {{ line_industry|safe }}, color: '#2563eb', smooth: true },
                { name: '科研成果', type: 'line', data: {{ line_research|safe }}, color: '#16a34a', smooth: true }
            ]
        });
    })();
    
    // Pie Chart
    (function(){
        var chart = echarts.init(document.getElementById('pie-chart'));
        chart.setOption({
            title: { text: '维度分布', left: 'center', textStyle: { fontSize: 16 } },
            tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
            series: [{
                type: 'pie', radius: ['40%', '70%'],
                data: {{ pie_data|safe }},
                label: { formatter: '{b}\n{d}%' },
                itemStyle: {
                    color: function(params) {
                        var colors = {'政策动态':'#dc2626','产业进展':'#2563eb','科研成果':'#16a34a'};
                        return colors[params.name] || '#999';
                    }
                }
            }]
        });
    })();
    
    // Bar Chart
    (function(){
        var chart = echarts.init(document.getElementById('bar-chart'));
        chart.setOption({
            title: { text: '信息来源 Top10', left: 'center', textStyle: { fontSize: 16 } },
            tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
            grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
            xAxis: { type: 'value', minInterval: 1 },
            yAxis: { type: 'category', data: {{ bar_sources|safe }}, axisLabel: { fontSize: 12 } },
            series: [{ type: 'bar', data: {{ bar_counts|safe }}, color: '#2563eb' }]
        });
    })();
    </script>
    {% endif %}
</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add templates/report.html
git commit -m "feat: add HTML report template with ECharts line/pie/bar charts"
```

---

### Task 17: 集成验证与修复

**Files:** None (validation only)

- [ ] **Step 1: 确认所有文件存在**

```bash
cd D:\workproject\summary
ls pyproject.toml app.py models.py sources.json scheduler.py reporter.py
ls crawlers/engine.py crawlers/fetcher.py crawlers/__init__.py
ls crawlers/parsers/base.py crawlers/parsers/rss_parsers.py crawlers/parsers/__init__.py
ls templates/base.html templates/dashboard.html templates/crawl.html templates/settings.html templates/report.html
ls static/css/style.css static/js/app.js
```

- [ ] **Step 2: 启动应用并测试核心流程**

```bash
cd D:\workproject\summary
uv run python -c "
from models import init_db
init_db()
print('DB OK')

from app import create_app
app = create_app()
print('App created OK')

# 测试路由
with app.test_client() as client:
    resp = client.get('/')
    assert resp.status_code == 200
    print('Dashboard: 200 OK')
    
    resp = client.get('/crawl')
    assert resp.status_code == 200
    print('Crawl page: 200 OK')
    
    resp = client.get('/settings')
    assert resp.status_code == 200
    print('Settings page: 200 OK')
    
    # 测试 API
    resp = client.get('/api/stats')
    assert resp.status_code == 200
    print(f'Stats API: {resp.get_json()}')
    
    resp = client.get('/api/schedule')
    assert resp.status_code == 200
    print(f'Schedule API: {resp.get_json()}')
    
print()
print('All integration checks passed!')
"
```

Expected: 所有检查通过

- [ ] **Step 3: 如果有任何错误，修复后重新验证**

- [ ] **Step 4: 启动完整应用做最终验证**

```bash
cd D:\workproject\summary
uv run python app.py
```

然后浏览器访问 `http://127.0.0.1:5000`，确认：
1. 仪表盘正常显示（四个统计卡片、爬取按钮、日期选择器）
2. 点击"爬取管理"导航到 `/crawl`，显示信息源列表
3. 点击"设置"导航到 `/settings`，可修改频率
4. 点击"立即爬取"，观察后台日志有爬取活动
5. 选择日期范围，点击"生成报告"，新标签页打开 HTML 报告

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "chore: integration verification - all pages and APIs working"
```

---

## 后续阶段（P6）

### Task 18-24: 逐个信息源调优解析器

按需为结构特殊的信息源编写专用解析器（如合肥日报、量子位等），放在 `crawlers/parsers/` 目录下，命名格式 `source_<name>.py`。

调优原则：
- 先用浏览器开发者工具分析目标网站的列表页 HTML 结构
- 编写专用解析器，提取更准确的标题、摘要和发布时间
- 更新 `sources.json` 中对应源的 `parser` 字段
- 在 `crawlers/engine.py` 的 `crawl_source()` 中增加对 `html_custom_*` 解析器的路由

---

## 自检清单

- [x] 所有 Task 包含完整代码，无 TBD/TODO
- [x] 文件路径与 spec 目录结构一致
- [x] 数据模型与 spec 一致（articles, config, crawl_log 三表）
- [x] API 路由覆盖 spec 所有接口
- [x] 前端页面覆盖 spec 所有页面
- [x] 报告模板包含三维度分类 + ECharts 图表 + 来源附录
- [x] 调度模块支持 daily/6h/12h/manual 四种频率
- [x] 无 API Key 依赖
