# 量子通信信息监测平台 — 设计方案

> 生成日期：2026-05-05  
> 版本：v1.0

---

## 一、项目概述

从权威媒体定时爬取量子通信领域信息，按政策/产业/科研三维度分类保存。用户可通过 Web 图形界面选择日期范围，一键生成包含统计图表的结构化 HTML 报告。

### 核心原则

- 不依赖任何需要 API Key 的外部服务
- 非计算机专业人员可轻松使用
- 界面简洁直观，易用性优先

---

## 二、技术架构

### 总体架构

```
┌─────────────────────────────────────────────┐
│             前端 Web 界面                     │
│     (仪表盘 / 爬取管理 / 报告生成)            │
│     HTML + CSS + JS + ECharts(CDN)           │
└──────────────────┬──────────────────────────┘
                   │ HTTP
┌──────────────────▼──────────────────────────┐
│           Python 后端 (Flask)                 │
│     路由 + 模板渲染 + REST API                │
├────────────┬──────────┬─────────────────────┤
│ 爬虫模块   │ 调度模块  │  报告生成模块         │
│ requests   │ APScheduler│ Jinja2 模板         │
│ BeautifulSoup│         │ ECharts 配置注入     │
├────────────┴──────────┴─────────────────────┤
│              SQLite 数据库                    │
└─────────────────────────────────────────────┘
```

### 技术选型表

| 层面 | 技术 | 说明 |
|------|------|------|
| 语言 | Python 3.12+ | — |
| 包管理 | uv + pyproject.toml | 现代 Python 项目管理 |
| Web 框架 | Flask | 轻量，提供路由 + API + 模板 |
| 爬虫 | requests + BeautifulSoup4 | HTTP 请求与 HTML 解析 |
| 调度 | APScheduler | 内嵌 Flask，无需独立进程 |
| 数据库 | SQLite | 零配置本地存储 |
| 模板 | Jinja2 | Flask 内置，报告 HTML 渲染 |
| 图表 | ECharts (CDN) | 无需安装，浏览器端渲染 |
| 前端 | 纯 HTML/CSS/JS | 无前端框架，保持轻量 |

### 项目目录结构

```
quantum-news-monitor/
├── pyproject.toml                  # 项目配置与依赖
├── sources.json                    # 信息源列表（27个，三维度分类）
├── app.py                          # Flask 应用入口
├── crawlers/
│   ├── __init__.py
│   ├── engine.py                   # 爬虫调度引擎（遍历源、去重、入库）
│   ├── fetcher.py                  # HTTP 请求封装（超时、重试、UA）
│   └── parsers/
│       ├── __init__.py
│       ├── base.py                 # 通用解析器（关键词过滤兜底）
│       ├── rss_parsers.py          # RSS/结构化接口解析器
│       ├── html_parsers.py         # HTML 页面解析器
│       └── source_*.py             # 按需添加特定源解析器
├── scheduler.py                    # APScheduler 配置与管理
├── models.py                       # SQLite 数据库模型（建表、CRUD）
├── reporter.py                     # 报告生成（查询聚合 + Jinja2 渲染）
├── templates/
│   ├── base.html                   # 基础布局模板
│   ├── dashboard.html              # 仪表盘页面
│   ├── crawl.html                  # 爬取管理页面
│   ├── settings.html               # 设置页面
│   └── report.html                 # 报告模板
├── static/
│   ├── css/
│   │   └── style.css               # 全局样式
│   └── js/
│       └── app.js                  # 前端交互逻辑
├── data/
│   └── quantum_news.db             # SQLite 数据库文件（运行时生成）
├── logs/
│   └── crawler.log                 # 爬取日志
└── reports/                        # 生成的 HTML 报告
```

---

## 三、数据模型

### SQLite 表结构

#### articles（主表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INTEGER | PK, AUTOINCREMENT | 自增主键 |
| `title` | TEXT | NOT NULL | 文章标题 |
| `summary` | TEXT | — | 内容摘要（前 200 字） |
| `url` | TEXT | NOT NULL, UNIQUE | 文章链接（MD5 哈希去重） |
| `source_name` | TEXT | NOT NULL | 信息来源名称 |
| `source_url` | TEXT | — | 信息源主页链接 |
| `dimension` | TEXT | NOT NULL | `policy` / `industry` / `research` |
| `publish_time` | TEXT | — | 文章原始发布时间 |
| `crawl_time` | TEXT | NOT NULL | 爬取入库时间 |
| `is_valid` | INTEGER | DEFAULT 1 | 1=正常，0=链接失效 |

