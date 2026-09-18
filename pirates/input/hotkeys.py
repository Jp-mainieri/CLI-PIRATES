"""
hotkeys.py – Atalhos de teclado em tempo real de CLI PIRATES.

Hotkeys funcionam apenas quando o prompt está vazio e a opção está ligada
em Ajustes. O sistema de "foco" mantém qual canhão ou parte de reparo
está selecionado para ajuste rápido via teclas.
"""

from ..constants import (
    PARTES, HOTKEY_PASSO_MIRA, HOTKEY_PASSO_LEME,
    ZOOM_NIVEIS, MUNDO_ZOOM_NAV_PADRAO,
)
from ..core.utils import clamp
from ..core.state import Estado, tentar_assumir_tripulacao, reconciliar_jogador
from ..core.tripulacao import POSTO_BOMBA, posto_reparo
from .commands import _armar_canhao_com_padrao

# Cada direção de zoom aceita a tecla com e sem SHIFT, porque no teclado é a
# mesma tecla física. Duas tuplas em vez de uma lista só: com uma lista o
# desempate vira um `or` de comparações, onde já escapou um `ord('+')` repetido
# no lugar de `ord('=')` e a tecla '=' ficou inerte sem ninguém notar.
ZOOM_APROXIMA = (ord('+'), ord('='))
ZOOM_AFASTA = (ord('-'), ord('_'))


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
    """Incrementa ou decrementa a mira de TODOS os canhões do jogador.

    Não depende de foco: I/K ajustam a frota inteira de uma vez, foco de
    canhão (J/L) serve só para outras hotkeys (ex.: armar/desarmar).
    """
    algum = False
    for lado in estado.jogador.canhoes:
        for c in estado.jogador.canhoes[lado]:
            algum = True
            novo = clamp(c.mira_atual + delta, 50, 900)
            c.mira_atual = novo
            if c.dist_alvo is not None:
                c.dist_alvo = novo
    if algum:
        sinal = "+" if delta >= 0 else "-"
        estado.log.append(f"Mira de todos os canhoes: {sinal}{abs(delta):.0f}m")


def _ajustar_bomba(estado: Estado, delta: int) -> None:
    """Adiciona (+1) ou remove (-1) um tripulante das bombas."""
    if delta > 0:
        atual = estado.crew_bomba
        final, _ = tentar_assumir_tripulacao(estado, atual + 1, atual, POSTO_BOMBA)
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
            estado, atual + 1, atual, posto_reparo(parte)
        )
        estado.crew_reparo[parte] = final
        if final <= atual:
            estado.log.append(f"Nao ha tripulacao disponivel para reparo de {parte}")
            return
    else:
        estado.crew_reparo[parte] = max(0, atual - 1)
    estado.log.append(f"Reparo {parte}: {estado.crew_reparo[parte]} tripulante(s)")


def _ajustar_zoom_nav(estado: Estado, passo: int) -> bool:
    """Move o zoom do mapa de navegação *passo* níveis em ZOOM_NIVEIS.

    passo = -1 aproxima (menos metros de alcance), +1 afasta. Fora dos
    extremos da lista a tecla é reconhecida mas não muda nada, só avisa.

    Returns:
        True se o nível de zoom mudou de fato.
    """
    atual = getattr(estado, 'zoom_nav', MUNDO_ZOOM_NAV_PADRAO)
    # Um zoom_nav restaurado de save antigo pode não estar na lista; o nível
    # mais próximo evita ValueError e devolve o jogador à escala canônica.
    if atual in ZOOM_NIVEIS:
        idx = ZOOM_NIVEIS.index(atual)
    else:
        idx = min(range(len(ZOOM_NIVEIS)), key=lambda i: abs(ZOOM_NIVEIS[i] - atual))
    novo_idx = idx + passo
    if not (0 <= novo_idx < len(ZOOM_NIVEIS)):
        limite = "maxima" if passo < 0 else "minima"
        estado.log.append(f"Mapa ja esta na aproximacao {limite} (~{atual}m)")
        return False
    estado.zoom_nav = ZOOM_NIVEIS[novo_idx]
    estado.zoom_nav_mudou_em = estado.tempo
    direcao = "aproximado" if passo < 0 else "afastado"
    estado.log.append(f"Mapa {direcao}: zoom ~{estado.zoom_nav}m")
    return True


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


