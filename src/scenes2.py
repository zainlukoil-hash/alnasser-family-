from scenes1 import *

NODE = {n[0]: n for n in NODES}
def node_xy(i, cam):
    x, y, w, h = cam; k = W / w
    return ((NODE[i][3] - x) * k, (NODE[i][4] - y) * k)

def tap_on_frame(f, xy, t, t0, size=1.0, dur=1.0):
    """fingertip glow + ripple on the full frame"""
    u = (t - t0) / dur
    if u < -0.2 or u > 1.25: return f
    cx, cy = int(xy[0]), int(xy[1])
    lay = np.zeros((H, W, 3), np.float32)
    a_in = float(sm(-0.2, 0.1, u)); a_out = float(1 - sm(0.5, 1.2, u))
    if a_in * a_out > 0.01:
        cv2.circle(lay, (cx, cy), int(46 * size), (255 * a_in * a_out, 255 * a_in * a_out, 255 * a_in * a_out), -1, cv2.LINE_AA)
        lay = cv2.GaussianBlur(lay, (0, 0), 9 * size) * 0.55
        f = f + lay
    if 0 <= u <= 1:
        rr = int(46 * size * (0.7 + 3.0 * float(ease(u)))); a = (1 - u) ** 1.4
        ring = np.zeros((H, W, 3), np.float32)
        cv2.circle(ring, (cx, cy), rr, (90 * a, 200 * a, 255 * a), max(2, int(5 * size)), cv2.LINE_AA)
        f = glow_add(f, ring, k=0.9, r=8, keep=1.0)
    return f


# ---------------------------------------------------------------- v3: floating glass cards (real UI crops, zoomed)
from PIL import Image, ImageDraw
HERO = {'t_search': (480, 380, 1110, 700), 't_card_fadhil': (440, 1040, 1130, 1330), 't_card_details': (340, 270, 1130, 560), 't_card_amir': (440, 1040, 1130, 1330),
        'm_01': (250, 520, 920, 1120), 't_wall': (420, 640, 1160, 1260), 'm_26': (130, 1330, 1040, 1900), 'm_40': (40, 1390, 1140, 1760),
        'm_21': (100, 790, 1130, 1240), 't_map': (180, 1000, 950, 1700), 'm_04': (100, 900, 1070, 1500), 'm_08': (280, 1480, 890, 2110), 't_tree': (285, 960, 885, 1560)}
_GC = {}
def _rr_mask(w, h, r, ss=3):
    im = Image.new('L', (w * ss, h * ss), 0)
    ImageDraw.Draw(im).rounded_rectangle([0, 0, w * ss - 1, h * ss - 1], r * ss, fill=255)
    return np.asarray(im.resize((w, h), Image.LANCZOS), np.float32) / 255.0
def _glass(name, w=430):
    if name in _GC: return _GC[name]
    x0, y0, x1, y1 = HERO[name]
    h = int(w * (y1 - y0) / (x1 - x0))
    img = cv2.resize(texf(name)[y0:y1, x0:x1], (w, h), interpolation=cv2.INTER_AREA)
    pad = 46
    m = _rr_mask(w, h, 26)
    inner = _rr_mask(w - 6, h - 6, 23)
    ring = m.copy(); ring[3:h - 3, 3:w - 3] -= inner; ring = np.clip(ring, 0, 1)
    gx = np.linspace(0, 1, w, dtype=np.float32)[None, :] * 0.6 + np.linspace(0, 1, h, dtype=np.float32)[:, None] * 0.4
    border = (np.array([60, 170, 255], np.float32)[None, None, :] * (0.55 + 0.6 * (1 - gx))[..., None])
    col = img * (1 - ring[..., None]) + border * ring[..., None]
    card = np.zeros((h + 2 * pad, w + 2 * pad, 4), np.float32)
    sh = np.zeros((h + 2 * pad, w + 2 * pad), np.float32); sh[pad + 16:pad + 16 + h, pad:pad + w] = m
    sh = cv2.GaussianBlur(sh, (0, 0), 20) * 0.62
    ca = np.zeros((h + 2 * pad, w + 2 * pad), np.float32); ca[pad:pad + h, pad:pad + w] = m * 0.97
    cc = np.zeros((h + 2 * pad, w + 2 * pad, 3), np.float32); cc[pad:pad + h, pad:pad + w] = col
    oa = ca + sh * (1 - ca)
    card[..., :3] = cc * (ca / np.maximum(oa, 1e-4))[..., None]
    card[..., 3] = oa * 255.0
    _GC[name] = card
    return card
