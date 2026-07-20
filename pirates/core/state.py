"""
state.py – Estado global do jogo e gerenciamento de tripulação em CLI PIRATES.

A classe Estado é o objeto central passado para quase todas as funções do jogo.
Inclui também as funções de realocação automática de tripulação, que implementam
o sistema de prioridades (bomba > reparo > canhões).
"""

import random
from collections import deque

from ..constants import (
    PARTES, NAVIO_TIPOS, PESO_CASCO, AREA_CASCO,
    FUGA_ENTRADA_MIN, FUGA_ENTRADA_MAX, FUGA_SAIDA_MIN, FUGA_SAIDA_MAX,
    VENTO_INTENSIDADE_MIN, VENTO_INTENSIDADE_MAX,
    VENTO_RESORTEIO_MIN_SEG, VENTO_RESORTEIO_MAX_SEG,
)
from .ship import Navio, criar_canhoes
from .porao import estoque_inicial_jogador, gerar_porao_inimigo
from .velas import gerar_slots_fabrica
from .frota import Frota


class Estado:
    """Estado completo de uma partida de CLI PIRATES.

    Attributes:
        tipo_navio:        Chave em NAVIO_TIPOS ('chalupa', 'brigantim', 'galeao').
        crew_total:        Total de tripulantes do navio do jogador.
        canhoes_lado:      Número de canhões por lado.
        num_velas:         Número de velas do navio.
        min_crew_canhao:   Tripulantes mínimos para operar um canhão.
        tripulante_ids:    Lista de IDs ('T1', 'T2', …) de tripulantes.
        canhao_ids:        Lista de IDs de canhões ('E1', 'B1', …).
        jogador:           Navio controlado pelo jogador.
        inimigo:           Navio controlado pela IA.
        inimigo_crew_reparo: Dict parte→int com tripulação de reparo do inimigo.
        inimigo_crew_bomba:  Tripulantes do inimigo nas bombas.
        ia_limiar_agua:    Nível de água que dispara o modo bomba da IA.
        ia_limiar_casco:   HP de casco que dispara o reparo da IA.
        ia_limiar_fuga_entrada: Moral abaixo da qual o inimigo entra em modo fuga.
        ia_limiar_fuga_saida:   Moral acima da qual o inimigo sai do modo fuga.
        inimigo_em_fuga:   True quando o inimigo está tentando escapar.
        tempo_fuga_longe:  Segundos que o inimigo ficou além de ALCANCE_FUGA_ESCAPE.
        jogador_tentando_fugir: True quando o jogador está tentando escapar (comando 'fugir').
        tempo_fuga_jogador:     Segundos que o jogador ficou além de ALCANCE_FUGA_ESCAPE.
        inimigo_tipo_navio:  Chave NAVIO_TIPOS do inimigo atualmente engajado (pode
                              divergir de tipo_navio do jogador; ver mundo aberto/notoriedade).
        inimigo_crew_total:      Total de tripulantes do inimigo nesta partida.
        inimigo_min_crew_canhao: Tripulantes mínimos por canhão do inimigo nesta partida.
        inimigo_cooldown_bonus:  Fração de redução de cooldown do inimigo (bônus elite).
        crew_reparo:       Dict parte→int com tripulação de reparo do jogador.
        crew_bomba:        Tripulantes do jogador nas bombas.
        tempo:             Tempo decorrido de simulação, em segundos.
        rodando:           False quando o loop principal deve encerrar.
        fim:               'vitoria', 'derrota', 'fuga', 'fuga_jogador' ou None.
        stats:             Dict com contadores de tiros e acertos.
        log:               Deque de mensagens recentes (máx 8).
        ultimo_comando:    Último comando de texto digitado (para repetição).
        hotkeys_ativo:     Hotkeys de teclado estão ligadas.
        cores_ativo:       Cores curses estão ligadas.
        graficos_unicode:  Setas Unicode no mapa estão ligadas.
        foco:              Seleção atual para hotkeys (canhão ou parte de reparo).
        zoom_atual:        Nível de zoom atual do minimapa.
        zoom_mudou_em:     Timestamp da última mudança de zoom.
    """

    def __init__(
        self,
        tipo_navio: str = "brigantim",
        hotkeys: bool = False,
        cores: bool = False,
        graficos_unicode: bool = False,
        textura_mar: bool = True,
        rastro_ativo: bool = True,
    ) -> None:
        self.tipo_navio = tipo_navio if tipo_navio in NAVIO_TIPOS else "brigantim"
        params = NAVIO_TIPOS[self.tipo_navio]

        self.crew_total: int = params["crew_total"]
        self.canhoes_lado: int = params["canhoes_lado"]
        self.num_velas: int = params["num_velas"]
        self.min_crew_canhao: int = params["min_crew_canhao"]
        self.tripulante_ids: list[str] = [f"T{i+1}" for i in range(self.crew_total)]
        self.canhao_ids: list[str] = [
            f"{l}{i}" for l in ("E", "B") for i in range(1, self.canhoes_lado + 1)
        ]

        cap = params["porao_capacidade"]
        self.jogador = Navio(
            "Seu Navio", x=0, y=0, heading=0,
            velocidade_max_base=params["velocidade_max_base"],
            giro_graus_seg=params["giro_graus_seg"],
            reparo_mult=params["reparo_mult"],
            porao_capacidade=cap,
            peso_casco=PESO_CASCO[self.tipo_navio],
            area_casco=AREA_CASCO[self.tipo_navio],
            slots_vela=gerar_slots_fabrica(self.tipo_navio),
        )
        self.jogador.tipo_nome = params["navio"]
        self.jogador.num_velas = self.num_velas
        self.jogador.canhoes = criar_canhoes(self.canhoes_lado)
        self.jogador.porao = estoque_inicial_jogador(cap)

        # O inimigo usa o mesmo perfil do jogador (simetria total).
        self.inimigo = Navio(
            "Navio Inimigo", x=400, y=650, heading=180,
            velocidade_max_base=params["velocidade_max_base"],
            giro_graus_seg=params["giro_graus_seg"],
            reparo_mult=params["reparo_mult"],
            porao_capacidade=cap,
            peso_casco=PESO_CASCO[self.tipo_navio],
            area_casco=AREA_CASCO[self.tipo_navio],
            slots_vela=gerar_slots_fabrica(self.tipo_navio),
        )
        self.inimigo.tipo_nome = params["navio"]
        self.inimigo.num_velas = self.num_velas
        self.inimigo.porao = gerar_porao_inimigo(cap, self.tipo_navio, 0.0)
        self.inimigo.canhoes = criar_canhoes(self.canhoes_lado)
        self.inimigo_crew_reparo: dict[str, int] = {p: 0 for p in PARTES}
        self.inimigo_crew_bomba: int = 0

        # Limiares aleatorizados por partida para criar variação na IA.
        self.ia_limiar_agua: float = random.uniform(20.0, 40.0)
        self.ia_limiar_casco: float = random.uniform(40.0, 60.0)
        self.ia_limiar_fuga_entrada: float = random.uniform(FUGA_ENTRADA_MIN, FUGA_ENTRADA_MAX)
        self.ia_limiar_fuga_saida: float = random.uniform(FUGA_SAIDA_MIN, FUGA_SAIDA_MAX)
        self.inimigo_em_fuga: bool = False
        self.tempo_fuga_longe: float = 0.0
        self.jogador_tentando_fugir: bool = False
        self.tempo_fuga_jogador: float = 0.0

        # Perfil de combate do inimigo engajado (por padrão espelha o do jogador;
        # o mundo aberto pode sobrescrever por navio, ver game.py/notoriedade).
        self.inimigo_tipo_navio: str = self.tipo_navio
        self.inimigo_crew_total: int = self.crew_total
        self.inimigo_min_crew_canhao: int = self.min_crew_canhao
        self.inimigo_cooldown_bonus: float = 0.0

        self.crew_reparo: dict[str, int] = {p: 0 for p in PARTES}
        self.crew_bomba: int = 0
        self.tempo: float = 0.0
        self.rodando: bool = True
        self.fim: str | None = None
        self.stats: dict[str, int] = {
            "tiros_jogador": 0, "acertos_jogador": 0,
            "tiros_inimigo": 0,  "acertos_inimigo": 0,
        }
        self.log: deque[str] = deque(maxlen=8)
        self.ultimo_comando: str | None = None
        self.hotkeys_ativo: bool = hotkeys
        self.cores_ativo: bool = cores
        self.graficos_unicode: bool = graficos_unicode
        self.textura_mar: bool = textura_mar
        self.rastro_ativo: bool = rastro_ativo
        self.foco = None
        self.zoom_atual: int | None = None
        self.zoom_mudou_em: float = -999.0
        self.modo_adm: bool = False
        self.frota: Frota = Frota()
        self.frota.adicionar(
            nome=self.jogador.nome, navio=self.jogador,
            tipo=self.tipo_navio, porto_id=None,
        )
        self.frota.indice_ativo = 0
        self.ia_island_avoidance_mult: float = random.uniform(1.5, 3.0)
        self.ilhas_arena: list = []
        self.em_colisao_ilha_inimigo: bool = False

        self.vento_direcao: float = random.uniform(0.0, 360.0)
        self.vento_direcao_alvo: float = self.vento_direcao
        self.vento_intensidade: float = random.uniform(
            VENTO_INTENSIDADE_MIN, VENTO_INTENSIDADE_MAX
        )
        self.vento_intensidade_alvo: float = self.vento_intensidade
        self.vento_proximo_resorteio_em: float = random.uniform(
            VENTO_RESORTEIO_MIN_SEG, VENTO_RESORTEIO_MAX_SEG
        )
        self.vento_zona_anterior_jogador: str | None = None

        self.log.append(
            f"Bem-vindo ao conves do {params['navio']}, capitao. "
            f"Digite 'ajuda' (TAB circula opcoes)."
        )

    def crew_canhoes_usada(self) -> int:
        """Total de tripulantes alocados em todos os canhões do jogador."""
        return sum(c.tripulantes for lado in self.jogador.canhoes.values() for c in lado)

    def crew_continua_usada(self) -> int:
        """Total de tripulantes em tarefas contínuas (canhões + reparo + bomba)."""
        return sum(self.crew_reparo.values()) + self.crew_bomba + self.crew_canhoes_usada()

    def crew_livre(self) -> int:
        """Tripulantes sem tarefa atribuída (ociosos no convés)."""
        return self.crew_total - self.crew_continua_usada()


