# ============================================================================
# EPW - REFERENCJA GEOMETRII: gospodarka wodna
# ----------------------------------------------------------------------------
# Ten plik NIE JEST przeznaczony do uruchamiania w aplikacji.
# To wzorzec geometrii do przepisania na komponenty Konva w TypeScripcie.
#
# Plotno kazdego obiektu: 128 x 96 jednostek (parzysta wielokrotnosc
# GRID_SIZE = 32, wiec srodki krawedzi wypadaja w wezlach siatki).
#
# STYL: retro industrial SCADA, cieniowanie pasmowe.
#   Kazdy ksztalt: czarny kontur, wypelnienie podstawowe,
#   jasniejszy pas u gory (albo z lewej), ciemniejszy u dolu (albo z prawej).
#   Twardo, bez gradientu. Ksztalty okragle: luk swiatla u gory-lewej.
#   Kolor niesie ZNACZENIE, nie zdobi.
#
# RURY: cztery przebiegi na jednej trasie - kontur, wypelnienie, cien, swiatlo.
#   Niebieskie gdy plynie woda, jasnoszare gdy nie plynie.
#   Zalamania zaokraglone, wiec kolanka nie wymagaja osobnego symbolu.
#
# PRYMITYWY klasy C:
#   r()   prostokat, pas jasny u gory, ciemny u dolu
#   vr()  prostokat, pas jasny z lewej, ciemny z prawej
#   c()   kolo z lukiem swiatla
#   p()   wielokat
#   l()   linia
#   t()   tekst
#   val() pole wartosci SCADA: jasne tlo, czarny kontur, monospace do prawej
#   led() dioda: ciemna gdy wylaczona, jasna z odblaskiem gdy zalaczona
#
# ZACHOWANIA APARATOW (kontrakt EPW):
#   tank2            MEASURED   poziom w procentach
#   zawor3           SWITCHED   tryb DUAL: krancowka A i krancowka B
#   zawor3sel        SELECTOR   trzy pozycje: A, ZAMKNIETY, B
#   przeplyw2        MEASURED   przeplyw chwilowy
#   wodomierz2       MEASURED   licznik sumaryczny
#   presostat        SIGNAL     suchobieg
#   czujnik_deszczu  SIGNAL     opad
#   hydrofor         SWITCHED   pompa z naczyniem
#   zawor_zwrotny2   grafika    bez tagu
#   filtr            grafika    bez tagu
#   zraszacz         grafika    element strefy
#   linia_krop       grafika    element strefy
# ============================================================================

