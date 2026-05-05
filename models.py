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
        cur = conn.execute(
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
        inserted = cur.rowcount > 0
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
