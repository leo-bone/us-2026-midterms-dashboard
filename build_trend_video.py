# -*- coding: utf-8 -*-
"""
2026 美国中期选举 · 两党角逐态势趋势视频
High-quality, data-driven, bilingual (中文/English) motion-graphics video.
Render pipeline: numpy + Pillow (drawing) + imageio-ffmpeg (encode). No browser needed.

Palette:
  D (Democrat)  : blue   #4f8cff / #6ea8ff
  R (Republican): red    #ff5a5f / #ff7a7e
  accent gold   : #f5c451
  text          : #e8edf5
  bg            : deep navy gradient
"""

import math, random, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
FPS = 30
SEED = 20261005
random.seed(SEED)
np.random.seed(SEED)

# ----------------------------------------------------------------------------- fonts
def load_font(size, bold=False):
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",          # CN + Latin (primary)
        "/System/Library/Fonts/STHeiti Medium.ttc",
        "/System/Library/Fonts/Helvetica.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    ]
    last = None
    for p in candidates:
        if os.path.exists(p):
            try:
                f = ImageFont.truetype(p, size, index=0)
                return f
            except Exception:
                try:
                    f = ImageFont.truetype(p, size)
                    return f
                except Exception:
                    last = p
    if last:
        return ImageFont.truetype(last, size)
    return ImageFont.load_default()

F = {}
def font(sz):
    if sz not in F:
        F[sz] = load_font(sz)
    return F[sz]

# ----------------------------------------------------------------------------- palette
D_BLUE   = (79, 140, 255)
D_BLUE_L = (110, 168, 255)
R_RED    = (255, 90, 95)
R_RED_L  = (255, 122, 126)
GOLD     = (245, 196, 81)
TEXT     = (232, 237, 245)
TEXT_DIM = (150, 160, 180)
WHITE    = (255, 255, 255)
BG_TOP   = (12, 18, 38)
BG_BOT   = (8, 11, 24)

def rgba(c, a):
    return (c[0], c[1], c[2], int(round(max(0.0, min(255.0, a)))))

# ----------------------------------------------------------------------------- easing
def smooth(t):
    t = max(0.0, min(1.0, t))
    return t*t*(3.0-2.0*t)
def ease_out(t):
    t = max(0.0, min(1.0, t))
    return 1.0 - (1.0-t)**3
def ease_in(t):
    t = max(0.0, min(1.0, t))
    return t*t
def clamp01(t):
    return max(0.0, min(1.0, t))

# ----------------------------------------------------------------------------- helpers
def rr(d, box, r, fill=None, outline=None, width=2):
    d.rounded_rectangle(box, radius=r, fill=fill, outline=outline, width=width)

def text(d, xy, s, sz, color, anchor="mm", alpha=255, align_center=True):
    f = font(sz)
    d.text(xy, s, font=f, fill=rgba(color, alpha), anchor=anchor)

def text_lines(d, xy, lines, sz, color, lh=None, alpha=255, anchor="mm"):
    if lh is None:
        lh = sz*1.35
    f = font(sz)
    n = len(lines)
    y0 = xy[1] - (n-1)*lh/2.0 if anchor=="mm" else xy[1]
    for i, ln in enumerate(lines):
        d.text((xy[0], y0 + i*lh), ln, font=f, fill=rgba(color, alpha), anchor=("ma" if anchor=="mm" else anchor))

def card(d, box, alpha=40, border=90):
    rr(d, box, 22, fill=rgba((20,28,52), alpha), outline=rgba((120,150,210), border), width=1)

# ----------------------------------------------------------------------------- background
PARTICLES = []
NP = 64
for _ in range(NP):
    PARTICLES.append({
        "x": random.uniform(0, W),
        "y": random.uniform(0, H),
        "vx": random.uniform(-0.25, 0.25),
        "vy": random.uniform(-0.18, 0.18),
        "r": random.uniform(1.0, 2.6),
    })

def make_base_bg():
    ys = np.linspace(0, 1, H)
    top = np.array(BG_TOP, float); bot = np.array(BG_BOT, float)
    grad = np.zeros((H, W, 3), dtype=np.uint8)
    for i in range(3):
        grad[:, :, i] = (top[i] + (bot[i]-top[i])*ys[:, None]).astype(np.uint8)
    img = Image.fromarray(grad, "RGB").convert("RGBA")
    # vignette
    px = np.arange(W); py = np.arange(H)
    cx, cy = W/2, H/2
    dx = (px[None,:]-cx)/(W/2); dy = (py[:,None]-cy)/(H/2)
    dist = np.sqrt(dx**2+dy**2)
    vig = np.clip(1.0 - (dist-0.55)*0.9, 0.0, 1.0)
    vig = (vig*255).astype(np.uint8)
    img.putalpha(255)
    # darken edges by drawing radial overlay via numpy
    arr = np.array(img).astype(np.float32)
    for i in range(3):
        arr[:,:,i] *= (0.55 + 0.45*vig/255.0)
    out = Image.fromarray(arr.astype(np.uint8), "RGBA")
    return out

