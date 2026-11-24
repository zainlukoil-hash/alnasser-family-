"""Motion-graphics logo reveal: golden particles assemble the palm emblem (ground -> trunk -> fronds),
geometric strokes draw themselves around it, then the Arabic title is wiped in with a light edge."""
import math, numpy as np, cv2
from film import *

_EMB = None
def _emblem():
    global _EMB
    if _EMB is None:
        im = cv2.imread('/home/claude/work/out/site227/icon-v3-512.png', cv2.IMREAD_UNCHANGED)
        hsv = cv2.cvtColor(im[..., :3], cv2.COLOR_BGR2HSV).astype(np.float32)
        S_, V_ = hsv[..., 1], hsv[..., 2]
        m = np.clip((V_ - 95) / 60, 0, 1) * np.clip((S_ - 45) / 55, 0, 1)
        m = cv2.GaussianBlur(m, (0, 0), 0.8)
        x0, x1, y0, y1 = 56, 456, 26, 478
        col = im[y0:y1, x0:x1, :3].astype(np.float32)
        a = m[y0:y1, x0:x1]
        _EMB = (col, a)
    return _EMB

_TG = None
def _targets(n=6500, seed=3):
    global _TG
    if _TG is None:
        col, a = _emblem()
        ys, xs = np.nonzero(a > 0.55)
        r = np.random.RandomState(seed)
        sel = r.choice(len(xs), n, replace=True)
        px, py = xs[sel].astype(np.float32) + r.rand(n) - 0.5, ys[sel].astype(np.float32) + r.rand(n) - 0.5
        c = col[np.clip(py.astype(int), 0, col.shape[0] - 1), np.clip(px.astype(int), 0, col.shape[1] - 1)]
        hh, ww = a.shape
        ang = r.rand(n) * 2 * math.pi
        rad = r.uniform(750, 1350, n)
        sx, sy = ww / 2 + rad * np.cos(ang) * 0.9, hh / 2 + rad * np.sin(ang) * 1.15 - 120
        ynorm = py / hh
        delay = 0.55 * (1 - ynorm) ** 0.9 + r.rand(n) * 0.12
        dur = r.uniform(0.7, 1.0, n)
        sw = r.uniform(-1, 1, n) * 0.55
        rad_ = r.uniform(1.3, 2.9, n)
        _TG = dict(px=px, py=py, c=c, sx=sx, sy=sy, delay=delay, dur=dur, sw=sw, rad=rad_, hh=hh, ww=ww)
    return _TG

_TI = {}
def _timg(name):
    if name not in _TI:
        im = cv2.imread(C + name + '.png', cv2.IMREAD_UNCHANGED)
        assert im is not None and im.shape[2] == 4, name
        _TI[name] = im.astype(np.float32)
    return _TI[name]

def _ease_out(u): u = np.clip(u, 0, 1); return 1 - (1 - u) ** 3
def _ease_io(u): u = np.clip(u, 0, 1); return u * u * (3 - 2 * u)

