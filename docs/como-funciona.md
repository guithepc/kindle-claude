# Como funciona

## De onde vêm os dados

### Estado e ferramenta atual: hooks do Claude Code

`python3 setup.py` adiciona estes hooks ao `~/.claude/settings.json`, sem remover os que já existem, e faz backup antes:

```json
{
  "hooks": {
    "PreToolUse":       [{ "matcher": "*", "hooks": [{ "type": "command", "command": "\"<PYTHON3>\" \"<PASTA_DO_REPO>/hook.py\"" }] }],
    "PostToolUse":      [{ "matcher": "*", "hooks": [{ "type": "command", "command": "\"<PYTHON3>\" \"<PASTA_DO_REPO>/hook.py\"" }] }],
    "UserPromptSubmit": [{ "hooks": [{ "type": "command", "command": "\"<PYTHON3>\" \"<PASTA_DO_REPO>/hook.py\"" }] }],
    "Notification":     [{ "hooks": [{ "type": "command", "command": "\"<PYTHON3>\" \"<PASTA_DO_REPO>/hook.py\"" }] }],
    "Stop":             [{ "hooks": [{ "type": "command", "command": "\"<PYTHON3>\" \"<PASTA_DO_REPO>/hook.py\"" }] }],
    "SessionEnd":       [{ "hooks": [{ "type": "command", "command": "\"<PYTHON3>\" \"<PASTA_DO_REPO>/hook.py\"" }] }]
  },
  "statusLine": { "type": "command", "command": "\"<PYTHON3>\" \"<PASTA_DO_REPO>/statusline.py\"" }
}
```

- `hook.py` grava cada sessão separada, pelo `session_id`, em `data/state.json`. Uma trava de arquivo deixa vários agentes escreverem ao mesmo tempo.
- O servidor junta as sessões e mostra a mais urgente: pedindo permissão > trabalhando > terminou > descansando.
- Atualiza a cada evento do Claude Code.

### % da sessão e da semana: statusLine

O Claude Code manda pra statusLine um JSON com `rate_limits.five_hour` e `rate_limits.seven_day` (`used_percentage`, `resets_at`).

- `statusline.py` salva isso em `data/statusline.json` e continua exibindo a statusLine que você já tinha.
- Atualiza quando o Claude Code redesenha a statusLine.
- Só aparece em planos Pro/Max, depois da primeira resposta da sessão.

### Tokens: históricos do Claude Code

O servidor lê `~/.claude/projects/**/*.jsonl`:

- soma `input + output + cache_creation + cache_read` de cada mensagem, sem duplicar;
- a média usa os 7 dias anteriores que tiveram uso;
- recalcula a cada leitura do Kindle, com cache por arquivo.

## Transporte: o Kindle puxa

A cada 30 s, o scriptlet no Kindle busca:

| Rota | O que devolve |
|---|---|
| `GET /status.txt` | estado, sequência de quadros e intervalo |
| `GET /screen/<quadro>.png` | uma tela inteira por quadro, já girada, só quando a tela mudou |

O computador nunca empurra nada. Pra parar, a rota `/parar` faz o servidor responder `stop` na próxima leitura. Sem USB e sem SSH.

Outras rotas úteis:

| Rota | Pra quê |
|---|---|
| `/preview.png` | a tela deitada, como você vê |
| `/preview.png?demo=<modo>` | exemplo com dados fictícios: `sopa`, `cebola`, `tempero`, `frigideira`, `prato`, `chamando`, `esperando`, `descansando`, `varios` |
| `/sprite/<quadro>.png` | um quadro do mascote, girado |

Também dá pra renderizar sem subir o servidor:

```sh
python3 server.py --render tela.png esperando
python3 server.py --sprites pasta/
```

## A animação no aparelho

- **Intervalo:** 1,5 s por quadro. Pedindo permissão: 1 s. Descansando: 4 s.
- **Sequência:** enquanto o Claude trabalha, o servidor sorteia 10 blocos de sopa, cebola, tempero e frigideira, sem repetir o mesmo bloco seguido. Cada bloco é sempre quadro 1 → quadro 2. Isso dá 30 s de animação por leitura.
- **Troca:** o servidor gera uma tela inteira por quadro e o Kindle alterna entre elas com `eips -g` (atualização parcial). Como as telas só diferem no retângulo do mascote, só ele muda no e-ink.
- **Refresh completo** (`eips -f`): no primeiro desenho, quando o estado muda e a cada 10 trocas de texto.

A primeira tentativa foi desenhar só a região do mascote (`eips -g quadro.png -x -y`), mas no aparelho o mascote não alternou. A causa provável é o `eips` desse firmware não posicionar a imagem, mas isso não foi confirmado. Por isso a troca passou a ser de tela inteira.

## Rotação

O Kindle é 600×800 em pé. O painel é desenhado deitado em 800×600 e girado antes de ir pro aparelho. `KINDLE_DASH_ROTATE=90` deixa o logo "kindle" à esquerda, e `270` deixa à direita.

## Bateria

Não foi medida. Com Wi-Fi sempre ligado e animação contínua, deixe no carregador.
