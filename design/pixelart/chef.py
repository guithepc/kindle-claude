# Claudinho chef v2 — corpo inteiro, props ao lado. '#'=preto 'g'=cinza 'w'=branco forçado '.'=vazio
W,H=36,24
FLOOR=23
def blank(): return [['.']*W for _ in range(H)]
def put(c,r,x,v='#'):
    if 0<=r<H and 0<=x<W: c[r][x]=v
def hline(c,r,a,b,v='#'):
    for x in range(a,b+1): put(c,r,x,v)
def stamp(c,top,left,rows,keep=('#','w','g')):
    for i,row in enumerate(rows):
        for j,ch in enumerate(row):
            if ch in keep: put(c,top+i,left+j,ch)
def line(c,r0,x0,r1,x1,v='#'):
    n=max(abs(r1-r0),abs(x1-x0))
    for i in range(n+1):
        put(c,round(r0+(r1-r0)*i/n),round(x0+(x1-x0)*i/n),v)
HAT=["...######...",
     ".##wwwwww##.",
     "#wwwwwwwwww#",
     ".##wwwwww##.",
     "..#wwwwww#..",
     "..########.."]
EYES={
 "right": [".####.####.##.", ".####.####.##."],
 "up":    [".####.####.##.", ".############."],
 "happy": [".####.####.##.", ".############."],
 "cry":   [".############.", ".###..##..###."],
 "open":  [".###.####.###.", ".###.####.###."],
}
EYES["happy"]=[".############.", ".####.####.##."]
def clawd(c,eyes="right",legs="a"):
    rows=[".############.",".############."]+EYES[eyes]+["##############","##############",".############.",".############.",
          ".#.#......#.#." if legs=="a" else "..#.#....#.#.."]
    stamp(c,14,1,rows)
    stamp(c,8,2,HAT)
def floor(c): hline(c,FLOOR,0,W-1)
# ---------- props ----------
def soup_pot(c, phase):
    hline(c,15,19,32)                       # borda
    for r in range(16,20): hline(c,r,20,31) # corpo
    hline(c,20,21,30)                       # fundo
    put(c,16,18); put(c,16,33)              # alças
    for r in (17,18): put(c,r,22,'w')       # brilho
    for x in range(21,31):                  # chama
        if (x+phase)%3==0: put(c,21,x)
    hline(c,22,20,31)                       # boca do fogão
def steam(c, cols, phase, base=14, height=9):
    wave=[0,0,1,1,0,0,-1,-1]
    for k,x0 in enumerate(cols):
        gap=(phase+k)%3*3+2
        for h in range(height-(k%2)*2):
            if h in (gap,gap+1): continue
            put(c,base-h,x0+wave[(h-phase*2+k*4)%8],'g')
def counter(c):
    hline(c,19,17,35)
    for r in (20,21,22): put(c,r,18); put(c,r,34)
def board(c): hline(c,18,19,33)
ONION=["...#...","..###..",".#www#.","#wwwww#","#wwwww#",".#####."]
KNIFE=["...######.","###wwwwww#","###wwwww#.","...####..."]
PAN=["#..........#","############",".##########."]
SHAKER=[".###.","#####","#www#","#www#","#####","#.#.#"]
def sparkle(c,r,x,v='#'):
    put(c,r,x,v); put(c,r-1,x,v); put(c,r+1,x,v); put(c,r,x-1,v); put(c,r,x+1,v)
# ---------- cenas ----------
def sopa(f):
    c=blank(); floor(c); clawd(c,"right","a" if f%2==0 else "b"); soup_pot(c,f)
    steam(c,[27,30],f)
    hx = 21 if f%2==0 else 25
    line(c,17,15,12,hx)                      # braço até a mão
    put(c,13,hx); put(c,14,hx)               # colher descendo na panela
    return c
def cebola(f):
    c=blank(); floor(c); counter(c); board(c)
    clawd(c,"right" if f==0 else "cry")
    stamp(c,12,28,ONION)
    if f==0:
        stamp(c,10,15,KNIFE); line(c,17,15,12,15)
        for x in (22,24): put(c,17,x)
    else:
        stamp(c,14,15,KNIFE); line(c,17,15,16,15)
        for x in (23,25,27): put(c,17,x)
        put(c,18,11,'g'); put(c,19,11,'g')   # lágrima
    return c
def frigideira(f):
    c=blank(); floor(c); clawd(c,"right" if f==0 else "up")
    hline(c,22,21,32); 
    for x in range(22,32):
        if (x+f)%3==0: put(c,21,x)
    lift = 0 if f==0 else 1
    top=16-lift
    stamp(c,top,21,PAN)
    hline(c,top+1,15,20)                     # cabo
    if lift: put(c,17,15)
    if f==0:
        hline(c,top,23,30)                   # panqueca na frigideira
        steam(c,[24,28],f,base=14,height=5)
    elif f==1:
        hline(c,6,25,30); hline(c,7,23,28)   # panqueca no ar
        for x in (24,27,30): put(c,10,x,'g'); put(c,11,x,'g')
    else:
        for r in range(9,13): put(c,r,27); put(c,r,28)   # girando de lado
        for x in (24,31): put(c,8,x,'g'); put(c,9,x,'g')
    return c