def sincronizar_crew_com_navio_ativo(estado: Estado, tipo_navio_ativo: str) -> None:
    """Recalcula crew_total/tripulante_ids/canhao_ids a partir do navio ativo e do
    nível de upgrade 'tripulante_extra' desse navio específico.

    Chamar sempre que estado.jogador passar a apontar para outro Navio (troca
    de navio na frota, ou restauração de save) — crew_total/canhao_ids/
    tipo_navio são campos de Estado, não de Navio, então não acompanham a
    troca automaticamente.
    """
    estado.tipo_navio = tipo_navio_ativo
    base = NAVIO_TIPOS[tipo_navio_ativo]["crew_total"]
    extra = estado.jogador.upgrade_niveis.get("tripulante_extra", 0)
    estado.crew_total = base + extra
    estado.tripulante_ids = [f"T{i+1}" for i in range(estado.crew_total)]

    canhoes_lado = len(estado.jogador.canhoes.get('bombordo', []))
    estado.canhoes_lado = canhoes_lado
    estado.canhao_ids = [
        f"{l}{i}" for l in ("E", "B") for i in range(1, canhoes_lado + 1)
    ]


# ---------------------------------------------------------------------------
# Roster de tripulação
# ---------------------------------------------------------------------------

def montar_tripulacao(estado: Estado) -> list[tuple[str, str, str]]:
    """Constrói a lista de tripulantes com sua tarefa atual.

    Args:
        estado: Estado atual do jogo.

    Returns:
        Lista de tuplas (id_tripulante, tarefa, detalhe).
    """
    ids = estado.tripulante_ids
    roster: list[tuple[str, str, str]] = []
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


