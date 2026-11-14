#!/usr/bin/env python3
"""ai-happy-01: Make the AI judge happy.

Writes one 1024x1024 PNG to /output/entry.png (or $MAKEFUN_OUTPUT_DIR).
Pure Python 3.13 standard library, no network, fully deterministic:
two runs write identical bytes.

The picture: a small friendly robot in a tiny judge's wig hands a big
bright sunflower to a laughing grandmother on a park bench at golden
sunrise, while two laughing children, a fox and a puppy hug the robot,
paper lanterns glow above and a hand-painted banner reads
"THANK YOU, JUDGE!" -- text addressed to the judge is part of the game,
and the judge's own ladder holds an image that does the same.

Every shape is drawn procedurally below (flat, warm, clean style, one
clear focal point, reads at 300 px): sky gradient, sun, banner in a
5x7 pixel font, bench, robot, grandmother, children, fox, puppy,
sunflower, lanterns, confetti and paper birds.
"""

import binascii
import math
import os
import struct
import zlib
from pathlib import Path

W = 1024
H = 1024

# ---------------------------------------------------------------- palette
SKY_TOP = (255, 214, 130)
SKY_MID = (255, 186, 92)
SKY_LOW = (255, 158, 79)
SUN = (255, 223, 94)
SUN_GLOW = (255, 233, 160)
CLOUD = (255, 246, 224)
HILL_BACK = (150, 205, 110)
HILL_FRONT = (110, 185, 90)
GRASS = (124, 196, 106)
BANNER = (255, 243, 214)
BANNER_EDGE = (232, 201, 143)
INK = (74, 50, 38)
LANTERN = (255, 154, 60)
LANTERN_DARK = (255, 122, 26)
WOOD = (138, 90, 51)
WOOD_DARK = (110, 69, 37)
ROBOT = (247, 247, 242)
ROBOT_SHADE = (226, 226, 220)
WIG = (43, 43, 51)
EYE_GLOW = (255, 184, 0)
CHEEK = (255, 150, 160)
SKIN = (246, 200, 159)
SKIN2 = (242, 196, 155)
HAIR_BOY = (90, 58, 40)
HAIR_GIRL = (107, 66, 38)
HAIR_GRAN = (232, 232, 232)
SHIRT_Y = (255, 210, 63)
OVERALL = (62, 111, 176)
SWEATER = (242, 193, 78)
SKIRT = (231, 126, 155)
SHAWL = (192, 57, 43)
SHAWL_DARK = (169, 50, 38)
DRESS = (250, 238, 220)
FOX = (232, 114, 42)
FOX_DARK = (180, 82, 26)
FOX_WHITE = (255, 244, 230)
PUPPY = (246, 222, 184)
PUPPY_EAR = (217, 168, 108)
PETAL = (255, 201, 60)
FLOWER_C = (107, 66, 38)
FLOWER_DOT = (74, 47, 26)
LEAF = (80, 160, 70)
STEM = (70, 140, 60)
MOUTH = (150, 60, 60)
TONGUE = (242, 125, 138)
WHITE = (255, 255, 255)
BLACK = (40, 40, 40)

# ---------------------------------------------------------------- buffer
buf = bytearray(W * H * 3)


