#!/bin/sh
# Name: Claude Dash
# Author: Guilherme
# DontUseFBInk

# >>> Troque pelo IP do seu Mac (no Mac: ipconfig getifaddr en0)
MAC="IP_DO_MAC"
PORT=8787

POLL=30          # segundos entre leituras do estado (textos e numeros)
FULL_EVERY=10    # trocas de tela parciais antes de um refresh completo (limpa fantasma)

BASE="http://$MAC:$PORT"
DIR=/tmp/claude_dash
PIDFILE=$DIR/pid
LOG=/mnt/us/claude_dash_log.txt   # aparece na raiz do Kindle quando liga no cabo

mkdir -p "$DIR"

# ja esta rodando? nao abre outro
if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  exit 0
fi

lipc-set-prop com.lab126.cmd wirelessEnable 1 2>/dev/null
lipc-set-prop com.lab126.powerd preventScreenSaver 1 2>/dev/null

log() {
  echo "$(date '+%H:%M:%S') $*" >> "$LOG"
  [ "$(wc -l < "$LOG")" -gt 300 ] && tail -n 150 "$LOG" > "$LOG.tmp" && mv "$LOG.tmp" "$LOG"
}

field() {  # valor de uma linha "chave valor" do status
  grep "^$1 " "$DIR/status.txt" | head -n 1 | cut -d' ' -f2-
}

pause_ms() {
  if command -v usleep >/dev/null 2>&1; then
    usleep $(( $1 * 1000 ))
  else
    sleep $(( ($1 + 500) / 1000 ))
  fi
}

stop_dash() {
  log "parando"
  rm -f "$PIDFILE"
  lipc-set-prop com.lab126.powerd preventScreenSaver 0 2>/dev/null
  lipc-set-prop com.lab126.appmgrd start app://com.lab126.booklet.home 2>/dev/null
  eips -c 2>/dev/null
  exit 0
}

loop() {
  sleep 3
  last_poll=0
  screen_hash=""
  anim=""
  frames=""
  delay_ms=1500
  frame_i=0
  partials=0
  fails=0
  log "iniciando em $BASE (usleep: $(command -v usleep || echo nao))"

  while true; do
    now=$(date +%s)

    # ---- a cada POLL segundos: le o estado e baixa as telas se mudou
    if [ $((now - last_poll)) -ge "$POLL" ]; then
      last_poll=$now
      if curl -s -f -m 10 -o "$DIR/status.txt" "$BASE/status.txt"; then
        fails=0
        grep -q '^stop' "$DIR/status.txt" && stop_dash
        new_hash=$(field screen)
        new_anim=$(field anim)
        new_frames=$(field frames)
        delay_ms=$(field delay_ms)

        if [ "$new_hash" != "$screen_hash" ]; then
          ok=1
          got=" "
          for f in $new_frames; do
            case "$got" in *" $f "*) continue ;; esac   # a sequencia repete quadros
            got="$got$f "
            if curl -s -f -m 15 -o "$DIR/new_$f.png" "$BASE/screen/$f.png"; then
              mv "$DIR/new_$f.png" "$DIR/s_$f.png"
            else
              ok=0
              log "falhou tela $f"
            fi
          done
          if [ "$ok" -eq 1 ]; then
            first=$(echo $new_frames | cut -d' ' -f1)
            if [ -z "$screen_hash" ] || [ "$new_anim" != "$anim" ] || [ "$partials" -ge "$FULL_EVERY" ]; then
              eips -f -g "$DIR/s_$first.png" >/dev/null 2>&1   # mudou o estado: refresh completo
              partials=0
              [ "$new_anim" != "$anim" ] && log "estado: $new_anim ($new_frames)"
            else
              eips -g "$DIR/s_$first.png" >/dev/null 2>&1
              partials=$((partials + 1))
            fi
            screen_hash=$new_hash
            frames=$new_frames
            anim=$new_anim
            frame_i=1                        # a tela ja mostra o quadro 1
          fi
        fi
      else
        fails=$((fails + 1))
        log "sem resposta do Mac ($fails)"
        if [ "$fails" -eq 3 ]; then
          eips 1 1 " sem conexao com o Mac... "
          screen_hash=""
        fi
      fi
    fi

    # ---- animacao: alterna entre as telas de cada quadro
    #      (so o mascote muda entre elas, entao so ele se mexe no e-ink)
    n=$(echo $frames | wc -w)
    if [ "$n" -gt 1 ] && [ -n "$screen_hash" ]; then
      f=$(echo $frames | cut -d' ' -f$(( frame_i % n + 1 )))
      [ -s "$DIR/s_$f.png" ] && eips -g "$DIR/s_$f.png" >/dev/null 2>&1
      frame_i=$((frame_i + 1))
    fi

    pause_ms "${delay_ms:-1500}"
  done
}

loop </dev/null >/dev/null 2>&1 &
echo $! > "$PIDFILE"
