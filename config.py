# 飞书应用凭据 — 填入你的 App ID 和 App Secret
APP_ID = "cli_a97c99058af89bd5"
APP_SECRET = "k2ZP49OhABoDmw9X7KBQBf6gcARV8vBZ"

# OAuth 回调地址（必须在飞书开放平台的「重定向 URL」列表中添加相同地址）
REDIRECT_URI = "http://localhost:8080/callback"
CALLBACK_PORT = 8080

# 飞书 API 基础地址
FEISHU_API_BASE = "https://open.feishu.cn/open-apis"

# 飞书是国内服务器，所有请求绕过系统代理直连
NO_PROXY = {"http": None, "https": None}

# 本地 token 缓存文件
TOKEN_FILE = "tokens.json"

# 同步根文件夹 token（飞书链接末段）
ROOT_FOLDER_TOKEN = "fldcnmlZz8UYIkwsfq2khWYo9xf"

# Obsidian vault 本地路径
OBSIDIAN_VAULT = r"D:\obsidian-vault-syn-20260504"