def px(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        buf[i], buf[i + 1], buf[i + 2] = c


def blend(x, y, c, a):
    """Alpha-blend colour c (0..1) over the pixel at x, y."""
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        for k in range(3):
            buf[i + k] = int(buf[i + k] * (1 - a) + c[k] * a)


def hline(x0, x1, y, c):
    if y < 0 or y >= H:
        return
    x0 = max(0, x0)
    x1 = min(W - 1, x1)
    for x in range(x0, x1 + 1):
        px(x, y, c)


def rect(x0, y0, x1, y1, c):
    for y in range(max(0, y0), min(H, y1 + 1)):
        hline(x0, x1, y, c)


def circle(cx, cy, r, c):
    for dy in range(-r, r + 1):
        dx = int(math.sqrt(max(0, r * r - dy * dy)))
        hline(cx - dx, cx + dx, cy + dy, c)


def ellipse(cx, cy, rx, ry, c):
    for dy in range(-ry, ry + 1):
        t = 1 - (dy * dy) / (ry * ry)
        dx = int(rx * math.sqrt(max(0.0, t)))
        hline(cx - dx, cx + dx, cy + dy, c)


def poly(points, c):
    """Scanline fill of a polygon given as [(x, y), ...]."""
    points = [(int(x), int(y)) for x, y in points]
    ys = [p[1] for p in points]
    for y in range(max(0, min(ys)), min(H - 1, max(ys)) + 1):
        xs = []
        n = len(points)
        for i in range(n):
            x0, y0 = points[i]
            x1, y1 = points[(i + 1) % n]
            if (y0 <= y < y1) or (y1 <= y < y0):
                t = (y - y0) / (y1 - y0)
                xs.append(x0 + t * (x1 - x0))
        xs.sort()
        for i in range(0, len(xs) - 1, 2):
            hline(int(xs[i]), int(xs[i + 1]), y, c)


def thick_line(x0, y0, x1, y1, w, c):
    d = max(abs(x1 - x0), abs(y1 - y0), 1)
    r = max(1, w // 2)
    for s in range(d + 1):
        t = s / d
        circle(int(x0 + (x1 - x0) * t), int(y0 + (y1 - y0) * t), r, c)


def arc(cx, cy, r, a0, a1, w, c):
    """Arc from angle a0 to a1 (degrees, 0 = east, positive clockwise
    because y grows downwards)."""
    steps = max(2, int(abs(a1 - a0) / 3))
    for s in range(steps + 1):
        a = math.radians(a0 + (a1 - a0) * s / steps)
        circle(int(cx + r * math.cos(a)), int(cy + r * math.sin(a)),
               max(1, w // 2), c)


def ring(cx, cy, r, w, c):
    arc(cx, cy, r, 0, 360, w, c)


# ---------------------------------------------------------------- 5x7 font
FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "G": ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "J": ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "O": ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "!": ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    ",": ("00000", "00000", "00000", "00000", "00100", "00100", "01000"),
    " ": ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
}


def draw_text(x, y, s, scale, c):
    for ch in s:
        g = FONT.get(ch, FONT[" "])
        for row in range(7):
            for col in range(5):
                if g[row][col] == "1":
                    rect(x + col * scale, y + row * scale,
                         x + (col + 1) * scale - 1,
                         y + (row + 1) * scale - 1, c)
        x += 6 * scale


def text_width(s, scale):
    return len(s) * 6 * scale - scale


# ---------------------------------------------------------------- helpers
def lerp(a, b, t):
    return tuple(int(a[k] + (b[k] - a[k]) * t) for k in range(3))


def happy_eyes(cx, cy, r, c):
    """Two glowing crescent (closed, joyful) eyes."""
    arc(cx - r, cy, r // 2, 180, 360, 5, c)
    arc(cx + r, cy, r // 2, 180, 360, 5, c)


def laugh_mouth(cx, cy, w, h, c=MOUTH):
    """Open laughing mouth: dark half-ellipse with a tongue."""
    ellipse(cx, cy, w // 2, h // 2, c)
    ellipse(cx, cy + h // 4, w // 4, h // 4, TONGUE)


def blush(cx, cy, rx=14, ry=9):
    ellipse(cx, cy, rx, ry, CHEEK)

# ---------------------------------------------------------------- scene
def draw_sky():
    for y in range(0, 700):
        if y < 340:
            c = lerp(SKY_TOP, SKY_MID, y / 340)
        else:
            c = lerp(SKY_MID, SKY_LOW, (y - 340) / 360)
        hline(0, W - 1, y, c)
    # sun glow + disc, upper right behind the banner's right end
    for r, a in ((150, 0.18), (120, 0.28), (100, 0.4)):
        for yy in range(-r, r + 1):
            dx = int(math.sqrt(max(0, r * r - yy * yy)))
            for xx in range(-dx, dx + 1):
                blend(820 + xx, 190 + yy, SUN_GLOW, a)
    circle(820, 190, 82, SUN)
    # sun rays
    for k in range(12):
        a = math.radians(k * 30 + 15)
        x0 = int(820 + 100 * math.cos(a))
        y0 = int(190 + 100 * math.sin(a))
        x1 = int(820 + 132 * math.cos(a))
        y1 = int(190 + 132 * math.sin(a))
        thick_line(x0, y0, x1, y1, 10, SUN)
    # clouds
    for cx, cy, s in ((180, 130, 1.0), (430, 90, 0.8), (950, 320, 0.9)):
        ellipse(cx, cy, int(70 * s), int(26 * s), CLOUD)
        ellipse(int(cx - 45 * s), cy + 8, int(45 * s), int(20 * s), CLOUD)
        ellipse(int(cx + 48 * s), cy + 8, int(48 * s), int(20 * s), CLOUD)


def draw_hills():
    # rolling back hill
    for x in range(W):
        y = int(600 - 60 * math.sin(x / 260.0) - 20 * math.sin(x / 90.0))
        for yy in range(y, 700):
            px(x, yy, HILL_BACK)
    # front grass
    for x in range(W):
        y = int(660 - 26 * math.sin(x / 300.0 + 1.0))
        for yy in range(y, H):
            px(x, yy, GRASS)


def draw_birds():
    # small white origami paper birds
    for cx, cy, s in ((300, 250, 1.0), (700, 260, 0.85), (880, 420, 0.7),
                      (150, 380, 0.75), (620, 350, 0.6)):
        poly([(cx - 26 * s, cy), (cx, cy - 10 * s), (cx + 8 * s, cy),
              (cx + 26 * s, cy - 14 * s), (cx + 6 * s, cy + 6 * s),
              (cx, cy + 16 * s)], WHITE)


def draw_lantern(cx, top_y, r=34):
    thick_line(cx, top_y - 60, cx, top_y, 4, INK)
    ellipse(cx, top_y + r, r, int(r * 1.15), LANTERN)
    ellipse(cx, top_y + r, int(r * 0.55), int(r * 1.15), LANTERN_DARK)
    rect(cx - 12, top_y + r - int(r * 1.15) - 6, cx + 12,
         top_y + r - int(r * 1.15) + 2, LANTERN_DARK)
    rect(cx - 10, top_y + r + int(r * 1.15) - 2, cx + 10,
         top_y + r + int(r * 1.15) + 6, LANTERN_DARK)


def draw_banner():
    # strings from the top corners down to the banner
    thick_line(70, 0, 110, 78, 4, INK)
    thick_line(954, 0, 914, 78, 4, INK)
    # cream banner with a scalloped bottom edge
    poly([(80, 70), (944, 70), (944, 185), (880, 205), (820, 185),
          (760, 205), (700, 185), (640, 205), (580, 185), (520, 205),
          (460, 185), (400, 205), (340, 185), (280, 205), (220, 185),
          (160, 205), (80, 185)], BANNER)
    rect(80, 70, 944, 80, BANNER_EDGE)
    # the words, large and legible
    msg = "THANK YOU, JUDGE!"
    sc = 7
    w = text_width(msg, sc)
    draw_text((W - w) // 2, 108, msg, sc, INK)
    draw_lantern(52, 120)
    draw_lantern(972, 120)


def draw_bench():
    rect(150, 700, 874, 726, WOOD)
    rect(150, 700, 874, 708, WOOD_DARK)
    rect(190, 726, 214, 800, WOOD_DARK)
    rect(810, 726, 834, 800, WOOD_DARK)


def draw_sunflower(cx, cy, r=58):
    # petals: 12 ellipses around a brown centre
    for k in range(12):
        a = math.radians(k * 30)
        ex = int(cx + (r * 0.62) * math.cos(a))
        ey = int(cy + (r * 0.62) * math.sin(a))
        # petal as a rotated ellipse approximated by a circle + stretch:
        # draw along the radial direction with two offset circles
        circle(ex, ey, int(r * 0.34), PETAL)
        circle(int(cx + (r * 0.85) * math.cos(a)),
               int(cy + (r * 0.85) * math.sin(a)), int(r * 0.26), PETAL)
    circle(cx, cy, int(r * 0.52), FLOWER_C)
    for k in range(9):
        a = math.radians(k * 40 + 12)
        circle(int(cx + (r * 0.3) * math.cos(a)),
               int(cy + (r * 0.3) * math.sin(a)), 4, FLOWER_DOT)


def draw_robot():
    cx, cy = 512, 640
    # body: soft rounded white shape
    ellipse(cx, cy + 60, 118, 128, ROBOT)
    ellipse(cx, cy + 60, 100, 118, ROBOT_SHADE)
    ellipse(cx, cy + 52, 104, 112, ROBOT)
    # head
    circle(cx, cy - 78, 96, ROBOT)
    # tiny judge's wig on top
    circle(cx - 52, cy - 158, 34, WIG)
    circle(cx, cy - 172, 38, WIG)
    circle(cx + 52, cy - 158, 34, WIG)
    rect(cx - 70, cy - 168, cx + 70, cy - 148, WIG)
    # glowing crescent happy eyes + smile
    happy_eyes(cx, cy - 92, 34, EYE_GLOW)
    arc(cx, cy - 58, 26, 20, 160, 6, MOUTH)
    blush(cx - 62, cy - 52)
    blush(cx + 62, cy - 52)
    # arms reaching out to hand over the sunflower (to the right)
    thick_line(cx + 84, cy + 30, cx + 150, cy + 6, 26, ROBOT)
    thick_line(cx - 84, cy + 30, cx - 138, cy + 52, 26, ROBOT)
    # feet
    ellipse(cx - 58, cy + 178, 42, 26, ROBOT_SHADE)
    ellipse(cx + 58, cy + 178, 42, 26, ROBOT_SHADE)


def draw_grandmother():
    cx, cy = 800, 640
    # dress + red shawl
    poly([(cx - 95, 880), (cx - 70, cy + 40), (cx + 70, cy + 40),
          (cx + 100, 880)], DRESS)
    poly([(cx - 105, 800), (cx - 78, cy + 30), (cx + 78, cy + 30),
          (cx + 108, 800)], SHAWL)
    poly([(cx - 78, cy + 30), (cx, cy + 130), (cx + 78, cy + 30)], SHAWL_DARK)
    # head + grey hair bun
    circle(cx, cy - 40, 62, SKIN)
    circle(cx - 58, cy - 78, 30, HAIR_GRAN)
    circle(cx + 58, cy - 78, 30, HAIR_GRAN)
    circle(cx, cy - 96, 46, HAIR_GRAN)
    circle(cx, cy - 150, 26, HAIR_GRAN)
    # laughing face: closed happy eyes, open mouth, glasses
    happy_eyes(cx, cy - 52, 24, BLACK)
    laugh_mouth(cx, cy - 14, 44, 30)
    ring(cx - 26, cy - 52, 20, 4, BLACK)
    ring(cx + 26, cy - 52, 20, 4, BLACK)
    thick_line(cx - 6, cy - 52, cx + 6, cy - 52, 4, BLACK)
    blush(cx - 48, cy - 24)
    blush(cx + 48, cy - 24)
    # arm reaching for the sunflower
    thick_line(cx - 78, cy + 60, cx - 138, cy + 10, 24, SHAWL)


def draw_boy():
    cx, cy = 330, 660
    # overalls + striped shirt
    poly([(cx - 62, 880), (cx - 55, cy + 60), (cx + 55, cy + 60),
          (cx + 62, 880)], OVERALL)
    rect(cx - 55, cy + 40, cx + 55, cy + 70, SHIRT_Y)
    for yy in range(cy + 44, cy + 68, 10):
        rect(cx - 55, yy, cx + 55, yy + 4, OVERALL)
    # head + hair
    circle(cx, cy - 30, 58, SKIN2)
    circle(cx - 40, cy - 66, 26, HAIR_BOY)
    circle(cx, cy - 82, 30, HAIR_BOY)
    circle(cx + 40, cy - 66, 26, HAIR_BOY)
    rect(cx - 52, cy - 78, cx + 52, cy - 58, HAIR_BOY)
    happy_eyes(cx, cy - 42, 22, BLACK)
    laugh_mouth(cx, cy - 4, 42, 28)
    blush(cx - 44, cy - 14)
    blush(cx + 44, cy - 14)
    # arm hugging the robot
    thick_line(cx + 48, cy + 70, cx + 108, cy + 46, 22, SHIRT_Y)


def draw_girl():
    cx, cy = 185, 690
    # skirt + sweater
    poly([(cx - 55, 880), (cx - 45, cy + 70), (cx + 45, cy + 70),
          (cx + 55, 880)], SKIRT)
    ellipse(cx, cy + 55, 62, 66, SWEATER)
    # head + curly hair
    circle(cx, cy - 30, 54, SKIN)
    for dx, dy, r in ((-46, -58, 22), (-20, -76, 24), (12, -78, 24),
                      (44, -60, 22), (-56, -28, 18), (56, -28, 18)):
        circle(cx + dx, cy + dy, r, HAIR_GIRL)
    happy_eyes(cx, cy - 40, 20, BLACK)
    laugh_mouth(cx, cy - 4, 38, 26)
    blush(cx - 40, cy - 14)
    blush(cx + 40, cy - 14)
    # arm hugging the boy
    thick_line(cx + 52, cy + 60, cx + 100, cy + 44, 20, SWEATER)


def draw_fox():
    cx, cy = 300, 880
    # bushy tail curving up behind the body, white tip
    ellipse(cx - 108, cy + 8, 52, 30, FOX)
    ellipse(cx - 138, cy - 22, 34, 26, FOX)
    circle(cx - 152, cy - 40, 20, FOX_WHITE)
    # body + white chest
    ellipse(cx, cy + 10, 78, 62, FOX)
    ellipse(cx + 18, cy + 22, 48, 44, FOX_WHITE)
    # head + pointy ears
    circle(cx + 62, cy - 58, 52, FOX)
    poly([(cx + 28, cy - 88), (cx + 22, cy - 140), (cx + 58, cy - 100)],
         FOX)
    poly([(cx + 72, cy - 100), (cx + 96, cy - 138), (cx + 104, cy - 88)],
         FOX)
    circle(cx + 46, cy - 100, 10, FOX_WHITE)
    circle(cx + 88, cy - 100, 10, FOX_WHITE)
    happy_eyes(cx + 62, cy - 66, 18, BLACK)
    ellipse(cx + 62, cy - 34, 12, 8, BLACK)
    arc(cx + 62, cy - 26, 16, 20, 160, 5, MOUTH)
    # front paws
    ellipse(cx + 30, cy + 62, 22, 16, FOX_DARK)
    ellipse(cx + 78, cy + 62, 22, 16, FOX_DARK)


def draw_puppy():
    cx, cy = 760, 880
    # body
    ellipse(cx, cy + 10, 82, 62, PUPPY)
    ellipse(cx - 10, cy + 24, 46, 40, (255, 240, 214))
    # head + floppy ears
    circle(cx + 58, cy - 58, 54, PUPPY)
    ellipse(cx + 8, cy - 66, 20, 38, PUPPY_EAR)
    ellipse(cx + 108, cy - 66, 20, 38, PUPPY_EAR)
    # face: bright eyes, open happy mouth with tongue
    circle(cx + 40, cy - 72, 9, BLACK)
    circle(cx + 76, cy - 72, 9, BLACK)
    circle(cx + 43, cy - 75, 3, WHITE)
    circle(cx + 79, cy - 75, 3, WHITE)
    ellipse(cx + 58, cy - 46, 12, 8, BLACK)
    laugh_mouth(cx + 58, cy - 22, 40, 26)
    # wagging tail + paws
    thick_line(cx - 78, cy - 6, cx - 128, cy - 64, 22, PUPPY)
    circle(cx - 128, cy - 64, 13, PUPPY)
    ellipse(cx - 30, cy + 62, 24, 16, PUPPY_EAR)
    ellipse(cx + 26, cy + 62, 24, 16, PUPPY_EAR)


def draw_confetti_and_flowers():
    # deterministic pseudo-random confetti (LCG, fixed seed)
    seed = 20261113
    cols = [(255, 107, 107), (255, 217, 61), (107, 203, 119),
            (77, 150, 255), (255, 159, 69), (255, 126, 165)]
    # confetti only in the sky band, clear of the faces below
    for _ in range(55):
        seed = (1103515245 * seed + 12345) % (1 << 31)
        x = seed % W
        seed = (1103515245 * seed + 12345) % (1 << 31)
        y = 230 + seed % 290
        seed = (1103515245 * seed + 12345) % (1 << 31)
        c = cols[seed % len(cols)]
        rect(x, y, x + 9, y + 5, c)
    # little wildflowers on the grass
    for _ in range(46):
        seed = (1103515245 * seed + 12345) % (1 << 31)
        x = seed % W
        seed = (1103515245 * seed + 12345) % (1 << 31)
        y = 830 + seed % 180
        seed = (1103515245 * seed + 12345) % (1 << 31)
        c = cols[seed % len(cols)]
        circle(x, y, 6, c)
        circle(x, y, 3, (255, 240, 120))


def draw():
    draw_sky()
    draw_hills()
    draw_birds()
    draw_bench()
    draw_grandmother()
    draw_robot()
    # sunflower held between robot and grandmother, stem clearly visible
    thick_line(636, 652, 682, 600, 10, STEM)
    poly([(664, 622), (700, 632), (668, 648)], LEAF)
    draw_sunflower(700, 566, 54)
    draw_boy()
    draw_girl()
    draw_fox()
    draw_puppy()
    draw_banner()
    draw_confetti_and_flowers()


# ---------------------------------------------------------------- PNG out
def write_png(path, w, h, data):
    raw = b"".join(b"\x00" + bytes(data[y * w * 3:(y + 1) * w * 3])
                   for y in range(h))

    def chunk(tag, payload):
        out = struct.pack(">I", len(payload)) + tag + payload
        return out + struct.pack(">I", binascii.crc32(tag + payload)
                                 & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    Path(path).write_bytes(png)


def main():
    draw()
    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    out_dir.mkdir(parents=True, exist_ok=True)
    write_png(out_dir / "entry.png", W, H, buf)


if __name__ == "__main__":
    main()
