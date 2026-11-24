from film import *
from logo import *
import bisect

NODES = json.load(open('/tmp/vid/nodes.json'))     # [i, g, d, cx, cy, w]
CAM = {}
def cams(name):
    if name not in CAM: CAM[name] = json.load(open('/tmp/vid/seq/%s/cam.json' % name))
    return CAM[name]
def seqframe(name, n):
    im = cv2.imread('/tmp/vid/seq/%s/f%04d.jpg' % (name, n))
    if im.shape[:2] != (H, W): im = cv2.resize(im, (W, H), interpolation=cv2.INTER_LINEAR)
    return im.astype(np.float32)

YS, XS = np.mgrid[0:H, 0:W].astype(np.float32)

# ------------------------------------------------------------------ procedural roots (svg units, base at the foot of the trunk)
def make_roots(seed=11, base=(750.0, 1452.0)):
    r = np.random.RandomState(seed)
    roots = []
    def grow(p0, ang, length, width, depth, delay):
        pts = [np.array(p0, np.float32)]; a = ang; step = 12.0
        n = int(length / step)
        for i in range(n):
            a += r.randn() * 0.13 + (0.0 if abs(a) < 1.9 else -0.1 * np.sign(a))
            d = np.array([math.sin(a), math.cos(a)], np.float32) * step      # angle 0 = straight down
            pts.append(pts[-1] + d)
        pts = np.array(pts)
        roots.append({'p': pts, 'w': width, 'delay': delay, 'depth': depth})
        if depth < 3:
            for fr in (0.3, 0.55, 0.78):
                if r.rand() < 0.78 - 0.12 * depth:
                    k = int(len(pts) * fr)
                    side = 1 if r.rand() < 0.5 else -1
                    grow(pts[k], a + side * r.uniform(0.45, 0.95), length * r.uniform(0.38, 0.58), width * 0.6, depth + 1, delay + fr * 0.55)
    for ang in (-1.35, -0.95, -0.55, -0.2, 0.15, 0.5, 0.92, 1.32):
        grow(base, ang + r.randn() * 0.06, r.uniform(300, 520), 7.0, 0, r.uniform(0, 0.35))
    return roots
ROOTS = make_roots()

def draw_roots(layer, cam, g, bright, tflow):
    x, y, w, h = cam; k = W / w
    for rt in ROOTS:
        gg = clamp01((g - rt['delay'] * 0.35) / (1 - rt['delay'] * 0.35 + 1e-6)); gg = float(gg)
        if gg <= 0: continue
        pts = rt['p']; m = max(2, int(len(pts) * gg))
        sp = (pts[:m] - np.array([x, y], np.float32)) * k
        wd = max(1.0, rt['w'] * k)
        for i in range(m - 1):
            tp = 1 - i / len(pts) * 0.55
            c = tuple(float(v * bright * (0.55 + 0.45 * tp)) for v in (60, 175, 255))
            cv2.line(layer, (int(sp[i, 0]), int(sp[i, 1])), (int(sp[i + 1, 0]), int(sp[i + 1, 1])), c, max(1, int(round(wd * tp))), cv2.LINE_AA)
        # glowing tip
        if gg < 1:
            cv2.circle(layer, (int(sp[m - 1, 0]), int(sp[m - 1, 1])), max(3, int(wd * 1.8)), (200 * bright, 235 * bright, 255 * bright), -1, cv2.LINE_AA)
    # light flowing up the roots towards the trunk
    if tflow is not None:
        for j, rt in enumerate(ROOTS):
            if rt['depth'] > 1: continue
            pts = rt['p']
            for q in range(2):
                s = (tflow * 0.22 + j * 0.173 + q * 0.5) % 1.0
                idx = int((1 - s) * (len(pts) - 1))
                p = (pts[idx] - np.array([x, y], np.float32)) * k
                a = math.sin(s * math.pi) * bright * g
                cv2.circle(layer, (int(p[0]), int(p[1])), max(2, int(5 * k * 1.1)), (170 * a, 225 * a, 255 * a), -1, cv2.LINE_AA)

ROOTFADE = (1 - 0.8 * sm(1400, 1730, np.arange(H, dtype=np.float32)))[:, None, None].astype(np.float32)
DUST1 = Dust(260, seed=5, rmin=1.0, rmax=3.4, vy=(-10, -42))
DUST1b = Dust(90, seed=9, rmin=2.2, rmax=5.0, vy=(-6, -22))

def R_svg(t): return 1520.0 * float(ease((t - 4.8) / 8.0))
def lit_time(dist):
    if dist <= 0: return 4.8
    lo, hi = 4.8, 12.8
    for _ in range(40):
        mid = (lo + hi) / 2
        if R_svg(mid) >= dist: hi = mid
        else: lo = mid
    return hi
