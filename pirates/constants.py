"""
constants.py – Constantes e configuração global de CLI PIRATES.

Todas as constantes numéricas, listas de referência, textos de arte ASCII
e definições de tipos de navio vivem aqui. Alterar valores neste módulo
afeta o equilíbrio do jogo globalmente.
"""

import os

# ---------------------------------------------------------------------------
# Flags de ambiente / modo desenvolvedor
# ---------------------------------------------------------------------------

MODO_ADM_DISPONIVEL = os.environ.get("CLI_PIRATES_DEBUG") == "1"
"""Só permite ativar o Modo ADM se CLI_PIRATES_DEBUG=1 estiver definida.
Protege contra ativação acidental em partidas normais."""

# ---------------------------------------------------------------------------
# Partes do navio
# ---------------------------------------------------------------------------

PARTES = ['casco', 'mastro', 'vela', 'roda']
"""Lista ordenada de todas as partes reparáveis de um navio."""

PARTES_CRITICAS = ['casco']
"""Partes cujo dano alimenta a entrada de água no porão."""

# ---------------------------------------------------------------------------
# Dimensões do mundo
# ---------------------------------------------------------------------------

MAPA_TAMANHO = 1200
"""Metade do lado do mapa quadrado (unidades de jogo). Navios são
limitados ao intervalo [-MAPA_TAMANHO, +MAPA_TAMANHO] em X e Y."""

# ---------------------------------------------------------------------------
# Tempo
# ---------------------------------------------------------------------------

SIM_TICK = 0.5
"""Intervalo mínimo entre atualizações da simulação, em segundos."""

POLL_MS = 100
"""Timeout de polling de teclado curses, em milissegundos."""

# ---------------------------------------------------------------------------
# Física / balanceamento
# ---------------------------------------------------------------------------

GIRO_GRAUS_SEG_PADRAO = 9.0
"""Taxa de giro padrão do leme, em graus por segundo."""

ACEL_VEL_SEG = 3.0
"""Aceleração/desaceleração do navio, em unidades por segundo²."""

TAXA_REPARO_SEG = 3.0
"""Pontos de HP recuperados por tripulante por segundo em reparo contínuo."""

FATOR_TABUAS_POR_HP = 0.15
"""Tábuas consumidas por ponto de HP reparado. Valor baixo para não esgotar
o estoque rapidamente (ajustável)."""

REPARO_K = 3.5
"""Fator exponencial: quanto maior, mais a eficiência de reparo cai
conforme o dano aumenta (previne recuperação trivial com casco destruído)."""

SAIDA_BOMBA_SEG = 2.5
"""Pontos de água removidos por tripulante por segundo nas bombas."""

COOLDOWN_CANHAO = 12.0
"""Tempo base de recarga de um canhão, em segundos."""

# ---------------------------------------------------------------------------
# Moral
# ---------------------------------------------------------------------------

MORAL_PESO_CASCO = 45.0
"""Peso do HP do casco no cálculo da moral-alvo (soma com os outros pesos = 100)."""

MORAL_PESO_AGUA = 30.0
"""Peso do nível de água (invertido) no cálculo da moral-alvo."""

MORAL_PESO_OUTRAS = 25.0
"""Peso médio das partes não-críticas no cálculo da moral-alvo."""

MORAL_QUEDA_TAXA_SEG = 40.0
"""Pontos de moral perdidos por segundo quando moral_atual > moral_alvo."""

MORAL_K = 3.5
"""Expoente da curva de recuperação de moral (espelha REPARO_K)."""

MORAL_RECUP_BASE_SEG = 6.0
"""Pontos de moral recuperados por segundo na recuperação passiva."""

MORAL_BONUS_ACERTO = 3.0
"""Pontos de moral ganhos ao registrar um acerto inimigo."""

MORAL_LIMIAR_ALTO = 40.0
"""Moral ≤ este valor: tripulação está 'Abalada'."""

MORAL_LIMIAR_MEDIO = 25.0
"""Moral ≤ este valor: tripulação está 'Combalida'."""

MORAL_MULT_NORMAL = 1.0
"""Multiplicador de acerto / recarga quando moral > MORAL_LIMIAR_ALTO."""

