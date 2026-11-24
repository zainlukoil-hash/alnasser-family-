import numpy as np, math, wave, sys
from scipy import signal
SR = 44100
DUR = 135.0
N = int(SR * DUR)
rng = np.random.RandomState(11)
BPM = 96.0; BEAT = 60.0 / BPM; BAR = 4 * BEAT       # 0.625 / 2.5 s

# ------------------------------------------------------------------ buses (stereo)
class Bus:
    def __init__(s): s.L = np.zeros(N, np.float32); s.R = np.zeros(N, np.float32)
DRY = Bus(); LONG = Bus(); SHORT = Bus()

def tt(d): return np.arange(int(d * SR)) / SR
def sm(a, b, x):
    u = np.clip((x - a) / (b - a), 0, 1); return u * u * (3 - 2 * u)
def lp(x, fc, order=2):
    b, a = signal.butter(order, min(fc, 20000) / (SR / 2), 'low'); return signal.lfilter(b, a, x).astype(np.float32)
def hp(x, fc, order=2):
    b, a = signal.butter(order, fc / (SR / 2), 'high'); return signal.lfilter(b, a, x).astype(np.float32)
def bp(x, f1, f2, order=2):
    b, a = signal.butter(order, [f1 / (SR / 2), min(f2, 20000) / (SR / 2)], 'band'); return signal.lfilter(b, a, x).astype(np.float32)
def noise(d): return rng.randn(int(d * SR)).astype(np.float32)

def put(sig, t0, dry=1.0, long=0.0, short=0.0, pan=0.0):
    """mono signal -> buses with constant-power pan (-1..1)"""
    i0 = int(t0 * SR)
    if i0 >= N or i0 + len(sig) <= 0: return
    if i0 < 0: sig = sig[-i0:]; i0 = 0
    n = min(len(sig), N - i0)
    s = sig[:n]
    th = (pan + 1) * math.pi / 4
    gl, gr = math.cos(th), math.sin(th)
    for bus, g in ((DRY, dry), (LONG, long), (SHORT, short)):
        if g > 0:
            bus.L[i0:i0 + n] += s * (g * gl); bus.R[i0:i0 + n] += s * (g * gr)

