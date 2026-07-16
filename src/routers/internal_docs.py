from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse
from pathlib import Path

from core.config import settings
from services.docs import build_nav, mark_active, render_page, search_docs

router = APIRouter(prefix="/internal-docs", tags=["internal-docs"])

_HEAD = """<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{title}</title>
<script src="https://cdn.tailwindcss.com"></script><script>tailwind.config={{darkMode:'class'}}</script>
<script src="https://cdn.jsdelivr.net/npm/@highlightjs/cdn-assets@11.9/highlight.min.js"></script>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@highlightjs/cdn-assets@11.9/styles/github-dark.min.css">
<style>
*{{margin:0;box-sizing:border-box}}body{{background:#030712;color:#e5e7eb;font-family:system-ui,sans-serif}}
.header{{position:fixed;top:0;left:0;right:0;z-50;height:56px;background:#111827;border-bottom:1px solid #1f2937;display:flex;align-items:center;padding:0 16px;gap:16px}}
.header a{{color:#60a5fa;font-weight:600;text-decoration:none}}
.sidebar{{position:fixed;top:56px;left:0;bottom:0;width:256px;background:#111827;border-right:1px solid #1f2937;overflow-y:auto;padding:16px;display:none}}
@media(min-width:1024px){{.sidebar{{display:block}}}}
.sidebar ul{{list-style:none;padding:0}}
.sidebar>ul>li{{margin-bottom:4px}}
.sidebar summary{{cursor:pointer;font-weight:500;color:#d1d5db;padding:4px 0}}
.sidebar summary:hover{{color:#fff}}
.sidebar a{{display:block;padding:2px 0;color:#9ca3af;text-decoration:none;font-size:14px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.sidebar a:hover{{color:#60a5fa}}
.sidebar a.active{{color:#60a5fa;font-weight:500}}
.sidebar ul ul{{margin-left:12px;border-left:1px solid #374151;padding-left:12px;margin-top:2px}}
.main{{padding-top:72px;padding-left:16px;padding-right:16px;max-width:900px;margin:0 auto}}
@media(min-width:1024px){{.main{{margin-left:256px}}}}
.breadcrumb{{padding:12px 0;font-size:13px;color:#6b7280}}
.breadcrumb a{{color:#60a5fa;text-decoration:none}}
.prose pre{{background:#1e293b;border-radius:8px;padding:16px;overflow-x:auto}}
.prose code{{font-size:14px}}
.prose table{{width:100%;border-collapse:collapse;margin:16px 0}}
.prose th,.prose td{{border:1px solid #475569;padding:8px 12px;text-align:left}}
.prose th{{background:#334155;font-weight:600}}
.prose blockquote{{border-left:4px solid #3b82f6;padding-left:16px;color:#94a3b8;margin:12px 0}}
.prose h1{{font-size:28px;font-weight:700;margin:0 0 16px;border-bottom:1px solid #334155;padding-bottom:8px}}
.prose h2{{font-size:22px;font-weight:600;margin:32px 0 12px}}
.prose h3{{font-size:18px;font-weight:600;margin:24px 0 8px}}
.prose ul,.prose ol{{padding-left:24px;margin:8px 0}}
.prose li{{margin-bottom:4px}}
.prose a{{color:#60a5fa}}
.prose p{{margin:8px 0;line-height:1.6}}
.prose hr{{border:0;border-top:1px solid #334155;margin:16px 0}}
.prose .task-item{{margin:4px 0;display:flex;align-items:center;gap:8px}}
.mobile-btn{{background:none;border:none;color:#9ca3af;font-size:24px;cursor:pointer;padding:4px}}
@media(min-width:1024px){{.mobile-btn{{display:none}}}}
.card{{background:#111827;border:1px solid #1f2937;border-radius:12px;padding:16px}}
.card:hover{{border-color:#3b82f6}}
.card-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(250px,1fr));gap:16px;margin-top:24px}}
.card h3{{color:#60a5fa;margin-bottom:4px}}
.card p{{color:#6b7280;font-size:12px}}
.search input{{width:100%;padding:8px 16px;border-radius:8px;background:#1f2937;border:1px solid #374151;color:#e5e7eb;font-size:14px}}
.search input:focus{{outline:none;border-color:#60a5fa}}
mark{{background:#854d0e;color:#fef08a;padding:0 2px;border-radius:2px}}
.result{{padding:12px;background:#111827;border:1px solid #1f2937;border-radius:8px;margin-bottom:8px}}
.result a{{color:#60a5fa;font-weight:500}}
.result .path{{font-size:11px;color:#4b5563}}
</style></head><body>
<div class="header">
<button class="mobile-btn" onclick="document.querySelector('.sidebar').classList.toggle('hidden')">&#9776;</button>
<a href="/internal-docs">Docs</a><div style="flex:1"></div>
<span style="font-size:12px;color:#4b5563">Internal</span>
</div>
<div class="sidebar">{nav}</div>
<main class="main">
<div class="breadcrumb"><a href="/internal-docs">Docs</a>{breadcrumb}</div>
<div class="prose">{content}</div>
</main></body></html>"""