MORAL_MULT_ABALADO = 0.85
"""Multiplicador quando MORAL_LIMIAR_MEDIO < moral ≤ MORAL_LIMIAR_ALTO."""

MORAL_MULT_COMBALIDO = 0.60
"""Multiplicador quando moral > 0 e ≤ MORAL_LIMIAR_MEDIO."""

MORAL_MULT_PANICO = 0.30
"""Multiplicador quando moral ≤ 0 (pânico total)."""

# ---------------------------------------------------------------------------
# Fuga do inimigo
# ---------------------------------------------------------------------------

FUGA_ENTRADA_MIN = 0.0
"""Limiar mínimo de moral para o inimigo entrar em modo fuga."""

FUGA_ENTRADA_MAX = 35.0
"""Limiar máximo de moral para o inimigo entrar em modo fuga."""

FUGA_SAIDA_MIN = 35.0
"""Limiar mínimo de moral para o inimigo sair do modo fuga."""

FUGA_SAIDA_MAX = 70.0
"""Limiar máximo de moral para o inimigo sair do modo fuga."""

ALCANCE_FUGA_ESCAPE = 900.0
"""Distância (unidades) que o inimigo precisa manter para o timer de fuga avançar."""

TEMPO_FUGA_ESCAPE_SEG = 15.0
"""Segundos que o inimigo precisa ficar além de ALCANCE_FUGA_ESCAPE para escapar."""

# ---------------------------------------------------------------------------
# Mundo aberto (esqueleto mínimo)
# ---------------------------------------------------------------------------

MUNDO_TAMANHO = 8000.0
"""Lado do mundo aberto toroidal, em unidades de jogo (8km)."""

MUNDO_NUM_INIMIGOS = 8
"""Quantos navios inimigos existem simultaneamente espalhados pelo mundo."""

MUNDO_ESPACAMENTO_MIN = 1000.0
"""Distância mínima entre navios inimigos entre si e do jogador ao sortear
novas posições de spawn."""

MUNDO_GATILHO_COMBATE = 750.0
"""Distância que aciona a transição automática pro loop de combate."""

MUNDO_ZOOM_NAV_FIXO = 800
"""Zoom fixo do MAPA DE NAVEGAÇÃO quando não há combate ativo (deve ser
um dos valores em ZOOM_NIVEIS)."""

MUNDO_ALCANCE_VISAO_FUGA = 900.0
"""Distância dentro da qual um navio em modo fuga no mundo foge ativamente
do jogador."""

MUNDO_TICK = 0.5
"""Intervalo de simulação do mundo em navegação livre (mesmo valor de SIM_TICK)."""

MUNDO_NUM_PORTOS = 2
"""Número de portos fixos espalhados pelo mundo."""

MUNDO_NUM_ILHAS = 10
"""Número de ilhas espalhadas pelo mundo (geração determinística)."""

ILHA_RAIO_MIN = 150.0
"""Raio base mínimo de uma ilha, em unidades de jogo."""

ILHA_RAIO_MAX = 400.0
"""Raio base máximo de uma ilha, em unidades de jogo."""

ILHA_PORTO_EXCLUSAO = 800.0
"""Distância mínima entre o centro de uma ilha e o spawn do jogador ou qualquer porto."""

DANO_COLISAO_BASE = 6.0
"""Dano base de colisão com ilha (% do casco) à velocidade zero."""

DANO_COLISAO_K = 1.5
"""Expoente da curva de dano por colisão (mais velocidade → mais dano exponencialmente)."""

DANO_COLISAO_V_REF = 13.0
"""Velocidade de referência para normalizar o dano de colisão (vel. máx do Galeão)."""

MUNDO_RAIO_ATRACACAO = 250.0
"""Distância máxima para poder usar o comando 'atracar'."""

MUNDO_RAIO_COLETA_LOOT = 250.0
"""Distância máxima para coletar automaticamente destroços de um navio afundado."""

# ---------------------------------------------------------------------------
# Dinâmica da água
# ---------------------------------------------------------------------------

AGUA_BASE = 2.0
"""Taxa base de entrada de água (multiplicada exponencialmente pelo dano)."""

