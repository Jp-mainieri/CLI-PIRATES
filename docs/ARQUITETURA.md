# Arquitetura

Como o código está organizado, por que está assim, e os conceitos que travam quem chega.

Se você só quer jogar, veja o [README](../README.md). Se vai mexer em equilíbrio, veja também [BALANCEAMENTO](BALANCEAMENTO.md).

---

## Em uma frase

Um jogo de terminal em Python puro (~10.400 linhas, zero dependências) com **dois loops de tempo real** que compartilham o mesmo objeto de estado do jogador, e uma camada de renderização que nunca decide nada.

---

## Os quatro conceitos que travam quem chega

Leia estes antes de abrir qualquer arquivo. Sem eles o código parece arbitrário.

### 1. Dois loops, um estado

```
main()
 └─ tela_menu
     ├─ "mundo"  → _mundo_menu_loop → mundo_loop ──┐
     └─ "jogar"  → _arena_menu_loop  → jogo_loop   │
                                                    │
                   mundo_loop chama jogo_loop ──────┘
                   quando inimigo < 750m
```

`mundo_loop` (navegação) e `jogo_loop` (combate) são loops de tempo real independentes, cada um com seu próprio `getch`/tick/render. Mas **o mesmo objeto `Estado` atravessa os dois**: dano, tripulação, moral, porão e frota do jogador não são recriados ao entrar em combate — são os mesmos.

É por isso que um `Estado` tem campos que só fazem sentido em combate (`estado.inimigo`, `estado.tempo`) convivendo com campos que atravessam tudo (`estado.jogador`, `estado.frota`).

> `jogo_loop` também roda sozinho, no modo Arena, sem `estado_mundo`. Por isso quase tudo que depende do mundo é opcional ali (`estado_mundo=None`) — veja as hotkeys de zoom, que ficam inertes nesse caso.

### 2. Coordenadas de arena vs. mundo

O mundo tem 32 km e é **toroidal**. A arena de combate tem 2400 unidades e é **centrada no jogador**.

```
mundo_para_arena()          arena_para_mundo()
jogador → (0, 0)            mundo = (arena_o + arena) % MUNDO_TAMANHO
inimigo → delta_toroidal
```

`arena_ox/oy` guardam onde no mundo o combate começou. Ao terminar a batalha, as posições finais voltam pelo caminho inverso.

Esquecer essa conversão é o erro mais comum ao mexer em combate: coordenadas de arena são pequenas e podem ser negativas; as do mundo são grandes e sempre positivas.

**`delta_toroidal`** existe porque no toro a menor distância pode atravessar a borda. Sempre use essa função para diferença de posições no mundo — nunca `x2 - x1`.

### 3. Física compartilhada, loops separados

`core/movimento.py::calcular_tick_fisica` é a **única** implementação de física de movimento. Ela é chamada de dois lugares:

| chamador | quem move | fronteira |
|---|---|---|
| `core/ship.py::Navio.atualizar_movimento` | jogador e inimigo em combate | `clamp` em ±`MAPA_TAMANHO` |
| `world/simulation.py` | jogador e inimigos no mundo | wraparound toroidal |

A diferença entre combate e navegação é só o tratamento de borda. Se você mudar física, muda nos dois — de propósito.

### 4. Renderização não decide nada

A camada de UI segue um contrato rígido:

```python
def build_algo_linhas(estado) -> list[tuple[str, int, list]]:
    # (texto, atributo_curses, [(coluna, trecho, atributo), ...])
```

Cada `build_*` em `ui/hud.py` monta **texto puro** mais overlays de cor, sem tocar em curses. O `ui/renderer.py` só posiciona. Consequências práticas:

- **Os painéis são testáveis sem terminal.** A maioria dos testes de HUD constrói um `Estado` e inspeciona strings. É por isso que dá para ter 600+ testes num jogo curses.
- **Um painel que não se aplica retorna `[]`**, e some sem deslocar nada. Veja `build_vigia_linhas` e `build_fuga_linhas`.
- **`safe_addstr` engole erros de borda em silêncio.** Escrever fora da tela não quebra o jogo. Isso é conveniente e perigoso: um painel pode estar sumindo sem erro nenhum. Se algo "não aparece", suspeite de tamanho de janela antes de suspeitar da lógica.

---

## Estrutura

