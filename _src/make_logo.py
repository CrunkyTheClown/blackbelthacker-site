"""Black Belt Hacker logo generator: SVGs, PNGs and glitch frames from one geometry spec."""
import os, sys, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

OUT = sys.argv[1]
FRAMES = sys.argv[2]
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

BG = "#07080f"; CYAN = "#3df0ff"; MAG = "#ff2bd6"; RED = "#ff2a3d"; BELT = "#12141c"; STITCH = "#2c3040"; WHITE = "#f4fbff"

# ---------- geometry in a 512x512 space ----------
HEX = [(256, 44), (436, 148), (436, 364), (256, 468), (76, 364), (76, 148)]
TRACES = [  # polyline, end dot
    ([(256, 44), (256, 150)], (256, 160)),
    ([(76, 172), (156, 172), (186, 202)], (192, 208)),
    ([(436, 172), (356, 172), (326, 202)], (320, 208)),
    ([(76, 330), (124, 330), (146, 352)], (152, 358)),
    ([(436, 330), (388, 330), (366, 352)], (360, 358)),
]
BAR = (40, 236, 472, 284)
KNOT = (204, 214, 308, 306)
TAIL_L = [(216, 300), (250, 300), (206, 400), (172, 400)]
TAIL_R = [(262, 300), (296, 300), (340, 400), (306, 400)]
TIP_R = [(290.6, 365), (324.6, 365), (340, 400), (306, 400)]
CHEVRON = [(232, 238), (258, 260), (232, 282)]
CURSOR = (268, 282, 292, 282)
TRACE_W, HEX_W, EDGE_W = 10, 14, 6


def pts(p):
    return " ".join(f"{x:g},{y:g}" for x, y in p)


