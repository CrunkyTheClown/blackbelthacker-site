#!/usr/bin/env python3
"""Publish an approved BBH queue pack to blackbelthacker.com/blog.

Requires an APPROVE file in the pack whose first line equals the slug,
or --force after David approved in chat this turn.

Does not publish to Medium by itself. It prints the canonical URL for
Medium import and writes medium-import.md with the exact steps.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
QUEUE = ROOT / "content" / "blog" / "queue"
PUBLISHED = ROOT / "content" / "blog" / "published"
SITE_BLOG = ROOT / "sites" / "blackbelthacker.com" / "blog"
PROGRESS = ROOT / "agents" / "bbh-news" / "PROGRESS.md"

PROJECT = "thomsen-kanban-2611"
ZONE = "us-east1-b"
INSTANCE = "kanban"


def read_status(pack: Path) -> dict:
    path = pack / "STATUS.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_status(pack: Path, data: dict) -> None:
    (pack / "STATUS.json").write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def assert_approved(pack: Path, slug: str, force: bool) -> None:
    approve = pack / "APPROVE"
    if force:
        return
    if not approve.exists():
        raise SystemExit(
            "Refuse: no APPROVE file. David must approve this slug first."
        )
    first = approve.read_text(encoding="utf-8").strip().splitlines()[0].strip()
    if first != slug:
        raise SystemExit(
            f"Refuse: APPROVE slug mismatch ({first!r} != {slug!r})."
        )


def rebuild_index() -> None:
    posts = []
    for html in sorted(SITE_BLOG.glob("2026-*.html"), reverse=True):
        text = html.read_text(encoding="utf-8")
        title_m = re.search(r"<h1>(.*?)</h1>", text, re.S)
        meta_m = re.search(r'<div class="meta">(.*?)</div>', text, re.S)
        title = (
            re.sub(r"\s+", " ", title_m.group(1)).strip()
            if title_m
            else html.stem
        )
        meta = (
            re.sub(r"\s+", " ", meta_m.group(1)).strip() if meta_m else ""
        )
        posts.append((html.name, title, meta))
    # Keep existing index styles if present; otherwise write a minimal list.
    index_path = SITE_BLOG / "index.html"
    if index_path.exists():
        base = index_path.read_text(encoding="utf-8")
        items = "\n".join(
            f'      <li><a href="{name}">{title}</a><span>{meta}</span></li>'
            for name, title, meta in posts
        )
        new = re.sub(
            r"<ul class=\"posts\">.*?</ul>",
            f'<ul class="posts">\n{items}\n    </ul>',
            base,
            count=1,
            flags=re.S,
        )
        index_path.write_text(new, encoding="utf-8", newline="\n")


def commit_and_push(slug: str, title: str) -> None:
    """Commit the published blog files and push them. No site-tree delete."""
    repo = SITE_BLOG.parent

    def git(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", *args],
            cwd=repo,
            check=True,
            text=True,
            capture_output=True,
        )

    git(
        "add",
        "--",
        f"blog/{slug}.html",
        "blog/index.html",
        "blog/assets",
    )
    staged = subprocess.run(
        ["git", "diff", "--cached", "--quiet"],
        cwd=repo,
        check=False,
    )
    if staged.returncode != 0:
        git("commit", "-m", f"post {slug}: {title}")
    git("push", "origin", "HEAD")
    print(f"pushed: {slug}")


def gcloud_bin() -> str:
    found = shutil.which("gcloud") or shutil.which("gcloud.cmd")
    if found:
        return found
    candidate = Path(
        r"C:\Program Files (x86)\Google\Cloud SDK\google-cloud-sdk\bin\gcloud.cmd"
    )
    if candidate.exists():
        return str(candidate)
    raise FileNotFoundError("gcloud not found on PATH")


def deploy(slug_html: str) -> None:
    local_blog = str(SITE_BLOG)
    gcloud = gcloud_bin()
    # Upload whole blog tree so index + assets stay consistent.
    subprocess.run(
        [
            gcloud,
            "compute",
            "ssh",
            INSTANCE,
            f"--zone={ZONE}",
            "--tunnel-through-iap",
            f"--project={PROJECT}",
            "--command=mkdir -p /tmp/bbh-site-upload && rm -rf /tmp/bbh-site-upload/blog",
        ],
        check=True,
    )
    subprocess.run(
        [
            gcloud,
            "compute",
            "scp",
            "--recurse",
            local_blog,
            f"{INSTANCE}:/tmp/bbh-site-upload/",
            f"--zone={ZONE}",
            "--tunnel-through-iap",
            f"--project={PROJECT}",
        ],
        check=True,
    )
    subprocess.run(
        [
            gcloud,
            "compute",
            "ssh",
            INSTANCE,
            f"--zone={ZONE}",
            "--tunnel-through-iap",
            f"--project={PROJECT}",
            "--command="
            "sudo rm -rf /srv/site/blog && "
            "sudo cp -a /tmp/bbh-site-upload/blog /srv/site/blog && "
            "sudo find /srv/site/blog -type d -exec chmod 755 {} \\; && "
            "sudo find /srv/site/blog -type f -exec chmod 644 {} \\;",
        ],
        check=True,
    )
    print(f"deployed: https://blackbelthacker.com/blog/{slug_html}")


def write_medium_card(pack: Path, canonical: str, title: str) -> None:
    body = f"""# Medium import card