B0S = (750.0, 1250.0)
NODE_T = [(n[0], n[1], n[3], n[4], n[5], lit_time(math.hypot(n[3] - B0S[0], n[4] - B0S[1]))) for n in NODES]

def scene1(t, n):
    """0..15 s"""
    cam = cams('s1')[str(min(n, 449))]
    x, y, w, h = cam; k = W / w
    f = dark_bg(0.5, 0.60, (26, 18, 10), (6, 4, 2))
    f *= float(sm(0.0, 1.4, t))
    # --- reveal of the real tree
    Rs = R_svg(t)
    if Rs > 0:
        tr = seqframe('s1', min(n, 449))
        bx, by = (B0S[0] - x) * k, (B0S[1] - y) * k
        dist = np.sqrt((XS - bx) ** 2 + (YS - by) ** 2)
        Rp = Rs * k; fp = 150 * k
        m = 1 - sm(Rp - 0.2 * fp, Rp + 0.8 * fp, dist)
        ysv = y + YS[:, 0] / H * h
        wp = float(sm(10.2, 12.4, t))
        row = 1 - (1 - wp) * sm(1325, 1360, ysv)
        m = m * row[:, None]
        # brightness settles after the front passes
        f = f * (1 - m[..., None]) + tr * m[..., None] * (0.82 + 0.18 * float(sm(10, 14, t)))
        ring = np.exp(-((dist - (Rp + 0.15 * fp)) / (0.22 * fp)) ** 2) * (1 - float(sm(12.0, 13.2, t))) * 0.6
        ring = ring * row[:, None]
        lay = ring[..., None] * np.array([70, 175, 255], np.float32) * 0.9
        f += lay
        # nodes flare when the front reaches them
        nl = np.zeros((H, W, 3), np.float32)
        for (i, g, cx, cy, wd, tl) in NODE_T:
            tau = t - tl
            if 0 <= tau < 1.3 and g >= 1:
                a = math.exp(-tau / 0.45) * (1 - tau / 1.3)
                px, py = (cx - x) * k, (cy - y) * k
                if -80 < px < W + 80 and -80 < py < H + 80:
                    cv2.circle(nl, (int(px), int(py)), int(min(60, max(8, wd * k * (0.7 + tau * 0.9)))), (95 * a, 195 * a, 255 * a), -1, cv2.LINE_AA)
        f = glow_add(f, nl, k=0.9, r=22, keep=0.5)
    # --- roots (grow first, then calm down)
    gr = float(clamp01((t - 1.4) / 4.8)); gr = float(ease(gr))
    if gr > 0:
        lay = np.zeros((H, W, 3), np.float32)
        br = 1.0 - 0.55 * float(sm(8.0, 13.5, t))
        draw_roots(lay, cam, gr, br, t if t > 2 else None)
        lay *= ROOTFADE
        f = glow_add(f, lay, k=1.0, r=14, keep=1.0)
    # --- dust (denser at the beginning, drawn toward the centre of the frame later)
    dl = np.zeros((H, W, 3), np.float32)
    DUST1.draw(dl, t, alpha=float(sm(0.2, 2.0, t)) * (1 - 0.35 * float(sm(10, 14, t))))
    DUST1b.draw(dl, t * 0.7, alpha=float(sm(0.5, 2.5, t)) * 0.8)
    f = glow_add(f, dl, k=0.8, r=10, keep=1.0)
    f = bloom(f, 165, 0.45, 20)
    f = vignette(f, 0.5)
    # --- captions
    f = scrim(f, 0.55, 0.62)
    caption(f, 'c1a', t, 3.1, 7.0, 1780)
    caption(f, 'c1b', t, 7.3, 11.8, 1780)
    caption(f, 'c1c', t, 12.1, 15.1, 1790, fade=0.5)
    # flash into the next scene
    fl = float(sm(14.35, 15.0, t)) ** 1.6
    f = flash(f, fl)
    return f


FL_RAD = None
def flash(f, a):
    global FL_RAD
    if a <= 0.002: return f
    if FL_RAD is None:
        d = np.sqrt(((XS - W / 2) / (W * 0.7)) ** 2 + ((YS - H * 0.45) / (H * 0.6)) ** 2)
        FL_RAD = (clamp01(1.12 - d * 0.55) ** 1.2)[..., None].astype(np.float32)
    al = clamp01(a * (0.55 + 0.6 * FL_RAD))
    col = np.array([218, 244, 255], np.float32)
    return f * (1 - al) + col * al

# ====================================================================== SCENE 2
PHONE = None
def phone():
    global PHONE
    if PHONE is None: PHONE = Phone()
    return PHONE