```
main.py                    entrada: python3 main.py
pirates/
  game.py          1056    os dois loops + menus + setup curses
  constants.py      874    TODO o equilíbrio
  saves.py          493    serialização por capitão
  core/
    state.py        464    Estado — uma partida de combate
    ship.py         433    Navio, Canhao — dano, água, reparo
    tripulacao.py   335    postos e trânsito entre eles
    combat.py       247    geometria, disparo, zoom adaptativo
    porao.py        246    barris, carga, loot
    movimento.py            física (empuxo, arrasto, deriva) — fonte única
    vento.py                direção, intensidade, zonas
    velas.py                slots de vela, somas de eficiência
    simulation.py           o tick de combate
    notoriedade.py          faixas, spawn por faixa, elites
    frota.py                múltiplos navios por capitão
    utils.py                puro: clamp, barra, setas, símbolos
  world/
    state.py                EstadoMundo — mapa, portos, ilhas, inimigos
    entities.py             NavioMundo, Porto, Ilha
    simulation.py           IA de patrulha, conversão mundo↔arena
  ai/enemy.py       447    IA de combate: manobra, tripulação, mira
  ui/
    hud.py         1124    os build_* — o arquivo maior do projeto
    renderer.py     354    posicionamento, safe_addstr
    menus.py        687    menus, ajustes, fim de jogo
    inventario.py   250    sub-loop do porão
    colors.py               helpers de cor
  input/
    commands.py     353    comandos de texto + TAB
    hotkeys.py      301    teclas diretas
  port/
    scene.py        818    cena do porto (sub-loop próprio)
    lojas.py        347    compra, venda, upgrades, velas
```

---

## O tick de combate

`core/simulation.py::atualizar_simulacao(estado, dt)` é **uma chamada que faz tudo**, nesta ordem:

1. Trânsito de tripulação avança; quem chegou passa a trabalhar
2. Reparo, bomba e moral do jogador
3. IA do inimigo (movimento, tripulação, mira) + reparo/água/moral dele
4. Disparos dos dois lados
5. Vento deriva
6. Movimento dos dois navios
7. Zoom do minimapa
8. Relógio avança
9. Condições de fim (afundou, fugiu, escapou)

> **Armadilha.** Como ela já chama `atualizar_ia_movimento` e `atualizar_movimento` internamente, chamar essas funções à mão *e depois* `atualizar_simulacao` move cada navio duas vezes por tick. Produz números plausíveis e errados. Se você está escrevendo uma simulação para medir equilíbrio, chame **só** `atualizar_simulacao`.

**Trânsito antes dos efetivos** (passo 1) é deliberado: quem vence o timer neste tick já trabalha neste tick.

---

## Tripulação: alocado ≠ efetivo

O sistema tem duas contagens, e confundi-las é fonte de bug:

| campo | significado |
|---|---|
| `tripulantes` | quantos foram **designados** ao posto |
| `efetivos` | quantos já **chegaram** e estão trabalhando |

`Canhao.armado()` olha `efetivos`. Um canhão cuja equipe está atravessando o convés não atira **e não recarrega** — a recarga fica congelada (`proximo_tiro += dt` em `core/combat.py`).

O custo de trânsito é medido a partir do **último posto onde a pessoa efetivamente trabalhou**, não do posto atual. É isso que impede estacionar tripulantes no convés para depois alocá-los de graça no bordo oposto.

`reconciliar_jogador(estado)` casa as contagens agregadas com o roster de indivíduos. É idempotente e barata, e é chamada num ponto único de saída em `processar_hotkey` e `processar_comando`, para que nenhum comando novo possa esquecer dela.

---

## Mundo e determinismo

`EstadoMundo(tipo_navio, seed)` gera **tudo** a partir da seed, usando um `random.Random(seed)` próprio — nunca o `random` global:

- 8 portos, 48 ilhas, 32 inimigos
- posições respeitando espaçamento mínimo e evitando ilhas

Consequência para os saves: **portos e ilhas não são gravados**. O save guarda a `seed_mundo` e eles são regenerados idênticos ao carregar. Só o que o jogador mudou é serializado:

```
versao_save, slug, nome_capitao, seed_mundo, criado_em, atualizado_em
preferencias   cores, hotkeys, unicode, textura do mar, rastro, zoom_nav
capitao        x, y, heading, notoriedade, portos_visitados, ...
frota          navios, dano, porão, upgrades, velas
```

