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
from pirates.ai.enemy import (
    _tempo_giro_bordada, _escolher_rumo_fuga, _heading_no_angulo_vento_mais_proximo,
)
from pirates.core.vento import angulo_relativo_vento


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

    def _guarnecer(self, canhoes):
        """Um canhao so conta como pronto se tiver tripulacao efetiva."""
        for c in canhoes:
            c.tripulantes = 1
            c.efetivos = 1

    def test_estibordo_apresenta_o_costado_de_estibordo(self):
        e = _estado()
        self._em_faixa_de_circulo(e)
        e.ia_lado_bordada = 'estibordo'
        self._guarnecer(self._todos_canhoes(e))
        for c in self._todos_canhoes(e):
            c.proximo_tiro = 0.0  # todos carregados
        atualizar_ia_movimento(e, 0.5)
        e.inimigo.heading = e.inimigo.heading_alvo
        assert dentro_do_arco(e.inimigo, e.jogador, 'estibordo')[0]

    def test_bombordo_apresenta_o_costado_de_bombordo(self):
        e = _estado()
        self._em_faixa_de_circulo(e)
        e.ia_lado_bordada = 'bombordo'
        self._guarnecer(self._todos_canhoes(e))
        for c in self._todos_canhoes(e):
            c.proximo_tiro = 0.0
        atualizar_ia_movimento(e, 0.5)
        e.inimigo.heading = e.inimigo.heading_alvo
        assert dentro_do_arco(e.inimigo, e.jogador, 'bombordo')[0]

    def test_troca_de_bordo_quando_lado_atual_descarrega(self):
        e = _estado()
        self._em_faixa_de_circulo(e)
        e.ia_lado_bordada = 'estibordo'
        # Os dois bordos guarnecidos: so assim trocar de costado faz sentido,
        # ja que um costado sem gente nao recarrega.
        self._guarnecer(self._todos_canhoes(e))
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
        self._guarnecer(self._todos_canhoes(e))
        for c in self._todos_canhoes(e):
            c.proximo_tiro = 0.0
        atualizar_ia_movimento(e, 0.5)
        assert e.ia_lado_bordada == 'estibordo'

    def test_nao_troca_se_os_dois_lados_estao_em_cooldown(self):
        e = _estado()
        self._em_faixa_de_circulo(e)
        e.ia_lado_bordada = 'estibordo'
        self._guarnecer(self._todos_canhoes(e))
        for c in self._todos_canhoes(e):
            c.proximo_tiro = e.tempo + 10.0
        atualizar_ia_movimento(e, 0.5)
        assert e.ia_lado_bordada == 'estibordo'


    def test_nao_troca_para_bordo_sem_tripulacao(self):
        """Costado sem gente nao recarrega, entao trocar para la e ilusao."""
        e = _estado()
        self._em_faixa_de_circulo(e)
        e.ia_lado_bordada = 'estibordo'
        self._guarnecer(e.inimigo.canhoes['estibordo'])
        for c in e.inimigo.canhoes['estibordo']:
            c.proximo_tiro = e.tempo + 10.0   # descarregado
        for c in e.inimigo.canhoes['bombordo']:
            c.tripulantes = c.efetivos = 0    # ninguem la
            c.proximo_tiro = 0.0              # "carregado" no papel
        atualizar_ia_movimento(e, 0.5)
        assert e.ia_lado_bordada == 'estibordo'

    def test_nao_troca_por_um_tripulante_solto_do_outro_lado(self):
        """A sobra de tripulacao no bordo oposto nao justifica atravessar."""
        e = _estado("galeao")
        self._em_faixa_de_circulo(e)
        e.ia_lado_bordada = 'estibordo'
        self._guarnecer(e.inimigo.canhoes['estibordo'])
        for c in e.inimigo.canhoes['estibordo']:
            c.proximo_tiro = e.tempo + 10.0
        for c in e.inimigo.canhoes['bombordo']:
            c.tripulantes = c.efetivos = 0
            c.proximo_tiro = e.tempo + 10.0
        solto = e.inimigo.canhoes['bombordo'][0]
        solto.tripulantes = solto.efetivos = 1
        solto.proximo_tiro = 0.0
        atualizar_ia_movimento(e, 0.5)
        assert e.ia_lado_bordada == 'estibordo'

    def test_nao_troca_se_o_giro_custa_mais_que_a_recarga(self):
        """Virar 180° deixa os dois bordos sem linha de tiro no caminho."""
        e = _estado()
        self._em_faixa_de_circulo(e)
        e.ia_lado_bordada = 'estibordo'
        self._guarnecer(self._todos_canhoes(e))
        espera = _tempo_giro_bordada(e) / 2.0
        for c in e.inimigo.canhoes['estibordo']:
            c.proximo_tiro = e.tempo + espera   # recarrega antes do giro acabar
        for c in e.inimigo.canhoes['bombordo']:
            c.proximo_tiro = 0.0
        atualizar_ia_movimento(e, 0.5)
        assert e.ia_lado_bordada == 'estibordo'


