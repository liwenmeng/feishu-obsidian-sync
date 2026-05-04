from config import FEISHU_API_BASE, NO_PROXY
from http_client import feishu_get, feishu_paginate, _SESSION

import time

_MIME_TO_EXT: dict[str, str] = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "image/bmp": ".bmp",
}


def get_docx_info(doc_token: str, user_token: str) -> dict:
    url = f"{FEISHU_API_BASE}/docx/v1/documents/{doc_token}"
    return feishu_get(url, user_token)["data"]["document"]


def get_docx_blocks(doc_token: str, user_token: str) -> list[dict]:
    url = f"{FEISHU_API_BASE}/docx/v1/documents/{doc_token}/blocks"
    return feishu_paginate(url, user_token, {"page_size": 500},
                           items_key="items", timeout=15)


def download_image_bytes(file_token: str, user_token: str) -> tuple[bytes, str]:
    url = f"{FEISHU_API_BASE}/drive/v1/medias/{file_token}/download"
    resp = _SESSION.get(url, headers={"Authorization": f"Bearer {user_token}"}, timeout=30, proxies=NO_PROXY)
    resp.raise_for_status()
    content_type = resp.headers.get("Content-Type", "image/png").split(";")[0].strip()
    return resp.content, _MIME_TO_EXT.get(content_type, ".png")


def get_doc_raw_content(doc_token: str, user_token: str) -> str:
    url = f"{FEISHU_API_BASE}/docx/v1/documents/{doc_token}/raw_content"
    return feishu_get(url, user_token, params={"lang": 0}, timeout=15)["data"]["content"]


def export_old_doc(doc_token: str, user_token: str) -> bytes:
    """Export old-format doc (doccn*) to .docx bytes via Feishu export API."""
    # Step 1: create export task
    create_url = f"{FEISHU_API_BASE}/drive/v1/export_tasks"
    resp = _SESSION.post(
        create_url,
        headers={"Authorization": f"Bearer {user_token}"},
        json={"file_extension": "docx", "token": doc_token, "type": "doc"},
        proxies=NO_PROXY,
        timeout=15,
    )
    resp.raise_for_status()
    ticket = resp.json()["data"]["ticket"]

    # Step 2: poll until done
    status_url = f"{FEISHU_API_BASE}/drive/v1/export_tasks/{ticket}"
    for _ in range(20):
        time.sleep(2)
        r = _SESSION.get(
            status_url,
            headers={"Authorization": f"Bearer {user_token}"},
            params={"token": doc_token},
            proxies=NO_PROXY,
            timeout=15,
        )
        r.raise_for_status()
        job = r.json().get("data", {}).get("result", {})
        status = job.get("job_status")
        if status == 0:
            file_token = job["file_token"]
            break
        if status not in (1, 2):
            raise RuntimeError(f"Export failed: {job.get('job_error_msg')}")
    else:
        raise TimeoutError("Export task timed out after 40 seconds")

    # Step 3: download
    dl = _SESSION.get(
        f"{FEISHU_API_BASE}/drive/v1/export_tasks/file/{file_token}/download",
        headers={"Authorization": f"Bearer {user_token}"},
        proxies=NO_PROXY,
        timeout=30,
    )
    dl.raise_for_status()
    return dl.content
