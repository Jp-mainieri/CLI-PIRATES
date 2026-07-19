"""Testes para IA reagindo ao vento em pirates/ai/enemy.py (doc08_vento.md seção 8)."""

import pytest

from pirates.core.state import Estado
from pirates.core.vento import angulo_relativo_vento
from pirates.ai.enemy import _ajustar_heading_vento, atualizar_ia_movimento
from pirates.world.entities import Ilha
from pirates.constants import (
    IA_VENTO_CORRECAO_MAX_GRAUS, IA_VENTO_CORRECAO_MAX_FUGA_GRAUS,
)


def _estado(tipo="brigantim"):
    return Estado(tipo_navio=tipo)


def _diff_angular(a: float, b: float) -> float:
    return abs((a - b + 540) % 360 - 180)


class TestAjustarHeadingVento:
    def test_sem_correcao_fora_da_zona_morta(self):
        # heading 90 com vento vindo de 0 -> angulo relativo 90 (fora da zona morta)
        resultado = _ajustar_heading_vento(90.0, 0.0, correcao_max=40.0)
        assert resultado == pytest.approx(90.0)

    def test_correcao_melhora_angulo_relativo(self):
        # heading 0 com vento de 0 -> angulo relativo 0 (bem no meio da zona morta)
        original_ang = angulo_relativo_vento(0.0, 0.0)
        resultado = _ajustar_heading_vento(0.0, 0.0, correcao_max=40.0)
        novo_ang = angulo_relativo_vento(resultado, 0.0)
        assert novo_ang > original_ang

    def test_correcao_nao_excede_max(self):
        resultado = _ajustar_heading_vento(0.0, 0.0, correcao_max=40.0)
        assert _diff_angular(resultado, 0.0) <= 40.0 + 1e-9

    def test_fuga_tira_completamente_da_zona_morta(self):
        # com correcao normal (40) nao sai (precisa de 50 pra chegar a 50deg),
        # com fuga (70) sai completamente.
        resultado_normal = _ajustar_heading_vento(
            0.0, 0.0, correcao_max=IA_VENTO_CORRECAO_MAX_GRAUS
        )
        resultado_fuga = _ajustar_heading_vento(
            0.0, 0.0, correcao_max=IA_VENTO_CORRECAO_MAX_FUGA_GRAUS
        )
        assert angulo_relativo_vento(resultado_normal, 0.0) <= 45.0
        assert angulo_relativo_vento(resultado_fuga, 0.0) > 45.0


class TestIntegracaoEvasaoIlhaVenceVento:
    def test_ilha_proxima_sobrepoe_correcao_de_vento(self):
        e = _estado()
        e.inimigo.x, e.inimigo.y = 100.0, 100.0
        e.jogador.x, e.jogador.y = 500.0, 500.0
        e.vento_direcao = 0.0

        ilha = Ilha(
            x=110.0, y=110.0, raio_base=50.0,
            a1=0.0, a2=0.0, a3=0.0,
            k1=1, k2=2, k3=3,
            f1=0.0, f2=0.0, f3=0.0,
        )
        e.ilhas_arena = [ilha]
        e.ia_island_avoidance_mult = 3.0

        atualizar_ia_movimento(e, dt=0.5)

        import math
        idx = e.inimigo.x - ilha.x
        idy = e.inimigo.y - ilha.y
        esperado = math.degrees(math.atan2(idx, idy)) % 360
        assert e.inimigo.heading_alvo == pytest.approx(esperado)