class TestManobraMantemOArco:
    """Aproximar e afastar não podem custar a linha de tiro.

    Com o arco estreito, apontar a proa (ou a popa) no jogador para manobrar
    tira o alvo do arco e obriga a IA a girar de volta antes de atirar.
    """

    def _preparar(self, e, dist, lado):
        e.jogador.x, e.jogador.y = 0.0, 0.0
        e.inimigo.x, e.inimigo.y = 0.0, dist
        e.vento_direcao = 0.0   # todos os rumos abaixo ficam fora da zona morta
        e.ilhas_arena = []
        e.inimigo_em_fuga = False
        e.tempo = 100.0
        e.ia_lado_bordada = lado
        for c in (c for l in ('estibordo', 'bombordo') for c in e.inimigo.canhoes[l]):
            c.tripulantes = c.efetivos = 1
            c.proximo_tiro = 0.0

    @pytest.mark.parametrize("lado", ['estibordo', 'bombordo'])
    def test_aproximando_dentro_do_alcance_mantem_o_alvo_no_arco(self, lado):
        e = _estado()
        dist = min(
            IA_DIST_APROXIMAR + 20.0,
            e.inimigo.alcance_canhao_efetivo() - 1.0,
        )
        self._preparar(e, dist, lado)
        atualizar_ia_movimento(e, 0.5)
        e.inimigo.heading = e.inimigo.heading_alvo
        assert e.ia_modo_movimento == 'aproximar'
        assert dentro_do_arco(e.inimigo, e.jogador, lado)[0]

    @pytest.mark.parametrize("lado", ['estibordo', 'bombordo'])
    def test_afastando_mantem_o_alvo_no_arco(self, lado):
        e = _estado()
        self._preparar(e, IA_DIST_AFASTAR - 20.0, lado)
        atualizar_ia_movimento(e, 0.5)
        e.inimigo.heading = e.inimigo.heading_alvo
        assert e.ia_modo_movimento == 'afastar'
        assert dentro_do_arco(e.inimigo, e.jogador, lado)[0]

    def test_fora_de_alcance_persegue_em_rumo_direto(self):
        """Sem tiro possível não há bordada a preservar: fecha pelo curto."""
        e = _estado()
        self._preparar(e, e.inimigo.alcance_canhao_efetivo() + 200.0, 'estibordo')
        atualizar_ia_movimento(e, 0.5)
        # Inimigo ao norte do jogador: rumo direto é 180°.
        assert abs(e.inimigo.heading_alvo - 180.0) < 1.0

    def test_afastando_abre_distancia_de_verdade(self):
        """A diagonal ainda precisa ter componente de afastamento."""
        import math
        e = _estado()
        self._preparar(e, IA_DIST_AFASTAR - 20.0, 'estibordo')
        atualizar_ia_movimento(e, 0.5)
        rumo_ao_jogador = 180.0
        rel = abs((e.inimigo.heading_alvo - rumo_ao_jogador + 180) % 360 - 180)
        assert math.cos(math.radians(rel)) < 0.0   # rumo se afasta do jogador

    def test_aproximando_fecha_distancia_de_verdade(self):
        import math
        e = _estado()
        dist = min(
            IA_DIST_APROXIMAR + 20.0,
            e.inimigo.alcance_canhao_efetivo() - 1.0,
        )
        self._preparar(e, dist, 'estibordo')
        atualizar_ia_movimento(e, 0.5)
        rel = abs((e.inimigo.heading_alvo - 180.0 + 180) % 360 - 180)
        assert math.cos(math.radians(rel)) > 0.0   # rumo se aproxima


