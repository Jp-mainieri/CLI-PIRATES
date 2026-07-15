"""
hotkeys.py – Atalhos de teclado em tempo real de CLI PIRATES.

Hotkeys funcionam apenas quando o prompt está vazio e a opção está ligada
em Ajustes. O sistema de "foco" mantém qual canhão ou parte de reparo
está selecionado para ajuste rápido via teclas.
"""

from ..constants import PARTES, HOTKEY_PASSO_MIRA, HOTKEY_PASSO_LEME
from ..core.utils import clamp
from ..core.state import Estado, tentar_assumir_tripulacao
from .commands import _definir_trip_canhao, _armar_canhao_com_padrao


def _ciclar_canhao(estado: Estado, lado: str) -> None:
    """Seleciona o próximo canhão do *lado* como foco das hotkeys."""
    lista = estado.jogador.canhoes[lado]
    if estado.foco and estado.foco[0] == "canhao" and estado.foco[1] == lado:
        novo_idx = (estado.foco[2] + 1) % len(lista)
    else:
        novo_idx = 0
    estado.foco = ("canhao", lado, novo_idx)
    c = lista[novo_idx]
    mira_txt = (f"{c.dist_alvo:.0f}m" if c.dist_alvo is not None
                else f"pendente {c.mira_atual:.0f}m")
    estado.log.append(f"Selecionado canhao {c.label} - trip:{c.tripulantes} mira:{mira_txt}")


def _ajustar_mira(estado: Estado, delta: float) -> None:
    """Incrementa ou decrementa a mira do canhão em foco."""
    if not (estado.foco and estado.foco[0] == "canhao"):
        estado.log.append("Selecione um canhao primeiro (tecla j ou l)")
        return
    _, lado, idx = estado.foco
    c = estado.jogador.canhoes[lado][idx]
    novo = clamp(c.mira_atual + delta, 50, 900)
    c.mira_atual = novo
    if c.dist_alvo is not None:
        c.dist_alvo = novo
    estado.log.append(f"Canhao {c.label} mira: {novo:.0f}m")


def _ajustar_bomba(estado: Estado, delta: int) -> None:
    """Adiciona (+1) ou remove (-1) um tripulante das bombas."""
    if delta > 0:
        atual = estado.crew_bomba
        final, _ = tentar_assumir_tripulacao(estado, atual + 1, atual)
        estado.crew_bomba = final
        if final <= atual:
            estado.log.append("Nao ha tripulacao disponivel para a bomba")
            return
    else:
        estado.crew_bomba = max(0, estado.crew_bomba - 1)
    estado.log.append(f"Bomba: {estado.crew_bomba} tripulante(s)")


def _ajustar_reparo(estado: Estado, delta: int) -> None:
    """Adiciona ou remove um tripulante da parte de reparo em foco."""
    if not (estado.foco and estado.foco[0] == "reparo"):
        estado.log.append("Selecione uma parte primeiro (tecla e)")
        return
    parte = PARTES[estado.foco[1]]
    atual = estado.crew_reparo.get(parte, 0)
    if delta > 0:
        final, _ = tentar_assumir_tripulacao(
            estado, atual + 1, atual, ignorar_parte=parte
        )
        estado.crew_reparo[parte] = final
        if final <= atual:
            estado.log.append(f"Nao ha tripulacao disponivel para reparo de {parte}")
            return
    else:
        estado.crew_reparo[parte] = max(0, atual - 1)
    estado.log.append(f"Reparo {parte}: {estado.crew_reparo[parte]} tripulante(s)")


def _ciclar_reparo(estado: Estado) -> None:
    """Avança o foco para a próxima parte de reparo (circular)."""
    if estado.foco and estado.foco[0] == "reparo":
        novo_idx = (estado.foco[1] + 1) % len(PARTES)
    else:
        novo_idx = 0
    estado.foco = ("reparo", novo_idx)
    parte = PARTES[novo_idx]
    n_atual = estado.crew_reparo.get(parte, 0)
    estado.log.append(f"Selecionado reparo: {parte} - tripulantes atuais: {n_atual}")


def _alternar_foco(estado: Estado) -> None:
    """ESPAÇO: alterna o canhão em foco (atirar/parar) ou +reparo."""
    if not estado.foco:
        estado.log.append("Nada selecionado (use j/l p/ canhao, e p/ reparo)")
        return
    tipo = estado.foco[0]

    if tipo == "canhao":
        _, lado, idx = estado.foco
        c = estado.jogador.canhoes[lado][idx]
        if c.dist_alvo is not None:
            c.dist_alvo = None
            c.tripulantes = 0
            estado.log.append(
                f"Canhao {c.label} parou de atirar e liberou a tripulacao"
            )
        else:
            _armar_canhao_com_padrao(estado, c, c.mira_atual)

    elif tipo == "reparo":
        _ajustar_reparo(estado, +1)


def _descrever_foco(estado: Estado) -> str:
    """Gera uma descrição textual do item em foco para o HUD de hotkeys."""
    if not estado.foco:
        return "nenhum"
    if estado.foco[0] == "canhao":
        _, lado, idx = estado.foco
        c = estado.jogador.canhoes[lado][idx]
        mira = (f"{c.dist_alvo:.0f}m" if c.dist_alvo is not None
                else f"pendente {c.mira_atual:.0f}m")
        status = "ATIRANDO" if c.dist_alvo is not None else "parado"
        return f"canhao {c.label} trip:{c.tripulantes} mira:{mira} [{status}]"
    if estado.foco[0] == "reparo":
        parte = PARTES[estado.foco[1]]
        n = estado.crew_reparo.get(parte, 0)
        status = "REPARANDO" if n > 0 else "parado"
        return f"reparo {parte} trip:{n} [{status}]"
    return "?"


def processar_hotkey(ch: int, estado: Estado) -> bool:
    """Processa uma tecla pressionada como hotkey de jogo.

    Mapeamento (maiúsculas e minúsculas equivalentes):
        ESPAÇO  – alterna o item em foco
        A / D   – leme ±HOTKEY_PASSO_LEME graus
        W / S   – vela ++ / --
        J / L   – seleciona canhão bombordo / estibordo
        I / K   – mira ±HOTKEY_PASSO_MIRA metros
        U / H   – bomba +1 / -1 tripulante
        E       – cicla partes de reparo
        R       – reparo -1 tripulante

    Args:
        ch:     Código de tecla retornado por curses.getch().
        estado: Estado atual do jogo.

    Returns:
        True se a tecla foi reconhecida e processada.
    """
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
        estado.log.append(
            f"Leme -{HOTKEY_PASSO_LEME:.0f} (direita/estibordo) -> "
            f"{jogador.heading_alvo:.0f} graus"
        )
        return True
    if letra == 'D':
        jogador.heading_alvo = (jogador.heading_alvo + HOTKEY_PASSO_LEME) % 360
        estado.log.append(
            f"Leme +{HOTKEY_PASSO_LEME:.0f} (esquerda/bombordo) -> "
            f"{jogador.heading_alvo:.0f} graus"
        )
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