#### config（配置表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `key` | TEXT | PK | 配置键 |
| `value` | TEXT | — | 配置值 |

预置配置项：
- `crawl_frequency`: `daily` / `6h` / `12h` / `manual`
- `crawl_hour`: 爬取执行的小时（默认 `8`）
- `last_crawl_time`: 上次爬取完成时间（ISO 格式）
- `auto_crawl_enabled`: `true` / `false`

#### crawl_log（爬取日志表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INTEGER | PK, AUTOINCREMENT | 自增主键 |
| `start_time` | TEXT | NOT NULL | 爬取开始时间 |
| `end_time` | TEXT | — | 爬取结束时间 |
| `total_sources` | INTEGER | — | 总信息源数 |
| `success_count` | INTEGER | — | 成功抓取数 |
| `new_articles` | INTEGER | — | 新增文章数 |
| `status` | TEXT | — | `running` / `completed` / `failed` |

---

## 四、模块详细设计

### 4.1 爬虫模块

#### 信息源配置格式（sources.json）

```json
[
  {
    "name": "中华人民共和国外交部",
    "url": "https://www.mfa.gov.cn/",
    "dimension": "policy",
    "parser": "html_generic",
    "enabled": true,
    "keywords": ["量子", "QKD", "quantum"],
    "encoding": "utf-8"
  }
]
```

每个源包含：名称、URL、维度分类、解析器类型、启用状态、搜索关键词、编码方式。

#### 爬取流程

```
定时/手动触发
  → 加载 sources.json（仅 enabled=true 的源）
  → 逐个信息源：
      ├─ HTTP GET（超时 30s，重试 2 次，间隔 2-5s）
      ├─ 调用对应解析器提取字段
      ├─ url 去重检查（UNIQUE 约束自动处理）
      └─ 新文章 → INSERT，重复 → 跳过
  → 更新 last_crawl_time
  → 写入 crawl_log
  → 返回统计：成功数/失败数/新增数
```

#### 解析器策略

| 解析器类型 | 适用站点 | 实现方式 |
|-----------|---------|---------|
| `rss` | Nature, Science, arXiv | feedparser 库解析 RSS/Atom |
| `html_generic` | 大部分政府/媒体站 | BeautifulSoup 提取列表页 `<a>` 标签，关键词过滤 |
| `html_custom_*` | 结构特殊的站点 | 按需编写，继承 base 解析器 |

#### 去重机制

- `url` 字段建 UNIQUE 索引
- 插入时使用 `INSERT OR IGNORE`
- 每次爬取返回 "新增 N 条，跳过 M 条"

---

### 4.2 调度模块

#### 设计要点

- APScheduler 内嵌在 Flask 进程中，`BackgroundScheduler`
- 应用启动时从 config 表读取频率配置，注册 Job
- 仅一个爬取 Job 活跃（防止并发），使用 `max_instances=1`
- 手动触发通过 API 调用，直接执行爬取函数，不走调度器

#### 调度 API

| 方法 | 路径 | 入参 | 说明 |
|------|------|------|------|
| GET | `/api/schedule` | — | 返回当前调度配置 |
| PUT | `/api/schedule` | `{frequency, hour}` | 更新调度频率与执行时间 |
| POST | `/api/crawl/trigger` | — | 手动触发爬取 |
| GET | `/api/crawl/status` | — | 返回最近爬取状态与日志 |

---

### 4.3 Web 界面

#### 页面路由

| 路径 | 页面 | 说明 |
|------|------|------|
| `/` | 仪表盘 | 首页，概览 + 报告生成入口 |
| `/crawl` | 爬取管理 | 信息源列表，启停管理 |
| `/settings` | 设置 | 爬取频率配置 |

#### 仪表盘（首页）

