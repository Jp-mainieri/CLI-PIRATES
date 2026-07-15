"""
constants.py – Constantes e configuração global de CLI PIRATES.

Todas as constantes numéricas, listas de referência, textos de arte ASCII
e definições de tipos de navio vivem aqui. Alterar valores neste módulo
afeta o equilíbrio do jogo globalmente.
"""

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

FUGA_SAIDA_MAX = 50.0
"""Limiar máximo de moral para o inimigo sair do modo fuga."""

ALCANCE_FUGA_ESCAPE = 900.0
"""Distância (unidades) que o inimigo precisa manter para o timer de fuga avançar."""

TEMPO_FUGA_ESCAPE_SEG = 15.0
"""Segundos que o inimigo precisa ficar além de ALCANCE_FUGA_ESCAPE para escapar."""

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

COMANDOS = ["leme", "vela", "reparar", "bomba", "canhao", "radar", "ajuda"]
"""Comandos de texto aceitos no prompt do jogo."""

CANHAO_SUBCMDS = ["trip", "mirar", "parar"]
"""Subcomandos válidos para o comando 'canhao'."""

ALIASES = {"l": "leme", "v": "vela", "r": "reparar", "b": "bomba", "c": "canhao"}
"""Atalhos de uma letra para comandos completos."""

REPARO_CREW_PADRAO = 2
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
        "reparo_mult": 1.0,
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
        "reparo_mult": 1.0,
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
        "reparo_mult": 1.0,
    },
}
"""Parâmetros de cada tipo de navio. O inimigo usa o mesmo perfil que o jogador
(simetria total), então a dificuldade vem do gerenciamento de recursos, não de
atributos assimétricos."""

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

COMO_JOGAR_TEXTO = [
    "COMO JOGAR",
    "",
    "O jogo roda em tempo real. O navio se move, a agua sobe e os",
    "canhoes atiram sozinhos - voce da ordens a qualquer momento.",
    "",
    "No menu, escolha seu navio: CHALUPA (facil, 2 tripulantes, 1 canhao",
    "por lado, 1 vela), BERGANTIM (medio, 3 tripulantes, 2 canhoes por",
    "lado, 3 velas) ou GALEAO (dificil, 7 tripulantes, 3 canhoes por",
    "lado, 7 velas). Chalupa e Bergantim precisam de so 1 tripulante",
    "por canhao; o Galeao exige 2 por canhao.",
    "",
    "COMANDOS (ENTER confirma; ESC sai do jogo; TAB circula opcoes)",
    "  leme <graus>  (ou 'l')                define o rumo (0-360)",
    "  vela <0-3>    (ou 'v')                define o nivel de vela",
    "  reparar <parte> <trip>  (ou 'r')      conserta continuamente",
    "                                        (parte: casco,mastro,vela,roda)",
    "  bomba <trip>  (ou 'b')                aloca gente nas bombas",
    "  canhao <id> <trip> <distancia>  (ou 'c')  aloca e mira num comando",
    "  canhao <id> <distancia>               aloca a tripulacao minima do",
    "                                        canhao (1 ou 2, conforme o navio)",
    "  canhao <id> trip <n>                  so realoca tripulacao",
    "  canhao <id> mirar <distancia>         so muda a mira",
    "  canhao <id> parar                     para de atirar e libera a",
    "                                        tripulacao (fica ociosa)",
    "  radar                                 leitura exata de distancia/rumo",
    "  ajuda                                 mostra os comandos no log",
    "  ENTER vazio                           repete o ultimo comando",
    "",
    "  <id> do canhao: E1,E2,... (estibordo) ou B1,B2,... (bombordo),",
    "  a quantidade varia conforme o navio escolhido.",
    "",
    "REALOCACAO AUTOMATICA: se voce pede tripulantes e nao tem gente",
    "livre, o jogo puxa de outras tarefas por prioridade: primeiro de",
    "canhoes (libera o canhao inteiro), depois de reparo (parcial).",
    "A tripulacao da BOMBA nunca e tocada automaticamente. Se ainda",
    "assim faltar gente, o comando completa com o que der e avisa.",
    "",
    "HOTKEYS (ligar em Ajustes) - so funcionam com o prompt vazio,",
    "funcionam com ou sem SHIFT:",
    "  a / d      leme 15 graus p/ direita(estibordo) / esquerda(bombordo)",
    "  w / s      vela ++ / vela --",
    "  j / l      seleciona proximo canhao de bombordo / estibordo",
    "  i / k      ajusta a mira do canhao selecionado (+/- 25m)",
    "  espaco     canhao: alterna atirar/parar | reparo: reparo ++",
    "  u / h      bombear ++ / bombear --",
    "  e / r      e: entra/circula pelas partes p/ reparo | r: reparo --",
    "",
    "A agua entra de forma EXPONENCIAL conforme o casco se danifica.",
    "Dano leve: as bombas seguram. Dano severo: nem toda a tripulacao",
    "nas bombas vai impedir o naufragio - conserte o casco a tempo!",
    "",
    "Pressione qualquer tecla para voltar ao menu.",
]
