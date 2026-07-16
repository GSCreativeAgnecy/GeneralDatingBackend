from __future__ import annotations

import os
import re
import time
from pathlib import Path
from typing import Any

from fastapi import Request

_DOCS_DIR = Path(os.environ.get("DOCS_DIR", Path(__file__).parent.parent.parent / "docs"))
_CACHE: dict[str, tuple[float, str]] = {}
_CACHE_TTL = int(os.environ.get("DOCS_CACHE_TTL", "300"))
_NAV_CACHE: tuple[float, list[dict]] | None = None

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+)$", re.MULTILINE)
_CODE_RE = re.compile(r"```(\w*)\n(.*?)```", re.DOTALL)
_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
_ITALIC_RE = re.compile(r"\*(.+?)\*")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]+)\)")
_LIST_RE = re.compile(r"^(\s*[-*+]|\s*\d+\.)\s+(.+)$", re.MULTILINE)
_TABLE_ROW_RE = re.compile(r"^\|(.+)\|$")
_TABLE_SEP_RE = re.compile(r"^\|[\s\-:]+\|$")
_BLOCKQUOTE_RE = re.compile(r"^>\s?(.+)$", re.MULTILINE)
_HR_RE = re.compile(r"^[-*_]{3,}$", re.MULTILINE)
_TASK_RE = re.compile(r"^[-*+]\s+\[([ xX])\]\s+(.+)$", re.MULTILINE)

_LABEL_MAP = {
    "index": "Overview",
    "getting-started": "Getting Started",
    "architecture": "Architecture",
    "database": "Database",
    "security": "Security",
    "deployment": "Deployment",
    "development": "Development",
    "coding-standards": "Coding Standards",
    "migrations": "Migrations",
    "troubleshooting": "Troubleshooting",
    "changelog": "Changelog",
    "api/authentication": "Authentication",
    "api/profiles": "Profiles",
    "api/matching": "Matching",
    "api/messaging": "Messaging",
    "api/subscriptions": "Subscriptions",
    "api/admin": "Admin",
}

_NAV_ORDER = [
    ("getting-started", "Getting Started"),
    ("architecture", "Architecture"),
    ("database", "Database Schema"),
    ("api", "API Reference", ["authentication", "profiles", "matching", "messaging", "subscriptions", "admin"]),
    ("security", "Security"),
    ("deployment", "Deployment"),
    ("development", "Development"),
    ("coding-standards", "Coding Standards"),
    ("migrations", "Migrations"),
    ("troubleshooting", "Troubleshooting"),
    ("changelog", "Changelog"),
]