# ------------------------------------------------------------------ pitch
NOTE = {'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11}
def mid(name):
    p = NOTE[name[0]]; i = 1
    while name[i] in '#b':
        p += 1 if name[i] == '#' else -1; i += 1
    return 12 * (int(name[i:]) + 1) + p
def hz(m): return 440.0 * 2 ** ((m - 69) / 12.0)
def F(name): return hz(mid(name))

# ------------------------------------------------------------------ instruments
def ks(f, d, g=0.996, bright=0.55, pos=0.18, body=True):
    """Karplus-Strong plucked string with fractional-delay tuning"""
    n = int(d * SR)
    Pf = SR / f - 0.5
    P = int(Pf); fr = Pf - P
    a = np.zeros(P + 3); a[0] = 1.0
    a[P] -= g * 0.5 * (1 - fr); a[P + 1] -= g * 0.5; a[P + 2] -= g * 0.5 * fr
    ex = rng.randn(P + 2)
    al = 1 - bright * 0.9
    ex = signal.lfilter([1 - al], [1, -al], ex)               # excitation colour
    k = max(1, int(P * pos))
    ex[k:] = ex[k:] - ex[:-k] * 0.9                           # pick position comb
    ex = ex / (np.abs(ex).max() + 1e-9)
    x = np.zeros(n); x[:min(len(ex), n)] = ex[:n]
    y = signal.lfilter([1.0], a, x)
    y *= np.minimum(1, np.arange(n) / 40.0)
    if body:
        for fc, q, gg in ((230, 5, 0.9), (480, 6, 0.6), (1100, 5, 0.3)):
            b_, a_ = signal.iirpeak(fc / (SR / 2), q)
            y = y + gg * signal.lfilter(b_, a_, y) * 0.5
    y = y / (np.abs(y).max() + 1e-9)
    return y.astype(np.float32)

def oud(f, d=2.4, vel=1.0):
    y = ks(f, d, g=0.9965, bright=0.38, pos=0.16, body=True)
    click = hp(noise(0.02), 2500) * np.exp(-tt(0.02) * 160) * 0.05
    y[:len(click)] += click
    return y * vel

def qanun(f, d=2.6, vel=1.0):
    y1 = ks(f * 1.0008, d, g=0.9985, bright=0.85, pos=0.08, body=False)
    y2 = ks(f * 0.9992, d, g=0.9985, bright=0.85, pos=0.08, body=False)
    return (0.5 * (y1 + y2) * vel).astype(np.float32)

def ney(f, d, vel=1.0, scoop=0.025, vib=0.0055):
    n = int(d * SR); t = np.arange(n) / SR
    fc = f * (1 - scoop * np.exp(-t / 0.07))
    vdepth = vib * sm(0.25, 0.9, t)
    fc = fc * (1 + vdepth * np.sin(2 * math.pi * 5.3 * t + rng.rand() * 6))
    ph = 2 * math.pi * np.cumsum(fc) / SR
    y = np.sin(ph) + 0.30 * np.sin(2 * ph) + 0.10 * np.sin(3 * ph) + 0.04 * np.sin(4 * ph)
    env = np.minimum(1, t / 0.09) * np.clip((d - t) / 0.22, 0, 1)
    env *= (0.82 + 0.18 * np.sin(2 * math.pi * 0.35 * t + 1))
    br = bp(noise(d), 1200, 5200) * (0.10 + 0.10 * np.exp(-t / 0.12))
    return ((y * 0.5 + br) * env * vel).astype(np.float32)

def saw_stack(f, d, voices=5, det=0.006, harm=14, vib=0.004, atk=0.5, rel=0.9, cutoff=3200):
    n = int(d * SR); t = np.arange(n) / SR
    y = np.zeros(n, np.float32)
    nh = int(min(harm, 9000 / f))
    for v in range(voices):
        dv = (v - (voices - 1) / 2) * det / max(1, (voices - 1) / 2)
        fv = f * (1 + dv) * (1 + vib * sm(0.3, 1.2, t) * np.sin(2 * math.pi * (5.0 + 0.3 * v) * t + v))
        ph = 2 * math.pi * np.cumsum(fv) / SR
        for k in range(1, nh + 1):
            y += (1.0 / k) * np.sin(k * ph + 0.9 * v + 0.37 * k).astype(np.float32)
    env = np.minimum(1, t / atk) ** 1.4 * np.clip((d - t) / rel, 0, 1) ** 1.3
    y = lp(y, cutoff) * env
    return (y / (voices * 1.2)).astype(np.float32)

def choir(f, d, vowel='a', atk=1.2, rel=1.5):
    n = int(d * SR); t = np.arange(n) / SR
    fv = f * (1 + 0.004 * sm(0.4, 1.5, t) * np.sin(2 * math.pi * 5.4 * t + rng.rand() * 6))
    ph = 2 * math.pi * np.cumsum(fv) / SR
    src = np.zeros(n, np.float32)
    for k in range(1, 24):
        src += (1.0 / k ** 0.8) * np.sin(k * ph + 1.3 * k).astype(np.float32)
    src += 0.25 * bp(noise(d), 800, 3500)
    forms = {'a': [(800, 9), (1200, 10), (2800, 12)], 'o': [(450, 8), (800, 9), (2830, 12)], 'u': [(350, 7), (700, 8), (2700, 12)]}[vowel]
    y = np.zeros(n, np.float32)
    for fc, q in forms:
        b_, a_ = signal.iirpeak(fc / (SR / 2), q); y += signal.lfilter(b_, a_, src).astype(np.float32) * (1.0 if fc < 1500 else 0.6)
    env = np.minimum(1, t / atk) ** 1.5 * np.clip((d - t) / rel, 0, 1) ** 1.3
    return (y * env * 0.5).astype(np.float32)

def drone(f, d, cutoff=420):
    n = int(d * SR); t = np.arange(n) / SR
    ph = 2 * math.pi * np.cumsum(f * (1 + 0.0025 * np.sin(2 * math.pi * 4.6 * t))) / SR
    y = np.zeros(n, np.float32)
    for k in range(1, 12): y += (1.0 / k) * np.sin(k * ph).astype(np.float32)
    env = np.minimum(1, t / 3.5) * np.clip((d - t) / 2.5, 0, 1)
    return (lp(y, cutoff, 3) * env * 0.5).astype(np.float32)

# --- percussion
def doum(vel=1.0):
    t = tt(0.55)
    f = 70 + 80 * np.exp(-t * 28)
    body = np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-t * 8)
    th = lp(noise(0.55), 400) * np.exp(-t * 60) * 0.5
    return ((body + th) * vel).astype(np.float32)
