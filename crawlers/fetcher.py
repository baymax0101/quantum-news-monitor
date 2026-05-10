"""HTTP 请求封装：超时、重试、UA 伪装。"""

import time
import logging
import requests
from typing import Optional

logger = logging.getLogger("crawler.fetcher")


USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
]

HEADERS_TEMPLATE = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Cache-Control": "max-age=0",
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

    session = requests.Session()
    # 使用适配器处理连接池和重试
    adapter = requests.adapters.HTTPAdapter(
        pool_connections=10,
        pool_maxsize=10,
        max_retries=0,  # 我们自己处理重试
    )
    session.mount("http://", adapter)
    session.mount("https://", adapter)

    for attempt in range(max_retries + 1):
        headers = {
            **HEADERS_TEMPLATE,
            "User-Agent": random.choice(USER_AGENTS),
        }
        try:
            resp = session.get(
                url,
                headers=headers,
                timeout=(5, timeout),  # (connect timeout, read timeout)
                allow_redirects=True,
                verify=True,
            )
            resp.raise_for_status()

            if encoding:
                resp.encoding = encoding
            elif resp.apparent_encoding:
                resp.encoding = resp.apparent_encoding

            session.close()
            return resp.text

        except requests.exceptions.Timeout:
            logger.warning(f"Timeout fetching {url} (attempt {attempt + 1}/{max_retries + 1})")
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "unknown"
            logger.warning(f"HTTP {status} fetching {url} (attempt {attempt + 1}/{max_retries + 1})")
            if status == 404:
                session.close()
                return None  # 404 不重试
        except requests.exceptions.SSLError as e:
            logger.warning(f"SSL error fetching {url}: {e} (attempt {attempt + 1}/{max_retries + 1})")
            if attempt == max_retries:
                # 最后一次尝试忽略SSL验证
                try:
                    resp = session.get(
                        url,
                        headers=headers,
                        timeout=(5, timeout),
                        allow_redirects=True,
                        verify=False,
                    )
                    resp.raise_for_status()
                    if encoding:
                        resp.encoding = encoding
                    elif resp.apparent_encoding:
                        resp.encoding = resp.apparent_encoding
                    session.close()
                    return resp.text
                except Exception:
                    pass
        except requests.exceptions.ConnectionError as e:
            # 检测底层是否为 SSL 错误（urllib3 的 MaxRetryError 可能包裹 SSLError）
            is_ssl_error = any(
                tag in str(e).lower()
                for tag in ("ssl", "certificate", "sslcertverificationerror")
            )
            if is_ssl_error and attempt == max_retries:
                try:
                    resp = session.get(
                        url,
                        headers=headers,
                        timeout=(5, timeout),
                        allow_redirects=True,
                        verify=False,
                    )
                    resp.raise_for_status()
                    if encoding:
                        resp.encoding = encoding
                    elif resp.apparent_encoding:
                        resp.encoding = resp.apparent_encoding
                    session.close()
                    return resp.text
                except Exception:
                    pass
            logger.warning(f"Connection error fetching {url}: {e} (attempt {attempt + 1}/{max_retries + 1})")
        except Exception as e:
            logger.warning(f"Error fetching {url}: {e} (attempt {attempt + 1}/{max_retries + 1})")

        if attempt < max_retries:
            time.sleep(delay * (attempt + 1))

    session.close()
    logger.error(f"Failed to fetch {url} after {max_retries + 1} attempts")
    return None
