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

# ---------------------------------------------------------------------------
# Vento (doc08_vento.md)
# ---------------------------------------------------------------------------

VENTO_INTENSIDADE_MIN = 0.0
VENTO_INTENSIDADE_MAX = 25.0
"""Piso/teto de intensidade de vento, em nós."""

VENTO_INTENSIDADE_LIMITE_FRACA = 5.0
VENTO_INTENSIDADE_LIMITE_MODERADA = 15.0
"""Limites da curva de intensidade: até LIMITE_FRACA, sobe de calmaria até
potência plena; entre os dois, platô de potência plena; acima de
LIMITE_MODERADA, sobe até o teto de rajada em VENTO_INTENSIDADE_MAX."""

VENTO_MULT_INTENSIDADE_CALMARIA = 0.5
VENTO_MULT_INTENSIDADE_PLENA = 1.0
VENTO_MULT_INTENSIDADE_MAXIMA = 1.3
"""Multiplicadores-âncora de velocidade máxima pela curva de intensidade:
0.5 em 0 nós (calmaria), 1.0 do início do platô (5 nós) até o fim dele
(15 nós), 1.3 no teto de rajada (25 nós). Curva suave, sem degraus –
interpolação linear entre âncoras (ver fator_intensidade_vento)."""

VENTO_DERIVA_DIRECAO_GRAUS_SEG = 0.1
"""Velocidade de deriva da direção do vento em direção ao alvo sorteado,
em graus/segundo. Placeholder – não calibrado."""

VENTO_DERIVA_INTENSIDADE_SEG = 0.05
"""Velocidade de deriva da intensidade do vento em direção ao alvo
sorteado, por segundo. Placeholder – não calibrado."""

VENTO_RESORTEIO_MIN_SEG = 300.0
VENTO_RESORTEIO_MAX_SEG = 600.0
"""Intervalo (min, max) em segundos entre resorteios do alvo de deriva do
vento. Placeholder – não calibrado."""

VENTO_ZONAS_ANGULO_MEIO = {
    "zona_morta": 22.5,
    "bolina": 67.5,
    "traves": 112.5,
    "popa": 157.5,
}
"""Ângulo relativo (0°=proa) representado pelo valor de eficiência de cada
zona, usado como ponto-chave pra interpolação linear (ver pirates/core/vento.py)."""

IA_VENTO_MARGEM_SAIDA_GRAUS = 5.0
"""Buffer além do limite de 45° da zona morta que a IA tenta alcançar ao
corrigir o rumo, pra evitar oscilar entrando/saindo da zona morta a cada
tick. Placeholder – não calibrado."""

IA_VENTO_CORRECAO_MAX_GRAUS = 40.0
"""Correção máxima de rumo (graus) que a IA aplica pra sair da zona morta
em combate normal (aproximar/afastar/circular). Placeholder – não
calibrado."""

IA_VENTO_CORRECAO_MAX_FUGA_GRAUS = 70.0
"""Correção máxima de rumo (graus) em modo fuga – maior que em combate
normal, porque velocidade importa mais que manter a direção exata oposta
ao jogador quando fugindo. Placeholder – não calibrado."""
# ---------------------------------------------------------------------------
# Deriva lateral (doc09_deriva.md)
# ---------------------------------------------------------------------------

BASE_ADERENCIA = 3.0
"""Coeficiente base da força de correção de deriva lateral, em 1/segundo.
Placeholder – não calibrado, mesma ordem de grandeza de ACEL_VEL_SEG."""

VELOCIDADE_REFERENCIA_ADERENCIA = 10.0
"""Velocidade de referência (unidades/s) usada no fator de aderência por
velocidade: quanto mais rápido o navio, mais aderência (fator_velocidade
= 1 + vel_atual / VELOCIDADE_REFERENCIA_ADERENCIA)."""

PESO_REFERENCIA_ADERENCIA = 500.0
"""Peso de referência (kg) usado no fator de aderência por peso – igual
ao peso_casco do Bergantim, tratado como o ponto neutro (fator_peso = 1.0)."""