AGUA_K = 3.0
"""Expoente da curva de inundação: torna a entrada de água muito mais
rápida quando o casco está severamente danificado."""

AGUA_CRITICA_LIMIAR = 70.0
"""Nível de água (%) a partir do qual o HUD fica vermelho como alerta."""

# ---------------------------------------------------------------------------
# Navegação / UI
# ---------------------------------------------------------------------------

DIRECOES = ['N ', 'NE', 'E ', 'SE', 'S ', 'SW', 'W ', 'NW']
"""Rótulos dos 8 pontos cardeais / colaterais, no sentido horário."""

ARROWS_ASCII = ['^', '/', '>', '\\', 'v', '/', '<', '\\']
"""Setas ASCII para os 8 rumos (fallback sem Unicode)."""

ARROWS_UNICODE = ['↑', '↗', '→', '↘',
                  '↓', '↙', '←', '↖']
"""Setas Unicode para os 8 rumos (↑ ↗ → ↘ ↓ ↙ ← ↖)."""

COMANDOS = ["leme", "vela", "reparar", "bomba", "canhao", "radar", "ajuda", "fugir"]
"""Comandos de texto aceitos no prompt do jogo."""

CANHAO_SUBCMDS = ["trip", "mirar", "parar"]
"""Subcomandos válidos para o comando 'canhao'."""

ALIASES = {"l": "leme", "v": "vela", "r": "reparar", "b": "bomba", "c": "canhao", "f": "fugir"}
"""Atalhos de uma letra para comandos completos."""

REPARO_CREW_PADRAO = 1
"""Quantidade padrão de tripulantes enviada a reparo quando não especificado."""

HOTKEY_PASSO_MIRA = 25.0
"""Incremento/decremento de distância de mira por toque de hotkey (metros)."""

HOTKEY_PASSO_LEME = 15.0
"""Incremento/decremento de rumo por toque de hotkey (graus)."""

SIMB_TRIPULANTE = "\\o/"
"""Símbolo ASCII que representa um tripulante na lista de tripulação."""

SIMB_CAPITAO = "^x^"
"""Símbolo ASCII do capitão (usado no cabeçalho da visão)."""

# ---------------------------------------------------------------------------
# Zoom do mapa
# ---------------------------------------------------------------------------

ZOOM_NIVEIS = [200, 400, 800, 1600, 3200]
"""Níveis fixos de zoom do mapa (em unidades de jogo = metade do alcance)."""

ZOOM_HISTERESE = 0.7
"""Fração do nível abaixo que deve ser atingida para reduzir o zoom,
evitando oscilações rápidas quando os navios estão na fronteira de dois níveis."""

# ---------------------------------------------------------------------------
# IDs de pares de cor curses
# ---------------------------------------------------------------------------

COR_VERDE = 1
COR_AMARELO = 2
COR_VERMELHO = 3
COR_JOGADOR = 4   # ciano
COR_INIMIGO = 5   # magenta
COR_MAR = 6       # azul
COR_ILHA = 7      # amarelo (terra/areia)

# ---------------------------------------------------------------------------
# Tipos de navio / dificuldade
# ---------------------------------------------------------------------------

DIFICULDADES = ["facil", "normal", "dificil"]
"""Chaves válidas para NAVIO_TIPOS, na ordem do menu de seleção."""

