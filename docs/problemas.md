# Problemas e soluções

## Encontrados no caminho

| Problema | O que resolveu |
|---|---|
| Kindle parado há anos não ligava | Bateria zerada. Deixar carregando por horas e fazer o reinício forçado (segurar o botão de ligar por 40 s). |
| Risco de atualização automática durante o jailbreak | Encher a memória até sobrarem ~50 MB com o Kindle-Filler-Disk, seguindo o guia de prevenção de updates do Kindle Modding. Depois do jailbreak as atualizações ficam bloqueadas e o enchimento pode ser apagado. |
| KUAL não aparece | É esperado. Nos jailbreaks atuais ele é obsoleto e os apps são scriptlets: arquivos `.sh` em `documents` aparecem na biblioteca e rodam ao tocar. |
| Mascote não animava | O desenho parcial por região não funcionou no aparelho. Trocado por alternância de telas inteiras. |
| Agentes em paralelo se misturavam num estado só | Cada sessão passou a ser acompanhada pelo `session_id`. |
| Barra "No fogo agora" parecia travada | Mostrava a última ferramenta mesmo minutos depois. Agora mostra a ferramenta atual, "pensando…" ou "nada no fogo". |
| Animação por ferramenta quase nunca aparecia | As ferramentas duram menos de 1 s e o Kindle olha a cada 30 s. Virou blocos sorteados enquanto o Claude trabalha. |
| Servidor morria ao fechar o Terminal | `servico.sh` registra um LaunchAgent no macOS (ainda não testado). |
| Kindle difícil de usar com o painel rodando | Ele desenha por cima de tudo. Hoje só sai pela rota `/parar` ou reiniciando. |

## Diagnóstico

- No Kindle, o script grava `claude_dash_log.txt` na raiz do armazenamento (visível pelo cabo).
- No computador:
  ```sh
  curl -s localhost:8787/status.txt   # o que o Kindle está recebendo
  cat data/state.json                 # o que os hooks gravaram
  ```
- Sessões abertas antes do `python3 setup.py` não mandam eventos até serem reiniciadas.