def tek(vel=1.0):
    t = tt(0.16)
    n_ = bp(noise(0.16), 1800, 5600) * np.exp(-t * 45)
    ring = np.sin(2 * math.pi * 410 * t) * np.exp(-t * 40) * 0.25
    return ((n_ * 0.9 + ring) * vel).astype(np.float32)
def ka(vel=1.0):
    t = tt(0.1)
    return (bp(noise(0.1), 2500, 7000) * np.exp(-t * 70) * 0.7 * vel).astype(np.float32)
def riq(vel=1.0):
    t = tt(0.22)
    n_ = hp(noise(0.22), 5500) * np.exp(-t * 28)
    ring = sum(np.sin(2 * math.pi * fq * t) * np.exp(-t * 25) for fq in (4900, 6300, 7700)) * 0.12
    return ((n_ * 0.55 + ring) * vel).astype(np.float32)
def taiko(vel=1.0, d=2.2):
    t = tt(d)
    f = 48 + 60 * np.exp(-t * 14)
    y = np.sin(2 * math.pi * np.cumsum(f) / SR) * np.exp(-t * 2.0)
    th = lp(noise(d), 260) * np.exp(-t * 14) * 0.9
    sk = bp(noise(d), 900, 3500) * np.exp(-t * 30) * 0.25
    return (np.tanh(1.6 * (y + th + sk)) * vel).astype(np.float32)
def crash(d=3.6, vel=1.0):
    t = tt(d)
    n_ = hp(noise(d), 2800) * np.exp(-t * 1.3)
    return (n_ * 0.5 * vel).astype(np.float32)
def revswell(d, vel=1.0):
    t = tt(d)
    n_ = hp(noise(d), 2200) * (t / d) ** 2.4
    tone = (np.sin(2 * math.pi * np.cumsum(180 * (4200 / 180) ** (t / d)) / SR)) * (t / d) ** 3 * 0.18
    return ((n_ * 0.5 + tone) * vel).astype(np.float32)
def whoosh(d=1.5, vel=1.0):
    t = tt(d)
    n_ = noise(d)
    out = np.zeros_like(n_)
    # sweeping band: crossfade of 3 bands
    for (f1, f2, c) in ((250, 900, 0.25), (800, 3000, 0.5), (2500, 9000, 0.75)):
        out += bp(n_, f1, f2) * np.exp(-((t / d - c) / 0.18) ** 2)
    return (out * 0.8 * vel * np.sin(math.pi * np.clip(t / d, 0, 1)) ** 0.7).astype(np.float32)
def sparkle(vel=1.0):
    f = rng.choice([F('D6'), F('A6'), F('F#6'), F('D7'), F('Bb6')])
    return qanun(f, 2.0, 0.5 * vel)

# ------------------------------------------------------------------ musical material
THEME_A = [('F#4', 1.5), ('G4', .5), ('A4', 2), ('Bb4', 1), ('A4', 1), ('G4', 1), ('F#4', 1), ('Eb4', 1.5), ('F#4', .5), ('Eb4', 1), ('D4', 1), ('D4', 4)]
THEME_B = [('A4', 1.5), ('Bb4', .5), ('C5', 2), ('D5', 1), ('C5', 1), ('Bb4', 1), ('A4', 1), ('G4', 1), ('F#4', 1), ('Eb4', 1), ('F#4', 1), ('D4', 4)]
CHORDS_A = ['D', 'D', 'Eb', 'D']
CHORDS_B = ['Gm', 'D', 'Eb', 'D']
VOIC = {'D': ['D3', 'A3', 'D4', 'F#4'], 'Eb': ['Eb3', 'Bb3', 'Eb4', 'G4'], 'Gm': ['G3', 'Bb3', 'D4', 'G4'], 'A': ['A2', 'E3', 'A3', 'C#4']}
ROOT = {'D': 'D2', 'Eb': 'Eb2', 'Gm': 'G2', 'A': 'A1'}