def mark_svg_body():
    s = []
    s.append(f'<polygon points="{pts(HEX)}" fill="none" stroke="{CYAN}" stroke-width="{HEX_W}" stroke-linejoin="round"/>')
    for line, dot in TRACES:
        s.append(f'<polyline points="{pts(line)}" fill="none" stroke="{CYAN}" stroke-width="{TRACE_W}" stroke-linecap="round" stroke-linejoin="round"/>')
        s.append(f'<circle cx="{dot[0]}" cy="{dot[1]}" r="11" fill="{BG}" stroke="{CYAN}" stroke-width="6"/>')
    # knock-out under belt so it reads over the hex
    x0, y0, x1, y1 = BAR
    s.append(f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" rx="6" fill="{BELT}" stroke="{BG}" stroke-width="18"/>')
    s.append(f'<rect x="{x0}" y="{y0}" width="{x1-x0}" height="{y1-y0}" rx="6" fill="{BELT}" stroke="{MAG}" stroke-width="{EDGE_W}"/>')
    for yy in (y0 + 11, y1 - 11):
        s.append(f'<line x1="{x0+14}" y1="{yy}" x2="{x1-14}" y2="{yy}" stroke="{STITCH}" stroke-width="3" stroke-dasharray="10 8"/>')
    for t in (TAIL_L, TAIL_R):
        s.append(f'<polygon points="{pts(t)}" fill="{BELT}" stroke="{BG}" stroke-width="18" stroke-linejoin="round"/>')
    for t in (TAIL_L, TAIL_R):
        s.append(f'<polygon points="{pts(t)}" fill="{BELT}" stroke="{MAG}" stroke-width="{EDGE_W}" stroke-linejoin="round"/>')
    s.append(f'<polygon points="{pts(TIP_R)}" fill="{RED}" stroke="{MAG}" stroke-width="{EDGE_W}" stroke-linejoin="round"/>')
    kx0, ky0, kx1, ky1 = KNOT
    s.append(f'<rect x="{kx0}" y="{ky0}" width="{kx1-kx0}" height="{ky1-ky0}" rx="14" fill="{BG}" stroke="{BG}" stroke-width="16"/>')
    s.append(f'<rect x="{kx0}" y="{ky0}" width="{kx1-kx0}" height="{ky1-ky0}" rx="14" fill="{BG}" stroke="{MAG}" stroke-width="{EDGE_W}"/>')
    s.append(f'<polyline points="{pts(CHEVRON)}" fill="none" stroke="{CYAN}" stroke-width="11" stroke-linecap="round" stroke-linejoin="round"/>')
    cx0, cy0, cx1, cy1 = CURSOR
    s.append(f'<line class="cursor" x1="{cx0}" y1="{cy0}" x2="{cx1}" y2="{cy1}" stroke="{CYAN}" stroke-width="11" stroke-linecap="round"/>')
    return "\n  ".join(s)


# ---------- raster (same geometry, PIL, supersampled) ----------
def draw_mark(size, cursor=True, glow=True):
    S = 4
    W = size * S
    k = W / 512
    im = Image.new("RGBA", (W, W), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    P = lambda p: [(x * k, y * k) for x, y in p]
    w = lambda v: max(1, int(round(v * k)))

    def poly_stroke(p, color, width):
        q = P(p) + [P(p)[0]]
        d.line(q, fill=color, width=w(width), joint="curve")
        r = width * k / 2
        for x, y in P(p):
            d.ellipse((x - r, y - r, x + r, y + r), fill=color)

    def polyline(p, color, width):
        q = P(p)
        d.line(q, fill=color, width=w(width), joint="curve")
        r = width * k / 2
        for x, y in (q[0], q[-1]):
            d.ellipse((x - r, y - r, x + r, y + r), fill=color)

    def rrect(b, r, fill, outline, width):
        x0, y0, x1, y1 = b
        d.rounded_rectangle((x0 * k - width * k / 2, y0 * k - width * k / 2, x1 * k + width * k / 2, y1 * k + width * k / 2), radius=r * k, fill=outline)
        d.rounded_rectangle((x0 * k + width * k / 2, y0 * k + width * k / 2, x1 * k - width * k / 2, y1 * k - width * k / 2), radius=max(0, (r - width / 2)) * k, fill=fill)

    poly_stroke(HEX, CYAN, HEX_W)
    for line, dot in TRACES:
        polyline(line, CYAN, TRACE_W)
        x, y = dot[0] * k, dot[1] * k
        d.ellipse((x - 14 * k, y - 14 * k, x + 14 * k, y + 14 * k), fill=CYAN)
        d.ellipse((x - 8 * k, y - 8 * k, x + 8 * k, y + 8 * k), fill=BG)
    rrect(BAR, 6, BELT, BG, 18)
    rrect(BAR, 6, BELT, MAG, EDGE_W)
    x0, y0, x1, y1 = BAR
    for yy in (y0 + 11, y1 - 11):
        xx = x0 + 14
        while xx < x1 - 14:
            d.line([(xx * k, yy * k), (min(xx + 10, x1 - 14) * k, yy * k)], fill=STITCH, width=w(3))
            xx += 18
    for t in (TAIL_L, TAIL_R):
        d.polygon(P(t), fill=BELT)
        poly_stroke(t, BG, 18)
        d.polygon(P(t), fill=BELT)
    for t in (TAIL_L, TAIL_R):
        poly_stroke(t, MAG, EDGE_W)
    d.polygon(P(TIP_R), fill=RED)
    poly_stroke(TIP_R, MAG, EDGE_W)
    rrect(KNOT, 14, BG, BG, 16)
    rrect(KNOT, 14, BG, MAG, EDGE_W)
    polyline(CHEVRON, CYAN, 11)
    if cursor:
        polyline([CURSOR[:2], CURSOR[2:]], CYAN, 11)
    im = im.resize((size, size), Image.LANCZOS)
    if glow:
        g = im.filter(ImageFilter.GaussianBlur(size / 40))
        base = Image.new("RGBA", im.size, (0, 0, 0, 0))
        base = Image.alpha_composite(base, g)
        base = Image.alpha_composite(base, g)
        im = Image.alpha_composite(base, im)
    return im


# ---------- text to SVG path ----------
TT = TTFont(FONT)
GS = TT.getGlyphSet()
CMAP = TT.getBestCmap()
UPM = TT["head"].unitsPerEm


def text_width(text, size, track):
    adv = sum(TT["hmtx"][CMAP[ord(c)]][0] for c in text) * size / UPM
    return adv + track * (len(text) - 1)


def text_path(text, x, y, size, track):
    sc = size / UPM
    out = []
    for c in text:
        g = CMAP[ord(c)]
        pen = SVGPathPen(GS)
        GS[g].draw(TransformPen(pen, (sc, 0, 0, -sc, x, y)))
        cmd = pen.getCommands()
        if cmd:
            out.append(cmd)
        x += TT["hmtx"][g][0] * sc + track
    return " ".join(out)


def fit_size(text, width, track_em):
    s = 100.0
    return width / (text_width(text, s, s * track_em) / s)


def write(path, data):
    with open(path, "w") as f:
        f.write(data)


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(FRAMES, exist_ok=True)
    body = mark_svg_body()

    # logo-mark.svg
    write(f"{OUT}/logo-mark.svg", f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512" role="img" aria-label="Black Belt Hacker mark">
  <title>Black Belt Hacker</title>
  <rect width="512" height="512" rx="96" fill="{BG}"/>
  {body}
</svg>
''')

    # logo.svg (mark + wordmark, text outlined)
    W, H = 1280, 400
    tx, tw = 400, 820
    s1 = fit_size("BLACK BELT", tw, 0.04)
    s2 = fit_size("HACKER", tw, 0.30)
    s2 = min(s2, s1)
    t1 = text_path("BLACK BELT", tx, 212, s1, s1 * 0.04)
    w2 = text_width("HACKER", s2, s2 * 0.30)
    t2 = text_path("HACKER", tx, 330, s2, s2 * 0.30)
    write(f"{OUT}/logo.svg", f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Black Belt Hacker">
  <title>Black Belt Hacker</title>
  <rect width="{W}" height="{H}" rx="40" fill="{BG}"/>
  <g transform="translate(40 40) scale(0.625)">
  {body}
  </g>
  <path d="{t1}" fill="{MAG}" transform="translate(-4 0)"/>
  <path d="{t1}" fill="{CYAN}" transform="translate(4 0)"/>
  <path d="{t1}" fill="{WHITE}"/>
  <path d="{t2}" fill="{CYAN}"/>
  <rect x="{tx}" y="350" width="{w2:.0f}" height="10" fill="{BELT}" stroke="{MAG}" stroke-width="3"/>
  <rect x="{tx + w2 - 90:.0f}" y="350" width="60" height="10" fill="{RED}"/>
</svg>
''')

    # PNGs
    font = lambda sz: ImageFont.truetype(FONT, int(round(sz)))
    fav = Image.new("RGBA", (512, 512), (0, 0, 0, 0))
    bgm = Image.new("RGBA", (512 * 4, 512 * 4), (0, 0, 0, 0))
    ImageDraw.Draw(bgm).rounded_rectangle((0, 0, 2047, 2047), radius=96 * 4, fill=BG)
    fav = Image.alpha_composite(fav, bgm.resize((512, 512), Image.LANCZOS))
    fav = Image.alpha_composite(fav, draw_mark(512))
    fav.save(f"{OUT}/favicon.png", optimize=True)

    def wordmark(im, d, tx, b1, b2, s1, s2, w2, scale=1.0):
        f1, f2 = font(s1), font(s2)
        def track_text(text, x, base, f, sz, track, fill, dx=0):
            for c in text:
                d.text((x + dx, base), c, font=f, fill=fill, anchor="ls")
                x += f.getlength(c) + track
        for dx, col in ((-4 * scale, MAG), (4 * scale, CYAN), (0, WHITE)):
            track_text("BLACK BELT", tx, b1, f1, s1, s1 * 0.04, col, dx)
        track_text("HACKER", tx, b2, f2, s2, s2 * 0.30, CYAN)

    logo = Image.new("RGB", (W, H), BG)
    logo.paste(draw_mark(320), (40, 40), draw_mark(320))
    d = ImageDraw.Draw(logo)
    wordmark(logo, d, tx, 212, 330, s1, s2, w2)
    d.rectangle((tx, 350, tx + w2, 360), fill=BELT, outline=MAG, width=3)
    d.rectangle((tx + w2 - 90, 350, tx + w2 - 30, 360), fill=RED)
    logo.save(f"{OUT}/logo.png", optimize=True)

    # ---------- glitch frames (600x600) ----------
    N = 30
    def base_frame(cursor):
        im = Image.new("RGB", (600, 600), BG)
        # faint background grid
        d = ImageDraw.Draw(im)
        for i in range(0, 600, 30):
            d.line([(i, 0), (i, 600)], fill="#0d1120")
            d.line([(0, i), (600, i)], fill="#0d1120")
        m = draw_mark(420, cursor=cursor)
        im.paste(m, (90, 24), m)
        d = ImageDraw.Draw(im)
        txt = "BLACK BELT HACKER"
        sz = 46
        f = font(sz)
        track = 4
        tw_ = sum(f.getlength(c) for c in txt) + track * (len(txt) - 1)
        x0 = (600 - tw_) / 2
        for dx, col in ((-3, MAG), (3, CYAN), (0, WHITE)):
            x = x0
            for c in txt:
                d.text((x + dx, 520), c, font=f, fill=col, anchor="ls")
                x += f.getlength(c) + track
        d.rectangle((x0, 540, x0 + tw_, 548), fill=BELT, outline=MAG, width=2)
        d.rectangle((x0 + tw_ - 70, 540, x0 + tw_ - 26, 548), fill=RED)
        return np.asarray(im).astype(np.int16)

    on = base_frame(True); off = base_frame(False)
    Image.fromarray(on.astype(np.uint8)).save(f"{OUT}/logo-square.png", optimize=True)
    scan = np.ones((600, 1, 1)); scan[1::3] = 0.78
    rng = random.Random(7)
    # glitch intensity per frame: two bursts, calm between; frame 0 and N-1 calm
    burst = {8: 0.5, 9: 1.0, 10: 0.8, 11: 0.4, 21: 0.6, 22: 0.3}
    dim = {10, 22}  # flicker dips (no white flashes): 2 per 2.4 s
    for i in range(N):
        a = (on if (i // 5) % 2 == 0 else off).copy()
        g = burst.get(i, 0)
        if g:
            dx = int(4 + 14 * g)
            r = np.roll(a[:, :, 0], -dx, axis=1); b = np.roll(a[:, :, 2], dx, axis=1)
            a = np.stack([np.maximum(r, a[:, :, 0] // 3), a[:, :, 1], np.maximum(b, a[:, :, 2] // 3)], axis=2)
            for _ in range(int(3 + 7 * g)):
                y = rng.randrange(0, 580); h = rng.randrange(4, int(10 + 40 * g))
                sh = rng.randint(-int(60 * g), int(60 * g))
                a[y:y + h] = np.roll(a[y:y + h], sh, axis=1)
                if rng.random() < 0.4:
                    tint = np.array([61, 240, 255] if rng.random() < 0.5 else [255, 43, 214])
                    a[y:y + h] = (a[y:y + h] * 0.7 + tint * 0.3)
            for _ in range(int(2 + 4 * g)):
                x = rng.randrange(0, 560); y = rng.randrange(0, 580)
                col = np.array([61, 240, 255] if rng.random() < 0.5 else [255, 43, 214])
                a[y:y + rng.randrange(2, 6), x:x + rng.randrange(10, 60)] = col
        if i in dim:
            a = a * 0.55
        # slow scan band (moves once per loop, seamless)
        band_y = int(i * 600 / N)
        yy = np.arange(600)[:, None, None]
        dist = np.minimum(np.abs(yy - band_y), 600 - np.abs(yy - band_y))
        a = a + 18 * np.exp(-(dist / 22.0) ** 2) * np.array([0.3, 1.0, 1.0])
        a = a * scan
        Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(f"{FRAMES}/f{i:03d}.png")
    print("ok", s1, s2)


main()
