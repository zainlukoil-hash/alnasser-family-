import numpy as np, cv2, json, math, os, sys
from PIL import Image, ImageDraw, ImageFilter
cv2.setNumThreads(2)
W, H, FPS = 1080, 1920, 30
A = '/tmp/vid/assets/'
C = '/tmp/vid/caps/'
GOLD = (70, 190, 245)      # BGR of (245,190,70)
WARM = (150, 215, 255)     # BGR of (255,215,150)

# ------------------------------------------------------------------ small maths
def clamp01(x): return np.clip(x, 0.0, 1.0)
def sm(a, b, x):
    t = clamp01((np.asarray(x, dtype=np.float32) - a) / (b - a)); return t * t * (3 - 2 * t)
def ease(u):
    u = clamp01(u); return u * u * u * (u * (6 * u - 15) + 10)
def lerp(a, b, u): return a + (b - a) * u

# ------------------------------------------------------------------ cache of images
_IM = {}
def img(path, flags=cv2.IMREAD_COLOR):
    k = (path, flags)
    if k not in _IM:
        im = cv2.imread(path, flags)
        assert im is not None, path
        _IM[k] = im
    return _IM[k]
def tex(name, w=None):
    """a phone screen shot from assets (BGR uint8)"""
    return img(A + name + '.png')

# ------------------------------------------------------------------ frame layers
def black(): return np.zeros((H, W, 3), np.float32)
_BG = {}
def dark_bg(cx=0.5, cy=0.46, c0=(30, 22, 14), c1=(9, 6, 3)):
    k = (cx, cy, c0, c1)
    if k not in _BG:
        ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((xs - cx * W) / (0.75 * W)) ** 2 + ((ys - cy * H) / (0.62 * H)) ** 2)
        m = clamp01(1 - d)[..., None] ** 1.6
        _BG[k] = (np.array(c1, np.float32) + (np.array(c0, np.float32) - np.array(c1, np.float32)) * m).astype(np.float32)
    return _BG[k].copy()

_VIG = None
def vignette(f, k=0.42):
    global _VIG
    if _VIG is None:
        ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
        d = np.sqrt(((xs - W / 2) / (W * 0.62)) ** 2 + ((ys - H / 2) / (H * 0.62)) ** 2)
        _VIG = (1 - k * clamp01(d - 0.35) ** 1.5)[..., None].astype(np.float32)
    f *= _VIG
    return f

_SCRIM = None
def scrim(f, k=0.62, y0=0.58):
    global _SCRIM
    if _SCRIM is None:
        ys = np.arange(H, dtype=np.float32) / H
        _SCRIM = (1 - k * sm(y0, 0.96, ys))[:, None, None].astype(np.float32)
    f *= _SCRIM
    return f

