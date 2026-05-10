# 🔬 量子通信信息监测平台

从权威媒体定时爬取量子通信领域信息，按政策/产业/科研（国内/国外）+ 合肥相关三维度七分类整理，通过 Web 界面一键生成带 ECharts 可视化图表的 HTML 报告。

## 功能特性

| 功能 | 说明 |
|------|------|
| 🕷️ **智能爬虫** | 57 个信息源（50 个默认启用），支持 RSS + HTML + RSSHub 三模式解析，自动去重 |
| 📊 **七维分类** | 政策动态 / 产业国内 / 产业国外 / 科研国内 / 科研国外 / 合肥相关 |
| ⏰ **定时调度** | 默认每天 8:00 自动爬取，可调频率（每 6h / 每 12h / 手动） |
| 📄 **HTML 报告** | 按维度分组展示 + ECharts 折线/环形/柱状图 + 原文链接 |
| 🖨️ **PDF 导出** | 浏览器打印为 PDF，利用 `@media print` CSS 完美排版 |
| 🎨 **易用界面** | 大字号、高对比度、响应式布局，非技术人员友好 |

## 快速开始

### 环境要求

- **Python** ≥ 3.12
- **uv**（Python 包管理器）

### 安装 uv

```bash
# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Mac / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 安装与运行

```bash
# 1. 克隆项目
git clone https://github.com/baymax0101/quantum-news-monitor.git
cd quantum-news-monitor

# 2. 安装依赖
uv sync

# 3. 启动应用
uv run python app.py
```

浏览器访问 **http://127.0.0.1:5000**

### 使用流程

1. **首页仪表盘** → 查看各维度信息总量，点击「立即爬取」获取最新信息
2. **爬取管理** → 查看 25 个信息源状态，按维度/启用状态筛选
3. **设置** → 调整自动爬取频率（每天 / 每 6 小时 / 每 12 小时 / 手动）
4. **生成报告** → 选择日期范围，点击「生成报告」即可在浏览器中预览
5. **导出 PDF** → 点击报告页「打印 / 导出 PDF」→ 浏览器打印对话框 → 另存为 PDF

### 信息源覆盖

| 维度 | 国内源 | 国际源 | 合肥源 |
|------|--------|--------|--------|
| 政策 | 外交部、国务院新闻办、科技部、工信部、国家发改委、国资委、人民银行、国家密码管理局、北京市密码管理局、新华网 | 欧盟量子旗舰、美国参议院 | 安徽省政府、合肥日报 |
| 产业 | 科技日报、中国电子报、C114、量子位、中新网、人民网、36氪、澎湃新闻、界面新闻、钛媒体、融中财经、21世纪经济报道、经济参考报、通信世界网、安全内参、OFweek、前瞻产业研究院、智研咨询、观研报告网 | Quantum Insider、Quantum Daily | 安徽发布、合肥日报 |
| 科研 | 中国科学院、上海技物所、济南量子院、北京量子院、中国科学报、中国物理快报 | Nature、Science、arXiv、New Scientist | 中科大、量子创新研究院、合肥日报 |
| 企业 | 国盾量子、中电信量子、问天量子、启科量子、本源量子、中国电科、国家电网 | — | — |
| 微信* | 量子客、量子大观、国盾量子、中电信量子、安全内参、网信前言观察、中科大 | — | — |

> *微信公众号通过 RSSHub 代理接入，默认禁用，需手动开启

## 项目结构

```
quantum-news-monitor/
├── app.py                  # Flask 入口（路由 + API）
├── models.py               # SQLite 数据模型
├── scheduler.py            # APScheduler 定时调度
├── reporter.py             # 报告生成（聚合 + 图表配置 + PDF）
├── sources.json            # 25 个信息源配置
├── crawlers/
│   ├── engine.py           # 爬虫引擎（遍历、去重、入库）
│   ├── fetcher.py          # HTTP 请求封装（重试、UA 伪装）
│   └── parsers/
│       ├── base.py         # 通用 HTML 解析器（关键词过滤）
│       └── rss_parsers.py  # RSS/Atom 解析器
├── templates/
│   ├── base.html           # 基础布局
│   ├── dashboard.html      # 仪表盘（7 统计卡片 + 爬取 + 报告生成）
│   ├── crawl.html          # 爬取管理（信息源列表 + 筛选）
│   ├── settings.html       # 设置（频率 / 执行时间）
│   └── report.html         # 报告模板（7 分区 + ECharts 图表）
├── static/
│   ├── css/style.css       # 全局样式
│   └── js/app.js           # 前端交互逻辑
├── data/                   # SQLite 数据库（运行时生成）
├── logs/                   # 爬取日志（运行时生成）
├── reports/                # 生成的报告（运行时生成）
└── pyproject.toml          # 项目配置与依赖
```

## 技术栈

| 层面 | 技术 |
|------|------|
| 语言 | Python 3.12+ |
| Web 框架 | Flask |
| 数据库 | SQLite (WAL 模式) |
| 爬虫 | requests + BeautifulSoup4 + feedparser |
| 调度 | APScheduler |
| 图表 | ECharts (CDN) |
| 前端 | HTML + CSS + JavaScript（无框架） |
| 包管理 | uv + pyproject.toml |

## License

MIT
