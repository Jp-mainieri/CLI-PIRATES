"""Testes para pirates/core/ship.py."""

import pytest
from pirates.core.ship import Navio, Canhao, resolver_canhao
from pirates.constants import (
    MORAL_MULT_NORMAL, MORAL_MULT_ABALADO, MORAL_MULT_COMBALIDO, MORAL_MULT_PANICO,
    MORAL_LIMIAR_ALTO, MORAL_LIMIAR_MEDIO, MORAL_BONUS_ACERTO,
)


class TestCanhao:
    def test_label_estibordo(self):
        c = Canhao('estibordo', 1)
        assert c.label == 'E1'

    def test_label_bombordo(self):
        c = Canhao('bombordo', 3)
        assert c.label == 'B3'

    def test_armado_com_tudo(self):
        c = Canhao('estibordo', 1)
        c.tripulantes = 1
        c.dist_alvo = 300.0
        assert c.armado() is True

    def test_nao_armado_sem_tripulante(self):
        c = Canhao('estibordo', 1)
        c.dist_alvo = 300.0
        assert c.armado() is False

    def test_nao_armado_sem_alvo(self):
        c = Canhao('estibordo', 1)
        c.tripulantes = 2
        assert c.armado() is False


class TestNavio:
    def _navio(self, **kwargs):
        return Navio("Teste", x=0, y=0, heading=0, **kwargs)

    def test_velocidade_maxima_sem_dano(self):
        n = self._navio(velocidade_max_base=10.0)
        n.nivel_vela = 3
        assert abs(n.velocidade_maxima() - 10.0) < 0.01

    def test_velocidade_maxima_zero_vela(self):
        n = self._navio(velocidade_max_base=10.0)
        n.nivel_vela = 0
        assert n.velocidade_maxima() == 0.0

    def test_velocidade_reduzida_por_dano_vela(self):
        n = self._navio(velocidade_max_base=10.0)
        n.nivel_vela = 3
        n.partes['vela'] = 50.0
        assert n.velocidade_maxima() < 10.0

    def test_vivo_inicialmente(self):
        n = self._navio()
        assert n.vivo() is True

    def test_afundado_quando_agua_cheia(self):
        n = self._navio()
        n.partes['casco'] = 0.0  # casco destruído → entrada de água máxima
        n.atualizar_agua(tripulantes_bomba=0, dt=1000.0)
        assert n.afundado is True

    def test_bomba_segura_agua_com_casco_intacto(self):
        n = self._navio()
        agua_antes = n.agua
        n.atualizar_agua(tripulantes_bomba=10, dt=1.0)
        assert n.agua <= agua_antes  # bomba impede subida

    def test_heading_clampado_a_360(self):
        n = self._navio()
        n.heading = 370
        n2 = Navio("X", 0, 0, 370)
        assert n2.heading == 10.0  # 370 % 360

    def test_reparar_aumenta_hp(self):
        n = self._navio()
        n.partes['mastro'] = 60.0
        antes = n.partes['mastro']
        n.reparar('mastro', tripulantes=2, dt=1.0)
        assert n.partes['mastro'] > antes

    def test_reparar_nao_ultrapassa_100(self):
        n = self._navio()
        n.partes['mastro'] = 99.9
        n.reparar('mastro', tripulantes=10, dt=100.0)
        assert n.partes['mastro'] <= 100.0


class TestResolverCanhao:
    def _jogador_com_canhoes(self):
        n = Navio("Jogador", 0, 0, 0)
        n.canhoes = {
            'estibordo': [Canhao('estibordo', 1), Canhao('estibordo', 2)],
            'bombordo':  [Canhao('bombordo', 1)],
        }
        return n

    def test_resolve_estibordo(self):
        j = self._jogador_com_canhoes()
        c = resolver_canhao('E1', j)
        assert c is not None
        assert c.label == 'E1'

    def test_resolve_case_insensitive(self):
        j = self._jogador_com_canhoes()
        assert resolver_canhao('e2', j) is not None
        assert resolver_canhao('E2', j) is not None

    def test_resolve_bombordo(self):
        j = self._jogador_com_canhoes()
        c = resolver_canhao('B1', j)
        assert c is not None
        assert c.label == 'B1'

    def test_indice_invalido(self):
        j = self._jogador_com_canhoes()
        assert resolver_canhao('E9', j) is None

    def test_prefixo_invalido(self):
        assert resolver_canhao('X1', Navio("", 0, 0, 0)) is None

    def test_string_vazia(self):
        assert resolver_canhao('', Navio("", 0, 0, 0)) is None


