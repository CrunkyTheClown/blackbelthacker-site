"""Turn page front matter into head tags and apply shared chrome.

Front matter is either a leading --- block or a run of key lines at the
start of <body>. Those lines are removed from the body. Known keys become
<title>, description, canonical, and Open Graph tags.
"""

from __future__ import annotations

import html as html_lib
import re
from pathlib import Path

ORIGIN = "https://www.blackbelthacker.com"
APEX = "https://blackbelthacker.com"
SKIP_NAMES = {"index-v1.html", "index-v2.html"}
FM_KEYS = (
    "title",
    "canonical",
    "meta-description",
    "meta-og",
    "description",
    "date",
    "slug",
    "tags",
    "status",
)
KEY_LINE = re.compile(
    rf"^(?:{'|'.join(FM_KEYS)})\s*:\s*\S.*$",
    re.I,
)
FILE_FM = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.S)
BODY_TEXT_FM = re.compile(r"(<body[^>]*>)\s*([^<]+)", re.I)
BODY_P_FM = re.compile(
    r"(<body[^>]*>)(\s*(?:<p>\s*(?:"
    + "|".join(FM_KEYS)
    + r")\s*:[^<]*</p>\s*){2,})",
    re.I,
)

HEADER = """<!-- site-header -->
<header class="site-header">
  <a class="skip" href="#content">Skip to content</a>
  <div class="inner">
    <a class="brand" href="/">Black Belt Hacker</a>
    <nav aria-label="Site">
      <a href="/products/">Products</a>
      <a href="/services/">Services</a>
      <a href="/blog/">Blog</a>
      <a href="/about/">About</a>
    </nav>
  </div>
</header>
<!-- /site-header -->"""

FOOTER = """<!-- site-footer -->
<footer class="site-footer">
  <div class="inner">
    <nav aria-label="Footer">
      <a href="mailto:n0auth@blackbelthacker.com">n0auth@blackbelthacker.com</a>
      <a href="https://www.instagram.com/blackbelthacker/">Instagram</a>
      <a href="https://medium.com/@n0auth">Medium</a>
      <a href="/legal/refund/">Refund Policy</a>
      <a href="/legal/privacy/">Privacy</a>
      <a href="/legal/terms/">Terms</a>
    </nav>
    <p>© 2026 Black Belt Hacker</p>
  </div>
</footer>
<!-- /site-footer -->"""


def public_url(rel: Path) -> str:
    posix = rel.as_posix()
    if posix == "index.html":
        return ORIGIN + "/"
    if posix.endswith("/index.html"):
        return ORIGIN + "/" + posix[: -len("index.html")]
    return ORIGIN + "/" + posix


def _pairs(block: str) -> dict[str, str]:
    meta: dict[str, str] = {}
    lines = []
    for raw in block.splitlines():
        line = raw.strip()
        if line and line != "---":
            lines.append(line)
    if len(lines) < 2 or not all(KEY_LINE.match(line) for line in lines):
        return {}
    for line in lines:
        key, val = line.split(":", 1)
        meta[key.strip().lower()] = val.strip().strip('"').strip("'")
    return meta


def _file_front_matter(text: str) -> tuple[dict[str, str], str]:
    match = FILE_FM.match(text)
    if not match:
        return {}, text
    return _pairs(match.group(1)), text[match.end() :]


def _body_front_matter(text: str) -> tuple[dict[str, str], str]:
    meta: dict[str, str] = {}
    para = BODY_P_FM.search(text)
    if para:
        meta.update(_pairs(re.sub(r"</?p>", "\n", para.group(2), flags=re.I)))
        text = text[: para.start(2)] + text[para.end(2) :]
    plain = BODY_TEXT_FM.search(text)
    if plain:
        found = _pairs(plain.group(2))
        if found:
            meta.update(found)
            text = text[: plain.start(2)] + text[plain.end(2) :]
    return meta, text


def _esc(value: str) -> str:
    return html_lib.escape(value, quote=True)


def _upsert_name(text: str, name: str, content: str) -> str:
    tag = f'<meta name="{name}" content="{_esc(content)}">'
    pat = rf'<meta\s+name="{re.escape(name)}"\s+content="[^"]*"\s*/?>'
    if re.search(pat, text, re.I):
        return re.sub(pat, tag, text, count=1, flags=re.I)
    return text.replace("</head>", f"  {tag}\n</head>", 1)


def _upsert_prop(text: str, prop: str, content: str) -> str:
    tag = f'<meta property="{prop}" content="{_esc(content)}">'
    pat = rf'<meta\s+property="{re.escape(prop)}"\s+content="[^"]*"\s*/?>'
    if re.search(pat, text, re.I):
        return re.sub(pat, tag, text, count=1, flags=re.I)
    return text.replace("</head>", f"  {tag}\n</head>", 1)


def _upsert_canonical(text: str, url: str) -> str:
    tag = f'<link rel="canonical" href="{_esc(url)}">'
    pat = r'<link\s+rel="canonical"\s+href="[^"]*"\s*/?>'
    if re.search(pat, text, re.I):
        return re.sub(pat, tag, text, count=1, flags=re.I)
    return text.replace("</head>", f"  {tag}\n</head>", 1)


