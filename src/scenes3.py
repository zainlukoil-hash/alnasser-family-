from scenes2 import *
from logo import *

# ====================================================================== SCENE 6 : a smartphone experience (98 .. 113)
_SCROLL = None
def scroll_tex():
    global _SCROLL
    if _SCROLL is None: _SCROLL = img(A + 't_home_scroll.png').astype(np.float32)
    return _SCROLL
def scene6(t, n):
    ts = t - 98.0
    f = wallpaper(t)
    dl = np.zeros((H, W, 3), np.float32)
    DUST3.draw(dl, t * 0.8 + 11, alpha=0.85)
    home, (ix, iy) = homescreen()
    t_tree = texf('t_tree')
    # screen timeline
    if ts < 3.0:
        tx = home.copy()
        tx = touch_fx(tx, ix, iy, ts, 2.2, 0.9, 1.3)
        # the icon swells when pressed
        if 2.3 < ts: tx = warp_scale(tx, 1.0 + 0.03 * float(sm(2.3, 3.0, ts)), ix, iy)
    elif ts < 4.9:
        u = float(ease((ts - 3.0) / 1.9))
        a = warp_scale(home, 1.0 + 3.2 * u, ix, iy)
        b = warp_scale(t_tree, lerp(0.25, 1.0, u), ix, iy)
        al = float(sm(0.0, 0.7, u))
        tx = a * (1 - al) + b * al
    elif ts < 7.0:
        tx = t_tree.copy()
        tx = touch_fx(tx, 675, 2400, ts, 5.7, 0.9, 1.25)
        if ts > 6.3: tx = trans(t_tree, scroll_tex()[0:2532], (ts - 6.3) / 0.7, 'fade')
    else:
        sc = scroll_tex()
        prog = float(ease((ts - 7.0) / 6.6))
        y0 = int(prog * (sc.shape[0] - 2532))
        tx = sc[y0:y0 + 2532].copy()
        # a thumb dragging upward, over and over
        if ts < 13.6:
            ph = ((ts - 7.0) * 0.55) % 1.0
            py = int(2050 - 950 * ph); a = float(sm(0, 0.12, ph) * (1 - sm(0.8, 1.0, ph)))
            lay = np.zeros(tx.shape[:2], np.float32)
            cv2.circle(lay, (620, py), 60, (0.65 * a,), -1, cv2.LINE_AA)
            lay = cv2.GaussianBlur(lay, (0, 0), 8)[..., None]
            tx = tx * (1 - lay) + 255 * lay
    # pose
    entry = float(ease(ts / 0.9))
    rx, ry, rz, sc_, cx, cy = phone_pose(ts, 0.58, 780, amp=1.1, ry0=-8, rx0=6)
    sc_ = sc_ * (0.94 + 0.06 * entry)
    gl = np.zeros((H, W, 3), np.float32)
    cv2.circle(gl, (W // 2, int(cy)), 470, (50, 92, 155), -1, cv2.LINE_AA)
    f = glow_add(f, gl, k=0.7, r=90, keep=0.0)
    f = glow_add(f, dl, k=0.8, r=10, keep=1.0)
    f, _ = phone().draw(f, tx, rx, ry, rz, sc_, cx, cy, light=float(((ts - 0.3) * 0.17) % 1.5 - 0.25), sheen=0.13, glow=0.6, shadow=0.5, alpha=1.0)
    f = bloom(f, 175, 0.35, 20)
    f = vignette(f, 0.42)
    f = scrim(f, 0.55, 0.66)
    caption(f, 'c6a', t, 98.6, 102.8, 1800)
    caption(f, 'c6b', t, 103.4, 111.8, 1800)
    f *= dipmul(ts, 0.0, 0.45, 14.5, 15.0)
    return f

# ====================================================================== SCENE 7 : the emotional connection (113 .. 125)
_PORT = {}
def portrait(i, r):
    key = (i, r)
    if key not in _PORT:
        im = cv2.imread('/tmp/vid/port/%d.png' % i)
        im = cv2.resize(im, (2 * r, 2 * r), interpolation=cv2.INTER_CUBIC if r > 130 else cv2.INTER_AREA)
        m = np.zeros((2 * r, 2 * r), np.float32); cv2.circle(m, (r, r), r - 6, 1.0, -1, cv2.LINE_AA)
        rgba = np.dstack([im.astype(np.float32), (m * 255)[..., None]])
        ring = np.zeros((2 * r, 2 * r), np.float32); cv2.circle(ring, (r, r), r - 4, 1.0, 6, cv2.LINE_AA)
        rgba[..., :3] = rgba[..., :3] * (1 - ring[..., None]) + np.array([80, 195, 250], np.float32) * ring[..., None]
        rgba[..., 3] = np.maximum(rgba[..., 3], ring * 255)
        _PORT[key] = rgba
    return _PORT[key]
ROWA = [(69, 140, 440), (75, 330, 410), (98, 540, 395), (28, 750, 410), (3, 940, 440)]
ROWB = [(4, 250, 830), (46, 450, 790), (59, 630, 790), (55, 830, 830)]
ORBS = [(165, 1210, '#A98BDB'), (320, 1170, '#44C2C8'), (475, 1215, '#F28B6B'), (605, 1215, '#B7CE4B'), (760, 1170, '#F6B93B'), (915, 1210, '#5AA9E6')]
FUT = [(210, 1405), (390, 1440), (570, 1415), (750, 1445), (900, 1410)]
def hex2bgr(h): return (int(h[5:7], 16), int(h[3:5], 16), int(h[1:3], 16))
def bez(p0, p1, p2, p3, u):
    a = (1 - u) ** 3; b = 3 * u * (1 - u) ** 2; c = 3 * u * u * (1 - u); d = u ** 3
    return (a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1])
def thread(layer, p0, p3, prog, bright, tpulse, seed):
    p1 = (p0[0], p0[1] + (p3[1] - p0[1]) * 0.5); p2 = (p3[0], p3[1] - (p3[1] - p0[1]) * 0.5)
    m = int(46 * prog)
    pts = [bez(p0, p1, p2, p3, i / 45) for i in range(m + 1)]
    for i in range(m):
        cv2.line(layer, (int(pts[i][0]), int(pts[i][1])), (int(pts[i + 1][0]), int(pts[i + 1][1])), (60 * bright, 170 * bright, 245 * bright), 3, cv2.LINE_AA)
    if prog > 0.99:
        for q in range(2):
            u = (tpulse * 0.32 + seed * 0.37 + q * 0.5) % 1.0
            x, y = bez(p0, p1, p2, p3, u)
            a = math.sin(u * math.pi) * bright
            cv2.circle(layer, (int(x), int(y)), 7, (190 * a, 235 * a, 255 * a), -1, cv2.LINE_AA)
LINKS_AB = [(0, 0), (0, 1), (1, 1), (2, 1), (2, 2), (3, 2), (4, 3), (3, 3)]
LINKS_BC = [(0, 0), (0, 1), (1, 1), (1, 2), (2, 2), (2, 3), (3, 4), (3, 5)]
_BG7 = None
def bg7():
    global _BG7
    if _BG7 is None:
        im = seqframe('s3', 659)
        im = cv2.GaussianBlur(im, (0, 0), 5)
        _BG7 = (im * 0.30 * np.array([1.0, 0.95, 0.85], np.float32)).astype(np.float32)
    return _BG7.copy()
DUST7 = Dust(180, seed=71, rmin=1.0, rmax=3.2, vy=(-16, -50))
def scene7(t, n):
    ts = t - 113.0
    f = bg7()
    f *= dipmul(ts, 0.0, 1.2, 99.0, 100.0)
    lay = np.zeros((H, W, 3), np.float32)
    # threads
    for j, (a, b) in enumerate(LINKS_AB):
        pr = float(ease((ts - (2.0 + 0.12 * j)) / 1.6))
        if pr > 0:
            thread(lay, (ROWA[a][1], ROWA[a][2] + 105), (ROWB[b][1], ROWB[b][2] - 96), pr, 0.9, ts, j)
    for j, (b, c) in enumerate(LINKS_BC):
        pr = float(ease((ts - (4.4 + 0.12 * j)) / 1.6))
        if pr > 0:
            thread(lay, (ROWB[b][1], ROWB[b][2] + 96), (ORBS[c][0], ORBS[c][1] - 66), pr, 0.9, ts + 1.3, j + 9)
    f = glow_add(f, lay, k=1.0, r=12, keep=1.0)
    # portraits / orbs
    gl = np.zeros((H, W, 3), np.float32)
    for k_, (pid, x, y) in enumerate(ROWA):
        a = float(ease((ts - (0.7 + 0.28 * k_)) / 1.1))
        if a > 0:
            cv2.circle(gl, (x, y), 130, (35 * a, 90 * a, 150 * a), -1, cv2.LINE_AA)
    for k_, (pid, x, y) in enumerate(ROWB):
        a = float(ease((ts - (3.0 + 0.3 * k_)) / 1.1))
        if a > 0: cv2.circle(gl, (x, y), 118, (35 * a, 90 * a, 150 * a), -1, cv2.LINE_AA)
    for k_, (x, y, col) in enumerate(ORBS):
        a = float(ease((ts - (5.2 + 0.22 * k_)) / 1.0))
        if a > 0:
            c = hex2bgr(col); cv2.circle(gl, (x, y), 92, tuple(float(v * 0.35 * a) for v in c), -1, cv2.LINE_AA)
    f = glow_add(f, gl, k=1.1, r=50, keep=0.0)
    for k_, (pid, x, y) in enumerate(ROWA):
        a = float(ease((ts - (0.7 + 0.28 * k_)) / 1.1))
        if a > 0:
            sc = 0.85 + 0.15 * a; put_center(f, portrait(pid, 105), x, y + (1 - a) * 18, sc, a)
    for k_, (pid, x, y) in enumerate(ROWB):
        a = float(ease((ts - (3.0 + 0.3 * k_)) / 1.1))
        if a > 0:
            sc = 0.85 + 0.15 * a; put_center(f, portrait(pid, 96), x, y + (1 - a) * 18, sc, a)
    ol = np.zeros((H, W, 3), np.float32)
    for k_, (x, y, col) in enumerate(ORBS):
        a = float(ease((ts - (5.2 + 0.22 * k_)) / 1.0))
        if a > 0:
            c = hex2bgr(col); r_ = int(60 + 6 * math.sin(ts * 1.6 + k_))
            cv2.circle(ol, (x, y), int(r_ * (0.7 + 0.3 * a)), tuple(float(v * a) for v in c), -1, cv2.LINE_AA)
            cv2.circle(ol, (x, y), int(r_ * (0.7 + 0.3 * a)), (255 * a, 245 * a, 220 * a), 4, cv2.LINE_AA)
    f = np.where(ol > 0, np.maximum(f, ol), f) if ts > 5.2 else f
    # future generations: dotted outlines that start to glow
    fl = np.zeros((H, W, 3), np.float32)
    for k_, (x, y) in enumerate(FUT):
        a = float(ease((ts - (7.0 + 0.3 * k_)) / 1.2))
        if a > 0:
            pulse = 0.55 + 0.45 * math.sin(ts * 2.0 + k_ * 1.3)
            for d in range(0, 360, 20):
                px = x + 46 * math.cos(math.radians(d)); py = y + 46 * math.sin(math.radians(d))
                cv2.circle(fl, (int(px), int(py)), 3, (110 * a * pulse, 215 * a * pulse, 255 * a * pulse), -1, cv2.LINE_AA)
            cv2.circle(fl, (x, y), 10, (170 * a * pulse, 235 * a * pulse, 255 * a * pulse), -1, cv2.LINE_AA)
    f = glow_add(f, fl, k=0.9, r=16, keep=1.0)
    dl = np.zeros((H, W, 3), np.float32)
    DUST7.draw(dl, t, alpha=0.9)
    f = glow_add(f, dl, k=0.8, r=10, keep=1.0)
    # row labels
    for nm, y_, t0 in (('gp', 585, 1.2), ('par', 976, 3.6), ('kid', 1320, 5.9), ('fut', 1500, 8.0)):
        a = float(sm(t0, t0 + 0.7, ts))
        if a > 0.01: put_center(f, txtimg('lab_' + nm), W / 2, y_, 0.62, a * 0.95)
    f = bloom(f, 170, 0.4, 20)
    f = vignette(f, 0.45)
    f = scrim(f, 0.5, 0.78)
    caption(f, 'c7a', t, 113.7, 118.3, 1800)
    caption(f, 'c7b', t, 118.9, 124.4, 1800)
    f *= dipmul(ts, 0.0, 0.5, 11.5, 12.0)
    return f

# ====================================================================== SCENE 8 : the grand finale (125 .. 135)
def R8(ts): return 1600.0 * float(ease((ts - 0.5) / 2.9))
ROOT8 = (756.0, 750.0)
NODE8 = [(n[0], n[1], n[3], n[4], n[5]) for n in NODES]
def lit8(dist):
    lo, hi = 0.5, 3.4
    for _ in range(30):
        mid = (lo + hi) / 2
        if R8(mid) >= dist: hi = mid
        else: lo = mid
    return hi
NODE8T = [(i, g, cx, cy, wd, lit8(math.hypot(cx - ROOT8[0], cy - ROOT8[1]))) for (i, g, cx, cy, wd) in NODE8]
DUST8 = Dust(150, seed=81, rmin=1.0, rmax=3.2, vy=(-14, -40))
def logo_rays(f, cx, cy, ts, a, length=900):
    ray = np.zeros((H, W, 3), np.float32)
    for q in range(16):
        ang = ts * 0.25 + q * (2 * math.pi / 16)
        w_ = 0.05 + 0.03 * math.sin(q * 2.1)
        p1 = (cx + length * math.cos(ang - w_), cy + length * math.sin(ang - w_)); p2 = (cx + length * math.cos(ang + w_), cy + length * math.sin(ang + w_))
        cv2.fillPoly(ray, [np.array([(cx, cy), p1, p2], np.int32)], (45 * a, 120 * a, 180 * a), cv2.LINE_AA)
    ray = cv2.GaussianBlur(ray, (0, 0), 10)
    f += ray
    return f
def scene8(t, n):
    ts = t - 125.0
    n8 = int(min(max(round(ts * FPS), 0), 194))
    cam = cams('s8')[str(n8)]
    x, y, w, h = cam; k = W / w
    f = seqframe('s8', n8)
    f = f * (0.78 + 0.22 * float(sm(0.2, 1.4, ts)))
    # the wave of light + simultaneous flare
    Rs = R8(ts)
    if 0 < Rs < 1700:
        rx_, ry_ = (ROOT8[0] - x) * k, (ROOT8[1] - y) * k
        dist = np.sqrt((XS - rx_) ** 2 + (YS - ry_) ** 2)
        ring = np.exp(-((dist - Rs * k) / (90 * k)) ** 2) * 0.8
        f += ring[..., None] * np.array([70, 175, 255], np.float32)
    nl = np.zeros((H, W, 3), np.float32)
    for (i, g, cx, cy, wd, tl) in NODE8T:
        tau = ts - tl
        if 0 <= tau < 1.6:
            a = math.exp(-tau / 0.55)
            px, py = (cx - x) * k, (cy - y) * k
            if -80 < px < W + 80 and -80 < py < H + 80:
                cv2.circle(nl, (int(px), int(py)), int(min(55, max(8, wd * k * (0.7 + tau * 0.8)))), (95 * a, 195 * a, 255 * a), -1, cv2.LINE_AA)
    f = glow_add(f, nl, k=0.9, r=22, keep=0.5)
    bump = float(sm(3.0, 3.35, ts) * (1 - sm(3.35, 4.2, ts)))
    f *= 1 + 0.55 * bump
    # logo reveal
    dim = (1 - 0.78 * float(sm(2.9, 4.4, ts))) * (1 - 0.55 * float(sm(6.2, 8.2, ts)))
    f *= dim
    la = float(sm(2.6, 3.6, ts))
    if la > 0:
        cx, cy = W / 2, 585
        f = logo_rays(f, cx, cy, ts, la * 0.38 * (1 - 0.7 * float(sm(5.6, 7.5, ts))))
        aura = np.zeros((H, W, 3), np.float32)
        ap = 0.30 * float(sm(3.2, 3.9, ts))
        cv2.circle(aura, (int(cx), int(cy)), 330, (50 * ap, 120 * ap, 190 * ap), -1, cv2.LINE_AA)
        f = glow_add(f, aura, k=1.3, r=80, keep=0.0)
        f = logo_mg(f, ts - 2.15, cx, cy, size=600, title_y=1000, line_y=1130, en_y=1218, tag_y=1348, tag_name='tag_en', a=1.0)
        ca = float(sm(6.0, 7.2, ts))
        if ca > 0.01: put_center(f, txtimg('credit_ar'), W / 2, 1462, 1.0, ca * 0.9)
    dl = np.zeros((H, W, 3), np.float32)
    DUST8.draw(dl, t, alpha=0.85)
    f = glow_add(f, dl, k=0.8, r=10, keep=1.0)
    f = bloom(f, 170, 0.45, 20)
    f = vignette(f, 0.5)
    sc_a = 1 - float(sm(4.2, 4.9, ts))
    if sc_a > 0.01:
        f = scrim(f, 0.55 * sc_a, 0.66)
        caption(f, 'c8a', t, 125.4, 129.0, 1800)
    caption(f, 'c8b', t, 129.7, 133.2, 1800)
    f *= dipmul(ts, 0.0, 0.5, 99.0, 100.0) * (1 - float(sm(9.35, 10.0, ts)))
    return f
