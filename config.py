import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    val = os.getenv(key)
    if not val:
        raise RuntimeError(f"缺少必要的环境变量：{key}（请检查 .env 文件）")
    return val


APP_ID = _require("FEISHU_APP_ID")
APP_SECRET = _require("FEISHU_APP_SECRET")
ROOT_FOLDER_TOKEN = _require("FEISHU_ROOT_FOLDER_TOKEN")
OBSIDIAN_VAULT = _require("OBSIDIAN_VAULT")

# OAuth 回调地址（必须在飞书开放平台的「重定向 URL」列表中添加相同地址）
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8080/callback")
CALLBACK_PORT = int(os.getenv("CALLBACK_PORT", "8080"))

# 飞书 API 基础地址
FEISHU_API_BASE = "https://open.feishu.cn/open-apis"

# 飞书是国内服务器，所有请求绕过系统代理直连
NO_PROXY = {"http": None, "https": None}

# 本地 token 缓存文件
TOKEN_FILE = os.getenv("TOKEN_FILE", "tokens.json")

# 飞书群机器人 webhook（可选，不填则不发通知）
FEISHU_WEBHOOK_URL = os.getenv("FEISHU_WEBHOOK_URL", "")
