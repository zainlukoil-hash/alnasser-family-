import sys,time; sys.path.insert(0,'/tmp/vid')
import scenes3 as S
name=sys.argv[1]; ts=[float(x) for x in sys.argv[2].split(',')]
fn=getattr(S,name)
tiles=[]
for t in ts:
    n=int(round(t*S.FPS)); t0=time.time()
    f=fn(t,n); f=S.signature(f); f=S.grain(f,n)
    u=S.to_u8(f); print('t=%.1f %.2fs'%(t,time.time()-t0))
    S.cv2.imwrite('/tmp/vid/shots/%s_%05.1f.jpg'%(name,t),u,[S.cv2.IMWRITE_JPEG_QUALITY,88]); tiles.append(S.cv2.resize(u,(270,480)))
S.cv2.imwrite('/tmp/vid/shots/%s_sheet.jpg'%name,S.np.hstack(tiles))