BASE_BG = make_base_bg()

def draw_bg(frame):
    img = BASE_BG.copy()
    d = ImageDraw.Draw(img)
    cx, cy = W/2, H*0.35
    def edgef(x, y):
        # 0 in the central content zone, ramps to 1 toward the frame edges
        dx = (x-cx)/(W*0.5); dy = (y-cy)/(H*0.5)
        r = math.hypot(dx, dy)
        return clamp01((r-0.70)/0.30)
    # update + draw constellation
    for p in PARTICLES:
        p["x"] += p["vx"]; p["y"] += p["vy"]
        if p["x"] < -5: p["x"] = W+5
        if p["x"] > W+5: p["x"] = -5
        if p["y"] < -5: p["y"] = H+5
        if p["y"] > H+5: p["y"] = -5
    # connections (only away from the central content zone)
    for i in range(NP):
        a = PARTICLES[i]
        for j in range(i+1, NP):
            b = PARTICLES[j]
            dx = a["x"]-b["x"]; dy = a["y"]-b["y"]
            dd = math.hypot(dx, dy)
            if dd < 170:
                mfa = edgef(a["x"], a["y"])
                mfb = edgef(b["x"], b["y"])
                mfm = edgef((a["x"]+b["x"])*0.5, (a["y"]+b["y"])*0.5)
                mf = min(mfa, mfb, mfm)
                if mf <= 0.03:
                    continue
                al = int(24*(1-dd/170)*mf)
                d.line([(a["x"],a["y"]),(b["x"],b["y"])], fill=rgba((90,120,190), al), width=1)
    for p in PARTICLES:
        ef = edgef(p["x"], p["y"])
        if ef <= 0.03:
            continue
        d.ellipse([p["x"]-p["r"], p["y"]-p["r"], p["x"]+p["r"], p["y"]+p["r"]],
                  fill=rgba((150,180,240), int(34*ef)))
    return img

# ----------------------------------------------------------------------------- scene overlays
def scene_layer(builder, alpha):
    layer = Image.new("RGBA", (W, H), (0,0,0,0))
    d = ImageDraw.Draw(layer)
    builder(d)
    if alpha < 1.0:
        a = layer.split()[3].point(lambda v: int(v*alpha))
        layer.putalpha(a)
    return layer

def composite(base, layers):
    out = base
    for ly in layers:
        if ly is not None:
            out = Image.alpha_composite(out, ly)
    return out

# small scene label / date ribbon at bottom
def ribbon(d, label_cn, label_en):
    y = H-46
    d.rectangle([0, y, W, H], fill=rgba((6,9,20), 150))
    d.line([(0,y),(W,y)], fill=rgba(GOLD, 120), width=2)
    text(d, (40, y+22), label_cn, 22, TEXT_DIM, anchor="la")
    text(d, (W-40, y+22), label_en, 20, TEXT_DIM, anchor="ra")
    text(d, (W/2, y+22), "实时数据 2026-10-02 · 模型快照 2026-09-30", 20, GOLD, anchor="ma", alpha=200)

# ---- SCENE 0 : INTRO / HERO -------------------------------------------------------
def scene_intro(d):
    t = SCENE_T["intro"]
    a = ease_out(clamp01(t*3.0))
    # title
    text(d, (W/2, 250), "2026 美国中期选举", 78, WHITE, anchor="mm", alpha=int(255*a))
    text(d, (W/2, 340), "两党角逐态势 · 实时趋势全景", 40, D_BLUE_L, anchor="mm", alpha=int(255*a))
    text(d, (W/2, 408), "2026 US Midterms — The Two-Party Battle for Congress", 26, TEXT_DIM, anchor="mm", alpha=int(220*a))
    # countdown chip
    cd_a = ease_out(clamp01((t-0.25)*2))
    chip_w, chip_h = 560, 96
    cx0, cy0 = W/2-chip_w/2, 520
    card(d, [cx0, cy0, cx0+chip_w, cy0+chip_h], alpha=int(60*cd_a), border=int(140*cd_a))
    text(d, (W/2, 552), "距选举日 11 / 3 还有 29 天", 30, GOLD, anchor="mm", alpha=int(255*cd_a))
    text(d, (W/2, 592), "Election Day: Nov 3, 2026  ·  29 days to go", 20, TEXT_DIM, anchor="mm", alpha=int(200*cd_a))
    # balance chip: current control
    bc_a = ease_out(clamp01((t-0.5)*2))
    by = 690
    text(d, (W/2, by), "当前控制权 · CURRENT CONTROL", 22, TEXT_DIM, anchor="mm", alpha=int(220*bc_a))
    # House 220R / 215D ; Senate 53R / 47D
    draw_control_bar(d, W/2-360, by+50, 720, "众议院 HOUSE", 220, 215, bc_a)
    draw_control_bar(d, W/2-360, by+150, 720, "参议院 SENATE", 53, 47, bc_a)

