"""
utils.py – Funções utilitárias puras de CLI PIRATES.

Todas as funções aqui são sem efeitos colaterais e não dependem de
estado de jogo nem de curses. Podem ser testadas de forma isolada.
"""

from ..constants import DIRECOES, ARROWS_ASCII, ARROWS_UNICODE


def clamp(v: float, lo: float, hi: float) -> float:
    """Restringe *v* ao intervalo [lo, hi].

    Args:
        v:  Valor a ser limitado.
        lo: Limite inferior.
        hi: Limite superior.

    Returns:
        O valor mais próximo de *v* dentro de [lo, hi].
    """
    return max(lo, min(hi, v))


def direcao_para_heading(h: float) -> str:
    """Converte um rumo em graus para o rótulo de 8 pontos mais próximo.

    Args:
        h: Rumo em graus (0-360, Norte = 0).

    Returns:
        String de 2 caracteres, e.g. 'N ', 'NE', 'SW'.
    """
    idx = int(((h % 360) + 22.5) // 45) % 8
    return DIRECOES[idx]


def seta_unicode_para_heading(h: float) -> str:
    """Retorna a seta Unicode (↑ ↗ → …) correspondente ao rumo *h*.

    Args:
        h: Rumo em graus.

    Returns:
        Caractere Unicode de seta direcional.
    """
    idx = int(((h % 360) + 22.5) // 45) % 8
    return ARROWS_UNICODE[idx]


def seta_ascii_para_heading(h: float) -> str:
    """Retorna a seta ASCII (^ / > \\ v …) correspondente ao rumo *h*.

    Args:
        h: Rumo em graus.

    Returns:
        Caractere ASCII de seta direcional.
    """
    idx = int(((h % 360) + 22.5) // 45) % 8
    return ARROWS_ASCII[idx]


def barra(valor: float, largura: int = 6) -> str:
    """Gera uma barra de progresso em texto simples.

    Args:
        valor:   Valor percentual (0-100).
        largura: Número de caracteres da barra.

    Returns:
        String com '#' para a parte preenchida e '-' para o restante.
    """
    cheio = int(clamp(valor, 0, 100) / 100 * largura)
    return '#' * cheio + '-' * (largura - cheio)


def nivel_cor(valor: float, pior_se_alto: bool = False) -> str:
    """Classifica um valor percentual em um nível de cor semântico.

    Função pura — não depende de curses nem de estado de jogo.

    Args:
        valor:        Valor percentual (0-100).
        pior_se_alto: Se True, valores altos são piores (água no porão).

    Returns:
        'verde', 'amarelo' ou 'vermelho'.
    """
    v = (100 - valor) if pior_se_alto else valor
    if v > 60:
        return 'verde'
    if v > 25:
        return 'amarelo'
    return 'vermelho'
