import sys, os, subprocess, time
sys.path.insert(0, '/tmp/vid')
import film
film.NODIP = True
import scenes3 as S
name, t0, t1 = sys.argv[1], float(sys.argv[2]), float(sys.argv[3])
OUTDIR = os.environ.get('OUTDIR', '/tmp/vid/out3')
os.makedirs(OUTDIR, exist_ok=True)
out = '%s/%s.mp4' % (OUTDIR, name)
if os.path.exists(out): print('exists', out); sys.exit(0)
tmp = '%s/%s.part.mp4' % (OUTDIR, name)
fn = getattr(S, name)
# transitions into this scene: (previous scene, boundary time, mode, duration, centre, flip)
TRANS = {'scene4': ('scene3', 52.0, 'ring', 0.9, (540, 880), False),
         'scene5': ('scene4', 70.0, 'sweep', 0.8, None, False),
         'scene6': ('scene5', 98.0, 'push', 0.9, (540, 860), False),
         'scene7': ('scene6', 113.0, 'sweep', 0.8, None, True),
         'scene8': ('scene7', 125.0, 'ring', 0.9, (540, 860), False)}
tr = TRANS.get(name)
A_last = None
n0, n1 = int(round(t0 * S.FPS)), int(round(t1 * S.FPS))
cmd = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', '%dx%d' % (S.W, S.H), '-r', str(S.FPS), '-i', '-',
       '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '17', '-pix_fmt', 'yuv420p', '-g', '60', '-threads', '1', '-an', '-movflags', '+faststart', tmp]
p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
st = time.time()
for n in range(n0, n1):
    t = n / S.FPS
    f = fn(t, n)
    if tr and t < tr[1] + tr[3]:
        if A_last is None:
            pv = getattr(S, tr[0]); tb = tr[1] - 1.0 / S.FPS
            A_last = pv(tb, int(round(tb * S.FPS))).copy()
        f = S.wipe(A_last, f, (t - tr[1]) / tr[3], tr[2], *(tr[4] if tr[4] else (None, None)), flip=tr[5]) if tr[2] != 'sweep' else S.wipe(A_last, f, (t - tr[1]) / tr[3], 'sweep', flip=tr[5])
    f = S.signature(f); f = S.grain(f, n)
    p.stdin.write(S.to_u8(f).tobytes())
    if (n - n0) % 60 == 0: print(name, n - n0, '/', n1 - n0, '%.0fs' % (time.time() - st), flush=True)
p.stdin.close(); rc = p.wait()
if rc == 0: os.rename(tmp, out); print('done', name, '%.0fs' % (time.time() - st))
else: print('ffmpeg failed', rc); sys.exit(1)