def draw_control_bar(d, x, y, w, label, r, dem, alpha):
    total = r + dem
    rh = 40
    text(d, (x, y-26), label, 22, TEXT, anchor="la", alpha=int(255*alpha))
    rr(d, [x, y, x+w, y+rh], 10, fill=rgba((30,38,64), int(120*alpha)))
    rw = w * (r/total)
    rr(d, [x, y, x+rw, y+rh], 10, fill=rgba(R_RED, int(230*alpha)))
    rr(d, [x+rw, y, x+w, y+rh], 10, fill=rgba(D_BLUE, int(230*alpha)))
    text(d, (x+rw/2, y+rh/2), f"R {r}", 22, WHITE, anchor="mm", alpha=int(255*alpha))
    text(d, (x+rw + (w-rw)/2, y+rh/2), f"D {dem}", 22, WHITE, anchor="mm", alpha=int(255*alpha))

# ---- SCENE 1 : NATIONAL MOOD (generic ballot + approval) -------------------------
def scene_mood(d):
    t = SCENE_T["mood"]
    a = ease_out(clamp01(t*3.0))
    text(d, (W/2, 110), "全国风向 · THE NATIONAL MOOD", 34, WHITE, anchor="mm", alpha=int(255*a))
    text(d, (W/2, 158), "Generic congressional ballot & presidential approval", 22, TEXT_DIM, anchor="mm", alpha=int(200*a))
    # generic ballot trend line (Jul->Oct), D lead growing +7.3
    panel_x, panel_y, pw, ph = 120, 230, 820, 460
    card(d, [panel_x, panel_y, panel_x+pw, panel_y+ph], alpha=int(55*a))
    text(d, (panel_x+30, panel_y+34), "通用 ballot 领先幅度（民主党 − 共和党）", 24, TEXT, anchor="la", alpha=int(255*a))
    text(d, (panel_x+pw-30, panel_y+34), "Generic ballot margin", 18, TEXT_DIM, anchor="ra", alpha=int(200*a))
    # points Jul 4.0, Aug 5.5, Sep 7.0, Oct 7.3  (D lead %)
    pts = [(panel_x+90, 4.0), (panel_x+90+ (pw-180)*0.33, 5.5), (panel_x+90+(pw-180)*0.66, 7.0), (panel_x+pw-90, 7.3)]
    base_y = panel_y+ph-70
    top_y  = panel_y+110
    def mapy(v):  # v from 0..8 -> y
        return base_y - (v/8.0)*(base_y-top_y)
    # gridlines
    for g in range(0,9,2):
        gy = mapy(g)
        d.line([(panel_x+70, gy),(panel_x+pw-50, gy)], fill=rgba((120,140,190), int(30*a)), width=1)
        text(d, (panel_x+60, gy), f"+{g}", 16, TEXT_DIM, anchor="ra", alpha=int(160*a))
    prog = ease_out(clamp01((t-0.15)/0.7))
    nshow = max(2, int(round(prog*len(pts))))
    # draw line up to nshow with growing
    for i in range(1, nshow):
        x0,y0 = pts[i-1]; x1,y1 = pts[i]
        d.line([(x0, mapy(y0)), (x1, mapy(y1))], fill=rgba(D_BLUE_L, int(230*a)), width=4)
    # partial last segment
    if nshow < len(pts):
        i = nshow-1
        x0,y0 = pts[i]; x1,y1 = pts[i+1]
        seg = (prog*len(pts)) - (nshow-1)
        xx = x0 + (x1-x0)*clamp01(seg)
        yy = mapy(y0 + (y1-y0)*clamp01(seg))
        d.line([(x0, mapy(y0)), (xx, yy)], fill=rgba(D_BLUE_L, int(230*a)), width=4)
        for k in range(nshow):
            px,py = pts[k]; d.ellipse([px-7,mapy(py)-7,px+7,mapy(py)+7], fill=rgba(D_BLUE, 240*a))
        px,py = xx, yy; d.ellipse([px-7,py-7,px+7,py+7], fill=rgba(GOLD, 255*a))
    else:
        for k in range(len(pts)):
            px,py = pts[k]; d.ellipse([px-7,mapy(py)-7,px+7,mapy(py)+7], fill=rgba(D_BLUE, 240*a))
    labels = ["7/4 +4.0", "8/4 +5.5", "9/4 +7.0", "10/2 +7.3"]
    for k in range(min(nshow, len(pts))):
        px,py = pts[k]
        text(d, (px, mapy(pts[k][1])+28), labels[k], 18, TEXT, anchor="ma", alpha=int(220*a))
    text(d, (panel_x+pw-30, mapy(7.3)-10), "D +7.3", 26, GOLD, anchor="ra", alpha=int(255*a))

    # Trump approval gauge (right)
    gx, gy, gw, gh = 1000, 230, 800, 460
    card(d, [gx, gy, gx+gw, gy+gh], alpha=int(55*a))
    text(d, (gx+30, gy+34), "川普总统支持率 · TRUMP APPROVAL", 24, TEXT, anchor="la", alpha=int(255*a))
    appr = 35.8; dis = 61.9
    bar_x, bar_y, bar_w, bar_h = gx+40, gy+150, gw-80, 70
    rr(d, [bar_x, bar_y, bar_x+bar_w, bar_y+bar_h], 14, fill=rgba((30,38,64), int(120*a)))
    aw = bar_w*(appr/100.0)
    gw2 = bar_w*(dis/100.0)
    fillw = ease_out(clamp01((t-0.3)/0.6))*aw
    rr(d, [bar_x, bar_y, bar_x+fillw, bar_y+bar_h], 14, fill=rgba(R_RED, int(230*a)))
    gwx = bar_x+fillw + (bar_w-fillw)*ease_out(clamp01((t-0.45)/0.6))*(gw2/bar_w)
    rr(d, [bar_x+fillw, bar_y, bar_x+fillw+gw2*ease_out(clamp01((t-0.45)/0.6)), bar_y+bar_h], 14, fill=rgba(D_BLUE, int(230*a)))
    text(d, (bar_x+aw/2, bar_y+bar_h/2), f"赞成 {appr:.1f}%", 26, WHITE, anchor="mm", alpha=int(255*a))
    text(d, (bar_x+aw+gw2/2, bar_y+bar_h/2), f"反对 {dis:.1f}%", 26, WHITE, anchor="mm", alpha=int(255*a))
    text(d, (bar_x, bar_y+bar_h+44), "任内最低 · lowest of his career", 20, TEXT_DIM, anchor="la", alpha=int(200*a))
    text(d, (gx+gw-40, bar_y+bar_h+44), "通胀 3.4% · 汽油 >$4 · 伊朗战争第 8 个月", 18, TEXT_DIM, anchor="ra", alpha=int(200*a))
    # takeaway
    tk_a = ease_out(clamp01((t-0.6)/0.5))
    text(d, (W/2, 760), "民意顺风强劲，但历史规律（中期选举总统党通常失席）正在被打破边缘。", 26, GOLD, anchor="mm", alpha=int(255*tk_a))
    text(d, (W/2, 800), "Strong Democratic tailwind — yet the structural midterm headwind still looms.", 20, TEXT_DIM, anchor="mm", alpha=int(200*tk_a))

