"""Flask 应用入口：路由、API、调度器启动。"""

import os
import logging
import threading
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory

from models import init_db, get_article_counts, get_recent_crawl_logs, get_all_config, set_config
from crawlers.engine import crawl_all
from scheduler import init_scheduler
from reporter import generate_report, generate_report_pdf, list_reports

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

    @app.route("/api/report/pdf", methods=["POST"])
    def api_report_pdf():
        data = request.get_json()
        start_date = data.get("start_date", "")
        end_date = data.get("end_date", "")
        if not start_date or not end_date:
            return jsonify({"error": "请提供开始和结束日期"}), 400
        try:
            from flask import Response
            from urllib.parse import quote
            result_type, result_bytes = generate_report_pdf(start_date, end_date)
            if result_type == "pdf":
                filename_cn = f"量子通信监测报告_{start_date}_{end_date}.pdf"
                filename_ascii = f"report_{start_date}_{end_date}.pdf"
                mimetype = "application/pdf"
            else:
                filename_cn = f"量子通信监测报告_{start_date}_{end_date}.html"
                filename_ascii = f"report_{start_date}_{end_date}.html"
                mimetype = "text/html"
            encoded = quote(filename_cn, safe="")
            return Response(
                result_bytes,
                mimetype=mimetype,
                headers={
                    "Content-Disposition": (
                        f"attachment; filename=\"{filename_ascii}\"; "
                        f"filename*=UTF-8''{encoded}"
                    ),
                },
            )
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route("/api/stats")
    def api_stats():
        counts = get_article_counts()
        return jsonify(counts)

    return app


# --- 启动入口 ---

if __name__ == "__main__":
    import os
    app = create_app()
    debug = os.environ.get("FLASK_ENV") == "development"
    print("\n" + "=" * 50)
    print("  量子通信信息监测平台")
    print("  访问地址: http://127.0.0.1:5000")
    print("=" * 50 + "\n")
    app.run(host="127.0.0.1", port=5000, debug=debug)
