"""tripulacao.py – Tripulantes como indivíduos, com trânsito entre postos.

O jogo aloca tripulação por CONTAGEM (`Canhao.tripulantes`, `estado.crew_bomba`,
`estado.crew_reparo`). Essa camada continua sendo a fonte de verdade da
*alocação*. Este módulo acrescenta a camada de *efetividade*: quem é cada
tripulante, de onde ele veio e quanto falta para começar a trabalhar no posto
novo.

As duas camadas são casadas por `reconciliar`, que compara o roster inteiro com
as contagens desejadas e move indivíduos para fechar a diferença. Como a
reconciliação é total (nunca incremental), não existe drift possível entre elas:
basta chamá-la depois de qualquer mudança de contagem, e ela é idempotente, o
que permite rodá-la a cada tick sem reiniciar timer de ninguém.

O módulo é puro — não conhece `Estado` — para servir aos dois navios (jogador e
inimigo) e para ser testável isoladamente.
"""

from ..constants import (
    TRANSITO_CANHAO_MESMO_BORDO,
    TRANSITO_CANHAO_BORDO_OPOSTO,
    TRANSITO_TAREFA_DIFERENTE,
    TRANSITO_REPARO_ENTRE_PARTES,
)

# Um Posto é uma tupla imutável usada como chave, ou None para 'ocioso':
#   ('canhao', lado, indice)   lado ∈ {'estibordo', 'bombordo'}
#   ('reparo', parte)          parte ∈ PARTES
#   ('bomba',)
Posto = tuple | None


def posto_canhao(canhao) -> tuple:
    """Posto correspondente a um objeto `Canhao`."""
    return ('canhao', canhao.lado, canhao.indice)


def posto_reparo(parte: str) -> tuple:
    """Posto de reparo de uma parte do navio."""
    return ('reparo', parte)


POSTO_BOMBA = ('bomba',)


def descrever_posto(posto: Posto) -> str:
    """Descrição curta de *posto* para log e HUD."""
    if posto is None:
        return "conves"
    if posto[0] == 'canhao':
        return f"canhao {'E' if posto[1] == 'estibordo' else 'B'}{posto[2]}"
    if posto[0] == 'reparo':
        return f"reparo {posto[1]}"
    return "bomba"


def descrever_frente(posto: Posto) -> str:
    """Nome da frente de trabalho de *posto*, não do posto em si.

    Um canhão pertence à bordada do seu bordo, e é a bordada inteira que a
    realocação automática protege (ver `mesma_tarefa`) — então as mensagens
    precisam falar em 'canhoes de estibordo', não em 'canhao E2'.
    """
    if posto is None:
        return "conves"
    if posto[0] == 'canhao':
        return f"canhoes de {posto[1]}"
    if posto[0] == 'reparo':
        return f"reparo de {posto[1]}"
    return "bomba"


def custo_transito(origem: Posto, destino: Posto) -> float:
    """Segundos que um tripulante leva para ir de *origem* até *destino*.

    *origem* é o último posto onde o tripulante EFETIVAMENTE trabalhou — nunca
    o estado 'ocioso'. É isso que impede o jogador de estacionar tripulantes no
    convés para depois alocá-los no bordo oposto de graça.

    `origem is None` significa tripulante recém-contratado, que nunca trabalhou:
    assumir o primeiro posto é grátis.
    """
    if destino is None or origem == destino or origem is None:
        return 0.0

    origem_canhao = origem[0] == 'canhao'
    destino_canhao = destino[0] == 'canhao'

    if origem_canhao and destino_canhao:
        if origem[1] == destino[1]:
            return TRANSITO_CANHAO_MESMO_BORDO
        return TRANSITO_CANHAO_BORDO_OPOSTO

    if origem[0] == destino[0]:
        # Mesma tarefa, estação diferente: só acontece com reparo (a bomba é
        # posto único, e portanto já caiu no `origem == destino` acima).
        return TRANSITO_REPARO_ENTRE_PARTES

    return TRANSITO_TAREFA_DIFERENTE


