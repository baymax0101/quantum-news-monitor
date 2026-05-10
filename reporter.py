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

    from datetime import timedelta

    # 1. 每日信息量（折线图）— 按维度+区域
    daily_counts = defaultdict(lambda: {
        "policy": 0,
        "industry_domestic": 0, "industry_international": 0,
        "research_domestic": 0, "research_international": 0,
        "hefei": 0,
    })

    for a in articles:
        pt = a.get("publish_time", "") or a.get("crawl_time", "")
        pt = pt[:10]
        if not pt:
            continue
        dim = a.get("dimension", "")
        reg = a.get("region", "domestic")

        if reg == "hefei":
            daily_counts[pt]["hefei"] += 1
        elif dim == "policy":
            daily_counts[pt]["policy"] += 1
        elif dim == "industry":
            key = "industry_domestic" if reg == "domestic" else "industry_international"
            daily_counts[pt][key] += 1
        elif dim == "research":
            key = "research_domestic" if reg == "domestic" else "research_international"
            daily_counts[pt][key] += 1

    sd = datetime.strptime(start_date, "%Y-%m-%d")
    ed = datetime.strptime(end_date, "%Y-%m-%d")
    all_dates = []
    policy_series = []
    ind_dom_series = []
    ind_int_series = []
    res_dom_series = []
    res_int_series = []
    hefei_series = []

    d = sd
    while d <= ed:
        ds = d.strftime("%Y-%m-%d")
        all_dates.append(ds)
        policy_series.append(daily_counts[ds]["policy"])
        ind_dom_series.append(daily_counts[ds]["industry_domestic"])
        ind_int_series.append(daily_counts[ds]["industry_international"])
        res_dom_series.append(daily_counts[ds]["research_domestic"])
        res_int_series.append(daily_counts[ds]["research_international"])
        hefei_series.append(daily_counts[ds]["hefei"])
        d += timedelta(days=1)

    # 2. 维度分布（环形图）— 7 个分类
    cat_counts = Counter()
    for a in articles:
        dim = a.get("dimension", "")
        reg = a.get("region", "domestic")
        if reg == "hefei":
            cat_counts["合肥相关"] += 1
        elif dim == "policy":
            cat_counts["政策动态"] += 1
        elif dim == "industry":
            label = "产业进展(国内)" if reg == "domestic" else "产业进展(国外)"
            cat_counts[label] += 1
        elif dim == "research":
            label = "科研成果(国内)" if reg == "domestic" else "科研成果(国外)"
            cat_counts[label] += 1

    # 3. 来源 Top10（横向柱状图）
    source_counts = Counter(a.get("source_name") for a in articles)
    top_sources = source_counts.most_common(10)

    return {
        "line_dates": json.dumps(all_dates, ensure_ascii=False),
        "line_policy": json.dumps(policy_series),
        "line_ind_dom": json.dumps(ind_dom_series),
        "line_ind_int": json.dumps(ind_int_series),
        "line_res_dom": json.dumps(res_dom_series),
        "line_res_int": json.dumps(res_int_series),
        "line_hefei": json.dumps(hefei_series),
        "pie_data": json.dumps([
            {"name": k, "value": v} for k, v in cat_counts.most_common()
        ], ensure_ascii=False),
        "bar_sources": json.dumps([s[0] for s in reversed(top_sources)], ensure_ascii=False),
        "bar_counts": json.dumps([s[1] for s in reversed(top_sources)]),
    }


def _render_html(start_date, end_date, articles, chart_data, generated_at, extra_context=None):
    """渲染报告 HTML 的通用逻辑。"""
    # 按维度+区域分组
    policy_articles = [a for a in articles if a["dimension"] == "policy" and a.get("region") != "hefei"]
    industry_domestic = [a for a in articles if a["dimension"] == "industry" and a.get("region") == "domestic"]
    industry_international = [a for a in articles if a["dimension"] == "industry" and a.get("region") == "international"]
    research_domestic = [a for a in articles if a["dimension"] == "research" and a.get("region") == "domestic"]
    research_international = [a for a in articles if a["dimension"] == "research" and a.get("region") == "international"]
    # 合肥相关：region=hefei 的所有文章
    hefei_articles = [a for a in articles if a.get("region") == "hefei"]
    # 合肥文章中按维度细分
    hefei_policy = [a for a in hefei_articles if a["dimension"] == "policy"]
    hefei_industry = [a for a in hefei_articles if a["dimension"] == "industry"]
    hefei_research = [a for a in hefei_articles if a["dimension"] == "research"]

    sources_set = set()
    for a in articles:
        if a.get("source_name"):
            sources_set.add(a["source_name"])

    ctx = {
        "start_date": start_date,
        "end_date": end_date,
        "generated_at": generated_at,
        "total": len(articles),
        "policy_count": len(policy_articles),
        "industry_domestic_count": len(industry_domestic),
        "industry_international_count": len(industry_international),
        "research_domestic_count": len(research_domestic),
        "research_international_count": len(research_international),
        "hefei_count": len(hefei_articles),
        "policy_articles": policy_articles,
        "industry_domestic_articles": industry_domestic,
        "industry_international_articles": industry_international,
        "research_domestic_articles": research_domestic,
        "research_international_articles": research_international,
        "hefei_articles": hefei_articles,
        "hefei_policy": hefei_policy,
        "hefei_industry": hefei_industry,
        "hefei_research": hefei_research,
        "sources": sorted(sources_set),
        **chart_data,
    }
    if extra_context:
        ctx.update(extra_context)

    return render_template("report.html", **ctx)


def generate_report(start_date: str, end_date: str) -> str:
    """生成 HTML 报告并保存到文件。"""
    _ensure_reports_dir()

    articles = get_articles_by_date_range(start_date, end_date)
    chart_data = _build_chart_data(articles, start_date, end_date)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = _render_html(start_date, end_date, articles, chart_data, generated_at)

    filename = f"{start_date}_{end_date}.html"
    filepath = os.path.join(REPORTS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    return filename


def generate_report_pdf(start_date: str, end_date: str):
    """生成 PDF 报告，返回 (type, bytes)。"""
    _ensure_reports_dir()

    articles = get_articles_by_date_range(start_date, end_date)
    chart_data = _build_chart_data(articles, start_date, end_date)
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = _render_html(start_date, end_date, articles, chart_data, generated_at)

    # 同时保存 HTML
    filename = f"{start_date}_{end_date}.html"
    filepath = os.path.join(REPORTS_DIR, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)

    # 尝试 WeasyPrint PDF
    try:
        from weasyprint import HTML
        pdf_bytes = HTML(string=html).write_pdf()
        pdf_filename = f"{start_date}_{end_date}.pdf"
        pdf_filepath = os.path.join(REPORTS_DIR, pdf_filename)
        with open(pdf_filepath, "wb") as f:
            f.write(pdf_bytes)
        return ("pdf", pdf_bytes)
    except Exception as e:
        import logging
        logging.getLogger("reporter").warning(f"WeasyPrint failed ({e}), falling back to HTML")
        return ("html", html.encode("utf-8"))


def list_reports() -> list[dict]:
    """列出已生成的报告文件。"""
    _ensure_reports_dir()
    reports = []
    for f in os.listdir(REPORTS_DIR):
        if f.endswith(".html") or f.endswith(".pdf"):
            fpath = os.path.join(REPORTS_DIR, f)
            mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
            reports.append({
                "filename": f,
                "created": mtime.strftime("%Y-%m-%d %H:%M"),
                "size": os.path.getsize(fpath),
            })
    reports.sort(key=lambda r: r["created"], reverse=True)
    return reports