COEFICIENTE_EMPUXO_LATERAL = 0.05
"""Coeficiente do empuxo lateral de vento de través sobre velocidade
lateral, em (unidades/s) por (nó × num_velas). Placeholder – não
calibrado."""

K_ARRASTO_CASCO = 0.018
"""Coeficiente de arrasto de água — usado no equilíbrio empuxo-vs-arrasto
que define a velocidade máxima física do navio (doc08_vento.md §6).
Placeholder – não calibrado."""

C_ARRASTO = 0.006
"""Coeficiente de arrasto aerodinâmico do casco — usado no empuxo
constante de vento (vento empurrando o navio mesmo parado/sem vela,
doc08_vento.md §7.4). Placeholder – não calibrado."""

AREA_CASCO = {"chalupa": 8.5, "brigantim": 16.0, "galeao": 27.0}
"""Área de casco exposta ao vento/água por tipo de navio (m² nominais),
usada no equilíbrio de velocidade máxima e no empuxo constante."""

PESO_CASCO = {"chalupa": 200.0, "brigantim": 500.0, "galeao": 1100.0}
"""Peso do casco vazio por tipo de navio (kg), usado na força de correção
de deriva lateral e no empuxo constante de vento."""

DERIVA_LIMIAR_DIRECAO = 0.05
"""Abaixo deste valor (unidades/s) a deriva lateral é considerada nula
pro HUD (mostra '--' em vez de ESTIB/BOMB)."""

DERIVA_LIMIAR_REFERENCIA = 1.5
"""Deriva lateral (unidades/s) tratada como 100% na barra de cor do HUD."""

PRECO_TROCA_VELA = {"chalupa": 30.0, "brigantim": 60.0, "galeao": 90.0}
"""Preço (ouro) pra trocar o tipo de uma vela de proa/mastro/popa já
existente, por tipo de navio."""

PRECO_INSTALAR_AUX = {"topo_quadrada": 50.0, "vela_de_asa": 70.0}
"""Preço (ouro) pra instalar/trocar uma vela auxiliar, por tipo de vela."""

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

MORAL_CRASH_RECURSOS_TETO = 15.0
"""Teto de moral imposto temporariamente quando pólvora, bolas ou tábuas
zeram. Moral não sobe acima disso enquanto o travamento estiver ativo."""

MORAL_CRASH_RECURSOS_DURACAO_SEG = 20.0
"""Duração (segundos) do travamento de moral após pólvora/bolas/tábuas
zerarem. Passado esse tempo, a moral volta a seguir moral_alvo() livremente."""

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

COMANDOS = ["leme", "vela", "reparar", "bomba", "canhao", "radar", "ajuda", "fugir", "ancorar"]
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
# Velas — tabela por tipo de vela (doc08_vento.md §5, doc10_customizacao_vela.md §2)
# ---------------------------------------------------------------------------

TIPOS_VELA = {
    "quadrada": {
        "eficiencia_vento": {"zona_morta": 0.15, "bolina": 0.40, "traves": 0.75, "popa": 1.00},
        "bonus_fixo": 0.40,
        "bonus_curva": 0.0,
        "auxiliar": False,
    },
    "latina": {
        "eficiencia_vento": {"zona_morta": 0.85, "bolina": 1.00, "traves": 0.90, "popa": 0.70},
        "bonus_fixo": 0.20,
        "bonus_curva": 0.10,
        "auxiliar": False,
    },
    "estai": {
        "eficiencia_vento": {"zona_morta": 0.60, "bolina": 0.80, "traves": 1.00, "popa": 0.85},
        "bonus_fixo": 0.10,
        "bonus_curva": 0.35,
        "auxiliar": False,
    },
    "carangueja": {
        "eficiencia_vento": {"zona_morta": 0.70, "bolina": 0.90, "traves": 1.00, "popa": 0.80},
        "bonus_fixo": 0.25,
        "bonus_curva": 0.15,
        "auxiliar": False,
    },
    "topo_quadrada": {
        "eficiencia_vento": {"zona_morta": 0.05, "bolina": 0.15, "traves": 0.40, "popa": 1.25},
        "bonus_fixo": 0.15,
        "bonus_curva": 0.0,
        "auxiliar": True,
    },
    "vela_de_asa": {
        "eficiencia_vento": {"zona_morta": 0.0, "bolina": 0.0, "traves": 0.0, "popa": 2.00},
        "bonus_fixo": 0.05,
        "bonus_curva": 0.0,
        "auxiliar": True,
    },
}
"""Parâmetros por tipo de vela. 'estai' nunca conta na soma de velocidade
(eficiencia_vento, bonus_fixo) — só entra na soma de bonus_curva, onde
quer que o slot esteja."""

