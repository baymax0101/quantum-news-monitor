# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

量子通信信息监测平台。从 25 个权威媒体定时爬取量子通信信息，按政策/产业/科研（国内/国外）+ 合肥相关三维度七分类整理，通过 Web 界面生成带 ECharts 图表的 HTML 报告。

## 技术栈

- Python 3.12+ / uv / Flask 3.x
- 数据库：SQLite（WAL 模式）
- 爬虫：requests + BeautifulSoup4 + feedparser
- 调度：APScheduler
- 图表：ECharts（CDN 引入）
- 前端：纯 HTML/CSS/JS（无框架）

## 常用命令

```bash
# 安装依赖
uv sync

# 启动应用
uv run python app.py
# 访问 http://127.0.0.1:5000

# 运行集成测试
uv run python -c "
from models import init_db; init_db()
from app import create_app
app = create_app()
with app.test_client() as client:
    assert client.get('/').status_code == 200
    assert client.get('/crawl').status_code == 200
    assert client.get('/settings').status_code == 200
    assert client.get('/api/stats').status_code == 200
    assert client.get('/api/schedule').status_code == 200
    assert client.get('/api/report/list').status_code == 200
print('All checks passed')
"

# 代码格式化
uv run ruff check .

# 删除数据库重新初始化
del data\quantum_news.db
```

## 架构概览

### 数据流

```
定时/手动触发
  → crawlers/engine.py（遍历 25 个来源）
    → crawlers/fetcher.py（HTTP 请求 + 重试）
    → crawlers/parsers/（RSS 或 HTML 解析 + 关键词过滤）
    → models.py（SQLite 去重入库）
  → templates/*.html（Flask 渲染页面）
  → reporter.py（报告聚合）
    → templates/report.html（Jinja2 + ECharts）
```

### 核心模块

| 模块 | 职责 |
|------|------|
| `app.py` | Flask 入口，注册所有路由和 API |
| `models.py` | SQLite 建表、CRUD（articles / config / crawl_log） |
| `crawlers/engine.py` | 爬取引擎：加载源、调用解析器、去重入库 |
| `crawlers/fetcher.py` | HTTP 请求：超时 30s、重试 2 次、UA 轮换 |
| `crawlers/parsers/base.py` | 通用 HTML 解析器：关键词正则匹配提取链接 |
| `crawlers/parsers/rss_parsers.py` | RSS/Atom 解析器 |
| `scheduler.py` | APScheduler 管理（daily/6h/12h/manual） |
| `reporter.py` | 报告生成：数据聚合、ECharts 配置注入、Jinja2 渲染 |
| `sources.json` | 25 个信息源配置（name/url/dimension/region/keywords） |

### 分类体系

- 维度：policy（政策）/ industry（产业）/ research（科研）
- 区域：domestic（国内）/ international（国外）/ hefei（合肥）
- 报告 7 分区：政策 / 产业·国内 / 产业·国外 / 科研·国内 / 科研·国外 / 合肥相关

### API 路由

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/stats` | 各维度文章计数（7 个字段） |
| POST | `/api/crawl/trigger` | 触发全量爬取 |
| GET | `/api/crawl/status` | 爬取状态与最近日志 |
| GET | `/api/schedule` | 获取调度配置 |
| PUT | `/api/schedule` | 更新调度频率 |
| POST | `/api/report/generate` | 生成日期范围报告 |
| POST | `/api/report/pdf` | 下载 PDF（降级为 HTML） |
| GET | `/api/report/list` | 已生成报告列表 |

## 开发注意事项

### 数据库兼容性

`models.py` 的 `init_db()` 包含兼容旧数据库的迁移逻辑。如果新增字段，应在 `init_db()` 中添加 `ALTER TABLE` + `CREATE INDEX IF NOT EXISTS` 的 try/except 块，确保不破坏已有运行实例的数据库。

### 信息源配置

`sources.json` 是爬虫配置中心。每个源包含 name/url/dimension/region/parser/enabled/keywords/encoding 等字段。新增或修改源后重启应用生效。

### 爬虫解析策略

- RSS 源（Nature / Science / arXiv）：使用 `rss_parsers.py`，自动提取发布时间
- HTML 源（其他 22 个）：使用 `base.py` 的 `extract_links()`，通过关键词匹配标题和 URL
- 合肥相关内容自动检测：`engine.py` 中的 `_detect_hefei()` 检查标题和 URL 中的合肥关键词

### PDF 导出

Windows 环境下 WeasyPrint 因缺少 GTK 系统库不可用，"下载 PDF"按钮会自动降级为调用浏览器 `window.print()` 功能（选择"另存为 PDF"）。Linux/Mac 上安装 GTK 后 WeasyPrint 可正常使用。

### 前后端数据契约

`get_article_counts()` 返回的 7 个字段与 `dashboard.html` 中的 7 个统计卡片一一对应。修改返回结构时需同步更新前端模板。
