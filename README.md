# CLI PIRATES

Jogo de comando naval em tempo real, 100% no terminal. Sem dependências externas — apenas a biblioteca padrão do Python.

```
  ..|'''.| '||'      '||'    '||''|.  '||' '||''|.       |     |''||''| '||''''|   .|'''.|
.|'     '   ||        ||      ||   ||  ||   ||   ||     |||       ||     ||  .     ||..  '
||          ||        ||      ||...|'  ||   ||''|'     |  ||      ||     ||''|      ''|||.
'|.      .  ||        ||      ||       ||   ||   |.   .''''|.     ||     ||       .     '||
 ''|....'  .||.....| .||.    .||.     .||. .||.  '|' .|.  .||.   .||.   .||.....| |'....|'

                       um jogo de comando naval em tempo real
```

Você comanda um navio num mundo aberto de 32 km × 32 km: navega pelo vento, caça e é caçado, saqueia destroços, atraca em portos para comprar velas e melhorias, e constrói uma frota. Nada pausa enquanto você digita — o navio segue navegando, a água segue subindo e os canhões seguem recarregando.

## Como rodar

```bash
python3 main.py
```

Requer **Python 3.10+** e um terminal real (TTY). Recomenda-se uma janela de pelo menos **100 colunas × 45 linhas**.

Não há nada a instalar: o jogo usa só `curses`, que já vem no Python em Linux e macOS.

## Os primeiros cinco minutos

1. **Novo capitão** no menu, escolha um nome e um navio. Comece pela **Chalupa** — ela é a mais perdoável.
2. Ligue as **hotkeys** em Ajustes. Comandar por texto funciona, mas em tempo real as teclas salvam vidas.
3. Use `A` e `D` para o leme, `W` para abrir vela. Veja a velocidade subir no HUD.
4. Procure um `[P]` no mapa — é um porto. Navegue até ele e digite `atracar`.
5. Quando um inimigo chegar a **750 m**, o combate começa sozinho. Alinhe o **través** (o inimigo a 90° da sua proa) e arme os canhões com `c E1 300`.

Se a coisa desandar, `fugir` e reze.

## Os dois modos

O jogo alterna entre dois loops, no mesmo mapa:

- **Navegação** — mundo aberto, portos, ilhas, destroços, inimigos em patrulha.
- **Combate** — dispara automaticamente quando um inimigo chega a 750 m. Mesmo navio, mesmo porão, mesma tripulação.

Vencer devolve você à navegação com todo o estado preservado. Afundar acaba a partida.

## Os navios

| | Chalupa | Brigantim | Galeão |
|---|---|---|---|
| Dificuldade | 1 | 2 | 3 |
| Tripulação | 2 | 3 | 4 |
| Canhões por bordo | 1 | 2 | 3 |
| Slots de porão | 6 | 9 | 14 |
| Recarga de canhão | **0,55×** (rápida) | 1,1× | 1,4× (lenta) |
| Erro de mira | 80 m | 40 m | **15 m** (preciso) |
| Giro do leme | **45°/s** | 25°/s | 12°/s |
| Resistência de casco | 0% | +15% | **+45%** |
| Reparo | **1,5×** | 1,0× | 1,0× |
| Bombas | **2,4×** | 1,3× | 0,8× |
| Preço | 70 | 150 | 300 |

Nenhum navio é estritamente melhor. A chalupa atira quase três vezes mais rápido e gira quatro vezes melhor, mas erra muito e afunda fácil. O galeão acerta de longe e aguenta pancada, mas é lento para virar e péssimo em controle de avarias.

**Onde cada um manda no vento** — velocidade com velas cheias, por ângulo entre a proa e o vento:

| | 0° (contra) | 60° | 90° | 180° (a favor) |
|---|---|---|---|---|
| Chalupa | **9,0** | 9,5 | 8,6 | 6,6 |
| Brigantim | 9,0 | **10,0** | 10,4 | 9,6 |
| Galeão | 7,0 | 9,4 | **12,7** | **16,4** |

A chalupa aponta contra o vento onde os outros não conseguem. O galeão domina a favor. Fugir é escolher o ângulo em que você ganha — não simplesmente virar as costas.

## Comandos

Digite no prompt. **TAB** completa, **ENTER vazio** repete o último, **ESC** volta ao menu.

