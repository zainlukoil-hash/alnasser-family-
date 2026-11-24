import sys,os,json,math,time; sys.path.insert(0,'/tmp/vid')
from boot import *
FPS=30
def ease(u):
    u=max(0,min(1,u)); return u*u*u*(u*(6*u-15)+10)
def flight(s,e,rho=1.38):
    # s,e = (cx,cy,w); van Wijk & Nuij, same as the app
    r2=rho*rho; r4=r2*r2; dx=e[0]-s[0]; dy=e[1]-s[1]; d2=dx*dx+dy*dy; w0=s[2]; w1=e[2]
    if d2<1e-9:
        return lambda u:(s[0],s[1],w0*math.exp(math.log(w1/w0)*u))
    d1=math.sqrt(d2)
    b0=(w1*w1-w0*w0+r4*d2)/(2*w0*r2*d1); b1=(w1*w1-w0*w0-r4*d2)/(2*w1*r2*d1)
    q0=math.log(math.sqrt(b0*b0+1)-b0); q1=math.log(math.sqrt(b1*b1+1)-b1)
    S=(q1-q0)/rho
    if not S>1e-4: S=1e-4
    ch0=math.cosh(q0); sh0=math.sinh(q0)
    def at(u):
        k=u*S; uu=w0/(r2*d1)*(ch0*math.tanh(rho*k+q0)-sh0)
        return (s[0]+uu*dx, s[1]+uu*dy, w0*ch0/math.cosh(rho*k+q0))
    return at
def path(waypoints):
    """waypoints: list of (t, cx, cy, w); legs use flight() with ease; returns f(t)->(cx,cy,w)"""
    legs=[]
    for a,b in zip(waypoints[:-1],waypoints[1:]):
        legs.append((a[0],b[0],flight(a[1:],b[1:])))
    def f(t):
        if t<=waypoints[0][0]: return waypoints[0][1:]
        for t0,t1,fl in legs:
            if t<=t1: return fl(ease((t-t0)/(t1-t0)))
        return waypoints[-1][1:]
    return f
SEQ={
 's1': (15.0, path([(0,750,1330,430),(2.5,750,1290,520),(15,750,985,1560)])),
 's3': (22.0, path([(0,750,985,1560),(3.5,756,800,620),(5.5,756,800,600),(9.5,440,520,560),(11.5,440,520,540),(15,456,835,520),(16.5,456,835,500),(19.5,443,950,440),(22,750,985,1560)])),
 's8': (6.5, path([(0,750,985,1560),(6.5,750,900,1180)])),
}
if __name__=='__main__':
    name=sys.argv[1]; dur,f=SEQ[name]
    a=int(sys.argv[2]) if len(sys.argv)>2 else 0
    z=int(sys.argv[3]) if len(sys.argv)>3 else int(round(dur*FPS))
    out='/tmp/vid/seq/'+name
    os.makedirs(out,exist_ok=True)
    cams={}
    if os.path.exists(out+'/cam.json'): cams=json.load(open(out+'/cam.json'))
    with sync_playwright() as p:
        b,pg,errs=boot(p,390,693,1080/390)
        pg.add_style_tag(content="#app > *:not(#stage){display:none!important}")
        pg.wait_for_timeout(500)
        t0=time.time()
        for n in range(a,z):
            t=n/FPS; cx,cy,w=f(t); h=w*693/390
            vb=pg.evaluate("(function(v){__cam.setView({x:v[0]-v[2]/2,y:v[1]-v[3]/2,w:v[2],h:v[3]},true);var b=__cam.vb;return [b.x,b.y,b.w,b.h]})(%s)"%json.dumps([cx,cy,w,h]))
            cams[n]=vb
            pg.screenshot(path='%s/f%04d.jpg'%(out,n),type='jpeg',quality=92)
        json.dump(cams,open(out+'/cam.json','w'))
        print(name,a,z,'done in %.0fs'%(time.time()-t0),'errs',errs[:2])
        b.close()
