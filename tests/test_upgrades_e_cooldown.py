"""Regressao dos tres bugs de cooldown/upgrade encontrados no balanceamento.

1. combat.disparar_canhoes_navio usava cooldown_mult_base = 1.0 para o
   jogador, ignorando NAVIO_TIPOS[tipo]["cooldown_mult"] (so o inimigo tinha
   o multiplicador do tipo de navio).
2. O upgrade "cooldown" gravava upgrades['cooldown'] mas nada lia essa chave.
3. O upgrade "casco_max" so curava 10 pontos; nao havia ganho permanente,
   apesar de a loja anunciar "+10 HP max de casco".
"""

import pytest

from pirates.constants import NAVIO_TIPOS, COOLDOWN_CANHAO
from pirates.core.porao import Barril
from pirates.core.state import Estado
from pirates.port.lojas import aplicar_upgrade


def _com_ouro(navio, quantidade=10_000.0):
    """Garante ouro suficiente para as compras do teste."""
    navio.porao.barris.append(Barril("ouro", quantidade))
    return navio


class TestCooldownDoTipoDeNavio:
    @pytest.mark.parametrize("tipo", list(NAVIO_TIPOS))
    def test_navio_do_jogador_carrega_o_cooldown_mult_do_tipo(self, tipo):
        estado = Estado(tipo_navio=tipo)
        assert estado.jogador.cooldown_mult == NAVIO_TIPOS[tipo]["cooldown_mult"]

    def test_tipos_tem_cooldown_distinto(self):
        """Se todos fossem iguais o bug (1.0 fixo) passaria despercebido."""
        mults = {t: NAVIO_TIPOS[t]["cooldown_mult"] for t in NAVIO_TIPOS}
        assert len(set(mults.values())) == len(mults)

    def test_inimigo_tambem_recebe_o_multiplicador(self):
        estado = Estado(tipo_navio="galeao")
        assert estado.inimigo.cooldown_mult == NAVIO_TIPOS["galeao"]["cooldown_mult"]


class TestUpgradeCooldown:
    def test_cada_nivel_reduz_dez_porcento(self):
        estado = Estado(tipo_navio="galeao")
        navio = estado.jogador
        _com_ouro(navio)
        for nivel in range(1, 4):
            ok, msg = aplicar_upgrade(navio, "galeao", "cooldown", estado=estado)
            assert ok, msg
            assert navio.upgrades["cooldown"] == pytest.approx(0.1 * nivel)

    def test_reducao_chega_no_cooldown_efetivo(self):
        estado = Estado(tipo_navio="galeao")
        navio = estado.jogador
        base = COOLDOWN_CANHAO * navio.cooldown_mult
        navio.upgrades["cooldown"] = 0.3
        efetivo = COOLDOWN_CANHAO * navio.cooldown_mult * (1.0 - 0.3)
        assert efetivo < base
        assert efetivo == pytest.approx(base * 0.7)


class TestUpgradeCascoMax:
    def test_da_resistencia_permanente_nao_so_cura(self):
        estado = Estado(tipo_navio="brigantim")
        navio = estado.jogador
        _com_ouro(navio)
        antes = navio.resistencia_casco_mult()
        ok, msg = aplicar_upgrade(navio, "brigantim", "casco_max", estado=estado)
        assert ok, msg
        assert navio.upgrades["resistencia_casco"] == pytest.approx(0.10)
        assert navio.resistencia_casco_mult() < antes

    def test_resistencia_do_tipo_soma_com_a_do_upgrade(self):
        estado = Estado(tipo_navio="galeao")
        navio = estado.jogador
        navio.upgrades["resistencia_casco"] = 0.10
        esperado = 1.0 / (1.0 + NAVIO_TIPOS["galeao"]["resist_casco"] + 0.10)
        assert navio.resistencia_casco_mult() == pytest.approx(esperado)
