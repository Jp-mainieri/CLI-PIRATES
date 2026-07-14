#!/usr/bin/env python3
"""
CLI PIRATES - modo tempo real
=================================
Sem game engine (usa apenas 'curses', da biblioteca padrao). Por padrao a
UI e 100% ASCII, sem emojis. Dois modos opcionais em Ajustes:
  - Cores: colore barras de saude/recarga e o log (verde/amarelo/vermelho).
  - Graficos Unicode: setas de rumo no mapa e navios entre colchetes/chaves
    ({seu navio} / [inimigo]) em vez do codigo de bussola de 2 letras.
Ambos caem de volta pro modo seguro se o terminal nao suportar.

O navio se move, a agua sobe, os reparos avancam e os canhoes atiram
sozinhos continuamente - voce da ordens a qualquer momento, sem "turnos".

COMO RODAR
  python3 batalha_naval.py
  (precisa de um terminal de verdade / TTY. Recomendo uma janela grande,
   ~100 colunas x 45 linhas, pra ver tudo sem cortar.)
"""

import locale
import math
import random
import sys
import time
from collections import deque

try:
    import curses
except ImportError:
    curses = None

# ----------------------------------------------------------------------
# CONFIGURACAO
# ----------------------------------------------------------------------

PARTES = ['casco', 'mastro', 'vela', 'roda']
PARTES_CRITICAS = ['casco']
MAPA_TAMANHO = 1200

SIM_TICK = 0.5
POLL_MS = 100

GIRO_GRAUS_SEG_PADRAO = 9.0
ACEL_VEL_SEG = 3.0
TAXA_REPARO_SEG = 3.0
REPARO_K = 3.5  # quanto maior, mais brusca a queda de eficiencia com dano alto
SAIDA_BOMBA_SEG = 2.5
COOLDOWN_CANHAO = 12.0
CHANCE_DANO_CANHAO = 30.0

AGUA_BASE = 2.0
AGUA_K = 3.0
AGUA_CRITICA_LIMIAR = 70.0

DIRECOES = ['N ', 'NE', 'E ', 'SE', 'S ', 'SW', 'W ', 'NW']
ARROWS_ASCII = ['^', '/', '>', '\\', 'v', '/', '<', '\\']
ARROWS_UNICODE = ['\u2191', '\u2197', '\u2192', '\u2198', '\u2193', '\u2199', '\u2190', '\u2196']
COMANDOS = ["leme", "vela", "reparar", "bomba", "canhao", "radar", "ajuda"]
CANHAO_SUBCMDS = ["trip", "mirar", "parar"]

ALIASES = {"l": "leme", "v": "vela", "r": "reparar", "b": "bomba", "c": "canhao"}
REPARO_CREW_PADRAO = 2
HOTKEY_PASSO_MIRA = 25.0
HOTKEY_PASSO_LEME = 15.0

SIMB_TRIPULANTE = "\\o/"
SIMB_CAPITAO = "^x^"

ZOOM_NIVEIS = [200, 400, 800, 1600, 3200]
ZOOM_HISTERESE = 0.7

COR_VERDE = 1
COR_AMARELO = 2
COR_VERMELHO = 3
COR_JOGADOR = 4
COR_INIMIGO = 5
COR_MAR = 6

DIFICULDADES = ["facil", "normal", "dificil"]
NAVIO_TIPOS = {
    "facil": {
        "navio": "Chalupa", "crew_total": 2, "canhoes_lado": 1, "num_velas": 1,
        "velocidade_max_base": 8.0, "giro_graus_seg": 14.0,
        "cooldown_mult": 1.4, "erro_mira": 80.0, "min_crew_canhao": 1, "reparo_mult": 1.0,
    },
    "normal": {
        "navio": "Bergantim", "crew_total": 3, "canhoes_lado": 2, "num_velas": 3,
        "velocidade_max_base": 11.0, "giro_graus_seg": 9.0,
        "cooldown_mult": 1.0, "erro_mira": 40.0, "min_crew_canhao": 1, "reparo_mult": 1.0,
    },
    "dificil": {
        "navio": "Galeao", "crew_total": 7, "canhoes_lado": 3, "num_velas": 7,
        "velocidade_max_base": 13.0, "giro_graus_seg": 6.0,
        "cooldown_mult": 0.7, "erro_mira": 15.0, "min_crew_canhao": 2, "reparo_mult": 1.0,
    },
}

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


def clamp(v, lo, hi):
    return max(lo, min(hi, v))


