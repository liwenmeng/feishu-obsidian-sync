import time
import requests
from auth import get_valid_token
from drive import traverse_tree
from fetcher import get_docx_blocks, get_doc_raw_content, export_old_doc
from converter import blocks_to_markdown, docx_bytes_to_markdown
from writer import write_document, process_images, save_embedded_images, resolve_doc_links
from sync_record import load, save, needs_sync, register_all, mark_synced
from config import ROOT_FOLDER_TOKEN, FEISHU_WEBHOOK_URL
from notify import send_sync_result


def sync_one(doc: dict, user_token: str, record: dict) -> bool:
    print(f"\n  同步: {doc['name']}")
    feishu_url = f"https://my.feishu.cn/docx/{doc['token']}"

    try:
        if doc["type"] == "docx":
            blocks = get_docx_blocks(doc["token"], user_token)
            markdown = blocks_to_markdown(blocks)
            markdown = process_images(markdown, doc["name"], user_token)
        elif doc["type"] == "doc":
            docx_bytes = export_old_doc(doc["token"], user_token)
            markdown, images = docx_bytes_to_markdown(docx_bytes)
            markdown = save_embedded_images(markdown, images, doc["name"])
        else:
            markdown = get_doc_raw_content(doc["token"], user_token)
    except requests.exceptions.HTTPError as e:
        print(f"  [跳过] HTTP错误（{e.response.status_code}），文档可能为旧格式或无权限: {doc['name']}")
        return False

    write_document(doc_token=doc["token"], rel_path=doc["path"],
                   markdown=markdown, feishu_url=feishu_url)
    mark_synced(doc, record)


if __name__ == "__main__":
    _start = time.time()
    token = get_valid_token()
    record = load()

    print(f"\n遍历文件夹 {ROOT_FOLDER_TOKEN}...\n")
    docs = traverse_tree(ROOT_FOLDER_TOKEN, token)

    if not docs:
        print("未找到任何文档。")
        raise SystemExit

    register_all(docs, record)

    synced = skipped = failed = 0
    for doc in docs:
        if needs_sync(doc, record):
            if sync_one(doc, token, record) is False:
                failed += 1
            else:
                synced += 1
        else:
            print(f"  跳过（未修改）: {doc['name']}")
            skipped += 1

    if synced > 0:
        resolve_doc_links(record)
    save(record)

    elapsed = time.time() - _start
    print(f"\n{'='*50}")
    print(f"同步完成：更新 {synced} 篇，跳过 {skipped} 篇，失败 {failed} 篇。")

    if FEISHU_WEBHOOK_URL:
        send_sync_result(FEISHU_WEBHOOK_URL, synced, skipped, failed, elapsed)
