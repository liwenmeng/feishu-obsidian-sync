import re
from datetime import datetime, timezone

_INVALID_CHARS = re.compile(r'[\\/:*?"<>|]')


def sanitize_name(name: str) -> str:
    name = _INVALID_CHARS.sub("_", name).strip(". ")
    return name or "未命名"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
