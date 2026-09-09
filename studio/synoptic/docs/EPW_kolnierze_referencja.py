# ============================================================================
# EPW - REFERENCJA GEOMETRII: standard przylacza hydraulicznego
# ----------------------------------------------------------------------------
# Plik NIE JEST do uruchamiania w aplikacji. To wzorzec geometrii
# do przepisania na komponenty Konva w TypeScripcie.
#
# Plotno obiektu: 128 x 96 jednostek (parzysta wielokrotnosc GRID_SIZE = 32).
# Zaciski na SRODKACH KRAWEDZI: lewo (0,48), prawo (128,48),
# gora (64,0), dol (64,96).
#
# ============================================================================
# STANDARD PRZYLACZA - obowiazuje KAZDY aparat o medium WODA
# ============================================================================
# Kazdy zacisk aparatu ma:
#   1. KROCIEC (stub)   - odcinek rury od korpusu do krawedzi plotna,
#                         rysowany funkcja tube(), wiec dziedziczy kolor
#                         stanu: szary bez przeplywu, niebieski z przeplywem
#   2. KOLNIERZ (flange) - belka PROSTOPADLA do osi rury, umieszczona
#                         tuz przy krawedzi plotna, szersza od rury,
#                         z pasmem swiatla u gory albo z lewej
#
# Skutek: rura uzytkownika dochodzi do ZEWNETRZNEJ sciany kolnierza,
# a zacisk pozostaje dokladnie na srodku krawedzi - regula siatki
# nienaruszona.
#
# WYMIARY - do przeniesienia do ScadaTheme, nie zapisywac na sztywno:
#   PIPE_W = 13   rdzen rury
#   STUB   = 14   dlugosc kroćca liczona od korpusu
#   FL_W   = 6    grubosc kolnierza wzdluz osi rury
#   FL_H   = PIPE_W + 11 = 24   rozpietosc kolnierza w poprzek rury
#
# Funkcja stub() rysuje krociec i kolnierz jednym wywolaniem, dla strony
# 'L', 'R', 'T' albo 'B'. Kazdy aparat wodny wola ja dla kazdego swojego
# zacisku.
#
# ============================================================================
# ZBIORNIK - uklad przylaczy
# ============================================================================
# DOPLYW  wchodzi z LEWEJ krawedzi, prowadzony w gorna czesc plaszcza.
# ODPLYW  wychodzi w PRAWO z dolnej czesci plaszcza.
# Oba z kolnierzami na krawedziach plotna.
# Odplyw rysowany jako NIEAKTYWNY, gdy poziom wynosi zero.
# Okienko poziomu WEWNATRZ plaszcza, pole procentu w prawym gornym rogu -
# przy 88 procentach nic na siebie nie nachodzi.
# ============================================================================

import math

CY='#00CFCF'; K='#000000'
G=dict(b='#C0C0C0',l='#F0F0F0',d='#808080'); DG=dict(b='#909090',l='#C8C8C8',d='#585858')
BL=dict(b='#2848D8',l='#5878FF',d='#182C90'); CO=dict(b='#D0D0C8',l='#F0F0E8',d='#9C9C94')
W,H=128,96
PIPE_W=13          # rdzen rury
STUB=14            # dlugosc kroćca od korpusu do kolnierza
FL_W=6             # grubosc kolnierza
FL_H=PIPE_W+11     # rozpietosc kolnierza w poprzek rury