def _title(text: str) -> str:
    match = re.search(r"<title>(.*?)</title>", text, re.S | re.I)
    if not match:
        return "Black Belt Hacker"
    return re.sub(r"\s+", " ", html_lib.unescape(match.group(1))).strip()


def _description(text: str) -> str:
    match = re.search(
        r'<meta\s+name="description"\s+content="([^"]*)"',
        text,
        re.I,
    )
    return html_lib.unescape(match.group(1)) if match else ""


def _set_title(text: str, title: str) -> str:
    if re.search(r"<title>.*?</title>", text, re.S | re.I):
        return re.sub(
            r"<title>.*?</title>",
            f"<title>{_esc(title)}</title>",
            text,
            count=1,
            flags=re.S | re.I,
        )
    return text.replace("</head>", f"  <title>{_esc(title)}</title>\n</head>", 1)


def _apply_meta(text: str, meta: dict[str, str], url: str) -> str:
    if meta.get("title"):
        text = _set_title(text, meta["title"])
    if meta.get("meta-description") or meta.get("description"):
        text = _upsert_name(
            text,
            "description",
            meta.get("meta-description") or meta.get("description", ""),
        )
    text = _upsert_canonical(text, url)
    title = _title(text)
    desc = _description(text)
    text = _upsert_prop(text, "og:site_name", "Black Belt Hacker")
    text = _upsert_prop(text, "og:title", title)
    if desc:
        text = _upsert_prop(text, "og:description", desc)
    text = _upsert_prop(text, "og:url", url)
    kind = "article" if "/blog/" in url and not url.endswith("/blog/") else "website"
    text = _upsert_prop(text, "og:type", kind)
    image = meta.get("meta-og", "")
    if image.startswith("http") and re.search(r"\.(png|jpe?g|webp|gif)(\?|$)", image, re.I):
        text = _upsert_prop(text, "og:image", image.replace(APEX, ORIGIN))
    return text


def _chrome(text: str) -> str:
    text = re.sub(
        r'\s*<nav class="site-nav"[^>]*>.*?</nav>\s*',
        "\n",
        text,
        count=1,
        flags=re.S,
    )
    text = re.sub(
        r"\s*<footer>© 2026 blackbelthacker.com</footer>\s*",
        "\n",
        text,
        count=1,
    )
    text = re.sub(
        r"<!-- site-header -->.*?<!-- /site-header -->",
        HEADER,
        text,
        count=1,
        flags=re.S,
    )
    text = re.sub(
        r"<!-- site-footer -->.*?<!-- /site-footer -->",
        FOOTER,
        text,
        count=1,
        flags=re.S,
    )
    if "<!-- site-header -->" not in text:
        text = re.sub(r"<body([^>]*)>", r"<body\1>\n" + HEADER, text, count=1, flags=re.I)
    if "<!-- site-footer -->" not in text:
        text = re.sub(r"</body>", FOOTER + "\n</body>", text, count=1, flags=re.I)
    if 'href="/site.css"' not in text:
        text = text.replace("</head>", '  <link rel="stylesheet" href="/site.css">\n</head>', 1)
    return text


def _phrases(text: str) -> str:
    return text.replace("self-hosted", "self hosted").replace("read-only", "read only")


def transform(text: str, rel: Path) -> str:
    meta, text = _file_front_matter(text)
    body_meta, text = _body_front_matter(text)
    meta.update(body_meta)
    text = _phrases(text.replace(APEX, ORIGIN))
    text = _apply_meta(text, meta, public_url(rel))
    return _chrome(text)


def skip_page(path: Path) -> bool:
    name = path.name
    return name in SKIP_NAMES or ".bak" in name


def apply_document(path: Path, site: Path | None = None) -> None:
    root = site or path.parents[0]
    if path.parent.name != "blackbelthacker.com" and site is None:
        for parent in path.parents:
            if parent.name == "blackbelthacker.com":
                root = parent
                break
    rel = path.relative_to(root)
    path.write_text(transform(path.read_text(encoding="utf-8"), rel), encoding="utf-8", newline="\n")


def write_sitemap(site: Path) -> None:
    pages = [
        p
        for p in site.rglob("*.html")
        if not skip_page(p) and "_src" not in p.parts and p.suffix.lower() != ".pdf"
    ]
    urls = []
    for path in pages:
        text = path.read_text(encoding="utf-8")
        if 'name="robots" content="noindex' in text:
            continue
        rel = path.relative_to(site)
        url = public_url(rel)
        date = re.search(r"(\d{4}-\d{2}-\d{2})", path.name)
        extra = f"<lastmod>{date.group(1)}</lastmod>" if date else ""
        if url.lower().endswith(".pdf"):
            continue
        urls.append((url, extra))
    urls.sort(key=lambda item: (item[0] != ORIGIN + "/", item[0]))
    body = "\n".join(f"  <url><loc>{url}</loc>{extra}</url>" for url, extra in urls)
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"{body}\n</urlset>\n"
    )
    (site / "sitemap.xml").write_text(xml, encoding="utf-8", newline="\n")
    robots = site / "robots.txt"
    lines = ["User-agent: *", "Allow: /", "", f"Sitemap: {ORIGIN}/sitemap.xml", ""]
    robots.write_text("\n".join(lines), encoding="utf-8", newline="\n")