LOADOUT_VELA_FABRICA = {
    "chalupa": [
        {"local": "proa",       "tipo": "estai",  "nivel": 1},
        {"local": "principal",  "tipo": "latina", "nivel": 1},
        {"local": "aux-1",      "tipo": None,     "nivel": 0},   # vazio
    ],
    "brigantim": [
        {"local": "proa",       "tipo": "estai",     "nivel": 1},
        {"local": "principal",  "tipo": "quadrada",  "nivel": 1},
        {"local": "popa",       "tipo": "carangueja","nivel": 1},
        {"local": "aux-1",      "tipo": None,        "nivel": 0},
        {"local": "aux-2",      "tipo": None,        "nivel": 0},
    ],
    "galeao": [
        {"local": "proa",         "tipo": "estai",         "nivel": 1},
        {"local": "principal-1",  "tipo": "quadrada",      "nivel": 1},
        {"local": "principal-2",  "tipo": "quadrada",      "nivel": 1},
        {"local": "principal-3",  "tipo": "quadrada",      "nivel": 1},
        {"local": "popa",         "tipo": "carangueja",    "nivel": 1},
        {"local": "aux-1",        "tipo": "topo_quadrada", "nivel": 1},
        {"local": "aux-2",        "tipo": "topo_quadrada", "nivel": 1},
        {"local": "aux-3",        "tipo": None,            "nivel": 0},  # vazio
    ],
}
"""Loadout inicial de slots de vela por tipo de navio. tipo: None = slot
auxiliar existente mas vazio. Nenhum slot pode ser criado além desta
lista — o loadout de fábrica é o teto de quantos slots um navio tem."""

# ---------------------------------------------------------------------------
# Tipos de navio / dificuldade
# ---------------------------------------------------------------------------

TIPOS_NAVIO = ["chalupa", "brigantim", "galeao"]
"""Chaves válidas para NAVIO_TIPOS, na ordem do menu de seleção."""

