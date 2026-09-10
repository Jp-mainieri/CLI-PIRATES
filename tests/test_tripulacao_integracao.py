"""Integração do trânsito de tripulação com Estado, inputs, IA e os dois loops."""

import pytest

from pirates.constants import (
    TRANSITO_CANHAO_MESMO_BORDO, TRANSITO_CANHAO_BORDO_OPOSTO,
    TRANSITO_TAREFA_DIFERENTE, PARTES, SAIDA_BOMBA_SEG,
)
from pirates.ai.enemy import _crewar_canhoes, atualizar_ia_tripulacao
from pirates.core.simulation import atualizar_simulacao
from pirates.core.state import Estado, reconciliar_jogador
from pirates.core.tripulacao import (
    POSTO_BOMBA, aplicar_efetivos, efetivos_bomba, efetivos_reparo,
)
from pirates.input.commands import processar_comando


def _estado(tipo="brigantim"):
    e = Estado(tipo_navio=tipo)
    e.jogador.heading = 0.0
    e.inimigo.x, e.inimigo.y = 200.0, 0.0
    return e


def _armar(e, label, dist=200.0):
    processar_comando(f"canhao {label} {dist:.0f}", e)


def _canhao(e, label):
    lado = 'estibordo' if label[0].lower() == 'e' else 'bombordo'
    return e.jogador.canhoes[lado][int(label[1:]) - 1]


class TestFluxoDoJogador:
    def test_armar_primeiro_canhao_e_imediato(self):
        e = _estado()
        _armar(e, "e1")
        c = _canhao(e, "e1")
        assert c.tripulantes == 1
        assert c.efetivos == 1
        assert c.armado()

    def test_trocar_de_bordo_custa_o_tempo_cheio(self):
        """O exploit original: armar E1, tirar dele e armar B1 do outro bordo."""
        e = _estado()
        e.crew_total = 1
        e.tripulacao.redimensionar(["T1"])
        _armar(e, "e1")
        _armar(e, "b1")
        b1 = _canhao(e, "b1")
        assert b1.tripulantes == 1
        assert b1.efetivos == 0
        assert not b1.armado()
        assert e.tripulacao.transito_restante_do_posto(
            ('canhao', 'bombordo', 1)
        ) == TRANSITO_CANHAO_BORDO_OPOSTO

    def test_trocar_no_mesmo_bordo_custa_menos(self):
        e = _estado()
        e.crew_total = 1
        e.tripulacao.redimensionar(["T1"])
        _armar(e, "e1")
        _armar(e, "e2")
        assert e.tripulacao.transito_restante_do_posto(
            ('canhao', 'estibordo', 2)
        ) == TRANSITO_CANHAO_MESMO_BORDO

    def test_canhao_para_bomba_custa_troca_de_tarefa(self):
        e = _estado()
        e.crew_total = 1
        e.tripulacao.redimensionar(["T1"])
        _armar(e, "e1")
        processar_comando("bomba 1", e)
        assert e.tripulacao.transito_restante_do_posto(POSTO_BOMBA) == (
            TRANSITO_TAREFA_DIFERENTE
        )

    def test_estacionar_no_conves_nao_barateia_a_troca(self):
        """Passar pelo ócio não pode lavar o custo do bordo oposto."""
        e = _estado()
        e.crew_total = 1
        e.tripulacao.redimensionar(["T1"])
        _armar(e, "e1")
        processar_comando("canhao e1 parar", e)
        _armar(e, "b1")
        assert e.tripulacao.transito_restante_do_posto(
            ('canhao', 'bombordo', 1)
        ) == TRANSITO_CANHAO_BORDO_OPOSTO

    def test_log_avisa_o_tempo_de_chegada(self):
        e = _estado()
        e.crew_total = 1
        e.tripulacao.redimensionar(["T1"])
        _armar(e, "e1")
        e.log.clear()
        _armar(e, "b1")
        assert any("a caminho" in m for m in e.log)


