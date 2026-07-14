"""
ship.py – Classes Navio e Canhao de CLI PIRATES.

Define as entidades físicas do jogo: o canhão como arma individual
e o navio como entidade composta com física de movimento, reparo e água.
"""

import math

from ..constants import (
    PARTES, PARTES_CRITICAS,
    MAPA_TAMANHO, GIRO_GRAUS_SEG_PADRAO,
    ACEL_VEL_SEG, TAXA_REPARO_SEG, REPARO_K,
    AGUA_BASE, AGUA_K, SAIDA_BOMBA_SEG,
)
from .utils import clamp


class Canhao:
    """Representa um canhão individual em um dos lados do navio.

    Attributes:
        lado:        'estibordo' ou 'bombordo'.
        indice:      Posição 1-based na fileira do lado (E1, E2, …).
        hp:          Pontos de durabilidade (0-100). Zero = destruído.
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
        self.hp: float = 100.0
        self.tripulantes: int = 0
        self.dist_alvo: float | None = None
        self.mira_atual: float = 300.0
        self.proximo_tiro: float = 0.0

    @property
    def label(self) -> str:
        """Identificador legível, e.g. 'E1', 'B2'."""
        return f"{'E' if self.lado == 'estibordo' else 'B'}{self.indice}"

    def operacional(self) -> bool:
        """Retorna True se o canhão ainda tem HP e pode ser usado."""
        return self.hp > 0

    def armado(self) -> bool:
        """Retorna True se o canhão tem tripulação, HP e alvo definido."""
        return self.operacional() and self.tripulantes >= 1 and self.dist_alvo is not None


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


class Navio:
    """Representa um navio com física de movimento, dano e inundação.

    Attributes:
        nome:                Nome exibido no HUD.
        x, y:               Posição no mapa (unidades de jogo).
        heading:            Rumo atual em graus (Norte = 0, horário).
        heading_alvo:       Rumo para o qual o leme aponta.
        velocidade:         Velocidade atual (unidades/segundo).
        nivel_vela:         Nível de vela configurado (0-3).
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
    ) -> None:
        self.nome = nome
        self.x = x
        self.y = y
        self.heading = heading % 360
        self.heading_alvo = heading % 360
        self.velocidade: float = 0.0
        self.nivel_vela: int = 1
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

    def vivo(self) -> bool:
        """Retorna True enquanto o navio não afundou."""
        return not self.afundado

    def taxa_giro(self) -> float:
        """Taxa de giro efetiva, reduzida proporcionalmente ao dano da roda do leme."""
        return self.giro_graus_seg * max(0.0, self.partes['roda'] / 100)

    def velocidade_maxima(self) -> float:
        """Velocidade máxima alcançável com o nível de vela e dano atuais."""
        fator_vela = self.nivel_vela / 3
        fator_dano = (self.partes['vela'] / 100) * (self.partes['mastro'] / 100)
        return self.velocidade_max_base * fator_vela * fator_dano

    def atualizar_movimento(self, dt: float) -> None:
        """Aplica física de giro e propulsão para o intervalo de tempo *dt*.

        Args:
            dt: Delta de tempo em segundos desde o último tick.
        """
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

    def reparar(self, parte: str, tripulantes: int, dt: float) -> None:
        """Avança o reparo contínuo de uma parte do navio.

        A eficiência cai exponencialmente com o dano acumulado (fator REPARO_K).

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
                * fator_recuperacao * self.reparo_mult * dt)
        self.partes[parte] = clamp(self.partes[parte] + taxa, 0, 100)

    def atualizar_agua(self, tripulantes_bomba: int, dt: float) -> None:
        """Atualiza o nível de água no porão.

        A entrada de água é exponencial no dano do casco; as bombas removem
        linearmente. Água em 100% = navio afundado.

        Args:
            tripulantes_bomba: Tripulantes alocados às bombas.
            dt:                Delta de tempo em segundos.
        """
        entrada = 0.0
        for p in PARTES_CRITICAS:
            dano_frac = (100 - self.partes[p]) / 100
            entrada += AGUA_BASE * (math.exp(AGUA_K * dano_frac) - 1)
        saida = tripulantes_bomba * SAIDA_BOMBA_SEG
        self.agua = clamp(self.agua + (entrada - saida) * dt, 0, 100)
        if self.agua >= 100:
            self.afundado = True

    def parte_critica_destruida(self) -> bool:
        """Retorna True se alguma parte crítica chegou a 0 HP."""
        return any(self.partes[p] <= 0 for p in PARTES_CRITICAS)
