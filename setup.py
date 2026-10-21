#!/usr/bin/env python3
"""Liga (ou desliga) os hooks e a statusLine do painel Kindle no
~/.claude/settings.json. Faz backup antes de mexer.

    python3 setup.py            # instala
    python3 setup.py remover    # desfaz
"""
import json
import os
import shutil
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
ORIG = os.path.join(DATA, "orig_statusline.txt")
SETTINGS = os.path.expanduser("~/.claude/settings.json")
PY = sys.executable or "python3"
HOOK_CMD = f'"{PY}" "{os.path.join(BASE, "hook.py")}"'
STATUS_CMD = f'"{PY}" "{os.path.join(BASE, "statusline.py")}"'
EVENTS = {"PreToolUse": "*", "PostToolUse": "*", "UserPromptSubmit": None,
          "Notification": None, "Stop": None, "SessionEnd": None}
MARK = "kindle-dash"


def is_ours(entry):
    return any(MARK in (h.get("command") or "") for h in entry.get("hooks", []))


def load():
    if not os.path.exists(SETTINGS):
        return {}
    with open(SETTINGS, encoding="utf-8") as f:
        return json.load(f)


def save(cfg):
    os.makedirs(os.path.dirname(SETTINGS), exist_ok=True)
    if os.path.exists(SETTINGS):
        bak = f"{SETTINGS}.bak-kindle-{int(time.time())}"
        shutil.copy2(SETTINGS, bak)
        print(f"Backup salvo em {bak}")
    with open(SETTINGS, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def install():
    cfg = load()
    hooks = cfg.setdefault("hooks", {})
    for event, matcher in EVENTS.items():
        lst = [e for e in hooks.get(event, []) if not is_ours(e)]
        entry = {"hooks": [{"type": "command", "command": HOOK_CMD}]}
        if matcher:
            entry["matcher"] = matcher
        lst.append(entry)
        hooks[event] = lst

    os.makedirs(DATA, exist_ok=True)
    current = (cfg.get("statusLine") or {}).get("command", "")
    if current and MARK not in current:
        with open(ORIG, "w", encoding="utf-8") as f:
            f.write(current)
        print("Sua statusLine antiga foi guardada e vai continuar aparecendo.")
    cfg["statusLine"] = {"type": "command", "command": STATUS_CMD}
    save(cfg)
    print("Pronto! Reinicie o Claude Code para os hooks comecarem a valer.")


def remove():
    cfg = load()
    hooks = cfg.get("hooks", {})
    for event in list(hooks):
        hooks[event] = [e for e in hooks[event] if not is_ours(e)]
        if not hooks[event]:
            del hooks[event]
    if not hooks:
        cfg.pop("hooks", None)
    if MARK in (cfg.get("statusLine") or {}).get("command", ""):
        if os.path.exists(ORIG):
            cfg["statusLine"] = {"type": "command",
                                 "command": open(ORIG, encoding="utf-8").read().strip()}
        else:
            cfg.pop("statusLine", None)
    save(cfg)
    print("Hooks do painel removidos.")


if __name__ == "__main__":
    remove() if len(sys.argv) > 1 and sys.argv[1] == "remover" else install()
