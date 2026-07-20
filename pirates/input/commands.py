"""
commands.py – Processamento de comandos de texto e autocompletar em CLI PIRATES.

Interpreta o que o jogador digita no prompt, valida os argumentos e aplica
as mudanças no estado do jogo. Inclui o sistema de autocompletar por TAB.
"""

from ..constants import PARTES, COMANDOS, CANHAO_SUBCMDS, ALIASES
from ..core.ship import resolver_canhao
from ..core.state import Estado, tentar_assumir_tripulacao
from ..core.combat import distancia, rumo_para


def processar_comando(texto: str, estado: Estado) -> None:
    """Analisa e executa um comando de texto digitado pelo jogador.

    Args:
        texto:  String de comando com possíveis argumentos.
        estado: Estado atual do jogo (modificado in-place).
    """
    partes_cmd = texto.strip().lower().split()
    if not partes_cmd:
        return
    cmd = partes_cmd[0]
    if cmd in ALIASES:
        cmd = ALIASES[cmd]
    jogador = estado.jogador
    inimigo = estado.inimigo

    if cmd == "ajuda":
        estado.log.append("l/v/r/b/c = leme/vela/reparar/bomba/canhao | ENTER vazio repete")
        estado.log.append("canhao <id> <n> <dist> | <id> <dist> (trip minimo) | <id> trip <n>")
        estado.log.append(
            f"canhoes deste navio: {', '.join(estado.canhao_ids)} | radar | ESC sai"
        )

    elif cmd == "radar":
        d = distancia(jogador, inimigo)
        r = rumo_para(jogador, inimigo)
        rel = (r - jogador.heading) % 360
        if 20 <= rel <= 160:
            arco = "ESTIBORDO"
        elif 200 <= rel <= 340:
            arco = "BOMBORDO"
        else:
            arco = "fora de arco"
        alcance = "dentro do alcance" if d <= jogador.alcance_canhao else "fora de alcance"
        estado.log.append(f"RADAR: {d:.0f}m, rumo {r:.0f} graus, {arco}, {alcance}")

    elif cmd == "leme" and len(partes_cmd) == 2:
        try:
            jogador.heading_alvo = float(partes_cmd[1]) % 360
            estado.log.append(f"Leme para {jogador.heading_alvo:.0f} graus")
        except ValueError:
            estado.log.append("Uso: leme <graus>")

    elif cmd == "vela" and len(partes_cmd) == 1:
        if not jogador.slots_vela:
            estado.log.append("Este navio nao tem slots de vela.")
        for i, slot in enumerate(jogador.slots_vela):
            marca = ">" if i == jogador.slot_vela_selecionado else " "
            tipo = slot["tipo"] or "vazio"
            pct = slot["nivel"] * 50
            estado.log.append(f"{marca}{i} {slot['local']}-{tipo} ({pct}%)")

    elif cmd == "vela" and len(partes_cmd) == 2:
        try:
            nivel = int(partes_cmd[1])
        except ValueError:
            estado.log.append("Uso: vela | vela <0-2> | vela <ID> <0-2>")
            return
        if not (0 <= nivel <= 2):
            estado.log.append("Nivel de vela deve ser 0, 1 ou 2.")
            return
        if not jogador.slots_vela:
            estado.log.append("Este navio nao tem slots de vela.")
            return
        slot = jogador.slots_vela[jogador.slot_vela_selecionado]
        if slot["tipo"] is None:
            estado.log.append("Slot selecionado esta vazio - instale uma vela no porto primeiro.")
            return
        slot["nivel"] = nivel
        estado.log.append(f"Slot {jogador.slot_vela_selecionado} ({slot['local']}) no nivel {nivel}")

    elif cmd == "vela" and len(partes_cmd) == 3:
        try:
            indice = int(partes_cmd[1])
            nivel = int(partes_cmd[2])
        except ValueError:
            estado.log.append("Uso: vela <ID> <0-2>")
            return
        if not (0 <= indice < len(jogador.slots_vela)):
            estado.log.append("ID de slot invalido.")
            return
        if not (0 <= nivel <= 2):
            estado.log.append("Nivel de vela deve ser 0, 1 ou 2.")
            return
        slot = jogador.slots_vela[indice]
        if slot["tipo"] is None:
            estado.log.append("Esse slot esta vazio - instale uma vela no porto primeiro.")
            return
        slot["nivel"] = nivel
        estado.log.append(f"Slot {indice} ({slot['local']}) no nivel {nivel}")

    elif cmd == "ancorar":
        jogador.ancorado = not jogador.ancorado
        if jogador.ancorado:
            estado.log.append("Ancora lancada - navio parado, leme ainda funciona.")
        else:
            estado.log.append("Ancora levantada.")

    elif cmd == "reparar" and len(partes_cmd) == 3:
        parte = partes_cmd[1]
        if parte not in PARTES:
            estado.log.append(f"Parte invalida. Opcoes: {', '.join(PARTES)}")
            return
        try:
            n = int(partes_cmd[2])
        except ValueError:
            estado.log.append("Uso: reparar <parte> <tripulantes>")
            return
        if n < 0:
            estado.log.append("Numero de tripulantes nao pode ser negativo")
            return
        atual = estado.crew_reparo[parte]
        final, cortou = tentar_assumir_tripulacao(estado, n, atual, ignorar_parte=parte)
        estado.crew_reparo[parte] = final
        if cortou:
            estado.log.append(
                f"So consegui {final} de {n} tripulante(s) pedidos para {parte} "
                f"(bomba nao foi mexida)"
            )
        else:
            estado.log.append(f"{final} tripulante(s) reparando {parte} continuamente")

    elif cmd == "bomba" and len(partes_cmd) == 2:
        try:
            n = int(partes_cmd[1])
        except ValueError:
            estado.log.append("Uso: bomba <tripulantes>")
            return
        if n < 0:
            estado.log.append("Numero de tripulantes nao pode ser negativo")
            return
        atual = estado.crew_bomba
        final, cortou = tentar_assumir_tripulacao(estado, n, atual)
        estado.crew_bomba = final
        if cortou:
            estado.log.append(
                f"So consegui {final} de {n} tripulante(s) pedidos para a bomba"
            )
        else:
            estado.log.append(f"{final} tripulante(s) nas bombas")

    elif cmd == "canhao" and len(partes_cmd) >= 2:
        canhao = resolver_canhao(partes_cmd[1], jogador)
        if canhao is None:
            estado.log.append(f"Canhao invalido. Use: {', '.join(estado.canhao_ids)}")
            return

        resto = partes_cmd[2:]

        if len(resto) == 1 and resto[0] == "parar":
            canhao.dist_alvo = None
            canhao.tripulantes = 0
            estado.log.append(
                f"Canhao {canhao.label} parou de atirar e liberou a tripulacao"
            )

        elif len(resto) == 1:
            try:
                dist = float(resto[0])
            except ValueError:
                estado.log.append(
                    "Uso: canhao <id> <distancia> | <id> <n> <distancia> | "
                    "<id> trip <n> | <id> mirar <d> | <id> parar"
                )
                return
            if canhao.tripulantes >= estado.min_crew_canhao:
                canhao.dist_alvo = dist
                canhao.mira_atual = dist
                estado.log.append(
                    f"Canhao {canhao.label} mirando {dist:.0f}m - atirara sozinho"
                )
            else:
                _armar_canhao_com_padrao(estado, canhao, dist)

        elif len(resto) == 2 and resto[0] == "trip":
            try:
                n = int(resto[1])
            except ValueError:
                estado.log.append("Uso: canhao <id> trip <n>")
                return
            if n != 0 and n < estado.min_crew_canhao:
                estado.log.append(
                    f"Um canhao precisa de pelo menos {estado.min_crew_canhao} "
                    f"tripulante(s) (ou 0 para liberar)"
                )
                return
            _definir_trip_canhao(estado, canhao, n)

        elif len(resto) == 2 and resto[0] == "mirar":
            if canhao.tripulantes < estado.min_crew_canhao:
                estado.log.append(
                    f"Aloque tripulantes no canhao {canhao.label} antes de mirar"
                )
                return
            try:
                dist = float(resto[1])
            except ValueError:
                estado.log.append("Uso: canhao <id> mirar <distancia>")
                return
            canhao.dist_alvo = dist
            canhao.mira_atual = dist
            estado.log.append(
                f"Canhao {canhao.label} mirando {dist:.0f}m - atirara sozinho"
            )

        elif len(resto) == 2:
            try:
                n = int(resto[0])
                dist = float(resto[1])
            except ValueError:
                estado.log.append(
                    "Uso: canhao <id> <tripulantes> <distancia> | "
                    "trip <n> | mirar <d> | parar"
                )
                return
            if n != 0 and n < estado.min_crew_canhao:
                estado.log.append(
                    f"Um canhao precisa de pelo menos {estado.min_crew_canhao} tripulante(s)"
                )
                return
            _definir_trip_canhao(estado, canhao, n, dist_se_armar=dist)

        else:
            estado.log.append(
                "Uso: canhao <id> <tripulantes> <distancia> | <id> <distancia> | "
                "trip <n> | mirar <d> | parar"
            )

    elif cmd == "fugir":
        if estado.inimigo_em_fuga:
            estado.log.append("O inimigo ja esta fugindo, nao ha sentido em fugir agora.")
        elif estado.jogador_tentando_fugir:
            estado.log.append("Voce ja esta tentando fugir. Afaste-se e mantenha distancia!")
        else:
            estado.jogador_tentando_fugir = True
            estado.tempo_fuga_jogador = 0.0
            estado.log.append(
                "Voce tenta fugir! Afaste-se a mais de 900m por 15s (custa notoriedade)."
            )

    else:
        estado.log.append("Comando nao reconhecido. Digite 'ajuda'.")


