#!/usr/bin/env python3
"""Servidor do painel "Claudinho chef" para o Kindle.

Monta a tela 800x600 do design do Paper com os dados reais do Claude Code e
serve para o Kindle (girada para a tela dele, que e 600x800 em pe).

    python3 server.py

Rotas:
    /preview.png            a tela como voce ve (deitada). ?demo=<modo> para exemplo
    /status.txt             o que o Kindle le a cada ~30s (tela atual + animacao)
    /screen.png             a tela girada para o Kindle
    /sprite/<quadro>.png    um quadro do mascote, girado
    /parar                  manda o Kindle sair do painel

Modos de demo: sopa, cebola, tempero, frigideira, prato, esperando, descansando
"""
import glob
import hashlib
import io
import json
import os
import random
import sys
import threading
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
STATE = os.path.join(DATA, "state.json")
STATUS = os.path.join(DATA, "statusline.json")
PROJECTS = os.path.expanduser("~/.claude/projects")
PORT = int(os.environ.get("KINDLE_DASH_PORT", "8787"))
# Kindle deitado com o logo "kindle" a esquerda = 90; logo a direita = 270
ROTATE = int(os.environ.get("KINDLE_DASH_ROTATE", "90"))

W, H = 800, 600
C_BLACK, C_444, C_888, C_AAA, C_D0, C_WHITE = 0, 0x44, 0x88, 0xAA, 0xD0, 0xFF

# Regiao do mascote (alinhada a 8px) e posicao do desenho dentro dela
REGION = (40, 120, 224, 152)          # x, y, w, h na tela deitada
SPRITE_POS = (42, 127)                 # canto do desenho 216x144
CELL = 6                               # 36x24 celulas de 6px

# Tempo de cada animacao (segundos por quadro)
ANIMS = {
    "sopa": 1.5, "cebola": 1.5, "tempero": 1.5, "frigideira": 1.5,
    "prato": 1.5, "esperando": 1.5, "chamando": 1.0, "descansando": 4.0,
    "cozinhando": 1.5,
}
# blocos sorteados enquanto o Claude trabalha (cada bloco = quadro 1, quadro 2)
COOKING = ["sopa", "cebola", "tempero", "frigideira"]
COOKING_BLOCKS = 10        # 10 blocos x 2 quadros x 1,5s = 30s, um ciclo por leitura do Kindle
TOOL_ANIM = {
    "Edit": "sopa", "Write": "sopa", "MultiEdit": "sopa", "NotebookEdit": "sopa",
    "Bash": "cebola", "BashOutput": "cebola", "KillShell": "cebola", "KillBash": "cebola",
    "Read": "tempero", "Grep": "tempero", "Glob": "tempero", "LS": "tempero",
    "WebFetch": "tempero", "WebSearch": "tempero",
}
PRATO_SECONDS = 60          # quanto tempo o "prato pronto" fica depois de terminar
REST_AFTER = 30 * 60        # parado ha mais que isso = descansando
TOOL_LINGER = 45           # animacao da ferramenta continua esse tempo depois de usada
TOOL_STALE = 10 * 60       # ferramenta "rodando" ha mais que isso: considera encerrada
WEEKDAYS = ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"]

# ------------------------------------------------------------------ fontes

FONT_FILES = {
    "inter": [os.path.join(BASE, "fonts", "InterTight.ttf")],
    "mono": [os.path.join(BASE, "fonts", "JetBrainsMono.ttf")],
}
FALLBACK = {
    "inter": ["/System/Library/Fonts/Supplemental/Arial Black.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"],
    "mono": ["/System/Library/Fonts/Menlo.ttc",
             "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"],
}
_fonts = {}


def font(family, size, weight=400):
    key = (family, size, weight)
    if key in _fonts:
        return _fonts[key]
    f = None
    for path in FONT_FILES[family]:
        if os.path.exists(path):
            f = ImageFont.truetype(path, size)
            try:
                axis = f.get_variation_axes()[0]
                f.set_variation_by_axes([max(axis["minimum"], min(axis["maximum"], weight))])
            except Exception:
                pass
            break
    if f is None:
        for path in FALLBACK[family]:
            if os.path.exists(path):
                f = ImageFont.truetype(path, size)
                break
    _fonts[key] = f or ImageFont.load_default(size)
    return _fonts[key]