def play_theme(t0, notes, fn, octave=0, vel=1.0, scale=1.0, **kw):
    t = t0
    for nm, db in notes:
        f = F(nm) * (2 ** octave)
        d = db * BEAT * scale
        fn(t, f, d, vel, **kw)
        t += d
    return t

def n_oud(t, f, d, vel, send=0.35, pan=-0.2):
    put(oud(f, max(1.2, d * 1.3 + 0.8), 0.55 * vel), t, 1.0, send, 0.0, pan)
def n_qanun(t, f, d, vel, send=0.45, pan=0.25):
    put(qanun(f, max(1.5, d * 1.2 + 1.0), 0.5 * vel), t, 1.0, send, 0.0, pan)
def n_ney(t, f, d, vel, send=0.5, pan=0.1):
    put(ney(f, d * 0.98 + 0.12, 0.5 * vel), t, 0.9, send, 0.0, pan)
def n_str(t, f, d, vel, send=0.5, pan=0.0, atk=0.35):
    put(saw_stack(f, d + 0.9, atk=atk, rel=0.8) * 0.36 * vel, t, 0.8, send, 0.0, pan)
def n_cello(t, f, d, vel, send=0.4):
    put(saw_stack(f, d + 0.7, voices=3, det=0.004, harm=10, atk=0.25, rel=0.6, cutoff=1500) * 0.55 * vel, t, 0.85, send, 0.0, -0.1)

def chord_strings(t0, name, d, vel=1.0, atk=1.2, oct_=0):
    for i, nm in enumerate(VOIC[name]):
        put(saw_stack(F(nm) * 2 ** oct_, d + 1.2, voices=4, atk=atk, rel=1.1, cutoff=2600) * 0.32 * vel, t0, 0.55, 0.9, 0.0, -0.5 + i * 0.33)
def bass_note(t0, name, d, vel=1.0):
    put(oud(F(ROOT[name]), min(d + 0.6, 3.0), 0.9 * vel), t0, 1.0, 0.18, 0.0, 0.0)
    put(drone(F(ROOT[name]), d + 0.8, 300) * 0.6 * vel, t0, 0.8, 0.15, 0.0, 0.0)

def groove(t0, t1, level=1.0, riq_on=True, doum_only=False):
    """maqsum on the 8th-note grid: D - T T D - T -"""
    step = BEAT / 2
    k = 0; t = t0
    pat = [('D', 1.0), None, ('T', 0.8), ('T', 0.5), ('D', 0.9), None, ('T', 0.75), None]
    while t < t1 - 1e-6:
        p = pat[k % 8]
        if p:
            if p[0] == 'D': put(doum(0.75 * p[1] * level), t, 1.0, 0.0, 0.12, -0.1)
            elif not doum_only: put(tek(0.42 * p[1] * level), t, 0.9, 0.0, 0.25, 0.15)
        if riq_on and not doum_only:
            put(riq((0.16 if k % 2 == 0 else 0.10) * level), t + (0.0 if k % 2 == 0 else 0.0), 0.8, 0.0, 0.3, 0.35 if k % 2 else -0.2)
        t += step; k += 1

def roll(t0, t1, v0=0.1, v1=0.7):
    t = t0; i = 0; n_ = int((t1 - t0) / 0.07)
    while t < t1:
        u = (t - t0) / (t1 - t0); gap = 0.13 - 0.085 * u
        put(tek(v0 + (v1 - v0) * u), t, 0.9, 0.0, 0.3, 0.3 * math.sin(i)); t += gap; i += 1

def hit(t0, size=1.0, rev=0.9):
    put(revswell(rev, 0.8 * size), t0 - rev, 0.9, 0.5, 0.0, 0)
    put(taiko(0.95 * size), t0, 1.0, 0.25, 0.0, 0)
    put(taiko(0.5 * size, 2.6), t0 + 0.012, 0.8, 0.3, 0.0, 0.2)
    put(crash(3.8, 0.7 * size), t0, 0.7, 0.5, 0.0, 0)
    put(np.sin(2 * math.pi * 36 * tt(3.0)).astype(np.float32) * np.exp(-tt(3.0) * 1.1) * 0.55 * size, t0, 1.0, 0.0, 0.0, 0)

