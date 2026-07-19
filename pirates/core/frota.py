"""frota.py – Navios possuídos pelo capitão (frota), além do ativo."""

from dataclasses import dataclass, field

from .ship import Navio, criar_canhoes
from .porao import Porao, estoque_inicial_jogador


@dataclass
class NavioPossuido:
    """Um navio da frota do capitão, ancorado num porto (ou o ativo, em jogo).

    Attributes:
        nome:           Nome único escolhido pelo jogador.
        navio:          Instância completa de Navio (porão, dano, upgrades).
        tipo:           Chave do tipo ('chalupa'/'brigantim'/'galeao').
        porto_ancorado: Índice do porto onde está parado (None se ativo).
    """
    nome: str
    navio: Navio
    tipo: str
    porto_ancorado: int | None = None


class Frota:
    """Coleção de todos os navios que o capitão possui."""

    def __init__(self) -> None:
        self.navios: list[NavioPossuido] = []
        self.indice_ativo: int = -1

    def ativo(self) -> NavioPossuido | None:
        if 0 <= self.indice_ativo < len(self.navios):
            return self.navios[self.indice_ativo]
        return None

    def navios_no_porto(self, porto_id: int) -> list[NavioPossuido]:
        return [n for n in self.navios if n.porto_ancorado == porto_id]

    def adicionar(self, nome: str, navio: Navio, tipo: str, porto_id: int | None) -> None:
        self.navios.append(
            NavioPossuido(nome=nome, navio=navio, tipo=tipo, porto_ancorado=porto_id)
        )

    def trocar_ativo(self, indice_na_lista: int, porto_atual_id: int) -> bool:
        """Troca o navio ativo por outro da frota, só se ambos estiverem
        no mesmo porto. O antigo ativo fica ancorado; o escolhido sai.

        Returns:
            False se o índice for inválido ou o navio não estiver no porto certo.
        """
        if not (0 <= indice_na_lista < len(self.navios)):
            return False
        alvo = self.navios[indice_na_lista]
        if alvo.porto_ancorado != porto_atual_id:
            return False
        atual = self.ativo()
        if atual is not None:
            atual.porto_ancorado = porto_atual_id
        alvo.porto_ancorado = None
        self.indice_ativo = indice_na_lista
        return True


def comprar_navio(
    frota: Frota, tipo: str, nome: str, porto_id: int, preco: float
) -> bool:
    """Cria um navio novo do tipo dado e adiciona à frota no porto.

    Não valida se o jogador tem ouro suficiente — isso é responsabilidade
    de quem chama (Tier 3b). Retorna False se o tipo for inválido.
    """
    from ..constants import NAVIO_TIPOS
    if tipo not in NAVIO_TIPOS:
        return False
    params = NAVIO_TIPOS[tipo]
    navio = Navio(
        nome, x=0.0, y=0.0, heading=0.0,
        velocidade_max_base=params["velocidade_max_base"],
        giro_graus_seg=params["giro_graus_seg"],
        reparo_mult=params["reparo_mult"],
        porao_capacidade=params["porao_capacidade"],
    )
    navio.tipo_nome = params["navio"]
    navio.num_velas = params["num_velas"]
    navio.canhoes = criar_canhoes(params["canhoes_lado"])
    navio.porao = estoque_inicial_jogador(params["porao_capacidade"])
    frota.adicionar(nome, navio, tipo, porto_id)
    return True


def renomear_navio(frota: Frota, indice: int, novo_nome: str) -> bool:
    """Renomeia o navio no índice dado. Retorna False se índice inválido."""
    if not (0 <= indice < len(frota.navios)):
        return False
    frota.navios[indice].nome = novo_nome
    return True
