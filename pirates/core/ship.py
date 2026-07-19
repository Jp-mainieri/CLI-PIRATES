"""
ship.py – Classes Navio e Canhao de CLI PIRATES.

Define as entidades físicas do jogo: o canhão como arma individual
e o navio como entidade composta com física de movimento, reparo e água.
"""

import math

from ..constants import (
    PARTES, PARTES_CRITICAS,
    MAPA_TAMANHO, GIRO_GRAUS_SEG_PADRAO,
    ACEL_VEL_SEG, TAXA_REPARO_SEG, REPARO_K, FATOR_TABUAS_POR_HP,
    AGUA_BASE, AGUA_K, SAIDA_BOMBA_SEG,
    MORAL_PESO_CASCO, MORAL_PESO_AGUA, MORAL_PESO_OUTRAS,
    MORAL_QUEDA_TAXA_SEG, MORAL_K, MORAL_RECUP_BASE_SEG, MORAL_BONUS_ACERTO,
    MORAL_LIMIAR_ALTO, MORAL_LIMIAR_MEDIO,
    MORAL_MULT_NORMAL, MORAL_MULT_ABALADO, MORAL_MULT_COMBALIDO, MORAL_MULT_PANICO,
)
from .utils import clamp
from .porao import Porao, estoque_inicial_jogador  # noqa: F401 (re-exportado)


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
        porao_capacidade: int = 0,
        bonus_fixo_vela: float = 0.0,
        bonus_curva_vela: float = 0.0,
        eficiencia_vento_tabela: dict | None = None,
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
        self.moral_atual: float = 100.0
        self.porao: Porao = Porao(porao_capacidade)
        self.upgrades: dict[str, float] = {}
        self.upgrade_niveis: dict[str, int] = {}
        self.itens_topo: dict[str, bool] = {}
        self.bonus_fixo_vela = bonus_fixo_vela
        self.bonus_curva_vela = bonus_curva_vela
        self.eficiencia_vento_tabela = eficiencia_vento_tabela or {
            "zona_morta": 1.0, "bolina": 1.0, "traves": 1.0, "popa": 1.0,
        }
        self.eficiencia_vento_atual: float = 1.0
        self.fator_intensidade_vento_atual: float = 1.0

    def vivo(self) -> bool:
        """Retorna True enquanto o navio não afundou."""
        return not self.afundado

    def taxa_giro(self) -> float:
        """Taxa de giro efetiva: giro_base × bônus de curva da vela, reduzida
        proporcionalmente ao dano da roda do leme. Não depende do vento
        (doc08_vento.md seção 3)."""
        base = self.giro_graus_seg * (1.0 + self.bonus_curva_vela)
        return base * max(0.0, self.partes['roda'] / 100)

    def velocidade_maxima(self) -> float:
        """Velocidade máxima alcançável com o nível de vela, dano e vento atuais.
        Aplica bônus de upgrade 'velocidade_giro' e o bônus fixo de vela, além
        da eficiência de vento do ângulo relativo atual (doc08_vento.md)."""
        fator_vela = self.nivel_vela / 3
        fator_dano = (self.partes['vela'] / 100) * (self.partes['mastro'] / 100)
        base = self.velocidade_max_base * (1.0 + self.bonus_fixo_vela)
        base *= self.eficiencia_vento_atual
        base *= self.fator_intensidade_vento_atual
        base *= (1.0 + self.upgrades.get('velocidade_giro', 0.0))
        return base * fator_vela * fator_dano

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
        self, dt: float, eficiencia_vento: float = 1.0,
        fator_intensidade_vento: float = 1.0,
    ) -> None:
        """Aplica física de giro e propulsão para o intervalo de tempo *dt*.

        Args:
            dt: Delta de tempo em segundos desde o último tick.
            eficiencia_vento: Eficiência de vento (0.0+) pro ângulo relativo
                atual do navio, calculada externamente (ver pirates/core/vento.py).
            fator_intensidade_vento: Multiplicador de teto de velocidade pela
                curva de intensidade do vento (0.5 a 1.3, suave), calculado
                externamente. Não afeta aceleração.
        """
        if self.afundado:
            return

        self.eficiencia_vento_atual = eficiencia_vento
        self.fator_intensidade_vento_atual = fator_intensidade_vento

        diff = (self.heading_alvo - self.heading + 540) % 360 - 180
        giro_max = self.taxa_giro() * dt
        if abs(diff) <= giro_max:
            self.heading = self.heading_alvo
        else:
            self.heading = (self.heading + (giro_max if diff > 0 else -giro_max)) % 360

        vmax = self.velocidade_maxima()
        acel = ACEL_VEL_SEG * dt * eficiencia_vento
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

    def atualizar_moral(self, dt: float) -> None:
        """Avança a moral para mais perto da moral-alvo pelo intervalo *dt*.

        Queda é proporcional a MORAL_QUEDA_TAXA_SEG; recuperação usa uma
        curva exponencial amortecida (igual a REPARO_K mas para a moral).
        """
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