NAVIO_TIPOS = {
    "facil": {
        "navio": "Chalupa",
        "crew_total": 2,
        "canhoes_lado": 1,
        "num_velas": 1,
        "velocidade_max_base": 8.0,
        "giro_graus_seg": 14.0,
        "cooldown_mult": 1.4,   # recarga mais lenta = mais fácil de sobreviver
        "erro_mira": 80.0,      # grande margem de erro na IA
        "min_crew_canhao": 1,
        "reparo_mult": 1.5,     # Chalupa repara mais rápido
        "porao_capacidade": 6,
    },
    "normal": {
        "navio": "Bergantim",
        "crew_total": 3,
        "canhoes_lado": 2,
        "num_velas": 3,
        "velocidade_max_base": 11.0,
        "giro_graus_seg": 9.0,
        "cooldown_mult": 1.0,
        "erro_mira": 40.0,
        "min_crew_canhao": 1,
        "reparo_mult": 1.0,     # Bergantim — velocidade de reparo média
        "porao_capacidade": 9,
    },
    "dificil": {
        "navio": "Galeao",
        "crew_total": 7,
        "canhoes_lado": 3,
        "num_velas": 7,
        "velocidade_max_base": 13.0,
        "giro_graus_seg": 6.0,
        "cooldown_mult": 0.7,   # recarga mais rápida = mais perigoso
        "erro_mira": 15.0,      # IA mira com precisão
        "min_crew_canhao": 2,
        "reparo_mult": 0.7,     # Galeão repara mais devagar
        "porao_capacidade": 14,
    },
}
"""Parâmetros de cada tipo de navio. O inimigo usa o mesmo perfil que o jogador
(simetria total), então a dificuldade vem do gerenciamento de recursos, não de
atributos assimétricos."""

# ---------------------------------------------------------------------------
# Economia / Loja
# ---------------------------------------------------------------------------

PRECO_BARRIL_NOVO = 5.0
"""Ouro por barril cheio (25 unidades) comprado na loja."""

PRECO_REABASTECER_POR_UNIDADE = 0.4
"""0.4/unidade: ponto de virada em 12.5 unidades (= 5.0 ouro = preço de um
barril novo cheio). Reabastecer mais que isso fica mais caro que comprar novo."""

PRECO_VENDA_BARRIL_CHEIO = 3.0
"""Preço de venda de um barril cheio; venda proporcional ao conteúdo restante."""

PRECO_REPARO_POR_PONTO_DANO = 0.5
"""Ouro por ponto percentual de dano reparado no porto."""

PRECO_NAVIO_NOVO = {"facil": 50, "normal": 100, "dificil": 200}
"""Preço de compra de um navio novo, por tipo."""

PRECO_RENOMEAR = 20.0
"""Ouro para renomear um navio."""

PRECO_UPGRADE = {
    "casco_max":        40.0,   # +10 HP máx. casco
    "cooldown":         60.0,   # -10% cooldown canhão
    "porao_slot":       50.0,   # +1 slot de porão
    "tripulante_extra": 80.0,   # +1 tripulante acima do máximo do tipo
    "velocidade_giro":  70.0,   # +10% velocidade/giro
    "alcance_canhao":   50.0,   # +50m alcance
}
"""Preços dos upgrades permanentes por navio."""

PRECO_ITENS_TOPO = {
    "casco_lendario":  600.0,   # +50% resistência efetiva de casco
    "alcance_lendario": 450.0,  # +120m alcance (empilha com upgrade normal)
    "porao_lendario":   500.0,  # +3 slots de porão de uma vez
}
"""Preços dos itens de topo, desbloqueados por faixa de notoriedade."""

FAIXA_MINIMA_ITEM_TOPO = {
    "casco_lendario":  6,   # índice 6 = "Terror dos Sete Mares"
    "alcance_lendario": 6,
    "porao_lendario":   7,  # índice 7 = "Lenda Viva"
}
"""Índice mínimo (0-indexado) em NOTORIEDADE_FAIXAS exigido para cada item de topo."""

# ---------------------------------------------------------------------------
# Arte ASCII
# ---------------------------------------------------------------------------

TITULO_ARTE = [
    "  ..|'''.| '||'      '||'    '||''|.  '||' '||''|.       |     |''||''| '||''''|   .|'''.|",
    ".|'     '   ||        ||      ||   ||  ||   ||   ||     |||       ||     ||  .     ||..  '",
    "||          ||        ||      ||...|'  ||   ||''|'     |  ||      ||     ||''|      ''|||.",
    "'|.      .  ||        ||      ||       ||   ||   |.   .''''|.     ||     ||       .     '||",
    " ''|....'  .||.....| .||.    .||.     .||. .||.  '|' .|.  .||.   .||.   .||.....| |'....|'",
    "",
    "                       um jogo de comando naval em tempo real",
]

ARTE_VITORIA = [
    "        |         |         |",
    "       )_)       )_)       )_)",
    "      )___)     )___)     )___)",
    "     )____)    )____)    )_____)",
    "  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~",
    "       O NAVIO INIMIGO AFUNDOU!",
]