class C:
    def __init__(s,w=W,h=H): s.w=w; s.h=h; s.o=[f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg"><rect width="{w}" height="{h}" fill="{CY}"/>']
    def out(s): return ''.join(s.o)+'</svg>'
    def r(s,x,y,w,h,c,b=4,ow=2.5):
        s.o.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{c["b"]}" stroke="{K}" stroke-width="{ow}"/>')
        if b: s.o.append(f'<rect x="{x+ow/2}" y="{y+ow/2}" width="{w-ow}" height="{b}" fill="{c["l"]}"/><rect x="{x+ow/2}" y="{y+h-b-ow/2}" width="{w-ow}" height="{b}" fill="{c["d"]}"/>')
    def c(s,cx,cy,r,col,ow=2.5):
        s.o.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{col["b"]}" stroke="{K}" stroke-width="{ow}"/>')
        s.o.append(f'<path d="M{cx-r*.7},{cy-r*.5} A{r*.85},{r*.85} 0 0 1 {cx+r*.1},{cy-r*.85}" fill="none" stroke="{col["l"]}" stroke-width="{r*.3}" stroke-linecap="round"/>')
    def p(s,pts,col,ow=2.5):
        s.o.append('<path d="M'+' L'.join(f'{x},{y}' for x,y in pts)+f' Z" fill="{col["b"]}" stroke="{K}" stroke-width="{ow}"/>')
    def val(s,x,y,w,t):
        s.o.append(f'<rect x="{x}" y="{y}" width="{w}" height="18" fill="#F0F0E8" stroke="{K}" stroke-width="2"/>')
        s.o.append(f'<text x="{x+w-4}" y="{y+13}" font-family="Consolas,monospace" font-size="11" font-weight="bold" fill="{K}" text-anchor="end">{t}</text>')

def tube(o,pts,live,w=PIPE_W):
    b = BL if live else G
    d='M'+' L'.join(f'{x},{y}' for x,y in pts)
    o.append(f'<path d="{d}" stroke="{K}" stroke-width="{w+5}" fill="none" stroke-linejoin="round" stroke-linecap="round"/>')
    o.append(f'<path d="{d}" stroke="{b["b"]}" stroke-width="{w}" fill="none" stroke-linejoin="round" stroke-linecap="round"/>')
    o.append(f'<path d="{d}" stroke="{b["l"]}" stroke-width="3.5" fill="none" stroke-linejoin="round" stroke-linecap="round" transform="translate(-1,-3.2)"/>')

def flange(o,x,y,side,live):
    """kolnierz prostopadly do osi rury, na koncu kroćca"""
    b = BL if live else G
    if side in ('L','R'):
        o.append(f'<rect x="{x-FL_W/2}" y="{y-FL_H/2}" width="{FL_W}" height="{FL_H}" fill="{b["b"]}" stroke="{K}" stroke-width="2.5"/>')
        o.append(f'<rect x="{x-FL_W/2+1.2}" y="{y-FL_H/2+1.2}" width="{FL_W-2.4}" height="3" fill="{b["l"]}"/>')
    else:
        o.append(f'<rect x="{x-FL_H/2}" y="{y-FL_W/2}" width="{FL_H}" height="{FL_W}" fill="{b["b"]}" stroke="{K}" stroke-width="2.5"/>')
        o.append(f'<rect x="{x-FL_H/2+1.2}" y="{y-FL_W/2+1.2}" width="3" height="{FL_W-2.4}" fill="{b["l"]}"/>')

def stub(o,bx,by,side,live):
    """krociec od korpusu do krawedzi plotna + kolnierz tuz przy krawedzi"""
    if side=='L':  a,bb=(bx,by),(0,by);  fx,fy=FL_W/2+1,by
    if side=='R':  a,bb=(bx,by),(W,by);  fx,fy=W-FL_W/2-1,by
    if side=='T':  a,bb=(bx,by),(bx,0);  fx,fy=bx,FL_W/2+1
    if side=='B':  a,bb=(bx,by),(bx,H);  fx,fy=bx,H-FL_W/2-1
    tube(o,[a,bb],live)
    flange(o,fx,fy,side,live)

# ---------- ZAWOR z kroćcami i kolnierzami ----------
def zawor(live):
    c=C(); cx,cy=64,48
    stub(c.o,cx-20,cy,'L',live); stub(c.o,cx+20,cy,'R',live)
    c.p([(cx-24,cy-20),(cx-24,cy+20),(cx,cy)],DG)
    c.p([(cx+24,cy-20),(cx+24,cy+20),(cx,cy)],DG)
    c.r(cx-9,cy-34,18,14,dict(b='#2860C8',l='#5890F0',d='#1A3C88'),b=3,ow=2)
    c.o.append(f'<rect x="{cx-3}" y="{cy-20}" width="6" height="6" fill="#707070" stroke="{K}" stroke-width="2"/>')
    return c

# ---------- FILTR ----------
def filtr(live):
    c=C(); cy=44
    stub(c.o,44,cy,'L',live); stub(c.o,84,cy,'R',live)
    c.r(44,30,40,14,G,b=3)
    c.o.append(f'<path d="M48,44 L80,44 L80,68 Q64,80 48,68 Z" fill="{G["b"]}" stroke="{K}" stroke-width="2.5"/>')
    c.o.append(f'<rect x="51" y="47" width="4" height="22" fill="{G["l"]}"/>')
    for i in range(4): c.o.append(f'<line x1="53" y1="{50+i*5}" x2="76" y2="{50+i*5}" stroke="{DG["d"]}" stroke-width="1.5"/>')
    return c

# ---------- ZBIORNIK: doplyw gora-lewo, odplyw dol-prawo ----------
def tank(pct):
    c=C(); BX,BY,BW,BH=26,38,64,40
    # fundament
    c.r(20,78,76,8,CO,b=3,ow=2)
    # plaszcz + woda
    c.o.append(f'<clipPath id="k"><rect x="{BX+2}" y="{BY+2}" width="{BW-4}" height="{BH-4}"/></clipPath>')
    c.o.append(f'<rect x="{BX}" y="{BY}" width="{BW}" height="{BH}" fill="{G["b"]}" stroke="{K}" stroke-width="2.5"/>')
    hg=int((BH-4)*pct/100)
    if hg>0:
        top=BY+BH-2-hg
        c.o.append(f'<g clip-path="url(#k)"><rect x="{BX+2}" y="{top}" width="{BW-4}" height="{hg}" fill="{BL["b"]}"/>'
                   f'<rect x="{BX+2}" y="{top}" width="{BW-4}" height="3" fill="{BL["l"]}"/></g>')
    c.o.append(f'<rect x="{BX+2}" y="{BY+2}" width="5" height="{BH-4}" fill="{G["l"]}" opacity="0.45"/>')
    c.o.append(f'<rect x="{BX}" y="{BY}" width="{BW}" height="{BH}" fill="none" stroke="{K}" stroke-width="2.5"/>')
    # kopula
    c.o.append(f'<path d="M{BX},{BY} A{BW/2},18 0 0 1 {BX+BW},{BY} Z" fill="{G["b"]}" stroke="{K}" stroke-width="2.5"/>')
    cxx=BX+BW/2
    for dx in (-22,-11,0,11,22):
        c.o.append(f'<path d="M{cxx},{BY-17} Q{cxx+dx*1.2},{BY-12} {cxx+dx*1.42},{BY}" fill="none" stroke="{DG["d"]}" stroke-width="1.2"/>')
    c.o.append(f'<path d="M{cxx-22},{BY-6} A{28},13 0 0 1 {cxx+22},{BY-6}" fill="none" stroke="{DG["d"]}" stroke-width="1.2"/>')
    c.o.append(f'<path d="M{BX+7},{BY-4} A22,13 0 0 1 {BX+24},{BY-13}" fill="none" stroke="{G["l"]}" stroke-width="3.5" stroke-linecap="round"/>')
    # DOPLYW: gora, wchodzi z LEWEJ na wysokosci gornej czesci plaszcza
    tube(c.o,[(0,20),(14,20),(14,BY+7),(BX,BY+7)],True)
    flange(c.o,FL_W/2+1,20,'L',True)
    # ODPLYW: dol, wychodzi w PRAWO na wysokosci dolnej czesci plaszcza
    tube(c.o,[(BX+BW,BY+BH-7),(112,BY+BH-7),(112,88),(W,88)],pct>0)
    flange(c.o,W-FL_W/2-1,88,'R',pct>0)
    # okienko poziomu na plaszczu, w srodku, nie nachodzi
    c.o.append(f'<rect x="{BX+BW-18}" y="{BY+5}" width="11" height="{BH-10}" fill="#F4F4EC" stroke="{K}" stroke-width="2"/>')
    ih=int((BH-14)*pct/100)
    if ih>0: c.o.append(f'<rect x="{BX+BW-16}" y="{BY+BH-7-ih}" width="7" height="{ih}" fill="{BL["b"]}"/>')
    # pole wartosci na wolnym miejscu, ponizej kopuly z prawej
    c.val(94,30,30,f'{pct}%')
    return c