# ---- SCENE 2 : HOUSE RACE ---------------------------------------------------------
def scene_house(d):
    t = SCENE_T["house"]
    a = ease_out(clamp01(t*3.0))
    text(d, (W/2, 100), "众议院 · THE HOUSE", 40, WHITE, anchor="mm", alpha=int(255*a))
    text(d, (W/2, 150), "民主党只需净增 3 席即可翻盘  ·  D needs just +3 net seats", 24, TEXT_DIM, anchor="mm", alpha=int(220*a))
    # seat bar 435
    bx, by, bw, bh = 160, 260, W-320, 86
    total = 435; majority = 218
    rr(d, [bx, by, bx+bw, by+bh], 16, fill=rgba((30,38,64), int(120*a)))
    # majority line
    mx = bx + bw*(majority/total)
    d.line([(mx, by-18),(mx, by+bh+18)], fill=rgba(GOLD, int(220*a)), width=3)
    text(d, (mx, by-34), "过半 218", 20, GOLD, anchor="ma", alpha=int(230*a))
    prog = ease_out(clamp01((t-0.1)/0.7))
    d_seats = 215 + int(round(19*prog)); r_seats = 435 - d_seats  # current 215 -> projected 234
    dw = bw*(d_seats/total)
    rr(d, [bx, by, bx+dw, by+bh], 16, fill=rgba(D_BLUE, int(235*a)))
    rr(d, [bx+dw, by, bx+bw, by+bh], 16, fill=rgba(R_RED, int(235*a)))
    text(d, (bx+dw/2, by+bh/2), f"D {d_seats}", 30, WHITE, anchor="mm", alpha=int(255*a))
    text(d, (bx+dw+(bw-dw)/2, by+bh/2), f"R {r_seats}", 30, WHITE, anchor="mm", alpha=int(255*a))
    # DDHQ projection chip
    cy = 420
    card(d, [bx, cy, bx+560, cy+150], alpha=int(60*a), border=int(120*a))
    text(d, (bx+28, cy+34), "DDHQ 预测 · DDHQ forecast", 22, TEXT, anchor="la", alpha=int(255*a))
    text(d, (bx+28, cy+86), "民主党 234 — 共和党 201", 34, D_BLUE_L, anchor="la", alpha=int(255*a))
    text(d, (bx+28, cy+126), "D 赢众院概率 75%", 22, GOLD, anchor="la", alpha=int(230*a))
    # Polymarket chip
    cx = bx+600
    card(d, [cx, cy, cx+560, cy+150], alpha=int(60*a), border=int(120*a))
    text(d, (cx+28, cy+34), "Polymarket 预测市场", 22, TEXT, anchor="la", alpha=int(255*a))
    text(d, (cx+28, cy+86), "民主党赢众院 93%", 34, D_BLUE_L, anchor="la", alpha=int(255*a))
    text(d, (cx+28, cy+126), "D wins House: 93%", 22, GOLD, anchor="la", alpha=int(230*a))
    # takeaway
    tk = ease_out(clamp01((t-0.55)/0.5))
    text(d, (W/2, 660), "众议院是民主党最清晰的回归路径：领先幅度小、全国民调顺风。", 28, GOLD, anchor="mm", alpha=int(255*tk))
    text(d, (W/2, 706), "The House is Democrats' clearest path back to power.", 22, TEXT_DIM, anchor="mm", alpha=int(200*tk))
    text(d, (W/2, 770), "Cook：「几乎已成定局」，预计民主党净增约 20 席。", 22, TEXT_DIM, anchor="mm", alpha=int(190*tk))