def draw_rings(f, tl, cx, cy, a):
    lay = np.zeros((H, W, 3), np.float32)
    gold = (70 * a, 185 * a, 255 * a)
    # ring 1: drawn clockwise from the top
    u1 = float(ease(clamp01((tl - 0.1) / 1.5)))
    if u1 > 0.002:
        cv2.ellipse(lay, (int(cx), int(cy)), (336, 336), 0, -90, -90 + 360 * u1, gold, 3, cv2.LINE_AA)
    # ring 2: ticks that appear one after another and keep rotating slowly
    for k in range(72):
        ta = 0.25 + k * 0.016
        v = float(clamp01((tl - ta) / 0.25))
        if v <= 0: continue
        ang = math.radians(k * 5 - 90 - tl * 6)
        r0 = 372 + (6 if k % 6 else 16) * (1 - 0.2 * (1 - v)); r1 = 372 + 2
        p0 = (cx + r1 * math.cos(ang), cy + r1 * math.sin(ang)); p1 = (cx + (r0 + (8 if k % 6 == 0 else 0)) * math.cos(ang), cy + (r0 + (8 if k % 6 == 0 else 0)) * math.sin(ang))
        cv2.line(lay, (int(p0[0]), int(p0[1])), (int(p1[0]), int(p1[1])), (60 * a * v, 150 * a * v, 230 * a * v), 2, cv2.LINE_AA)
    # four diamonds on ring 1
    for k in range(4):
        v = float(ease(clamp01((tl - 1.0 - k * 0.12) / 0.5)))
        if v <= 0: continue
        ang = math.radians(k * 90 - 90 + tl * 10)
        px_, py_ = cx + 336 * math.cos(ang), cy + 336 * math.sin(ang)
        s_ = 11 * v
        cv2.fillPoly(lay, [np.array([(px_, py_ - s_), (px_ + s_, py_), (px_, py_ + s_), (px_ - s_, py_)], np.int32)], (90 * a, 205 * a, 255 * a), cv2.LINE_AA)
    # shock-wave when the emblem completes
    wu = (tl - 1.65) / 1.1
    if 0 < wu < 1:
        rr = int(340 + 640 * float(ease(wu))); wa = (1 - wu) ** 1.6 * a
        cv2.circle(lay, (int(cx), int(cy)), rr, (80 * wa, 190 * wa, 255 * wa), 4, cv2.LINE_AA)
    return glow_add(f, lay, k=0.9, r=9, keep=1.0)

def draw_particles(f, tl, cx, cy, size, a):
    g = _targets(); sc = size / g['hh']
    u = (tl - g['delay']) / g['dur']
    live = (u > 0) & (u < 1.6)
    idx = np.nonzero(live)[0]
    if len(idx) == 0: return f
    uu = u[idx]
    e = _ease_out(uu)
    tx = cx + (g['px'][idx] - g['ww'] / 2) * sc; ty = cy + (g['py'][idx] - g['hh'] / 2) * sc
    sx = cx + (g['sx'][idx] - g['ww'] / 2) * sc * 1.0; sy = cy + (g['sy'][idx] - g['hh'] / 2) * sc * 1.0
    # swirl: control point offset perpendicular to the straight path
    dx, dy = tx - sx, ty - sy
    mx, my = sx + dx * 0.5 - dy * g['sw'][idx], sy + dy * 0.5 + dx * g['sw'][idx]
    om = 1 - e
    x = om * om * sx + 2 * om * e * mx + e * e * tx
    y = om * om * sy + 2 * om * e * my + e * e * ty
    prog = np.clip(uu, 0, 1)
    c = g['c'][idx]
    colr = np.array([200, 235, 255], np.float32)[None, :] * (1 - prog[:, None]) + c * prog[:, None]
    br = np.clip(uu * 3, 0, 1) * (1 - np.clip((uu - 1.0) / 0.6, 0, 1)) * a
    lay = np.zeros((H, W, 3), np.float32)
    rr = g['rad'][idx] * (1.5 - 0.5 * prog)
    for i in range(len(idx)):
        if br[i] < 0.02: continue
        xi, yi = int(x[i]), int(y[i])
        if xi < -5 or xi >= W + 5 or yi < -5 or yi >= H + 5: continue
        cv2.circle(lay, (xi, yi), max(1, int(round(rr[i]))), (float(colr[i, 0] * br[i]), float(colr[i, 1] * br[i]), float(colr[i, 2] * br[i])), -1, cv2.LINE_AA)
    return glow_add(f, lay, k=0.55, r=7, keep=0.95)

def draw_emblem(f, tl, cx, cy, size, a):
    ea = float(sm(1.3, 1.85, tl)) * a
    if ea <= 0.003: return f
    col, al = _emblem()
    sc = size / col.shape[0]
    h, w = int(col.shape[0] * sc), int(col.shape[1] * sc)
    rgba = np.dstack([cv2.resize(col, (w, h), interpolation=cv2.INTER_CUBIC), cv2.resize(al, (w, h), interpolation=cv2.INTER_CUBIC) * 255.0])
    # colour lift + light sweep (a diagonal highlight crossing the emblem once)
    su = (tl - 1.75) / 1.1
    if 0 < su < 1:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
        d = (xx * 0.8 + yy * 0.6) / (w * 0.8 + h * 0.6)
        beam = np.exp(-((d - su) / 0.09) ** 2)[..., None] * 0.9
        rgba[..., :3] = rgba[..., :3] + beam * np.array([255, 245, 220], np.float32) * 0.55
    # soft glow behind the crisp emblem
    over(f, rgba, int(cx - w / 2), int(cy - h / 2), alpha=ea)
    return f