class TestExploitDoRodizio:
    """A recarga não pode correr num canhão cuja equipe está longe."""

    def test_canhao_abandonado_nao_recarrega(self):
        e = _estado()
        e.crew_total = 1
        e.tripulacao.redimensionar(["T1"])
        _armar(e, "e1")
        c = _canhao(e, "e1")
        c.proximo_tiro = 100.0
        _armar(e, "b1")           # leva o único tripulante embora
        assert c.tripulantes == 0

        antes = c.proximo_tiro
        for _ in range(20):
            atualizar_simulacao(e, 0.5)
        # Sem ninguém ao canhão, o cooldown não anda: proximo_tiro acompanha
        # o relógio em vez de ficar para trás.
        assert c.proximo_tiro > antes

    def test_canhao_com_equipe_a_caminho_nao_dispara(self):
        e = _estado()
        e.crew_total = 1
        e.tripulacao.redimensionar(["T1"])
        _armar(e, "e1")
        _armar(e, "b1")
        b1 = _canhao(e, "b1")
        b1.proximo_tiro = 0.0
        atualizar_simulacao(e, 0.5)
        assert not b1.armado()
        assert e.stats["tiros_jogador"] == 0


class TestRelogio:
    """Armadilha 1: os timers são relativos, não instantes de estado.tempo."""

    def test_transito_continua_apos_reset_do_tempo(self):
        e = _estado()
        e.crew_total = 1
        e.tripulacao.redimensionar(["T1"])
        _armar(e, "e1")
        _armar(e, "b1")
        t = e.tripulacao.membros[0]

        # 4s de "navegação" (mesma chamada que game.py faz no mundo_loop)
        for _ in range(8):
            e.tripulacao.atualizar(0.5)
            aplicar_efetivos(e.jogador, e.tripulacao)
        parcial = t.transito_restante
        assert 0 < parcial < TRANSITO_CANHAO_BORDO_OPOSTO

        e.tempo = 0.0  # novo combate
        atualizar_simulacao(e, 0.5)
        assert t.transito_restante == pytest.approx(parcial - 0.5)

    def test_transito_vence_e_o_canhao_volta_a_valer(self):
        e = _estado()
        e.crew_total = 1
        e.tripulacao.redimensionar(["T1"])
        _armar(e, "e1")
        _armar(e, "b1")
        for _ in range(int(TRANSITO_CANHAO_BORDO_OPOSTO / 0.5) + 1):
            e.tripulacao.atualizar(0.5)
        aplicar_efetivos(e.jogador, e.tripulacao)
        assert _canhao(e, "b1").efetivos == 1


class TestEfetivoVsAlocado:
    """Armadilha 3: quem está a caminho não trabalha."""

    def _dois_na_bomba_um_em_transito(self, e):
        """Deixa a bomba com 2 alocados dos quais 1 ainda está a caminho.

        Note que a bomba nunca é esvaziada automaticamente por
        `_liberar_tripulantes`: para tirar alguém dela é preciso pedir.
        """
        e.crew_total = 2
        e.tripulacao.redimensionar(["T1", "T2"])
        processar_comando("bomba 2", e)
        assert efetivos_bomba(e.tripulacao) == 2

        processar_comando("bomba 1", e)   # libera um explicitamente
        _armar(e, "e1")                   # ele vai ao canhão (6s)
        for _ in range(int(TRANSITO_TAREFA_DIFERENTE / 0.5) + 1):
            e.tripulacao.atualizar(0.5)   # deixa chegar, para valer o posto novo
        processar_comando("bomba 2", e)   # e volta à bomba: outros 6s

    def test_bomba_so_conta_quem_chegou(self):
        e = _estado()
        self._dois_na_bomba_um_em_transito(e)
        assert e.crew_bomba == 2
        assert efetivos_bomba(e.tripulacao) == 1

    def test_agua_sai_na_taxa_dos_efetivos(self):
        e = _estado()
        e.jogador.partes = {p: 100.0 for p in PARTES}
        self._dois_na_bomba_um_em_transito(e)
        e.jogador.agua = 50.0

        antes = e.jogador.agua
        atualizar_simulacao(e, 1.0)
        removido = antes - e.jogador.agua
        # 1 efetivo, não 2 (casco intacto ⇒ entrada de água desprezível).
        assert removido == pytest.approx(SAIDA_BOMBA_SEG, abs=0.3)

    def test_reparo_so_conta_quem_chegou(self):
        e = _estado()
        e.crew_total = 2
        e.tripulacao.redimensionar(["T1", "T2"])
        processar_comando("reparar casco 2", e)
        assert efetivos_reparo(e.tripulacao) == {"casco": 2}

        _armar(e, "e1")  # puxa um do reparo
        for _ in range(int(TRANSITO_TAREFA_DIFERENTE / 0.5) + 1):
            e.tripulacao.atualizar(0.5)
        processar_comando("reparar casco 2", e)  # e devolve ao reparo
        assert e.crew_reparo["casco"] == 2
        assert efetivos_reparo(e.tripulacao) == {"casco": 1}

    def test_volta_atras_no_meio_do_caminho_e_gratis(self):
        """Trânsito interrompido não credita o destino — nem cobra a volta."""
        e = _estado()
        e.crew_total = 2
        e.tripulacao.redimensionar(["T1", "T2"])
        processar_comando("reparar casco 2", e)
        _armar(e, "e1")                          # um sai do reparo (6s)
        processar_comando("reparar casco 2", e)  # arrependimento imediato
        assert efetivos_reparo(e.tripulacao) == {"casco": 2}


