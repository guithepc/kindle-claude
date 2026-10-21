#!/usr/bin/env python3
"""Hook do Claude Code: registra o que cada sessao (cada agente do Orca,
cada terminal) esta fazendo, para o painel do Kindle.
So usa a biblioteca padrao e nunca falha nem imprime nada.

Eventos usados:
  UserPromptSubmit -> cozinhando (sem ferramenta = pensando / frigideira)
  PreToolUse       -> ferramenta rodando (sopa / cebola / tempero)
  PostToolUse      -> ferramenta terminou
  Notification     -> precisa de voce (esperando)
  Stop             -> terminou (prato pronto, depois esperando)
  SessionEnd       -> sessao fechada
"""
import fcntl
import json
import os
import sys
import time

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
STATE = os.path.join(DATA, "state.json")
LOCK = os.path.join(DATA, "state.lock")
MAX_TOOLS = 12
FORGET_AFTER = 6 * 3600   # sessoes paradas ha mais que isso saem do arquivo


def short_desc(tool, inp):
    if not isinstance(inp, dict):
        return ""
    if tool == "Bash":
        return inp.get("description") or (inp.get("command") or "").split("\n")[0]
    for key in ("file_path", "notebook_path", "path"):
        if inp.get(key):
            return os.path.basename(str(inp[key]).rstrip("/")) or str(inp[key])
    for key in ("pattern", "query", "url", "description", "prompt", "subject"):
        if inp.get(key):
            return str(inp[key]).split("\n")[0]
    return ""


def display_name(tool):
    if tool.startswith("mcp__"):
        parts = tool.split("__")
        return "mcp:" + (parts[1] if len(parts) > 1 else "?"), (parts[2] if len(parts) > 2 else "")
    return tool, ""


def update(state, event, now):
    name = event.get("hook_event_name", "")
    sid = event.get("session_id") or "sem-id"
    sessions = state.setdefault("sessions", {})
    s = sessions.setdefault(sid, {})
    cwd = event.get("cwd")
    if cwd:
        s["project"] = os.path.basename(cwd.rstrip("/")) or cwd

    if name == "PreToolUse":
        tool, fn = display_name(event.get("tool_name", "?"))
        desc = short_desc(event.get("tool_name", ""), event.get("tool_input"))
        if fn:
            desc = f"{fn} {desc}".strip()
        s.update(status="working", tool_running=True, tool_name=tool,
                 tool_desc=desc.strip(), tool_started=now)
        tools = state.setdefault("tools", [])
        tools.append({"name": tool, "desc": desc.strip(), "t": now, "session": sid})
        state["tools"] = tools[-MAX_TOOLS:]
    elif name == "PostToolUse":
        s.update(status="working", tool_running=False)
    elif name == "UserPromptSubmit":
        s.update(status="working", tool_running=False)
    elif name == "Notification":
        s.update(status="waiting", tool_running=False, waiting_since=now)
    elif name == "Stop":
        s.update(status="done", tool_running=False, done_at=now)
    elif name == "SessionEnd":
        s.update(status="closed", tool_running=False)
    else:
        return False

    s["last_event"] = now
    state["last_event"] = now
    for k in [k for k, v in sessions.items() if now - float(v.get("last_event") or 0) > FORGET_AFTER]:
        del sessions[k]
    return True


def main():
    try:
        event = json.load(sys.stdin)
    except Exception:
        return
    os.makedirs(DATA, exist_ok=True)
    # varios agentes podem chamar o hook ao mesmo tempo: trava o arquivo
    with open(LOCK, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            with open(STATE, encoding="utf-8") as f:
                state = json.load(f)
        except Exception:
            state = {}
        if "sessions" not in state:      # formato antigo: recomeca limpo
            state = {"tools": state.get("tools", [])}
        if not update(state, event, time.time()):
            return
        tmp = STATE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False)
        os.replace(tmp, STATE)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
