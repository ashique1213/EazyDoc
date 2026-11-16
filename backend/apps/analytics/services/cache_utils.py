import hashlib
import json
from typing import Any, Callable, Optional
from django.core.cache import cache
import logging

logger = logging.getLogger("apps.analytics")

ANALYTICS_CACHE_TTL = 180  # 3 minutes default TTL


def generate_cache_key(prefix: str, scope: str, params: dict) -> str:
    """
    Generates a deterministic Redis cache key based on tenant scope and query parameters.
    Example: eazydoc:analytics:admin:overview:a1b2c3d4...
    """
    sorted_items = sorted(params.items(), key=lambda x: x[0])
    raw_str = json.dumps(sorted_items, default=str)
    hashed = hashlib.sha256(raw_str.encode("utf-8")).hexdigest()[:16]
    return f"eazydoc:analytics:{scope}:{prefix}:{hashed}"


def get_cached_or_compute(
    cache_key: str,
    compute_fn: Callable[[], Any],
    ttl: int = ANALYTICS_CACHE_TTL,
    bypass_cache: bool = False,
) -> Any:
    """
    Retrieves cached analytics result or executes compute function and caches output.
    """
    if not bypass_cache:
        try:
            cached_val = cache.get(cache_key)
            if cached_val is not None:
                return cached_val
        except Exception as e:
            logger.warning(f"Cache retrieval failed for key {cache_key}: {e}")

    result = compute_fn()

    try:
        cache.set(cache_key, result, timeout=ttl)
    except Exception as e:
        logger.warning(f"Cache write failed for key {cache_key}: {e}")

    return result
