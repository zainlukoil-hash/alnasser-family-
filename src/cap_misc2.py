import sys,os; sys.path.insert(0,'/tmp/vid')
from boot import *
A='/tmp/vid/assets/'
def search(pg,txt):
    pg.evaluate("(function(){var q=document.getElementById('q');q.value='';q.dispatchEvent(new Event('input',{bubbles:true}))})()")
    pg.click('#q'); pg.keyboard.type(txt,delay=70); pg.wait_for_timeout(800)
def pick(pg,i):
    pg.evaluate("(function(i){document.querySelector('#sugg button.row[data-i=\"'+i+'\"]').click()})(%d)"%i); pg.wait_for_timeout(2600)
with sync_playwright() as p:
    b,pg,errs=boot(p,390,844,3)
    pg.add_style_tag(content="#nlv{display:none!important}")
    # gallery held
    search(pg,'فاض'); pick(pg,46)
    pg.evaluate("(function(){var a=document.querySelector('#card .cav');if(a)a.click()})()"); pg.wait_for_timeout(1600)
    box=pg.evaluate("(function(){var w=document.querySelector('#phB .phgw');if(!w)return null;var r=w.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]})()")
    print('gal box',box)
    if box:
        pg.mouse.move(box[0],box[1]); pg.mouse.down(); pg.wait_for_timeout(1500); pg.screenshot(path=A+'t_gallery_held.png'); pg.mouse.up(); pg.wait_for_timeout(500)
    pg.evaluate("(function(){var x=document.querySelector('#phB [data-close], #phB .x, #phB button');if(x)x.click()})()"); pg.wait_for_timeout(800)
    b.close()
    # muayyad / amir cards
    for name,txt,idx in (('muayyad','مؤيد',93),('amir','امير',51)):
        b,pg,errs=boot(p,390,844,3)
        pg.add_style_tag(content="#nlv{display:none!important}")
        search(pg,txt); pick(pg,idx); pg.screenshot(path=A+'t_card_%s.png'%name); print(name,errs[:1]); b.close()
    # wall: held reveal
    b,pg,errs=boot(p,390,844,3)
    pg.add_style_tag(content="#nlv{display:none!important}")
    pg.evaluate("document.getElementById('bExplore').click()"); pg.wait_for_timeout(1200)
    pg.screenshot(path=A+'t_home.png')
    pg.evaluate("""(function(){var b=[].filter.call(document.querySelectorAll('#menuB .nfh9-c'),function(e){return /جدار/.test(e.innerText)})[0];b.click()})()"""); pg.wait_for_timeout(1800)
    pg.evaluate("""(function(){var b=[].filter.call(document.querySelectorAll('button'),function(e){return /^\\s*تخط/.test(e.textContent)&&e.offsetParent!==null})[0];if(b)b.click()})()"""); pg.wait_for_timeout(2500)
    pg.screenshot(path=A+'t_wall.png')
    tb=pg.evaluate("(function(){var t=document.querySelector('.nfpic');if(!t)return null;var r=t.getBoundingClientRect();return [r.left+r.width/2,r.top+r.height/2]})()")
    print('tile',tb)
    if tb:
        pg.mouse.move(tb[0],tb[1]); pg.mouse.down(); pg.wait_for_timeout(1400); pg.screenshot(path=A+'t_wall_held.png'); pg.mouse.up()
    b.close()
    # map with khasib selected
    b,pg,errs=boot(p,390,844,3)
    pg.add_style_tag(content="#nlv{display:none!important}")
    pg.evaluate("document.getElementById('bExplore').click()"); pg.wait_for_timeout(800)
    pg.evaluate("(function(){var it=document.querySelectorAll('#menuB .item')[19];it.click()})()"); pg.wait_for_timeout(3000)
    pg.evaluate("(function(){var e=document.querySelector('#pmpins .m-pin[data-k=khasib]');e.dispatchEvent(new MouseEvent('click',{bubbles:true}))})()"); pg.wait_for_timeout(2200)
    pg.screenshot(path=A+'t_map.png'); print('ERR',errs[:2]); b.close()
