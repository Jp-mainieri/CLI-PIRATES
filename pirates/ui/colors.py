"""
colors.py – Helpers de atributos de cor para curses em CLI PIRATES.

Cada função recebe o estado atual do jogo e retorna o atributo curses
correto (inteiro). Quando cores estão desativadas retornam 0 (padrão).
"""

try:
    import curses as _curses
except ImportError:
    _curses = None  # type: ignore[assignment]

from ..constants import (
    COR_VERDE, COR_AMARELO, COR_VERMELHO,
    COR_JOGADOR, COR_INIMIGO, COR_MAR,
    AGUA_CRITICA_LIMIAR,
)
from ..core.utils import nivel_cor


def cor_valor(estado, valor: float, pior_se_alto: bool = False) -> int:
    """Atributo curses para colorir uma métrica percentual (HP, água, etc.).

    Args:
        estado:       Estado atual do jogo.
        valor:        Valor percentual (0-100).
        pior_se_alto: Se True, valores altos são piores (água no porão).

    Returns:
        Atributo curses ou 0 se cores desativadas.
    """
    if not estado.cores_ativo or _curses is None:
        return 0
    mapa = {'verde': COR_VERDE, 'amarelo': COR_AMARELO, 'vermelho': COR_VERMELHO}
    return _curses.color_pair(mapa[nivel_cor(valor, pior_se_alto)])


def cor_log(estado, linha: str) -> int:
    """Atributo curses para colorir uma linha do log de combate.

    Args:
        estado: Estado atual do jogo.
        linha:  Texto da linha de log.

    Returns:
        Atributo curses ou 0.
    """
    if not estado.cores_ativo or _curses is None:
        return 0
    if linha.startswith("[ACERTO]"):
        if "acerta Seu Navio" in linha:
            return _curses.color_pair(COR_VERMELHO)
        return _curses.color_pair(COR_VERDE)
    if linha.startswith("Tripulacao realocada"):
        return _curses.color_pair(COR_AMARELO)
    if "moral" in linha.lower() and ("perde" in linha.lower() or "fuga" in linha.lower()):
        return _curses.color_pair(COR_AMARELO)
    return 0


def cor_mar(estado) -> int:
    """Atributo curses para o fundo azul do mar (mapa e visão do capitão)."""
    if not estado.cores_ativo or _curses is None:
        return 0
    return _curses.color_pair(COR_MAR)


def cor_navio(estado, e_jogador: bool) -> int:
    """Atributo curses para o ícone de navio no mapa (ciano=jogador, magenta=inimigo)."""
    if not estado.cores_ativo or _curses is None:
        return 0
    return _curses.color_pair(COR_JOGADOR if e_jogador else COR_INIMIGO)


def cor_norte(estado) -> int:
    """Atributo curses para o marcador 'N' da bússola (vermelho)."""
    if not estado.cores_ativo or _curses is None:
        return 0
    return _curses.color_pair(COR_VERMELHO)


def cor_tripulacao_livre(estado) -> int:
    """Atributo curses para o contador de tripulação livre no cabeçalho.

    Vermelho+negrito quando não há ninguém disponível.
    """
    if _curses is None:
        return 0
    if not estado.cores_ativo:
        return _curses.A_BOLD
    if estado.crew_livre() <= 0:
        return _curses.color_pair(COR_VERMELHO) | _curses.A_BOLD
    return _curses.A_BOLD


def cor_tipo_navio(estado) -> int:
    """Cor do nome do navio no cabeçalho: verde (Chalupa), amarelo (Bergantim), vermelho (Galeão)."""
    if _curses is None:
        return 0
    if estado.cores_ativo:
        mapa = {'facil': COR_VERDE, 'normal': COR_AMARELO, 'dificil': COR_VERMELHO}
        cor = mapa.get(estado.tipo_navio, COR_JOGADOR)
        return _curses.color_pair(cor) | _curses.A_BOLD
    return _curses.A_BOLD


def cor_header(estado) -> int:
    """Atributo curses para o cabeçalho principal.

    Vermelho+negrito quando a água está acima do limiar crítico.
    """
    if _curses is None:
        return 0
    if not estado.cores_ativo:
        return _curses.A_BOLD
    if estado.jogador.agua > AGUA_CRITICA_LIMIAR:
        return _curses.color_pair(COR_VERMELHO) | _curses.A_BOLD
    return _curses.A_BOLD


def cor_cooldown(estado, pronto: bool) -> int:
    """Atributo curses para a barra de recarga de um canhão."""
    if not estado.cores_ativo or _curses is None:
        return 0
    return _curses.color_pair(COR_VERDE) if pronto else _curses.color_pair(COR_VERMELHO)


def cor_tarefa(estado, tarefa: str) -> int:
    """Atributo curses para colorir a tarefa de um tripulante na lista."""
    if not estado.cores_ativo or _curses is None:
        return 0
    mapa = {"canhao": COR_INIMIGO, "reparo": COR_VERDE, "bomba": COR_JOGADOR}
    if tarefa in mapa:
        return _curses.color_pair(mapa[tarefa])
    return 0
