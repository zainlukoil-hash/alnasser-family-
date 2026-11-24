import sys,os,json; sys.path.insert(0,'/tmp/vid')
os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH','/opt/pw-browsers')
from playwright.sync_api import sync_playwright
CAPS={
 'c1a':("قبل سنينٍ طويلة… بدأت الحكاية من جذرٍ واحد.",64),
 'c1b':("جذرٌ كبر، وتفرّع، وصار عائلة.",62),
 'c1c':("عائلة الناصر",120),
 'c2a':("واليوم… صارت الحكاية بين يديك.",64),
 'c2b':("كلّ العائلة في مكانٍ واحد، بلمسة.",54),
 'c3a':("اكتشف جذورك.",66),
 'c3b':("تنقّل بين الأجيال، وتتبّع كلّ فرع، واعرف من أين جاء كلّ اسم.",56),
 'c3c':("لكلّ اسمٍ حكاية… ولكلّ فرعٍ مكان.",62),
 'c4a':("لكلّ شخصٍ ملفّه.",70),
 'c4b':("افتح ملفّ أيّ فردٍ من العائلة: صورته، ونسبه، وأبناؤه… كلّها بلمسة.",52),
 'c5a':("وهي أكثر من شجرة.",66),
 'c5b':("ابحث عن أيّ اسم.",66),
 'c5c':("شاهد الوجوه، واقرأ القصص.",60),
 'c5d':("تابع مناسبات العائلة، واسأل مرشد الأنساب.",54),
 'c5e':("وشاهد أين تنتشر العائلة، وكيف ترتبط أجيالها.",62),
 'c6a':("بسيطٌ في استخدامه.",66),
 'c6b':("وفي جيبك… أينما كنت.",60),
 'c7a':("العائلة ليست أسماءً فقط.",66),
 'c7b':("هي ذكرياتٌ نتشاركها… وإرثٌ نتركه لمن بعدنا.",56),
 'c8a':("من جذور الأمس… إلى أجيال الغد.",66),
 'c8b':("تختلف الأجيال، وتبقى الجذور واحدة.",62),
}
CSS="""
html,body{margin:0;padding:0;background:transparent!important}
#box{width:1080px;padding:0 90px;box-sizing:border-box;direction:rtl;text-align:center;font-family:'AmiriQuran','Amiri',serif;font-weight:400;line-height:1.62;position:absolute;top:20px;left:0}
#box span.w{display:inline-block;margin:0 .13em;white-space:nowrap}
"""
k_cur=None
def build(text,size,mode):
    ws=text.split(' ')
    col='#FFF4D8'
    shadow='0 3px 22px rgba(0,0,0,.85),0 0 3px rgba(0,0,0,.6)'
    op='1' if mode=='b' else '.28'
    size=int(size*(1.0 if k_cur=='c8b' else 1.2))
    return "<div id='box' style='font-size:%dpx;color:%s;text-shadow:%s;-webkit-text-stroke:1.6px %s;paint-order:stroke fill;opacity:%s'>%s</div>"%(size,col,shadow,col,op,''.join("<span class='w'>%s</span>"%w for w in ws))
with sync_playwright() as p:
    b=p.chromium.launch(args=['--no-sandbox'])
    pg=b.new_page(viewport={'width':1080,'height':520})
    pg.goto('file:///tmp/vid/camout/nasser_test.html'); pg.wait_for_timeout(2500)
    pg.evaluate("async()=>{await document.fonts.load('400 60px AmiriQuran');await document.fonts.ready}")
    pg.evaluate("(function(css){document.body.innerHTML='';document.body.removeAttribute('class');document.documentElement.removeAttribute('class');document.body.setAttribute('style','background:transparent');var s=document.createElement('style');s.textContent=css;document.head.appendChild(s)})(%s)"%json.dumps(CSS))
    meta={}
    ONLY=sys.argv[1:]
    for k,(txt,size) in CAPS.items():
        k_cur=k
        if ONLY and k not in ONLY: continue
        for mode in ('d','b'):
            pg.evaluate("(function(h){document.body.innerHTML=h})(%s)"%json.dumps(build(txt,size,mode)))
            pg.wait_for_timeout(120)
            r=pg.evaluate("""(function(){var bx=document.getElementById('box');var r=bx.getBoundingClientRect();return {h:r.height,w:[].map.call(bx.querySelectorAll('span.w'),function(s){var q=s.getBoundingClientRect();return [q.left,q.top,q.right,q.bottom]})}})()""")
            hh=int(r['h'])+60
            pg.set_viewport_size({'width':1080,'height':hh})
            pg.screenshot(path='/tmp/vid/caps/%s_%s.png'%(k,mode),omit_background=True,clip={'x':0,'y':0,'width':1080,'height':hh})
            if mode=='b': meta[k]={'h':hh,'words':r['w'],'text':txt,'size':size}
    if not ONLY: json.dump(meta,open('/tmp/vid/caps/meta.json','w'),ensure_ascii=False)
    print({k:(v['h'],len(v['words'])) for k,v in meta.items()})
    b.close()