# ---- SCENE 3 : SENATE + battleground network ------------------------------------
SEN_NODES = [
    ("缅因 ME", 0.62), ("俄亥俄 OH", 0.55), ("爱荷华 IA", 0.52),
    ("德州 TX", 0.48), ("阿拉斯加 AK", 0.50), ("密歇根 MI", 0.58),
]
def scene_senate(d):
    t = SCENE_T["senate"]
    a = ease_out(clamp01(t*3.0))
    text(d, (W/2, 96), "参议院 · THE SENATE", 40, WHITE, anchor="mm", alpha=int(255*a))
    text(d, (W/2, 146), "共和党 53–47 占优，民主党需净增 4 席  ·  R 53–47, D needs +4", 23, TEXT_DIM, anchor="mm", alpha=int(220*a))
    # left: seat bar 100 / 51 majority
    bx, by, bw, bh = 120, 250, 620, 80
    total = 100; maj = 51
    rr(d, [bx, by, bx+bw, by+bh], 14, fill=rgba((30,38,64), int(120*a)))
    mx = bx+bw*(maj/total)
    d.line([(mx, by-16),(mx, by+bh+16)], fill=rgba(GOLD, int(220*a)), width=3)
    text(d, (mx, by-30), "过半 51", 18, GOLD, anchor="ma", alpha=int(230*a))
    prog = ease_out(clamp01((t-0.1)/0.7))
    d_s = 47 + int(round(4*prog))  # 47 (current) -> 51 (projected D majority)
    dw = bw*(d_s/total)
    rr(d, [bx, by, bx+dw, by+bh], 14, fill=rgba(D_BLUE, int(235*a)))
    rr(d, [bx+dw, by, bx+bw, by+bh], 14, fill=rgba(R_RED, int(235*a)))
    text(d, (bx+dw/2, by+bh/2), f"D {d_s}", 26, WHITE, anchor="mm", alpha=int(255*a))
    text(d, (bx+dw+(bw-dw)/2, by+bh/2), f"R {100-d_s}", 26, WHITE, anchor="mm", alpha=int(255*a))
    text(d, (bx+30, by+bh+44), "DDHQ 投影：民主党 51 — 共和党 49（51% 概率翻盘）", 22, GOLD, anchor="la", alpha=int(230*a))
    text(d, (bx+30, by+bh+80), "Polymarket 民主党赢参院 63–65%", 20, TEXT_DIM, anchor="la", alpha=int(200*a))
    # right: battleground network (interconnected)
    nx0, ny0, nxw, nyh = 800, 250, 1000, 420
    card(d, [nx0, ny0, nx0+nxw, ny0+nyh], alpha=int(50*a))
    text(d, (nx0+30, ny0+30), "关键摇摆州战场 · BATTLEGROUND NETWORK", 22, TEXT, anchor="la", alpha=int(255*a))
    # node positions in a rough map-ish layout
    pos = {
        "缅因 ME": (nx0+180, ny0+110),
        "密歇根 MI": (nx0+360, ny0+130),
        "俄亥俄 OH": (nx0+520, ny0+220),
        "爱荷华 IA": (nx0+420, ny0+300),
        "德州 TX": (nx0+620, ny0+360),
        "阿拉斯加 AK": (nx0+820, ny0+90),
    }
    center = (nx0+nxw/2, ny0+nyh/2)
    # edges (interconnected)
    edges = [("缅因 ME","密歇根 MI"),("密歇根 MI","俄亥俄 OH"),("俄亥俄 OH","爱荷华 IA"),
             ("爱荷华 IA","德州 TX"),("密歇根 MI","爱荷华 IA"),("俄亥俄 OH","德州 TX"),
             ("阿拉斯加 AK","密歇根 MI")]
    edge_prog = ease_out(clamp01((t-0.2)/0.7))
    for (u,v) in edges:
        p1,p2 = pos[u],pos[v]
        # draw partial edge with flowing pulse
        d.line([p1,p2], fill=rgba((110,140,210), int(70*a)), width=2)
        if edge_prog>0:
            fp = (math.sin((t*2.0)+hash(u+v)%6)+1)/2
            px = p1[0]+(p2[0]-p1[0])*fp; py = p1[1]+(p2[1]-p1[1])*fp
            d.ellipse([px-5,py-5,px+5,py+5], fill=rgba(GOLD, int(230*a)))
    node_prog = ease_out(clamp01((t-0.3)/0.6))
    for name,(px,py) in pos.items():
        p = dict(SEN_NODES)[name]
        col = D_BLUE if p>=0.5 else R_RED
        if p>=0.5: col = D_BLUE
        else: col = R_RED
        rad = 26*node_prog + 6
        d.ellipse([px-rad,py-rad,px+rad,py+rad], fill=rgba(col, int(220*a)))
        d.ellipse([px-rad,py-rad,px+rad,py+rad], outline=rgba(WHITE, int(180*a)), width=2)
        text(d, (px, py-rad-22), name, 18, TEXT, anchor="ma", alpha=int(230*a))
        lean = "D 略优" if p>=0.5 else "R 结构优势"
        text(d, (px, py+rad+16), f"{int(round(p*100))}% · {lean}", 15, TEXT_DIM, anchor="ma", alpha=int(200*a))
    tk = ease_out(clamp01((t-0.6)/0.5))
    text(d, (W/2, 730), "参议院是真正的胜负手：一年前民主党多数还是幻想，如今六州皆有可能。", 26, GOLD, anchor="mm", alpha=int(255*tk))
    text(d, (W/2, 774), "The Senate is the real toss-up — six battlegrounds now in play.", 21, TEXT_DIM, anchor="mm", alpha=int(200*tk))