import math
CY='#00CFCF'; K='#000000'
G=dict(b='#C0C0C0',l='#F0F0F0',d='#808080'); DG=dict(b='#909090',l='#C8C8C8',d='#585858')
BL=dict(b='#2848D8',l='#5878FF',d='#182C90'); CO=dict(b='#D0D0C8',l='#F0F0E8',d='#9C9C94')
GR=dict(b='#00B800',l='#50E850',d='#007000'); RD=dict(b='#E00000',l='#FF7070',d='#900000')
YE=dict(b='#FFD800',l='#FFF080',d='#B08800'); DK=dict(b='#585C64',l='#8C9098',d='#303438')
W,H=128,96
class C:
    def __init__(s): s.o=[f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg"><rect width="{W}" height="{H}" fill="{CY}"/>']
    def out(s): return ''.join(s.o)+'</svg>'
    def r(s,x,y,w,h,c,b=4,ow=2.5):
        s.o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{c["b"]}" stroke="{K}" stroke-width="{ow}"/>')
        if b: s.o.append(f'<rect x="{x+ow/2}" y="{y+ow/2}" width="{w-ow}" height="{b}" fill="{c["l"]}"/>'
                         f'<rect x="{x+ow/2}" y="{y+h-b-ow/2}" width="{w-ow}" height="{b}" fill="{c["d"]}"/>')
    def vr(s,x,y,w,h,c,b=4,ow=2.5):
        s.o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{c["b"]}" stroke="{K}" stroke-width="{ow}"/>')
        s.o.append(f'<rect x="{x+ow/2}" y="{y+ow/2}" width="{b}" height="{h-ow}" fill="{c["l"]}"/>'
                   f'<rect x="{x+w-b-ow/2}" y="{y+ow/2}" width="{b}" height="{h-ow}" fill="{c["d"]}"/>')
    def c(s,cx,cy,r,col,ow=2.5):
        s.o.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{col["b"]}" stroke="{K}" stroke-width="{ow}"/>')
        s.o.append(f'<path d="M{cx-r*.7},{cy-r*.5} A{r*.85},{r*.85} 0 0 1 {cx+r*.1},{cy-r*.85}" fill="none" stroke="{col["l"]}" stroke-width="{r*.3}" stroke-linecap="round"/>')
    def p(s,pts,col,ow=2.5):
        s.o.append('<path d="M'+' L'.join(f'{x},{y}' for x,y in pts)+f' Z" fill="{col["b"]}" stroke="{K}" stroke-width="{ow}"/>')
    def l(s,x1,y1,x2,y2,col=K,w=2.5,cap='butt'):
        s.o.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col}" stroke-width="{w}" stroke-linecap="{cap}"/>')
    def t(s,x,y,txt,sz=11,col=K,an='middle'):
        s.o.append(f'<text x="{x}" y="{y}" font-family="Tahoma,DejaVu Sans" font-size="{sz}" font-weight="bold" fill="{col}" text-anchor="{an}">{txt}</text>')
    def val(s,x,y,w,txt):
        s.o.append(f'<rect x="{x}" y="{y}" width="{w}" height="18" fill="#F0F0E8" stroke="{K}" stroke-width="2"/>')
        s.o.append(f'<text x="{x+w-4}" y="{y+13}" font-family="Consolas,DejaVu Sans Mono,monospace" font-size="11" font-weight="bold" fill="{K}" text-anchor="end">{txt}</text>')
    def led(s,x,y,on,col='#00E838'):
        s.o.append(f'<circle cx="{x}" cy="{y}" r="6" fill="{col if on else "#3C4048"}" stroke="{K}" stroke-width="2"/>')
        if on: s.o.append(f'<circle cx="{x-1.6}" cy="{y-1.6}" r="2.6" fill="#C0FFC8"/>')


def pipe_seg(c,pts,live,w=13):
    b=BL if live else G
    d='M'+' L'.join(f'{x},{y}' for x,y in pts)
    c.o.append(f'<path d="{d}" stroke="{K}" stroke-width="{w+5}" fill="none" stroke-linejoin="round" stroke-linecap="round"/>')
    c.o.append(f'<path d="{d}" stroke="{b["b"]}" stroke-width="{w}" fill="none" stroke-linejoin="round" stroke-linecap="round"/>')
    c.o.append(f'<path d="{d}" stroke="{b["l"]}" stroke-width="3.5" fill="none" stroke-linejoin="round" stroke-linecap="round" transform="translate(-1,-3.2)"/>')

def zawor3(pos):
    c=C(); A=pos=='A'; cx,cy=58,54
    pipe_seg(c,[(4,cy),(cx,cy)],True)
    pipe_seg(c,[(cx,cy),(112,cy)],A)
    pipe_seg(c,[(cx,cy),(cx,92)],not A)
    c.c(cx,cy,17,DG)
    ang=0 if A else 90
    c.o.append(f'<g transform="rotate({ang} {cx} {cy})"><path d="M{cx-13},{cy} L{cx+13},{cy}" stroke="{BL["b"]}" stroke-width="6" stroke-linecap="round"/>'
               f'<path d="M{cx+6},{cy-6} L{cx+13},{cy} L{cx+6},{cy+6}" fill="none" stroke="{BL["b"]}" stroke-width="3.5" stroke-linejoin="round"/></g>')
    c.r(cx-11,cy-38,22,20,G,b=3,ow=2)
    c.l(cx,cy-18,cx,cy-16,K,7)
    c.led(cx-22,cy-46,A); c.t(cx-22,cy-54,'A',10)
    c.led(cx+22,cy-46,not A); c.t(cx+22,cy-54,'B',10)
    return c