Se você adicionar algo ao mundo que **não** derive da seed, precisa serializar. Se derivar, não serialize — deixe a seed fazer o trabalho.

`VERSAO_SAVE` existe para migração. Campos novos devem ser opcionais na leitura (`prefs.get(...)` com default), e aí a versão não precisa subir.

---

## A IA inimiga

`ai/enemy.py` tem três frentes independentes, chamadas em sequência pelo tick:

| função | decide |
|---|---|
| `atualizar_ia_movimento` | rumo e nível de vela |
| `atualizar_ia_tripulacao` | quem vai para canhão, bomba, reparo |
| `atualizar_ia_mira` | distância de mira dos canhões |

O movimento tem **modos com histerese** (`aproximar` / `circular` / `afastar`) e um atrator importante em `alcance_canhao_efetivo()`: acima disso a IA persegue em linha reta; abaixo, apresenta o través e para de fechar. Esse é o comportamento que produz o ciclo-limite descrito em [BALANCEAMENTO](BALANCEAMENTO.md#32-fuga).

A IA tem **personalidade por partida**, sorteada em `Estado.__init__`: `ia_island_avoidance_mult`, `ia_lado_bordada`, limiares de moral. Dois combates contra o mesmo tipo de navio não se comportam igual.

---

## Onde mexer para cada tipo de mudança

| você quer... | mexa em |
|---|---|
| Ajustar equilíbrio | `constants.py` — e leia [BALANCEAMENTO](BALANCEAMENTO.md) antes |
| Novo comando de texto | `input/commands.py` + `COMANDOS`/`ALIASES` |
| Nova hotkey | `input/hotkeys.py` — trate antes do filtro `isalpha` se não for letra |
| Novo painel no HUD | novo `build_*` em `ui/hud.py` + chamada em `ui/renderer.py` |
| Mudar física | `core/movimento.py` — afeta combate e navegação juntos |
| Comportamento do inimigo em combate | `ai/enemy.py` |
| Comportamento no mundo aberto | `world/simulation.py` |
| Loja, upgrade, preço | `port/lojas.py` + `PRECO_*` em `constants.py` |
| Algo que precise sobreviver ao save | `saves.py` — e confira se não deriva da seed |

---

## Convenções

**Português no código.** Nomes, docstrings e comentários são em português. Mantenha — mistura fica pior que qualquer das duas escolhas.

**Comentário explica decisão, não mecânica.** `# incrementa i` não ajuda ninguém. `# histerese aqui senão a IA oscila de modo a cada tick` ajuda muito. O repositório tem muito do segundo tipo; siga o padrão.

**Constantes com docstring.** Todo valor em `constants.py` tem uma string logo abaixo explicando o que é e, quando aplicável, que outras constantes ele afeta.

**Ponto único de saída para reconciliação.** Quando uma operação tem dezenas de caminhos de retorno e todos precisam de um passo final, o padrão do repositório é um wrapper fino que faz o passo uma vez só. Veja `processar_hotkey`.

**Falha visível é melhor que fallback silencioso.** Um valor não mapeado deve parecer desconhecido, não se disfarçar de válido. Um fallback plausível demais esconde bug — já aconteceu com o símbolo de tipo de navio no mapa.

---

## Testes

```bash
python3 -m pytest tests/ -q
```

614 testes, 27 arquivos, rodam em menos de um segundo. Não há mock de curses: os testes constroem `Estado`/`EstadoMundo` reais e inspecionam o retorno dos `build_*` ou o estado depois de ticks.

Três categorias:

1. **Comportamento** — dado este estado, isto acontece.
2. **Invariantes de equilíbrio** — a relação entre constantes que precisa valer. Ver a tabela em [BALANCEAMENTO](BALANCEAMENTO.md#constantes-acopladas).
3. **Contratos de dados** — todo tipo em `NAVIO_TIPOS` tem símbolo de mapa, os símbolos são distintos, o fallback não colide.

A categoria 3 é a que pega o bug que ninguém procurava. Quando adicionar uma tabela indexada por tipo, adicione o teste que verifica que ela cobre todos os tipos.

---

## Ver também

- [README](../README.md) — visão geral e como rodar
- [COMO_JOGAR](COMO_JOGAR.md) — os instrumentos, do ponto de vista do jogador
- [BALANCEAMENTO](BALANCEAMENTO.md) — os números e como medi-los
