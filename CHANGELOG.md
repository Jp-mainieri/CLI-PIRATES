# Changelog

Todas as mudanças notáveis neste projeto são documentadas aqui.
Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/).

---

## [Não lançado]

### Planejado
- Modo multiplayer local (dois jogadores no mesmo terminal)
- Mais tipos de navio (fragata, cutter)
- Sistema de saves entre partidas

---

## [0.3.0] – 2026-07-14

### Adicionado
- Estrutura de pacote modular com subpacotes `core/`, `ai/`, `ui/`, `input/`
- `pyproject.toml` com metadados completos e entry point `cli-pirates`
- Suite de testes unitários para funções puras (`tests/`)
- `.gitignore` padrão Python
- Documentação open-source: `README.md`, `LICENSE` (MIT), `CHANGELOG.md`

### Alterado
- Código monolítico (`batalha_navalX-0-3.py`) separado em 14 módulos documentados
- Todas as classes e funções públicas documentadas com docstrings

---

## [0.2.0] – 2026-07 (interno)

### Adicionado
- Sistema de hotkeys em tempo real (WASD + IJKL + UH + ER)
- Gráficos Unicode opcionais (setas ↑↗→↘↓↙←↖) no minimapa
- Sistema de cores curses (verde/amarelo/vermelho por nível de HP)
- Zoom adaptativo do minimapa com histerese
- Realocação automática de tripulação por prioridade

### Alterado
- IA do inimigo com limiares aleatorizados por partida
- Física de reparo exponencial (dano alto = reparo mais lento)
- Entrada de água exponencial no dano do casco

---

## [0.1.0] – 2026-07 (interno)

### Adicionado
- Jogo base: combate naval em tempo real no terminal via curses
- Três tipos de navio: Chalupa (fácil), Bergantim (normal), Galeão (difícil)
- Sistema de canhões com arcos de tiro por lado (estibordo/bombordo)
- Comandos de texto: leme, vela, reparar, bomba, canhão, radar, ajuda
- Autocompletar por TAB para todos os comandos
- Bússola deslizante e visão do capitão no HUD