NAVIO_TIPOS = {
    "chalupa": {
        "navio": "Chalupa",
        "crew_total": 2,
        "canhoes_lado": 1,
        "num_velas": 1,
        "velocidade_max_base": 8.0,
        "giro_graus_seg": 45.0,
        "cooldown_mult": 1.4,   # recarga mais lenta = mais fácil de sobreviver
        "erro_mira": 80.0,      # grande margem de erro na IA
        "min_crew_canhao": 1,
        "reparo_mult": 1.5,     # Chalupa repara mais rápido
        "porao_capacidade": 6,
    },
    "brigantim": {
        "navio": "Brigantim",
        "crew_total": 3,
        "canhoes_lado": 2,
        "num_velas": 3,
        "velocidade_max_base": 11.0,
        "giro_graus_seg": 25.0,
        "cooldown_mult": 1.0,
        "erro_mira": 40.0,
        "min_crew_canhao": 1,
        "reparo_mult": 1.0,     # Brigantim — velocidade de reparo média
        "porao_capacidade": 9,
    },
    "galeao": {
        "navio": "Galeao",
        "crew_total": 7,
        "canhoes_lado": 3,
        "num_velas": 7,
        "velocidade_max_base": 14.0,
        "giro_graus_seg": 12.0,
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

PRECO_NAVIO_NOVO = {"chalupa": 70, "brigantim": 150, "galeao": 300}
"""Preço BASE de compra de um navio novo, por tipo (antes do multiplicador
de frota — ver comprar_navio_loja, que escala por quantos navios daquele
tipo o jogador já possui)."""

PRECO_RENOMEAR = 20.0
"""Ouro para renomear um navio."""

PRECO_TRANSFERENCIA_FROTA = 5.0
"""Ouro cobrado por transferência de um barril entre navios da frota.
Se o barril transferido é de ouro, a taxa sai do próprio barril; senão,
tenta debitar do navio de origem e, se não tiver, do navio de destino."""

PRECO_UPGRADE = {
    "casco_max":              60.0,   # +10 HP máx. casco
    "cooldown":               90.0,   # -10% cooldown canhão
    "porao_slot":             75.0,   # +1 slot de porão
    "tripulante_extra":      120.0,   # +1 tripulante acima do máximo do tipo
    "velocidade_giro":       100.0,   # +10% velocidade/giro
    "alcance_canhao":         75.0,   # +50m alcance
    "capacidade_barril_ouro": 50.0,   # +10 capacidade barril ouro
}
"""Preços dos upgrades permanentes por navio."""

TAXA_CRESCIMENTO_UPGRADE = {"capacidade_barril_ouro": 1.30}
"""Taxa de crescimento de preço por nível, só pras chaves listadas aqui.
Qualquer upgrade que não apareça usa a taxa padrão de 1.5 (ver
lojas.preco_upgrade_nivel)."""

PRECO_ITENS_TOPO = {
    "casco_lendario":  900.0,   # +50% resistência efetiva de casco
    "alcance_lendario": 700.0,  # +120m alcance (empilha com upgrade normal)
    "porao_lendario":   800.0,  # +3 slots de porão de uma vez
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
    "NAVIOS   Chalupa (dificuldade 1): 2 trip, 1 canhao/lado, 6 slots porao",
    "         Brigantim (dificuldade 2): 3 trip, 2 canhoes/lado, 9 slots",
    "         Galeao (dificuldade 3): 7 trip, 3 canhoes/lado, 14 slots",
    "",
    "VENTO E VELAS",
    "  Vale em combate, arena e navegacao no mundo aberto. Direcao e",
    "  intensidade do vento mudam lentamente com o tempo (ver HUD: VENTO).",
    "  Cada navio tem slots de vela individuais (proa/mastros/popa/",
    "  auxiliares) - cada um com um tipo de vela e um nivel (0/50/100%).",
    "  Nao ha teto artificial de velocidade: ela emerge do equilibrio",
    "  entre o empuxo somado das suas velas e o arrasto do casco.",
    "  O angulo do casco em relacao ao vento define 4 zonas (zona morta,",
    "  bolina, traves, popa) - a zona ideal varia por tipo de vela, veja",
    "  'Tipos de Navio' pra saber a do seu loadout de fabrica.",
    "  Vento fraco reduz o teto de velocidade; vento forte (rajada) aumenta.",
    "  Virar o leme bruscamente e vento de traves geram deriva lateral -",
    "  o navio desliza de lado, corrigida aos poucos pela aderencia do casco.",
    "  Comando 'ancorar' zera a velocidade-alvo e os empuxos de vento",
    "  (o leme continua funcionando). Troque/instale velas na Loja de",
    "  Navios de qualquer porto.",
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
    "  Velas: trocar tipo de vela (proa/mastro/popa) ou instalar/trocar",
    "  vela auxiliar - nunca cria slot novo, so troca o que ja existe",
    "  Doca: zarpar de volta ao mundo",
    "",
    "COMANDOS (combate, arena ou navegacao)",
    "  leme <graus>             define o rumo (0-360)  alias: l",
    "  vela                     lista os slots de vela do navio",
    "  vela <0-2>               nivel do slot selecionado alias: v",
    "  vela <ID> <0-2>          nivel de um slot especifico",
    "  ancorar                  liga/desliga a ancora (leme continua livre)",
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
    "  q       cicla o slot de vela selecionado",
    "  w / s   nivel ++ / -- do slot de vela selecionado",
    "  j / l   seleciona canhao bombordo / estibordo",
    "  i / k   mira +25m / -25m",
    "  espaco  atirar/parar | reparo ++",
    "  u / h   bombas ++ / --",
    "  e / r   circula partes de reparo / reparo --",
    "",
    "Pressione qualquer tecla para voltar ao menu.",
]
