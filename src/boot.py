import os, sys
os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH','/opt/pw-browsers')
from playwright.sync_api import sync_playwright
PAGE=os.environ.get('NPAGE','file:///tmp/vid/camout/nasser_test.html')
UA='Mozilla/5.0 (Linux; Android 13; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Mobile Safari/537.36'
def boot(p, w=390, h=844, dsf=2):
    b=p.chromium.launch(args=['--no-sandbox'])
    c=b.new_context(viewport={'width':w,'height':h},user_agent=UA,is_mobile=True,has_touch=True,device_scale_factor=dsf)
    pg=c.new_page(); errs=[]
    pg.on('pageerror',lambda e:errs.append('PE '+str(e)[:200]))
    pg.goto(PAGE); pg.wait_for_timeout(2000)
    loc=pg.get_by_text('تشغيل مباشر')
    for i in range(loc.count()):
        if loc.nth(i).is_visible(): loc.nth(i).click(timeout=4000); break
    pg.wait_for_timeout(3000)
    pg.evaluate("(function(){var g=document.getElementById('pickGo');if(g)g.click()})()"); pg.wait_for_timeout(4000)
    pg.evaluate("(function(){var x=document.getElementById('instc');if(x)x.remove();var c=document.getElementById('chooser');if(c)c.classList.remove('on')})()")
    pg.wait_for_timeout(800)
    return b,pg,errs
