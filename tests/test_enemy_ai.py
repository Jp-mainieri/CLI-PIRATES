"""Testes para pirates/ai/enemy.py (IA do inimigo e modo fuga)."""

import pytest
from pirates.core.state import Estado
from pirates.ai.enemy import (
    atualizar_estado_fuga, atualizar_ia_tripulacao, atualizar_ia_movimento,
)
from pirates.core.combat import dentro_do_arco
from pirates.world.entities import Ilha
from pirates.constants import (
    IA_DIST_APROXIMAR, IA_DIST_AFASTAR, IA_DIST_HISTERESE,
)


def _estado(tipo="brigantim"):
    return Estado(tipo_navio=tipo)


class TestAtualizarEstadoFuga:
    def test_entra_em_fuga_quando_moral_baixa(self):
        e = _estado()
        e.inimigo.moral_atual = 0.0
        e.ia_limiar_fuga_entrada = 20.0
        e.ia_limiar_fuga_saida = 40.0
        atualizar_estado_fuga(e)
        assert e.inimigo_em_fuga is True

    def test_nao_entra_em_fuga_com_moral_alta(self):
        e = _estado()
        e.inimigo.moral_atual = 80.0
        e.ia_limiar_fuga_entrada = 20.0
        atualizar_estado_fuga(e)
        assert e.inimigo_em_fuga is False

    def test_sai_da_fuga_quando_moral_recupera(self):
        e = _estado()
        e.inimigo_em_fuga = True
        e.inimigo.moral_atual = 60.0
        e.ia_limiar_fuga_saida = 50.0
        e.tempo_fuga_longe = 5.0
        atualizar_estado_fuga(e)
        assert e.inimigo_em_fuga is False
        assert e.tempo_fuga_longe == 0.0

    def test_permanece_em_fuga_entre_limiares(self):
        e = _estado()
        e.inimigo_em_fuga = True
        e.inimigo.moral_atual = 30.0
        e.ia_limiar_fuga_entrada = 15.0
        e.ia_limiar_fuga_saida = 45.0
        atualizar_estado_fuga(e)
        assert e.inimigo_em_fuga is True

    def test_log_registra_entrada_em_fuga(self):
        e = _estado()
        e.inimigo.moral_atual = 0.0
        e.ia_limiar_fuga_entrada = 20.0
        atualizar_estado_fuga(e)
        assert any("fugir" in msg.lower() for msg in e.log)

    def test_log_registra_saida_da_fuga(self):
        e = _estado()
        e.inimigo_em_fuga = True
        e.inimigo.moral_atual = 90.0
        e.ia_limiar_fuga_saida = 50.0
        atualizar_estado_fuga(e)
        assert any("volta" in msg.lower() for msg in e.log)


class TestAtualizarIaTripulacaoModoFuga:
    def test_fuga_desarma_todos_canhoes(self):
        e = _estado("brigantim")
        e.inimigo_em_fuga = True
        for lado in ('estibordo', 'bombordo'):
            for c in e.inimigo.canhoes[lado]:
                c.tripulantes = 2
                c.dist_alvo = 300.0
        atualizar_ia_tripulacao(e)
        for lado in ('estibordo', 'bombordo'):
            for c in e.inimigo.canhoes[lado]:
                assert c.tripulantes == 0
                assert c.dist_alvo is None

    def test_normal_pode_armar_canhoes(self):
        e = _estado("brigantim")
        e.inimigo_em_fuga = False
        atualizar_ia_tripulacao(e)
        total_armados = sum(
            1 for lado in ('estibordo', 'bombordo')
            for c in e.inimigo.canhoes[lado]
            if c.tripulantes > 0
        )
        assert total_armados >= 1


