import requests
from config import FEISHU_API_BASE, NO_PROXY

_SESSION = requests.Session()


def feishu_get(url: str, token: str, *, params=None, timeout: int = 10) -> dict:
    resp = _SESSION.get(
        url,
        headers={"Authorization": f"Bearer {token}"},
        params=params,
        timeout=timeout,
        proxies=NO_PROXY,
    )
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Feishu API error [{url}]: {data.get('msg', data)}")
    return data


def feishu_post(url: str, token: str | None = None, *, json=None, timeout: int = 10) -> dict:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    resp = _SESSION.post(url, headers=headers, json=json, timeout=timeout, proxies=NO_PROXY)
    resp.raise_for_status()
    data = resp.json()
    if data.get("code") != 0:
        raise RuntimeError(f"Feishu API error [{url}]: {data.get('msg', data)}")
    return data


def feishu_paginate(
    url: str,
    token: str,
    params: dict,
    *,
    items_key: str,
    next_key: str = "page_token",
    timeout: int = 10,
) -> list:
    """Collect all pages from a Feishu list endpoint."""
    results = []
    page_token = ""
    while True:
        p = {**params, **({"page_token": page_token} if page_token else {})}
        data = feishu_get(url, token, params=p, timeout=timeout)["data"]
        results.extend(data.get(items_key, []))
        if not data.get("has_more"):
            break
        page_token = data[next_key]
    return results
