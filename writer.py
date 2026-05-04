import re
from pathlib import Path

from config import OBSIDIAN_VAULT
from fetcher import download_image_bytes
from utils import sanitize_name, utc_now

_IMG_PLACEHOLDER = re.compile(r'!\[\]\(feishu-image://([^)]+)\)')
_EMBEDDED_IMG = re.compile(r'!\[\]\(embedded-image://(\d+\.[a-z]+)\)')
_DOC_LINK = re.compile(r'\[([^\]]*)\]\(feishu-doc://([^)]+)\)')


def process_images(markdown: str, doc_name: str, user_token: str) -> str:
    tokens = _IMG_PLACEHOLDER.findall(markdown)
    if not tokens:
        return markdown

    safe_name = sanitize_name(doc_name)
    attach_dir = Path(OBSIDIAN_VAULT) / "附件" / safe_name
    attach_dir.mkdir(parents=True, exist_ok=True)

    # deduplicated download; None sentinel = failed
    token_to_file: dict[str, str | None] = {}
    for img_token in dict.fromkeys(tokens):
        try:
            content, ext = download_image_bytes(img_token, user_token)
            filename = f"{img_token}{ext}"
            (attach_dir / filename).write_bytes(content)
            token_to_file[img_token] = filename
            print(f"  [图片] {filename}  ({len(content) // 1024 + 1} KB)")
        except Exception as e:
            print(f"  [图片] 下载失败 ({img_token[:12]}...): {e}")
            token_to_file[img_token] = None

    def _replace(m: re.Match) -> str:
        filename = token_to_file.get(m.group(1))
        return f"![[附件/{safe_name}/{filename}]]" if filename else m.group(0)

    return _IMG_PLACEHOLDER.sub(_replace, markdown)


def save_embedded_images(
    markdown: str, images: list[tuple[int, bytes, str]], doc_name: str
) -> str:
    if not images:
        return markdown

    safe_name = sanitize_name(doc_name)
    attach_dir = Path(OBSIDIAN_VAULT) / "附件" / safe_name
    attach_dir.mkdir(parents=True, exist_ok=True)

    idx_to_filename: dict[str, str] = {}
    for idx, img_bytes, ext in images:
        filename = f"img_{idx:03d}{ext}"
        (attach_dir / filename).write_bytes(img_bytes)
        idx_to_filename[f"{idx}{ext}"] = filename
        print(f"  [图片] {filename}  ({len(img_bytes) // 1024 + 1} KB)")

    def _replace(m: re.Match) -> str:
        filename = idx_to_filename.get(m.group(1))
        return f"![[附件/{safe_name}/{filename}]]" if filename else m.group(0)

    return _EMBEDDED_IMG.sub(_replace, markdown)


def resolve_doc_links(record: dict) -> None:
    """Replace feishu-doc://TOKEN placeholders with [[safe_name]] Obsidian links."""

    def _replace(m: re.Match) -> str:
        entry = record.get(m.group(2))
        if entry:
            return f"[[{entry['safe_name']}]]"
        title = m.group(1)
        return f"[[{sanitize_name(title)}]]" if title else m.group(0)

    changed = 0
    for md_file in Path(OBSIDIAN_VAULT).rglob("*.md"):
        text = md_file.read_text(encoding="utf-8")
        new_text = _DOC_LINK.sub(_replace, text)
        if new_text != text:
            md_file.write_text(new_text, encoding="utf-8")
            changed += 1

    print(f"[链接] {changed} 篇文档的互引链接已转换为 Obsidian 内链。")


def write_document(doc_token: str, rel_path: str, markdown: str, feishu_url: str) -> Path:
    parts = [sanitize_name(p) for p in rel_path.split("/")]
    vault = Path(OBSIDIAN_VAULT)
    dir_path = vault.joinpath(*parts[:-1]) if len(parts) > 1 else vault
    dir_path.mkdir(parents=True, exist_ok=True)
    file_path = dir_path / f"{parts[-1]}.md"
    frontmatter = f"---\nfeishu_id: {doc_token}\nlast_sync: {utc_now()}\nsource: {feishu_url}\n---\n\n"
    file_path.write_text(frontmatter + markdown, encoding="utf-8")
    return file_path
