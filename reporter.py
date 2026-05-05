"""报告生成：数据聚合 + Jinja2 渲染 + ECharts 配置注入 + PDF 导出。"""

import os
import json
import io
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


def generate_report_pdf(start_date: str, end_date: str) -> bytes:
    """
    生成 PDF 报告并返回字节流。

    Args:
        start_date: 开始日期 (YYYY-MM-DD)
        end_date: 结束日期 (YYYY-MM-DD)

    Returns:
        PDF 文件字节流
    """
    _ensure_reports_dir()

    articles = get_articles_by_date_range(start_date, end_date)

    policy_articles = [a for a in articles if a["dimension"] == "policy"]
    industry_articles = [a for a in articles if a["dimension"] == "industry"]
    research_articles = [a for a in articles if a["dimension"] == "research"]

    chart_data = _build_chart_data(articles, start_date, end_date)

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

    # 同时保存 HTML 副本
    filename = f"{start_date}_{end_date}.html"
    filepath = os.path.join(REPORTS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    # 使用 WeasyPrint 生成 PDF
    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html).write_pdf()

        # 保存 PDF 副本
        pdf_filename = f"{start_date}_{end_date}.pdf"
        pdf_filepath = os.path.join(REPORTS_DIR, pdf_filename)
        with open(pdf_filepath, "wb") as f:
            f.write(pdf_bytes)

        return ("pdf", pdf_bytes)
    except Exception as e:
        # Windows 缺少 GTK 库时回退到 HTML
        import logging
        logging.getLogger("reporter").warning(f"WeasyPrint failed ({e}), falling back to HTML")
        return ("html", html.encode("utf-8"))


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
