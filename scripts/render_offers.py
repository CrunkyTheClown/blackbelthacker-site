#!/usr/bin/env python3
"""Render product, service, about, and legal pages from data/offers.json."""

from __future__ import annotations

import html
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from layout import apply_document, write_sitemap  # noqa: E402

ORIGIN = "https://www.blackbelthacker.com"
DATA = ROOT / "data" / "offers.json"


def esc(value: str) -> str:
    return html.escape(value or "", quote=True)


def load() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def by_id(data: dict, offer_id: str) -> dict:
    for offer in data["offers"]:
        if offer["id"] == offer_id:
            return offer
    raise KeyError(offer_id)


def resolve(data: dict, value: str) -> str:
    if not value:
        return ""
    return data["placeholders"].get(value, value)


def abs_url(path: str) -> str:
    if path.startswith("http"):
        return path
    return ORIGIN + path


def ld_script(payload: dict) -> str:
    blob = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return f'<script type="application/ld+json">{blob}</script>'


def status_badge(offer: dict) -> str:
    parts = []
    if offer.get("status") == "early_access":
        parts.append('<p class="badge">Early access</p>')
    elif offer.get("status") == "coming_soon":
        parts.append('<p class="badge">Coming soon</p>')
    if offer.get("includes_kit"):
        parts.append('<p class="badge">Includes the Kit</p>')
    return "".join(parts)


def bullets(items: list[str]) -> str:
    if not items:
        return ""
    lis = "".join(f"<li>{esc(item)}</li>" for item in items)
    return f"<ul>{lis}</ul>"


def cta(label: str, url: str, kind: str = "buy") -> str:
    external = url.startswith("http") or url.startswith("mailto:")
    rel = ' target="_blank" rel="noopener noreferrer"' if url.startswith("http") else ""
    return f'<a class="{kind}" href="{esc(url)}"{rel}>{esc(label)}</a>'


def shell(
    title: str,
    description: str,
    image: str,
    body: str,
    linked: dict | None,
    narrow: bool = False,
    robots: str = "index, follow",
) -> str:
    ld = ld_script(linked) if linked else ""
    width = " narrow" if narrow else ""
    image_url = abs_url(image)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(title)}</title>
  <meta name="description" content="{esc(description)}">
  <meta name="robots" content="{esc(robots)}">
  <meta name="theme-color" content="#000000">
  <meta name="color-scheme" content="dark">
  <link rel="icon" type="image/png" href="/favicon.png">
  <link rel="icon" type="image/svg+xml" href="/logo-mark.svg">
  <meta property="og:image" content="{esc(image_url)}">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:image" content="{esc(image_url)}">
  {ld}
</head>
<body>
  <main id="content" class="hub{width}">
{body}
  </main>