```
┌──────────────────────────────────────────────────┐
│  🔬 量子通信信息监测平台              [爬取管理] [设置] │
├──────────────────────────────────────────────────┤
│                                                  │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐   │
│  │ 总信息  │ │ 政策   │ │ 产业   │ │ 科研   │   │
│  │ 1,247  │ │  312   │ │  508   │ │  427   │   │
│  └────────┘ └────────┘ └────────┘ └────────┘   │
│                                                  │
│  [立即爬取]  上次爬取：2026-05-05 08:00 新增12条  │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │  生成报告                                   │  │
│  │  开始 [____]  结束 [____]  [生成] [预览]    │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │  最近爬取日志                               │  │
│  │  05-05 08:05  完成  新增 12 条              │  │
│  │  05-04 08:00  完成  新增 23 条              │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
└──────────────────────────────────────────────────┘
```

#### 爬取管理页面

- 信息源列表，每行：名称 | 维度 | URL | 启用开关 | 最近爬取 | 新增数
- 维度筛选（全部/政策/产业/科研）
- 按启用/禁用状态筛选

#### 设置页面

- 爬取频率：下拉选择（每天/每6小时/每12小时/手动）
- 执行时间：小时选择器（仅"每天"模式显示）
- 自动爬取开关：全局启用/暂停

#### 样式设计原则

- 大字号（正文 16px+），高对比度（深色文字 + 浅色背景）
- 卡片式布局，信息分层清晰
- 按钮带 hover/active 状态，操作有明确反馈
- `@media print` 支持报告打印/另存 PDF
- 响应式适配桌面（1200px+）和笔记本（1024px）

---

### 4.4 报告生成

#### 生成流程

```
用户选择日期范围 → POST /api/report/generate
  → 查询 articles WHERE publish_time BETWEEN start AND end
  → 按 dimension 分组
  → 统计：每日数量、维度分布、来源 Top10
  → Jinja2 渲染 report.html 模板
  → 保存到 reports/YYYY-MM-DD_YYYY-MM-DD.html
  → 返回文件路径，浏览器新标签页打开
```

#### 报告内容结构

```
┌───────────────────────────────────────────────┐
│  量子通信信息监测报告                           │
│  2026-04-01 至 2026-04-05 | 生成于 2026-05-05  │
├───────────────────────────────────────────────┤
│  📊 概览                                       │
│  · 本时段共收集 47 条信息                       │
│  · 政策 12 | 产业 18 | 科研 17                 │
│  · 每日信息量折线图（ECharts）                  │
│  · 维度分布环形图（ECharts）                    │
│  · 信息来源 Top10 柱状图（ECharts）             │
├───────────────────────────────────────────────┤
│  🔴 一、政策动态                                │
│  · 文章标题（可点击跳转原文）                    │
│    摘要 | 来源 | 发布时间                        │
│  · ...                                         │
├───────────────────────────────────────────────┤
│  🔵 二、产业进展                                │
│  · ...                                         │
├───────────────────────────────────────────────┤
│  🟢 三、科研成果                                │
│  · ...                                         │
├───────────────────────────────────────────────┤
│  📎 附录：本报告涉及信息源列表                    │
└───────────────────────────────────────────────┘
```

#### 图表配置（ECharts）

| 图表 | 类型 | 数据 |
|------|------|------|
| 每日信息量 | 折线图 | X=日期, Y=数量, 三条线=三维度 |
| 维度分布 | 环形图 | 三维度占比 |
| 来源 Top10 | 横向柱状图 | 产出最多的 10 个源 |

图表配置由 Python 后端计算好数据，注入到 HTML 的 `<script>` 变量中，浏览器端 ECharts 渲染。

#### 报告 API

| 方法 | 路径 | 入参 | 说明 |
|------|------|------|------|
| POST | `/api/report/generate` | `{start_date, end_date}` | 生成报告 |
| GET | `/api/report/list` | — | 列出已生成报告 |
| GET | `/reports/<filename>` | — | 访问已生成的报告文件 |

---

## 五、信息源完整清单

### 政策维度（policy）

| # | 名称 | URL |
|---|------|-----|
| 1 | 中华人民共和国外交部 | https://www.mfa.gov.cn/ |
| 2 | 国务院新闻办公室 | http://www.scio.gov.cn/ |
| 3 | 科学技术部 | https://www.most.gov.cn/ |
| 4 | 工业和信息化部 | https://www.miit.gov.cn/ |
| 5 | 安徽省人民政府官网 | https://www.ah.gov.cn/ |
| 6 | 新华网（政策频道） | http://politics.news.cn/ |
| 7 | 合肥日报 | https://newspaper.hf365.com/hfrb/ |
| 8 | 欧盟委员会量子旗舰计划 | https://quantum-flagship.eu/ |
| 9 | 美国参议院官网 | https://www.senate.gov/ |