def zawor3(pos):
    c=C(); A=pos=='A'; cx,cy=58,54
    pipe_seg(c,[(4,cy),(cx,cy)],True)
    pipe_seg(c,[(cx,cy),(112,cy)],A)
    pipe_seg(c,[(cx,cy),(cx,92)],not A)
    c.c(cx,cy,17,DG)
    ang=0 if A else 90
    c.o.append(f'<g transform="rotate({ang} {cx} {cy})"><path d="M{cx-13},{cy} L{cx+13},{cy}" stroke="{BL["b"]}" stroke-width="6" stroke-linecap="round"/>'
               f'<path d="M{cx+6},{cy-6} L{cx+13},{cy} L{cx+6},{cy+6}" fill="none" stroke="{BL["b"]}" stroke-width="3.5" stroke-linejoin="round"/></g>')
    c.r(cx-11,cy-38,22,20,G,b=3,ow=2)
    c.l(cx,cy-18,cx,cy-16,K,7)
    c.led(cx-22,cy-46,A); c.t(cx-22,cy-54,'A',10)
    c.led(cx+22,cy-46,not A); c.t(cx+22,cy-54,'B',10)
    return c

def czujnik_deszczu(on):
    c=C()
    c.r(48,64,32,26,DG,b=4)
    c.p([(26,64),(102,64),(94,44),(34,44)],G)
    c.o.append(f'<ellipse cx="64" cy="44" rx="32" ry="7" fill="{G["l"]}" stroke="{K}" stroke-width="2.5"/>')
    if on:
        for i,(x,y) in enumerate(((30,16),(46,8),(62,14),(80,7),(96,17))):
            c.o.append(f'<path d="M{x},{y} q4,9 0,13 q-4,-4 0,-13 Z" fill="{BL["b"]}" stroke="{K}" stroke-width="1.6"/>')
    c.led(64,78,on,'#3898FF')
    return c

def presostat(on):
    c=C()
    pipe_seg(c,[(4,74),(124,74)],True)
    c.vr(52,44,24,24,G,b=3)
    c.c(64,32,17,G)
    c.o.append(f'<circle cx="64" cy="32" r="12" fill="#F4F4EC" stroke="{K}" stroke-width="2"/>')
    a=math.radians(-40 if on else -140)
    c.l(64,32,64+10*math.cos(a),32+10*math.sin(a),'#C01818',2.5,'round')
    c.o.append(f'<circle cx="64" cy="32" r="2.5" fill="{K}"/>')
    c.led(100,32,on)
    return c

def hydrofor(on):
    c=C()
    c.r(10,80,108,8,CO,b=3,ow=2)
    c.o.append(f'<rect x="14" y="30" width="42" height="50" rx="8" fill="{BL["b"] if on else G["b"]}" stroke="{K}" stroke-width="2.5"/>')
    c.o.append(f'<rect x="18" y="34" width="6" height="42" fill="{BL["l"] if on else G["l"]}"/>')
    c.o.append(f'<rect x="47" y="34" width="5" height="42" fill="{BL["d"] if on else G["d"]}" opacity="0.6"/>')
    c.c(86,56,20,GR if on else RD)
    c.p([(78,46),(78,66),(98,56)],DK)
    pipe_seg(c,[(56,56),(66,56)],on,10)
    c.led(110,26,on)
    return c

def zraszacz(on):
    c=C()
    c.r(46,72,36,16,CO,b=3,ow=2)
    c.vr(56,52,16,22,DG,b=3)
    c.c(64,48,9,BL if on else DG,ow=2)
    if on:
        for dx in (-34,-18,0,18,34):
            c.o.append(f'<path d="M64,42 Q{64+dx*1.4},10 {64+dx*2.0},44" fill="none" stroke="#5898FF" stroke-width="3" opacity="0.8"/>')
    return c

def linia_krop(on):
    c=C()
    pipe_seg(c,[(6,44),(122,44)],on,11)
    for x in (24,48,72,96):
        c.o.append(f'<rect x="{x-4}" y="50" width="8" height="7" fill="{DG["b"]}" stroke="{K}" stroke-width="1.8"/>')
        if on:
            c.o.append(f'<path d="M{x},60 q3,7 0,11 q-3,-4 0,-11 Z" fill="{BL["b"]}" stroke="{K}" stroke-width="1.5"/>')
            c.o.append(f'<ellipse cx="{x}" cy="84" rx="9" ry="3.5" fill="{BL["b"]}" opacity="0.45"/>')
    return c