def mesma_tarefa(a: Posto, b: Posto) -> bool:
    """True se *a* e *b* são a mesma frente de trabalho.

    Canhões contam como a mesma frente quando estão no mesmo bordo — uma
    bordada é uma tarefa só, servida por vários canhões. Reparo, quando é a
    mesma parte. A bomba, sempre consigo mesma.

    Serve à realocação automática (`state._liberar_tripulantes`): quem já está
    na frente de trabalho pedida não pode ser roubado para ela, senão atender
    ao pedido não a fortalece — só embaralha as mesmas pessoas.

    O convés (None) nunca é a mesma tarefa que nada: tripulante ocioso é
    sempre elegível.
    """
    if a is None or b is None:
        return False
    if a[0] != b[0]:
        return False
    if a[0] == 'canhao':
        return a[1] == b[1]      # mesmo bordo
    if a[0] == 'reparo':
        return a[1] == b[1]      # mesma parte
    return True                  # bomba é posto único


class Tripulante:
    """Um tripulante individual e seu estado de trânsito.

    Attributes:
        id:                Rótulo estável ('T1', 'I3', ...).
        posto:             Posto ao qual está alocado agora (None = ocioso).
        ultimo_posto:      Último posto onde efetivamente trabalhou. Base do
                           cálculo de custo; preservado ao ficar ocioso.
        transito_restante: Segundos até começar a trabalhar. 0.0 = trabalhando.
    """

    def __init__(self, id: str) -> None:
        self.id: str = id
        self.posto: Posto = None
        self.ultimo_posto: Posto = None
        self.transito_restante: float = 0.0

    def efetivo(self) -> bool:
        """True se está num posto e já começou a trabalhar."""
        return self.posto is not None and self.transito_restante <= 0.0

    def em_transito(self) -> bool:
        """True se está alocado mas ainda atravessando o convés."""
        return self.posto is not None and self.transito_restante > 0.0

    def __repr__(self) -> str:  # pragma: no cover - only for debugging
        return (
            f"Tripulante({self.id}, posto={self.posto}, "
            f"ultimo={self.ultimo_posto}, transito={self.transito_restante:.1f})"
        )


class Tripulacao:
    """Roster de tripulantes de um navio."""

    def __init__(self, ids: list[str] | None = None) -> None:
        self.membros: list[Tripulante] = []
        if ids:
            self.redimensionar(ids)

    # -- ciclo de vida ------------------------------------------------------

    def redimensionar(self, ids: list[str]) -> None:
        """Ajusta o roster para *ids*, preservando quem permanece.

        Quem fica mantém posto, último posto e trânsito. Quem entra é gente
        contratada agora: entra ocioso com `ultimo_posto=None`, e por isso
        assume o primeiro posto sem pagar trânsito.
        """
        por_id = {t.id: t for t in self.membros}
        self.membros = [por_id.get(i) or Tripulante(i) for i in ids]

    def atualizar(self, dt: float) -> None:
        """Avança *dt* segundos de trânsito.

        Ao vencer o trânsito, o posto atual vira o `ultimo_posto` — é neste
        instante que o tripulante 'trabalhou' de fato naquele posto, e é o que
        faz o custo seguinte ser medido a partir dele.
        """
        for t in self.membros:
            if t.transito_restante > 0.0:
                t.transito_restante = max(0.0, t.transito_restante - dt)
                if t.transito_restante <= 0.0:
                    t.ultimo_posto = t.posto

    # -- movimentação -------------------------------------------------------

    def alocar(self, trip: Tripulante, novo: Posto) -> None:
        """Move *trip* para *novo*, cobrando o trânsito devido."""
        if trip.posto == novo:
            return
        trip.posto = novo
        trip.transito_restante = custo_transito(trip.ultimo_posto, novo)
        if trip.transito_restante <= 0.0:
            trip.ultimo_posto = novo

    def liberar(self, trip: Tripulante) -> None:
        """Devolve *trip* ao convés, preservando o último posto trabalhado."""
        trip.posto = None
        trip.transito_restante = 0.0

    # -- consultas ----------------------------------------------------------

    def efetivos_por_posto(self) -> dict[Posto, int]:
        """Contagem de tripulantes já trabalhando, por posto."""
        contagem: dict[Posto, int] = {}
        for t in self.membros:
            if t.efetivo():
                contagem[t.posto] = contagem.get(t.posto, 0) + 1
        return contagem

    def alocados_por_posto(self) -> dict[Posto, int]:
        """Contagem de tripulantes alocados (trabalhando ou em trânsito)."""
        contagem: dict[Posto, int] = {}
        for t in self.membros:
            if t.posto is not None:
                contagem[t.posto] = contagem.get(t.posto, 0) + 1
        return contagem

    def em_transito(self) -> list[Tripulante]:
        """Tripulantes que ainda estão atravessando o convés."""
        return [t for t in self.membros if t.em_transito()]

    def transito_restante_do_posto(self, posto: Posto) -> float:
        """Menor trânsito restante entre quem está indo para *posto*.

        Retorna 0.0 se ninguém está a caminho.
        """
        tempos = [
            t.transito_restante for t in self.membros
            if t.posto == posto and t.em_transito()
        ]
        return min(tempos) if tempos else 0.0