class TestFugaEscolheRumoPeloVento:
    """A fuga deve escolher bolina ou popa pela vantagem de velocidade real
    sobre o perseguidor, não sempre "a favor do vento"."""

    def _preparar(self, e, slots_inimigo, slots_jogador):
        e.jogador.x, e.jogador.y = 0.0, 0.0
        e.inimigo.x, e.inimigo.y = 0.0, 200.0  # inimigo ao norte do jogador
        e.vento_direcao = 0.0
        e.inimigo.slots_vela = slots_inimigo
        e.jogador.slots_vela = slots_jogador

    def _slot(self, tipo, nivel=2):
        return [{"local": "principal", "tipo": tipo, "nivel": nivel}]

    def test_prefere_bolina_quando_e_o_ponto_forte_do_fugitivo(self):
        """Ex.: chalupa (latina, forte em bolina) fugindo de galeão (quadrada,
        forte em popa) — deve fugir contra o vento, não a favor."""
        e = _estado()
        self._preparar(e, self._slot("latina"), self._slot("quadrada"))
        heading = _escolher_rumo_fuga(e)
        ang = angulo_relativo_vento(heading, e.vento_direcao)
        assert ang < 90.0   # bolina, não popa

    def test_prefere_popa_quando_e_o_ponto_forte_do_fugitivo(self):
        """O inverso do caso acima: quem tem a vela de popa forte foge a
        favor do vento."""
        e = _estado()
        self._preparar(e, self._slot("quadrada"), self._slot("latina"))
        heading = _escolher_rumo_fuga(e)
        ang = angulo_relativo_vento(heading, e.vento_direcao)
        assert ang > 90.0   # popa, não bolina

    def test_empate_desempata_para_popa(self):
        """Mesmo tipo de vela nos dois lados: a razão de vantagem é 1.0 nos
        dois pontos, e o desempate favorece popa (soma o empuxo constante
        do vento)."""
        e = _estado()
        self._preparar(e, self._slot("latina"), self._slot("latina"))
        heading = _escolher_rumo_fuga(e)
        ang = angulo_relativo_vento(heading, e.vento_direcao)
        assert ang > 90.0

    def test_heading_escolhido_ainda_afasta_do_perseguidor(self):
        """Dos dois headings possíveis pro ângulo de vento escolhido, fica
        com o que mais se aproxima do rumo direto de fuga (oposto ao
        perseguidor), não o espelhado."""
        import math
        e = _estado()
        self._preparar(e, self._slot("latina"), self._slot("quadrada"))
        heading = _escolher_rumo_fuga(e)
        # Inimigo ao norte do jogador: fugir é seguir mais para o norte (rumo 0).
        rel = abs((heading - 0.0 + 180) % 360 - 180)
        assert math.cos(math.radians(rel)) > 0.0

    def test_atualizar_ia_movimento_usa_o_rumo_de_fuga_escolhido(self):
        e = _estado()
        self._preparar(e, self._slot("latina"), self._slot("quadrada"))
        e.inimigo_em_fuga = True
        e.ilhas_arena = []
        esperado = _escolher_rumo_fuga(e)
        atualizar_ia_movimento(e, 0.5)
        assert abs((e.inimigo.heading_alvo - esperado + 180) % 360 - 180) < 0.1


class TestHeadingNoAnguloVentoMaisProximo:
    def test_escolhe_o_lado_mais_proximo_da_referencia(self):
        # Vento vindo do norte (0°); ângulo relativo de 90° dá dois
        # candidatos: 90° (leste) e 270° (oeste). Referência a leste.
        h = _heading_no_angulo_vento_mais_proximo(0.0, 90.0, 100.0)
        assert h == 90.0

    def test_escolhe_o_outro_lado_quando_mais_proximo(self):
        h = _heading_no_angulo_vento_mais_proximo(0.0, 90.0, 260.0)
        assert h == 270.0


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
