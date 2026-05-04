import io
import urllib.parse

from docx import Document
from docx.oxml.ns import qn


_DOCX_MIME_TO_EXT: dict[str, str] = {
    "image/png": ".png", "image/jpeg": ".jpg", "image/gif": ".gif",
    "image/webp": ".webp", "image/bmp": ".bmp",
}

_HEADING_STYLES = {
    "heading 1": "#", "heading 2": "##", "heading 3": "###",
    "heading 4": "####", "heading 5": "#####", "heading 6": "######",
}


def docx_bytes_to_markdown(docx_bytes: bytes) -> tuple[str, list[tuple[int, bytes, str]]]:
    """Convert exported .docx bytes to (markdown_str, [(idx, img_bytes, ext), ...])."""
    doc = Document(io.BytesIO(docx_bytes))
    lines: list[str] = []
    images: list[tuple[int, bytes, str]] = []
    img_counter = 0

    for para in doc.paragraphs:
        parts: list[str] = []

        for run in para.runs:
            # detect inline images via XML drawing element
            for blip in run.element.iter(qn("a:blip")):
                rId = blip.get(qn("r:embed"))
                if not rId:
                    continue
                rel = doc.part.rels.get(rId)
                if rel is None or "image" not in rel.reltype:
                    continue
                img_counter += 1
                ext = _DOCX_MIME_TO_EXT.get(rel.target_part.content_type, ".png")
                images.append((img_counter, rel.target_part.blob, ext))
                parts.append(f"![](embedded-image://{img_counter}{ext})")

            if not run.text:
                continue
            text = run.text
            if run.bold and run.italic:
                text = f"***{text}***"
            elif run.bold:
                text = f"**{text}**"
            elif run.italic:
                text = f"*{text}*"
            parts.append(text)

        line = "".join(parts)
        if not line.strip() and not any("embedded-image" in p for p in parts):
            lines.append("")
            continue

        style = para.style.name.lower() if para.style else ""
        prefix = _HEADING_STYLES.get(style, "")
        if prefix:
            lines.append(f"{prefix} {line}")
        elif "list bullet" in style:
            lines.append(f"- {line}")
        elif "list number" in style:
            lines.append(f"1. {line}")
        else:
            lines.append(line)

    # collapse >2 consecutive blank lines to 1
    import re
    markdown = re.sub(r"\n{3,}", "\n\n", "\n".join(lines))
    return markdown, images

_CODE_LANG: dict[int, str] = {
    1: "", 7: "bash", 8: "csharp", 9: "cpp", 10: "c", 12: "css",
    13: "coffeescript", 18: "dockerfile", 22: "go", 24: "html", 28: "json",
    29: "java", 30: "javascript", 32: "kotlin", 38: "makefile",
    39: "markdown", 43: "php", 46: "powershell", 49: "python", 50: "r",
    52: "ruby", 53: "rust", 55: "scss", 56: "sql", 57: "scala",
    60: "shell", 61: "swift", 63: "typescript", 66: "xml", 67: "yaml",
    68: "cmake", 69: "diff", 71: "graphql", 75: "toml",
}


def _render_inline(elements: list[dict]) -> str:
    parts: list[str] = []
    for el in elements:
        if "text_run" in el:
            run = el["text_run"]
            text = run.get("content", "")
            style = run.get("text_element_style", {})
            # inline_code cannot combine with bold/italic in Markdown
            if style.get("inline_code"):
                parts.append(f"`{text}`")
                continue
            if style.get("bold"):
                text = f"**{text}**"
            if style.get("italic"):
                text = f"*{text}*"
            if style.get("strikethrough"):
                text = f"~~{text}~~"
            link_url = style.get("link", {}).get("url", "")
            if link_url:
                text = f"[{text}]({urllib.parse.unquote(link_url)})"
            parts.append(text)
        elif "mention_doc" in el:
            md = el["mention_doc"]
            title, token = md.get("title", ""), md.get("token", "")
            # resolved to [[title]] by resolve_doc_links after full sync
            parts.append(f"[{title}](feishu-doc://{token})" if title else "")
        elif "mention_user" in el:
            name = el["mention_user"].get("name", "")
            if name:
                parts.append(f"@{name}")
    return "".join(parts)