def tempero(f):
    c=blank(); floor(c); clawd(c,"up"); soup_pot(c,f); steam(c,[30],f)
    top = 6 if f==0 else 5
    left = 21 if f==0 else 22
    stamp(c,top,left,SHAKER)
    line(c,17,15,top+3,left-1)              # braço até o saleiro
    by=top+6
    grains=[(by,left+1),(by+2,left+3),(by+3,left),(by+5,left+2)] if f==0 else [(by+1,left+2),(by+2,left),(by+4,left+3),(by+5,left+1)]
    for r,x in grains: put(c,r,x,'g')
    return c
PLATE_FOOD=["...#####...",
            "..#wwwww#..",
            ".#wwwwwww#.",
            "###########",
            ".#########."]
def pronto(f):
    c=blank(); floor(c); clawd(c,"happy" if f else "right")
    top = 9 if f==0 else 7
    stamp(c,top,17,PLATE_FOOD)              # prato com comida
    line(c,17,15,top+4,17)                  # braço segurando o prato
    for k,x in enumerate((19,22,25)):       # vaporzinho do prato
        put(c,top-2-(k+f)%2,x,'g'); put(c,top-3-(k+f)%2,x+(1 if k%2 else -1),'g')
    if f==0: sparkle(c,6,30); sparkle(c,13,32,'g')
    else:    sparkle(c,4,31); sparkle(c,11,33); sparkle(c,2,24,'g')
    return c

BELL=["....#....",
      "...###...",
      "..#www#..",
      ".#wwwww#.",
      ".#######.",
      "#########"]
Q=["###","..#",".##","...",".#."]
EXC=[".#.",".#.",".#.","...",".#."]
def bubble(c,top,left,glyph):
    w,h=9,7
    hline(c,top,left+1,left+w-2); hline(c,top+h-1,left+1,left+w-2)
    for r in range(top+1,top+h-1): put(c,r,left); put(c,r,left+w-1)
    put(c,top+h,left+1); put(c,top+h+1,left)          # rabinho apontando pro Claudinho
    stamp(c,top+1,left+3,glyph)
def esperando(f):
    c=blank(); floor(c); counter(c)
    clawd(c,"open","a" if f==0 else "b")
    stamp(c,13,22,BELL)
    if f==0:
        line(c,17,15,10,21)                             # mão no alto
        bubble(c,0,15,Q)
    else:
        line(c,17,15,12,22); put(c,12,23)               # mão batendo no sino
        for r,x in [(12,19),(11,18),(12,29),(11,30),(10,26),(9,27)]: put(c,r,x,'g')   # "ding"
        bubble(c,0,15,EXC)
    return c
MUG=[".####.","#wwww##","#wwww#.#","#wwww##",".####."]
MUG=["#####..","#www###","#www#.#","#www###","#####.."]
Z_BIG=["####","..#.",".#..","####"]
Z_SM=["###",".#.","###"]
def descansando(f):
    c=blank(); floor(c)
    rows=[".############.",".############.",".############.",".##..####..##.","##############","##############",".############.",".############."]
    stamp(c,15,1,rows)                                 # sentado, olhos fechados
    stamp(c,9,2,HAT)
    stamp(c,18,19,MUG)                                 # cafezinho
    wave=[0,1,1,0]
    for h in range(4):
        if (h+f)%4!=3: put(c,17-h,21+wave[(h+f*2)%4],'g')
    if f==0:
        stamp(c,6,15,Z_SM,('#',)); stamp(c,3,18,Z_BIG,('#',))
    else:
        stamp(c,5,16,Z_SM,('#',)); stamp(c,1,20,Z_BIG,('#',)); put(c,8,14,'g'); put(c,8,15,'g')
    return c

SCENES={"sopa":[sopa(0),sopa(1)],"cebola":[cebola(0),cebola(1)],
        "frigideira":[frigideira(0),frigideira(1)],
        "tempero":[tempero(0),tempero(1)],"pronto":[pronto(0),pronto(1)],
        "esperando":[esperando(0),esperando(1)],"descansando":[descansando(0),descansando(1)]}
def rows(c): return ["".join(r) for r in c]
def svg(c,u,black="#000",gray="#888"):
    R=rows(c)
    def path(ch):
        out=[]
        for y,r in enumerate(R):
            x=0
            while x<len(r):
                if r[x]==ch:
                    s=x
                    while x<len(r) and r[x]==ch: x+=1
                    out.append(f'M{s*u} {y*u}h{(x-s)*u}v{u}h-{(x-s)*u}z')
                else: x+=1
        return "".join(out)
    w=W*u; h=H*u; g=path('g'); b=path('#')
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg">'
            +(f'<path fill="{gray}" d="{g}"/>' if g else '')+f'<path fill="{black}" d="{b}"/></svg>')
if __name__=="__main__":
    import sys
    for name,fr in SCENES.items():
        if len(sys.argv)>1 and name not in sys.argv[1:]: continue
        for i,c in enumerate(fr):
            print(f"--- {name} {i}"); print("\n".join(rows(c)))
