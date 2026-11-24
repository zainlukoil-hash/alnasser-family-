import sys; sys.path.insert(0,'/tmp/vid')
import film; film.NODIP=True
import scenes3 as S, numpy as np, cv2
TR={'scene4':('scene3',52.0,'ring',0.9,(540,880),False),'scene5':('scene4',70.0,'sweep',0.8,None,False),'scene6':('scene5',98.0,'push',0.9,(540,860),False),'scene7':('scene6',113.0,'sweep',0.8,None,True),'scene8':('scene7',125.0,'ring',0.9,(540,860),False)}
rows=[]
for nm,(pv,tb,mode,d,c,flip) in TR.items():
    A=getattr(S,pv)(tb-1/30,0).copy(); tiles=[]
    for u in (0.12,0.3,0.5,0.7,0.9):
        t=tb+u*d; B=getattr(S,nm)(t,int(t*30))
        f=S.wipe(A,B,u,mode,*(c if c else (None,None)),flip=flip) if mode!='sweep' else S.wipe(A,B,u,'sweep',flip=flip)
        tiles.append(cv2.resize(S.to_u8(f),(216,384)))
    rows.append(np.hstack(tiles))
cv2.imwrite('/tmp/vid/shots/trans_sheet.jpg',np.vstack(rows[:3])); cv2.imwrite('/tmp/vid/shots/trans_sheet2.jpg',np.vstack(rows[3:]))
print('ok')
