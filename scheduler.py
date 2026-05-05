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