def filtr(on):
    c=C()
    pipe_seg(c,[(4,40),(124,40)],on)
    c.o.append(f'<path d="M44,48 L84,48 L84,74 Q64,88 44,74 Z" fill="{G["b"]}" stroke="{K}" stroke-width="2.5"/>')
    c.o.append(f'<rect x="48" y="52" width="5" height="24" fill="{G["l"]}"/>')
    for i in range(4):
        c.l(50,56+i*6,78,56+i*6,DG['d'],1.6)
    c.r(46,34,36,14,G,b=3,ow=2)
    return c


def zawor3sel(pos):
    """trojpolozeniowy: A, B, ZAMKNIETY"""
    c=C(); cx,cy=58,54
    A = pos=='A'; B = pos=='B'; Z = pos=='ZAMK'
    pipe_seg(c,[(4,cy),(cx,cy)],not Z)
    pipe_seg(c,[(cx,cy),(112,cy)],A)
    pipe_seg(c,[(cx,cy),(cx,92)],B)
    c.c(cx,cy,17,DG)
    if Z:
        # klin odcinajacy: gruba poprzeczka w korpusie
        c.o.append(f'<rect x="{cx-14}" y="{cy-4}" width="28" height="8" fill="{RD["b"]}" stroke="{K}" stroke-width="2"/>')
        c.o.append(f'<rect x="{cx-4}" y="{cy-14}" width="8" height="28" fill="{RD["b"]}" stroke="{K}" stroke-width="2"/>')
    else:
        ang = 0 if A else 90
        c.o.append(f'<g transform="rotate({ang} {cx} {cy})"><path d="M{cx-13},{cy} L{cx+13},{cy}" stroke="{BL["b"]}" stroke-width="6" stroke-linecap="round"/>'
                   f'<path d="M{cx+6},{cy-6} L{cx+13},{cy} L{cx+6},{cy+6}" fill="none" stroke="{BL["b"]}" stroke-width="3.5" stroke-linejoin="round"/></g>')
    c.r(cx-11,cy-38,22,20,G,b=3,ow=2)
    c.l(cx,cy-18,cx,cy-16,K,7)
    for lx,lbl,on,col in ((cx-30,'A',A,'#00E838'),(cx,'Z',Z,'#E02020'),(cx+30,'B',B,'#00E838')):
        c.led(lx,cy-48,on,col); c.t(lx,cy-56,lbl,10)
    return c

# ZBIORNIK poprawiony: okienko poziomu przesuniete, brak nachodzenia
def tank2(pct):
    c=C(); BX,BY,BW,BH=14,40,70,42
    c.r(8,82,82,8,CO,b=3,ow=2)
    c.o.append(f'<clipPath id="k"><rect x="{BX+2}" y="{BY+2}" width="{BW-4}" height="{BH-4}"/></clipPath>')
    c.o.append(f'<rect x="{BX}" y="{BY}" width="{BW}" height="{BH}" fill="{G["b"]}" stroke="{K}" stroke-width="2.5"/>')
    hg=int((BH-4)*pct/100)
    if hg>0:
        top=BY+BH-2-hg
        c.o.append(f'<g clip-path="url(#k)"><rect x="{BX+2}" y="{top}" width="{BW-4}" height="{hg}" fill="{BL["b"]}"/>'
                   f'<rect x="{BX+2}" y="{top}" width="{BW-4}" height="3" fill="{BL["l"]}"/>'
                   f'<rect x="{BX+2}" y="{top+3}" width="5" height="{hg-3}" fill="{BL["l"]}" opacity="0.5"/></g>')
    c.o.append(f'<rect x="{BX+2}" y="{BY+2}" width="5" height="{BH-4}" fill="{G["l"]}" opacity="0.45"/>'
               f'<rect x="{BX}" y="{BY}" width="{BW}" height="{BH}" fill="none" stroke="{K}" stroke-width="2.5"/>')
    c.o.append(f'<path d="M{BX},{BY} A{BW/2},20 0 0 1 {BX+BW},{BY} Z" fill="{G["b"]}" stroke="{K}" stroke-width="2.5"/>')
    cx=BX+BW/2
    for dx in (-24,-12,0,12,24):
        c.o.append(f'<path d="M{cx},{BY-19} Q{cx+dx*1.2},{BY-13} {cx+dx*1.4},{BY}" fill="none" stroke="{DG["d"]}" stroke-width="1.3"/>')
    for rr,yy in ((0.72,7),(0.42,13)):
        c.o.append(f'<path d="M{cx-BW/2*rr},{BY-yy} A{BW/2*rr*1.4},{16*rr} 0 0 1 {cx+BW/2*rr},{BY-yy}" fill="none" stroke="{DG["d"]}" stroke-width="1.3"/>')
    c.o.append(f'<path d="M{BX+8},{BY-4} A{BW/2.6},15 0 0 1 {BX+26},{BY-15}" fill="none" stroke="{G["l"]}" stroke-width="4" stroke-linecap="round"/>')
    # okienko poziomu NA ZEWNATRZ plaszcza, po prawej - brak nachodzenia
    c.o.append(f'<rect x="{BX+BW+3}" y="{BY+4}" width="12" height="{BH-8}" fill="#F4F4EC" stroke="{K}" stroke-width="2"/>')
    ih=int((BH-12)*pct/100)
    if ih>0: c.o.append(f'<rect x="{BX+BW+5}" y="{BY+BH-6-ih}" width="8" height="{ih}" fill="{BL["b"]}"/>')
    c.r(BX-12,BY+BH-12,12,7,G,b=2,ow=2)
    c.r(BX+BW+15,BY+2,10,6,G,b=2,ow=2)
    c.val(92,58,32,f'{pct}%')
    return c

