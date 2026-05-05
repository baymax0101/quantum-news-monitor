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
