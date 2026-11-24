import sys,os,json; sys.path.insert(0,'/tmp/vid')
os.environ.setdefault('PLAYWRIGHT_BROWSERS_PATH','/opt/pw-browsers')
from playwright.sync_api import sync_playwright
LABELS={'natural':'الشجرة الطبيعية','search':'البحث بالاسم','wall':'جدار الوجوه','stories':'قصص الناصر','events':'مناسبات العائلة','greet':'تهنئة العائلة','map':'الانتشار الجغرافي','galaxy':'مجرّة الناصر','sigil':'الوسم النسبي','card':'الملف الشخصي','details':'النسب والتفاصيل','fatiha':'اقرأ الفاتحة على روحه','tree':'الشجرة الحيّة','guide':'مرشد الأنساب','gp':'الأجداد','par':'الآباء','kid':'الأبناء','fut':'الأجيال القادمة'}
CSS="""
html,body{margin:0;padding:0;background:transparent!important}
.t{position:absolute;left:0;top:0;white-space:nowrap;font-family:'Tajawal',sans-serif}
"""
ITEMS={
 'sig':("<div class='t' id='x' style='font-family:Tajawal,sans-serif;font-weight:500;font-size:27px;letter-spacing:.08em;color:#fff;text-shadow:0 1px 8px rgba(0,0,0,.8);padding:6px 12px;direction:ltr'>By Zain Al-Rubaie</div>"),
 'title_en':("<div class='t' id='x' style='font-weight:800;font-size:92px;letter-spacing:.22em;padding:20px 40px;direction:ltr;background:linear-gradient(180deg,#FFF1C9 0%,#F5C451 48%,#B9822A 100%);-webkit-background-clip:text;color:transparent;filter:drop-shadow(0 4px 22px rgba(245,196,81,.35))'>NASSER FAMILY</div>"),
 'tag_en':("<div class='t' id='x' style='font-weight:500;font-size:37px;letter-spacing:.07em;padding:10px 30px;direction:ltr;color:#F7E8C4;text-shadow:0 2px 12px rgba(0,0,0,.8)'>Connected by Roots. United Across Generations.</div>"),
 'title_ar':("<div class='t' id='x' style='font-family:AmiriQuran,Amiri,serif;font-weight:400;font-size:170px;line-height:1.35;padding:44px 80px;direction:rtl;background:linear-gradient(180deg,#FFF1C9 0%,#F5C451 50%,#B9822A 100%);-webkit-background-clip:text;color:transparent;filter:drop-shadow(0 0 1.6px rgba(250,205,95,.95)) drop-shadow(0 0 1.6px rgba(250,205,95,.9)) drop-shadow(0 5px 26px rgba(245,196,81,.38))'>عائلة الناصر</div>"),
 'sub_ar':("<div class='t' id='x' style='font-family:AmiriQuran,Amiri,serif;font-weight:400;font-size:56px;-webkit-text-stroke:1px #F7E8C4;padding:10px 30px;direction:rtl;color:#F7E8C4;letter-spacing:.02em;text-shadow:0 2px 12px rgba(0,0,0,.8)'>منصّة الأجيال الرقمية</div>"),
 'credit_ar':("<div class='t' id='x' style='font-family:AmiriQuran,Amiri,serif;font-weight:400;font-size:52px;line-height:1.25;padding:6px 30px 26px;direction:rtl;color:#F7E8C4;-webkit-text-stroke:.8px #F7E8C4;text-shadow:0 2px 12px rgba(0,0,0,.85)'>إعداد: زين الربيعي</div>"),
 'slogan_ar':("<div class='t' id='x' style='font-family:AmiriQuran,Amiri,serif;font-weight:400;font-size:58px;-webkit-text-stroke:1px #F7E8C4;padding:10px 30px;direction:rtl;color:#F7E8C4;text-shadow:0 2px 12px rgba(0,0,0,.85)'>إرثٌ واحد. أجيالٌ لا تنتهي.</div>"),
}
for k,v in LABELS.items():
    ITEMS['lab_'+k]=("<div class='t' id='x' style='font-family:AmiriQuran,Amiri,serif;font-weight:400;font-size:60px;line-height:1.2;-webkit-text-stroke:1.2px #FFE9B0;color:#FFE9B0;padding:0px 48px 40px;border-radius:60px;background:rgba(10,14,26,.72);border:3px solid rgba(245,196,81,.75);box-shadow:0 6px 30px rgba(0,0,0,.5);direction:rtl'>%s</div>"%v)
with sync_playwright() as p:
    b=p.chromium.launch(args=['--no-sandbox'])
    pg=b.new_page(viewport={'width':1400,'height':400})
    pg.goto('file:///tmp/vid/camout/nasser_test.html'); pg.wait_for_timeout(2500)
    pg.evaluate("async()=>{await document.fonts.load('400 60px AmiriQuran');document.fonts.load('800 60px Tajawal');await document.fonts.load('500 30px Tajawal');await document.fonts.ready}")
    pg.evaluate("(function(css){document.body.innerHTML='';document.body.removeAttribute('class');document.documentElement.removeAttribute('class');document.body.setAttribute('style','background:transparent');var s=document.createElement('style');s.textContent=css;document.head.appendChild(s)})(%s)"%json.dumps(CSS))
    ONLY=sys.argv[1:]
    for k,h in ITEMS.items():
        if ONLY and k not in ONLY: continue
        pg.evaluate("(function(h){document.body.innerHTML=h})(%s)"%json.dumps(h)); pg.wait_for_timeout(150)
        r=pg.evaluate("(function(){var r=document.getElementById('x').getBoundingClientRect();return [r.width,r.height]})()")
        w,hh=int(r[0])+4,int(r[1])+4
        pg.set_viewport_size({'width':max(w,10),'height':max(hh,10)})
        pg.screenshot(path='/tmp/vid/%s.png'%('sig' if k=='sig' else 'caps/'+k),omit_background=True,clip={'x':0,'y':0,'width':w,'height':hh})
        print(k,w,hh)
    b.close()