Canonical URL (publish this first; already live if deploy succeeded):

{canonical}

## Steps in Medium

1. Sign in as Black Belt Hacker (`n0auth@blackbelthacker.com`).
2. Open your publication → **Import a story** (or Stories → Import).
3. Paste the canonical URL above.
4. Confirm Medium set the canonical link back to blackbelthacker.com
   (view page source; look for `rel="canonical"`).
5. Add the publication, tags, and the header image if import dropped it.
6. Publish.

Title expected: {title}
Pack: {pack.name}
Generated: {datetime.now(timezone.utc).isoformat()}
"""
    (pack / "medium-import.md").write_text(
        body, encoding="utf-8", newline="\n"
    )


def append_progress(slug: str, canonical: str) -> None:
    PROGRESS.parent.mkdir(parents=True, exist_ok=True)
    if not PROGRESS.exists():
        PROGRESS.write_text("# Progress\n\n", encoding="utf-8", newline="\n")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    with PROGRESS.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(f"- {stamp}: published `{slug}` → {canonical}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("slug", help="Queue folder name / slug")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip APPROVE file (only after explicit chat approval)",
    )
    parser.add_argument(
        "--skip-deploy",
        action="store_true",
        help="Copy into local site tree only",
    )
    args = parser.parse_args()

    pack = QUEUE / args.slug
    if not pack.exists():
        raise SystemExit(f"Missing pack: {pack}")

    html_candidates = list(pack.glob("*.html"))
    html_candidates = [p for p in html_candidates if p.name != "index.html"]
    if not html_candidates:
        raise SystemExit("Refuse: pack has no article HTML yet.")
    article = html_candidates[0]
    slug = args.slug
    assert_approved(pack, slug, args.force)

    SITE_BLOG.mkdir(parents=True, exist_ok=True)
    dest_html = SITE_BLOG / f"{slug}.html"
    shutil.copy2(article, dest_html)
    src_assets = pack / "assets"
    dest_assets = SITE_BLOG / "assets"
    dest_assets.mkdir(exist_ok=True)
    if src_assets.exists():
        for asset in src_assets.iterdir():
            if asset.is_file():
                shutil.copy2(asset, dest_assets / asset.name)

    rebuild_index()
    title_m = re.search(
        r"<h1>(.*?)</h1>", dest_html.read_text(encoding="utf-8"), re.S
    )
    title = (
        re.sub(r"\s+", " ", title_m.group(1)).strip()
        if title_m
        else slug
    )
    canonical = f"https://blackbelthacker.com/blog/{slug}.html"
    write_medium_card(pack, canonical, title)
    commit_and_push(slug, title)

    if not args.skip_deploy:
        deploy(f"{slug}.html")

    published = PUBLISHED / slug
    if published.exists():
        shutil.rmtree(published)
    shutil.copytree(pack, published)

    status = read_status(pack)
    status.update(
        {
            "status": "published_site",
            "canonical": canonical,
            "published_at": datetime.now(timezone.utc).isoformat(),
            "medium_next": "import_url",
        }
    )
    write_status(pack, status)
    append_progress(slug, canonical)
    print(f"canonical: {canonical}")
    print(f"medium card: {pack / 'medium-import.md'}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print(f"deploy failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
