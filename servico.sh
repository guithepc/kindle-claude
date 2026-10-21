#!/bin/sh
# Liga o servidor do painel como servico do macOS (launchd):
# sobe quando voce entra no Mac e reinicia sozinho se cair.
#
#   sh ~/kindle-dash/servico.sh            # instala e liga
#   sh ~/kindle-dash/servico.sh remover    # desliga e remove
#   sh ~/kindle-dash/servico.sh status     # mostra se esta rodando

LABEL="com.kindle-dash.server"
DIR="$(cd "$(dirname "$0")" && pwd)"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
PY="$(command -v python3)"
DOMAIN="gui/$(id -u)"

case "$1" in
  remover)
    launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null
    rm -f "$PLIST"
    echo "Servico removido. Para rodar na mao: python3 $DIR/server.py"
    exit 0
    ;;
  status)
    if launchctl print "$DOMAIN/$LABEL" >/dev/null 2>&1; then
      echo "Servico instalado."
      curl -s -o /dev/null -w "Servidor respondendo: HTTP %{http_code}\n" http://localhost:8787/status.txt
      echo "Log: $DIR/data/server.log"
    else
      echo "Servico nao instalado."
    fi
    exit 0
    ;;
esac

if [ -z "$PY" ]; then
  echo "Nao achei o python3."; exit 1
fi

# para qualquer servidor que esteja rodando na mao
lsof -ti :8787 | xargs kill 2>/dev/null

mkdir -p "$HOME/Library/LaunchAgents" "$DIR/data"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PY</string>
    <string>$DIR/server.py</string>
  </array>
  <key>WorkingDirectory</key><string>$DIR</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>10</integer>
  <key>StandardOutPath</key><string>$DIR/data/server.log</string>
  <key>StandardErrorPath</key><string>$DIR/data/server.log</string>
</dict>
</plist>
EOF

launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null
launchctl bootstrap "$DOMAIN" "$PLIST" || { echo "Nao consegui ligar o servico."; exit 1; }

sleep 2
if curl -s -o /dev/null http://localhost:8787/status.txt; then
  echo "Pronto! O servidor esta rodando em segundo plano e volta sozinho."
  echo "Pode fechar o Terminal."
else
  echo "Servico instalado, mas o servidor ainda nao respondeu."
  echo "Veja o log: $DIR/data/server.log"
fi
