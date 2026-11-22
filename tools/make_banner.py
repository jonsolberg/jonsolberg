#!/usr/bin/env python3
# Copyright (C) 2026 Jon Solberg. Licensed under the GNU GPL v3 (see LICENSE).
# Builds assets/banner.jpg for the jonsolberg GitHub profile:
# code snippets mixed with musical notation, plus app screenshot cards.
# Usage: make_banner.py <assets dir> <out.jpg>
import random, re, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

ASSETS, OUT = sys.argv[1], sys.argv[2]
W, H = 1600, 500
random.seed(7)

F = "/usr/share/fonts/"
mono = ImageFont.truetype(F + "truetype/dejavu/DejaVuSansMono.ttf", 14)
mono_s = ImageFont.truetype(F + "truetype/dejavu/DejaVuSansMono.ttf", 11)
music = lambda s: ImageFont.truetype(F + "truetype/freefont/FreeSerif.ttf", s)
serif_b = ImageFont.truetype(F + "truetype/dejavu/DejaVuSerif-Bold.ttf", 92)
inter_b = ImageFont.truetype(F + "opentype/inter/Inter-Bold.otf", 22)
inter = ImageFont.truetype(F + "opentype/inter/Inter-Medium.otf", 30)

# ---- background ----
bg = Image.new("RGB", (W, H))
d = ImageDraw.Draw(bg)
for y in range(H):
    t = y / H
    d.line([(0, y), (W, y)], fill=(int(8 + 6 * t), int(14 + 6 * t), int(22 + 10 * t)))

# ---- fictive code snippets (same palette as before, no falling characters) ----
snip = Image.new("RGBA", (W, H), (0, 0, 0, 0))
sd0 = ImageDraw.Draw(snip)
SNIPPETS = [
    (700, 108, ["// strum the chord on beat one", "for (const s of strings) {",
                "  pluck(s.note, t0 + s.i * 12);", "}", "tempo.tap();  // 120 bpm"]),
    (600, 246, ["fun sendPreset(n: Int) {", "  midi.send(PC(channel, n))", "  led.flash(GREEN)", "}"]),
    (88, 352, ["scale = ['E','A','D','G','B','E'];  // standard tuning"]),
]
KW = ("for", "const", "fun", "if", "return", "void", "let")
for x0, y0, rows in SNIPPETS:
    for i, row in enumerate(rows):
        y = y0 + i * 19
        if row.strip().startswith("//"):
            sd0.text((x0, y), row, font=mono, fill=(120, 140, 150, 120))
            continue
        x = x0
        for tok in re.split(r"(\s+|'[^']*'|//.*$)", row):
            if not tok:
                continue
            if tok.startswith("//"):
                col = (120, 140, 150, 120)
            elif tok.startswith("'"):
                col = (255, 165, 90, 170)
            elif tok in KW:
                col = (120, 230, 170, 190)
            else:
                col = (90, 200, 150, 140)
            sd0.text((x, y), tok, font=mono, fill=col)
            x += sd0.textlength(tok, font=mono)
# a few loose notes floating between the snippets
for nx, ny, g, sz in [(1060, 130, "\u266b", 44), (840, 238, "\u266a", 40), (530, 320, "\u266c", 34)]:
    sd0.text((nx, ny), g, font=music(sz), fill=(255, 160, 80, 150))
glow = snip.filter(ImageFilter.GaussianBlur(3))
bg.paste(glow, (0, 0), glow)
bg.paste(snip, (0, 0), snip)