def glass_card(f, name, t, t0, t1, side=1, idx=0, cx=None, cy=None):
    a = float(sm(t0, t0 + 0.6, t) * (1 - sm(t1 - 0.45, t1, t)))
    if a < 0.01: return f
    card = _glass(name)
    e = float(ease(clamp01((t - t0) / 0.7)))
    sc = 0.8 + 0.2 * e
    ch, cw = card.shape[:2]
    rot = side * 4.5 + 1.6 * math.sin(t * 0.6 + idx)
    M = cv2.getRotationMatrix2D((cw / 2, ch / 2), rot, sc)
    warped = cv2.warpAffine(card, M, (cw, ch), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
    px = (255 if side < 0 else 825) if cx is None else cx
    py = (520 if side < 0 else 1010) if cy is None else cy
    px += side * (1 - e) * -70 + 6 * math.sin(t * 0.8 + idx)
    py += 12 * math.sin(t * 0.9 + idx * 1.7) + (1 - e) * 30
    over(f, warped, int(px - cw / 2), int(py - ch / 2), alpha=a)
    return f

DUST3 = Dust(120, seed=33, rmin=1.0, rmax=2.6, vy=(-10, -30))
def scene3(t, n):
    ts = t - 30.0
    n3 = int(min(max(round(ts * FPS), 0), 659))
    cam = cams('s3')[str(n3)]
    f = seqframe('s3', n3)
    f *= 1.04
    dl = np.zeros((H, W, 3), np.float32)
    DUST3.draw(dl, t, alpha=0.8)
    f = glow_add(f, dl, k=0.7, r=9, keep=0.9)
    # three taps on real people while the camera rests near them
    for (pid, tt) in ((84, 10.3), (98, 15.7), (116, 19.9)):
        xy = node_xy(pid, cam)
        # node highlight ring while the finger is down
        u = (ts - tt) / 1.4
        if -0.1 < u < 1.0:
            a = float(sm(-0.1, 0.1, u) * (1 - sm(0.45, 1.0, u)))
            ring = np.zeros((H, W, 3), np.float32)
            cv2.circle(ring, (int(xy[0]), int(xy[1])), int(NODE[pid][5] * W / cam[2] * 0.9 + 14), (80 * a, 200 * a, 255 * a), 5, cv2.LINE_AA)
            f = glow_add(f, ring, k=1.0, r=10, keep=1.0)
        f = tap_on_frame(f, xy, ts, tt)
    f = bloom(f, 185, 0.35, 20)
    f = vignette(f, 0.42)
    f = scrim(f, 0.62, 0.64)
    caption(f, 'c3a', t, 31.0, 35.2, 1790)
    caption(f, 'c3b', t, 36.0, 44.6, 1790)
    caption(f, 'c3c', t, 45.2, 51.4, 1790)
    f = flash(f, (1 - float(sm(0.0, 0.5, ts))) ** 1.6)
    f *= dipmul(ts, -1.0, -0.5, 21.2, 22.0)
    return f

# ====================================================================== phone scenes helpers
_HOME = None
def homescreen():
    """a stylised phone home screen (wallpaper + empty glass tiles + the real app icon)"""
    global _HOME
    if _HOME is not None: return _HOME
    w, h = 1170, 2532
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    g = np.zeros((h, w, 3), np.float32)
    d1 = np.sqrt(((xs - w * 0.3) / (w * 0.9)) ** 2 + ((ys - h * 0.28) / (h * 0.5)) ** 2)
    d2 = np.sqrt(((xs - w * 0.85) / (w * 0.8)) ** 2 + ((ys - h * 0.8) / (h * 0.55)) ** 2)
    g += np.array([95, 45, 25], np.float32) * clamp01(1 - d1)[..., None] ** 1.5
    g += np.array([40, 70, 120], np.float32) * clamp01(1 - d2)[..., None] ** 1.5
    g += np.array([22, 14, 10], np.float32)
    # grid of glass tiles
    cols, rows = 4, 6
    tw = 190; gx = (w - cols * tw) // (cols + 1); gy = 120
    top = 420
    pos = {}
    for r_ in range(rows):
        for c_ in range(cols):
            x0 = gx + c_ * (tw + gx); y0 = top + r_ * (tw + gy + 55)
            tile = np.zeros((h, w), np.float32)
            cv2.rectangle(tile, (x0, y0), (x0 + tw, y0 + tw), 1.0, -1)
            tile = cv2.GaussianBlur(tile, (0, 0), 1.2)
            m = np.zeros((h, w), np.float32)
            rad = 46
            sub = np.zeros((tw, tw), np.float32)
            cv2.rectangle(sub, (rad, 0), (tw - rad, tw), 1, -1); cv2.rectangle(sub, (0, rad), (tw, tw - rad), 1, -1)
            for cx_, cy_ in ((rad, rad), (tw - rad, rad), (rad, tw - rad), (tw - rad, tw - rad)): cv2.circle(sub, (cx_, cy_), rad, 1, -1)
            sub = cv2.GaussianBlur(sub, (0, 0), 1.0)
            m[y0:y0 + tw, x0:x0 + tw] = sub
            shade = np.array([120, 100, 90], np.float32)
            gv = (m * 0.20)[..., None]
            g = g * (1 - gv) + shade * gv
            pos[(r_, c_)] = (x0, y0)
    # the real icon replaces one tile
    ix, iy = pos[(1, 2)]
    ic = icon_rgba(tw)
    a = ic[..., 3:4].astype(np.float32) / 255
    g[iy:iy + tw, ix:ix + tw] = g[iy:iy + tw, ix:ix + tw] * (1 - a) + ic[..., :3].astype(np.float32) * a
    # dock
    dock = np.zeros((h, w), np.float32)
    cv2.rectangle(dock, (60, h - 330), (w - 60, h - 110), 1.0, -1)
    dock = cv2.GaussianBlur(dock, (0, 0), 30)
    g = g * (1 - dock[..., None] * 0.25) + np.array([160, 140, 130], np.float32) * dock[..., None] * 0.25
    _HOME = (g.astype(np.float32), (ix + tw // 2, iy + tw // 2))
    return _HOME

def warp_scale(tx, s, cx, cy):
    M = np.array([[s, 0, cx - s * cx], [0, s, cy - s * cy]], np.float32)
    return cv2.warpAffine(tx, M, (tx.shape[1], tx.shape[0]), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

def wallpaper(t, hue=0):
    """dark moving-light background for the phone scenes"""
    f = dark_bg(0.5, 0.40, (34, 24, 14), (8, 6, 4))
    bokeh(f, t, seed=3, n=11, alpha=0.9, zone=(120, 1500))
    return f

def phone_pose(ts, base_scale=0.5, cy=700, amp=1.0, ry0=0.0, rx0=5.0):
    ry = ry0 + 11 * amp * math.sin(ts * 0.55)
    rx = rx0 + 3.0 * amp * math.sin(ts * 0.43 + 1.0)
    rz = 1.4 * amp * math.sin(ts * 0.37 + 2.0)
    cyy = cy + 10 * math.sin(ts * 0.7)
    return rx, ry, rz, base_scale, W / 2, cyy

def chip(f, name, t, t0, t1, y=1362):
    a = float(sm(t0, t0 + 0.35, t) * (1 - sm(t1 - 0.3, t1, t)))
    if a <= 0.01: return f
    put_center(f, txtimg('lab_' + name), W / 2, y + (1 - a) * 10, 1.0, a)
    return f

# ====================================================================== SCENE 4 : personal profiles (52 .. 70)
TAPS4 = []
def scene4(t, n):
    ts = t - 52.0
    f = wallpaper(t)
    dl = np.zeros((H, W, 3), np.float32)
    DUST3.draw(dl, t * 1.1, alpha=0.8)
    # screen timeline
    S_TREE, S_SEARCH, S_FAD, S_DET, S_AMIR = 't_tree', 't_search', 't_card_fadhil', 't_card_details', 't_card_amir'
    if ts < 1.9:   a_, b_, u, mode = S_TREE, S_SEARCH, 0, 'fade'
    segs = [(0.0, 1.7, S_TREE, S_SEARCH, 'fade'), (1.7, 4.2, S_SEARCH, S_FAD, 'up'), (4.2, 8.3, S_FAD, S_DET, 'fade'), (8.3, 12.5, S_DET, S_AMIR, 'slide')]
    # transition windows: [start, end]
    T = {'t1': (1.45, 2.0), 't2': (4.1, 4.8), 't3': (8.0, 8.8), 't4': (12.2, 13.0)}
    order = [S_TREE, S_SEARCH, S_FAD, S_DET, S_AMIR]
    modes = ['fade', 'up', 'fade', 'slide']
    wins = [T['t1'], T['t2'], T['t3'], T['t4']]
    cur = 0
    for i, (a0, a1) in enumerate(wins):
        if ts >= a1: cur = i + 1
    tx = texf(order[cur]).copy()
    for i, (a0, a1) in enumerate(wins):
        if a0 <= ts < a1:
            tx = trans(texf(order[i]), texf(order[i + 1]), (ts - a0) / (a1 - a0), modes[i])
    # fingertip taps (texture coordinates)
    for (tt, px, py) in ((0.9, 640, 150), (3.4, 600, 500), (7.4, 190, 1992), (11.6, 975, 1290)):
        tx = touch_fx(tx, px, py, ts, tt, 0.9, 1.25)
    # camera
    zoom = float(ease((ts - 14.0) / 2.2)) * (1 - float(ease((ts - 17.0) / 1.0)))
    rx, ry, rz, sc, cx, cy = phone_pose(ts, 0.47, 665, amp=1.0 - 0.6 * zoom)
    sc = lerp(sc, 0.9, zoom); cy = lerp(cy, 1010, zoom)
    entry = float(ease(ts / 1.0))
    gl = np.zeros((H, W, 3), np.float32)
    cv2.circle(gl, (W // 2, int(cy)), 430, (46, 88, 150), -1, cv2.LINE_AA)
    f = glow_add(f, gl, k=0.7, r=90, keep=0.0)
    f = glow_add(f, dl, k=0.8, r=10, keep=1.0)
    f, _ = phone().draw(f, tx, rx, ry, rz, sc, cx, cy, light=float(((ts - 1.0) * 0.16) % 1.5 - 0.25), sheen=0.12, glow=0.55, shadow=0.5, alpha=entry)
    for i_, (c0, c1, nm_, sd_) in enumerate(((2.0, 4.3, 't_search', 1), (4.6, 8.2, 't_card_fadhil', -1), (8.5, 12.3, 't_card_details', 1), (12.6, 13.9, 't_card_amir', -1))):
        glass_card(f, nm_, ts, c0, c1, sd_, i_)
    f = bloom(f, 175, 0.35, 20)
    f = vignette(f, 0.42)
    f = scrim(f, 0.55, 0.64)
    chip(f, 'search', t, 52 + 1.6, 52 + 3.6)
    chip(f, 'card', t, 52 + 4.6, 52 + 8.0)
    chip(f, 'details', t, 52 + 8.6, 52 + 12.0)
    chip(f, 'fatiha', t, 52 + 13.2, 52 + 17.2)
    caption(f, 'c4a', t, 52.7, 55.6, 1800)
    caption(f, 'c4b', t, 56.0, 68.6, 1800)
    f *= dipmul(ts, 0.0, 0.5, 17.5, 18.0)
    return f

# ====================================================================== SCENE 5 : the platform (70 .. 98)
MOM = [  # (screen, chip, start, end)
    ('m_01', 'natural', 70.0, 73.3),
    ('t_search', 'search', 73.3, 76.3),
    ('t_wall', 'wall', 76.3, 79.3),
    ('m_26', 'stories', 79.3, 82.8),
    ('m_40', 'events', 82.8, 86.0),
    ('m_21', 'guide', 86.0, 89.0),
    ('t_map', 'map', 89.0, 92.3),
    ('m_04', 'galaxy', 92.3, 95.3),
    ('m_08', 'sigil', 95.3, 98.0),
]
TAPXY = [(560, 1250), (600, 500), (330, 900), (870, 1300), (440, 1000), (760, 1500), (560, 1100), (300, 800), (600, 1700)]
def scene5(t, n):
    ts = t - 70.0
    f = wallpaper(t)
    dl = np.zeros((H, W, 3), np.float32)
    DUST3.draw(dl, t * 0.9 + 30, alpha=0.85)
    TR = 0.5
    # which moment
    idx = 0
    for i, (nm, ch, a0, a1) in enumerate(MOM):
        if t >= a0: idx = i
    nm, ch, a0, a1 = MOM[idx]
    tx = texf(nm).copy()
    if idx + 1 < len(MOM) and t > a1 - TR:
        tx = trans(texf(nm), texf(MOM[idx + 1][0]), (t - (a1 - TR)) / TR, 'slide' if idx % 2 == 0 else 'fade')
    elif idx > 0 and t < a0 + 0.0:
        pass
    # finger tap just before each change
    for i, (nm_, ch_, b0, b1) in enumerate(MOM[:-1]):
        px, py = TAPXY[i]
        tx = touch_fx(tx, px, py, t, b1 - 1.05, 0.9, 1.25)
    # slow camera life
    k_ = idx + float(clamp01((t - a0) / (a1 - a0)))
    rx, ry, rz, sc, cx, cy = phone_pose(ts, 0.47, 665, amp=1.0, ry0=-4 * math.sin(k_ * 0.9), rx0=5)
    sc *= 1.0 + 0.04 * math.sin(ts * 0.5)
    entry = float(ease(ts / 0.8))
    gl = np.zeros((H, W, 3), np.float32)
    cv2.circle(gl, (W // 2, int(cy)), 430, (46, 88, 150), -1, cv2.LINE_AA)
    f = glow_add(f, gl, k=0.7, r=90, keep=0.0)
    f = glow_add(f, dl, k=0.8, r=10, keep=1.0)
    f, _ = phone().draw(f, tx, rx, ry, rz, sc, cx, cy, light=float(((ts - 0.5) * 0.15) % 1.5 - 0.25), sheen=0.12, glow=0.55, shadow=0.5, alpha=1.0)
    for i_, (nm_, ch_, b0, b1) in enumerate(MOM):
        glass_card(f, nm_, t, b0 + 0.45, b1 - 0.25, 1 if i_ % 2 == 0 else -1, i_)
    f = bloom(f, 175, 0.35, 20)
    f = vignette(f, 0.42)
    f = scrim(f, 0.55, 0.64)
    for (nm_, ch_, b0, b1) in MOM:
        chip(f, ch_, t, b0 + 0.2, b1 - 0.1)
    caption(f, 'c5a', t, 70.3, 73.0, 1800)
    caption(f, 'c5b', t, 73.2, 75.7, 1800)
    caption(f, 'c5c', t, 76.0, 80.6, 1800)
    caption(f, 'c5d', t, 81.0, 88.6, 1800)
    caption(f, 'c5e', t, 89.2, 97.4, 1800)
    f *= dipmul(ts, 0.0, 0.4, 27.6, 28.0)
    return f