class TestMoral:
    def _navio(self, **kwargs):
        return Navio("Teste", x=0, y=0, heading=0, **kwargs)

    def test_moral_inicial_cem(self):
        n = self._navio()
        assert n.moral_atual == 100.0

    def test_multiplicador_normal(self):
        n = self._navio()
        n.moral_atual = MORAL_LIMIAR_ALTO + 1
        assert n.multiplicador_moral() == MORAL_MULT_NORMAL

    def test_multiplicador_abalado(self):
        n = self._navio()
        n.moral_atual = (MORAL_LIMIAR_ALTO + MORAL_LIMIAR_MEDIO) / 2
        assert n.multiplicador_moral() == MORAL_MULT_ABALADO

    def test_multiplicador_combalido(self):
        n = self._navio()
        n.moral_atual = MORAL_LIMIAR_MEDIO / 2
        assert n.multiplicador_moral() == MORAL_MULT_COMBALIDO

    def test_multiplicador_panico(self):
        n = self._navio()
        n.moral_atual = 0.0
        assert n.multiplicador_moral() == MORAL_MULT_PANICO

    def test_registrar_acerto_aumenta_moral(self):
        n = self._navio()
        n.moral_atual = 50.0
        n.registrar_acerto_moral()
        assert n.moral_atual == 50.0 + MORAL_BONUS_ACERTO

    def test_registrar_acerto_nao_ultrapassa_100(self):
        n = self._navio()
        n.moral_atual = 99.0
        n.registrar_acerto_moral()
        assert n.moral_atual <= 100.0

    def test_moral_alvo_navio_perfeito(self):
        n = self._navio()
        alvo = n.moral_alvo()
        assert abs(alvo - 100.0) < 0.1

    def test_moral_alvo_casco_zero(self):
        n = self._navio()
        n.partes['casco'] = 0.0
        alvo = n.moral_alvo()
        assert alvo < 100.0

    def test_atualizar_moral_desce_quando_acima_alvo(self):
        n = self._navio()
        n.partes['casco'] = 0.0
        n.moral_atual = 100.0
        n.atualizar_moral(dt=1.0)
        assert n.moral_atual < 100.0

    def test_atualizar_moral_sobe_quando_abaixo_alvo(self):
        n = self._navio()
        n.moral_atual = 10.0
        n.atualizar_moral(dt=5.0)
        assert n.moral_atual > 10.0

    def test_atualizar_moral_nao_sai_do_intervalo(self):
        n = self._navio()
        n.partes['casco'] = 0.0
        n.moral_atual = 100.0
        n.atualizar_moral(dt=10000.0)
        assert 0.0 <= n.moral_atual <= 100.0


class TestMoralCrashRecursos:
    def _navio_estocado(self):
        n = Navio("Teste", x=0, y=0, heading=0, porao_capacidade=6)
        n.porao.adicionar("polvora", 10.0)
        n.porao.adicionar("bolas", 10.0)
        n.porao.adicionar("tabuas", 10.0)
        n.moral_atual = 100.0
        n.atualizar_moral(dt=0.1)  # estabelece baseline sem disparar
        return n

    @pytest.mark.parametrize("tipo", ["polvora", "bolas", "tabuas"])
    def test_zerar_recurso_trava_moral_no_teto(self, tipo):
        from pirates.constants import MORAL_CRASH_RECURSOS_TETO
        n = self._navio_estocado()
        n.porao.consumir(tipo, 999.0)
        n.atualizar_moral(dt=0.1)
        assert n.moral_atual <= MORAL_CRASH_RECURSOS_TETO

    def test_nao_retrigera_enquanto_continua_zerado(self):
        from pirates.constants import MORAL_CRASH_RECURSOS_DURACAO_SEG
        n = self._navio_estocado()
        n.porao.consumir("polvora", 999.0)
        n.atualizar_moral(dt=0.1)
        restante_apos_disparo = n.moral_lock_restante
        assert restante_apos_disparo == pytest.approx(MORAL_CRASH_RECURSOS_DURACAO_SEG - 0.1)
        n.atualizar_moral(dt=0.1)
        # decrementou normalmente, não resetou pro valor cheio de novo
        assert n.moral_lock_restante == pytest.approx(MORAL_CRASH_RECURSOS_DURACAO_SEG - 0.2)

    def test_moral_libera_apos_duracao_do_travamento(self):
        from pirates.constants import MORAL_CRASH_RECURSOS_TETO, MORAL_CRASH_RECURSOS_DURACAO_SEG
        n = self._navio_estocado()
        n.porao.consumir("polvora", 999.0)
        n.atualizar_moral(dt=0.1)
        assert n.moral_atual <= MORAL_CRASH_RECURSOS_TETO
        # avança em ticks normais (0.5s, como o jogo real) além da duração do travamento
        tempo_restante = MORAL_CRASH_RECURSOS_DURACAO_SEG + 2.0
        while tempo_restante > 0:
            n.atualizar_moral(dt=0.5)
            tempo_restante -= 0.5
        assert n.moral_lock_restante == 0.0
        assert n.moral_atual > MORAL_CRASH_RECURSOS_TETO

    def test_dispara_de_novo_apos_reabastecer_e_zerar(self):
        n = self._navio_estocado()
        n.porao.consumir("bolas", 999.0)
        n.atualizar_moral(dt=0.1)
        primeiro_disparo = n.moral_lock_restante
        assert primeiro_disparo > 0.0

        n.porao.adicionar("bolas", 5.0)
        n.atualizar_moral(dt=0.1)  # recurso voltou a existir, limpa o estado
        n.porao.consumir("bolas", 999.0)
        n.atualizar_moral(dt=0.1)
        assert n.moral_lock_restante > 0.0

    def test_porao_vazio_desde_o_inicio_nao_dispara_no_primeiro_tick(self):
        n = Navio("Teste", x=0, y=0, heading=0)  # porao_capacidade=0 (vazio)
        n.moral_atual = 100.0
        n.atualizar_moral(dt=0.1)
        assert n.moral_lock_restante == 0.0