def _render_markdown(text: str) -> str:
    lines = text.split("\n")
    html: list[str] = []
    in_list = False
    in_code_block = False
    code_lang = ""
    code_lines: list[str] = []
    in_table = False
    table_rows: list[list[str]] = []
    table_header = True

    def flush_list() -> None:
        nonlocal in_list
        if in_list:
            html.append("</ul>" if not _last_ol else "</ol>")
            in_list = False

    def flush_table() -> None:
        nonlocal in_table, table_rows, table_header
        if in_table and table_rows:
            html.append("<table>")
            for ri, row in enumerate(table_rows):
                html.append("<thead>" if ri == 0 and table_header else "<tr>")
                tag = "th" if ri == 0 and table_header else "td"
                for cell in row:
                    html.append(f"<{tag}>{cell.strip()}</{tag}>")
                html.append("</thead>" if ri == 0 and table_header else "</tr>")
            html.append("</table>")
            in_table = False
            table_rows = []
            table_header = True

    def flush_code() -> str:
        nonlocal in_code_block, code_lang, code_lines
        lang_attr = f' class="language-{code_lang}"' if code_lang else ""
        escaped = _escape_html("\n".join(code_lines))
        result = f'<div class="code-block-wrapper"><pre><code{lang_attr}>{escaped}</code></pre><button class="copy-btn">Copy</button></div>'
        in_code_block = False
        code_lang = ""
        code_lines = []
        return result

    _last_ol = False

    for line in lines:
        if in_code_block:
            if line.strip() == "```":
                html.append(flush_code())
                continue
            code_lines.append(line)
            continue

        if line.strip().startswith("```"):
            flush_list()
            flush_table()
            in_code_block = True
            code_lang = line.strip()[3:].strip()
            code_lines = []
            continue

        if _HR_RE.match(line.strip()):
            flush_list()
            flush_table()
            html.append("<hr>")
            continue

        if _TABLE_SEP_RE.match(line.strip()):
            table_header = False
            continue

        tm = _TABLE_ROW_RE.match(line.strip())
        if tm:
            flush_list()
            if not in_table:
                in_table = True
                table_rows = []
            cells = [c.strip() for c in tm.group(1).split("|")]
            table_rows.append(cells)
            continue
        elif in_table:
            flush_table()

        bm = _BLOCKQUOTE_RE.match(line)
        if bm:
            flush_list()
            html.append(f"<blockquote>{_render_inline(bm.group(1))}</blockquote>")
            continue

        hx = _HEADING_RE.match(line.strip())
        if hx:
            flush_list()
            flush_table()
            level = len(hx.group(1))
            text_content = _render_inline(hx.group(2))
            slug = _slugify(hx.group(2))
            html.append(f'<h{level} id="{slug}"><a href="#{slug}" class="heading-anchor">#</a> {text_content}</h{level}>')
            continue

        task = _TASK_RE.match(line)
        if task:
            flush_list()
            checked = ' checked' if task.group(1).lower() == 'x' else ''
            html.append(f'<div class="task-item"><input type="checkbox"{checked} disabled> {_render_inline(task.group(2))}</div>')
            continue

        lm = _LIST_RE.match(line)
        if lm:
            is_ol = lm.group(1).strip()[0].isdigit()
            if not in_list or _last_ol != is_ol:
                flush_list()
                in_list = True
                _last_ol = is_ol
                html.append("<ol>" if is_ol else "<ul>")
            html.append(f"<li>{_render_inline(lm.group(2))}</li>")
            continue
        elif in_list:
            flush_list()

        stripped = line.strip()
        if not stripped:
            flush_list()
            flush_table()
            continue

        flush_list()
        html.append(f"<p>{_render_inline(stripped)}</p>")

    flush_list()
    flush_table()
    if in_code_block:
        html.append(flush_code())

    return "\n".join(html)


def _render_inline(text: str) -> str:
    text = _escape_html(text)
    text = _IMAGE_RE.sub(r'<img src="\2" alt="\1" class="rounded max-w-full my-2">', text)
    text = _LINK_RE.sub(r'<a href="\2">\1</a>', text)
    text = _BOLD_RE.sub(r"<strong>\1</strong>", text)
    text = _ITALIC_RE.sub(r"<em>\1</em>", text)
    text = _INLINE_CODE_RE.sub(r'<code class="bg-gray-800 px-1 py-0.5 rounded text-yellow-300 text-sm">\1</code>', text)
    return text


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _slugify(text: str) -> str:
    return re.sub(r"[^\w\- ]", "", text.lower()).strip().replace(" ", "-")


def _resolve_path(doc_path: str) -> Path:
    clean = doc_path.strip("/")
    if not clean:
        clean = "index"
    md = _DOCS_DIR / f"{clean}.md"
    if md.exists():
        return md
    d = _DOCS_DIR / clean
    if d.is_dir() and (d / "index.md").exists():
        return d / "index.md"
    return md


def _path_to_route(doc_path: str) -> str:
    clean = doc_path.strip("/")
    if not clean or clean == "index":
        return "/internal-docs"
    return f"/internal-docs/{clean}"


def _path_to_label(file_path: str) -> str:
    key = file_path.replace("\\", "/").removesuffix(".md")
    if key in _LABEL_MAP:
        return _LABEL_MAP[key]
    if "/" in key:
        return key.rsplit("/", 1)[-1].replace("-", " ").title()
    return key.replace("-", " ").title()