class TestLiberacaoAutomatica:
    """Armadilha 7: `_liberar_tripulantes` agora tem preço."""

    def test_puxa_do_mesmo_bordo_do_destino(self):
        e = _estado()
        e.crew_total = 2
        e.tripulacao.redimensionar(["T1", "T2"])
        _armar(e, "e1")
        _armar(e, "b1")
        for _ in range(40):
            e.tripulacao.atualizar(0.5)
        aplicar_efetivos(e.jogador, e.tripulacao)

        # Sem gente livre, armar E2 deve sacrificar E1 (mesmo bordo, 3s),
        # não B1 do outro lado.
        _armar(e, "e2")
        assert _canhao(e, "e1").tripulantes == 0
        assert _canhao(e, "b1").tripulantes == 1
        assert e.tripulacao.transito_restante_do_posto(
            ('canhao', 'estibordo', 2)
        ) == TRANSITO_CANHAO_MESMO_BORDO

    def test_retirada_parcial_nao_esvazia_canhao_inteiro(self):
        e = _estado()
        e.crew_total = 3
        e.tripulacao.redimensionar(["T1", "T2", "T3"])
        processar_comando("canhao e1 3 200", e)
        assert _canhao(e, "e1").tripulantes == 3
        processar_comando("bomba 1", e)
        # Só um tripulante é levado; o canhão continua operante.
        assert _canhao(e, "e1").tripulantes == 2
        assert _canhao(e, "e1").dist_alvo is not None


class TestSimetriaComAIA:
    def test_mesmo_custo_para_jogador_e_inimigo(self):
        e = _estado()
        for roster, canhoes in (
            (e.tripulacao, e.jogador.canhoes),
            (e.inimigo_tripulacao, e.inimigo.canhoes),
        ):
            roster.redimensionar(["X1"])
            t = roster.membros[0]
            roster.alocar(t, ('canhao', 'estibordo', 1))
            roster.alocar(t, ('canhao', 'bombordo', 1))
            assert t.transito_restante == TRANSITO_CANHAO_BORDO_OPOSTO

    def test_ia_estavel_nao_entra_em_transito_permanente(self):
        """O risco nº 1: IA realocando todo tick nunca chegaria a atirar."""
        e = _estado()
        atualizar_ia_tripulacao(e)
        for _ in range(50):
            e.inimigo_tripulacao.atualizar(0.5)
            atualizar_ia_tripulacao(e)
        assert e.inimigo_tripulacao.em_transito() == []
        assert any(
            c.efetivos > 0
            for lado in ('estibordo', 'bombordo')
            for c in e.inimigo.canhoes[lado]
        )

    def test_ia_realoca_ao_trocar_de_bordada(self):
        e = _estado()
        e.ia_lado_bordada = 'estibordo'
        e.inimigo_crew_total = 2
        e.inimigo_tripulacao.redimensionar(["I1", "I2"])
        atualizar_ia_tripulacao(e)
        for _ in range(50):
            e.inimigo_tripulacao.atualizar(0.5)
        atualizar_ia_tripulacao(e)
        assert e.inimigo.canhoes['estibordo'][0].efetivos == 1

        e.ia_lado_bordada = 'bombordo'
        atualizar_ia_tripulacao(e)
        assert len(e.inimigo_tripulacao.em_transito()) > 0

    def test_throttle_evita_realocar_a_cada_oscilacao_de_agua(self):
        e = _estado()
        e.ia_limiar_agua = 20.0
        e.inimigo.agua = 21.0
        e.tempo = 100.0
        atualizar_ia_tripulacao(e)
        for _ in range(30):
            e.tempo += 0.5
            e.inimigo.agua += 0.4 if int(e.tempo) % 2 else -0.4
            e.inimigo_tripulacao.atualizar(0.5)
            atualizar_ia_tripulacao(e)
        assert e.inimigo_tripulacao.em_transito() == []