| Comando | Alias | O que faz |
|---|---|---|
| `leme <graus>` | `l` | Define o rumo (0–360°) |
| `vela` | | Lista os slots de vela do navio |
| `vela <0-2>` | `v` | Nível do slot selecionado (0 / 50% / 100%) |
| `vela <ID> <0-2>` | | Nível de um slot específico |
| `ancorar` | | Liga/desliga a âncora (o leme continua livre) |
| `reparar <parte> <trip>` | `r` | Reparo contínuo (`casco`, `mastro`, `vela`, `roda`) |
| `bomba <trip>` | `b` | Tripulantes nas bombas |
| `canhao <id> <dist>` | `c` | Aloca tripulação e mira a *dist* metros |
| `canhao <id> parar` | | Para o canhão e libera a tripulação |
| `radar` | | Distância e rumo exatos do inimigo |
| `fugir` | `f` | Tenta escapar — fique a 800 m+ por 15 s |
| `atracar` | | Ancora no porto (a menos de 250 m do `[P]`) |
| `ajuda` | | Abre a tela completa de instruções |

Canhões usam os IDs `E1`, `E2`, … (estibordo) e `B1`, `B2`, … (bombordo).

## Hotkeys

Precisam estar ligadas em **Ajustes**, e só funcionam com o prompt vazio.

| Tecla | Ação |
|---|---|
| `A` / `D` | Leme −15° / +15° |
| `Q` | Circula o slot de vela selecionado |
| `W` / `S` | Nível do slot ++ / −− |
| `J` / `L` | Seleciona canhão de bombordo / estibordo |
| `I` / `K` | Mira +25 m / −25 m (**todos** os canhões) |
| `Espaço` | Alterna atirar/parar, ou +1 no reparo |
| `U` / `H` | Bombas +1 / −1 tripulante |
| `E` / `R` | Circula partes de reparo / −1 tripulante |
| `+` `=` / `-` `_` | Aproxima / afasta o mapa de navegação (mesma tecla, com e sem SHIFT) |
| `M` | Alterna mapa de navegação ↔ mapa-mundo |
| `V` | Abre o inventário do porão |
| `N` | Atraca no porto, ou ancora |

## As mecânicas que decidem partidas

### Vento e velas

Não existe teto artificial de velocidade — ela emerge do equilíbrio entre o empuxo somado das suas velas e o arrasto do casco. Cada navio tem slots individuais (proa, mastros, popa, auxiliares), cada um com um **tipo** de vela e um **nível** (0 / 50% / 100%).

O ângulo entre o casco e o vento define quatro zonas: **zona morta** (0–45°), **bolina** (45–90°), **través** (90–135°) e **popa** (135–180°). Cada tipo de vela rende diferente em cada zona:

- **Quadrada** e **topo quadrada** — inúteis contra o vento, excelentes a favor.
- **Latina** e **carangueja** — apontam contra o vento, medianas a favor.
- **Estai** — não dá velocidade nenhuma; só **giro**. É a vela de manobra.

Virar o leme bruscamente e vento de través geram **deriva lateral**: o navio desliza de lado até o casco corrigir. Cascos pesados derrapam mais.

Troque velas na Loja de Navios de qualquer porto. Slots auxiliares começam vazios — são seu espaço de customização.

### Água e reparo

A água entra de forma **exponencial** conforme o casco é danificado. Com dano leve as bombas seguram; com dano severo nem a tripulação inteira nas bombas impede o naufrágio. Conserte o casco.

Reparo consome tábuas (0,15 por HP) e fica mais lento conforme o dano acumula.

### Tripulação e trânsito

Tripulante levado de um posto a outro **não trabalha durante a travessia** — leva 6 s entre canhões do mesmo bordo, 8 s para o bordo oposto, 4 s para trocar de tipo de tarefa. Guarnecer os dois bordos ao mesmo tempo elimina esse custo, mas consome a tripulação que faria o controle de avarias.

Ao pedir tripulantes sem ter gente livre, o jogo puxa primeiro dos canhões, depois do reparo. A bomba **nunca** é tocada automaticamente.

### Moral

Afeta a recarga dos canhões e a eficiência de reparo e bombas. O inimigo com moral baixa entra em modo de fuga e tenta escapar.

### Economia e notoriedade