class TestBordadaAlternada:
    """A IA deve virar de bordo quando o costado apresentado descarrega."""

    def _em_faixa_de_circulo(self, e):
        """Posiciona o inimigo a 200m ao norte do jogador (faixa 150-280m)."""
        e.jogador.x, e.jogador.y = 0.0, 0.0
        e.inimigo.x, e.inimigo.y = 0.0, 200.0
        e.vento_direcao = 0.0
        e.ilhas_arena = []
        e.inimigo_em_fuga = False
        e.tempo = 100.0

    def _todos_canhoes(self, e):
        return [c for lado in ('estibordo', 'bombordo') for c in e.inimigo.canhoes[lado]]

    def test_estibordo_apresenta_o_costado_de_estibordo(self):
        e = _estado()
        self._em_faixa_de_circulo(e)
        e.ia_lado_bordada = 'estibordo'
        for c in self._todos_canhoes(e):
            c.proximo_tiro = 0.0  # todos carregados
        atualizar_ia_movimento(e, 0.5)
        e.inimigo.heading = e.inimigo.heading_alvo
        assert dentro_do_arco(e.inimigo, e.jogador, 'estibordo')[0]

    def test_bombordo_apresenta_o_costado_de_bombordo(self):
        e = _estado()
        self._em_faixa_de_circulo(e)
        e.ia_lado_bordada = 'bombordo'
        for c in self._todos_canhoes(e):
            c.proximo_tiro = 0.0
        atualizar_ia_movimento(e, 0.5)
        e.inimigo.heading = e.inimigo.heading_alvo
        assert dentro_do_arco(e.inimigo, e.jogador, 'bombordo')[0]

    def test_troca_de_bordo_quando_lado_atual_descarrega(self):
        e = _estado()
        self._em_faixa_de_circulo(e)
        e.ia_lado_bordada = 'estibordo'
        for c in e.inimigo.canhoes['estibordo']:
            c.proximo_tiro = e.tempo + 10.0  # em cooldown
        for c in e.inimigo.canhoes['bombordo']:
            c.proximo_tiro = 0.0             # carregados
        atualizar_ia_movimento(e, 0.5)
        assert e.ia_lado_bordada == 'bombordo'

    def test_mantem_bordo_enquanto_houver_carga(self):
        e = _estado()
        self._em_faixa_de_circulo(e)
        e.ia_lado_bordada = 'estibordo'
        for c in self._todos_canhoes(e):
            c.proximo_tiro = 0.0
        atualizar_ia_movimento(e, 0.5)
        assert e.ia_lado_bordada == 'estibordo'

    def test_nao_troca_se_os_dois_lados_estao_em_cooldown(self):
        e = _estado()
        self._em_faixa_de_circulo(e)
        e.ia_lado_bordada = 'estibordo'
        for c in self._todos_canhoes(e):
            c.proximo_tiro = e.tempo + 10.0
        atualizar_ia_movimento(e, 0.5)
        assert e.ia_lado_bordada == 'estibordo'


class TestGestaoDeVelas:
    """A IA deve içar/recolher velas conforme a fase do combate."""

    def _niveis(self, navio):
        return [s["nivel"] for s in navio.slots_vela if s["tipo"] is not None]

    def _preparar(self, e, dist):
        e.jogador.x, e.jogador.y = 0.0, 0.0
        e.inimigo.x, e.inimigo.y = 0.0, dist
        e.vento_direcao = 0.0
        e.ilhas_arena = []
        for s in e.inimigo.slots_vela:
            if s["tipo"] is not None:
                s["nivel"] = 0

    def test_velas_cheias_ao_aproximar(self):
        e = _estado()
        self._preparar(e, 500.0)
        atualizar_ia_movimento(e, 0.5)
        assert self._niveis(e.inimigo) == [2] * len(self._niveis(e.inimigo))

    def test_velas_cheias_ao_afastar(self):
        e = _estado()
        self._preparar(e, 100.0)
        atualizar_ia_movimento(e, 0.5)
        assert all(n == 2 for n in self._niveis(e.inimigo))

    def test_meio_pau_na_faixa_de_bordada(self):
        e = _estado()
        self._preparar(e, 200.0)
        atualizar_ia_movimento(e, 0.5)
        assert all(n == 1 for n in self._niveis(e.inimigo))

    def test_velas_cheias_em_fuga(self):
        e = _estado()
        self._preparar(e, 200.0)
        e.inimigo_em_fuga = True
        atualizar_ia_movimento(e, 0.5)
        assert all(n == 2 for n in self._niveis(e.inimigo))

    def test_slot_vazio_permanece_vazio(self):
        e = _estado()
        self._preparar(e, 500.0)
        for s in e.inimigo.slots_vela:
            s["tipo"] = None
            s["nivel"] = 0
        atualizar_ia_movimento(e, 0.5)
        assert all(s["nivel"] == 0 for s in e.inimigo.slots_vela)