def arp(t0, t1, chord, vel=1.0, rate=0.5, pat=(0, 1, 2, 3, 2, 1, 3, 2), oct_=1, send=0.45):
    notes = [F(n) * 2 ** oct_ for n in VOIC[chord]]
    t = t0; k = 0
    while t < t1 - 1e-6:
        f = notes[pat[k % len(pat)] % 4]
        pan = 0.55 * math.sin(k * 0.9)
        put(qanun(f, 2.0, 0.34 * vel * (0.7 + 0.3 * ((k % 4) == 0))), t, 1.0, send, 0.0, pan)
        t += BEAT * rate / 2; k += 1

def bars(t0, t1, seq):
    """yield (bar_start, chord) from t0 to t1 cycling through seq, one chord per bar"""
    out = []; t = t0; i = 0
    while t < t1 - 1e-6:
        out.append((t, seq[i % len(seq)])); t += BAR; i += 1
    return out

# ================================================================== ARRANGEMENT
# ---- S1  0-15 : awakening (free time) ------------------------------------------------
put(drone(F('D2'), 17.0, 380) * 0.42, 0.0, 0.9, 0.5, 0, 0)
put(drone(F('A1'), 14.0, 300) * 0.22, 2.0, 0.9, 0.4, 0, 0)
for (t, nm, d, v) in [(3.0, 'A4', 2.7, 0.8), (5.9, 'Bb4', 0.7, 0.8), (6.6, 'A4', 0.7, 0.7), (7.3, 'G4', 0.9, 0.75), (8.2, 'F#4', 2.2, 0.85),
                      (10.7, 'Eb4', 1.2, 0.8), (11.9, 'F#4', 0.6, 0.7), (12.5, 'Eb4', 0.8, 0.7), (13.3, 'D4', 1.9, 0.85)]:
    n_ney(t, F(nm), d, v, send=0.8)
for t in (5.0, 7.0, 9.0, 10.6, 11.8, 12.8, 13.5):                     # distant heartbeat
    put(doum(0.35 + 0.35 * sm(5, 13.5, t)), t, 0.8, 0.5, 0.0, 0)
    put(doum(0.2 + 0.25 * sm(5, 13.5, t)), t + 0.27, 0.7, 0.5, 0.0, 0)
for t, nm in [(4.2, 'D6'), (6.6, 'A6'), (9.4, 'F#6'), (11.0, 'D7'), (12.4, 'A6')]:
    put(qanun(F(nm), 3.0, 0.22), t, 0.9, 0.9, 0.0, 0.4 * math.sin(t))
chord_strings(7.0, 'D', 8.0, 0.4, atk=4.5)
put(revswell(3.4, 1.0), 11.6, 0.9, 0.5, 0, 0)
roll(12.2, 14.6, 0.08, 0.5)
hit(15.0, 1.0, rev=0.9)

# ---- S2  15-30 : the digital world ---------------------------------------------------------
for (tb, ch) in bars(15.0, 30.0, ['D', 'D', 'Eb', 'D', 'Gm', 'D']):
    chord_strings(tb, ch, BAR, 0.62 + 0.2 * sm(15, 30, tb), atk=0.9)
    bass_note(tb, ch, BAR, 0.8)
    arp(tb, tb + BAR, ch, 0.45 + 0.6 * sm(15, 30, tb), rate=0.5, send=0.5)
play_theme(17.5, THEME_A, n_qanun, 0, 0.9)
play_theme(17.5, THEME_A, n_oud, -1, 0.65)
for t in np.arange(20.0, 30.0, BEAT * 2):
    put(doum(0.5 * (0.5 + 0.5 * sm(20, 30, t))), t, 1.0, 0.0, 0.1, 0)
for t in np.arange(22.5, 29.5, BEAT):
    put(ka(0.35), t + BEAT / 2, 0.8, 0.0, 0.2, 0.3)
put(revswell(3.5, 0.9), 26.5, 0.9, 0.5, 0, 0); roll(27.3, 29.9, 0.1, 0.6)
hit(30.0, 0.85, rev=0.8)