ARTE_DERROTA = [
    "                    |",
    "                   )_)",
    "                  )___)",
    "                 )____)",
    "  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~",
    "           SEU NAVIO AFUNDOU...",
]

ARTE_FUGA = [
    "  ~  ~  ~  ~  ~  ~  ~  ~  ~  ~",
    "          [ SHIP ]-->-->-->",
    "  ~  ~  ~  ~  ~  ~  ~  ~  ~  ~",
    "",
    "     O INIMIGO FUGIU NO HORIZONTE!",
]

ARTE_FUGA_JOGADOR = [
    "  ~  ~  ~  ~  ~  ~  ~  ~  ~  ~",
    "  <--<--<--[ SEU NAVIO ]",
    "  ~  ~  ~  ~  ~  ~  ~  ~  ~  ~",
    "",
    "     VOCE ESCAPOU NO HORIZONTE!",
]

COMO_JOGAR_TEXTO = [
    "COMO JOGAR",
    "",
    "CLI PIRATES e um jogo naval em tempo real. Voce navega um mundo",
    "aberto de 8km x 8km, enfrenta inimigos, coleta loot e administra",
    "recursos (polvora, bolas, tabuas, ouro) no porao do seu navio.",
    "",
    "NAVIOS   Chalupa (facil): 2 trip, 1 canhao/lado, 6 slots porao",
    "         Bergantim (medio): 3 trip, 2 canhoes/lado, 9 slots",
    "         Galeao (dificil): 7 trip, 3 canhoes/lado, 14 slots",
    "",
    "MUNDO ABERTO",
    "  M              alterna mapa de navegacao / mapa mundo (8km)",
    "  V              abre o inventario do porao",
    "  ESC            volta ao menu",
    "  mapa / radar   mesmo que M / leitura do inimigo mais proximo",
    "  atracar        ancora no porto (precisa estar a menos de 150m do P)",
    "",
    "  Inimigo a menos de 750m = combate automatico (mesmo mapa).",
    "  Porto desaparece do mapa durante a batalha.",
    "  Vitoria: volta a navegar preservando todo o estado.",
    "  Navio afundado: tela de derrota.",
    "",
    "PORTO (comando 'atracar')",
    "  WASD           move o capitao pela cena",
    "  Loja polvora/bolas/tabuas: comprar barril, reabastecer, vender",
    "  Loja de navios: comprar novo navio, trocar ativo, renomear",
    "  Upgrades: casco, cooldown, porao, tripulacao, velocidade, alcance",
    "  Doca: zarpar de volta ao mundo",
    "",
    "COMBATE (comandos durante a batalha)",
    "  leme <graus>             define o rumo (0-360)  alias: l",
    "  vela <0-3>               nivel de vela          alias: v",
    "  reparar <parte> <trip>   reparo continuo        alias: r",
    "  bomba <trip>             tripulantes nas bombas alias: b",
    "  canhao <id> <dist>       aloca e mira           alias: c",
    "  canhao <id> parar        para e libera crew",
    "  radar                    distancia/rumo exatos do inimigo",
    "  fugir                    tenta escapar (fica a 900m+ por 15s) alias: f",
    "                           inimigo nao pode estar fugindo; custa notoriedade",
    "  ENTER vazio              repete o ultimo comando",
    "",
    "  Canhao consome 1 polvora + 1 bola por tiro.",
    "  Reparo consome tabuas (0.15/HP). Sem tabuas = reparo reduzido.",
    "  Ouro e fisico — fica no porao, sem banco.",
    "",
    "HOTKEYS (prompt vazio, com ou sem SHIFT)",
    "  a / d   leme estibordo / bombordo (+15 graus)",
    "  w / s   vela ++ / vela --",
    "  j / l   seleciona canhao bombordo / estibordo",
    "  i / k   mira +25m / -25m",
    "  espaco  atirar/parar | reparo ++",
    "  u / h   bombas ++ / --",
    "  e / r   circula partes de reparo / reparo --",
    "",
    "Pressione qualquer tecla para voltar ao menu.",
]