# ---------------------------------------------------------------------------
# Reconciliação
# ---------------------------------------------------------------------------

def _ordem_posto(posto: Posto) -> tuple:
    """Chave de ordenação determinística para postos."""
    return tuple(str(p) for p in posto)


def reconciliar(tripulacao: Tripulacao, desejado: dict[Posto, int]) -> None:
    """Move indivíduos até o roster bater com as contagens de *desejado*.

    *desejado* mapeia posto → número de tripulantes alocados. Postos ausentes
    valem zero.

    A operação é idempotente: se o roster já corresponde a *desejado*, ninguém
    é tocado e nenhum timer reinicia. É isso que permite chamá-la a cada tick.
    """
    atual = tripulacao.alocados_por_posto()

    # 1) Devolve ao convés o excedente de cada posto. Sai primeiro quem ainda
    #    está em trânsito: é quem tem menos a perder, já que sequer começou a
    #    trabalhar (e assim não expulsamos quem já está produzindo).
    for posto in sorted(atual, key=_ordem_posto):
        excedente = atual[posto] - desejado.get(posto, 0)
        if excedente <= 0:
            continue
        ocupantes = [t for t in tripulacao.membros if t.posto == posto]
        ocupantes.sort(key=lambda t: (not t.em_transito(), t.id))
        for t in ocupantes[:excedente]:
            tripulacao.liberar(t)

    # 2) Preenche os déficits com quem está no convés, escolhendo sempre o
    #    tripulante mais barato para aquele posto.
    for posto in sorted(desejado, key=_ordem_posto):
        if posto is None:
            continue
        faltam = desejado[posto] - sum(
            1 for t in tripulacao.membros if t.posto == posto
        )
        for _ in range(max(0, faltam)):
            pool = [t for t in tripulacao.membros if t.posto is None]
            if not pool:
                return
            melhor = min(
                pool, key=lambda t: (custo_transito(t.ultimo_posto, posto), t.id)
            )
            tripulacao.alocar(melhor, posto)


# ---------------------------------------------------------------------------
# Ponte com as contagens do jogo
# ---------------------------------------------------------------------------

def desejado_de_contagens(navio, crew_reparo: dict[str, int], crew_bomba: int) -> dict[Posto, int]:
    """Traduz as contagens de alocação de um navio num dict de postos."""
    desejado: dict[Posto, int] = {}
    for lado in ('estibordo', 'bombordo'):
        for c in navio.canhoes[lado]:
            if c.tripulantes > 0:
                desejado[posto_canhao(c)] = c.tripulantes
    for parte, n in crew_reparo.items():
        if n > 0:
            desejado[posto_reparo(parte)] = n
    if crew_bomba > 0:
        desejado[POSTO_BOMBA] = crew_bomba
    return desejado


def aplicar_efetivos(navio, tripulacao: Tripulacao) -> None:
    """Escreve `Canhao.efetivos` a partir do roster.

    `Canhao.tripulantes` continua sendo a alocação; `efetivos` é quem já está
    de fato ao canhão. É a diferença entre os dois que congela a recarga
    enquanto a equipe atravessa o convés.
    """
    efetivos = tripulacao.efetivos_por_posto()
    for lado in ('estibordo', 'bombordo'):
        for c in navio.canhoes[lado]:
            c.efetivos = efetivos.get(posto_canhao(c), 0)


def efetivos_reparo(tripulacao: Tripulacao) -> dict[str, int]:
    """Tripulantes já trabalhando em cada parte, por nome de parte."""
    efetivos = tripulacao.efetivos_por_posto()
    return {
        posto[1]: n for posto, n in efetivos.items()
        if posto is not None and posto[0] == 'reparo'
    }


def efetivos_bomba(tripulacao: Tripulacao) -> int:
    """Tripulantes já trabalhando nas bombas."""
    return tripulacao.efetivos_por_posto().get(POSTO_BOMBA, 0)