def build_nav() -> list[dict]:
    global _NAV_CACHE
    now = time.time()
    if _NAV_CACHE and now - _NAV_CACHE[0] < _CACHE_TTL:
        return _NAV_CACHE[1]

    nav: list[dict] = []
    for entry in _NAV_ORDER:
        if len(entry) == 3:
            key, label, children_keys = entry
            children = []
            for ck in children_keys:
                child_key = f"api/{ck}"
                child_path = f"api/{ck}.md"
                if (_DOCS_DIR / child_path).exists():
                    children.append({
                        "label": _LABEL_MAP.get(child_key, ck.replace("-", " ").title()),
                        "url": _path_to_route(child_key),
                        "active": False,
                    })
            if children:
                nav.append({"label": label, "children": children, "url": f"/internal-docs/{key}"})
        else:
            key, label = entry
            path = f"{key}.md"
            if (_DOCS_DIR / path).exists():
                nav.append({"label": label, "url": _path_to_route(key)})

    _NAV_CACHE = (now, nav)
    return nav


def mark_active(nav: list[dict], current_path: str) -> list[dict]:
    for item in nav:
        if item.get("url") == current_path:
            item["active"] = True
        for child in item.get("children", []):
            if child.get("url") == current_path:
                child["active"] = True
    return nav


def build_breadcrumbs(doc_path: str) -> list[dict]:
    clean = doc_path.strip("/")
    if not clean:
        return []
    parts = clean.split("/")
    crumbs = []
    accumulated = ""
    for i, part in enumerate(parts):
        accumulated = f"{accumulated}/{part}" if accumulated else part
        label = _LABEL_MAP.get(accumulated, part.replace("-", " ").title())
        crumbs.append({"label": label, "url": _path_to_route(accumulated), "active": i == len(parts) - 1})
    return crumbs


def get_page_title(doc_path: str) -> str:
    clean = doc_path.strip("/")
    if not clean:
        return "Overview"
    return _LABEL_MAP.get(clean, clean.rsplit("/", 1)[-1].replace("-", " ").title())


def render_page(doc_path: str) -> dict[str, Any]:
    md_file = _resolve_path(doc_path)
    if not md_file.exists():
        return None

    mtime = md_file.stat().st_mtime
    cache_key = str(md_file)
    now = time.time()
    if cache_key in _CACHE and now - _CACHE[cache_key][0] < _CACHE_TTL:
        content = _CACHE[cache_key][1]
    else:
        raw = md_file.read_text(encoding="utf-8")
        content = _render_markdown(raw)
        _CACHE[cache_key] = (now, content)

    page_path = _path_to_route(doc_path)
    nav = build_nav()
    nav = mark_active(nav, page_path)

    return {
        "title": get_page_title(doc_path),
        "content": content,
        "nav": nav,
        "breadcrumbs": build_breadcrumbs(doc_path),
        "last_updated": mtime,
    }


def search_docs(query: str) -> list[dict]:
    if not query or len(query.strip()) < 2:
        return []
    q = query.strip().lower()
    results: list[dict] = []

    for md_file in _DOCS_DIR.rglob("*.md"):
        rel = str(md_file.relative_to(_DOCS_DIR)).replace("\\", "/")
        route_key = rel.removesuffix(".md")
        if route_key.endswith("/index"):
            route_key = route_key[:-6]

        name_match = q in route_key.lower() or q in _path_to_label(route_key).lower()

        try:
            text = md_file.read_text(encoding="utf-8")
        except Exception:
            continue

        if name_match or q in text.lower():
            lines = text.split("\n")
            title = get_page_title(route_key)
            snippet = ""
            for i, line in enumerate(lines):
                if q in line.lower():
                    start = max(0, i - 1)
                    end = min(len(lines), i + 2)
                    snippet_lines = lines[start:end]
                    snippet = " ... ".join(
                        s.strip()[:120] for s in snippet_lines if s.strip()
                    )
                    snippet = re.sub(
                        f"({re.escape(q)})",
                        r"<mark>\1</mark>",
                        snippet,
                        flags=re.IGNORECASE,
                    )
                    break

            results.append({
                "title": title,
                "url": _path_to_route(route_key),
                "path": rel,
                "snippet": snippet or text[:200],
            })

    results.sort(key=lambda r: 0 if q in r["title"].lower() else 1)
    return results[:20]


def invalidate_cache() -> None:
    global _NAV_CACHE
    _CACHE.clear()
    _NAV_CACHE = None
