import sys,os; sys.path.insert(0,'/tmp/vid')
from boot import *
A='/tmp/vid/assets/'
def search(pg,txt):
    pg.evaluate("(function(){var q=document.getElementById('q');q.value='';q.dispatchEvent(new Event('input',{bubbles:true}))})()")
    pg.click('#q'); pg.keyboard.type(txt,delay=70); pg.wait_for_timeout(900)
def pick(pg,i):
    pg.evaluate("(function(i){document.querySelector('#sugg button.row[data-i=\"'+i+'\"]').click()})(%d)"%i); pg.wait_for_timeout(2600)
with sync_playwright() as p:
    b,pg,errs=boot(p,390,844,3)
    pg.add_style_tag(content="#nlv{display:none!important}")
    pg.wait_for_timeout(500)
    search(pg,'الحاج ابراهيم'); pg.screenshot(path=A+'t_search.png')
    pick(pg,98); pg.screenshot(path=A+'t_card_fadhil.png')
    pg.evaluate("""(function(){var b=[].filter.call(document.querySelectorAll('#card button'),function(e){return /التفاصيل/.test(e.textContent)})[0];if(b)b.click()})()"""); pg.wait_for_timeout(1400)
    pg.screenshot(path=A+'t_card_details.png'); print('ERR1',errs[:2]); b.close()
    b,pg,errs=boot(p,390,844,3)
    pg.add_style_tag(content="#nlv{display:none!important}")
    search(pg,'نوري'); pick(pg,116); pg.screenshot(path=A+'t_card_amir.png'); print('ERR2',errs[:2]); b.close()