def text_width(txt, fnt, ls=0.0):
    if not txt:
        return 0.0
    return fnt.getlength(txt) + ls * len(txt)


def draw_text(d, x, top, txt, fnt, fill, line_h, ls=0.0, align="left"):
    """Desenha como o CSS do Paper: caixa de linha `line_h`, letter-spacing `ls` px."""
    if not txt:
        return 0
    w = text_width(txt, fnt, ls)
    if align == "right":
        x -= w
    elif align == "center":
        x -= w / 2
    asc, desc = fnt.getmetrics()
    baseline = top + (line_h - (asc + desc)) / 2 + asc
    if not ls:
        d.text((x, baseline), txt, font=fnt, fill=fill, anchor="ls")
        return w
    for i, ch in enumerate(txt):
        # posicao com kerning: largura do prefixo (incluindo o char) menos o avanco dele
        cx = x + fnt.getlength(txt[: i + 1]) - fnt.getlength(ch) + ls * i
        d.text((cx, baseline), ch, font=fnt, fill=fill, anchor="ls")
    return w


def fit(txt, fnt, max_w, ls=0.0):
    if text_width(txt, fnt, ls) <= max_w:
        return txt
    while txt and text_width(txt + "…", fnt, ls) > max_w:
        txt = txt[:-1]
    return txt.rstrip() + "…"


# ------------------------------------------------------------------ sprites

with open(os.path.join(BASE, "sprites.json"), encoding="utf-8") as _f:
    SPRITES = json.load(_f)
FRAMES = {a: sorted(k for k in SPRITES if k.rsplit("_", 1)[0] == a) for a in ANIMS}
FRAMES["chamando"] = FRAMES["esperando"]   # pedido de permissao: mesmo sino, mais rapido
FRAMES["cozinhando"] = FRAMES["sopa"]      # quadro da tela parada (preview); no Kindle e sorteado


def frame_sequence(mode):
    """A ordem dos quadros que o Kindle vai mostrar ate a proxima leitura."""
    if mode != "cozinhando":
        return FRAMES[mode]
    seq, last = [], None
    for _ in range(COOKING_BLOCKS):
        block = random.choice([b for b in COOKING if b != last])
        seq += FRAMES[block]                  # sempre _1 e depois _2
        last = block
    return seq


def sprite_image(name):
    """Quadro 216x144 em celulas de 6px: traco branco, cinza #888, fundo preto."""
    grid = SPRITES[name]
    img = Image.new("L", (len(grid[0]) * CELL, len(grid) * CELL), C_BLACK)
    d = ImageDraw.Draw(img)
    for y, row in enumerate(grid):
        for x, ch in enumerate(row):
            if ch != ".":
                d.rectangle((x * CELL, y * CELL, (x + 1) * CELL - 1, (y + 1) * CELL - 1),
                            fill=C_WHITE if ch == "#" else C_888)
    return img


def region_image(name):
    """A regiao alinhada do mascote, pronta para o eips desenhar por cima."""
    rx, ry, rw, rh = REGION
    img = Image.new("L", (rw, rh), C_BLACK)
    img.paste(sprite_image(name), (SPRITE_POS[0] - rx, SPRITE_POS[1] - ry))
    return img


def rotate(img):
    if ROTATE == 90:
        return img.transpose(Image.Transpose.ROTATE_90)
    if ROTATE == 270:
        return img.transpose(Image.Transpose.ROTATE_270)
    return img


def region_on_kindle():
    """Onde a regiao do mascote cai na tela do Kindle (em pe)."""
    rx, ry, rw, rh = REGION
    if ROTATE == 90:
        return ry, W - rx - rw
    if ROTATE == 270:
        return H - ry - rh, rx
    return rx, ry


def png(img):
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


# ------------------------------------------------------------------ dados

