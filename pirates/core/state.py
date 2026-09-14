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
from .tripulacao import (
    POSTO_BOMBA, Posto, Tripulacao, aplicar_efetivos, desejado_de_contagens,
    descrever_frente, descrever_posto, mesma_tarefa, posto_canhao,
    posto_reparo, reconciliar,
)


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
        ia_lado_bordada:   Lado ('estibordo'/'bombordo') que a IA apresenta ao
            jogador ao circular; alterna quando o lado atual esgota a carga.
        ia_modo_movimento: 'aproximar' | 'circular' | 'afastar' — modo de
            manobra atual da IA, mantido entre ticks para dar histerese.
        ia_ilha_evadindo: Índice em `ilhas_arena` da ilha que a IA está
            contornando agora, ou None.
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
            bomba_mult=params["bomba_mult"],
            cooldown_mult=params["cooldown_mult"],
            resist_casco=params["resist_casco"],
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
            bomba_mult=params["bomba_mult"],
            cooldown_mult=params["cooldown_mult"],
            resist_casco=params["resist_casco"],
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

        # Roster de indivíduos (ver pirates/core/tripulacao.py). As contagens
        # acima seguem sendo a alocação; o roster diz quem já chegou ao posto.
        self.tripulacao: Tripulacao = Tripulacao(self.tripulante_ids)
        self.inimigo_tripulacao: Tripulacao = Tripulacao(
            [f"I{i+1}" for i in range(self.inimigo_crew_total)]
        )

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
        self.ia_lado_bordada: str = random.choice(('estibordo', 'bombordo'))
        self.ia_modo_movimento: str = 'circular'
        self.ia_ilha_evadindo: int | None = None
        self.ia_crew_reavaliado_em: float = -999.0
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

    # Quem permanece mantém posto e trânsito; quem entra é gente contratada
    # agora, e por isso assume o primeiro posto sem pagar trânsito.
    estado.tripulacao.redimensionar(estado.tripulante_ids)
    reconciliar_jogador(estado)


def reconciliar_jogador(estado: Estado) -> None:
    """Casa o roster do jogador com as contagens de alocação.

    Chamar depois de qualquer mudança em `Canhao.tripulantes`, `crew_reparo`
    ou `crew_bomba`. É idempotente: se nada mudou, ninguém é tocado e nenhum
    trânsito reinicia.

    Loga cada trânsito que começa agora. É a única mensagem que ensina a regra
    ao jogador, e só aqui o tempo de chegada é conhecido — quem mexeu nas
    contagens ainda não sabia de onde viria cada tripulante.
    """
    antes = {t.id: t.posto for t in estado.tripulacao.membros}

    reconciliar(
        estado.tripulacao,
        desejado_de_contagens(estado.jogador, estado.crew_reparo, estado.crew_bomba),
    )
    aplicar_efetivos(estado.jogador, estado.tripulacao)

    partidas: dict[tuple, float] = {}
    for t in estado.tripulacao.membros:
        if t.posto != antes.get(t.id) and t.em_transito():
            chave = (t.posto, t.ultimo_posto)
            partidas[chave] = max(partidas.get(chave, 0.0), t.transito_restante)
    for (destino, origem), segundos in partidas.items():
        estado.log.append(
            f"Equipe a caminho de {descrever_posto(destino)}"
            f" (vinha de {descrever_posto(origem)}): {segundos:.0f}s"
        )


def reconciliar_inimigo(estado: Estado) -> None:
    """Espelho de `reconciliar_jogador` para o navio inimigo."""
    reconciliar(
        estado.inimigo_tripulacao,
        desejado_de_contagens(
            estado.inimigo, estado.inimigo_crew_reparo, estado.inimigo_crew_bomba
        ),
    )
    aplicar_efetivos(estado.inimigo, estado.inimigo_tripulacao)


# ---------------------------------------------------------------------------
# Roster de tripulação
# ---------------------------------------------------------------------------

def montar_tripulacao(estado: Estado) -> list[tuple[str, str, str]]:
    """Constrói a lista de tripulantes com sua tarefa atual.

    Lê o roster de indivíduos (`estado.tripulacao`), e não as contagens: assim
    cada ID fica preso ao seu tripulante, em vez de pular de posto sempre que
    outro é realocado.

    Args:
        estado: Estado atual do jogo.

    Returns:
        Lista de tuplas (id_tripulante, tarefa, detalhe). A tarefa é uma de
        'canhao', 'reparo', 'bomba', 'transito' ou 'ocioso'.
    """
    roster: list[tuple[str, str, str]] = []

    for t in estado.tripulacao.membros:
        if t.posto is None:
            roster.append((t.id, "ocioso", "conves"))
        elif t.em_transito():
            destino = descrever_posto(t.posto)
            roster.append((t.id, "transito", f"-> {destino} ({t.transito_restante:.1f}s)"))
        elif t.posto[0] == 'canhao':
            label = f"{'E' if t.posto[1] == 'estibordo' else 'B'}{t.posto[2]}"
            roster.append((t.id, "canhao", f"canhao {label}"))
        elif t.posto[0] == 'reparo':
            roster.append((t.id, "reparo", t.posto[1]))
        else:
            roster.append((t.id, "bomba", "porao"))

    return roster