</body>
</html>
"""


def product_card(data: dict, offer: dict) -> str:
    price = esc(offer["price_label"])
    image = ""
    if offer.get("image"):
        image = (
            f'<img src="{esc(offer["image"])}" alt="{esc(offer.get("image_alt", offer["name"]))}" '
            f'width="{offer.get("image_width", 1024)}" height="{offer.get("image_height", 576)}">'
        )
    return f"""<article class="card">
      {image}
      {status_badge(offer)}
      <h2>{esc(offer["name"])}</h2>
      <p class="price">{price}</p>
      <p>{esc(offer["tagline"])}</p>
      {bullets(offer.get("bullets") or [])}
      {cta(offer["cta_label"], resolve(data, offer["cta_url"]))}
    </article>"""


def offer_image(offer: dict, class_name: str = "") -> str:
    if not offer.get("image"):
        return ""
    class_attr = f' class="{class_name}"' if class_name else ""
    return (
        f'<img{class_attr} src="{esc(offer["image"])}" alt="{esc(offer.get("image_alt", offer.get("name", "")))}" '
        f'width="{offer.get("image_width", 1200)}" height="{offer.get("image_height", 675)}">'
    )


def service_card(data: dict, offer: dict) -> str:
    price = f'<p class="price">{esc(offer["price_label"])}</p>' if offer.get("price_label") else ""
    return f"""<article class="card">
      {offer_image(offer)}
      {status_badge(offer)}
      <h2>{esc(offer["name"])}</h2>
      {price}
      <p>{esc(offer["tagline"])}</p>
      {bullets(offer.get("bullets") or [])}
      {cta(offer["cta_label"], resolve(data, offer["cta_url"]))}
    </article>"""


def product_ld(offer: dict) -> dict:
    node = {
        "@type": "Product",
        "name": offer["name"],
        "description": offer["tagline"],
        "brand": {"@type": "Brand", "name": "Black Belt Hacker"},
        "offers": {
            "@type": "Offer",
            "price": offer["price_usd"],
            "priceCurrency": "USD",
            "url": offer["cta_url"],
            "availability": "https://schema.org/InStock",
        },
    }
    if offer.get("image"):
        node["image"] = abs_url(offer["image"])
    return node


def products_page(data: dict) -> str:
    kit = by_id(data, "kit")
    sentinel = by_id(data, "sentinel")
    hero = data["products_hero"]
    rows = []
    for row in data["comparison"]["rows"]:
        cells = "".join(
            f'<td data-col="{esc(col)}">{esc(cell)}</td>'
            for col, cell in zip(data["comparison"]["columns"], row["cells"])
        )
        rows.append(f'<tr><th scope="row">{esc(row["label"])}</th>{cells}</tr>')
    head = "".join(f"<th scope=\"col\">{esc(col)}</th>" for col in data["comparison"]["columns"])
    shots = []
    for shot in data["gallery"]:
        shots.append(
            f'<figure><img src="{esc(shot["src"])}" width="{shot["width"]}" height="{shot["height"]}" '
            f'alt="{esc(shot["alt"])}" loading="lazy"><figcaption>{esc(shot["caption"])}</figcaption></figure>'
        )
    assurance = "".join(f"<li>{esc(line)}</li>" for line in data["assurance"])
    body = f"""<h1>Products</h1>
    <p class="lede">{esc(hero["line"])}</p>
    <p>{esc(hero["sub"])}</p>
    {offer_image(hero, "hero-shot")}
    <div class="belt" aria-hidden="true"></div>
    <div class="offer-grid two">
      {product_card(data, kit)}
      {product_card(data, sentinel)}
    </div>
    <h2>{esc(data["comparison"]["caption"])}</h2>
    <div class="table-wrap">
      <table class="compare">
        <caption class="sr-only">{esc(data["comparison"]["caption"])}</caption>
        <thead><tr><th scope="col">Item</th>{head}</tr></thead>
        <tbody>{''.join(rows)}<tr><th scope="row">Checkout</th><td data-col="{esc(kit["name"])}"><a href="{esc(kit["cta_url"])}">{esc(kit["cta_label"])}</a></td><td data-col="{esc(sentinel["name"])}"><a href="{esc(sentinel["cta_url"])}">{esc(sentinel["cta_label"])}</a></td></tr></tbody>
      </table>
    </div>
    <h2>Before you buy</h2>
    <ul class="plain">{assurance}</ul>
    <div class="shots">{''.join(shots)}</div>"""
    description = (
        f"Agent Hardening Kit ({kit['price_label']}) and Black Belt Sentinel "
        f"({sentinel['price_label']} early access). A checklist you run yourself, "
        "and an auditor that runs the checks."
    )
    linked = {"@context": "https://schema.org", "@graph": [product_ld(kit), product_ld(sentinel)]}
    return shell(
        "Products · Black Belt Hacker",
        description,
        hero["image"],
        body,
        linked,
    )


def services_page(data: dict) -> str:
    hero = data["services_hero"]
    order = ["pentest", "bjj"]
    cards = "".join(service_card(data, by_id(data, offer_id)) for offer_id in order)
    body = f"""<h1>Services</h1>
    <p class="lede">{esc(hero["line"])}</p>
    <p>{esc(hero["sub"])}</p>
    <div class="belt" aria-hidden="true"></div>
    <div class="offer-grid">{cards}</div>
    <p>Belt tier courses and Offensive Security Certified Professional (OSCP) prep are under <a href="/#training">Training</a>.</p>"""
    return shell(
        "Services · Black Belt Hacker",
        "Penetration testing, and private Brazilian jiu jitsu lessons at American Top Team Atlanta.",
        data["og_default"],
        body,
        None,
    )


def tier_card(tier: dict) -> str:
    badge = f'<p class="sig">{esc(tier["badge"])}</p>' if tier.get("badge") else ""
    return f"""<article class="tier">
      {offer_image(tier)}
      <p class="k">{esc(tier["belt"])} test</p>
      {badge}
      <h3>{esc(tier["name"])}</h3>
      <p><span class="k">Best for</span> {esc(tier["best_for"])}</p>
      <p><span class="k">What I test</span> {esc(tier["what_i_test"])}</p>
      <p><span class="k">Typical duration</span> {esc(tier["duration"])}</p>
      <p class="price"><span class="k">Starting at</span> {esc(tier["price_label"])}</p>
    </article>"""


def documents_html(data: dict, missing: list[str]) -> str:
    cards = []
    for doc in data["documents"]:
        rel = doc.get("pdf") or ""
        path = ROOT / rel.lstrip("/")
        if rel and path.is_file():
            action = f'<p><a href="{esc(rel)}">{esc(doc["name"])} PDF</a></p>'
        else:
            missing.append(doc["name"])
            action = f'<p class="k">{esc(data["documents_missing_label"])}</p>'
        cards.append(
            f'<article class="doc"><h3>{esc(doc["name"])}</h3><p>{esc(doc["summary"])}</p>{action}</article>'
        )
    return "".join(cards)


def form_html(data: dict) -> str:
    options = ['<option value="">Select an engagement</option>']
    for tier in data["tiers"]:
        label = f'{tier["belt"]} test: {tier["name"]}'
        options.append(f'<option value="{esc(tier["id"])}">{esc(label)}</option>')
    email = esc(data["support_email"])
    return f"""<form class="scope-form" data-scope-form action="mailto:{email}" method="post">
      <p id="form-errors" role="alert" aria-live="polite" tabindex="-1" hidden></p>
      <div><label for="scope-name">Name</label><input id="scope-name" name="name" autocomplete="name" required><p class="field-error" id="err-name" hidden></p></div>
      <div><label for="scope-email">Work email</label><input id="scope-email" name="email" type="email" autocomplete="email" spellcheck="false" required><p class="field-error" id="err-email" hidden></p></div>
      <div><label for="scope-company">Company</label><input id="scope-company" name="company" autocomplete="organization" required><p class="field-error" id="err-company" hidden></p></div>
      <div><label for="scope-website">Website</label><input id="scope-website" name="website" type="url" autocomplete="url" required><p class="field-error" id="err-website" hidden></p></div>
      <div><label for="scope-tier">Engagement type</label><select id="scope-tier" name="tier" required>{''.join(options)}</select><p class="field-error" id="err-tier" hidden></p></div>
      <div><label for="scope-size">Approx. size (IPs / apps / agents)</label><input id="scope-size" name="size" required><p class="field-error" id="err-size" hidden></p></div>
      <div><label for="scope-when">Preferred timeframe</label><input id="scope-when" name="when" required><p class="field-error" id="err-when" hidden></p></div>
      <div><label for="scope-notes">Anything I should know</label><textarea id="scope-notes" name="notes" aria-describedby="notes-help"></textarea><p class="help" id="notes-help">Do not include passwords. Share those after the NDA.</p></div>
      <div><label class="check" for="scope-auth"><input id="scope-auth" name="authorized" type="checkbox" required> I am authorized to request testing of these systems</label><p class="field-error" id="err-authorized" hidden></p></div>
      <button class="buy" type="submit">Send scoping request</button>
    </form>
    <script src="/site.js" defer></script>"""


def pentest_page(data: dict, missing: list[str]) -> str:
    offer = by_id(data, "pentest")
    hero = data["pentest_hero"]
    booking = resolve(data, offer["booking_url"])
    tiers = "".join(tier_card(tier) for tier in data["tiers"])
    steps = "".join(
        f'<li><span class="num">{index}</span> {esc(step)}</li>'
        for index, step in enumerate(data["steps"], start=1)
    )
    deliverables = "".join(f"<li>{esc(item)}</li>" for item in data["deliverables"])
    rules = "".join(f"<li>{esc(item)}</li>" for item in data["rules"])
    faqs = "".join(
        f'<details><summary>{esc(item["q"])}</summary><p>{esc(item["a"])}</p></details>'
        for item in data["faqs"]
    )
    book = cta(offer["cta_label"], booking)
    body = f"""<h1>{esc(hero["line"])}</h1>
    <p class="lede">{esc(hero["sub"])}</p>
    {offer_image(hero, "hero-shot")}
    <p>{book} {cta("See how it works", "#how-it-works", "ghost")}</p>
    <div class="belt" aria-hidden="true"></div>
    <h2 id="engagements">Test tiers</h2>
    <div class="tier-grid">{tiers}</div>
    <h2 id="how-it-works">How it works</h2>
    <ol class="steps">{steps}</ol>
    <h2>What you get</h2>
    <ul class="plain">{deliverables}</ul>
    <h2>Rules I work by</h2>
    <ul class="plain">{rules}</ul>
    <h2>Engagement documents</h2>
    <div class="doc-grid">{documents_html(data, missing)}</div>
    <p>{esc(data["documents_note"])}</p>
    <h2 id="scoping">Scoping request</h2>
    {form_html(data)}
    <h2 id="faq">FAQ</h2>
    <div class="faq">{faqs}</div>
    <div class="cta-band"><h2>Book a scoping call</h2><p>{book}</p></div>"""
    linked = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "Service",
                "name": offer["name"],
                "description": offer["tagline"],
                "url": ORIGIN + "/services/penetration-testing/",
                "provider": {
                    "@type": "Organization",
                    "name": "Black Belt Hacker",
                    "url": ORIGIN + "/",
                },
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": item["q"],
                        "acceptedAnswer": {"@type": "Answer", "text": item["a"]},
                    }
                    for item in data["faqs"]
                ],
            },
        ],
    }
    return shell(
        "Penetration Testing · Black Belt Hacker",
        "Penetration testing from an Offensive Security Certified Professional (OSCP). External, web, API, AI agent, and internal tests. Findings your team can fix.",
        hero["image"],
        body,
        linked,
    )


def about_page(data: dict) -> str:
    body = """<h1>About</h1>
    <div class="belt" aria-hidden="true"></div>
    <img class="portrait" src="/logo-square.png" width="320" height="320" alt="Black Belt Hacker mark">
    <p>I am David. I hold the Offensive Security Certified Professional (OSCP). I have spent over 20 years defending Fortune 500 environments, and I come from a military background.</p>
    <p>I am a Brazilian jiu jitsu (BJJ) black belt. I write as n0auth.</p>
    <p>Email <a href="mailto:n0auth@blackbelthacker.com">n0auth@blackbelthacker.com</a>.</p>"""
    return shell(
        "About · Black Belt Hacker",
        "David, an Offensive Security Certified Professional. Over 20 years defending Fortune 500 environments. Brazilian jiu jitsu black belt. Writes as n0auth.",
        data["og_default"],
        body,
        None,
        narrow=True,
    )


def legal_page(data: dict, title: str, description: str, paragraphs: list[str]) -> str:
    copy = "".join(f"<p>{esc(line)}</p>" for line in paragraphs)
    body = f"""<h1>{esc(title.split(' · ')[0])}</h1>
    <p class="todo-banner">Draft pending review</p>
    <div class="belt" aria-hidden="true"></div>
    {copy}"""
    return shell(title, description, data["og_default"], body, None, narrow=True, robots="noindex, follow")


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def home_page(data: dict) -> str:
    kit = by_id(data, "kit")
    sentinel = by_id(data, "sentinel")
    bjj = by_id(data, "bjj")
    course = by_id(data, "course")
    pentest = by_id(data, "pentest")
    kit_url = resolve(data, kit["cta_url"])
    sentinel_url = resolve(data, sentinel["cta_url"])
    bjj_url = resolve(data, bjj["cta_url"])
    course_url = resolve(data, course["cta_url"])
    pentest_url = resolve(data, pentest["booking_url"])
    oscp_url = "mailto:n0auth@blackbelthacker.com?subject=OSCP%20prep"
    body = f"""<img class="hero-mark" src="/logo-square.png" width="96" height="96" alt="" fetchpriority="high">
    <h1>Defender first security you can buy, book, or study.</h1>
    <p class="lede">An Offensive Security Certified Professional (OSCP) and a Brazilian jiu jitsu (BJJ) black belt. Kits, lessons, courses, exam prep, and field notes.</p>
    <p>{cta(kit["cta_label"], kit_url)} {cta("Read the blog", "/blog/", "ghost")}</p>
    <div class="belt" aria-hidden="true"></div>
    <h2>Offers</h2>
    <div class="offer-grid">
      <article class="card">
        <p class="k">Kit</p>
        <h3>Agent Hardening Kit</h3>
        <p class="price">{esc(kit["price_label"])}</p>
        <p>{esc(kit["tagline"])}</p>
        {cta(kit["cta_label"], kit_url)}
      </article>
      <article class="card">
        <p class="k">Lessons</p>
        <h3>Private BJJ lessons</h3>
        <p class="price">{esc(bjj["price_label"])}</p>
        <p>{esc(bjj["tagline"])}</p>
        {cta(bjj["cta_label"], bjj_url)}
      </article>
      <article class="card">
        <p class="k">Courses</p>
        <h3>Belt tier security courses</h3>
        <p class="price">{esc(course["price_label"])}</p>
        <p>{esc(course["tagline"])}</p>
        {cta("See the courses", "/courses/")}
      </article>
      <article class="card">
        <p class="k">Exam prep</p>
        <h3>OSCP prep</h3>
        <p class="price">$300</p>
        <p class="guarantee">This prep does not promise a pass. You still sit the exam.</p>
        {cta("See OSCP prep", "/oscp/")}
      </article>
      <article class="card">
        <p class="k">Notes</p>
        <h3>Blog</h3>
        <p>Field notes for defenders.</p>
        {cta("Read the blog", "/blog/")}
      </article>
    </div>
    <h2>The kit</h2>
    <p>{esc(kit["tagline"])}</p>
    <p>Sentinel is {esc(sentinel["price_label"])} early access and includes the kit.</p>
    <p>{cta(kit["cta_label"], kit_url)} {cta(sentinel["cta_label"], sentinel_url, "ghost")}</p>
    <h2 id="training">Training</h2>
    <div class="offer-grid two">
      <article class="card">
        <p class="k">Courses</p>
        <h3>Belt tier security courses</h3>
        <p class="price">{esc(course["price_label"])}</p>
        <p>Five belts, from first checks to a stack you can run. These belts are courses, not penetration tests.</p>
        {cta("See the courses", "/courses/")} {cta(course["cta_label"], course_url, "ghost")}
      </article>
      <article class="card">
        <p class="k">OSCP</p>
        <h3>Prepare for the OSCP</h3>
        <p class="price">$300</p>
        <p class="guarantee">This prep does not promise a pass. You still sit the exam.</p>
        {cta("See OSCP prep", "/oscp/")} {cta("Email to enroll", oscp_url, "ghost")}
      </article>
    </div>
    <h2>Services</h2>
    <div class="offer-grid two">
      <article class="card">
        <p class="k">Testing</p>
        <h3>Penetration testing</h3>
        <p class="price">{esc(pentest["price_label"])}</p>
        <p>{esc(pentest["tagline"])}</p>
        {cta(pentest["cta_label"], pentest_url)}
      </article>
      <article class="card">
        <p class="k">Lessons</p>
        <h3>Private BJJ lessons</h3>
        <p class="price">{esc(bjj["price_label"])}</p>
        <p>{esc(bjj["tagline"])}</p>
        {cta(bjj["cta_label"], bjj_url)}
      </article>
    </div>
    <h2>Latest notes</h2>
    <ul class="posts">
      <li><a href="/blog/2026-11-14-friday-the-13th-faa-ground-stop.html">Friday the 13th Grounded America. By Midnight, Washington Sent a $50 Billion Ransom Note.</a></li>
      <li><a href="/blog/2026-11-14-agent-dashboard-host-header-bypass.html">One Header Bypassed My Login: Hardening a Self Hosted AI Agent Stack</a></li>
      <li><a href="/blog/2026-11-12-signdrop-windows-clfs-zero-day.html">Windows Zero-Day SignDrop Turns a Standard User Into SYSTEM, and Microsoft Has Not Patched It</a></li>
    </ul>
    <p><a href="/blog/">All notes</a></p>
    <h2>About</h2>
    <p>I am David, an OSCP and a BJJ black belt.</p>
    <p>I write as n0auth.</p>
    <p>Email <a href="mailto:n0auth@blackbelthacker.com">n0auth@blackbelthacker.com</a>.</p>"""
    return shell(
        "Black Belt Hacker",
        "Defender first security you can buy, book, or study. Kits, private lessons, courses, OSCP prep, and field notes.",
        data["og_default"],
        body,
        {
            "@context": "https://schema.org",
            "@type": "Organization",
            "name": "Black Belt Hacker",
            "url": ORIGIN + "/",
            "logo": ORIGIN + "/logo-square.png",
            "email": data["support_email"],
            "sameAs": [
                "https://www.instagram.com/blackbelthacker/",
                "https://medium.com/@n0auth",
            ],
        },
    )


def courses_page(data: dict) -> str:
    course = by_id(data, "course")
    url = resolve(data, course["cta_url"])
    belts = [
        "White Belt course",
        "Blue Belt course",
        "Purple Belt course",
        "Brown Belt course",
        "Black Belt course",
    ]
    items = "".join(f"<li>{esc(name)}</li>" for name in belts)
    body = f"""<h1>Belt tier security courses</h1>
    <p class="lede">{esc(course["tagline"])}</p>
    <p class="price">{esc(course["price_label"])}</p>
    <p>These belts are the course path. They are not the penetration test tiers.</p>
    <ul class="plain">{items}</ul>
    <p>Email me to enroll. I reply with how to pay.</p>
    <p>{cta(course["cta_label"], url)} {cta("See OSCP prep", "/oscp/", "ghost")}</p>"""
    return shell(
        "Belt tier security courses · Black Belt Hacker",
        "Five belt tier security courses for $59. Separate from penetration test tiers.",
        data["og_default"],
        body,
        None,
        narrow=True,
    )


def oscp_page(data: dict) -> str:
    url = "mailto:n0auth@blackbelthacker.com?subject=OSCP%20prep"
    body = f"""<h1>Prepare for the OSCP</h1>
    <p class="lede">A prep path for the Offensive Security Certified Professional exam.</p>
    <p class="price">$300</p>
    <p class="guarantee">This prep does not promise a pass. You still sit the exam.</p>
    <p>Email me to enroll. I reply with how to pay.</p>
    <p>{cta("Email to enroll", url)} {cta("See the courses", "/courses/", "ghost")}</p>"""
    return shell(
        "Prepare for the OSCP · Black Belt Hacker",
        "OSCP prep for $300. This prep does not promise a pass. You still sit the exam.",
        data["og_default"],
        body,
        None,
        narrow=True,
    )


def patch_home(data: dict) -> None:
    write(ROOT / "index.html", home_page(data))


def retire(rel: str, dest: str) -> None:
    path = ROOT / rel
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    text = text.replace('content="index, follow"', 'content="noindex, follow"', 1)
    if 'id="content"' not in text:
        text = text.replace("<main ", '<main id="content" ', 1)
    note = f'<p>The current page is <a href="{dest}">{dest}</a>.</p>'
    if dest not in text:
        text = text.replace("</h1>", "</h1>\n    " + note, 1)
    path.write_text(text, encoding="utf-8", newline="\n")


def visible_text(page: str) -> str:
    page = re.sub(r"<script[\s\S]*?</script>", " ", page, flags=re.I)
    page = re.sub(r"<style[\s\S]*?</style>", " ", page, flags=re.I)
    page = re.sub(r"<[^>]+>", " ", page)
    return html.unescape(page)


def check_copy(paths: list[Path]) -> None:
    bad = []
    for path in paths:
        text = visible_text(path.read_text(encoding="utf-8"))
        if "—" in text or "–" in text or " - " in text:
            bad.append(f"{path}: spaced hyphen or dash")
        hit = re.search(r"[A-Za-z]{2,}-[A-Za-z]{2,}", text)
        if hit:
            bad.append(f"{path}: {hit.group(0)}")
    if bad:
        raise SystemExit("copy check failed: " + "; ".join(bad))


def render() -> list[str]:
    data = load()
    images = ROOT / "images"
    images.mkdir(exist_ok=True)
    og = images / "og-default.webp"
    if not og.exists():
        shutil.copyfile(ROOT / "products" / "sentinel-cover.webp", og)
    missing: list[str] = []
    pages = {
        ROOT / "products" / "index.html": products_page(data),
        ROOT / "services" / "index.html": services_page(data),
        ROOT / "services" / "penetration-testing" / "index.html": pentest_page(data, missing),
        ROOT / "about" / "index.html": about_page(data),
        ROOT / "courses" / "index.html": courses_page(data),
        ROOT / "oscp" / "index.html": oscp_page(data),
        ROOT / "legal" / "refund" / "index.html": legal_page(
            data,
            "Refund Policy · Black Belt Hacker",
            "14 day refund, no questions asked, for Gumroad products. Draft pending review.",
            [
                "Gumroad products can be refunded for 14 days. No questions asked.",
                "Email n0auth@blackbelthacker.com.",
            ],
        ),
        ROOT / "legal" / "privacy" / "index.html": legal_page(
            data,
            "Privacy · Black Belt Hacker",
            "No ads and no tracking cookies on Black Belt Hacker. Draft pending review.",
            [
                "This site does not run ads and does not set tracking cookies.",
                "Mail sent to n0auth@blackbelthacker.com is read so I can answer it.",
                "Kit checkout happens on Gumroad.",
            ],
        ),
        ROOT / "legal" / "terms" / "index.html": legal_page(
            data,
            "Terms · Black Belt Hacker",
            "Terms for Black Belt Hacker kits and testing. Draft pending review.",
            [
                "Kits and notes are for people securing systems they are allowed to test.",
                "Penetration testing starts only after written authorization.",
                "Kit purchases go through Gumroad. The refund window is 14 days, no questions asked.",
            ],
        ),
    }
    for path, text in pages.items():
        write(path, text)
    patch_home(data)
    retire("refund/index.html", "/legal/refund/")
    retire("privacy/index.html", "/legal/privacy/")
    retire("terms/index.html", "/legal/terms/")
    targets = list(pages) + [
        ROOT / "index.html",
        ROOT / "refund" / "index.html",
        ROOT / "privacy" / "index.html",
        ROOT / "terms" / "index.html",
    ]
    for path in targets:
        if path.exists():
            apply_document(path, ROOT)
    write_sitemap(ROOT)
    check_copy(list(pages))
    return missing


def main() -> None:
    missing = render()
    print("rendered offers")
    if missing:
        print("missing pdfs:")
        for item in missing:
            print(item)


if __name__ == "__main__":
    main()
