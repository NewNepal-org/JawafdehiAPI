import hashlib

from django.core.cache import caches

QUOTA_CACHE_NAME = "public_chat_quota"


def get_client_ip(request) -> str:
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "unknown")


def _quota_identity(config, request, session_id: str) -> str:
    ip = get_client_ip(request)
    if config.quota_scope == "ip":
        return f"ip:{ip}"
    if config.quota_scope == "session":
        return f"session:{session_id or 'missing'}"
    return f"ip_session:{ip}:{session_id or 'missing'}"


def _increment_key(config, identity: str) -> int:
    digest = hashlib.sha256(identity.encode("utf-8")).hexdigest()
    key = f"public_chat_quota:{config.id}:{digest}"
    quota_cache = caches[QUOTA_CACHE_NAME]
    quota_cache.add(key, 0, timeout=config.quota_window_seconds)
    try:
        return quota_cache.incr(key)
    except ValueError:
        quota_cache.set(key, 1, timeout=config.quota_window_seconds)
        return 1


def check_and_increment_quota(config, request, session_id: str) -> dict:
    identity = _quota_identity(config, request, session_id)
    used_values = [_increment_key(config, identity)]
    if config.quota_scope == "ip_session":
        used_values.append(_increment_key(config, f"ip:{get_client_ip(request)}"))

    used = max(used_values)
    remaining = max(config.quota_limit - used, 0)
    return {
        "allowed": used <= config.quota_limit,
        "used": used,
        "remaining": remaining,
        "limit": config.quota_limit,
        "window_seconds": config.quota_window_seconds,
    }