class TestHistereseDeDistancia:
    """A IA não deve trocar de modo de manobra a cada tick nos limiares."""

    def _preparar(self, e, dist, modo):
        e.jogador.x, e.jogador.y = 0.0, 0.0
        e.inimigo.x, e.inimigo.y = 0.0, dist
        e.vento_direcao = 0.0
        e.ilhas_arena = []
        e.ia_modo_movimento = modo

    def test_entra_em_aproximar_acima_do_limiar(self):
        e = _estado()
        self._preparar(e, IA_DIST_APROXIMAR + 1, 'circular')
        atualizar_ia_movimento(e, 0.5)
        assert e.ia_modo_movimento == 'aproximar'

    def test_continua_aproximando_logo_abaixo_do_limiar(self):
        e = _estado()
        self._preparar(e, IA_DIST_APROXIMAR - 1, 'aproximar')
        atualizar_ia_movimento(e, 0.5)
        assert e.ia_modo_movimento == 'aproximar'

    def test_volta_a_circular_apos_cruzar_a_histerese(self):
        e = _estado()
        self._preparar(e, IA_DIST_APROXIMAR - IA_DIST_HISTERESE - 1, 'aproximar')
        atualizar_ia_movimento(e, 0.5)
        assert e.ia_modo_movimento == 'circular'

    def test_entra_em_afastar_abaixo_do_limiar(self):
        e = _estado()
        self._preparar(e, IA_DIST_AFASTAR - 1, 'circular')
        atualizar_ia_movimento(e, 0.5)
        assert e.ia_modo_movimento == 'afastar'

    def test_continua_afastando_logo_acima_do_limiar(self):
        e = _estado()
        self._preparar(e, IA_DIST_AFASTAR + 1, 'afastar')
        atualizar_ia_movimento(e, 0.5)
        assert e.ia_modo_movimento == 'afastar'

    def test_volta_a_circular_apos_afastar_o_bastante(self):
        e = _estado()
        self._preparar(e, IA_DIST_AFASTAR + IA_DIST_HISTERESE + 1, 'afastar')
        atualizar_ia_movimento(e, 0.5)
        assert e.ia_modo_movimento == 'circular'

    def test_parado_no_limiar_nao_oscila_entre_ticks(self):
        e = _estado()
        self._preparar(e, IA_DIST_APROXIMAR, 'circular')
        modos = []
        for _ in range(5):
            atualizar_ia_movimento(e, 0.5)
            modos.append(e.ia_modo_movimento)
        assert len(set(modos)) == 1


class TestHistereseDeIlha:
    """A evasão de ilha deve grudar até o navio se afastar de verdade."""

    def _ilha(self, x, y, raio):
        # a1..a3 = 0 => raio_maximo (property) == raio_base
        return Ilha(x=x, y=y, raio_base=raio,
                    a1=0.0, a2=0.0, a3=0.0, k1=2, k2=3, k3=4,
                    f1=0.0, f2=0.0, f3=0.0)

    def _preparar(self, e, dist_ilha):
        e.jogador.x, e.jogador.y = 0.0, 0.0
        e.inimigo.x, e.inimigo.y = 0.0, 200.0
        e.vento_direcao = 0.0
        e.ia_island_avoidance_mult = 2.0
        e.ilhas_arena = [self._ilha(0.0, 200.0 - dist_ilha, 50.0)]

    def test_dispara_evasao_dentro_do_raio(self):
        e = _estado()
        self._preparar(e, 90.0)  # < 50 * 2.0 = 100
        atualizar_ia_movimento(e, 0.5)
        assert e.ia_ilha_evadindo == 0

    def test_mantem_evasao_na_margem_de_histerese(self):
        e = _estado()
        self._preparar(e, 110.0)  # entre 100 e 100 * 1.25 = 125
        e.ia_ilha_evadindo = 0
        atualizar_ia_movimento(e, 0.5)
        assert e.ia_ilha_evadindo == 0

    def test_nao_dispara_na_margem_se_ainda_nao_evadia(self):
        e = _estado()
        self._preparar(e, 110.0)
        e.ia_ilha_evadindo = None
        atualizar_ia_movimento(e, 0.5)
        assert e.ia_ilha_evadindo is None

    def test_solta_a_evasao_alem_da_histerese(self):
        e = _estado()
        self._preparar(e, 130.0)  # > 125
        e.ia_ilha_evadindo = 0
        atualizar_ia_movimento(e, 0.5)
        assert e.ia_ilha_evadindo is None

    def test_sem_ilhas_nao_evade(self):
        e = _estado()
        self._preparar(e, 90.0)
        e.ilhas_arena = []
        atualizar_ia_movimento(e, 0.5)
        assert e.ia_ilha_evadindo is None