def wodomierz2(on):
    """licznik sumaryczny - wyrazny wyswietlacz cyfrowy z opisem m3"""
    c=C()
    pipe_seg(c,[(4,70),(124,70)],on)
    c.r(30,26,68,34,G,b=4)
    c.o.append(f'<rect x="36" y="32" width="56" height="16" fill="#101418" stroke="{K}" stroke-width="2"/>')
    c.o.append(f'<text x="88" y="45" font-family="Consolas,DejaVu Sans Mono,monospace" font-size="12" font-weight="bold" fill="#30E840" text-anchor="end">{"04728" if on else "04728"}</text>')
    c.t(64,57,'m3  SUMA',9)
    c.l(64,60,64,70,K,4)
    return c

def przeplyw2(on):
    """chwilowy - z wirnikiem i strzalka kierunku"""
    c=C()
    pipe_seg(c,[(4,62),(124,62)],on)
    c.c(64,36,20,G)
    c.o.append(f'<circle cx="64" cy="36" r="14" fill="#101418" stroke="{K}" stroke-width="2"/>')
    c.o.append(f'<text x="64" y="40" font-family="Consolas,DejaVu Sans Mono,monospace" font-size="11" font-weight="bold" fill="{"#30E840" if on else "#2C4030"}" text-anchor="middle">{"12.4" if on else "0.0"}</text>')
    c.t(64,17,'l/min',9)
    c.l(64,56,64,62,K,4)
    if on:
        c.o.append(f'<path d="M92,62 L108,62 M102,56 L108,62 L102,68" fill="none" stroke="#FFFFFF" stroke-width="2.5" stroke-linejoin="round"/>')
    return c

def zawor_zwrotny2(live):
    """klapa zwrotna - wyraznie wodna, nie elektroniczna"""
    c=C()
    pipe_seg(c,[(4,54),(124,54)],live)
    c.r(42,36,44,36,G,b=4)
    # klapa uchylna na zawiasie u gory
    if live:
        c.o.append(f'<path d="M52,42 L74,60" stroke="{K}" stroke-width="7" stroke-linecap="round"/>')
        c.o.append(f'<path d="M52,42 L74,60" stroke="{GR["b"]}" stroke-width="4" stroke-linecap="round"/>')
    else:
        c.o.append(f'<path d="M52,42 L52,68" stroke="{K}" stroke-width="7" stroke-linecap="round"/>')
        c.o.append(f'<path d="M52,42 L52,68" stroke="{RD["b"]}" stroke-width="4" stroke-linecap="round"/>')
    c.o.append(f'<circle cx="52" cy="42" r="3.5" fill="{K}"/>')
    c.o.append(f'<path d="M92,26 L108,26 M102,20 L108,26 L102,32" fill="none" stroke="{K}" stroke-width="2.5" stroke-linejoin="round"/>')
    return c