# ---- S3  30-52 : the tree experience ---------------------------------------------------------
for (tb, ch) in bars(30.0, 52.5, ['Gm', 'D', 'Eb', 'D', 'D', 'D', 'Eb', 'D']):
    chord_strings(tb, ch, BAR, 0.95, atk=0.5)
    bass_note(tb, ch, BAR, 1.0)
    arp(tb, tb + BAR, ch, 0.65, rate=0.5, pat=(0, 2, 1, 3, 2, 1, 3, 2), send=0.45)
groove(30.0, 52.0, 1.0, riq_on=True)
play_theme(30.0, THEME_B, n_str, 0, 0.9, send=0.55)
play_theme(30.0, THEME_B, n_ney, 0, 0.7, send=0.6)
play_theme(40.0, THEME_A, n_qanun, 1, 0.85)
play_theme(40.0, THEME_A, n_ney, 0, 0.85, send=0.6)
play_theme(40.0, THEME_A, n_str, -1, 0.55, send=0.5)
put(revswell(1.4, 0.7), 50.6, 0.8, 0.5, 0, 0)
hit(52.0, 0.6, rev=0.7)

# ---- S4  52-70 : personal profiles (warm, intimate) ----------------------------------------
for (tb, ch) in bars(52.5, 70.0, ['D', 'D', 'Eb', 'D', 'Gm', 'D', 'Eb', 'D']):
    chord_strings(tb, ch, BAR, 0.75, atk=1.0)
    bass_note(tb, ch, BAR, 0.8)
    arp(tb, tb + BAR, ch, 0.38, rate=1.0, pat=(0, 1, 2, 3), send=0.55, oct_=2)
groove(52.0, 70.0, 0.62, riq_on=False)
play_theme(52.5, THEME_A, n_cello, -1, 0.9)
play_theme(52.5, THEME_A, n_oud, 0, 0.7)
play_theme(62.5, THEME_B, n_str, 0, 0.8, send=0.6)
play_theme(62.5, THEME_B, n_ney, 0, 0.55, send=0.65)
hit(70.0, 0.6, rev=0.7)

# ---- S5  70-98 : exploring the platform (rising energy) ------------------------------------
for (tb, ch) in bars(70.0, 97.5, ['D', 'Eb', 'D', 'Gm', 'D', 'Eb', 'D', 'A']):
    e = 0.7 + 0.5 * sm(70, 96, tb)
    chord_strings(tb, ch, BAR, e, atk=0.4)
    bass_note(tb, ch, BAR, e)
    arp(tb, tb + BAR, ch, 0.5 + 0.5 * sm(70, 96, tb), rate=0.5, pat=(0, 1, 2, 3, 2, 3, 1, 2), send=0.45)
groove(70.0, 97.5, 0.9 + 0.2 * 0, riq_on=True)
play_theme(72.5, THEME_A, n_qanun, 1, 0.9)
play_theme(72.5, THEME_A, n_str, 0, 0.85, send=0.6)
play_theme(72.5, THEME_A, n_ney, 1, 0.55, send=0.6)
play_theme(82.5, THEME_B, n_str, 0, 1.0, send=0.6)
play_theme(82.5, THEME_B, n_ney, 1, 0.7, send=0.6)
play_theme(82.5, THEME_B, n_qanun, 1, 0.8)
for t in np.arange(90.0, 94.0, BEAT):
    put(taiko(0.35 + 0.25 * sm(90, 94, t), 1.0), t, 1.0, 0.1, 0, 0)
put(revswell(4.0, 1.0), 93.5, 0.9, 0.5, 0, 0); roll(94.0, 97.6, 0.15, 0.85)
hit(98.0, 0.7, rev=0.45)

# ---- S6  98-113 : in your hand (intimate, oud solo) -----------------------------------------
chord_strings(98.0, 'D', 8.0, 0.35, atk=3.0)
chord_strings(106.0, 'Eb', 3.0, 0.3, atk=1.5)
chord_strings(109.0, 'D', 5.0, 0.35, atk=1.5)
put(drone(F('D2'), 15.5, 360) * 0.8, 98.0, 0.9, 0.5, 0, 0)
play_theme(100.0, THEME_A, n_oud, 0, 1.0, send=0.5)
play_theme(100.0, THEME_A, n_qanun, 1, 0.4, send=0.6)
for t in np.arange(100.0, 112.0, BEAT * 2):
    put(doum(0.28), t, 0.9, 0.5, 0.1, 0)