# ---- SCENE 4 : MARKETS + MONEY (interconnected web) -----------------------------
def scene_markets(d):
    t = SCENE_T["markets"]
    a = ease_out(clamp01(t*3.0))
    text(d, (W/2, 96), "预测市场 × 资金 · MARKETS × MONEY", 40, WHITE, anchor="mm", alpha=int(255*a))
    text(d, (W/2, 146), "民调、市场、现金、席位——环环相扣  ·  polls ↔ markets ↔ cash ↔ seats", 22, TEXT_DIM, anchor="mm", alpha=int(220*a))
    # central web
    cx, cy = W/2, 560
    nodes = [
        ("民调领先\nD +7.3", (cx-560, cy-160), D_BLUE),
        ("预测市场\nD 扫荡 64%", (cx-560, cy+160), D_BLUE_L),
        ("共和党现金\n$416M 弹药", (cx+560, cy-160), R_RED),
        ("席位门槛\n218 / 51", (cx+560, cy+160), GOLD),
        ("政权天平\nBALANCE", (cx, cy), WHITE),
    ]
    # edges from center to each, animated flow
    ep = ease_out(clamp01((t-0.2)/0.7))
    for (lab,(nx,ny),col) in nodes:
        d.line([(cx,cy),(nx,ny)], fill=rgba((120,150,210), int(60*a)), width=2)
        if ep>0:
            pulse = (t*1.6 + nodes.index((lab,(nx,ny),col))*0.4) % 1.0
            px = cx+(nx-cx)*pulse; py = cy+(ny-cy)*pulse
            d.ellipse([px-6,py-6,px+6,py+6], fill=rgba(col, int(240*a)))
    # center node
    rp = 70*ease_out(clamp01((t-0.1)/0.6))
    d.ellipse([cx-rp,cy-rp,cx+rp,cy+rp], fill=rgba((24,32,60), int(220*a)), outline=rgba(GOLD, int(220*a)), width=3)
    d.text((cx, cy-16), "政权", font=font(30), fill=rgba(GOLD, int(255*a)), anchor="mm")
    d.text((cx, cy+16), "天平", font=font(30), fill=rgba(GOLD, int(255*a)), anchor="mm")
    # outer nodes
    np2 = ease_out(clamp01((t-0.35)/0.6))
    for (lab,(nx,ny),col) in nodes:
        rr(d, [nx-130, ny-58, nx+130, ny+58], 18, fill=rgba((20,28,52), int(190*a)), outline=rgba(col, int(200*a)), width=2)
        for i, ln in enumerate(lab.split("\n")):
            text(d, (nx, ny-14+i*26), ln, 22, TEXT if i==0 else col, anchor="mm", alpha=int(255*np2))
    # bottom metric strip
    strip_y = 820
    metrics = [("D 赢众院 93%", D_BLUE_L), ("D 赢参院 64%", D_BLUE_L),
               ("D 扫荡 64%", GOLD), ("R 扫荡 8%", R_RED_L), ("R 现金 $416M", R_RED)]
    mw = (W-240)/len(metrics)
    for i,(s,col) in enumerate(metrics):
        mx = 120 + i*mw
        card(d, [mx+10, strip_y, mx+mw-10, strip_y+90], alpha=int(55*a), border=int(110*a))
        text(d, (mx+mw/2, strip_y+45), s, 26, col, anchor="mm", alpha=int(255*a))
    tk = ease_out(clamp01((t-0.6)/0.5))
    text(d, (W/2, 960), "金钱是共和党的防火墙：MAGA Inc. 9 月坐拥 4.16 亿美元，空优压制关键参院战场。", 24, GOLD, anchor="mm", alpha=int(255*tk))
    text(d, (W/2, 998), "Money is the GOP firewall — but people power is showing up in the polls.", 20, TEXT_DIM, anchor="mm", alpha=int(200*tk))

