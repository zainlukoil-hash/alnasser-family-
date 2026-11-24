import sys,os; sys.path.insert(0,'/tmp/vid')
from boot import *
items=[int(x) for x in sys.argv[1].split(',')]
CSS="#nlv{display:none!important}"
with sync_playwright() as p:
    for k in items:
        b,pg,errs=boot(p,390,844,3)
        try:
            pg.add_style_tag(content=CSS)
            pg.evaluate("document.getElementById('bExplore').click()"); pg.wait_for_timeout(700)
            name=pg.evaluate("(function(k){var it=document.querySelectorAll('#menuB .item')[k];var n=it.textContent.trim().slice(0,24);it.click();return n})(%d)"%k)
            pg.wait_for_timeout(1800)
            sk=pg.evaluate("""(function(){var b=[].filter.call(document.querySelectorAll('button'),function(e){return /^\\s*تخط/.test(e.textContent)&&e.offsetParent!==null})[0];if(b){b.click();return 1}return 0})()""")
            pg.wait_for_timeout(2600 if k not in (4,16) else 5000)
            pg.screenshot(path='/tmp/vid/assets/m_%02d.png'%k)
            print(k,name,'skip' if sk else '',errs[:1],flush=True)
        except Exception as e:
            print(k,'FAIL',str(e)[:120],flush=True)
        b.close()