class TestSincronizacaoDeRoster:
    def test_crescer_a_tripulacao_preserva_postos(self):
        from pirates.core.state import sincronizar_crew_com_navio_ativo
        e = _estado()
        _armar(e, "e1")
        veterano = next(t for t in e.tripulacao.membros if t.posto is not None)
        e.jogador.upgrade_niveis["tripulante_extra"] = 2
        sincronizar_crew_com_navio_ativo(e, e.tipo_navio)
        assert len(e.tripulacao.membros) == e.crew_total
        assert veterano.posto == ('canhao', 'estibordo', 1)
        assert _canhao(e, "e1").efetivos == 1


class TestRoster:
    def test_montar_tripulacao_marca_transito(self):
        from pirates.core.state import montar_tripulacao
        e = _estado()
        e.crew_total = 1
        e.tripulacao.redimensionar(["T1"])
        _armar(e, "e1")
        _armar(e, "b1")
        roster = montar_tripulacao(e)
        assert [tarefa for _, tarefa, _ in roster] == ["transito"]
        assert "canhao B1" in roster[0][2]

    def test_roster_tem_uma_linha_por_tripulante(self):
        from pirates.core.state import montar_tripulacao
        e = _estado()
        _armar(e, "e1")
        processar_comando("bomba 2", e)
        assert len(montar_tripulacao(e)) == e.crew_total

    def test_ids_ficam_presos_ao_tripulante(self):
        """O roster antigo derivava das contagens e fazia os IDs pularem."""
        from pirates.core.state import montar_tripulacao
        e = _estado()
        _armar(e, "e1")
        dono = next(tid for tid, tarefa, _ in montar_tripulacao(e) if tarefa == "canhao")
        processar_comando("bomba 1", e)
        ainda = next(tid for tid, tarefa, _ in montar_tripulacao(e) if tarefa == "canhao")
        assert ainda == dono


class TestAcoplamentoBordadaTripulacao:
    """A escolha de bordo não pode perseguir uma salva que não existe.

    `_escolher_lado_bordada` decide pela prontidão dos canhões, e a prontidão
    passou a depender de haver tripulação — que por sua vez é alocada segundo o
    bordo escolhido. Sem cuidado, os dois se realimentam e a IA passa o combate
    atravessando o convés.
    """

    def test_canhao_sem_tripulacao_nao_conta_como_pronto(self):
        from pirates.ai.enemy import _lado_pronto
        e = _estado()
        e.tempo = 100.0
        for c in e.inimigo.canhoes['bombordo']:
            c.proximo_tiro = 0.0   # cooldown vencido...
            c.efetivos = 0         # ...mas sem ninguém para disparar
        assert _lado_pronto(e, 'bombordo') == 0

    def test_nao_troca_de_bordo_com_tripulacao_curta(self):
        e = _estado()
        e.inimigo_crew_total = 2   # dá para guarnecer um bordo só
        e.inimigo_tripulacao.redimensionar(["I1", "I2"])
        e.ia_lado_bordada = 'estibordo'
        atualizar_ia_tripulacao(e)

        for _ in range(200):
            e.tempo += 0.5
            e.inimigo_tripulacao.atualizar(0.5)
            atualizar_ia_tripulacao(e)
        assert e.ia_lado_bordada == 'estibordo'
        assert e.inimigo_tripulacao.em_transito() == []

    def test_ia_nao_fica_atravessando_o_conves(self):
        """Regressão: a IA gastava o combate inteiro em trânsito."""
        from pirates.core.simulation import atualizar_simulacao
        import random
        random.seed(3)
        e = _estado("galeao")
        e.inimigo.x, e.inimigo.y = 400.0, 0.0

        ticks = em_transito = 0
        while e.rodando and ticks < 400:
            atualizar_simulacao(e, 0.5)
            ticks += 1
            if e.inimigo_tripulacao.em_transito():
                em_transito += 1
        assert em_transito / ticks < 0.35
