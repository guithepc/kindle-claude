#!/usr/bin/env python3
"""Converte os paths SVG dos quadros do Paper (retangulos num grid de 8px)
em grids de texto 36x24: '#' = traço (preto no Paper, branco na tela),
'+' = cinza, '.' = vazio. Gera ../sprites.json."""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
CELL, COLS, ROWS = 8, 36, 24
RECT = re.compile(r"M(-?\d+) (-?\d+)h(-?\d+)v(-?\d+)h-?\d+z")


def paint(grid, path, ch):
    for x, y, w, h in RECT.findall(path):
        x, y, w, h = map(int, (x, y, w, h))
        for gy in range(y // CELL, (y + h) // CELL):
            for gx in range(x // CELL, (x + w) // CELL):
                grid[gy][gx] = ch
    leftover = RECT.sub("", path).strip()
    if leftover:
        sys.exit(f"path com formato inesperado: {leftover[:60]}")


def main():
    with open(os.path.join(HERE, "sprites_src.json"), encoding="utf-8") as f:
        src = json.load(f)
    out = {}
    for name, (gray, black) in src.items():
        grid = [["."] * COLS for _ in range(ROWS)]
        paint(grid, gray, "+")
        paint(grid, black, "#")
        out[name] = ["".join(r) for r in grid]
    dest = os.path.join(HERE, "..", "sprites.json")
    with open(dest, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1)
    print(f"{len(out)} quadros -> {os.path.normpath(dest)}")


if __name__ == "__main__":
    main()