def _render_block(block: dict, by_id: dict, depth: int) -> str:
    btype = block.get("block_type", 0)
    children = block.get("children", [])

    if btype == 1:
        return _render_kids(children, by_id, 0)

    if btype == 2:
        # empty paragraph returns "" so _render_kids produces a blank line
        return _render_inline(block.get("text", {}).get("elements", []))

    if 3 <= btype <= 11:
        level = btype - 2
        inline = _render_inline(block.get(f"heading{level}", {}).get("elements", []))
        return f"{'#' * min(level, 6)} {inline}"

    if btype in (12, 13):
        key, marker = ("bullet", "- ") if btype == 12 else ("ordered", "1. ")
        inline = _render_inline(block.get(key, {}).get("elements", []))
        result = f"{'  ' * depth}{marker}{inline}"
        if children:
            result += "\n" + _render_kids(children, by_id, depth + 1)
        return result

    if btype == 14:
        code_data = block.get("code", {})
        lang = _CODE_LANG.get(code_data.get("style", {}).get("language", 1), "")
        code_text = "".join(
            el.get("text_run", {}).get("content", "") for el in code_data.get("elements", [])
        )
        return f"```{lang}\n{code_text}\n```"

    if btype == 15:
        return f"> {_render_inline(block.get('quote', {}).get('elements', []))}"

    if btype == 16:
        todo_data = block.get("todo", {})
        check = "x" if todo_data.get("style", {}).get("done") else " "
        return f"- [{check}] {_render_inline(todo_data.get('elements', []))}"

    if btype == 18:
        emoji = block.get("callout", {}).get("emoji_id", "")
        child_md = _render_kids(children, by_id, 0)
        quoted = "\n".join(f"> {line}" for line in child_md.splitlines())
        return (f"> {emoji}\n" if emoji else "") + quoted

    if btype == 19:
        return "---"

    if btype == 27:
        return f"![](feishu-image://{block.get('image', {}).get('token', '')})"

    if btype == 28:
        return _render_table(block, by_id)

    if btype == 31:
        child_md = _render_kids(children, by_id, 0)
        return "\n".join(f"> {line}" for line in child_md.splitlines())

    return _render_kids(children, by_id, depth) if children else ""


def _render_kids(block_ids: list[str], by_id: dict, depth: int) -> str:
    parts = [_render_block(by_id[bid], by_id, depth) for bid in block_ids if bid in by_id]
    # nested list children must not be separated by blank lines or the list breaks
    sep = "\n" if depth > 0 else "\n\n"
    return sep.join(p for p in parts if p != "")


def _render_table(table_block: dict, by_id: dict) -> str:
    prop = table_block.get("table", {}).get("property", {})
    rows, cols = prop.get("row_size", 0), prop.get("column_size", 0)
    cell_ids = table_block.get("children", [])
    if not rows or not cols or not cell_ids:
        return ""

    grid = []
    for r in range(rows):
        row = []
        for c in range(cols):
            idx = r * cols + c
            if idx < len(cell_ids):
                cell = by_id.get(cell_ids[idx], {})
                text = _render_kids(cell.get("children", []), by_id, 0)
                text = text.replace("\n", " ").replace("|", "\\|")
            else:
                text = ""
            row.append(text)
        grid.append(row)

    lines = [
        "| " + " | ".join(grid[0]) + " |",
        "| " + " | ".join("---" for _ in range(cols)) + " |",
    ]
    lines += ["| " + " | ".join(row) + " |" for row in grid[1:]]
    return "\n".join(lines)


def blocks_to_markdown(blocks: list[dict]) -> str:
    if not blocks:
        return ""
    by_id = {b["block_id"]: b for b in blocks}
    root = next((b for b in blocks if b.get("block_type") == 1), None)
    return _render_block(root, by_id, 0) if root else ""