def _definir_trip_canhao(
    estado: Estado,
    canhao,
    n: int,
    dist_se_armar: float | None = None,
) -> None:
    """Define a tripulação de um canhão, realocando se necessário.

    Args:
        estado:        Estado atual do jogo.
        canhao:        Objeto Canhao a configurar.
        n:             Número de tripulantes (0 = liberar).
        dist_se_armar: Se fornecida, define a mira ao armar.
    """
    if n == 0:
        canhao.tripulantes = 0
        canhao.dist_alvo = None
        estado.log.append(f"Canhao {canhao.label} liberado")
        return

    atual = canhao.tripulantes
    final, cortou = tentar_assumir_tripulacao(estado, n, atual, ignorar_canhao=canhao)
    if final < estado.min_crew_canhao:
        canhao.tripulantes = 0
        canhao.dist_alvo = None
        estado.log.append(
            f"Nao ha tripulacao suficiente (nem realocando) para o canhao "
            f"{canhao.label} - continua sem tripulacao"
        )
        return

    canhao.tripulantes = final
    if dist_se_armar is not None:
        canhao.dist_alvo = dist_se_armar
        canhao.mira_atual = dist_se_armar
    if cortou:
        estado.log.append(
            f"So consegui {final} de {n} tripulante(s) pedidos para o canhao {canhao.label}"
        )
    else:
        msg = f"{final} tripulante(s) no canhao {canhao.label}"
        msg += f", mirando {dist_se_armar:.0f}m" if dist_se_armar is not None else ". Use 'mirar' para armar."
        estado.log.append(msg)


