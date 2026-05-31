"""URL validation utilities for AI-generated learning resources."""

import asyncio
import re
import logging
from typing import List, Tuple, Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

URL_PATTERN = re.compile(
    r'^https?://'
    r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'
    r'localhost|'
    r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'
    r'(?::\d+)?'
    r'(?:/?|[/?]\S+)$', re.IGNORECASE)


def is_valid_url_format(url: str) -> bool:
    """Check if URL has valid format (no network call)."""
    if not url or not isinstance(url, str):
        return False
    if not URL_PATTERN.match(url):
        return False
    try:
        result = urlparse(url)
        return all([result.scheme in ('http', 'https'), result.netloc])
    except Exception:
        return False


async def check_url_reachable(
    url: str,
    client: httpx.AsyncClient,
    timeout: float = 5.0
) -> bool:
    """Check if URL is reachable via HEAD request (falls back to GET on 405)."""
    try:
        response = await client.head(url, timeout=timeout, follow_redirects=True)
        if response.status_code < 400:
            return True
        if response.status_code == 405:
            response = await client.get(url, timeout=timeout, follow_redirects=True)
            return response.status_code < 400
        return False
    except (httpx.TimeoutException, httpx.RequestError) as e:
        logger.debug(f"URL unreachable: {url} - {type(e).__name__}")
        return False
    except Exception as e:
        logger.warning(f"Unexpected error checking URL {url}: {e}")
        return False


async def validate_url(
    url: str,
    client: httpx.AsyncClient,
    check_reachable: bool = True,
    timeout: float = 5.0
) -> Tuple[bool, Optional[str]]:
    """Validate a single URL. Returns (is_valid, error_message)."""
    if not is_valid_url_format(url):
        return False, "Invalid URL format"
    if check_reachable:
        if not await check_url_reachable(url, client, timeout):
            return False, "URL not reachable"
    return True, None


async def validate_urls_batch(
    urls: List[str],
    check_reachable: bool = True,
    timeout: float = 5.0,
    max_concurrent: int = 10
) -> dict:
    """Validate multiple URLs concurrently with rate limiting."""
    results = {}
    semaphore = asyncio.Semaphore(max_concurrent)

    async with httpx.AsyncClient(
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": "Landas-URLValidator/1.0"}
    ) as client:
        async def validate_with_semaphore(url: str):
            async with semaphore:
                return url, await validate_url(url, client, check_reachable, timeout)

        tasks = [validate_with_semaphore(url) for url in urls]
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for result in completed:
            if isinstance(result, Exception):
                logger.error(f"Batch validation error: {result}")
                continue
            url, (is_valid, error) = result
            results[url] = (is_valid, error)

    return results


async def filter_valid_resources(
    resources: List[dict],
    url_key: str = "url",
    check_reachable: bool = True,
    timeout: float = 5.0
) -> Tuple[List[dict], List[dict]]:
    """Filter resource dicts, returning (valid_resources, invalid_resources)."""
    if not resources:
        return [], []

    urls = [r.get(url_key, "") for r in resources]
    validation_results = await validate_urls_batch(urls, check_reachable, timeout)

    valid, invalid = [], []
    for resource in resources:
        url = resource.get(url_key, "")
        is_valid, error = validation_results.get(url, (False, "Not validated"))
        if is_valid:
            valid.append(resource)
        else:
            invalid.append({**resource, "_validation_error": error})
            logger.info(f"Filtered invalid resource URL: {url} - {error}")

    return valid, invalid
