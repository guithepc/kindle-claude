#!/usr/bin/env python3
"""statusLine do Claude Code: guarda os limites de uso (5h e semana) para o
painel do Kindle e imprime uma linha de status. Se voce ja tinha uma
statusLine antes, ela continua sendo usada."""
import json
import os
import subprocess
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
STATUS = os.path.join(DATA, "statusline.json")
ORIG = os.path.join(DATA, "orig_statusline.txt")


def main():
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except Exception:
        data = {}

    try:
        os.makedirs(DATA, exist_ok=True)
        try:
            with open(STATUS, encoding="utf-8") as f:
                old = json.load(f)
        except Exception:
            old = {}
        # rate_limits so aparece depois da primeira resposta: mantem o anterior
        if not data.get("rate_limits") and old.get("rate_limits"):
            data["rate_limits"] = old["rate_limits"]
        data["saved_at"] = time.time()
        tmp = STATUS + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, STATUS)
    except Exception:
        pass

    if os.path.exists(ORIG):
        cmd = open(ORIG, encoding="utf-8").read().strip()
        if cmd:
            try:
                out = subprocess.run(cmd, shell=True, input=raw, text=True,
                                     capture_output=True, timeout=5).stdout
                sys.stdout.write(out)
                return
            except Exception:
                pass

    model = (data.get("model") or {}).get("display_name", "Claude")
    rl = data.get("rate_limits") or {}
    five = (rl.get("five_hour") or {}).get("used_percentage")
    week = (rl.get("seven_day") or {}).get("used_percentage")
    parts = [model]
    if five is not None:
        parts.append(f"5h {five:.0f}%")
    if week is not None:
        parts.append(f"semana {week:.0f}%")
    print(" | ".join(parts))


if __name__ == "__main__":
    main()
