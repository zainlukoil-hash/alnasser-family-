import sys,os,json; sys.path.insert(0,'/tmp/vid')
from boot import *
with sync_playwright() as p:
    b,pg,errs=boot(p,390,693,2)
    r=pg.evaluate("""(function(){var c=__cam,D=c.D;var u=[1e9,1e9,-1e9,-1e9];D.forEach(function(d){var bb=d.bb;u[0]=Math.min(u[0],bb[0]);u[1]=Math.min(u[1],bb[1]);u[2]=Math.max(u[2],bb[2]);u[3]=Math.max(u[3],bb[3])});
      var m=document.querySelector('.nsmound').getBBox();
      var pl=[].filter.call(document.querySelectorAll('#tree text'),function(t){return /منصة عائلة/.test(t.textContent)})[0];var plb=pl?pl.getBBox():null;
      var lab=[].map.call(document.querySelectorAll('#tree text'),function(t){return t.textContent});
      return {fit:c.fit,B:c.B,union:u,mound:[m.x,m.y,m.width,m.height],plaque:plb?[plb.x,plb.y,plb.width,plb.height]:null,root:D[0].bb,g:[0,2,46,98,62,76,84,93].map(function(i){return [i,D[i].n,D[i].bb]})}})()""")
    print(json.dumps(r,ensure_ascii=False))
    json.dump(r,open('/tmp/vid/geo.json','w'),ensure_ascii=False)
    b.close()
