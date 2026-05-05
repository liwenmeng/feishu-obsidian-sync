import requests
from config import NO_PROXY


def send_sync_result(webhook_url: str, synced: int, skipped: int, failed: int, elapsed: float) -> None:
    minutes, seconds = divmod(int(elapsed), 60)
    elapsed_str = f"{minutes}m {seconds}s" if minutes else f"{seconds}s"

    if failed == 0:
        icon = "✅"
        status = "同步完成"
    else:
        icon = "⚠️"
        status = "同步完成（含失败）"

    text = (
        f"{icon} 飞书 → Obsidian {status}\n"
        f"更新 {synced} 篇　跳过 {skipped} 篇　失败 {failed} 篇\n"
        f"耗时 {elapsed_str}"
    )

    try:
        resp = requests.post(
            webhook_url,
            json={"msg_type": "text", "content": {"text": text}},
            proxies=NO_PROXY,
            timeout=10,
        )
        resp.raise_for_status()
    except Exception as e:
        print(f"[notify] Webhook 发送失败: {e}")
