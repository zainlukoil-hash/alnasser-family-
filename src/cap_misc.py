import sys,os; sys.path.insert(0,'/tmp/vid')
from boot import *
A='/tmp/vid/assets/'
def search(pg,txt,i=None):
    pg.evaluate("(function(){var q=document.getElementById('q');q.value='';q.dispatchEvent(new Event('input',{bubbles:true}))})()")
    pg.click('#q'); pg.keyboard.type(txt,delay=70); pg.wait_for_timeout(800)
def pick(pg,i):
    pg.evaluate("(function(i){document.querySelector('#sugg button.row[data-i=\"'+i+'\"]').click()})(%d)"%i); pg.wait_for_timeout(2600)
def closecard(pg):
    pg.evaluate("(function(){var x=document.querySelector('#card [data-close], #card .xbtn, #card .cx');if(x)x.click()})()"); pg.wait_for_timeout(700)
with sync_playwright() as p:
    b,pg,errs=boot(p,390,844,3)
    pg.add_style_tag(content="#nlv{display:none!important}")
    pg.wait_for_timeout(500)
    pg.screenshot(path=A+'t_tree.png')
    search(pg,'فاض'); pg.screenshot(path=A+'t_search.png')
    pick(pg,46); pg.screenshot(path=A+'t_card_fadhil.png')
    print('btns',pg.evaluate("[].map.call(document.querySelectorAll('#card button'),function(e){return (e.getAttribute('data-act')||e.id)+':'+e.textContent.trim().slice(0,12)})"))
    pg.evaluate("""(function(){var b=[].filter.call(document.querySelectorAll('#card button'),function(e){return /التفاصيل/.test(e.textContent)})[0];if(b)b.click()})()"""); pg.wait_for_timeout(1400)
    pg.screenshot(path=A+'t_card_details.png')
    pg.evaluate("(function(){var c=document.getElementById('cGrip');if(c)c.click()})()"); pg.wait_for_timeout(900)
    pg.evaluate("(function(){var a=document.querySelector('#card .cav');if(a)a.click()})()"); pg.wait_for_timeout(1600)
    pg.screenshot(path=A+'t_gallery.png')
    print('ERR',errs[:3]); b.close()