_TX = {}
def texf(name):
    """texture resized to the phone screen size, float32 BGR"""
    if name not in _TX:
        im = img(A + name + '.png')
        if im.shape[:2] != (2532, 1170): im = cv2.resize(im, (1170, 2532), interpolation=cv2.INTER_AREA)
        _TX[name] = im.astype(np.float32)
    return _TX[name]
_ICON = None
def icon_rgba(size):
    global _ICON
    if _ICON is None: _ICON = cv2.imread('/home/claude/work/out/site227/icon-v3-512.png', cv2.IMREAD_UNCHANGED)
    return cv2.resize(_ICON, (size, size), interpolation=cv2.INTER_AREA if size < 512 else cv2.INTER_CUBIC)
_TXT = {}
def txtimg(name):
    if name not in _TXT:
        im = cv2.imread(C + name + '.png', cv2.IMREAD_UNCHANGED)
        assert im is not None and im.ndim == 3 and im.shape[2] == 4, name
        _TXT[name] = im
    return _TXT[name]
def put_center(f, rgba, cx, cy, scale=1.0, alpha=1.0, add=False):
    if scale != 1.0:
        rgba = cv2.resize(rgba, (max(2, int(rgba.shape[1] * scale)), max(2, int(rgba.shape[0] * scale))), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)
    h, w = rgba.shape[:2]
    return over(f, rgba, int(cx - w / 2), int(cy - h / 2), alpha, add)

DUST2 = Dust(160, seed=21, rmin=1.0, rmax=3.0, vy=(-12, -34))
def scene2(t, n):
    ts = t - 15.0
    f = dark_bg(0.5, 0.45, (36, 24, 12), (7, 5, 3))
    dl = np.zeros((H, W, 3), np.float32)
    DUST2.draw(dl, t, alpha=0.9)
    # ---------------- logo reveal
    la = float(1 - sm(4.2, 4.9, ts))
    if la > 0.002 and ts > 0.2:
        cx, cy = W / 2, 640
        aura = np.zeros((H, W, 3), np.float32)
        ag = la * float(sm(0.7, 1.5, ts)); cv2.circle(aura, (int(cx), int(cy)), 320, (40 * 0.5 * ag, 105 * 0.5 * ag, 175 * 0.5 * ag), -1, cv2.LINE_AA)
        f = glow_add(f, aura, k=1.2, r=70, keep=0.0)
        f = logo_mg(f, (ts - 0.25) * 1.35, cx, cy, size=600, title_y=985, line_y=1115, en_y=1200, tag_y=1330, tag_name='sub_ar', a=la)
    # ---------------- phone
    tp = ts - 4.3
    if tp > -0.1:
        pu = float(ease(tp / 3.8))
        push = float(ease((ts - 11.8) / 3.0))
        scale = lerp(lerp(0.38, 0.50, pu), 1.04, push)
        cy = lerp(lerp(2350, 700, pu), 960, push)
        cx = W / 2 + lerp(0, 0, push)
        ry = lerp(lerp(-52, -15, pu), 0, push) + 2.5 * math.sin(ts * 0.8) * (1 - push)
        rx = lerp(lerp(24, 7, pu), 0, push) + 1.5 * math.sin(ts * 0.6 + 1) * (1 - push)
        rz = lerp(lerp(7, -2, pu), 0, push)
        light = float(((ts - 6.0) * 0.18) % 1.6 - 0.3)
        gl = np.zeros((H, W, 3), np.float32)
        cv2.circle(gl, (int(W / 2), int(cy)), 420, (50 * pu, 95 * pu, 160 * pu), -1, cv2.LINE_AA)
        f = glow_add(f, gl, k=0.8, r=90, keep=0.0)
        f = glow_add(f, dl, k=0.8, r=10, keep=1.0)
        dl = None
        f, _ = phone().draw(f, texf('t_tree'), rx, ry, rz, scale, cx, cy, light=light, sheen=0.12, glow=0.6, shadow=0.5, alpha=float(sm(-0.1, 0.5, tp)))
    if dl is not None:
        f = glow_add(f, dl, k=0.8, r=10, keep=1.0)
    f = bloom(f, 170, 0.4, 20)
    f = vignette(f, 0.45)
    cap_a = 1 - float(sm(11.6, 12.3, ts))
    if cap_a > 0.01:
        f = scrim(f, 0.5 * cap_a, 0.62)
        caption(f, 'c2a', t, 15.9, 20.0, 1780)
        caption(f, 'c2b', t, 20.6, 26.6, 1780)
    # flash in (from scene 1) and flash out (into scene 3)
    fi = (1 - float(sm(0.0, 0.5, ts))) ** 1.6
    f = flash(f, fi)
    fo = float(sm(14.4, 15.0, ts)) ** 1.6
    f = flash(f, fo)
    return f