def direcao_para_heading(h):
    idx = int(((h % 360) + 22.5) // 45) % 8
    return DIRECOES[idx]


def seta_unicode_para_heading(h):
    idx = int(((h % 360) + 22.5) // 45) % 8
    return ARROWS_UNICODE[idx]


def seta_ascii_para_heading(h):
    idx = int(((h % 360) + 22.5) // 45) % 8
    return ARROWS_ASCII[idx]


def barra(valor, largura=6):
    cheio = int(clamp(valor, 0, 100) / 100 * largura)
    return '#' * cheio + '-' * (largura - cheio)


def nivel_cor(valor, pior_se_alto=False):
    """Retorna 'verde'/'amarelo'/'vermelho' - funcao pura, sem depender de curses,
    pra poder ser testada sem uma sessao curses ativa."""
    v = (100 - valor) if pior_se_alto else valor
    if v > 60:
        return 'verde'
    if v > 25:
        return 'amarelo'
    return 'vermelho'


def cor_valor(estado, valor, pior_se_alto=False):
    if not estado.cores_ativo:
        return 0
    mapa = {'verde': COR_VERDE, 'amarelo': COR_AMARELO, 'vermelho': COR_VERMELHO}
    return curses.color_pair(mapa[nivel_cor(valor, pior_se_alto)])


def cor_log(estado, linha):
    if not estado.cores_ativo:
        return 0
    if linha.startswith("[ACERTO]"):
        if "acerta Seu Navio" in linha:
            return curses.color_pair(COR_VERMELHO)
        return curses.color_pair(COR_VERDE)
    if linha.startswith("[DANO]") or linha.startswith("[AVARIA]"):
        return curses.color_pair(COR_VERMELHO)
    if linha.startswith("Tripulacao realocada"):
        return curses.color_pair(COR_AMARELO)
    return 0


def cor_mar(estado):
    if not estado.cores_ativo:
        return 0
    return curses.color_pair(COR_MAR)


def cor_navio(estado, e_jogador):
    if not estado.cores_ativo:
        return 0
    return curses.color_pair(COR_JOGADOR if e_jogador else COR_INIMIGO)


def cor_norte(estado):
    if not estado.cores_ativo:
        return 0
    return curses.color_pair(COR_VERMELHO)


def cor_tripulacao_livre(estado):
    if not estado.cores_ativo:
        return curses.A_BOLD
    if estado.crew_livre() <= 0:
        return curses.color_pair(COR_VERMELHO) | curses.A_BOLD
    return curses.A_BOLD


def cor_header(estado):
    """Titulo/HUD principal fica vermelho quando a agua do jogador esta critica."""
    if not estado.cores_ativo:
        return curses.A_BOLD
    if estado.jogador.agua > AGUA_CRITICA_LIMIAR:
        return curses.color_pair(COR_VERMELHO) | curses.A_BOLD
    return curses.A_BOLD


def cor_cooldown(estado, pronto):
    if not estado.cores_ativo:
        return 0
    return curses.color_pair(COR_VERDE) if pronto else curses.color_pair(COR_VERMELHO)


def cor_tarefa(estado, tarefa):
    if not estado.cores_ativo:
        return 0
    mapa = {"canhao": COR_INIMIGO, "reparo": COR_VERDE, "bomba": COR_JOGADOR}
    if tarefa in mapa:
        return curses.color_pair(mapa[tarefa])
    return 0


# ----------------------------------------------------------------------
# CANHAO
# ----------------------------------------------------------------------

class Canhao:
    def __init__(self, lado, indice):
        self.lado = lado
        self.indice = indice
        self.hp = 100.0
        self.tripulantes = 0
        self.dist_alvo = None
        self.mira_atual = 300.0
        self.proximo_tiro = 0.0

    @property
    def label(self):
        return f"{'E' if self.lado == 'estibordo' else 'B'}{self.indice}"

    def operacional(self):
        return self.hp > 0

    def armado(self):
        return self.operacional() and self.tripulantes >= 1 and self.dist_alvo is not None


def resolver_canhao(id_str, jogador):
    id_str = id_str.strip().lower()
    if len(id_str) < 2 or id_str[0] not in ('e', 'b'):
        return None
    lado = 'estibordo' if id_str[0] == 'e' else 'bombordo'
    try:
        idx = int(id_str[1:])
    except ValueError:
        return None
    lista = jogador.canhoes.get(lado)
    if lista is None or not (1 <= idx <= len(lista)):
        return None
    return lista[idx - 1]


# ----------------------------------------------------------------------
# NAVIO
# ----------------------------------------------------------------------

class Navio:
    def __init__(self, nome, x, y, heading, velocidade_max_base=11.0,
                 giro_graus_seg=GIRO_GRAUS_SEG_PADRAO, reparo_mult=1.0):
        self.nome = nome
        self.x = x
        self.y = y
        self.heading = heading % 360
        self.heading_alvo = heading % 360
        self.velocidade = 0.0
        self.nivel_vela = 1
        self.partes = {p: 100.0 for p in PARTES}
        self.agua = 0.0
        self.afundado = False
        self.canhoes_por_lado = 3
        self.alcance_canhao = 550.0
        self.velocidade_max_base = velocidade_max_base
        self.giro_graus_seg = giro_graus_seg
        self.reparo_mult = reparo_mult
        self.tipo_nome = ""
        self.num_velas = 1

    def vivo(self):
        return not self.afundado

    def taxa_giro(self):
        return self.giro_graus_seg * max(0.0, self.partes['roda'] / 100)

    def velocidade_maxima(self):
        fator_vela = self.nivel_vela / 3
        fator_dano = (self.partes['vela'] / 100) * (self.partes['mastro'] / 100)
        return self.velocidade_max_base * fator_vela * fator_dano

    def atualizar_movimento(self, dt):
        if self.afundado:
            return
        diff = (self.heading_alvo - self.heading + 540) % 360 - 180
        giro_max = self.taxa_giro() * dt
        if abs(diff) <= giro_max:
            self.heading = self.heading_alvo
        else:
            self.heading = (self.heading + (giro_max if diff > 0 else -giro_max)) % 360

        vmax = self.velocidade_maxima()
        acel = ACEL_VEL_SEG * dt
        if self.velocidade < vmax:
            self.velocidade = min(vmax, self.velocidade + acel)
        else:
            self.velocidade = max(vmax, self.velocidade - acel)

        rad = math.radians(self.heading)
        self.x += math.sin(rad) * self.velocidade * dt
        self.y += math.cos(rad) * self.velocidade * dt
        self.x = clamp(self.x, -MAPA_TAMANHO, MAPA_TAMANHO)
        self.y = clamp(self.y, -MAPA_TAMANHO, MAPA_TAMANHO)

    def reparar(self, parte, tripulantes, dt):
        if tripulantes <= 0:
            return
        eficiencia = clamp(self.partes['casco'] / 100, 0.3, 1.0)
        dano_frac = (100 - self.partes[parte]) / 100
        fator_recuperacao = math.exp(-REPARO_K * dano_frac)
        taxa = tripulantes * TAXA_REPARO_SEG * eficiencia * fator_recuperacao * self.reparo_mult * dt
        self.partes[parte] = clamp(self.partes[parte] + taxa, 0, 100)

    def atualizar_agua(self, tripulantes_bomba, dt):
        entrada = 0.0
        for p in PARTES_CRITICAS:
            dano_frac = (100 - self.partes[p]) / 100
            entrada += AGUA_BASE * (math.exp(AGUA_K * dano_frac) - 1)
        saida = tripulantes_bomba * SAIDA_BOMBA_SEG
        self.agua = clamp(self.agua + (entrada - saida) * dt, 0, 100)
        if self.agua >= 100:
            self.afundado = True

    def parte_critica_destruida(self):
        return any(self.partes[p] <= 0 for p in PARTES_CRITICAS)


# ----------------------------------------------------------------------
# GEOMETRIA / COMBATE
# ----------------------------------------------------------------------

def distancia(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def rumo_para(a, b):
    dx = b.x - a.x
    dy = b.y - a.y
    return math.degrees(math.atan2(dx, dy)) % 360


def dentro_do_arco(atirador, alvo, lado):
    d = distancia(atirador, alvo)
    if d > atirador.alcance_canhao:
        return False, d
    r = rumo_para(atirador, alvo)
    rel = (r - atirador.heading) % 360
    if lado == 'estibordo':
        ok = 20 <= rel <= 160
    else:
        ok = 200 <= rel <= 340
    return ok, d


def escolher_parte_atingida():
    pesos = {'casco': 45, 'mastro': 20, 'vela': 20, 'roda': 15}
    partes = list(pesos.keys())
    return random.choices(partes, weights=[pesos[p] for p in partes], k=1)[0]


def talvez_danificar_canhao(alvo, dano_casco, log):
    if not hasattr(alvo, 'canhoes'):
        return
    if random.uniform(0, 100) > CHANCE_DANO_CANHAO:
        return
    candidatos = [c for lado in alvo.canhoes.values() for c in lado if c.operacional()]
    if not candidatos:
        return
    c = random.choice(candidatos)
    c.hp = clamp(c.hp - dano_casco * 0.6, 0, 100)
    if c.hp <= 0:
        log.append(f"[DANO] Canhao {c.label} de {alvo.nome} foi destruido!")
        if c.tripulantes > 0:
            log.append(f"       {c.tripulantes} tripulante(s) liberado(s).")
        c.tripulantes = 0
        c.dist_alvo = None
    else:
        log.append(f"[AVARIA] Canhao {c.label} de {alvo.nome} avariado ({c.hp:.0f}%)")


def disparar_canhao_unico(atirador, alvo, canhao, log):
    """Disparo de UM canhao (usado pelo jogador). Retorna 'acerto'/'erro'/False."""
    ok, d = dentro_do_arco(atirador, alvo, canhao.lado)
    if not ok:
        return False

    erro_estimativa = abs(canhao.dist_alvo - d)
    instabilidade = (100 - atirador.partes['casco']) / 100 * 35
    chance_acerto = clamp(88 - erro_estimativa * 0.18 - instabilidade - d * 0.03, 4, 92)

    if random.uniform(0, 100) < chance_acerto:
        parte = escolher_parte_atingida()
        dano = random.uniform(9, 19)
        alvo.partes[parte] = clamp(alvo.partes[parte] - dano, 0, 100)
        log.append(f"[ACERTO] Canhao {canhao.label} acerta {alvo.nome} no(a) {parte} (-{dano:.0f}%)")
        if parte == 'casco':
            talvez_danificar_canhao(alvo, dano, log)
        return "acerto"
    else:
        log.append(f"[ERRO] Canhao {canhao.label} erra o alvo")
        return "erro"


# ----------------------------------------------------------------------
# ZOOM DO MAPA (niveis fixos, com histerese)
# ----------------------------------------------------------------------

def escolher_zoom(d, zoom_atual):
    alvo = d * 0.75
    if zoom_atual is None:
        for n in ZOOM_NIVEIS:
            if n >= alvo:
                return n
        return ZOOM_NIVEIS[-1]

    idx_atual = ZOOM_NIVEIS.index(zoom_atual)
    if alvo > zoom_atual and idx_atual < len(ZOOM_NIVEIS) - 1:
        return ZOOM_NIVEIS[idx_atual + 1]
    if idx_atual > 0:
        nivel_abaixo = ZOOM_NIVEIS[idx_atual - 1]
        if alvo < nivel_abaixo * ZOOM_HISTERESE:
            return nivel_abaixo
    return zoom_atual


# ----------------------------------------------------------------------
# ESTADO DO JOGO
# ----------------------------------------------------------------------

class Estado:
    def __init__(self, tipo_navio="normal", hotkeys=False, cores=False, graficos_unicode=False):
        self.tipo_navio = tipo_navio if tipo_navio in NAVIO_TIPOS else "normal"
        params = NAVIO_TIPOS[self.tipo_navio]

        self.crew_total = params["crew_total"]
        self.canhoes_lado = params["canhoes_lado"]
        self.num_velas = params["num_velas"]
        self.min_crew_canhao = params["min_crew_canhao"]
        self.tripulante_ids = [f"T{i+1}" for i in range(self.crew_total)]
        self.canhao_ids = [f"{l}{i}" for l in ("E", "B") for i in range(1, self.canhoes_lado + 1)]

        self.jogador = Navio("Seu Navio", x=0, y=0, heading=0,
                              velocidade_max_base=params["velocidade_max_base"],
                              giro_graus_seg=params["giro_graus_seg"],
                              reparo_mult=params["reparo_mult"])
        self.jogador.tipo_nome = params["navio"]
        self.jogador.num_velas = self.num_velas
        self.jogador.canhoes = {
            'bombordo': [Canhao('bombordo', i + 1) for i in range(self.canhoes_lado)],
            'estibordo': [Canhao('estibordo', i + 1) for i in range(self.canhoes_lado)],
        }

        # o inimigo usa exatamente o mesmo navio (mesma tripulacao, canhoes,
        # minimo por canhao, reparo_mult) que o jogador escolheu - simetria total
        self.inimigo = Navio("Navio Inimigo", x=400, y=650, heading=180,
                              velocidade_max_base=params["velocidade_max_base"],
                              giro_graus_seg=params["giro_graus_seg"],
                              reparo_mult=params["reparo_mult"])
        self.inimigo.tipo_nome = params["navio"]
        self.inimigo.num_velas = self.num_velas
        self.inimigo.canhoes = {
            'bombordo': [Canhao('bombordo', i + 1) for i in range(self.canhoes_lado)],
            'estibordo': [Canhao('estibordo', i + 1) for i in range(self.canhoes_lado)],
        }
        self.inimigo_crew_reparo = {p: 0 for p in PARTES}
        self.inimigo_crew_bomba = 0

        # "personalidade" da IA: limiares sorteados por partida, nao fixos
        self.ia_limiar_agua = random.uniform(20.0, 40.0)     # media 30%
        self.ia_limiar_casco = random.uniform(40.0, 60.0)    # media 50%

        self.crew_reparo = {p: 0 for p in PARTES}
        self.crew_bomba = 0
        self.tempo = 0.0
        self.rodando = True
        self.fim = None
        self.stats = {"tiros_jogador": 0, "acertos_jogador": 0,
                       "tiros_inimigo": 0, "acertos_inimigo": 0}
        self.log = deque(maxlen=8)
        self.ultimo_comando = None
        self.hotkeys_ativo = hotkeys
        self.cores_ativo = cores
        self.graficos_unicode = graficos_unicode
        self.foco = None
        self.zoom_atual = None
        self.zoom_mudou_em = -999.0
        self.log.append(f"Bem-vindo ao conves do {params['navio']}, capitao. "
                         f"Digite 'ajuda' (TAB circula opcoes).")

    def crew_canhoes_usada(self):
        total = 0
        for lado in self.jogador.canhoes.values():
            for c in lado:
                total += c.tripulantes
        return total

    def crew_continua_usada(self):
        return sum(self.crew_reparo.values()) + self.crew_bomba + self.crew_canhoes_usada()

    def crew_livre(self):
        return self.crew_total - self.crew_continua_usada()


def montar_tripulacao(estado):
    ids = estado.tripulante_ids
    roster = []
    i = 0
    for lado in ('estibordo', 'bombordo'):
        for c in estado.jogador.canhoes[lado]:
            for _ in range(c.tripulantes):
                if i >= len(ids):
                    break
                detalhe = f"canhao {c.label}"
                if c.dist_alvo is not None:
                    detalhe += f" (mira {c.dist_alvo:.0f}m)"
                roster.append((ids[i], "canhao", detalhe))
                i += 1
    for parte in PARTES:
        for _ in range(estado.crew_reparo.get(parte, 0)):
            if i >= len(ids):
                break
            roster.append((ids[i], "reparo", parte))
            i += 1
    for _ in range(estado.crew_bomba):
        if i >= len(ids):
            break
        roster.append((ids[i], "bomba", "porao"))
        i += 1
    while i < len(ids):
        roster.append((ids[i], "ocioso", "conves"))
        i += 1
    return roster


# ----------------------------------------------------------------------
# REALOCACAO AUTOMATICA DE TRIPULACAO
# ----------------------------------------------------------------------

def _liberar_tripulantes(estado, necessario, ignorar_canhao=None, ignorar_parte=None):
    """Tenta liberar 'necessario' tripulantes puxando primeiro de canhoes
    (libera o canhao inteiro - sem prioridade) e so depois de reparo (parcial,
    alta prioridade). NUNCA mexe na tripulacao da bomba (prioridade maxima).
    Retorna quantos conseguiu liberar de fato (pode ser menor que o pedido)
    e registra no log o que foi movido."""
    liberado = 0
    movimentos = []

    for lado in ('bombordo', 'estibordo'):
        for c in estado.jogador.canhoes[lado]:
            if liberado >= necessario:
                break
            if c is ignorar_canhao or c.tripulantes <= 0:
                continue
            qtd = c.tripulantes
            movimentos.append(f"{qtd} de Canhao {c.label}")
            c.tripulantes = 0
            c.dist_alvo = None
            liberado += qtd
        if liberado >= necessario:
            break

    if liberado < necessario:
        for parte in PARTES:
            if liberado >= necessario:
                break
            if parte == ignorar_parte:
                continue
            n_atual = estado.crew_reparo.get(parte, 0)
            if n_atual <= 0:
                continue
            falta = necessario - liberado
            tirar = min(n_atual, falta)
            estado.crew_reparo[parte] -= tirar
            liberado += tirar
            movimentos.append(f"{tirar} de Reparo {parte}")

    if movimentos:
        estado.log.append(f"Tripulacao realocada: {', '.join(movimentos)}")
    return liberado


def tentar_assumir_tripulacao(estado, quantidade_desejada, atual_no_alvo,
                               ignorar_canhao=None, ignorar_parte=None):
    """Retorna (quantidade_final, cortou) - quantidade_final pode ser menor
    que quantidade_desejada se nem puxando de outras tarefas der pra completar
    (a bomba nunca e sacrificada, entao pode nao sobrar gente suficiente)."""
    livre = estado.crew_livre() + atual_no_alvo
    if quantidade_desejada <= livre:
        return quantidade_desejada, False
    faltam = quantidade_desejada - livre
    liberado = _liberar_tripulantes(estado, faltam, ignorar_canhao=ignorar_canhao,
                                     ignorar_parte=ignorar_parte)
    livre_final = livre + liberado
    final = min(quantidade_desejada, livre_final)
    return final, final < quantidade_desejada


# ----------------------------------------------------------------------
# IA DO INIMIGO
# ----------------------------------------------------------------------

def atualizar_ia_movimento(estado, dt):
    inimigo = estado.inimigo
    jogador = estado.jogador
    if inimigo.afundado:
        return
    d = distancia(inimigo, jogador)
    r = rumo_para(inimigo, jogador)

    if d > 380:
        inimigo.heading_alvo = r
        inimigo.nivel_vela = 3
    elif d < 250:
        inimigo.heading_alvo = (r + 180) % 360
        inimigo.nivel_vela = 2
    else:
        inimigo.heading_alvo = (r + 90) % 360
        inimigo.nivel_vela = 2


def atualizar_ia_tripulacao(estado):
    """Aloca a tripulacao finita do inimigo por prioridade: bomba (se a agua
    passar do limiar 'nervoso' dessa partida), depois reparo do casco (se
    estiver abaixo do limiar), e o resto nos canhoes. Recalculado a cada tick,
    entao reage a mudancas de estado (chegou mais dano, etc)."""
    inimigo = estado.inimigo
    total = estado.crew_total
    min_c = estado.min_crew_canhao

    bomba_alvo = 0
    if inimigo.agua > estado.ia_limiar_agua:
        faixa = max(1.0, 100 - estado.ia_limiar_agua)
        gravidade = clamp((inimigo.agua - estado.ia_limiar_agua) / faixa, 0, 1)
        bomba_alvo = min(total, max(1, round(total * (0.35 + 0.35 * gravidade))))
    restante = total - bomba_alvo

    reparo_alvo = 0
    if inimigo.partes['casco'] < estado.ia_limiar_casco and restante > 0:
        reparo_alvo = min(restante, max(1, round(total * 0.3)))
    restante -= reparo_alvo

    estado.inimigo_crew_bomba = bomba_alvo
    for p in PARTES:
        estado.inimigo_crew_reparo[p] = reparo_alvo if p == 'casco' else 0

    # o que sobra vai pros canhoes. Prioridade: 1) o lado que esta de fato
    # com o alvo no arco AGORA (senao o navio fica "mudo" tripulando o lado
    # errado); 2) canhoes que ja estavam armados, como desempate pra nao
    # ficar trocando de ideia toda hora; 3) o resto.
    jogador = estado.jogador
    lados_no_arco = [lado for lado in ('estibordo', 'bombordo')
                      if dentro_do_arco(inimigo, jogador, lado)[0]]

    def prioridade(c):
        if c.lado in lados_no_arco:
            return 0
        if c.dist_alvo is not None:
            return 1
        return 2

    canhoes = [c for lado in ('estibordo', 'bombordo') for c in inimigo.canhoes[lado]
               if c.operacional()]
    canhoes.sort(key=prioridade)

    for c in canhoes:
        if restante >= min_c:
            c.tripulantes = min_c
            restante -= min_c
        else:
            c.tripulantes = 0
            c.dist_alvo = None


def atualizar_ia_mira(estado):
    """Sempre que um canhao do inimigo esta tripulado e pronto pra atirar de
    novo (ou acabou de ganhar tripulacao), recalibra a mira com o mesmo tipo
    de erro de estimativa que um artilheiro humano teria."""
    inimigo = estado.inimigo
    jogador = estado.jogador
    erro = NAVIO_TIPOS[estado.tipo_navio]["erro_mira"]
    d_real = distancia(inimigo, jogador)

    for lado in ('bombordo', 'estibordo'):
        for c in inimigo.canhoes[lado]:
            if not c.operacional() or c.tripulantes < estado.min_crew_canhao:
                continue
            if c.dist_alvo is None or estado.tempo >= c.proximo_tiro:
                novo = d_real + random.uniform(-erro, erro)
                c.dist_alvo = novo
                c.mira_atual = novo


def _disparar_canhoes_navio(estado, atirador, alvo):
    """Dispara os canhoes armados de 'atirador' contra 'alvo', respeitando
    arco/alcance/cooldown de cada canhao individualmente. Usado tanto pro
    jogador quanto pelo inimigo - o mesmo sistema pros dois lados."""
    e_jogador = atirador is estado.jogador
    cooldown_mult = 1.0 if e_jogador else NAVIO_TIPOS[estado.tipo_navio]["cooldown_mult"]

    for lado in ('bombordo', 'estibordo'):
        for c in atirador.canhoes[lado]:
            if not c.armado():
                continue
            if estado.tempo < c.proximo_tiro:
                continue
            ok, _ = dentro_do_arco(atirador, alvo, lado)
            if not ok:
                continue
            resultado = disparar_canhao_unico(atirador, alvo, c, estado.log)
            if resultado in ("acerto", "erro"):
                if e_jogador:
                    estado.stats["tiros_jogador"] += 1
                    if resultado == "acerto":
                        estado.stats["acertos_jogador"] += 1
                else:
                    estado.stats["tiros_inimigo"] += 1
                    if resultado == "acerto":
                        estado.stats["acertos_inimigo"] += 1
                c.proximo_tiro = estado.tempo + COOLDOWN_CANHAO * cooldown_mult \
                    + random.uniform(-0.5, 0.8)



# COMANDOS DO JOGADOR (texto)
# ----------------------------------------------------------------------

def processar_comando(texto, estado):
    partes_cmd = texto.strip().lower().split()
    if not partes_cmd:
        return
    cmd = partes_cmd[0]
    if cmd in ALIASES:
        cmd = ALIASES[cmd]
    jogador = estado.jogador
    inimigo = estado.inimigo

    if cmd == "ajuda":
        estado.log.append("l/v/r/b/c = leme/vela/reparar/bomba/canhao | ENTER vazio repete")
        estado.log.append("canhao <id> <n> <dist> | <id> <dist> (trip minimo) | <id> trip <n>")
        estado.log.append(f"canhoes deste navio: {', '.join(estado.canhao_ids)} | radar | ESC sai")

    elif cmd == "radar":
        d = distancia(jogador, inimigo)
        r = rumo_para(jogador, inimigo)
        rel = (r - jogador.heading) % 360
        if 20 <= rel <= 160:
            arco = "ESTIBORDO"
        elif 200 <= rel <= 340:
            arco = "BOMBORDO"
        else:
            arco = "fora de arco"
        alcance = "dentro do alcance" if d <= jogador.alcance_canhao else "fora de alcance"
        estado.log.append(f"RADAR: {d:.0f}m, rumo {r:.0f} graus, {arco}, {alcance}")

    elif cmd == "leme" and len(partes_cmd) == 2:
        try:
            jogador.heading_alvo = float(partes_cmd[1]) % 360
            estado.log.append(f"Leme para {jogador.heading_alvo:.0f} graus")
        except ValueError:
            estado.log.append("Uso: leme <graus>")

    elif cmd == "vela" and len(partes_cmd) == 2:
        try:
            n = int(partes_cmd[1])
            if 0 <= n <= 3:
                jogador.nivel_vela = n
                estado.log.append(f"Velas no nivel {n}")
            else:
                estado.log.append("Nivel de vela deve ser 0-3")
        except ValueError:
            estado.log.append("Uso: vela <0-3>")

    elif cmd == "reparar" and len(partes_cmd) == 3:
        parte = partes_cmd[1]
        if parte not in PARTES:
            estado.log.append(f"Parte invalida. Opcoes: {', '.join(PARTES)}")
            return
        try:
            n = int(partes_cmd[2])
        except ValueError:
            estado.log.append("Uso: reparar <parte> <tripulantes>")
            return
        if n < 0:
            estado.log.append("Numero de tripulantes nao pode ser negativo")
            return
        atual = estado.crew_reparo[parte]
        final, cortou = tentar_assumir_tripulacao(estado, n, atual, ignorar_parte=parte)
        estado.crew_reparo[parte] = final
        if cortou:
            estado.log.append(f"So consegui {final} de {n} tripulante(s) pedidos para {parte} "
                               f"(bomba nao foi mexida)")
        else:
            estado.log.append(f"{final} tripulante(s) reparando {parte} continuamente")

    elif cmd == "bomba" and len(partes_cmd) == 2:
        try:
            n = int(partes_cmd[1])
        except ValueError:
            estado.log.append("Uso: bomba <tripulantes>")
            return
        if n < 0:
            estado.log.append("Numero de tripulantes nao pode ser negativo")
            return
        atual = estado.crew_bomba
        final, cortou = tentar_assumir_tripulacao(estado, n, atual)
        estado.crew_bomba = final
        if cortou:
            estado.log.append(f"So consegui {final} de {n} tripulante(s) pedidos para a bomba")
        else:
            estado.log.append(f"{final} tripulante(s) nas bombas")

    elif cmd == "canhao" and len(partes_cmd) >= 2:
        canhao = resolver_canhao(partes_cmd[1], jogador)
        if canhao is None:
            estado.log.append(f"Canhao invalido. Use: {', '.join(estado.canhao_ids)}")
            return
        if not canhao.operacional():
            estado.log.append(f"Canhao {canhao.label} esta destruido")
            return

        resto = partes_cmd[2:]

        if len(resto) == 1 and resto[0] == "parar":
            canhao.dist_alvo = None
            canhao.tripulantes = 0
            estado.log.append(f"Canhao {canhao.label} parou de atirar e liberou a tripulacao")

        elif len(resto) == 1:
            try:
                dist = float(resto[0])
            except ValueError:
                estado.log.append("Uso: canhao <id> <distancia> | <id> <n> <distancia> | "
                                   "<id> trip <n> | <id> mirar <d> | <id> parar")
                return
            if canhao.tripulantes >= estado.min_crew_canhao:
                canhao.dist_alvo = dist
                canhao.mira_atual = dist
                estado.log.append(f"Canhao {canhao.label} mirando {dist:.0f}m - atirara sozinho")
            else:
                _armar_canhao_com_padrao(estado, canhao, dist)

        elif len(resto) == 2 and resto[0] == "trip":
            try:
                n = int(resto[1])
            except ValueError:
                estado.log.append("Uso: canhao <id> trip <n>")
                return
            if n != 0 and n < estado.min_crew_canhao:
                estado.log.append(f"Um canhao precisa de pelo menos {estado.min_crew_canhao} "
                                   f"tripulante(s) (ou 0 para liberar)")
                return
            _definir_trip_canhao(estado, canhao, n)

        elif len(resto) == 2 and resto[0] == "mirar":
            if canhao.tripulantes < estado.min_crew_canhao:
                estado.log.append(f"Aloque tripulantes no canhao {canhao.label} antes de mirar")
                return
            try:
                dist = float(resto[1])
            except ValueError:
                estado.log.append("Uso: canhao <id> mirar <distancia>")
                return
            canhao.dist_alvo = dist
            canhao.mira_atual = dist
            estado.log.append(f"Canhao {canhao.label} mirando {dist:.0f}m - atirara sozinho")

        elif len(resto) == 2:
            try:
                n = int(resto[0])
                dist = float(resto[1])
            except ValueError:
                estado.log.append("Uso: canhao <id> <tripulantes> <distancia> | trip <n> | mirar <d> | parar")
                return
            if n != 0 and n < estado.min_crew_canhao:
                estado.log.append(f"Um canhao precisa de pelo menos {estado.min_crew_canhao} tripulante(s)")
                return
            _definir_trip_canhao(estado, canhao, n, dist_se_armar=dist)

        else:
            estado.log.append("Uso: canhao <id> <tripulantes> <distancia> | <id> <distancia> | "
                               "trip <n> | mirar <d> | parar")

    else:
        estado.log.append("Comando nao reconhecido. Digite 'ajuda'.")


def _definir_trip_canhao(estado, canhao, n, dist_se_armar=None):
    """Define a tripulacao de um canhao (0 libera), puxando de outras tarefas
    se faltar gente livre. Se nao der pra atingir o minimo do navio, zera."""
    if n == 0:
        canhao.tripulantes = 0
        canhao.dist_alvo = None
        estado.log.append(f"Canhao {canhao.label} liberado")
        return

    atual = canhao.tripulantes
    final, cortou = tentar_assumir_tripulacao(estado, n, atual, ignorar_canhao=canhao)
    if final < estado.min_crew_canhao:
        canhao.tripulantes = 0
        canhao.dist_alvo = None
        estado.log.append(f"Nao ha tripulacao suficiente (nem realocando) para o canhao "
                           f"{canhao.label} - continua sem tripulacao")
        return

    canhao.tripulantes = final
    if dist_se_armar is not None:
        canhao.dist_alvo = dist_se_armar
        canhao.mira_atual = dist_se_armar
    if cortou:
        estado.log.append(f"So consegui {final} de {n} tripulante(s) pedidos para o canhao "
                           f"{canhao.label}")
    else:
        msg = f"{final} tripulante(s) no canhao {canhao.label}"
        msg += f", mirando {dist_se_armar:.0f}m" if dist_se_armar is not None else ". Use 'mirar' para armar."
        estado.log.append(msg)


def _armar_canhao_com_padrao(estado, canhao, dist):
    _definir_trip_canhao(estado, canhao, estado.min_crew_canhao, dist_se_armar=dist)


def obter_candidatos(tokens_completos, partial, estado):
    pl = partial.lower()
    if len(tokens_completos) == 0:
        return [c for c in COMANDOS if c.startswith(pl)]
    cmd = tokens_completos[0]
    if cmd in ALIASES:
        cmd = ALIASES[cmd]
    pos = len(tokens_completos)
    if cmd == "canhao":
        if pos == 1:
            return [c for c in estado.canhao_ids if c.lower().startswith(pl)]
        if pos == 2:
            return [c for c in CANHAO_SUBCMDS if c.startswith(pl)]
    elif cmd == "reparar" and pos == 1:
        return [c for c in PARTES if c.startswith(pl)]
    elif cmd == "vela" and pos == 1:
        return [c for c in ("0", "1", "2", "3") if c.startswith(pl)]
    return []


# ----------------------------------------------------------------------
# HOTKEYS (teclas soltas, so ativas com o prompt vazio)
# ----------------------------------------------------------------------

def _ciclar_canhao(estado, lado):
    lista = estado.jogador.canhoes[lado]
    if estado.foco and estado.foco[0] == "canhao" and estado.foco[1] == lado:
        novo_idx = (estado.foco[2] + 1) % len(lista)
    else:
        novo_idx = 0
    estado.foco = ("canhao", lado, novo_idx)
    c = lista[novo_idx]
    mira_txt = f"{c.dist_alvo:.0f}m" if c.dist_alvo is not None else f"(pendente {c.mira_atual:.0f}m)"
    estado.log.append(f"Selecionado canhao {c.label} - trip:{c.tripulantes} mira:{mira_txt}")


def _ajustar_mira(estado, delta):
    if not (estado.foco and estado.foco[0] == "canhao"):
        estado.log.append("Selecione um canhao primeiro (tecla j ou l)")
        return
    _, lado, idx = estado.foco
    c = estado.jogador.canhoes[lado][idx]
    if not c.operacional():
        estado.log.append(f"Canhao {c.label} esta destruido")
        return
    novo = clamp(c.mira_atual + delta, 50, 900)
    c.mira_atual = novo
    if c.dist_alvo is not None:
        c.dist_alvo = novo
    estado.log.append(f"Canhao {c.label} mira: {novo:.0f}m")


def _ajustar_bomba(estado, delta):
    if delta > 0:
        atual = estado.crew_bomba
        final, cortou = tentar_assumir_tripulacao(estado, atual + 1, atual)
        estado.crew_bomba = final
        if final <= atual:
            estado.log.append("Nao ha tripulacao disponivel para a bomba")
            return
    else:
        estado.crew_bomba = max(0, estado.crew_bomba - 1)
    estado.log.append(f"Bomba: {estado.crew_bomba} tripulante(s)")


def _ajustar_reparo(estado, delta):
    if not (estado.foco and estado.foco[0] == "reparo"):
        estado.log.append("Selecione uma parte primeiro (tecla e)")
        return
    parte = PARTES[estado.foco[1]]
    atual = estado.crew_reparo.get(parte, 0)
    if delta > 0:
        final, cortou = tentar_assumir_tripulacao(estado, atual + 1, atual, ignorar_parte=parte)
        estado.crew_reparo[parte] = final
        if final <= atual:
            estado.log.append(f"Nao ha tripulacao disponivel para reparo de {parte}")
            return
    else:
        estado.crew_reparo[parte] = max(0, atual - 1)
    estado.log.append(f"Reparo {parte}: {estado.crew_reparo[parte]} tripulante(s)")


def _ciclar_reparo(estado):
    if estado.foco and estado.foco[0] == "reparo":
        novo_idx = (estado.foco[1] + 1) % len(PARTES)
    else:
        novo_idx = 0
    estado.foco = ("reparo", novo_idx)
    parte = PARTES[novo_idx]
    n_atual = estado.crew_reparo.get(parte, 0)
    estado.log.append(f"Selecionado reparo: {parte} - tripulantes atuais: {n_atual}")


def _alternar_foco(estado):
    """SPACE: pro canhao, alterna atirar/parar. Pro reparo, adiciona 1
    tripulante (o R separado remove 1) - o mesmo espirito da bomba."""
    if not estado.foco:
        estado.log.append("Nada selecionado (use j/l p/ canhao, e p/ reparo)")
        return
    tipo = estado.foco[0]

    if tipo == "canhao":
        _, lado, idx = estado.foco
        c = estado.jogador.canhoes[lado][idx]
        if not c.operacional():
            estado.log.append(f"Canhao {c.label} esta destruido")
            return
        if c.dist_alvo is not None:
            c.dist_alvo = None
            c.tripulantes = 0
            estado.log.append(f"Canhao {c.label} parou de atirar e liberou a tripulacao")
        else:
            _armar_canhao_com_padrao(estado, c, c.mira_atual)

    elif tipo == "reparo":
        _ajustar_reparo(estado, +1)


def _descrever_foco(estado):
    if not estado.foco:
        return "nenhum"
    if estado.foco[0] == "canhao":
        _, lado, idx = estado.foco
        c = estado.jogador.canhoes[lado][idx]
        if not c.operacional():
            return f"{c.label} [DESTRUIDO]"
        mira = f"{c.dist_alvo:.0f}m" if c.dist_alvo is not None else f"(pendente {c.mira_atual:.0f}m)"
        status = "ATIRANDO" if c.dist_alvo is not None else "parado"
        return f"canhao {c.label} trip:{c.tripulantes} mira:{mira} [{status}]"
    if estado.foco[0] == "reparo":
        parte = PARTES[estado.foco[1]]
        n = estado.crew_reparo.get(parte, 0)
        status = "REPARANDO" if n > 0 else "parado"
        return f"reparo {parte} trip:{n} [{status}]"
    return "?"


def processar_hotkey(ch, estado):
    """Retorna True se ch era uma hotkey reconhecida (e ja foi tratada).
    As letras funcionam com ou sem SHIFT (maiuscula ou minuscula)."""
    jogador = estado.jogador

    if ch == ord(' '):
        _alternar_foco(estado)
        return True

    if not (32 <= ch <= 126):
        return False
    caractere = chr(ch)
    if not caractere.isalpha():
        return False
    letra = caractere.upper()

    if letra == 'A':
        jogador.heading_alvo = (jogador.heading_alvo - HOTKEY_PASSO_LEME) % 360
        estado.log.append(f"Leme -{HOTKEY_PASSO_LEME:.0f} (direita/estibordo) -> "
                           f"{jogador.heading_alvo:.0f} graus")
        return True
    if letra == 'D':
        jogador.heading_alvo = (jogador.heading_alvo + HOTKEY_PASSO_LEME) % 360
        estado.log.append(f"Leme +{HOTKEY_PASSO_LEME:.0f} (esquerda/bombordo) -> "
                           f"{jogador.heading_alvo:.0f} graus")
        return True
    if letra == 'W':
        jogador.nivel_vela = min(3, jogador.nivel_vela + 1)
        estado.log.append(f"Vela ++ -> nivel {jogador.nivel_vela}")
        return True
    if letra == 'S':
        jogador.nivel_vela = max(0, jogador.nivel_vela - 1)
        estado.log.append(f"Vela -- -> nivel {jogador.nivel_vela}")
        return True
    if letra == 'J':
        _ciclar_canhao(estado, 'bombordo')
        return True
    if letra == 'L':
        _ciclar_canhao(estado, 'estibordo')
        return True
    if letra == 'I':
        _ajustar_mira(estado, HOTKEY_PASSO_MIRA)
        return True
    if letra == 'K':
        _ajustar_mira(estado, -HOTKEY_PASSO_MIRA)
        return True
    if letra == 'U':
        _ajustar_bomba(estado, +1)
        return True
    if letra == 'H':
        _ajustar_bomba(estado, -1)
        return True
    if letra == 'E':
        _ciclar_reparo(estado)
        return True
    if letra == 'R':
        _ajustar_reparo(estado, -1)
        return True
    return False


# ----------------------------------------------------------------------
# SIMULACAO
# ----------------------------------------------------------------------

def _atualizar_zoom(estado):
    d = distancia(estado.jogador, estado.inimigo)
    novo = escolher_zoom(d, estado.zoom_atual)
    if estado.zoom_atual is not None and novo != estado.zoom_atual:
        estado.log.append(f"Mapa: zoom ajustado para ~{novo}m")
        estado.zoom_mudou_em = estado.tempo
    estado.zoom_atual = novo


def atualizar_simulacao(estado, dt):
    jogador = estado.jogador
    inimigo = estado.inimigo

    for parte, n in estado.crew_reparo.items():
        jogador.reparar(parte, n, dt)
    jogador.atualizar_agua(estado.crew_bomba, dt)

    if not inimigo.afundado:
        atualizar_ia_movimento(estado, dt)
        atualizar_ia_tripulacao(estado)
        atualizar_ia_mira(estado)
        for parte, n in estado.inimigo_crew_reparo.items():
            inimigo.reparar(parte, n, dt)
        inimigo.atualizar_agua(estado.inimigo_crew_bomba, dt)

    if not inimigo.afundado:
        _disparar_canhoes_navio(estado, jogador, inimigo)
    if not jogador.afundado:
        _disparar_canhoes_navio(estado, inimigo, jogador)

    jogador.atualizar_movimento(dt)
    inimigo.atualizar_movimento(dt)

    _atualizar_zoom(estado)

    estado.tempo += dt

    if jogador.afundado and estado.fim is None:
        estado.log.append("Seu navio afundou! Fim de jogo.")
        estado.fim = "derrota"
        estado.rodando = False

    elif inimigo.afundado and estado.fim is None:
        estado.log.append("O navio inimigo afundou! Vitoria!")
        estado.fim = "vitoria"
        estado.rodando = False


# ----------------------------------------------------------------------
# VISUALIZACOES (HUD do jogo) - cada uma retorna lista de (texto, atributo)
# ----------------------------------------------------------------------

def build_navio_diagrama(estado):
    j = estado.jogador
    linhas = [
        (f"CASCO [{barra(j.partes['casco'], 10)}] {j.partes['casco']:5.1f}%",
         cor_valor(estado, j.partes['casco'])),
        (f"MASTRO[{barra(j.partes['mastro'], 10)}] {j.partes['mastro']:5.1f}%",
         cor_valor(estado, j.partes['mastro'])),
        (f"VELA  [{barra(j.partes['vela'], 10)}] {j.partes['vela']:5.1f}%  "
         f"({j.num_velas} velas)", cor_valor(estado, j.partes['vela'])),
        (f"RODA  [{barra(j.partes['roda'], 10)}] {j.partes['roda']:5.1f}%",
         cor_valor(estado, j.partes['roda'])),
        (f"AGUA  [{barra(j.agua, 10)}] {j.agua:5.1f}%",
         cor_valor(estado, j.agua, pior_se_alto=True)),
        (f"Rumo {j.heading:5.1f}->{j.heading_alvo:5.1f} "
         f"Vel {j.velocidade:4.1f}/{j.velocidade_maxima():4.1f} Vela {j.nivel_vela}/3", 0),
    ]
    return linhas


def build_canhoes_linhas(estado):
    linhas = []
    for lado in ('estibordo', 'bombordo'):
        for c in estado.jogador.canhoes[lado]:
            if not c.operacional():
                linhas.append((f"{c.label} [DESTRUIDO]", cor_valor(estado, 0)))
                continue
            hp_txt = f"{c.label} hp[{barra(c.hp)}]{c.hp:3.0f}% trip:{c.tripulantes}"
            if c.dist_alvo is None:
                status = "sem mira" if c.tripulantes >= estado.min_crew_canhao else "sem trip."
                linhas.append((f"{hp_txt} {status}", cor_valor(estado, c.hp)))
            elif estado.tempo < c.proximo_tiro:
                restante = c.proximo_tiro - estado.tempo
                pct_cd = clamp(100 * (1 - restante / COOLDOWN_CANHAO), 0, 100)
                linhas.append((hp_txt, cor_valor(estado, c.hp)))
                linhas.append((f"   cd[{barra(pct_cd)}] {restante:4.1f}s mira:{c.dist_alvo:.0f}m",
                                cor_cooldown(estado, pronto=False)))
            else:
                linhas.append((hp_txt, cor_valor(estado, c.hp)))
                linhas.append((f"   cd[{barra(100)}] pronto  mira:{c.dist_alvo:.0f}m",
                                cor_cooldown(estado, pronto=True)))
    return linhas


def build_bussola_linhas(estado, largura=50):
    """Bussola 'na mao': proa fixa no centro, os pontos cardeais deslizam.
    O N ganha destaque em vermelho quando as cores estao ligadas."""
    jogador = estado.jogador
    linha = [' '] * largura
    marcos = {0: 'N', 45: 'NE', 90: 'E', 135: 'SE', 180: 'S', 225: 'SW', 270: 'W', 315: 'NW'}
    overlays = []
    for graus, label in marcos.items():
        rel = (graus - jogador.heading + 540) % 360 - 180
        pos = clamp(int(round((rel + 180) / 360 * (largura - 1))), 0, largura - 1)
        ini = clamp(pos - len(label) // 2, 0, largura - len(label))
        for i, c in enumerate(label):
            linha[ini + i] = c
        if label == 'N':
            overlays.append((ini, label, cor_norte(estado)))

    ponteiro = [' '] * largura
    ponteiro[largura // 2] = '|'

    diff = (jogador.heading_alvo - jogador.heading + 540) % 360 - 180
    if abs(diff) < 0.5:
        sentido = "(parado)"
    elif diff > 0:
        sentido = ">>> virando p/ bombordo"
    else:
        sentido = "<<< virando p/ estibordo"

    return [
        (''.join(linha), 0, overlays),
        (''.join(ponteiro), 0, []),
        (f"Rumo atual: {jogador.heading:.0f} graus {sentido}", 0, []),
    ]


def build_vista_linhas(estado):
    jogador, inimigo = estado.jogador, estado.inimigo
    largura = 50
    if inimigo.afundado:
        return [("Nenhum navio inimigo a vista.", 0, [])]

    d_real = distancia(jogador, inimigo)
    alcance_visual = 900
    attr_mar = cor_mar(estado)
    if d_real > alcance_visual:
        return [("~" * largura, attr_mar, []), ("O horizonte esta vazio.", 0, [])]

    rel = (rumo_para(jogador, inimigo) - jogador.heading + 540) % 360 - 180
    pos = clamp(int(round((rel + 180) / 360 * (largura - 1))), 0, largura - 1)

    if d_real < 150:
        icone = "#[SHIP]#"
    elif d_real < 400:
        icone = "[SHIP]"
    else:
        icone = "."
    linha = list('~' * largura)
    inicio = clamp(pos - len(icone) // 2, 0, largura - len(icone))
    for i, ch in enumerate(icone):
        linha[inicio + i] = ch
    horizonte = ''.join(linha)
    overlay_navio = [(inicio, icone, cor_navio(estado, e_jogador=False))]

    regua = [' '] * largura
    marcos = {-180: 'POPA', -90: 'BOMB', 0: 'PROA', 90: 'ESTIB', 180: 'POPA'}
    for graus, label in marcos.items():
        p = clamp(int(round((graus + 180) / 360 * (largura - 1))), 0, largura - 1)
        ini = clamp(p - len(label) // 2, 0, largura - len(label))
        for i, c in enumerate(label):
            regua[ini + i] = c
    ruler = ''.join(regua)

    erro_vigia = random.uniform(-0.1, 0.1) * d_real
    vigia = f'Vigia: "a {d_real + erro_vigia:.0f}m!"'

    return [(horizonte, attr_mar, overlay_navio), (ruler, 0, []), (vigia, 0, [])]


def build_mapa_linhas(estado):
    jogador, inimigo = estado.jogador, estado.inimigo
    unicode_on = estado.graficos_unicode
    GRID_W, GRID_H = 20, 8

    cx = (jogador.x + inimigo.x) / 2
    cy = (jogador.y + inimigo.y) / 2
    half_range = estado.zoom_atual or 400

    def to_cell(nx, ny):
        gx = (nx - cx) / (2 * half_range) * (GRID_W - 1) + (GRID_W - 1) / 2
        gy = (ny - cy) / (2 * half_range) * (GRID_H - 1) + (GRID_H - 1) / 2
        col = clamp(int(round(gx)), 0, GRID_W - 1)
        row = clamp(int(round((GRID_H - 1) - gy)), 0, GRID_H - 1)
        return col, row

    def celula(navio, e_jogador):
        glifo = seta_unicode_para_heading(navio.heading) if unicode_on \
            else seta_ascii_para_heading(navio.heading)
        return ('{' + glifo + '}') if e_jogador else ('[' + glifo + ']')

    largura_celula = 3
    filler = '~' * largura_celula
    grid = [[filler for _ in range(GRID_W)] for _ in range(GRID_H)]
    overlays_por_linha = {r: [] for r in range(GRID_H)}

    if inimigo.vivo():
        c, r = to_cell(inimigo.x, inimigo.y)
        texto_celula = celula(inimigo, False)
        grid[r][c] = texto_celula
        overlays_por_linha[r].append((c * largura_celula, texto_celula, cor_navio(estado, e_jogador=False)))
    if jogador.vivo():
        c, r = to_cell(jogador.x, jogador.y)
        texto_celula = celula(jogador, True)
        grid[r][c] = texto_celula
        overlays_por_linha[r].append((c * largura_celula, texto_celula, cor_navio(estado, e_jogador=True)))

    d = distancia(jogador, inimigo)
    attr_mar = cor_mar(estado)
    linhas = [("  N", 0, [])]
    for i, row in enumerate(grid):
        linhas.append((''.join(row), attr_mar, overlays_por_linha[i]))
    linhas.append(("  S", 0, []))

    zoom_recente = (estado.tempo - estado.zoom_mudou_em) < 2.0
    attr_zoom = curses.A_BOLD | curses.A_REVERSE if (zoom_recente and curses) else 0
    if zoom_recente and estado.cores_ativo:
        attr_zoom |= curses.color_pair(COR_AMARELO)
    linhas.append((f"ZOOM: ~{half_range}m | dist real: {d:.0f}m", attr_zoom, []))
    return linhas



# ----------------------------------------------------------------------
# INTERFACE CURSES
# ----------------------------------------------------------------------

RIGHT_X = 36


def safe_addstr(stdscr, y, x, text, attr=0):
    max_y, max_x = stdscr.getmaxyx()
    if y < 0 or y >= max_y or x >= max_x:
        return
    try:
        stdscr.addstr(y, x, text[:max(0, max_x - x - 1)], attr)
    except curses.error:
        pass


def desenhar_tela(stdscr, estado, buffer_entrada):
    stdscr.erase()
    max_y, max_x = stdscr.getmaxyx()

    row = 0
    prefixo = (f"CLI PIRATES | {estado.jogador.tipo_nome.upper()} | "
               f"tempo: {estado.tempo:5.1f}s | tripulacao livre: ")
    numero_livre = f"{estado.crew_livre()}/{estado.crew_total}"
    safe_addstr(stdscr, row, 0, prefixo, cor_header(estado))
    safe_addstr(stdscr, row, len(prefixo), numero_livre, cor_tripulacao_livre(estado))
    row += 1
    safe_addstr(stdscr, row, 0, "-" * min(max_x - 1, 78))
    row += 1

    if estado.hotkeys_ativo:
        safe_addstr(stdscr, row, 0,
                    "HOTKEYS: a/d leme  w/s vela  j/l canhao  i/k mira  espaco atirar/parar  "
                    "u/h bomba  e/r reparo (e circula, r remove, espaco add) | foco: " +
                    _descrever_foco(estado))
        row += 1

    safe_addstr(stdscr, row, 0, f"SEU NAVIO ({estado.jogador.tipo_nome.upper()})", curses.A_UNDERLINE)
    safe_addstr(stdscr, row, RIGHT_X, "CANHOES", curses.A_UNDERLINE)
    row += 1
    topo_colunas = row

    esquerda = build_navio_diagrama(estado)
    canhoes_linhas = build_canhoes_linhas(estado)
    roster = montar_tripulacao(estado)
    direita = canhoes_linhas + [("", 0), ("TRIPULACAO:", 0)] + \
        [(f"{SIMB_TRIPULANTE} {tid:4s} {tarefa:8s} {detalhe}", cor_tarefa(estado, tarefa))
         for tid, tarefa, detalhe in roster]

    maxlen = max(len(esquerda), len(direita))
    for i in range(maxlen):
        rowi = topo_colunas + i
        if i < len(esquerda):
            texto, attr = esquerda[i]
            safe_addstr(stdscr, rowi, 0, texto, attr)
        if i < len(direita):
            texto, attr = direita[i]
            safe_addstr(stdscr, rowi, RIGHT_X, texto, attr)

    row = topo_colunas + maxlen + 1
    safe_addstr(stdscr, row, 0, "== MAPA ==", curses.A_UNDERLINE)
    row += 1
    for texto, attr, overlays in build_mapa_linhas(estado):
        safe_addstr(stdscr, row, 0, texto, attr)
        for col, segmento, attr_seg in overlays:
            safe_addstr(stdscr, row, col, segmento, attr_seg)
        row += 1
    row += 1

    safe_addstr(stdscr, row, 0, "BUSSOLA", curses.A_UNDERLINE)
    row += 1
    for texto, attr, overlays in build_bussola_linhas(estado):
        safe_addstr(stdscr, row, 0, texto, attr)
        for col, segmento, attr_seg in overlays:
            safe_addstr(stdscr, row, col, segmento, attr_seg)
        row += 1
    row += 1

    safe_addstr(stdscr, row, 0, f"VISAO DO CAPITAO {SIMB_CAPITAO}", curses.A_UNDERLINE)
    row += 1
    for texto, attr, overlays in build_vista_linhas(estado):
        safe_addstr(stdscr, row, 0, texto, attr)
        for col, segmento, attr_seg in overlays:
            safe_addstr(stdscr, row, col, segmento, attr_seg)
        row += 1

    log_lines = list(estado.log)[-4:]
    base = max_y - (2 + len(log_lines) + 2)
    safe_addstr(stdscr, base, 0, "LOG", curses.A_UNDERLINE)
    for i, linha in enumerate(log_lines):
        safe_addstr(stdscr, base + 1 + i, 0, linha, cor_log(estado, linha))
    safe_addstr(stdscr, max_y - 2, 0, "-" * min(max_x - 1, 78))
    safe_addstr(stdscr, max_y - 1, 0, f"> {buffer_entrada}", curses.A_REVERSE)

    stdscr.refresh()


# ----------------------------------------------------------------------
# TELAS DE MENU / AJUDA / NAVIO / AJUSTES / FIM DE JOGO
# ----------------------------------------------------------------------

def tela_menu(stdscr):
    opcoes = [("Jogar", "jogar"), ("Como jogar", "como_jogar"),
              ("Escolher navio", "navio"), ("Ajustes", "ajustes"), ("Sair", "sair")]
    idx = 0
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    while True:
        stdscr.erase()
        for i, l in enumerate(TITULO_ARTE):
            safe_addstr(stdscr, i, 2, l)
        row = len(TITULO_ARTE) + 2
        for i, (label, _) in enumerate(opcoes):
            marcador = "> " if i == idx else "  "
            attr = curses.A_REVERSE if i == idx else 0
            safe_addstr(stdscr, row + i, 2, f"{marcador}[{i + 1}] {label}", attr)
        safe_addstr(stdscr, row + len(opcoes) + 2, 2,
                    "Use as setas + ENTER, ou digite o numero da opcao.")
        stdscr.refresh()

        ch = stdscr.getch()
        if ch == curses.KEY_UP:
            idx = (idx - 1) % len(opcoes)
        elif ch == curses.KEY_DOWN:
            idx = (idx + 1) % len(opcoes)
        elif ch in (curses.KEY_ENTER, 10, 13):
            return opcoes[idx][1]
        elif ord('1') <= ch <= ord(str(len(opcoes))):
            return opcoes[ch - ord('1')][1]


def tela_como_jogar(stdscr):
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    stdscr.erase()
    for i, l in enumerate(COMO_JOGAR_TEXTO):
        safe_addstr(stdscr, i, 2, l)
    stdscr.refresh()
    stdscr.getch()


def tela_navio(stdscr, config):
    idx = DIFICULDADES.index(config["tipo_navio"])
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    while True:
        stdscr.erase()
        safe_addstr(stdscr, 0, 2, "ESCOLHER NAVIO", curses.A_BOLD)
        safe_addstr(stdscr, 1, 2, "-" * 44)

        chave = DIFICULDADES[idx]
        p = NAVIO_TIPOS[chave]
        safe_addstr(stdscr, 3, 2, f"<  {p['navio'].upper()}  >", curses.A_BOLD)
        safe_addstr(stdscr, 4, 2, f"   dificuldade: {chave.upper()}")
        safe_addstr(stdscr, 6, 2, f"   Tripulacao total .... {p['crew_total']}")
        safe_addstr(stdscr, 7, 2, f"   Canhoes por lado .... {p['canhoes_lado']} "
                                   f"({p['canhoes_lado']*2} no total)")
        safe_addstr(stdscr, 8, 2, f"   Velas ............... {p['num_velas']}")
        safe_addstr(stdscr, 9, 2, f"   Tripulantes minimos/canhao ... {p['min_crew_canhao']}")
        safe_addstr(stdscr, 10, 2, f"   Velocidade base ...... {p['velocidade_max_base']:.0f}")
        safe_addstr(stdscr, 11, 2, f"   Taxa de giro ......... {p['giro_graus_seg']:.0f} graus/s")

        safe_addstr(stdscr, 13, 2, "SETA ESQUERDA/DIREITA muda | ENTER confirma e volta")
        stdscr.refresh()

        ch = stdscr.getch()
        if ch == curses.KEY_LEFT:
            idx = (idx - 1) % len(DIFICULDADES)
        elif ch == curses.KEY_RIGHT:
            idx = (idx + 1) % len(DIFICULDADES)
        elif ch in (curses.KEY_ENTER, 10, 13, 27):
            config["tipo_navio"] = DIFICULDADES[idx]
            return


def tela_ajustes(stdscr, config):
    itens = [
        ("Hotkeys", "hotkeys"),
        ("Cores", "cores"),
        ("Graficos Unicode", "unicode"),
    ]
    idx = 0
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    cores_disponiveis = bool(curses and curses.has_colors())
    while True:
        stdscr.erase()
        safe_addstr(stdscr, 0, 2, "AJUSTES", curses.A_BOLD)
        safe_addstr(stdscr, 1, 2, "-" * 44)
        for i, (label, chave) in enumerate(itens):
            estado_txt = "LIGADO" if config[chave] else "DESLIGADO"
            marcador = "> " if i == idx else "  "
            attr = curses.A_REVERSE if i == idx else 0
            safe_addstr(stdscr, 3 + i, 2, f"{marcador}{label:18s} <  {estado_txt}  >", attr)
        if not cores_disponiveis:
            safe_addstr(stdscr, 3 + len(itens), 2, "(este terminal nao parece suportar cores)")

        row = 3 + len(itens) + 2
        safe_addstr(stdscr, row, 2, "Com hotkeys LIGADO, teclas soltas controlam o navio sem")
        safe_addstr(stdscr, row + 1, 2, "precisar digitar comando + ENTER (ver 'Como jogar').")
        safe_addstr(stdscr, row + 2, 2, "Obs: com hotkeys ligado, 'a', 'l' e 'r' no prompt vazio")
        safe_addstr(stdscr, row + 3, 2, "viram hotkeys em vez de iniciar 'ajuda'/'leme'/'reparar'.")
        safe_addstr(stdscr, row + 4, 2, "Use TAB no prompt vazio pra digitar esses comandos mesmo assim.")
        safe_addstr(stdscr, row + 6, 2, "Graficos Unicode troca o codigo de bussola do mapa por")
        safe_addstr(stdscr, row + 7, 2, "setas unicode entre {chaves} (voce) / [colchetes] (inimigo).")
        safe_addstr(stdscr, row + 9, 2, "SETA CIMA/BAIXO move | ESQUERDA/DIREITA ou ENTER alterna")
        safe_addstr(stdscr, row + 10, 2, "ESC volta ao menu")
        stdscr.refresh()

        ch = stdscr.getch()
        if ch == curses.KEY_UP:
            idx = (idx - 1) % len(itens)
        elif ch == curses.KEY_DOWN:
            idx = (idx + 1) % len(itens)
        elif ch in (curses.KEY_LEFT, curses.KEY_RIGHT, curses.KEY_ENTER, 10, 13):
            chave = itens[idx][1]
            config[chave] = not config[chave]
        elif ch == 27:
            return


def tela_fim(stdscr, estado):
    stdscr.nodelay(False)
    stdscr.timeout(-1)
    opcoes = [("Jogar novamente", "jogar"), ("Menu principal", "menu"), ("Sair", "sair")]
    idx = 0
    while True:
        stdscr.erase()
        arte = list(ARTE_VITORIA if estado.fim == "vitoria" else ARTE_DERROTA)
        attr_arte = 0
        if estado.cores_ativo:
            attr_arte = curses.color_pair(COR_VERDE if estado.fim == "vitoria" else COR_VERMELHO)

        linhas = [""]
        linhas.append(f"Navio: {estado.jogador.tipo_nome}   "
                       f"Tempo de batalha: {estado.tempo:.1f}s")
        linhas.append(f"Tiros disparados: {estado.stats['tiros_jogador']}  "
                       f"Acertos: {estado.stats['acertos_jogador']}")
        linhas.append(f"Tiros recebidos:  {estado.stats['tiros_inimigo']}  "
                       f"Acertos do inimigo: {estado.stats['acertos_inimigo']}")
        canhoes_perdidos = sum(1 for lado in estado.jogador.canhoes.values()
                                for c in lado if not c.operacional())
        linhas.append(f"Canhoes perdidos: {canhoes_perdidos}/{estado.canhoes_lado * 2}")
        linhas.append("")
        linhas.append("Estado final do seu navio:")
        for p in PARTES:
            linhas.append(f"  {p:8s}[{barra(estado.jogador.partes[p], 10)}] "
                           f"{estado.jogador.partes[p]:5.1f}%")
        linhas.append("")

        for i, l in enumerate(arte):
            safe_addstr(stdscr, i, 2, l, attr_arte)
        for i, l in enumerate(linhas):
            safe_addstr(stdscr, len(arte) + i, 2, l)
        total_linhas = len(arte) + len(linhas)
        base = total_linhas + 1
        for i, (label, _) in enumerate(opcoes):
            marcador = "> " if i == idx else "  "
            attr = curses.A_REVERSE if i == idx else 0
            safe_addstr(stdscr, base + i, 2, f"{marcador}[{i + 1}] {label}", attr)
        stdscr.refresh()

        ch = stdscr.getch()
        if ch == curses.KEY_UP:
            idx = (idx - 1) % len(opcoes)
        elif ch == curses.KEY_DOWN:
            idx = (idx + 1) % len(opcoes)
        elif ch in (curses.KEY_ENTER, 10, 13):
            return opcoes[idx][1]
        elif ord('1') <= ch <= ord(str(len(opcoes))):
            return opcoes[ch - ord('1')][1]


# ----------------------------------------------------------------------
# LOOP DO JOGO
# ----------------------------------------------------------------------

def jogo_loop(stdscr, config):
    stdscr.nodelay(True)
    stdscr.timeout(POLL_MS)

    cores = config["cores"] and bool(curses.has_colors())
    estado = Estado(tipo_navio=config["tipo_navio"], hotkeys=config["hotkeys"],
                     cores=cores, graficos_unicode=config["unicode"])
    buffer_entrada = ""
    last_tick = time.time()
    tab_estado = {"ativo": False, "candidatos": [], "indice": 0, "prefixo": ""}

    while estado.rodando:
        ch = stdscr.getch()
        if ch != -1:
            if ch == 27:
                estado.rodando = False
                estado.fim = estado.fim or "derrota"
            elif ch in (curses.KEY_ENTER, 10, 13):
                if buffer_entrada.strip():
                    processar_comando(buffer_entrada.strip(), estado)
                    estado.ultimo_comando = buffer_entrada.strip()
                elif estado.ultimo_comando:
                    processar_comando(estado.ultimo_comando, estado)
                buffer_entrada = ""
                tab_estado["ativo"] = False
            elif ch in (curses.KEY_BACKSPACE, 127, 8):
                buffer_entrada = buffer_entrada[:-1]
                tab_estado["ativo"] = False
            elif ch == 9:
                if tab_estado["ativo"] and tab_estado["candidatos"]:
                    tab_estado["indice"] = (tab_estado["indice"] + 1) % len(tab_estado["candidatos"])
                else:
                    if buffer_entrada == "" or buffer_entrada.endswith(' '):
                        tokens_completos = [t for t in buffer_entrada.split(' ') if t != '']
                        partial = ''
                    else:
                        partes_buf = buffer_entrada.split(' ')
                        tokens_completos = [t for t in partes_buf[:-1] if t != '']
                        partial = partes_buf[-1]
                    prefixo = (' '.join(tokens_completos) + ' ') if tokens_completos else ''
                    candidatos = obter_candidatos(tokens_completos, partial, estado)
                    tab_estado["candidatos"] = candidatos
                    tab_estado["prefixo"] = prefixo
                    tab_estado["indice"] = 0
                    tab_estado["ativo"] = True
                if tab_estado["candidatos"]:
                    buffer_entrada = tab_estado["prefixo"] + tab_estado["candidatos"][tab_estado["indice"]]
            elif estado.hotkeys_ativo and buffer_entrada == "" and processar_hotkey(ch, estado):
                pass
            elif 32 <= ch <= 126:
                buffer_entrada += chr(ch)
                tab_estado["ativo"] = False

        agora = time.time()
        if agora - last_tick >= SIM_TICK:
            atualizar_simulacao(estado, agora - last_tick)
            last_tick = agora

        desenhar_tela(stdscr, estado, buffer_entrada)

    if estado.fim is None:
        estado.fim = "derrota"
    return tela_fim(stdscr, estado)


# ----------------------------------------------------------------------
# ESTADO GLOBAL DE TELAS (menu <-> jogo <-> navio <-> ajustes)
# ----------------------------------------------------------------------

def main(stdscr):
    try:
        locale.setlocale(locale.LC_ALL, '')
    except locale.Error:
        pass
    curses.curs_set(0)
    curses.noecho()
    stdscr.keypad(True)

    if curses.has_colors():
        curses.start_color()
        try:
            curses.use_default_colors()
            fundo = -1
        except curses.error:
            fundo = curses.COLOR_BLACK
        curses.init_pair(COR_VERDE, curses.COLOR_GREEN, fundo)
        curses.init_pair(COR_AMARELO, curses.COLOR_YELLOW, fundo)
        curses.init_pair(COR_VERMELHO, curses.COLOR_RED, fundo)
        curses.init_pair(COR_JOGADOR, curses.COLOR_CYAN, fundo)
        curses.init_pair(COR_INIMIGO, curses.COLOR_MAGENTA, fundo)
        curses.init_pair(COR_MAR, curses.COLOR_BLUE, fundo)

    config = {"tipo_navio": "normal", "hotkeys": False, "cores": False, "unicode": False}
    tela_atual = "menu"

    while tela_atual != "sair":
        if tela_atual == "menu":
            tela_atual = tela_menu(stdscr)
        elif tela_atual == "como_jogar":
            tela_como_jogar(stdscr)
            tela_atual = "menu"
        elif tela_atual == "navio":
            tela_navio(stdscr, config)
            tela_atual = "menu"
        elif tela_atual == "ajustes":
            tela_ajustes(stdscr, config)
            tela_atual = "menu"
        elif tela_atual == "jogar":
            tela_atual = jogo_loop(stdscr, config)
        else:
            tela_atual = "menu"


if __name__ == "__main__":
    if curses is None:
        print("O modulo 'curses' nao esta disponivel neste ambiente.")
        sys.exit(1)
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    except curses.error as e:
        print(f"Erro de terminal (talvez a janela esteja pequena demais): {e}")
        sys.exit(1)