_GR = {}
def grain(f, n, amp=2.2):
    r = np.random.RandomState(n % 24)
    if n % 24 not in _GR:
        g = r.randn(H // 2, W // 2).astype(np.float32)
        _GR[n % 24] = cv2.resize(g, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
    f += _GR[n % 24] * amp
    return f

def bloom(f, thresh=150, k=0.55, r=21, scale=4):
    s = cv2.resize(f, (W // scale, H // scale), interpolation=cv2.INTER_AREA)
    s = np.maximum(s - thresh, 0)
    b = cv2.GaussianBlur(s, (0, 0), r / scale) + 0.6 * cv2.GaussianBlur(s, (0, 0), 3 * r / scale)
    f += k * cv2.resize(b, (W, H), interpolation=cv2.INTER_LINEAR)
    return f

def glow_add(f, layer, k=1.0, r=18, scale=4, keep=0.6):
    """layer: float32 additive layer (full res). Adds layer*keep plus its blurred halo"""
    s = cv2.resize(layer, (W // scale, H // scale), interpolation=cv2.INTER_AREA)
    b = cv2.GaussianBlur(s, (0, 0), r / scale) + 0.5 * cv2.GaussianBlur(s, (0, 0), 3.2 * r / scale)
    f += keep * layer
    f += k * cv2.resize(b, (W, H), interpolation=cv2.INTER_LINEAR)
    return f

def over(f, rgba, x, y, alpha=1.0, add=False):
    """straight-alpha BGRA (uint8 or float) onto float frame at integer x,y (top-left); clips"""
    h, w = rgba.shape[:2]
    x0, y0 = max(x, 0), max(y, 0); x1, y1 = min(x + w, W), min(y + h, H)
    if x1 <= x0 or y1 <= y0: return f
    p = rgba[y0 - y:y1 - y, x0 - x:x1 - x].astype(np.float32)
    a = (p[..., 3:4] / 255.0) * alpha
    if add:
        f[y0:y1, x0:x1] += p[..., :3] * a
    else:
        f[y0:y1, x0:x1] = f[y0:y1, x0:x1] * (1 - a) + p[..., :3] * a
    return f

def to_u8(f): return np.clip(f, 0, 255).astype(np.uint8)

# ------------------------------------------------------------------ dust
class Dust:
    def __init__(s, n, seed=1, rmin=0.8, rmax=3.0, vy=(-14, -48), spread=1.0, col=GOLD, y_range=(0, H)):
        r = np.random.RandomState(seed)
        s.n = n; s.x0 = r.rand(n) * W; s.y0 = y_range[0] + r.rand(n) * (y_range[1] - y_range[0])
        s.vy = r.uniform(vy[0], vy[1], n); s.ax = r.uniform(6, 40, n) * spread; s.fx = r.uniform(0.2, 0.9, n)
        s.ph = r.rand(n) * 6.28; s.tw = r.uniform(0.8, 2.6, n); s.rad = r.uniform(rmin, rmax, n)
        s.br = r.uniform(0.35, 1.0, n); s.col = np.array(col, np.float32); s.yr = y_range
    def draw(s, layer, t, alpha=1.0, wrap=True):
        span = s.yr[1] - s.yr[0]
        for i in range(s.n):
            x = s.x0[i] + math.sin(t * s.fx[i] + s.ph[i]) * s.ax[i]
            y = s.yr[0] + ((s.y0[i] - s.yr[0] + s.vy[i] * t) % span)
            a = alpha * s.br[i] * (0.35 + 0.65 * math.sin(t * s.tw[i] + s.ph[i]) ** 2)
            if a < 0.02: continue
            c = tuple(float(v * a) for v in s.col * 1.0)
            cv2.circle(layer, (int(x) % W, int(y)), max(1, int(round(s.rad[i]))), c, -1, cv2.LINE_AA)
        return layer

# ------------------------------------------------------------------ captions
_META = None
_CAP = {}
def cap_meta():
    global _META
    if _META is None: _META = json.load(open(C + 'meta.json'))
    return _META
def _capimg(k, m):
    if (k, m) not in _CAP: _CAP[(k, m)] = cv2.imread(C + '%s_%s.png' % (k, m), cv2.IMREAD_UNCHANGED).astype(np.float32)
    return _CAP[(k, m)]
def caption(f, cid, t, t0, t1, y_bottom=1800, words=True, fade=0.4, yshift=0):
    if t < t0 - 0.01 or t > t1 + 0.01: return f
    meta = cap_meta()[cid]; hh = meta['h']
    a = float(sm(t0, t0 + fade, t) * (1 - sm(t1 - fade, t1, t)))
    if a <= 0.003: return f
    d = _capimg(cid, 'd'); b = _capimg(cid, 'b')
    if words:
        ws = meta['words']; n = len(ws)
        lens = np.array([max(2, len(w)) for w in meta['text'].split(' ')], np.float32)
        cum = np.concatenate([[0], np.cumsum(lens)]) / lens.sum()
        u = float(clamp01((t - (t0 + 0.15)) / max(0.5, (t1 - t0) * 0.74)))
        mask = np.zeros((hh, W, 1), np.float32)
        for i, (l, tp, r, bt) in enumerate(ws):
            fr = float(clamp01((u - cum[i]) / max(1e-4, cum[i + 1] - cum[i])))
            if fr <= 0: continue
            x1 = int(r + 8); x0 = int(r + 8 - (r - l + 16) * fr)
            mask[max(0, int(tp) - 6):min(hh, int(bt) + 6), max(0, x0):min(W, x1)] = 1
        img_ = d * (1 - mask) + b * mask
    else:
        img_ = b
    rise = int((1 - ease((t - t0) / fade)) * 16)
    over(f, img_, 0, int(y_bottom - hh + rise + yshift), alpha=a)
    return f

# ------------------------------------------------------------------ signature
_SIG = None
def signature(f, a=0.62):
    global _SIG
    if _SIG is None: _SIG = cv2.imread('/tmp/vid/sig.png', cv2.IMREAD_UNCHANGED)
    h, w = _SIG.shape[:2]
    over(f, _SIG, W - w - 40, H - h - 62, alpha=a)
    return f

# ------------------------------------------------------------------ finger touch (drawn in screen texture space)
def touch_fx(tx, cx, cy, t, t0, dur=0.9, size=1.0):
    """draw a fingertip glow + ripple on a BGR float texture at (cx,cy) texture px"""
    u = (t - t0) / dur
    if u < -0.15 or u > 1.2: return tx
    base = 62 * size
    a_in = float(sm(-0.15, 0.08, u)); a_out = float(1 - sm(0.55, 1.2, u))
    lay = np.zeros(tx.shape[:2] + (1,), np.float32)
    if a_in * a_out > 0.01:
        cv2.circle(lay, (int(cx), int(cy)), int(base), (0.55 * a_in * a_out,), -1, cv2.LINE_AA)
        lay = cv2.GaussianBlur(lay, (0, 0), 7 * size)[..., None] if lay.ndim == 2 else cv2.GaussianBlur(lay, (0, 0), 7 * size).reshape(lay.shape)
        tx = tx * (1 - lay * 0.9) + np.array([255, 255, 255], np.float32) * lay * 0.9
    if 0.0 <= u <= 1.0:
        rr = base * (0.6 + 2.6 * ease(u)); aa = (1 - u) ** 1.5
        ring = np.zeros(tx.shape[:2], np.float32)
        cv2.circle(ring, (int(cx), int(cy)), int(rr), (aa,), max(2, int(6 * size)), cv2.LINE_AA)
        ring = cv2.GaussianBlur(ring, (0, 0), 2.2 * size)
        tx = tx + ring[..., None] * np.array([120, 200, 255], np.float32) * 0.9
    return tx

# ------------------------------------------------------------------ phone
class Phone:
    BEZ = 33; FRM = 20; RAD_OUT = 168; RAD_SCR = 120
    SW, SH = 1170, 2532
    def __init__(s):
        s.PW = s.SW + 2 * (s.BEZ + s.FRM); s.PH = s.SH + 2 * (s.BEZ + s.FRM)
        s._build()
        s.cache = {}
    def _rr(s, w, h, r, ss=2):
        im = Image.new('L', (w * ss, h * ss), 0)
        ImageDraw.Draw(im).rounded_rectangle([0, 0, w * ss - 1, h * ss - 1], r * ss, fill=255)
        return np.asarray(im.resize((w, h), Image.LANCZOS), np.float32) / 255.0
    def _build(s):
        PW, PH = s.PW, s.PH
        outer = s._rr(PW, PH, s.RAD_OUT)
        inner_b = s._rr(PW - 2 * s.FRM, PH - 2 * s.FRM, s.RAD_OUT - s.FRM)
        scr = s._rr(s.SW, s.SH, s.RAD_SCR)
        # titanium frame: vertical + diagonal brushed gradient
        ys, xs = np.mgrid[0:PH, 0:PW].astype(np.float32)
        g = 0.5 + 0.5 * np.sin((xs / PW) * 5.2 + (ys / PH) * 2.1)
        met = (62 + 70 * g)[..., None] * np.array([1.0, 1.02, 1.06], np.float32)
        # specular edge: stronger on outer rim
        edge = clamp01(1 - (cv2.GaussianBlur(inner_b_pad(inner_b, PW, PH, s.FRM), (0, 0), 3)))  # 0 inside, 1 outside
        rim = np.maximum(outer - cv2.erode(outer, np.ones((5, 5), np.uint8)), 0)[..., None]
        body = met + rim * 120
        bez = np.zeros((PH, PW, 3), np.float32) + 6
        inner_pad = inner_b_pad(inner_b, PW, PH, s.FRM)[..., None]
        img_ = body * (1 - inner_pad) + bez * inner_pad
        # hole for the screen
        hole = np.zeros((PH, PW), np.float32)
        o = s.BEZ + s.FRM
        hole[o:o + s.SH, o:o + s.SW] = scr
        alpha = outer * (1 - hole)
        s.body = np.dstack([img_, alpha[..., None] * 255]).astype(np.float32)
        s.scr_mask = scr[..., None].astype(np.float32)
        s.off = o
        # side buttons (drawn as extra bars on the frame at the outside edges)
        for (yy, hh) in ((int(PH * 0.20), int(PH * 0.045)), (int(PH * 0.285), int(PH * 0.07)), (int(PH * 0.375), int(PH * 0.07))):
            s.body[yy:yy + hh, 0:6, :3] = 105; s.body[yy:yy + hh, 0:6, 3] = 255
        yy, hh = int(PH * 0.31), int(PH * 0.11)
        s.body[yy:yy + hh, PW - 6:PW, :3] = 105; s.body[yy:yy + hh, PW - 6:PW, 3] = 255
        # dynamic island (on top of the screen)
        isl = np.zeros((s.SH, s.SW), np.float32)
        iw, ih = 330, 96
        cx = s.SW // 2; cy = 62
        cv2.ellipse(isl, (cx, cy), (iw // 2, ih // 2), 0, 0, 360, 1.0, -1, cv2.LINE_AA)
        s.island = isl[..., None]
        # glass sheen band template (diagonal)
        ys2, xs2 = np.mgrid[0:s.SH // 4, 0:s.SW // 4].astype(np.float32)
        s.diag = (xs2 * 0.55 + ys2 * 0.83) / ((s.SW / 4) * 0.55 + (s.SH / 4) * 0.83)
    def screen_img(s, texture, light=0.0, sheen=0.11):
        """texture: BGR float32 (SH,SW,3) -> composite screen with sheen + island"""
        t = texture
        if sheen > 0:
            band = np.exp(-((s.diag - light) / 0.07) ** 2) * 1.0 + 0.35 * np.exp(-((s.diag - light + 0.18) / 0.03) ** 2)
            band = cv2.resize(band.astype(np.float32), (s.SW, s.SH), interpolation=cv2.INTER_LINEAR)[..., None]
            t = t + band * 255 * sheen
        t = t * (1 - s.island)
        return t
    def compose(s, texture, light=0.0, sheen=0.11):
        sc = s.screen_img(texture, light, sheen) * s.scr_mask
        o = s.off
        B = s.body.copy()
        a = B[..., 3:4] / 255.0
        out = np.zeros((s.PH, s.PW, 4), np.float32)
        out[..., :3] = B[..., :3] * a
        out[..., 3:4] = a
        # insert screen in the hole (premultiplied)
        reg = out[o:o + s.SH, o:o + s.SW]
        m = s.scr_mask
        reg[..., :3] = reg[..., :3] * (1 - m) + sc * m
        reg[..., 3:4] = np.maximum(reg[..., 3:4], m)
        return out   # premultiplied BGRA float

    def project(s, rx, ry, rz, scale, cx, cy, f=3200.0):
        """4 destination corners (TL,TR,BR,BL) of the whole phone"""
        pw, ph = s.PW * scale, s.PH * scale
        pts = np.array([[-pw / 2, -ph / 2, 0], [pw / 2, -ph / 2, 0], [pw / 2, ph / 2, 0], [-pw / 2, ph / 2, 0]], np.float32)
        a, b, c = math.radians(rx), math.radians(ry), math.radians(rz)
        Rx = np.array([[1, 0, 0], [0, math.cos(a), -math.sin(a)], [0, math.sin(a), math.cos(a)]], np.float32)
        Ry = np.array([[math.cos(b), 0, math.sin(b)], [0, 1, 0], [-math.sin(b), 0, math.cos(b)]], np.float32)
        Rz = np.array([[math.cos(c), -math.sin(c), 0], [math.sin(c), math.cos(c), 0], [0, 0, 1]], np.float32)
        R = Rz @ Rx @ Ry
        q = pts @ R.T
        k = f / (f + q[:, 2])
        return np.stack([cx + q[:, 0] * k, cy + q[:, 1] * k], 1).astype(np.float32)

    def draw(s, f, texture, rx=0, ry=0, rz=0, scale=0.62, cx=W / 2, cy=H / 2, light=0.0, sheen=0.11, glow=0.5, shadow=0.55, alpha=1.0):
        """composite the phone on float frame f (BGR). texture float32 BGR (SH,SW,3)"""
        dst = s.project(rx, ry, rz, scale, cx, cy)
        # pre-shrink the texture for quality
        r = float(np.clip(scale * 1.25, 0.3, 1.0))
        if r < 0.98:
            tw, th = int(s.SW * r), int(s.SH * r)
            tex_s = cv2.resize(texture, (tw, th), interpolation=cv2.INTER_AREA)
        else:
            tex_s = texture
        # re-compose at reduced size
        if r < 0.98:
            P = s.compose_small(tex_s, r, light, sheen)
        else:
            P = s.compose(tex_s, light, sheen)
        ph, pw = P.shape[:2]
        src = np.array([[0, 0], [pw, 0], [pw, ph], [0, ph]], np.float32)
        M = cv2.getPerspectiveTransform(src, dst)
        Wp = cv2.warpPerspective(P, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        a = Wp[..., 3:4]
        # shadow + rim glow
        if shadow > 0 or glow > 0:
            sm_ = cv2.resize(a[..., 0], (W // 4, H // 4), interpolation=cv2.INTER_AREA)
            if glow > 0:
                gl = cv2.GaussianBlur(sm_, (0, 0), 16)
                f += (cv2.resize(gl, (W, H), interpolation=cv2.INTER_LINEAR))[..., None] * np.array([70, 130, 200], np.float32) * glow * alpha * 0.55
            if shadow > 0:
                sh = cv2.GaussianBlur(sm_, (0, 0), 20)
                sh = cv2.resize(sh, (W, H), interpolation=cv2.INTER_LINEAR)[..., None]
                f *= (1 - sh * shadow * 0.55 * alpha)
        f[:] = f * (1 - a * alpha) + Wp[..., :3] * alpha
        return f, dst

    _small = {}
    def compose_small(s, tex_s, r, light, sheen):
        key = r
        if key not in s._small:
            while len(s._small) > 2: s._small.pop(next(iter(s._small)))
            ph, pw = int(s.PH * r), int(s.PW * r)
            body = cv2.resize(s.body, (pw, ph), interpolation=cv2.INTER_AREA)
            o = int(round(s.off * r)); sh, sw = tex_s.shape[:2]
            mk = cv2.resize(s.scr_mask[..., 0], (sw, sh), interpolation=cv2.INTER_AREA)[..., None]
            isl = cv2.resize(s.island[..., 0], (sw, sh), interpolation=cv2.INTER_AREA)[..., None]
            ys2, xs2 = np.mgrid[0:sh, 0:sw].astype(np.float32)
            diag = (xs2 * 0.55 + ys2 * 0.83) / (sw * 0.55 + sh * 0.83)
            s._small[key] = (body, o, mk, isl, diag)
        body, o, mk, isl, diag = s._small[key]
        sh, sw = tex_s.shape[:2]
        t = tex_s
        if sheen > 0:
            band = np.exp(-((diag - light) / 0.07) ** 2) + 0.35 * np.exp(-((diag - light + 0.18) / 0.03) ** 2)
            t = t + band[..., None] * 255 * sheen
        t = t * (1 - isl)
        a = body[..., 3:4] / 255.0
        out = np.zeros(body.shape[:2] + (4,), np.float32)
        out[..., :3] = body[..., :3] * a; out[..., 3:4] = a
        reg = out[o:o + sh, o:o + sw]
        reg[..., :3] = reg[..., :3] * (1 - mk) + t * mk
        reg[..., 3:4] = np.maximum(reg[..., 3:4], mk)
        return out

def inner_b_pad(inner_b, PW, PH, FRM):
    z = np.zeros((PH, PW), np.float32)
    z[FRM:PH - FRM, FRM:PW - FRM] = inner_b
    return z

# ------------------------------------------------------------------ transitions between two screens (BGR float32, same size)
def trans(a, b, u, mode='fade'):
    u = float(ease(u))
    if u <= 0: return a
    if u >= 1: return b
    if mode == 'fade':
        return a * (1 - u) + b * u
    h, w = a.shape[:2]
    if mode == 'slide':      # b comes from the right (like a swipe)
        sh = int(w * u)
        out = np.empty_like(a)
        out[:, :w - sh] = a[:, sh:] * (1 - 0.35 * u)
        out[:, w - sh:] = b[:, :sh]
        return out
    if mode == 'up':          # b rises from the bottom
        sh = int(h * u)
        out = np.empty_like(a)
        out[:h - sh] = a[sh:] * (1 - 0.35 * u)
        out[h - sh:] = b[:sh]
        return out
    return a * (1 - u) + b * u


# ====================================================================== v3: dips, wipes, kinetic captions, bokeh
NODIP = False
def dipmul(ts, s0, s1, e0, e1):
    """fade-from/to-black multiplier used at scene boundaries; disabled when scenes are joined by wipes"""
    if NODIP: return 1.0
    return float(sm(s0, s1, ts)) * (1 - float(sm(e0, e1, ts)))

_YX = None
def _grid():
    global _YX
    if _YX is None: _YX = np.mgrid[0:H, 0:W].astype(np.float32)
    return _YX

def zoom_img(img, z, cx=None, cy=None, dx=0.0, dy=0.0):
    cx = W / 2 if cx is None else cx; cy = H / 2 if cy is None else cy
    M = np.array([[z, 0, cx - z * cx + dx], [0, z, cy - z * cy + dy]], np.float32)
    return cv2.warpAffine(img, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)

GOLD_BGR = np.array([70, 175, 255], np.float32)
def wipe(A, B, u, mode='ring', cx=None, cy=None, flip=False):
    """A -> B transition, u in 0..1 (A is the held last frame, B live). returns a new frame"""
    ys, xs = _grid()
    eu = float(ease(clamp01(u)))
    cx = W / 2 if cx is None else cx; cy = H * 0.46 if cy is None else cy
    if mode == 'ring':
        Rmax = math.hypot(max(cx, W - cx), max(cy, H - cy)) * 1.08
        R = eu * Rmax
        Az = zoom_img(A, 1 + 0.10 * eu, cx, cy)
        Bz = zoom_img(B, 1.16 - 0.16 * eu, cx, cy)
        dist = np.sqrt((xs - cx) ** 2 + (ys - cy) ** 2)
        m = clamp01((R - dist) / 90.0 + 0.5)[..., None]
        out = Az * (1 - m) + Bz * m
        ring = np.exp(-((dist - R) / 34.0) ** 2) * math.sin(math.pi * clamp01(u)) ** 0.6
        lay = (ring[..., None] * GOLD_BGR * 1.25).astype(np.float32)
        out = glow_add(out, lay, k=1.4, r=34, keep=1.0)
        return out
    if mode == 'sweep':
        a = math.radians(24)
        proj = (xs - W / 2) * math.cos(a) + (ys - H / 2) * math.sin(a)
        span = abs(W * math.cos(a)) / 2 + abs(H * math.sin(a)) / 2 + 160
        p = (-span + 2 * span * eu) * (-1 if flip else 1)
        sgn = -1 if flip else 1
        m = clamp01(sgn * (p - proj) / 70.0 + 0.5)[..., None]
        sh = 70 * eu * (-1 if not flip else 1)
        Az = zoom_img(A, 1.0 + 0.05 * eu, dx=sh)
        Bz = zoom_img(B, 1.06 - 0.06 * eu, dx=sh - sgn * 0)
        out = Az * (1 - m) + Bz * m
        beam = np.exp(-((proj - p) / 46.0) ** 2) * math.sin(math.pi * clamp01(u)) ** 0.5
        lay = (beam[..., None] * np.array([120, 205, 255], np.float32) * 1.3).astype(np.float32)
        out = glow_add(out, lay, k=1.6, r=40, keep=1.0)
        return out
    if mode == 'push':
        Az = zoom_img(A, 1 + 0.75 * eu ** 1.3, cx, cy)
        if eu > 0.05: Az = cv2.GaussianBlur(Az, (0, 0), 14 * eu)
        Bz = zoom_img(B, 0.72 + 0.28 * eu, cx, cy)
        k = float(sm(0.28, 0.72, u))
        out = Az * (1 - k) + Bz * k
        fl = math.sin(math.pi * clamp01(u)) ** 3
        out = out + fl * 0.5 * np.array([150, 215, 255], np.float32)
        return out
    return B

_BOK = None
def bokeh(f, t, seed=5, n=12, alpha=0.5, zone=(0, H)):
    """slow drifting out-of-focus light discs (depth); additive"""
    r = np.random.RandomState(seed)
    lay = np.zeros((H // 4, W // 4, 3), np.float32)
    for i in range(n):
        x0, y0 = r.rand() * W, zone[0] + r.rand() * (zone[1] - zone[0])
        rad = r.uniform(26, 80); vx, vy = r.uniform(-9, 9), r.uniform(-22, -6)
        ph = r.rand() * 6.28; col = np.array([r.uniform(40, 90), r.uniform(120, 190), r.uniform(200, 255)], np.float32)
        x = (x0 + vx * t) % W; y = zone[0] + ((y0 - zone[0] + vy * t) % (zone[1] - zone[0]))
        a = alpha * (0.25 + 0.75 * math.sin(t * 0.5 + ph) ** 2) * 0.22
        cv2.circle(lay, (int(x / 4), int(y / 4)), int(rad / 4), tuple(float(c * a) for c in col), -1, cv2.LINE_AA)
    lay = cv2.GaussianBlur(lay, (0, 0), 3.0)
    f += cv2.resize(lay, (W, H), interpolation=cv2.INTER_LINEAR)
    return f

def caption_k(f, cid, t, t0, t1, y_bottom=1800, words=True, fade=0.45, yshift=-28):
    """kinetic captions: each word rises out of blur with a golden flash as it is spoken"""
    if t < t0 - 0.01 or t > t1 + 0.01: return f
    meta = cap_meta()[cid]; hh = meta['h']
    out_a = float(1 - sm(t1 - fade, t1, t))
    if out_a <= 0.003: return f
    b = _capimg(cid, 'b')
    ws = meta['words']
    lens = np.array([max(2, len(w)) for w in meta['text'].split(' ')], np.float32)
    cum = np.concatenate([[0], np.cumsum(lens)]) / lens.sum()
    span = max(0.5, (t1 - t0) * 0.74)
    layer = np.zeros((hh, W, 4), np.float32)
    glow = np.zeros((hh, W, 3), np.float32)
    PAD = 14
    for i, (l, tp, r, bt) in enumerate(ws):
        ta = t0 + 0.12 + cum[i] * span
        k = (t - ta) / 0.55
        if k <= 0: continue
        e = float(ease(clamp01(k)))
        x0, x1 = max(0, int(l) - PAD), min(W, int(r) + PAD)
        y0, y1 = max(0, int(tp) - PAD), min(hh, int(bt) + PAD)
        crop = b[y0:y1, x0:x1].copy()
        if e < 0.98:
            s_ = (1 - e) * 5.0
            if s_ > 0.4: crop = cv2.GaussianBlur(crop, (0, 0), s_)
        crop[..., 3] *= e
        dy = int((1 - e) * 30)
        yy0, yy1 = y0 + dy, y1 + dy
        if yy1 > hh: crop = crop[:hh - yy0]; yy1 = hh
        dst = layer[yy0:yy1, x0:x1]
        sa = crop[..., 3:4] / 255.0; da = dst[..., 3:4] / 255.0
        oa = sa + da * (1 - sa)
        dst[..., :3] = np.where(oa > 1e-4, (crop[..., :3] * sa + dst[..., :3] * da * (1 - sa)) / np.maximum(oa, 1e-4), 0)
        dst[..., 3:4] = oa * 255.0
        if 0 < k < 1.8:
            g = math.exp(-k * 2.6) * (1.0 if k > 0 else 0)
            glow[yy0:yy1, x0:x1] += (crop[..., 3:4] / 255.0) * g * np.array([90, 190, 255], np.float32) * 0.9
    ys = int(y_bottom - hh + yshift)
    over(f, layer, 0, ys, alpha=out_a)
    if glow.max() > 1:
        gb = cv2.GaussianBlur(glow, (0, 0), 12)
        y0_, y1_ = max(ys, 0), min(ys + hh, H)
        if y1_ > y0_: f[y0_:y1_] += (gb[y0_ - ys:y1_ - ys] + 0.5 * glow[y0_ - ys:y1_ - ys]) * out_a
    return f

caption_classic = caption
caption = caption_k
