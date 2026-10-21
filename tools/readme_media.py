#!/usr/bin/env python3
"""Gera as imagens do README a partir do proprio renderer (modos de demo).

    python3 tools/readme_media.py

Saida em docs/img/: painel.gif (capa), estados/*.png e sprites/*.gif.
"""
import os
import sys

os.environ.setdefault("KINDLE_DASH_FAKE_TIME", "2026-10-21 13:12")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from PIL import Image, ImageDraw  # noqa: E402

import server  # noqa: E402

OUT = os.path.join(ROOT, "docs", "img")


def screen(mode, frame):
    img, _ = server.render(demo_mode=mode)
    img.paste(server.sprite_image(frame), server.SPRITE_POS)
    return img


def bezel(img):
    """Moldura simples de Kindle em volta da tela 800x600."""
    pad_x, pad_top, pad_bottom = 64, 56, 56
    w, h = img.width + pad_x * 2, img.height + pad_top + pad_bottom
    out = Image.new("RGB", (w, h), (255, 255, 255))
    d = ImageDraw.Draw(out)
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=48, fill=(43, 43, 43), outline=(26, 26, 26), width=3)
    out.paste(img.convert("RGB"), (pad_x, pad_top))
    return out


def save_gif(path, frames, durations):
    frames = [f.convert("P", palette=Image.Palette.ADAPTIVE, colors=32) for f in frames]
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=durations,
                   loop=0, optimize=True, disposal=1)


def main():
    os.makedirs(os.path.join(OUT, "estados"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "sprites"), exist_ok=True)

    # capa: cozinhando em blocos, depois esperando e descansando
    seq = [("sopa", "sopa"), ("cebola", "cebola"), ("tempero", "tempero"),
           ("frigideira", "frigideira"), ("esperando", "esperando"), ("descansando", "descansando")]
    frames, durations = [], []
    for mode, anim in seq:
        reps = 2 if mode in ("esperando", "descansando") else 1
        for _ in range(reps):
            for name in server.FRAMES[anim]:
                frames.append(bezel(screen(mode, name)))
                durations.append(1400 if mode == "descansando" else 700)
    save_gif(os.path.join(OUT, "painel.gif"), frames, durations)

    for mode in ("sopa", "esperando", "descansando"):
        img, _ = server.render(demo_mode=mode)
        name = {"sopa": "trabalhando"}.get(mode, mode)
        img.save(os.path.join(OUT, "estados", f"{name}.png"), optimize=True)

    for anim in ("sopa", "cebola", "frigideira", "tempero", "prato", "esperando", "descansando"):
        fr = [server.sprite_image(n).resize((432, 288), Image.Resampling.NEAREST) for n in server.FRAMES[anim]]
        save_gif(os.path.join(OUT, "sprites", f"{anim}.gif"), fr, [int(server.ANIMS[anim] * 600)] * len(fr))
    print("ok:", OUT)


if __name__ == "__main__":
    main()