def read_json(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


_tok_cache = {}


def token_stats():
    """(hoje, ultima hora, media por dia nos 7 dias anteriores com uso)."""
    now = datetime.now().astimezone()
    today = now.date()
    hour_ago = now - timedelta(hours=1)
    cutoff = time.time() - 8 * 86400
    seen, per_day, last_hour = set(), {}, 0
    for path in glob.glob(os.path.join(PROJECTS, "**", "*.jsonl"), recursive=True):
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue
        if mtime < cutoff:
            continue
        cached = _tok_cache.get(path)
        if not cached or cached[0] != mtime:
            entries = {}
            with open(path, encoding="utf-8", errors="ignore") as f:
                for n, line in enumerate(f):
                    if '"usage"' not in line:
                        continue
                    try:
                        d = json.loads(line)
                        msg = d.get("message") or {}
                        usage = msg.get("usage")
                        if not usage:
                            continue
                        dt = datetime.fromisoformat(
                            d["timestamp"].replace("Z", "+00:00")).astimezone()
                    except Exception:
                        continue
                    key = f'{msg.get("id")}|{d.get("requestId")}'
                    if key == "None|None":
                        key = f"{path}:{n}"
                    tokens = sum(int(usage.get(k) or 0) for k in (
                        "input_tokens", "output_tokens",
                        "cache_creation_input_tokens", "cache_read_input_tokens"))
                    entries[key] = (dt, tokens)
            cached = (mtime, entries)
            _tok_cache[path] = cached
        for key, (dt, tokens) in cached[1].items():
            if key in seen:
                continue
            seen.add(key)
            per_day[dt.date()] = per_day.get(dt.date(), 0) + tokens
            if dt >= hour_ago:
                last_hour += tokens
    past = [v for day, v in per_day.items() if today - timedelta(days=7) <= day < today]
    avg = sum(past) / len(past) if past else None
    return per_day.get(today, 0), last_hour, avg


def session_view(s, now):
    """(prioridade, modo, desde, ferramenta, descricao) de uma sessao."""
    last = float(s.get("last_event") or 0)
    status = s.get("status")
    if status == "waiting":
        since = float(s.get("waiting_since") or last)
        asked_tool = now - float(s.get("tool_started") or 0) < 120
        if asked_tool and s.get("tool_name"):
            return 5, "chamando", since, s["tool_name"], s.get("tool_desc", "")
        return 5, "chamando", since, "", "esperando sua resposta"
    if status == "working":
        started = float(s.get("tool_started") or 0)
        # ferramentas costumam durar menos de 1s e o Kindle olha a cada 30s:
        # a animacao da ultima ferramenta continua por TOOL_LINGER segundos
        recent = now - started < TOOL_LINGER
        # a animacao e sempre "cozinhando" (blocos aleatorios); a barra mostra a ferramenta
        if (s.get("tool_running") and now - started < TOOL_STALE) or recent:
            return 4, "cozinhando", last, s.get("tool_name", ""), s.get("tool_desc", "")
        return 3, "cozinhando", last, "", "pensando…"
    if status == "done":
        done_at = float(s.get("done_at") or last)
        if now - done_at < PRATO_SECONDS:
            return 2, "prato", done_at, "", "nada no fogo"
        return 1, "esperando", done_at, "", "nada no fogo"
    return 0, "descansando", last, "", "nada no fogo"


def derive(state, now):
    """Junta todas as sessoes (agentes do Orca, terminais) numa tela so:
    mostra a mais importante e conta quantas estao ativas."""
    sessions = state.get("sessions") or {}
    live = [s for s in sessions.values()
            if s.get("status") != "closed" and now - float(s.get("last_event") or 0) < REST_AFTER]
    views = [(session_view(s, now), s) for s in live]
    active = sum(1 for v, _ in views if v[0] >= 3)
    if not views:
        last = max([float(s.get("last_event") or 0) for s in sessions.values()] or
                   [float(state.get("last_event") or 0)])
        return {"mode": "descansando", "since": last, "tool": "", "desc": "nada no fogo",
                "active": 0, "project": ""}
    (rank, mode, since, tool, desc), s = max(
        views, key=lambda vs: (vs[0][0], float(vs[1].get("last_event") or 0)))
    return {"mode": mode, "since": since, "tool": tool, "desc": desc,
            "active": active, "project": s.get("project", "")}


def demo(mode):
    now = time.time()
    tools = ["Read", "Grep", "Bash", "mcp:notion", "Edit"]
    descs = ["server.py", "rate_limits", "Rodar os testes", "notion-search", "DashboardController.java"]
    names = {"sopa": "Edit", "cebola": "Bash", "tempero": "Grep"}
    tool = names.get(mode, "Edit")
    tdesc = {"Edit": "DashboardController.java", "Bash": "mvn test -pl api",
             "Grep": "rate_limits"}[tool]
    s = {"status": "working", "last_event": now - 7, "tool_running": True,
         "tool_started": now - 2, "tool_name": tool, "tool_desc": tdesc, "project": "camaleao"}
    state = {"sessions": {"demo": s},
             "tools": [{"name": a, "desc": b} for a, b in zip(tools, descs)]}
    if mode in names:
        state["tools"][-1] = {"name": tool, "desc": tdesc}
    elif mode == "frigideira":
        s["tool_running"] = False
    elif mode == "chamando":
        s.update(status="waiting", waiting_since=now - 40, last_event=now - 40, tool_started=now - 45)
    elif mode == "prato":
        s.update(status="done", done_at=now - 12, last_event=now - 12)
    elif mode == "esperando":
        s.update(status="done", done_at=now - 125, last_event=now - 125)
    elif mode == "descansando":
        s.update(status="done", done_at=now - 2700, last_event=now - 2700)
    elif mode == "varios":
        state["sessions"].update({
            "b": {"status": "working", "last_event": now - 20, "project": "kindle-dash"},
            "c": {"status": "working", "last_event": now - 3, "project": "orca-api"}})
    status = {"rate_limits": {
        "five_hour": {"used_percentage": 11, "resets_at": now + 3 * 3600},
        "seven_day": {"used_percentage": 19, "resets_at": now + 3 * 86400}}}
    return state, status, (2_480_000, 420_000, 1_830_000)


# ------------------------------------------------------------------ texto

def fmt_tokens(n):
    if n is None:
        return "--"
    if n >= 100_000:
        return f"{n / 1_000_000:.1f}".replace(".", ",") + " mi"
    if n >= 1_000:
        return f"{n / 1_000:.0f} mil"
    return str(int(n))


def fmt_ago(seconds):
    s = int(max(0, seconds))
    if s < 60:
        return f"{s}s"
    if s < 3600:
        return f"{s // 60} min"
    h, m = divmod(s // 60, 60)
    return f"{h} h" if not m or h >= 3 else f"{h} h {m} min"


def fmt_reset(epoch, week):
    try:
        dt = datetime.fromtimestamp(float(epoch))
    except Exception:
        return ""
    return f"zera {WEEKDAYS[dt.weekday()]} {dt:%H:%M}" if week else f"zera às {dt:%H:%M}"


# ------------------------------------------------------------------ desenho

def asterisk(d, cx, cy, r, fill):
    """O ✳ do status (a fonte nao tem esse simbolo)."""
    k = r * 0.7071
    for (x0, y0, x1, y1) in [(cx - r, cy, cx + r, cy), (cx, cy - r, cx, cy + r),
                             (cx - k, cy - k, cx + k, cy + k), (cx - k, cy + k, cx + k, cy - k)]:
        d.line((x0, y0, x1, y1), fill=fill, width=2)


def ring(img, x, y, pct):
    """Anel de 24 segmentos, 170x170, igual ao do Paper (desenhado em 4x e reduzido)."""
    s = 4
    big = Image.new("L", (170 * s, 170 * s), C_WHITE)
    d = ImageDraw.Draw(big)
    filled = 0 if pct is None else max(1 if pct > 0 else 0, min(24, round(pct * 24 / 100)))
    box = (0, 0, 170 * s - 1, 170 * s - 1)
    for i in range(24):
        start = -90 + 15 * i + 2.04
        d.arc(box, start, start + 10.92, fill=C_BLACK if i < filled else C_D0, width=18 * s)
    img.paste(big.resize((170, 170), Image.Resampling.LANCZOS), (x, y))


def render(mode=None, demo_mode=None):
    now = time.time()
    if demo_mode:
        state, status, (tok_today, tok_hour, tok_avg) = demo(demo_mode)
    else:
        state, status = read_json(STATE), read_json(STATUS)
        try:
            tok_today, tok_hour, tok_avg = token_stats()
        except Exception:
            tok_today, tok_hour, tok_avg = 0, 0, None
    info = derive(state, now)
    mode, since = info["mode"], info["since"]

    img = Image.new("L", (W, H), C_WHITE)
    d = ImageDraw.Draw(img)
    fake = os.environ.get("KINDLE_DASH_FAKE_TIME")  # so para testes: "2026-10-21 13:12"
    dt = datetime.strptime(fake, "%Y-%m-%d %H:%M") if fake else datetime.now()

    # ---- painel do mascote (preto)
    d.rectangle((0, 0, 299, H - 1), fill=C_BLACK)
    mono13 = font("mono", 13)
    draw_text(d, 30, 30, "CLAUDE CODE", font("mono", 13, 700), C_WHITE, 16, ls=13 * 0.14)
    draw_text(d, 270, 30, f"{WEEKDAYS[dt.weekday()]} {dt:%d/%m}", mono13, C_AAA, 16, align="right")

    frame = FRAMES[mode][0]
    img.paste(sprite_image(frame), SPRITE_POS)

    estado, ultima = {
        "descansando": ("Fogão desligado", "última ação há {}"),
        "esperando": ("Tá pronto!", "esperando você há {}"),
        "chamando": ("Te chamando!", "esperando você há {}"),
        "prato": ("Prato pronto!", "terminou há {}"),
    }.get(mode, ("Cozinhando…", "última ação há {}"))
    asterisk(d, 40.5, 368, 10, C_WHITE)
    inter28 = font("inter", 28, 800)
    draw_text(d, 59, 351, fit(estado, inter28, 240, -0.56), inter28, C_WHITE, 32, ls=-0.56)
    ago = fmt_ago(now - since) if since else "--"
    line = ultima.format(ago)
    if info["active"] > 1:
        line += f" · {info['active']} no fogo"
    draw_text(d, 30, 389, fit(line, mono13, 240), mono13, C_AAA, 16)
    draw_text(d, 30, 486, f"{dt:%H:%M}", font("inter", 92, 900), C_WHITE, 84, ls=-4.6)

    # ---- painel de dados (branco)
    draw_text(d, 330, 30, "NO FOGO AGORA", font("mono", 12, 700), C_444, 16, ls=12 * 0.16)
    d.rectangle((330, 54, 769, 89), fill=C_BLACK)
    tools = state.get("tools") or []
    mono15b, mono15 = font("mono", 15, 700), font("mono", 15)
    draw_text(d, 342, 63, "▶", mono15b, C_WHITE, 18)
    x = 364
    if info["tool"]:
        x += draw_text(d, x, 63, fit(info["tool"], mono15b, 200), mono15b, C_WHITE, 18) + 10
    desc = info["desc"]
    if info["active"] > 1 and info["project"] and info["tool"]:
        desc = f"{desc} · {info['project']}"     # varios agentes: diz de qual projeto e
    draw_text(d, x, 63, fit(desc, mono15, 758 - x), mono15, C_WHITE, 18)

    draw_text(d, 342, 98, "antes:", mono13, C_888, 16)
    # as ferramentas anteriores (sem repetir a que esta na barra agora)
    past = tools[:-1] if info["tool"] and tools else tools
    before = " · ".join(t.get("name", "?") for t in reversed(past[-4:])) or "nada ainda"
    draw_text(d, 399, 98, fit(before, mono13, 770 - 399), mono13, C_888, 16)

    rl = status.get("rate_limits") or {}
    for cx, key, label, week in ((434, "five_hour", "SESSÃO", False),
                                 (666, "seven_day", "SEMANA", True)):
        info = rl.get(key) or {}
        pct = info.get("used_percentage")
        ring(img, cx - 85, 200, pct)
        txt = "--" if pct is None else f"{pct:.0f}%"
        draw_text(d, cx, 252, txt, font("inter", 52, 900), C_BLACK, 50, ls=-2.08, align="center")
        draw_text(d, cx, 304, label, font("mono", 11, 700), C_444, 14, ls=11 * 0.16, align="center")
        draw_text(d, cx, 380, fmt_reset(info.get("resets_at"), week), mono13, C_444, 16, align="center")

    d.rectangle((330, 483, 769, 485), fill=C_BLACK)
    draw_text(d, 330, 504, "TOKENS HOJE", font("mono", 12, 700), C_444, 16, ls=12 * 0.16)
    draw_text(d, 330, 524, fmt_tokens(tok_today), font("inter", 48, 900), C_BLACK, 46, ls=-1.92)
    hour_txt = f"{fmt_tokens(tok_hour)} na última hora"
    w = draw_text(d, 770, 534, hour_txt, mono13, C_444, 16, align="right")
    draw_text(d, 770 - w - 6, 534, "▲", mono13, C_444, 16, align="right")
    draw_text(d, 770, 554, f"média {fmt_tokens(tok_avg)}/dia", mono13, C_444, 16, align="right")

    return img, mode


# ------------------------------------------------------------------ http

class Dash:
    """Guarda a ultima tela gerada para /status.txt e /screen.png baterem."""
    lock = threading.Lock()
    screen = b""
    screens = {}
    stop = False


def status_txt():
    img, mode = render()
    data = png(rotate(img))
    # uma tela inteira para cada quadro da animacao (o Kindle alterna entre elas)
    seq = frame_sequence(mode)
    screens = {}
    for name in dict.fromkeys(seq):           # uma tela por quadro diferente
        frame_img = img.copy()
        frame_img.paste(sprite_image(name), SPRITE_POS)
        screens[name] = png(rotate(frame_img))
    with Dash.lock:
        Dash.screen = data
        Dash.screens = screens
    kx, ky = region_on_kindle()
    lines = [
        f"screen {hashlib.md5(data).hexdigest()}",
        f"anim {mode}",
        f"frames {' '.join(seq)}",
        f"delay_ms {int(ANIMS[mode] * 1000)}",
        f"x {kx}",
        f"y {ky}",
    ]
    return ("\n".join(lines) + "\n").encode()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        try:
            if url.path == "/parar":
                Dash.stop = True
                return self.reply(200, "Ok! O Kindle sai do painel na próxima atualização.\n"
                                  .encode(), "text/plain; charset=utf-8")
            if url.path == "/status.txt":
                if Dash.stop:
                    Dash.stop = False
                    return self.reply(200, b"stop\n", "text/plain")
                return self.reply(200, status_txt(), "text/plain")
            if url.path == "/screen.png":
                with Dash.lock:
                    data = Dash.screen
                if not data:
                    data = png(rotate(render()[0]))
                return self.reply(200, data, "image/png")
            if url.path.startswith("/screen/") and url.path.endswith(".png"):
                name = url.path[len("/screen/"):-4]
                with Dash.lock:
                    data = Dash.screens.get(name)
                if data is None:
                    return self.reply(404, b"quadro fora da animacao atual", "text/plain")
                return self.reply(200, data, "image/png")
            if url.path.startswith("/sprite/") and url.path.endswith(".png"):
                name = url.path[len("/sprite/"):-4]
                if name not in SPRITES:
                    return self.reply(404, b"quadro desconhecido", "text/plain")
                return self.reply(200, png(rotate(region_image(name))), "image/png")
            if url.path in ("/", "/preview.png"):
                img, _ = render(demo_mode=(q.get("demo") or [None])[0])
                return self.reply(200, png(img), "image/png")
        except Exception as e:
            return self.reply(500, f"erro: {e}".encode(), "text/plain; charset=utf-8")
        self.reply(404, b"nao encontrado", "text/plain")

    def reply(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


def main():
    args = sys.argv[1:]
    if args and args[0] == "--render":
        out = args[1]
        mode = args[2] if len(args) > 2 else None
        img, _ = render(demo_mode=mode)
        img.save(out)
        return
    if args and args[0] == "--sprites":
        out = args[1]
        os.makedirs(out, exist_ok=True)
        for name in SPRITES:
            region_image(name).save(os.path.join(out, f"{name}.png"))
        return
    os.makedirs(DATA, exist_ok=True)
    srv = ThreadingHTTPServer(("0.0.0.0", PORT), Handler)
    print(f"Painel no ar na porta {PORT}. Veja em http://localhost:{PORT}/preview.png")
    print("Ctrl+C para sair.")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