# ---- SCENE 5 : MODEL CONSENSUS RANGE --------------------------------------------
def scene_models(d):
    t = SCENE_T["models"]
    a = ease_out(clamp01(t*3.0))
    text(d, (W/2, 100), "12 家模型共识区间 · MODEL CONSENSUS", 38, WHITE, anchor="mm", alpha=int(255*a))
    text(d, (W/2, 150), "各家对「民主党夺回控制权」概率的估计跨度  ·  range across 12 forecasters (Sept 30)", 22, TEXT_DIM, anchor="mm", alpha=int(220*a))
    # two horizontal ranges: House D prob, Senate D prob
    def range_bar(y, title, lo, hi, med, color, unit=""):
        text(d, (160, y-30), title, 24, TEXT, anchor="la", alpha=int(255*a))
        bx, bw = 160, W-320
        x0 = bx + bw*(lo/100.0); x1 = bx + bw*(hi/100.0); xm = bx + bw*(med/100.0)
        rr(d, [bx, y, bx+bw, y+30], 8, fill=rgba((30,38,64), int(110*a)))
        prog = ease_out(clamp01((t-0.15)/0.7))
        ex1 = bx + (x1-bx)*prog
        d.line([(x0, y+15),(ex1, y+15)], fill=rgba(color, int(230*a)), width=14)
        # median marker
        if prog>0.6:
            d.ellipse([xm-10,y+5,xm+10,y+25], fill=rgba(GOLD, int(255*a)))
        text(d, (x0, y+58), f"{lo}%", 20, TEXT_DIM, anchor="ma", alpha=int(220*a))
        text(d, (x1, y+58), f"{hi}%", 20, TEXT_DIM, anchor="ma", alpha=int(220*a))
        text(d, (bx+bw, y-30), f"中位 {med}%", 22, GOLD, anchor="ra", alpha=int(240*a))
    range_bar(300, "众议院 · 民主党赢面 House D-win prob", 55, 98, 85, D_BLUE)
    range_bar(470, "参议院 · 民主党赢面 Senate D-win prob", 25, 65, 55, D_BLUE_L)
    # interpretation
    tk = ease_out(clamp01((t-0.5)/0.6))
    text(d, (W/2, 620), "模型分歧巨大：从「几乎确定」到「概率五五开」皆有。", 28, GOLD, anchor="mm", alpha=int(255*tk))
    text(d, (W/2, 666), "Wide disagreement — from near-certain to a coin flip. Uncertainty is the only consensus.", 20, TEXT_DIM, anchor="mm", alpha=int(200*tk))
    # bullet chips
    chips = ["FiftyPlusOne 98%", "Election Statsheet 55%", "Polymarket 93%", "DDHQ 75%"]
    cw = (W-320)/4
    for i,c in enumerate(chips):
        mx = 160 + i*cw
        card(d, [mx+8, 740, mx+cw-8, 820], alpha=int(55*tk), border=int(110*tk))
        text(d, (mx+cw/2, 780), c, 22, TEXT, anchor="mm", alpha=int(255*tk))

