import sys,os,json; sys.path.insert(0,'/tmp/vid')
from boot import *
A='/tmp/vid/assets/'
H=int(sys.argv[1])
with sync_playwright() as p:
    b,pg,errs=boot(p,390,H,3)
    pg.add_style_tag(content="#nlv{display:none!important}")
    pg.evaluate("document.getElementById('bExplore').click()"); pg.wait_for_timeout(1800)
    info=pg.evaluate("""(function(){var m=document.getElementById('menuB');var o=[];var e=m;for(var k=0;k<5&&e;k++){o.push([e.id,e.className.slice(0,20),e.scrollHeight,e.clientHeight]);e=e.parentElement}return o})()""")
    print(info)
    pg.screenshot(path=A+'t_home_tall.png'); print('ok',errs[:2])
    b.close()
