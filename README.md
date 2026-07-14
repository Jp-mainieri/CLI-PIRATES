# CLI PIRATES

Jogo de combate naval em tempo real, 100% no terminal. Sem dependências externas — apenas a biblioteca padrão do Python.

```
  ..|'''.| '||'      '||'    '||''|.  '||' '||''|.       |     |''||''| '||''''|   .|'''.|
.|'     '   ||        ||      ||   ||  ||   ||   ||     |||       ||     ||  .     ||..  '
||          ||        ||      ||...|'  ||   ||''|'     |  ||      ||     ||''|      ''|||.
'|.      .  ||        ||      ||       ||   ||   |.   .''''|.     ||     ||       .     '||
 ''|....'  .||.....| .||.    .||.     .||. .||.  '|' .|.  .||.   .||.   .||.....| |'....|'

                       um jogo de comando naval em tempo real
```

## Como rodar

```bash
python3 main.py
```

Requer **Python 3.10+** e um terminal real (TTY). Recomenda-se uma janela de **~100 colunas × 45 linhas**.

## Como jogar

O jogo roda em **tempo real** — o navio se move, a água sobe e os canhões atiram sozinhos enquanto você digita ordens.

### Escolha seu navio

| Navio      | Dificuldade | Tripulação | Canhões/lado | Trip./canhão |
|------------|-------------|------------|--------------|--------------|
| Chalupa    | Fácil       | 2          | 1            | 1            |
| Bergantim  | Normal      | 3          | 2            | 1            |
| Galeão     | Difícil     | 7          | 3            | 2            |

### Comandos

| Comando | Atalho | Descrição |
|---------|--------|-----------|
| `leme <graus>` | `l` | Define o rumo (0–360°) |
| `vela <0-3>` | `v` | Define o nível de vela |
| `reparar <parte> <n>` | `r` | Aloca *n* tripulantes para reparo contínuo (`casco`, `mastro`, `vela`, `roda`) |
| `bomba <n>` | `b` | Aloca *n* tripulantes para bombear água |
| `canhao <id> <n> <dist>` | `c` | Arma um canhão com *n* tripulantes mirando a *dist* metros |
| `canhao <id> parar` | | Para o canhão e libera a tripulação |
| `radar` | | Exibe distância e rumo exatos do inimigo |
| `ajuda` | | Lista comandos no log |

**TAB** circula opções de autocompletar. **ENTER vazio** repete o último comando. **ESC** encerra a partida.

### IDs dos canhões

`E1`, `E2`, … (estibordo) e `B1`, `B2`, … (bombordo).

### Hotkeys (ativar em Ajustes)

Funcionam com o prompt vazio, maiúsculas ou minúsculas:

| Tecla | Ação |
|-------|------|
| A / D | Leme ±15° |
| W / S | Vela ++ / -- |
| J / L | Seleciona canhão de bombordo / estibordo |
| I / K | Mira +25m / -25m |
| Espaço | Alterna atirar/parar (canhão) ou +reparo |
| U / H | Bomba +1 / -1 tripulante |
| E / R | Circula partes de reparo / remove tripulante |

### Mecânicas importantes

- **Água**: entra de forma **exponencial** conforme o casco é danificado. Com dano leve as bombas seguram; com dano severo, nem toda a tripulação nas bombas impede o naufrágio — conserte o casco!
- **Realocação automática**: ao pedir tripulantes sem ter gente livre, o jogo puxa primeiro de canhões (libera o canhão inteiro), depois de reparo (parcial). A bomba **nunca** é tocada automaticamente.
- **Reparo**: a eficiência cai conforme o dano acumula — reparar com o casco destruído é muito mais lento.

## Estrutura do código

```
main.py              ← ponto de entrada
pirates/
  __init__.py        ← documentação do pacote
  constants.py       ← constantes e configuração global
  utils.py           ← funções utilitárias puras (clamp, barra, ...)
  colors.py          ← helpers de cor para curses
  ship.py            ← classes Navio e Canhao
  combat.py          ← geometria, combate, zoom
  state.py           ← Estado do jogo + gerenciamento de tripulação
  ai.py              ← inteligência artificial do inimigo
  commands.py        ← processamento de comandos de texto + TAB
  hotkeys.py         ← atalhos de teclado em tempo real
  simulation.py      ← loop de simulação por tick
  hud.py             ← construtores de elementos HUD
  ui.py              ← renderização curses (safe_addstr, desenhar_tela)
  menus.py           ← telas de menu, ajustes, navio e fim de jogo
  game.py            ← loop principal + setup curses
```

## Contribuindo

1. Fork o repositório
2. Crie uma branch para sua feature (`git checkout -b feature/nova-mecanica`)
3. Faça seus commits com mensagens claras
4. Abra um Pull Request

O código é 100% Python padrão — sem dependências a instalar. Para testar localmente basta `python3 main.py`.

## Licença

MIT — veja [LICENSE](LICENSE).
