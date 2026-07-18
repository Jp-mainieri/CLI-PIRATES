# CLI PIRATES — Contexto do Projeto

Jogo naval em tempo real rodando no terminal via Python `curses`. O jogador navega um mundo aberto de 8km×8km, gerencia tripulação, canhões e porão, e entra em combate com inimigos.

## Estrutura do pacote

```
main.py                    # entrada: python main.py
pirates/
  game.py                  # loops principais: jogo_loop (combate), mundo_loop (navegação)
  constants.py             # todas as constantes numéricas e de equilíbrio
  saves.py                 # serialização/deserialização de saves por capitão
  core/
    state.py               # class Estado — estado de uma partida de combate
    ship.py                # class Navio, class Canhao — física e dano
    combat.py              # geometria, disparo, zoom adaptativo
    simulation.py          # tick de simulação (água, reparo, moral)
    porao.py               # class Porao, Barril, loot
    frota.py               # class Frota — múltiplos navios por capitão
    utils.py               # clamp, barra, setas
  world/
    state.py               # class EstadoMundo — posição no mundo, inimigos, portos, ilhas
    entities.py            # dataclasses: NavioMundo, Porto, Ilha + eh_solido_ilha()
    simulation.py          # atualizar_ia_mundo, atualizar_jogador_mundo, mundo↔arena
  ai/
    enemy.py               # IA de combate: movimento, tripulação, mira
  ui/
    renderer.py            # safe_addstr, desenhar_tela, desenhar_tela_mundo
    hud.py                 # build_* — construtores de painéis HUD
    menus.py               # telas de menu, fim, seleção de navio
    inventario.py          # sub-loop do porão com cursor
    colors.py              # helpers de cor curses
  input/
    commands.py            # processar_comando (texto livre)
    hotkeys.py             # processar_hotkey (teclas diretas)
  port/
    scene.py               # porto_loop — cena de loja/upgrades
    lojas.py               # lógica de compra/venda/upgrade
```

## Padrões arquiteturais críticos

- **Dois loops distintos:** `jogo_loop` (combate arena) e `mundo_loop` (navegação). O mundo_loop chama jogo_loop quando inimigo está a < 750m, passando `estado`, `estado_mundo`, `arena_ox`, `arena_oy`.
- **Coords arena vs mundo:** Jogador fica em (0,0) na arena; inimigo em `delta_toroidal`. `arena_ox/oy` = posição do jogador no mundo quando o combate começou. Conversão: `mundo_x = (arena_ox + arena_x) % MUNDO_TAMANHO`.
- **Física:** `atualizar_posicao_toroidal` em `world/simulation.py` — giro gradual + aceleração + wraparound toroidal. A versão de combate está em `core/ship.py` (`atualizar_movimento`).
- **Tick:** `dt = min(agora - last_tick, MUNDO_TICK)`. Mundo: 0.5s. Combate: `SIM_TICK = 0.5s`.
- **Determinismo:** `EstadoMundo` usa `self._rng = random.Random(seed)` para portos e ilhas — mesma seed reproduz o mesmo mapa. Salvo em `saves.py` como `seed_mundo`.
- **Cores curses:** pares 1–7 definidos em `main()` de `game.py`: VERDE=1, AMARELO=2, VERMELHO=3, JOGADOR(ciano)=4, INIMIGO(magenta)=5, MAR(azul)=6, ILHA(amarelo)=7.
- **Renderização:** `safe_addstr` ignora silenciosamente erros de borda. Cada `build_*` retorna `list[tuple[str, int, list[overlay]]]`.
- **Moral:** afeta cooldown de canhão (`1/mult_moral`) e eficiência de reparo/bomba.

## Estado de combate (`core/state.py`)
- `estado.jogador`, `estado.inimigo` — `Navio` com partes, canhões, porão
- `estado.tempo` — resetado a 0.0 a cada novo combate em `mundo_loop`
- `estado.ilhas_arena` — ilhas em coords de arena (populado antes de `jogo_loop`)
- `estado.ia_island_avoidance_mult` — personalidade de evasão de ilha por partida
- `estado.frota` — `Frota` com navios reserva para respawn

## Estado do mundo (`world/state.py`)
- `EstadoMundo(tipo_navio, seed)` — gera portos, ilhas e inimigos deterministicamente
- `estado_mundo.ilhas: list[Ilha]` — 20 ilhas com forma harmônica
- `estado_mundo.em_colisao_ilha: bool` — flag de primeiro tick de colisão (navegação)
- `estado_mundo.notoriedade: int` — pontuação de reputação do jogador
- `estado_mundo.em_combate: bool` — True durante jogo_loop

## Saves
- `salvar(estado, estado_mundo, slug)` — serializa em `saves/<slug>.json`
- `restaurar_estado(data, config)` — reconstrói `Estado` + `EstadoMundo(seed=seed)`; ilhas/portos são regenerados da seed, sem salvar

## Testes
```bash
python -m pytest tests/ -q   # 218 testes, devem todos passar
```

## Branch atual: `feat/islands`
Features implementadas nesta branch (ainda não mergeada em main):
- Ilhas colidíveis com forma orgânica harmônica
- Colisão com dano + push + zeragem de velocidade/heading
- IA de patrulha e combate evita ilhas (personalidade via `avoidance_mult`)
- Ilhas nos 3 mapas (nav `###`, mundo `[#]`, combate `###`)
- Fix: push de colisão zera velocidade e alinha heading imediatamente
- Fix: cooldown de canhão zerado ao iniciar novo combate

## Próximo feature planejado (não iniciado): `feat/infamy`
Sistema de notoriedade/fama (Infamy):
- Player pode fugir de inimigos (mesmos requisitos de fuga do inimigo: distância + inimigo não estar fugindo)
- Fugir = perder notoriedade
- Ver prompt `prompt-infamy.md` na raiz para spec completo (se existir)
