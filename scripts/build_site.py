#!/usr/bin/env python3
"""Apply shared chrome and front matter handling to the static site."""

from __future__ import annotations

from pathlib import Path

from layout import apply_document, skip_page, transform, write_sitemap

FIXTURE = """---
title: "Example Title"
canonical: https://blackbelthacker.com/blog/example.html
meta-description: "Defender first notes."
meta-og: https://blackbelthacker.com/logo-square.png
---
<!doctype html>
<html><head><title>Old</title></head><body>
canonical: https://blackbelthacker.com/blog/example.html
meta-description: Defender first notes.
meta-og: https://blackbelthacker.com/logo-square.png
title: Example Title
<main><p>Body stays. A self-hosted read-only check.</p></main>
</body></html>
"""


def check_fixture() -> None:
    out = transform(FIXTURE, Path("blog/example.html"))
    body = out.split("<body", 1)[1]
    if "meta-description" in out or "canonical:" in body or "title: Example" in body:
        raise SystemExit("front matter still visible")
    if "Body stays." not in body:
        raise SystemExit("page body was dropped")
    if "self hosted" not in body or "read only" not in body:
        raise SystemExit("phrase replace missed")
    if 'href="https://www.blackbelthacker.com/blog/example.html"' not in out:
        raise SystemExit("canonical was not written to head")
    if 'content="Defender first notes."' not in out:
        raise SystemExit("description was not written to head")
    if 'property="og:image" content="https://www.blackbelthacker.com/logo-square.png"' not in out:
        raise SystemExit("og image was not written to head")


def main() -> None:
    check_fixture()
    site = Path(__file__).resolve().parents[1]
    pages = [p for p in site.rglob("*.html") if not skip_page(p)]
    for path in pages:
        apply_document(path, site)
    write_sitemap(site)
    print(f"built {len(pages)} pages")


if __name__ == "__main__":
    main()