# ---------------------------------------------------------------------------
# Realocação automática de tripulação
# ---------------------------------------------------------------------------

def _liberar_tripulantes(
    estado: Estado,
    necessario: int,
    destino: Posto,
) -> int:
    """Libera até *necessario* tripulantes puxando de outras tarefas.

    Ordem (quem é retirado primeiro):
    1. Canhões do bordo oposto (retira o mínimo necessário, não o canhão inteiro).
    2. Reparo de outras partes (retira parcialmente).
    3. Bomba — último recurso, e nunca fica zerada enquanto houver água a bordo.

    **Quem já está na mesma frente de trabalho do destino nunca é candidato**
    (ver `tripulacao.mesma_tarefa`): canhões do mesmo bordo, reparo da mesma
    parte. Roubar de B1 para guarnecer B2 não fortalece a bordada de bombordo,
    só embaralha as mesmas pessoas — e ainda cobra trânsito por isso.

    Isso restringe apenas a realocação automática. Mover gente entre canhões do
    mesmo bordo continua possível de forma explícita ('canhao e1 parar' e
    depois armar E2), passando pelo convés.

    Args:
        estado:     Estado atual do jogo.
        necessario: Quantidade de tripulantes a liberar.
        destino:    Posto que vai receber os tripulantes.

    Returns:
        Quantidade efetivamente liberada.
    """
    liberado = 0
    movimentos: list[str] = []
    bloqueados = 0  # gente que só não veio por ser da mesma frente de trabalho

    for lado in ('bombordo', 'estibordo'):
        for c in estado.jogador.canhoes[lado]:
            if liberado >= necessario:
                break
            if c.tripulantes <= 0:
                continue
            if mesma_tarefa(posto_canhao(c), destino):
                bloqueados += c.tripulantes
                continue
            tirar = min(c.tripulantes, necessario - liberado)
            restante = c.tripulantes - tirar
            if restante < estado.min_crew_canhao:
                # Sobra abaixo do mínimo não opera o canhão: leva todos.
                tirar = c.tripulantes
                c.dist_alvo = None
            movimentos.append(f"{tirar} de Canhao {c.label}")
            c.tripulantes -= tirar
            liberado += tirar
        if liberado >= necessario:
            break

    if liberado < necessario:
        for parte in PARTES:
            if liberado >= necessario:
                break
            n_atual = estado.crew_reparo.get(parte, 0)
            if n_atual <= 0:
                continue
            if mesma_tarefa(posto_reparo(parte), destino):
                bloqueados += n_atual
                continue
            tirar = min(n_atual, necessario - liberado)
            estado.crew_reparo[parte] -= tirar
            liberado += tirar
            movimentos.append(f"{tirar} de Reparo {parte}")

    if liberado < necessario and not mesma_tarefa(POSTO_BOMBA, destino):
        # A bomba é o último a ceder, e mantém pelo menos um homem enquanto
        # houver água a bordo — ficar sem bombeamento afunda o navio.
        reserva = 1 if estado.jogador.agua > 0 else 0
        disponivel = max(0, estado.crew_bomba - reserva)
        tirar = min(disponivel, necessario - liberado)
        if tirar > 0:
            estado.crew_bomba -= tirar
            liberado += tirar
            movimentos.append(f"{tirar} da Bomba")
            if estado.jogador.agua > 0:
                estado.log.append(
                    f"Atencao: {tirar} tripulante(s) saiu da bomba com o porao"
                    f" a {estado.jogador.agua:.0f}% de agua"
                )

    if movimentos:
        estado.log.append(f"Tripulacao realocada: {', '.join(movimentos)}")
    if liberado < necessario and bloqueados > 0:
        estado.log.append(
            f"Tripulantes de {descrever_frente(destino)} nao podem ser"
            f" realocados para reforcar a propria frente"
        )
    return liberado


def tentar_assumir_tripulacao(
    estado: Estado,
    quantidade_desejada: int,
    atual_no_alvo: int,
    destino: Posto,
) -> tuple[int, bool]:
    """Tenta alocar *quantidade_desejada* tripulantes, realocando se necessário.

    Args:
        estado:             Estado atual do jogo.
        quantidade_desejada: Número total de tripulantes desejado na tarefa.
        atual_no_alvo:      Tripulantes já alocados na tarefa alvo.
        destino:            Posto que vai receber os tripulantes. Define tanto
                            o alvo quanto quem está fora da lista de doadores
                            (ver `_liberar_tripulantes`).

    Returns:
        Tupla (quantidade_final, cortou) onde *cortou* indica insuficiência.
    """
    livre = estado.crew_livre() + atual_no_alvo
    if quantidade_desejada <= livre:
        return quantidade_desejada, False
    faltam = quantidade_desejada - livre
    liberado = _liberar_tripulantes(estado, faltam, destino)
    livre_final = livre + liberado
    final = min(quantidade_desejada, livre_final)
    return final, final < quantidade_desejada
