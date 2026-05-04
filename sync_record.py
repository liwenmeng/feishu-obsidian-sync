import json
from pathlib import Path

from utils import sanitize_name, utc_now

SYNC_RECORD_FILE = "sync_record.json"


def load() -> dict:
    p = Path(SYNC_RECORD_FILE)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


def save(record: dict) -> None:
    Path(SYNC_RECORD_FILE).write_text(
        json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def needs_sync(doc: dict, record: dict) -> bool:
    entry = record.get(doc["token"])
    if entry is None:
        return True
    return doc.get("modified_time", "") != entry.get("modified_time", "")


def register_all(docs: list[dict], record: dict) -> None:
    """Pre-populate name/safe_name/path for all docs so link resolution works
    even for docs skipped this run."""
    for doc in docs:
        entry = record.setdefault(doc["token"], {})
        entry["name"] = doc["name"]
        entry["safe_name"] = sanitize_name(doc["name"])
        entry["path"] = doc["path"]


def mark_synced(doc: dict, record: dict) -> None:
    record[doc["token"]]["modified_time"] = doc.get("modified_time", "")
    record[doc["token"]]["last_sync"] = utc_now()