for t, nm in [(103.5, 'A6'), (106.5, 'F#6'), (109.0, 'D7'), (111.0, 'A6')]:
    put(qanun(F(nm), 3.0, 0.2), t, 0.9, 0.9, 0.0, 0.4 * math.sin(t))
put(revswell(2.2, 0.7), 110.8, 0.9, 0.5, 0, 0)
hit(113.0, 0.5, rev=0.5)

# ---- S7  113-125 : emotional connection (strings + choir) ------------------------------------
for (tb, ch) in bars(112.5, 125.0, ['Gm', 'D', 'Eb', 'D', 'D']):
    chord_strings(tb, ch, BAR, 1.0, atk=0.9)
    bass_note(tb, ch, BAR, 0.9)
for (tb, ch) in bars(112.5, 125.0, ['Gm', 'D', 'Eb', 'D', 'D']):
    for i, nm in enumerate(VOIC[ch][:3]):
        put(choir(F(nm) * (1 if i < 2 else 1), BAR + 1.2, 'a' if (int(tb / BAR) % 2 == 0) else 'o') * 0.7, tb, 0.5, 0.9, 0, -0.4 + 0.4 * i)
play_theme(112.5, THEME_B, n_str, 1, 1.0, send=0.65)
play_theme(112.5, THEME_B, n_ney, 1, 0.55, send=0.7)
for t in np.arange(113.0, 121.0, BEAT * 2):
    put(doum(0.32 + 0.25 * sm(113, 121, t)), t, 0.9, 0.4, 0.1, 0)
put(revswell(3.8, 1.0), 121.2, 0.9, 0.5, 0, 0); roll(122.0, 124.9, 0.1, 0.8)
hit(125.0, 0.55, rev=0.5)

# ---- S8  125-135 : finale ------------------------------------------------------------------------
for k, t in enumerate(np.arange(125.2, 128.0, 0.5 - 0.0)):
    put(taiko(0.4 + 0.08 * k, 1.2), t, 1.0, 0.1, 0, 0)
arp(125.0, 128.6, 'Gm', 0.7, rate=0.25, pat=(0, 1, 2, 3, 2, 1, 3, 2), oct_=2, send=0.5)
chord_strings(125.0, 'Gm', 3.8, 0.9, atk=1.4)
chord_strings(126.9, 'A', 2.0, 0.9, atk=0.6)
put(revswell(3.0, 1.1), 125.8, 0.9, 0.5, 0, 0); roll(126.3, 128.7, 0.2, 0.9)
hit(128.0, 0.7, rev=0.4)                       # wave of light
hit(128.8, 1.35, rev=0.35)                     # logo reveal
for i, nm in enumerate(['D3', 'A3', 'D4', 'F#4', 'A4']):
    put(saw_stack(F(nm), 8.0, voices=5, atk=0.15, rel=2.2, cutoff=3400) * 0.36, 128.8, 0.6, 0.9, 0, -0.6 + i * 0.3)
    put(choir(F(nm) * (1 if i < 4 else 1), 7.5, 'a', atk=0.5, rel=2.2) * 0.8, 128.8, 0.5, 0.9, 0, -0.5 + i * 0.25)
put(drone(F('D1') * 1.0, 8.0, 200) * 1.1, 128.8, 0.9, 0.3, 0, 0)
for i, nm in enumerate(['D5', 'A5', 'F#5', 'D6', 'A6', 'D7', 'F#6', 'A6']):
    put(qanun(F(nm), 3.5, 0.35), 128.85 + i * 0.09, 1.0, 0.8, 0.0, -0.6 + i * 0.17)
