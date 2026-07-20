"""
ship.py – Classes Navio e Canhao de CLI PIRATES.

Define as entidades físicas do jogo: o canhão como arma individual
e o navio como entidade composta com física de movimento, reparo e água.
"""

import math

from ..constants import (
    PARTES, PARTES_CRITICAS,
    MAPA_TAMANHO, GIRO_GRAUS_SEG_PADRAO,
    TAXA_REPARO_SEG, REPARO_K, FATOR_TABUAS_POR_HP,
    AGUA_BASE, AGUA_K, SAIDA_BOMBA_SEG,
    MORAL_PESO_CASCO, MORAL_PESO_AGUA, MORAL_PESO_OUTRAS,
    MORAL_QUEDA_TAXA_SEG, MORAL_K, MORAL_RECUP_BASE_SEG, MORAL_BONUS_ACERTO,
    MORAL_LIMIAR_ALTO, MORAL_LIMIAR_MEDIO,
    MORAL_MULT_NORMAL, MORAL_MULT_ABALADO, MORAL_MULT_COMBALIDO, MORAL_MULT_PANICO,
    MORAL_CRASH_RECURSOS_TETO, MORAL_CRASH_RECURSOS_DURACAO_SEG,
    K_ARRASTO_CASCO,
)
from .utils import clamp
from .porao import Porao, estoque_inicial_jogador  # noqa: F401 (re-exportado)
from .velas import (
    bonus_fixo_vela_bruto, bonus_curva_vela_bruto,
    indice_slot_principal_inicial,
)
from .movimento import calcular_tick_fisica


class Canhao:
    """Representa um canhão individual em um dos lados do navio.

    Attributes:
        lado:        'estibordo' ou 'bombordo'.
        indice:      Posição 1-based na fileira do lado (E1, E2, …).
        tripulantes: Quantos tripulantes estão operando este canhão.
        dist_alvo:   Distância estimada do alvo em metros, ou None se
                     o canhão não está mirando.
        mira_atual:  Última distância configurada (mantida ao parar,
                     para reutilização na próxima vez que for armado).
        proximo_tiro: Timestamp (estado.tempo) a partir do qual o canhão
                      pode disparar novamente.
    """

    def __init__(self, lado: str, indice: int) -> None:
        self.lado = lado
        self.indice = indice
        self.tripulantes: int = 0
        self.dist_alvo: float | None = None
        self.mira_atual: float = 300.0
        self.proximo_tiro: float = 0.0
        self.aviso_sem_municao: bool = False

    @property
    def label(self) -> str:
        """Identificador legível, e.g. 'E1', 'B2'."""
        return f"{'E' if self.lado == 'estibordo' else 'B'}{self.indice}"

    def armado(self) -> bool:
        """Retorna True se o canhão tem tripulação e alvo definido."""
        return self.tripulantes >= 1 and self.dist_alvo is not None


def calcular_entrada_agua(partes: dict) -> float:
    """Calcula a taxa de entrada de água (unid/s) a partir do dano nas partes críticas.

    Função pura: não aplica dt nem modifica nenhum estado.

    Args:
        partes: Dict parte→HP (0-100) do navio.

    Returns:
        Taxa de entrada de água em unidades por segundo.
    """
    entrada = 0.0
    for p in PARTES_CRITICAS:
        dano_frac = (100 - partes[p]) / 100
        entrada += AGUA_BASE * (math.exp(AGUA_K * dano_frac) - 1)
    return entrada


def resolver_canhao(id_str: str, jogador: 'Navio') -> 'Canhao | None':
    """Converte um ID de texto ('E1', 'b2', etc.) para o objeto Canhao.

    Args:
        id_str:  String de identificação do canhão (case-insensitive).
        jogador: Navio do jogador que possui os canhões.

    Returns:
        O objeto Canhao correspondente, ou None se o ID for inválido.
    """
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


def criar_canhoes(canhoes_lado: int) -> dict[str, list[Canhao]]:
    """Cria o dict lado→lista[Canhao] para um navio com *canhoes_lado* canhões por lado."""
    return {
        'bombordo':  [Canhao('bombordo',  i + 1) for i in range(canhoes_lado)],
        'estibordo': [Canhao('estibordo', i + 1) for i in range(canhoes_lado)],
    }