Pólvora, bolas, tábuas e ouro são **físicos** — ocupam barris no porão, e não há banco. Cada tiro custa 1 pólvora + 1 bola.

Afundar inimigos rende **notoriedade**, que sobe por oito faixas (de *Desconhecido* a *Lenda Viva*). Quanto mais alta, mais galeões e mais elites aparecem no mundo — e mais caro fica fugir, porque fugir custa notoriedade.

## O mundo

32 km × 32 km, toroidal (sair por uma borda entra pela oposta), dividido em quadrantes de 8 km. Contém **8 portos**, **48 ilhas** colidíveis e **32 inimigos** em patrulha.

Ilhas causam dano por colisão e zeram sua velocidade. A IA inimiga também as evita, com personalidades diferentes de cautela.

O mundo é gerado por **seed**: a mesma seed reproduz exatamente o mesmo mapa. A seed vai no save, e portos e ilhas são regenerados a partir dela em vez de serem gravados.

Saves ficam em `saves/<capitao>.json`, um por capitão.

## Estrutura do código

```
main.py                    entrada: python main.py
pirates/
  game.py                  os dois loops: jogo_loop (combate), mundo_loop (navegação)
  constants.py             TODAS as constantes de equilíbrio
  saves.py                 serialização por capitão
  core/
    state.py               Estado — uma partida de combate
    ship.py                Navio, Canhao — física e dano
    movimento.py           tick de física (empuxo, arrasto, deriva)
    vento.py               direção, intensidade, zonas
    velas.py               slots de vela, somas de eficiência
    combat.py              geometria, disparo, zoom adaptativo
    simulation.py          tick de simulação de combate
    tripulacao.py          postos e trânsito entre eles
    porao.py               barris, carga, loot
    frota.py               múltiplos navios por capitão
    notoriedade.py         faixas, spawn por faixa, elites
  world/
    state.py               EstadoMundo — mapa, portos, ilhas, inimigos
    entities.py            NavioMundo, Porto, Ilha
    simulation.py          IA de patrulha, conversão mundo↔arena
  ai/enemy.py              IA de combate: manobra, tripulação, mira
  ui/                      renderer, hud, menus, inventário, cores
  input/                   commands (texto), hotkeys (teclas)
  port/                    cena do porto e lojas
```

Cerca de 10 mil linhas, sem dependências.

**Dois conceitos que você precisa entender antes de mexer:**

1. **Coordenadas de arena vs. mundo.** Em combate o jogador fica na origem `(0,0)` e o inimigo na posição relativa. `arena_ox/oy` guardam onde no mundo o combate começou. A conversão é `mundo = (arena_o + arena) % MUNDO_TAMANHO`.

2. **`constants.py` é o painel de controle.** Quase todo equilíbrio do jogo é um número lá, documentado. Algumas constantes são **acopladas** — as de trânsito de tripulação, por exemplo, precisam satisfazer a desigualdade triangular, ou o jogador troca de bordo mais rápido passando pelo reparo. Onde existe esse tipo de acoplamento, há um comentário dizendo qual e um teste travando.

## Testes

```bash
python3 -m pytest tests/ -q
```

589 testes, sem dependências além do `pytest`. Devem todos passar antes de qualquer PR.

Boa parte deles trava **invariantes de equilíbrio**, não só comportamento — por exemplo, que o maior nível de zoom não revele inimigos além do alcance de visão do capitão. Se você recalibrar constantes e um teste desses falhar, leia a mensagem: ela diz qual regra foi quebrada.

## Contribuindo

1. Faça um fork e crie uma branch (`git checkout -b feat/nova-mecanica`)
2. Rode `python3 -m pytest tests/ -q` antes e depois
3. Abra um Pull Request descrevendo **o que mudou e por quê**

Convenções do repositório:

- Branches por escopo: `feat/`, `fix/`, `balance/`, `mod/`
- Mensagens de commit no imperativo, com o *porquê* no corpo — não só o *o quê*
- Mudança de equilíbrio merece número: diga o que você mediu, e o que **não** mediu
- Comentário explica decisão, não mecânica óbvia

## Documentação

- [docs/BALANCEAMENTO.md](docs/BALANCEAMENTO.md) — como o equilíbrio está montado, como medir uma
  mudança antes de fazê-la, o que já foi medido e o que está aberto.

## Licença

MIT — veja [LICENSE](LICENSE).