FIN = [('F#5', 1.5), ('G5', .5), ('A5', 2), ('Bb5', 1), ('A5', 1), ('G5', 1), ('F#5', 1), ('Eb5', 2), ('D5', 6)]
play_theme(129.0, FIN, n_str, 0, 0.9, scale=0.78, send=0.7)
play_theme(129.0, FIN, n_ney, 0, 0.6, scale=0.78, send=0.7)
play_theme(129.0, FIN, n_qanun, 0, 0.6, scale=0.78)
for t, nm in [(131.2, 'D6'), (131.6, 'F#6'), (132.0, 'A6'), (132.5, 'D7'), (133.0, 'A6')]:
    put(qanun(F(nm), 3.0, 0.22), t, 0.9, 0.9, 0.0, 0.4 * math.sin(t * 3))
put(whoosh(2.4, 0.9), 127.9, 0.7, 0.6, 0, 0)

# ================================================================== REVERBS + MIX
def make_ir(d, seed, rts, pre=0.022):
    r = np.random.RandomState(seed)
    n = int(d * SR); t = np.arange(n) / SR
    bands = [(60, 250, rts[0]), (250, 1200, rts[1]), (1200, 4000, rts[2]), (4000, 12000, rts[3])]
    ir = np.zeros(n, np.float32)
    for (f1, f2, rt) in bands:
        x = r.randn(n).astype(np.float32)
        x = bp(x, f1, f2, 2)
        ir += x * np.exp(-t * 6.9 / rt) * (1.0 / math.sqrt(max(1, (f2 - f1) / 400)))
    # early reflections
    for dly, g in ((0.011, .5), (0.019, .42), (0.029, .35), (0.041, .3), (0.057, .22), (0.071, .18)):
        i = int((pre + dly) * SR)
        if i < n: ir[i] += g * r.choice([-1, 1]) * 3
    ir[:int(pre * SR)] = 0
    ir /= np.sqrt(np.sum(ir ** 2))
    return ir

def convbus(bus, d, rts, seeds):
    irL = make_ir(d, seeds[0], rts); irR = make_ir(d, seeds[1], rts)
    wl = signal.fftconvolve(bus.L, irL)[:N].astype(np.float32)
    wr = signal.fftconvolve(bus.R, irR)[:N].astype(np.float32)
    return wl, wr
lwl, lwr = convbus(LONG, 5.0, (4.5, 3.8, 2.8, 1.4), (5, 6))
swl, swr = convbus(SHORT, 1.1, (0.9, 0.8, 0.6, 0.35), (7, 8))
outL = DRY.L + 0.62 * lwl + 0.5 * swl
outR = DRY.R + 0.62 * lwr + 0.5 * swr
tm = np.arange(N) / SR
mf = sm(0, 1.0, tm) * (1 - sm(133.6, 135.0, tm))
outL *= mf; outR *= mf
outL = hp(outL, 28, 1); outR = hp(outR, 28, 1)
# gentle bus compression: slow RMS-follower gain
def comp(x, thr=0.22, ratio=2.2, atk=0.02, rel=0.35):
    env = np.abs(x)
    a_ = math.exp(-1 / (atk * SR)); r_ = math.exp(-1 / (rel * SR))
    # fast vectorised smoothing via lfilter (attack/release approximated by one-pole on rectified signal)
    sm_ = signal.lfilter([1 - r_], [1, -r_], env)
    g = np.where(sm_ > thr, (thr + (sm_ - thr) / ratio) / (sm_ + 1e-9), 1.0)
    g = signal.lfilter([1 - a_], [1, -a_], g)
    return (x * g).astype(np.float32)
mono = 0.5 * (outL + outR)
pk = max(np.abs(outL).max(), np.abs(outR).max())
outL /= pk; outR /= pk
outL = comp(outL); outR = comp(outR)
pk = max(np.abs(outL).max(), np.abs(outR).max())
outL /= pk; outR /= pk
outL = np.tanh(1.35 * outL) / np.tanh(1.35); outR = np.tanh(1.35 * outR) / np.tanh(1.35)
outL *= 0.74; outR *= 0.74
st = np.stack([outL, outR], 1)
pcm = (np.clip(st, -1, 1) * 32767).astype(np.int16)
out = sys.argv[1] if len(sys.argv) > 1 else '/tmp/vid/music2.wav'
with wave.open(out, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('ok', out, 'peak', float(np.abs(st).max()), 'rms', float(np.sqrt((st ** 2).mean())))