class Navio:
    """Representa um navio com física de movimento, dano e inundação.

    Attributes:
        nome:                Nome exibido no HUD.
        x, y:               Posição no mapa (unidades de jogo).
        heading:            Rumo atual em graus (Norte = 0, horário).
        heading_alvo:       Rumo para o qual o leme aponta.
        velocidade:         Velocidade atual (unidades/segundo).
        slots_vela:         Lista de slots de vela (proa/mastros/popa/aux).
        ancorado:           Se True, velocidade máxima é 0 e os empuxos de
                             vento são suprimidos (leme continua girando).
        partes:             Dict parte→HP (0-100) para cada parte reparável.
        agua:               Nível de água no porão (0-100). 100 = afundou.
        afundado:           True quando água atinge 100.
        canhoes:            Dict lado→lista[Canhao], populado externamente.
        alcance_canhao:     Alcance máximo dos canhões deste navio.
        velocidade_max_base: Velocidade máxima sem dano nem velas.
        giro_graus_seg:     Taxa de giro do leme (graus/segundo).
        reparo_mult:        Multiplicador de eficiência de reparo.
        tipo_nome:          Nome do tipo de navio ('Chalupa', etc.).
        num_velas:          Número de velas (cosmético, exibido no HUD).
    """

    def __init__(
        self,
        nome: str,
        x: float,
        y: float,
        heading: float,
        velocidade_max_base: float = 11.0,
        giro_graus_seg: float = GIRO_GRAUS_SEG_PADRAO,
        reparo_mult: float = 1.0,
        porao_capacidade: int = 0,
        peso_casco: float = 500.0,
        area_casco: float = 16.0,
        slots_vela: list[dict] | None = None,
    ) -> None:
        self.nome = nome
        self.x = x
        self.y = y
        self.heading = heading % 360
        self.heading_alvo = heading % 360
        self.velocidade: float = 0.0
        self.partes: dict[str, float] = {p: 100.0 for p in PARTES}
        self.agua: float = 0.0
        self.afundado: bool = False
        self.canhoes: dict[str, list[Canhao]] = {}
        self.alcance_canhao: float = 550.0
        self.velocidade_max_base = velocidade_max_base
        self.giro_graus_seg = giro_graus_seg
        self.reparo_mult = reparo_mult
        self.tipo_nome: str = ""
        self.num_velas: int = 1
        self.moral_atual: float = 100.0
        self.porao: Porao = Porao(porao_capacidade)
        self.upgrades: dict[str, float] = {}
        self.upgrade_niveis: dict[str, int] = {}
        self.itens_topo: dict[str, bool] = {}
        self.peso_casco = peso_casco
        self.area_casco = area_casco
        self.slots_vela: list[dict] = slots_vela if slots_vela is not None else []
        self.slot_vela_selecionado: int = (
            indice_slot_principal_inicial(self.slots_vela) if self.slots_vela else 0
        )
        self.ancorado: bool = False
        self.eficiencia_vento_atual: float = 1.0
        self.fator_intensidade_vento_atual: float = 1.0
        self.velocidade_lateral: float = 0.0
        self._recursos_criticos_zerados: bool | None = None
        self.moral_lock_restante: float = 0.0

    def vivo(self) -> bool:
        """Retorna True enquanto o navio não afundou."""
        return not self.afundado

    def taxa_giro(self) -> float:
        """Taxa de giro efetiva: giro_base × bônus de curva da soma dos
        slots de vela, reduzida proporcionalmente ao dano da roda do
        leme. Não depende do vento (doc08_vento.md §3)."""
        base = self.giro_graus_seg * (1.0 + bonus_curva_vela_bruto(self.slots_vela))
        return base * max(0.0, self.partes['roda'] / 100)

    def velocidade_maxima(self) -> float:
        """Velocidade máxima como ponto de equilíbrio entre empuxo da vela
        (soma dos slots) e arrasto do casco (doc08_vento.md §6) — sem teto
        artificial. Zero se ancorado."""
        fator_dano = (self.partes['vela'] / 100) * (self.partes['mastro'] / 100)

        if self.ancorado:
            return 0.0

        empuxo = (
            self.velocidade_max_base
            * (1.0 + bonus_fixo_vela_bruto(self.slots_vela))
            * self.eficiencia_vento_atual
            * self.fator_intensidade_vento_atual
            * (1.0 + self.upgrades.get('velocidade_giro', 0.0))
        )
        if empuxo <= 0 or self.area_casco <= 0:
            return 0.0

        vmax = math.sqrt(empuxo / (K_ARRASTO_CASCO * self.area_casco))
        return vmax * fator_dano

    def alcance_canhao_efetivo(self) -> float:
        """Alcance efetivo dos canhões, incluindo upgrade 'alcance_canhao' (metros extras)."""
        return self.alcance_canhao + self.upgrades.get('alcance_canhao', 0.0)

    def resistencia_casco_mult(self) -> float:
        """Multiplicador aplicado ao dano recebido no casco.

        Um bônus fracionário de "+X% HP casco" (upgrades['resistencia_casco'])
        é matematicamente equivalente a reduzir o dano recebido por um fator
        1/(1+X), sem alterar a escala 0-100 de partes['casco'].
        """
        return 1.0 / (1.0 + self.upgrades.get('resistencia_casco', 0.0))

    def atualizar_movimento(
        self, dt: float,
        angulo_relativo_vento_atual: float = 90.0,
        intensidade_vento_atual: float = 0.0,
        vento_direcao_atual: float = 0.0,
    ) -> None:
        """Aplica física de giro, propulsão (equilíbrio empuxo-vs-arrasto),
        deriva lateral (curva de leme + través) e empuxo constante de vento
        pro intervalo de tempo *dt*. Ver doc08_vento.md, doc09_deriva.md,
        doc10_customizacao_vela.md. O leme continua girando normalmente
        mesmo ancorado.

        Args:
            dt: Delta de tempo em segundos desde o último tick.
            angulo_relativo_vento_atual: Ângulo relativo (0-180) entre o
                rumo do navio e a direção do vento.
            intensidade_vento_atual: Intensidade do vento em nós.
            vento_direcao_atual: Direção do vento (graus), usada pro
                empuxo constante.
        """
        if self.afundado:
            return

        fator_dano = (self.partes['vela'] / 100) * (self.partes['mastro'] / 100)
        fator_upgrade = 1.0 + self.upgrades.get('velocidade_giro', 0.0)

        (
            self.heading, self.velocidade, self.velocidade_lateral, dx, dy,
            self.eficiencia_vento_atual, self.fator_intensidade_vento_atual,
        ) = calcular_tick_fisica(
            self.heading, self.heading_alvo, self.velocidade, self.velocidade_lateral,
            self.giro_graus_seg, self.velocidade_max_base, self.slots_vela,
            self.peso_casco, self.area_casco, self.num_velas, self.ancorado,
            fator_dano, dt,
            angulo_relativo_vento_atual, intensidade_vento_atual, vento_direcao_atual,
            fator_vmax_extra=fator_upgrade,
        )

        self.x = clamp(self.x + dx, -MAPA_TAMANHO, MAPA_TAMANHO)
        self.y = clamp(self.y + dy, -MAPA_TAMANHO, MAPA_TAMANHO)

    def reparar(self, parte: str, tripulantes: int, dt: float) -> None:
        """Avança o reparo contínuo de uma parte do navio.

        A eficiência cai exponencialmente com o dano acumulado (fator REPARO_K).
        Se o porão tiver capacidade > 0, consome tábuas proporcionalmente ao HP
        restaurado; sem tábuas suficientes, o reparo é proporcionalmente reduzido.

        Args:
            parte:       Nome da parte a reparar.
            tripulantes: Número de tripulantes alocados ao reparo.
            dt:          Delta de tempo em segundos.
        """
        if tripulantes <= 0:
            return
        eficiencia = clamp(self.partes['casco'] / 100, 0.3, 1.0)
        dano_frac = (100 - self.partes[parte]) / 100
        fator_recuperacao = math.exp(-REPARO_K * dano_frac)
        taxa = (tripulantes * TAXA_REPARO_SEG * eficiencia
                * fator_recuperacao * self.reparo_mult * self.multiplicador_moral() * dt)

        if self.porao.capacidade > 0 and taxa > 1e-9:
            saude_potencial = min(taxa, 100.0 - self.partes[parte])
            tabuas_necessarias = saude_potencial * FATOR_TABUAS_POR_HP
            if tabuas_necessarias > 1e-9:
                disponivel = self.porao.total("tabuas")
                if disponivel < tabuas_necessarias:
                    fracao = disponivel / tabuas_necessarias if tabuas_necessarias > 0 else 0.0
                    taxa *= fracao
                    self.porao.consumir("tabuas", disponivel)
                else:
                    self.porao.consumir("tabuas", tabuas_necessarias)

        self.partes[parte] = clamp(self.partes[parte] + taxa, 0, 100)

    def atualizar_agua(self, tripulantes_bomba: int, dt: float) -> None:
        """Atualiza o nível de água no porão.

        A entrada de água é exponencial no dano do casco; as bombas removem
        linearmente. Água em 100% = navio afundado.

        Args:
            tripulantes_bomba: Tripulantes alocados às bombas.
            dt:                Delta de tempo em segundos.
        """
        entrada = calcular_entrada_agua(self.partes)
        saida = tripulantes_bomba * SAIDA_BOMBA_SEG * self.multiplicador_moral()
        self.agua = clamp(self.agua + (entrada - saida) * dt, 0, 100)
        if self.agua >= 100:
            self.afundado = True

    def parte_critica_destruida(self) -> bool:
        """Retorna True se alguma parte crítica chegou a 0 HP."""
        return any(self.partes[p] <= 0 for p in PARTES_CRITICAS)

    def moral_alvo(self) -> float:
        """Calcula a moral-alvo com base no estado atual do navio (0-100).

        Combina HP do casco, nível de água (invertido) e média das partes
        não-críticas, ponderados por MORAL_PESO_*.
        """
        hp_casco = self.partes['casco']
        fator_agua = clamp(100.0 - self.agua, 0.0, 100.0)
        outras = [v for k, v in self.partes.items() if k not in PARTES_CRITICAS]
        media_outras = sum(outras) / len(outras) if outras else 100.0
        alvo = (
            hp_casco * MORAL_PESO_CASCO
            + fator_agua * MORAL_PESO_AGUA
            + media_outras * MORAL_PESO_OUTRAS
        ) / 100.0
        return clamp(alvo, 0.0, 100.0)

    def _recursos_criticos_zerados_agora(self) -> bool:
        """True se pólvora, bolas ou tábuas estiverem em 0 no porão agora."""
        return any(
            self.porao.total(t) <= 0 for t in ('polvora', 'bolas', 'tabuas')
        )

    def atualizar_moral(self, dt: float) -> None:
        """Avança a moral para mais perto da moral-alvo pelo intervalo *dt*.

        Queda é proporcional a MORAL_QUEDA_TAXA_SEG; recuperação usa uma
        curva exponencial amortecida (igual a REPARO_K mas para a moral).

        Se pólvora, bolas ou tábuas zerarem (transição de >0 para 0), a
        moral trava temporariamente num teto baixo (MORAL_CRASH_RECURSOS_TETO)
        por MORAL_CRASH_RECURSOS_DURACAO_SEG segundos — um solavanco, não um
        travamento permanente nem um evento de um tick só.
        """
        zerado_agora = self._recursos_criticos_zerados_agora()
        if zerado_agora and self._recursos_criticos_zerados is False:
            self.moral_lock_restante = MORAL_CRASH_RECURSOS_DURACAO_SEG
            self.moral_atual = min(self.moral_atual, MORAL_CRASH_RECURSOS_TETO)
        self._recursos_criticos_zerados = zerado_agora

        alvo = self.moral_alvo()
        if self.moral_atual > alvo:
            self.moral_atual = max(alvo, self.moral_atual - MORAL_QUEDA_TAXA_SEG * dt)
        else:
            dano_moral = (100.0 - self.moral_atual) / 100.0
            fator = math.exp(-MORAL_K * dano_moral)
            self.moral_atual = min(
                alvo,
                self.moral_atual + MORAL_RECUP_BASE_SEG * fator * dt,
            )
        self.moral_atual = clamp(self.moral_atual, 0.0, 100.0)

        if self.moral_lock_restante > 0:
            self.moral_lock_restante = max(0.0, self.moral_lock_restante - dt)
            self.moral_atual = min(self.moral_atual, MORAL_CRASH_RECURSOS_TETO)

    def registrar_acerto_moral(self) -> None:
        """Adiciona um bonus de moral por acerto bem-sucedido."""
        self.moral_atual = clamp(self.moral_atual + MORAL_BONUS_ACERTO, 0.0, 100.0)

    def multiplicador_moral(self) -> float:
        """Retorna o multiplicador de eficiência (acerto / reparo / bomba) conforme a moral."""
        if self.moral_atual > MORAL_LIMIAR_ALTO:
            return MORAL_MULT_NORMAL
        if self.moral_atual > MORAL_LIMIAR_MEDIO:
            return MORAL_MULT_ABALADO
        if self.moral_atual > 0:
            return MORAL_MULT_COMBALIDO
        return MORAL_MULT_PANICO
