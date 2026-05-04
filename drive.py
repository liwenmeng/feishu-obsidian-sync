from config import FEISHU_API_BASE
from http_client import feishu_paginate

DOC_TYPES = {"doc", "docx"}

_SKIP_TYPE_LABELS = {
    "sheet": "表格", "bitable": "多维表格", "mindnote": "思维导图",
    "slides": "幻灯片", "wiki": "知识库页面", "file": "附件文件", "shortcut": "快捷方式",
}


def list_folder(folder_token: str, user_token: str) -> list[dict]:
    url = f"{FEISHU_API_BASE}/drive/v1/files"
    return feishu_paginate(
        url, user_token,
        {"folder_token": folder_token, "page_size": 200},
        items_key="files",
        next_key="next_page_token",
    )


def traverse_tree(folder_token: str, user_token: str, _depth: int = 0, _path: str = "") -> list[dict]:
    docs: list[dict] = []
    indent = "  " * _depth

    for item in list_folder(folder_token, user_token):
        itype = item.get("type", "")
        name = item.get("name", "未命名")
        itoken = item.get("token", "")
        item_path = f"{_path}/{name}" if _path else name

        if itype == "folder":
            print(f"{indent}[目录] {name}/")
            docs.extend(traverse_tree(itoken, user_token, _depth + 1, item_path))
        elif itype in DOC_TYPES:
            print(f"{indent}[文档] [{itype}] {name}")
            print(f"{indent}       token: {itoken}")
            docs.append({
                "token": itoken,
                "name": name,
                "type": itype,
                "path": item_path,
                "folder_token": folder_token,
                "modified_time": item.get("modified_time", ""),
            })
        else:
            print(f"{indent}[跳过] [{_SKIP_TYPE_LABELS.get(itype, itype)}] {name}")

    return docs