_DISABLED = _HEAD.format(
    title="Disabled", nav="", breadcrumb="", content="<h1>Internal docs are disabled</h1><p>Set <code>ENABLE_INTERNAL_DOCS=true</code>.</p>"
).replace("{nav}", "").replace("{breadcrumb}", "").replace("{content}", "<h1>Internal docs are disabled</h1>")


def _build_nav_html(nav: list[dict]) -> str:
    parts = ['<ul>']
    for item in nav:
        parts.append('<li>')
        if item.get("children"):
            parts.append('<details open><summary>' + item["label"] + '</summary><ul>')
            for child in item["children"]:
                cls = ' class="active"' if child.get("active") else ""
                parts.append(f'<li><a href="{child["url"]}"{cls}>{child["label"]}</a></li>')
            parts.append('</ul></details>')
        else:
            cls = ' class="active"' if item.get("active") else ""
            parts.append(f'<a href="{item["url"]}"{cls}>{item["label"]}</a>')
        parts.append('</li>')
    parts.append('</ul>')
    return "\n".join(parts)


def _build_breadcrumb(crumbs: list[dict]) -> str:
    if not crumbs:
        return ""
    parts = []
    for c in crumbs:
        parts.append('<span style="margin:0 4px">/</span>')
        if c.get("active"):
            parts.append(f'<span>{c["label"]}</span>')
        else:
            parts.append(f'<a href="{c["url"]}">{c["label"]}</a>')
    return "".join(parts)


@router.get("", response_class=HTMLResponse)
async def docs_index(request: Request):
    if not getattr(settings, "ENABLE_INTERNAL_DOCS", False):
        return HTMLResponse(_DISABLED, 403)
    nav = build_nav()
    nav = mark_active(nav, "/internal-docs")
    cards = "".join(
        f'<a class="card" href="{item["url"]}"><h3>{item["label"]}</h3><p>{len(item.get("children",[]))} pages</p></a>'
        if item.get("children")
        else f'<a class="card" href="{item["url"]}"><h3>{item["label"]}</h3></a>'
        for item in nav
    )
    html = _HEAD.format(
        title="Documentation",
        nav=_build_nav_html(nav),
        breadcrumb="",
        content=f'<h1>Ardhang Matrimony &mdash; Internal Documentation</h1><p>Select a page from the sidebar.</p><div class="card-grid">{cards}</div>',
    )
    return HTMLResponse(html)


@router.get("/search", response_class=HTMLResponse)
async def docs_search(request: Request, q: str = Query(default="")):
    if not getattr(settings, "ENABLE_INTERNAL_DOCS", False):
        return HTMLResponse(_DISABLED, 403)
    nav = build_nav()
    results_html = ""
    if q.strip():
        results = search_docs(q)
        results_html = "".join(
            f'<div class="result"><a href="{r["url"]}">{r["title"]}</a><div style="font-size:14px;color:#9ca3af;margin-top:4px">{r["snippet"]}</div><div class="path">{r["path"]}</div></div>'
            for r in results
        ) or f'<p style="color:#6b7280">No results for "{q}".</p>'
    html = _HEAD.format(
        title=f"Search: {q}",
        nav=_build_nav_html(nav),
        breadcrumb='<span style="margin:0 4px">/</span><span>Search</span>',
        content=f'<h1>Search</h1><div class="search"><form action="/internal-docs/search"><input name="q" value="{q}" placeholder="Search docs..."><button type="submit" style="display:none">Search</button></form></div><div style="margin-top:16px">{results_html}</div>',
    )
    return HTMLResponse(html)


@router.get("/{doc_path:path}", response_class=HTMLResponse)
async def docs_page(request: Request, doc_path: str):
    if not getattr(settings, "ENABLE_INTERNAL_DOCS", False):
        return HTMLResponse(_DISABLED, 403)
    page = render_page(doc_path)
    if page is None:
        nav_html = _build_nav_html(build_nav())
        return HTMLResponse(_HEAD.format(
            title="Not Found", nav=nav_html, breadcrumb="",
            content=f'<h1>404</h1><p>The page <code>{doc_path}</code> was not found.</p><p><a href="/internal-docs">Back to docs</a></p>',
        ), 404)
    html = _HEAD.format(
        title=page["title"],
        nav=_build_nav_html(page["nav"]),
        breadcrumb=_build_breadcrumb(page.get("breadcrumbs", [])),
        content=page["content"],
    )
    return HTMLResponse(html)
