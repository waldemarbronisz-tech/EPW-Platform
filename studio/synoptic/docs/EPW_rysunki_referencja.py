CY='#00CFCF'; K='#000000'
def sh(base, lt, dk): return dict(b=base, l=lt, d=dk)
GREY  = sh('#C0C0C0','#F0F0F0','#808080')
DGREY = sh('#909090','#C8C8C8','#585858')
GREEN = sh('#00B800','#50E850','#007000')
RED   = sh('#E00000','#FF7070','#900000')
BLUE  = sh('#2848D8','#6080FF','#182C90')
TAN   = sh('#C8A870','#E8D0A0','#907040')
YELL  = sh('#FFD800','#FFF080','#B08800')
DARK  = sh('#585C64','#8C9098','#303438')
CONC  = sh('#D0D0C8','#F0F0E8','#9C9C94')
GRASS = sh('#3C9430','#68C050','#28641C')
BRICK = sh('#B45838','#E08860','#7C3820')

class C:
    def __init__(s,w,h): s.w=w; s.h=h; s.o=[f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg"><rect width="{w}" height="{h}" fill="{CY}"/>']
    def out(s): return ''.join(s.o)+'</svg>'
    def rect(s,x,y,w,h,c,band=4,ow=2.5):
        s.o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{c["b"]}" stroke="{K}" stroke-width="{ow}"/>')
        if band:
            s.o.append(f'<rect x="{x+ow/2}" y="{y+ow/2}" width="{w-ow}" height="{band}" fill="{c["l"]}"/>')
            s.o.append(f'<rect x="{x+ow/2}" y="{y+h-band-ow/2}" width="{w-ow}" height="{band}" fill="{c["d"]}"/>')
    def vrect(s,x,y,w,h,c,band=4,ow=2.5):
        s.o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{c["b"]}" stroke="{K}" stroke-width="{ow}"/>')
        s.o.append(f'<rect x="{x+ow/2}" y="{y+ow/2}" width="{band}" height="{h-ow}" fill="{c["l"]}"/>')
        s.o.append(f'<rect x="{x+w-band-ow/2}" y="{y+ow/2}" width="{band}" height="{h-ow}" fill="{c["d"]}"/>')
    def circ(s,cx,cy,r,c,ow=2.5):
        s.o.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{c["b"]}" stroke="{K}" stroke-width="{ow}"/>')
        s.o.append(f'<path d="M{cx-r*0.72},{cy-r*0.5} A{r*0.88},{r*0.88} 0 0 1 {cx+r*0.1},{cy-r*0.86}" fill="none" stroke="{c["l"]}" stroke-width="{r*0.28}" stroke-linecap="round"/>')
        s.o.append(f'<path d="M{cx+r*0.62},{cy+r*0.5} A{r*0.85},{r*0.85} 0 0 1 {cx-r*0.2},{cy+r*0.85}" fill="none" stroke="{c["d"]}" stroke-width="{r*0.22}" stroke-linecap="round"/>')
    def poly(s,pts,c,ow=2.5,fill=None):
        d='M'+' L'.join(f'{x},{y}' for x,y in pts)+' Z'
        s.o.append(f'<path d="{d}" fill="{fill or c["b"]}" stroke="{K}" stroke-width="{ow}"/>')
    def line(s,x1,y1,x2,y2,col=K,w=2.5,cap='butt'):
        s.o.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="{w}" stroke-linecap="{cap}"/>')
    def txt(s,x,y,t,size=11,col=K,anch='middle',bold=True):
        s.o.append(f'<text x="{x}" y="{y}" font-family="Tahoma,Verdana,DejaVu Sans" font-size="{size}" font-weight="{"bold" if bold else "normal"}" fill="{col}" text-anchor="{anch}">{t}</text>')
    def glow(s,cx,cy,r,col='#FFE800'):
        for i,(rr,op) in enumerate(((r*2.6,0.18),(r*1.8,0.28),(r*1.15,0.45))):
            s.o.append(f'<circle cx="{cx}" cy="{cy}" r="{rr}" fill="{col}" opacity="{op}"/>')

W,H=160,120
def dom(on):
    c=C(W,H); R = BRICK if on else sh('#8C6050','#B08878','#5C3828')
    c.rect(18,34,124,72,CONC)
    c.poly([(12,38),(80,10),(148,38),(140,44),(80,20),(20,44)],R)
    c.poly([(20,44),(80,20),(140,44),(140,50),(80,26),(20,50)],sh(R['d'],R['d'],R['d']),ow=0)
    c.line(80,20,80,106,K,2)
    for x in (36,56,104,124):
        c.rect(x-9,58,18,16,BLUE if on else DGREY,band=3,ow=2)
    c.rect(70,80,20,26,sh('#8C6038','#B08050','#5C3820'),band=3,ow=2)
    c.rect(112,14,12,20,sh('#909090','#C0C0C0','#585858'),band=3,ow=2)
    return c
def magazyn(on):
    c=C(W,H); m = GREY if on else DGREY
    c.rect(14,36,132,70,m)
    c.poly([(8,40),(80,16),(152,40),(146,46),(80,24),(14,46)],DGREY)
    for i in range(1,7):
        x=14+i*132/7; c.line(x,46,x,106,'#707070',1.6)
    c.rect(58,66,44,40,DARK,band=4,ow=2.5)
    for i in range(1,4): c.line(58,66+i*10,102,66+i*10,'#404448',1.5)
    c.rect(20,72,20,16,BLUE if on else DGREY,band=3,ow=2)
    c.rect(120,72,20,16,BLUE if on else DGREY,band=3,ow=2)
    return c
def brama(state):
    c=C(W,H)
    c.rect(6,80,148,14,CONC,band=3)
    for x in (14,146): c.rect(x-8,44,16,44,GREY,band=3)
    frac={'ZAMKNIETA':1.0,'W_RUCHU':0.5,'OTWARTA':0.08}[state]
    col={'ZAMKNIETA':RED,'W_RUCHU':YELL,'OTWARTA':GREEN}[state]
    wdt=int(110*frac)
    if wdt>6:
        c.rect(26,50,wdt,30,col,band=4)
        for i in range(1,max(2,wdt//16)):
            c.line(26+i*16,52,26+i*16,78,K,1.6)
    c.rect(20,60,14,24,DARK,band=3,ow=2)
    c.circ(146,38,7, GREEN if state=='OTWARTA' else (YELL if state=='W_RUCHU' else RED),ow=2)
    return c
def zbiornik(on):
    c=C(W,H)
    c.circ(80,64,44,GREY)
    c.o.append(f'<circle cx="80" cy="64" r="34" fill="none" stroke="#909090" stroke-width="2"/>')
    lvl = 0.68 if on else 0.22
    hgt=int(62*lvl)
    c.o.append(f'<clipPath id="cl"><circle cx="80" cy="64" r="33"/></clipPath>')
    c.o.append(f'<g clip-path="url(#cl)"><rect x="47" y="{95-hgt}" width="66" height="{hgt}" fill="{BLUE["b"]}"/>'
               f'<rect x="47" y="{95-hgt}" width="66" height="5" fill="{BLUE["l"]}"/></g>')
    c.o.append(f'<circle cx="80" cy="64" r="33" fill="none" stroke="{K}" stroke-width="2"/>')
    c.circ(80,64,11,DGREY,ow=2)
    c.rect(122,58,30,12,GREY,band=3,ow=2)
    return c
def oczyszczalnia(on):
    c=C(W,H)
    c.rect(16,40,128,58,CONC)
    for cx in (48,80,112):
        c.circ(cx,69,15,DGREY,ow=2)
        c.circ(cx,69,8,BLUE if on else sh('#5C6470','#8C94A0','#3C4450'),ow=1.8)
    c.rect(6,60,12,18,GREY,band=3,ow=2)
    c.rect(142,60,12,18,GREY,band=3,ow=2)
    c.circ(140,30,8,GREEN if on else RED,ow=2)
    return c
def slup(n,on):
    c=C(W,H)
    c.rect(72,88,16,18,CONC,band=3,ow=2)
    c.vrect(75,26,10,64,DGREY,band=3)
    if n==2:
        c.line(30,26,130,26,K,7,'round'); c.line(30,25,130,25,'#B0B0B0',2.5,'round')
        for x in (30,130):
            if on: c.glow(x,40,11)
            c.poly([(x-13,26),(x+13,26),(x+9,38),(x-9,38)],YELL if on else DARK)
    else:
        c.line(80,26,124,26,K,7,'round'); c.line(80,25,124,25,'#B0B0B0',2.5,'round')
        if on: c.glow(124,40,12)
        c.poly([(111,26),(137,26),(133,38),(115,38)],YELL if on else DARK)
    return c
def halogen(on):
    c=C(W,H)
    c.rect(66,74,28,32,DGREY,band=4)
    c.poly([(30,26),(130,26),(122,66),(38,66)],DGREY)
    if on: c.glow(80,52,26)
    c.rect(40,32,80,28,YELL if on else DARK,band=4)
    c.line(80,66,80,74,K,6)
    return c
def slupek_ogr(on):
    c=C(W,H)
    c.rect(66,92,28,14,CONC,band=3,ow=2)
    c.vrect(71,44,18,50,DGREY,band=4)
    if on: c.glow(80,36,18)
    c.poly([(58,44),(102,44),(96,22),(64,22)],YELL if on else DARK)
    c.rect(56,16,48,8,DGREY,band=2,ow=2)
    return c
def studzienka(on):
    c=C(W,H)
    c.circ(80,64,40,CONC)
    c.circ(80,64,29,DGREY,ow=2)
    for a in range(0,360,45):
        import math
        r1,r2=13,26; rad=math.radians(a)
        c.line(80+r1*math.cos(rad),64+r1*math.sin(rad),80+r2*math.cos(rad),64+r2*math.sin(rad),'#606060',2)
    c.circ(80,64,11,BLUE if on else DGREY,ow=2)
    return c
def zlacze(on):
    c=C(W,H)
    c.rect(34,22,92,84,GREY)
    c.rect(42,30,76,50,DARK,band=4,ow=2)
    for i,y in enumerate((38,50,62)):
        c.rect(48,y,20,8,RED if on else DGREY,band=2,ow=1.5)
        c.rect(76,y,34,8,CONC,band=2,ow=1.5)
    c.circ(58,92,7,GREEN if on else DGREY,ow=2)
    c.circ(80,92,7,RED if not on else DGREY,ow=2)
    c.txt(104,96,'ZK',13)
    return c
def kogut(on):
    c=C(W,H)
    c.rect(60,86,40,20,DGREY,band=4)
    if on: c.glow(80,56,30,'#FF3030')
    c.o.append(f'<path d="M52,86 A28,34 0 0 1 108,86 Z" fill="{(RED if on else sh("#8C3838","#B06060","#5C2020"))["b"]}" stroke="{K}" stroke-width="2.5"/>')
    c.o.append(f'<path d="M60,72 A22,26 0 0 1 74,50" fill="none" stroke="{RED["l"] if on else "#A05858"}" stroke-width="7" stroke-linecap="round"/>')
    if on:
        for a,l in ((-60,1),(-90,1),(-120,1)):
            import math; rad=math.radians(a)
            c.line(80+34*math.cos(rad),70+34*math.sin(rad),80+48*math.cos(rad),70+48*math.sin(rad),'#FF4040',5,'round')
    return c
def tuba(on):
    c=C(W,H)
    c.rect(30,52,26,28,DGREY,band=4)
    c.poly([(56,42),(120,20),(120,110),(56,90)],GREY if not on else sh('#D8D8D0','#F8F8F0','#A0A098'))
    c.line(120,20,120,110,K,3)
    if on:
        for i,(x,op) in enumerate(((132,0.55),(142,0.38),(152,0.22))):
            c.o.append(f'<path d="M{x},{34+i*4} Q{x+9},65 {x},{96-i*4}" fill="none" stroke="#FFE800" stroke-width="4" opacity="{op}"/>')
    c.rect(18,58,14,16,DARK,band=3,ow=2)
    return c
def trawa(on):
    c=C(W,H); g = GRASS if on else sh('#8C9440','#B0B860','#5C6428')
    c.rect(8,20,144,80,g,band=6)
    import random; random.seed(3)
    for i in range(46):
        x=14+random.random()*140; y=28+random.random()*64
        c.line(x,y,x-2,y-7,g['l'],1.6,'round'); c.line(x+3,y,x+4,y-6,g['d'],1.6,'round')
    return c
def droga(on):
    c=C(W,H)
    c.rect(8,28,144,64,CONC,band=6)
    for x in (56,104): c.line(x,30,x,90,'#A0A098',2.5)
    c.line(8,60,152,60,'#A0A098',2.5)
    for i in range(0,7):
        c.line(20+i*20,58,32+i*20,58,'#FFFFFF',3)
    return c
def slupek_podl(on):
    c=C(W,H)
    c.rect(64,88,32,18,CONC,band=3,ow=2)
    c.vrect(70,40,20,50,GREY,band=4)
    c.rect(60,26,40,16,DGREY,band=3,ow=2)
    c.circ(80,20,8,BLUE if on else DGREY,ow=2)
    if on:
        for dx in (-26,-13,0,13,26):
            c.o.append(f'<path d="M80,14 Q{80+dx*1.5},{-8} {80+dx*2.4},{16}" fill="none" stroke="#60A0FF" stroke-width="3" opacity="0.75"/>')
    c.rect(56,60,10,10,GREEN if on else RED,band=0,ow=2)
    return c