def processar_hotkey(ch: int, estado: Estado, estado_mundo=None) -> bool:
    """Processa uma hotkey e casa o roster de tripulação com o resultado.

    Wrapper fino sobre `_processar_hotkey`: como o dispatcher tem dezenas de
    pontos de saída, a reconciliação fica aqui, num lugar só, para que nenhuma
    hotkey nova possa esquecer dela. É idempotente e barata.

    Args:
        estado_mundo: Estado do mundo aberto, quando houver. Só as hotkeys de
            zoom do mapa de navegação o consultam — ver `_processar_hotkey`.
    """
    resultado = _processar_hotkey(ch, estado, estado_mundo)
    reconciliar_jogador(estado)
    return resultado


def _processar_hotkey(ch: int, estado: Estado, estado_mundo=None) -> bool:
    """Processa uma tecla pressionada como hotkey de jogo.

    Mapeamento (maiúsculas e minúsculas equivalentes):
        ESPAÇO  – alterna o item em foco
        + = / - _ – zoom do mapa de navegação (só fora de combate)
        A / D   – leme ±HOTKEY_PASSO_LEME graus
        Q       – cicla o slot de vela selecionado
        W / S   – nível ++ / -- do slot de vela selecionado
        J / L   – seleciona canhão bombordo / estibordo
        I / K   – mira ±HOTKEY_PASSO_MIRA metros
        U / H   – bomba +1 / -1 tripulante
        E       – cicla partes de reparo
        R       – reparo -1 tripulante

    Args:
        ch:     Código de tecla retornado por curses.getch().
        estado: Estado atual do jogo.
        estado_mundo: Estado do mundo aberto (None em combate de arena avulso).

    Returns:
        True se a tecla foi reconhecida e processada.
    """
    jogador = estado.jogador

    if ch == ord(' '):
        _alternar_foco(estado)
        return True

    # +/- antes do filtro isalpha abaixo, que barraria os dois. Só valem quando
    # o mapa de navegação está na tela: em combate o minimapa usa zoom
    # automático e mexer em zoom_nav ali não teria efeito visível.
    if ch in ZOOM_APROXIMA or ch in ZOOM_AFASTA:
        if estado_mundo is None or getattr(estado_mundo, 'em_combate', False):
            return False
        _ajustar_zoom_nav(estado, -1 if ch in ZOOM_APROXIMA else +1)
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
    if letra == 'Q':
        n = len(jogador.slots_vela)
        if n:
            idx = jogador.slot_vela_selecionado
            for _ in range(n):
                idx = (idx + 1) % n
                if jogador.slots_vela[idx]["tipo"] is not None:
                    break
            jogador.slot_vela_selecionado = idx
            slot = jogador.slots_vela[idx]
            tipo = slot["tipo"] or "vazio"
            estado.log.append(f"Slot {idx} selecionado: {slot['local']}-{tipo}")
        return True
    if letra == 'W':
        if jogador.slots_vela:
            slot = jogador.slots_vela[jogador.slot_vela_selecionado]
            if slot["tipo"] is not None:
                slot["nivel"] = min(2, slot["nivel"] + 1)
                estado.log.append(f"Slot {jogador.slot_vela_selecionado} nivel {slot['nivel']}")
        return True
    if letra == 'S':
        if jogador.slots_vela:
            slot = jogador.slots_vela[jogador.slot_vela_selecionado]
            if slot["tipo"] is not None:
                slot["nivel"] = max(0, slot["nivel"] - 1)
                estado.log.append(f"Slot {jogador.slot_vela_selecionado} nivel {slot['nivel']}")
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