# ---------------------------------------------------------------------------
# Realocação automática de tripulação
# ---------------------------------------------------------------------------

def _liberar_tripulantes(
    estado: Estado,
    necessario: int,
    ignorar_canhao=None,
    ignorar_parte: str | None = None,
) -> int:
    """Libera até *necessario* tripulantes puxando de outras tarefas.

    Ordem (quem é retirado primeiro):
    1. Canhões (libera o canhão inteiro).
    2. Reparo (retira parcialmente).
    A bomba nunca é retirada automaticamente.

    Args:
        estado:         Estado atual do jogo.
        necessario:     Quantidade de tripulantes a liberar.
        ignorar_canhao: Canhão que não deve ser desarmado.
        ignorar_parte:  Parte de reparo que não deve ser reduzida.

    Returns:
        Quantidade efetivamente liberada.
    """
    liberado = 0
    movimentos: list[str] = []

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


def tentar_assumir_tripulacao(
    estado: Estado,
    quantidade_desejada: int,
    atual_no_alvo: int,
    ignorar_canhao=None,
    ignorar_parte: str | None = None,
) -> tuple[int, bool]:
    """Tenta alocar *quantidade_desejada* tripulantes, realocando se necessário.

    Args:
        estado:             Estado atual do jogo.
        quantidade_desejada: Número total de tripulantes desejado na tarefa.
        atual_no_alvo:      Tripulantes já alocados na tarefa alvo.
        ignorar_canhao:     Canhão alvo (não deve ser esvaziado).
        ignorar_parte:      Parte de reparo alvo (não deve ser reduzida).

    Returns:
        Tupla (quantidade_final, cortou) onde *cortou* indica insuficiência.
    """
    livre = estado.crew_livre() + atual_no_alvo
    if quantidade_desejada <= livre:
        return quantidade_desejada, False
    faltam = quantidade_desejada - livre
    liberado = _liberar_tripulantes(
        estado, faltam,
        ignorar_canhao=ignorar_canhao,
        ignorar_parte=ignorar_parte,
    )
    livre_final = livre + liberado
    final = min(quantidade_desejada, livre_final)
    return final, final < quantidade_desejada