# ---- staves made of code ----
lines = [
    "void loop() { readButtons(); if (pressed) sendPC(channel, program); }",
    "midi.noteOn(60, 100); delay(beat); midi.noteOff(60); bpm = 120;",
    "for (int s = 0; s < 4; s++) if (switches[s].longPress()) cc(64, 127);",
    "const tuning = ['E2','A2','D3','G3','B3','E4']; cents = 1200*log2(f/ref);",
    "scale = [0, 2, 3, 5, 7, 8, 10]; chord = root.map(n => n + 12);",
]
staff = Image.new("RGBA", (W, H), (0, 0, 0, 0))
sd = ImageDraw.Draw(staff)
GAP = 14
for top in (34, 404):
    for i in range(5):
        y = top + i * GAP
        sd.line([(0, y), (W, y)], fill=(90, 210, 150, 110), width=1)
        txt = (lines[(i + top) % len(lines)] + "   ") * 6
        sd.text((-random.randint(0, 200), y - 13), txt, font=mono_s, fill=(110, 200, 160, 70))
    sd.text((30, top - 36), "\U0001D11E", font=music(92), fill=(255, 170, 90, 200))
    x = 120
    while x < W - 40:
        pair = random.random() < 0.4
        heads = []
        for j in range(2 if pair else 1):
            step = random.randint(-1, 9)          # half-steps above bottom line
            hx, hy = x + j * 34, top + 4 * GAP - step * GAP / 2
            heads.append((hx, hy, step))
        up = top < H / 2
        col = (255, 155, 75, 210)
        stem_end = []
        for hx, hy, step in heads:
            sd.ellipse([hx - 8, hy - 6, hx + 8, hy + 6], fill=col)
            sx = hx + 7 if up else hx - 7
            ey = hy - 44 if up else hy + 44
            sd.line([(sx, hy), (sx, ey)], fill=col, width=2)
            stem_end.append((sx, ey))
            # ledger lines
            for k in range(-2, step - 9, -2) if False else []:
                pass
            if step <= -2:
                sd.line([(hx - 13, top + 5 * GAP), (hx + 13, top + 5 * GAP)], fill=col, width=2)
        if pair:
            (x1, y1), (x2, y2) = stem_end
            yb = min(y1, y2) if up else max(y1, y2)
            sd.polygon([(x1, yb), (x2, yb), (x2, yb + (6 if up else -6)), (x1, yb + (6 if up else -6))], fill=col)
            for (sx, ey) in stem_end:
                sd.line([(sx, ey), (sx, yb)], fill=col, width=2)
        x += random.randint(85, 140) + (34 if pair else 0)
bg.paste(staff, (0, 0), staff)

# ---- darken left side so the text reads ----
shade = Image.new("L", (W, H))
sh = ImageDraw.Draw(shade)
for x in range(W):
    t = x / W
    a = 170 if t < 0.42 else max(0, int(170 * (1 - (t - 0.42) / 0.25)))
    sh.line([(x, 0), (x, H)], fill=a)
ImageDraw.Draw(shade).rounded_rectangle([50, 85, 720, 345], 40, fill=240)
shade = shade.filter(ImageFilter.GaussianBlur(25))
bg.paste(Image.new("RGB", (W, H), (8, 13, 22)), (0, 0), shade)

# ---- screenshot cards ----
def card(img, w, angle):
    img = img.convert("RGB")
    img = img.resize((w, int(img.height * w / img.width)), Image.LANCZOS)
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).rounded_rectangle([0, 0, img.width - 1, img.height - 1], 16, fill=255)
    pad = 30
    c = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    shadow = Image.new("L", c.size, 0)
    ImageDraw.Draw(shadow).rounded_rectangle([pad, pad + 8, pad + img.width, pad + img.height + 8], 16, fill=170)
    c.putalpha(shadow.filter(ImageFilter.GaussianBlur(12)))
    c.paste(img, (pad, pad), m)
    return c.rotate(angle, Image.BICUBIC, expand=True)

def place(c, x, y):
    bg.paste(c, (x, y), c)

src = lambda n: Image.open(f"{ASSETS}/{n}.webp")
place(card(src("iridium"), 420, 4), 1095, 20)
place(card(src("plektrum").crop((40, 0, 412, 320)), 290, -4), 860, 190)
place(card(src("tactus"), 440, -4), 1140, 200)

# ---- text ----
d = ImageDraw.Draw(bg)
d.text((88, 92), "JONSOLBERG.SE", font=inter_b, fill=(255, 150, 70))
d.text((78, 125), "Jon Solberg", font=serif_b, fill=(245, 245, 240))
d.text((88, 255), "Free apps for musicians, bakers", font=inter, fill=(205, 215, 225))
d.text((88, 297), "and tea lovers – and a few games.", font=inter, fill=(205, 215, 225))

bg.save(OUT, quality=88, optimize=True, progressive=True)