### 产业进展维度（industry）

| # | 名称 | URL |
|---|------|-----|
| 1 | 科技日报 | https://www.stdaily.com.cn/ |
| 2 | 中国电子报 | https://www.cena.com.cn/ |
| 3 | 通信信息报社（C114） | https://www.c114.com/ |
| 4 | 安徽发布 | https://www.ah.gov.cn/ahfb/ |
| 5 | 合肥日报 | https://newspaper.hf365.com/hfrb/ |
| 6 | 量子位（QbitAI） | https://www.qbitai.com/ |
| 7 | 中新网 | https://www.chinanews.com/ |
| 8 | 人民网 | https://www.people.com.cn/ |
| 9 | 中国电信官方新闻中心 | (需进一步确认 URL) |
| 10 | 中国移动官方新闻中心 | (需进一步确认 URL) |
| 11 | The Quantum Insider | https://thequantuminsider.com/ |
| 12 | Quantum Daily | https://quantumdaily.com/ |

### 科研成果维度（research）

| # | 名称 | URL |
|---|------|-----|
| 1 | 中国科学院官网 | https://www.cas.cn/ |
| 2 | 中科院量子信息与量子科技创新研究院 | http://www.qiis.ac.cn/ |
| 3 | 中国科学技术大学官网 | https://www.ustc.edu.cn/ |
| 4 | 合肥日报 | https://newspaper.hf365.com/hfrb/ |
| 5 | Nature News | https://www.nature.com/news |
| 6 | Science News | https://www.science.org/news |
| 7 | arXiv | https://arxiv.org/ |
| 8 | New Scientist | https://www.newscientist.com/ |

> 注：合肥日报同时出现在三个维度中，爬取一次后按内容关键词自动归类。中国电信/中国移动新闻中心具体 URL 需实施时确认。

---

## 六、非功能需求

### 性能

- 27 个信息源全量爬取预计耗时 3-8 分钟（含 2-5s 间隔）
- 报告生成（含图表数据计算）预计 < 2 秒
- SQLite 在万级数据量下查询性能充足

### 可靠性

- 单个信息源爬取失败不影响其他源
- HTTP 请求超时 30 秒，重试 2 次
- 爬取异常写入日志，不中断整体流程

### 可维护性

- 每个信息源独立解析器文件，新增/移除互不影响
- sources.json 可热编辑，重启后生效
- 日志记录每次爬取的详细情况便于排查

---

## 七、依赖清单（pyproject.toml）

```toml
[project]
name = "quantum-news-monitor"
version = "0.1.0"
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

---

## 八、开发阶段划分

| 阶段 | 内容 | 预计产出 |
|------|------|---------|
| P1 | 项目骨架：Flask 入口、目录结构、数据库模型、基础模板 | 可启动的空应用 |
| P2 | 爬虫核心：fetcher + 通用解析器 + sources.json + 去重入库 | 可手动触发爬取 |
| P3 | 调度模块：APScheduler 集成 + 调度 API | 定时自动爬取 |
| P4 | Web 界面：仪表盘 + 爬取管理 + 设置页面 | 完整 GUI |
| P5 | 报告生成：数据聚合 + Jinja2 + ECharts 图表 | 完整报告功能 |
| P6 | 逐个信息源调优解析器 | 爬取质量优化 |

---

## 九、验收标准

1. 启动应用后浏览器访问本地地址，显示仪表盘
2. 点击"立即爬取"，能从 27 个信息源抓取量子通信相关内容并入库
3. 信息按政策/产业/科研三维度正确分类
4. 默认每天 8:00 自动爬取，无需人工干预
5. 在仪表盘选择日期范围，点击生成报告，浏览器新标签页打开 HTML 报告
6. 报告包含三维度分类信息（每条有标题、摘要、来源、链接、时间）+ 统计图表
7. 可在设置页调整爬取频率
8. 全程无需 API Key
