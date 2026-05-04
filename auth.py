import json
import time
import secrets
import webbrowser
import threading
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

from config import APP_ID, APP_SECRET, REDIRECT_URI, FEISHU_API_BASE, TOKEN_FILE, CALLBACK_PORT
from http_client import feishu_post


# ---------- OAuth 回调服务器 ----------

class _CallbackHandler(BaseHTTPRequestHandler):
    auth_code = None
    state_expected = None

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if parsed.path != "/callback":
            self._respond(404, "Not found")
            return

        state = params.get("state", [None])[0]
        if state != _CallbackHandler.state_expected:
            self._respond(400, "State mismatch — please retry.")
            return

        _CallbackHandler.auth_code = params.get("code", [None])[0]
        self._respond(200, "授权成功！可以关闭此窗口，回到终端继续。")

    def _respond(self, status: int, body: str):
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(body.encode("utf-8"))

    def log_message(self, *_):
        pass  # 屏蔽服务器请求日志


# ---------- 飞书 API 调用 ----------

def _get_app_access_token() -> str:
    url = f"{FEISHU_API_BASE}/auth/v3/app_access_token/internal"
    return feishu_post(url, json={"app_id": APP_ID, "app_secret": APP_SECRET})["app_access_token"]


def _exchange_code(code: str, app_access_token: str) -> dict:
    url = f"{FEISHU_API_BASE}/authen/v1/oidc/access_token"
    return feishu_post(url, app_access_token, json={"grant_type": "authorization_code", "code": code})["data"]


def _refresh_token(refresh_token: str, app_access_token: str) -> dict:
    url = f"{FEISHU_API_BASE}/authen/v1/oidc/refresh_access_token"
    return feishu_post(url, app_access_token, json={"grant_type": "refresh_token", "refresh_token": refresh_token})["data"]


# ---------- 本地 token 持久化 ----------

def _save_tokens(token_data: dict):
    token_data["saved_at"] = int(time.time())
    with open(TOKEN_FILE, "w", encoding="utf-8") as f:
        json.dump(token_data, f, indent=2, ensure_ascii=False)
    print(f"[auth] Token 已保存到 {TOKEN_FILE}")


def _load_tokens() -> dict | None:
    p = Path(TOKEN_FILE)
    if not p.exists():
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _is_expired(token_data: dict) -> bool:
    """access_token 是否已过期（提前 5 分钟判定）"""
    expires_at = token_data.get("saved_at", 0) + token_data.get("expires_in", 0)
    return time.time() > expires_at - 300


# ---------- OAuth 浏览器授权流程 ----------

def _run_oauth_flow() -> dict:
    state = secrets.token_urlsafe(16)
    _CallbackHandler.state_expected = state
    _CallbackHandler.auth_code = None

    # 启动本地回调服务器
    server = HTTPServer(("localhost", CALLBACK_PORT), _CallbackHandler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()

    # 构造授权 URL
    params = urllib.parse.urlencode({
        "app_id": APP_ID,
        "redirect_uri": REDIRECT_URI,
        "scope": "docs:doc:readonly docx:document:readonly drive:drive:readonly drive:file:readonly drive:export:readonly",
        "state": state,
    })
    auth_url = f"{FEISHU_API_BASE}/authen/v1/authorize?{params}"

    print("[auth] 正在打开浏览器进行飞书授权...")
    print(f"[auth] 若浏览器未自动打开，请手动访问:\n  {auth_url}\n")
    webbrowser.open(auth_url)

    # 等待回调（最多 120 秒）
    deadline = time.time() + 120
    while _CallbackHandler.auth_code is None:
        if time.time() > deadline:
            server.shutdown()
            raise TimeoutError("[auth] 授权超时（120 秒），请重试。")
        time.sleep(0.5)

    code = _CallbackHandler.auth_code
    server.shutdown()
    print("[auth] 授权码获取成功，正在换取 token...")

    app_token = _get_app_access_token()
    token_data = _exchange_code(code, app_token)
    _save_tokens(token_data)
    return token_data


# ---------- 公开接口 ----------

def get_valid_token() -> str:
    """
    返回有效的 user_access_token。
    - 无本地 token → 触发浏览器 OAuth 授权
    - token 过期   → 自动用 refresh_token 刷新
    - 刷新失败     → 重新触发浏览器授权
    """
    token_data = _load_tokens()

    if token_data is None:
        print("[auth] 未找到本地 token，开始 OAuth 授权流程...")
        token_data = _run_oauth_flow()
    elif _is_expired(token_data):
        print("[auth] access_token 已过期，尝试刷新...")
        try:
            app_token = _get_app_access_token()
            token_data = _refresh_token(token_data["refresh_token"], app_token)
            _save_tokens(token_data)
            print("[auth] Token 刷新成功。")
        except Exception as e:
            print(f"[auth] 刷新失败（{e}），重新授权...")
            token_data = _run_oauth_flow()
    else:
        remaining = token_data.get("saved_at", 0) + token_data.get("expires_in", 0) - int(time.time())
        print(f"[auth] 使用本地缓存 token（剩余有效期 {remaining // 60} 分钟）。")

    return token_data["access_token"]