def _armar_canhao_com_padrao(estado: Estado, canhao, dist: float) -> None:
    """Arma um canhão com a tripulação mínima e a distância especificada."""
    _definir_trip_canhao(estado, canhao, estado.min_crew_canhao, dist_se_armar=dist)


def obter_candidatos(
    tokens_completos: list[str],
    partial: str,
    estado: Estado,
) -> list[str]:
    """Retorna sugestões de autocompletar para o contexto atual do prompt.

    Args:
        tokens_completos: Tokens já completos à esquerda do cursor.
        partial:          Token parcial na posição do cursor.
        estado:           Estado atual (para IDs de canhões disponíveis).

    Returns:
        Lista de strings que completam *partial* no contexto dado.
    """
    pl = partial.lower()
    if len(tokens_completos) == 0:
        return [c for c in COMANDOS if c.startswith(pl)]
    cmd = tokens_completos[0]
    if cmd in ALIASES:
        cmd = ALIASES[cmd]
    pos = len(tokens_completos)
    if cmd == "canhao":
        if pos == 1:
            return [c for c in estado.canhao_ids if c.lower().startswith(pl)]
        if pos == 2:
            return [c for c in CANHAO_SUBCMDS if c.startswith(pl)]
    elif cmd == "reparar" and pos == 1:
        return [c for c in PARTES if c.startswith(pl)]
    elif cmd == "vela" and pos == 1:
        opcoes = [str(i) for i in range(len(estado.jogador.slots_vela))]
        opcoes += [c for c in ("0", "1", "2") if c not in opcoes]
        return [c for c in opcoes if c.startswith(pl)]
    elif cmd == "vela" and pos == 2:
        return [c for c in ("0", "1", "2") if c.startswith(pl)]
    return []
