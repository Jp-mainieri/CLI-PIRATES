"""Testes para pirates/core/ship.py."""

import pytest
from pirates.core.ship import Navio, Canhao, resolver_canhao


class TestCanhao:
    def test_label_estibordo(self):
        c = Canhao('estibordo', 1)
        assert c.label == 'E1'

    def test_label_bombordo(self):
        c = Canhao('bombordo', 3)
        assert c.label == 'B3'

    def test_operacional_com_hp(self):
        c = Canhao('estibordo', 1)
        assert c.operacional() is True

    def test_nao_operacional_sem_hp(self):
        c = Canhao('estibordo', 1)
        c.hp = 0
        assert c.operacional() is False

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