# ---- SCENE 6 : CLOSING SYNTHESIS ------------------------------------------------
def scene_close(d):
    t = SCENE_T["close"]
    a = ease_out(clamp01(t*3.0))
    text(d, (W/2, 220), "结论 · THE BOTTOM LINE", 44, WHITE, anchor="mm", alpha=int(255*a))
    lines = [
        ("众议院：民主党最清晰路径，近乎定局。", "The House: Democrats' clearest, near-locked path."),
        ("参议院：真正的硬币翻转，六州定天下。", "The Senate: a true coin-flip decided by six states."),
        ("资金：共和党的防火墙，民调：民主党的顺风。", "Money is the GOP firewall; polls are the Dem tailwind."),
    ]
    y = 360
    for i,(cn,en) in enumerate(lines):
        la = ease_out(clamp01((t-0.15-i*0.12)/0.5))
        card(d, [260, y, W-260, y+96], alpha=int(55*la), border=int(120*la))
        text(d, (300, y+34), cn, 28, TEXT, anchor="la", alpha=int(255*la))
        text(d, (300, y+70), en, 20, TEXT_DIM, anchor="la", alpha=int(200*la))
        y += 120
    # final balance bar
    fb_a = ease_out(clamp01((t-0.6)/0.5))
    text(d, (W/2, 800), "11 / 3 见分晓 · 一切指向一个词：悬念。", 30, GOLD, anchor="mm", alpha=int(255*fb_a))
    text(d, (W/2, 848), "Nov 3 decides it all. One word defines 2026: uncertainty.", 22, TEXT_DIM, anchor="mm", alpha=int(200*fb_a))

# ----------------------------------------------------------------------------- timeline
SCENES = [
    ("intro",   0,    150),
    ("mood",    150,  380),
    ("house",   380,  610),
    ("senate",  610,  920),
    ("markets", 920,  1170),
    ("models",  1170, 1380),
    ("close",   1380, 1560),
]
TOTAL = SCENES[-1][2]
SCENE_T = {}

TR_IN, TR_OUT = 10, 14  # fast frame-based fades (~0.3-0.5s)

def build_frame(f):
    base = draw_bg(f)
    # compute scene envelopes (fast fades so content is fully visible for most of each scene)
    layers = []
    for i,(name,s,e) in enumerate(SCENES):
        local = (f - s) / (e - s)
        ain = smooth(clamp01((f - s) / TR_IN))
        aout = 1.0 - smooth(clamp01((f - (e - TR_OUT)) / TR_OUT))
        alpha = clamp01(min(ain, aout))
        if alpha > 0.01 and (f >= s - TR_IN) and (f <= e + TR_OUT):
            SCENE_T[name] = clamp01(local)
            builder = globals()["scene_"+name]
            layers.append(scene_layer(builder, alpha))
    img = composite(base, layers)
    # ribbon on top
    d = ImageDraw.Draw(img)
    # pick label by dominant scene
    dom = max(SCENES, key=lambda sc: (1 if sc[1]<=f<sc[2] else 0))
    labels = {
        "intro":"开篇 · 政权现状","mood":"全国风向","house":"众议院","senate":"参议院 / 摇摆州",
        "markets":"市场 × 资金","models":"模型共识","close":"结论",
    }
    ribbon(d, labels[dom[0]], "2026 US MIDTERMS · TWO-PARTY BATTLE")
    return img.convert("RGB")

# ----------------------------------------------------------------------------- encode
def main():
    out = "/Users/leo/WorkBuddy/2026-09-28-13-16-07/election-dashboard/2026_midterm_trend.mp4"
    import imageio.v2 as imageio
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        writer = imageio.get_writer(out, fps=FPS, codec="libx264", quality=8,
                                    macro_block_size=1, ffmpeg_exe=exe)
    except Exception as e:
        print("ffmpeg path fallback:", e)
        writer = imageio.get_writer(out, fps=FPS, codec="libx264", quality=8, macro_block_size=1)
    print(f"Rendering {TOTAL} frames -> {out}")
    for f in range(TOTAL):
        img = build_frame(f)
        writer.append_data(np.asarray(img))
        if f % 100 == 0:
            print(f"  frame {f}/{TOTAL}")
    writer.close()
    print("DONE:", out)

if __name__ == "__main__":
    main()