def _reveal(img, u, edge=90):
    """right-to-left wipe for Arabic (u 0..1) returns RGBA float with alpha multiplied"""
    h, w = img.shape[:2]
    xs = np.arange(w, dtype=np.float32)
    front = (1 - u) * (w + edge) - edge * 0 + 0
    m = np.clip((xs - ((1 - u) * (w + edge) - edge)) / edge, 0, 1)
    out = img.copy(); out[..., 3] *= m[None, :]
    return out, front

def draw_title(f, tl, cx, title_y, line_y, en_y, tag_y, tag_name, a):
    # Arabic title: wipe from the right with a light edge
    ua = float(ease(clamp01((tl - 1.85) / 0.95)))
    if ua > 0.002:
        im = _timg('title_ar')
        h, w = im.shape[:2]
        out, front = _reveal(im, ua, 140)
        rise = int((1 - ua) * 22)
        over(f, out, int(cx - w / 2), int(title_y - h / 2 + rise), alpha=a)
        if ua < 0.995:
            ex = int(cx - w / 2 + (w + 140) - ((1 - 0) * 0) - ((1 - ua) * (w + 140)) - 70) if False else int(cx - w / 2 + w - (ua * (w + 140)) + 140 - 70)
            bar = np.zeros((H, W, 3), np.float32)
            cv2.line(bar, (ex, int(title_y - 80)), (ex, int(title_y + 80)), (150 * a, 225 * a, 255 * a), 6, cv2.LINE_AA)
            f[:] = glow_add(f, bar, k=1.2, r=16, keep=0.7)
    # line with diamonds growing from the centre
    lu = float(ease(clamp01((tl - 2.4) / 0.8)))
    if lu > 0.002:
        lay = np.zeros((H, W, 3), np.float32)
        half = int(300 * lu)
        cv2.line(lay, (int(cx - half), int(line_y)), (int(cx + half), int(line_y)), (70 * a, 185 * a, 255 * a), 3, cv2.LINE_AA)
        for sgn in (-1, 1):
            px_ = cx + sgn * (half + 22 * lu); s_ = 9 * lu
            cv2.fillPoly(lay, [np.array([(px_, line_y - s_), (px_ + s_, line_y), (px_, line_y + s_), (px_ - s_, line_y)], np.int32)], (90 * a, 205 * a, 255 * a), cv2.LINE_AA)
        f[:] = glow_add(f, lay, k=0.8, r=8, keep=1.0)
    # English title: tracking opens up
    ea = float(sm(2.7, 3.5, tl))
    if ea > 0.003:
        im = _timg('title_en'); h, w = im.shape[:2]
        z = float(lerp(0.88, 1.0, ease(clamp01((tl - 2.7) / 1.3))))
        im2 = cv2.resize(im, (max(2, int(w * z)), h), interpolation=cv2.INTER_AREA)
        over(f, im2, int(cx - im2.shape[1] / 2), int(en_y - h / 2 + (1 - ea) * 14), alpha=ea * a)
    ta = float(sm(3.3, 4.2, tl))
    if ta > 0.003:
        im = _timg(tag_name); h, w = im.shape[:2]
        over(f, im, int(cx - w / 2), int(tag_y - h / 2 + (1 - ta) * 12), alpha=ta * a)
    return f

def logo_mg(f, tl, cx, cy, size=600, title_y=1000, line_y=1128, en_y=1215, tag_y=1345, tag_name='tag_en', a=1.0):
    """tl = seconds since the logo started assembling"""
    if tl < -0.05: return f
    f = draw_rings(f, tl, cx, cy, a)
    f = draw_particles(f, tl, cx, cy, size, a)
    f = draw_emblem(f, tl, cx, cy, size, a)
    f = draw_title(f, tl, cx, title_y, line_y, en_y, tag_y, tag_name, a)
    return f
