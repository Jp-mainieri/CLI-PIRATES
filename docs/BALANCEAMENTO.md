# Balanceamento

Como o equilíbrio do CLI PIRATES está montado, como medir uma mudança antes de fazê-la, e o que está aberto.

Este documento existe porque equilíbrio de jogo é fácil de quebrar por acidente e difícil de perceber que quebrou. Várias das lições abaixo foram aprendidas do jeito ruim.

---

## 1. Onde mexer

**`pirates/constants.py` é o painel de controle.** Quase todo número que define equilíbrio está lá, com docstring. Se você quer mudar o jogo, comece lendo aquele arquivo de ponta a ponta — leva uns quinze minutos e evita reescrever algo que já é um parâmetro.

Muitas constantes estão marcadas como *"Placeholder – não calibrado"*. Isso é honesto: elas foram chutadas para o sistema funcionar, nunca ajustadas com dados. São as melhores candidatas a mexer.

### Constantes acopladas

Algumas constantes **não são independentes**, e mexer numa sem olhar a outra reintroduz bug. Onde isso acontece há um comentário no código dizendo qual é a relação, e um teste travando.

| Grupo | Invariante | Travado por |
|---|---|---|
| Trânsito de tripulação | `MESMO_BORDO` e `BORDO_OPOSTO` ≤ 2 × `TAREFA_DIFERENTE` | `TestDesigualdadeTriangular` |
| Zoom vs. visão | `ZOOM_NIVEIS[-1]` ≤ `MUNDO_VISAO_INIMIGOS` | `test_zoom_maximo_nao_ultrapassa_a_visao_do_capitao` |
| Fuga vs. gatilho | `ALCANCE_FUGA_ESCAPE` > `MUNDO_GATILHO_COMBATE` | `test_limiar_fica_acima_do_gatilho_de_combate` |

Se um desses testes falhar depois de você recalibrar, **leia a mensagem** — ela diz qual regra foi quebrada e por quê ela existe. Não relaxe o teste sem entender.

---

## 2. Como medir uma mudança

Equilíbrio não se avalia por intuição. O jogo é determinístico o suficiente para simular.

### O básico

```python
from pirates.core.simulation import atualizar_simulacao
from pirates.constants import SIM_TICK

while t < duracao and estado.fim is None:
    estado.jogador.heading_alvo = <sua politica>
    atualizar_simulacao(estado, SIM_TICK)   # UMA chamada por tick
    t += SIM_TICK
```

### Quatro armadilhas, todas já pisadas

**1. `atualizar_simulacao` já faz tudo.** Ela chama `atualizar_ia_movimento` e `atualizar_movimento` dos dois navios internamente. Chamar essas funções à mão *e depois* `atualizar_simulacao` move cada navio duas vezes por tick e produz números que parecem plausíveis e estão errados.

**2. Rumo fixo não é o jogador.** O vento gira (`atualizar_vento`), então um rumo escolhido no t=0 vai ficando ruim. Uma política realista recalcula a cada tick. A que uso para fuga maximiza distância ganha por segundo:

```python
ganho(h) = velocidade_no_angulo(h) * cos(h - rumo_de_fuga)
```

Maximizar só a velocidade manda o navio para o melhor ponto de vela **mesmo que seja na direção do perseguidor**. Maximizar só a direção joga o navio para um ângulo de vento ruim. É o produto que importa.

**3. Uma geometria não é amostra.** Vento e posição relativa mudam completamente o resultado. Meço sobre 16 combinações (4 direções de vento × 4 posições do inimigo) e reporto a fração, não um caso.

**4. Vento constante infla os números.** Com vento fixo a fuga parece bem mais fácil do que é. Use o loop real, que faz o vento derivar.

### O que reportar

Diga o que mediu **e o que não mediu**. Uma mudança de velocidade que foi validada em fuga mas não em duelo direto é exatamente isso — e a mensagem de commit deve dizer.

---

## 3. Os sistemas, e o que já foi medido

### 3.1 Vento e velas

Velocidade emerge de um equilíbrio, sem teto artificial:

```
empuxo = vmax_base × (1 + Σbonus_fixo) × Σeficiencia × fator_intensidade
vmax   = √( empuxo / (K_ARRASTO_CASCO × area_casco) ) × fator_dano
```

Três consequências não óbvias:

- **A raiz quadrada achata tudo.** Dobrar o empuxo dá +41% de velocidade, não +100%.
- **Eficiência tem um segundo emprego.** A aceleração é `ACEL_VEL_SEG × dt × eficiencia`, mas a desaceleração é `ACEL_VEL_SEG × dt` sem multiplicador. Eficiência baixa não só limita o teto — ela faz o navio demorar muito mais para chegar lá, enquanto frear continua rápido.
- **`fator_dano` é multiplicativo:** `(vela/100) × (mastro/100)`. Vela a 70% + mastro a 70% = **49%** da velocidade. Dano de rigging é brutal.

**As velas** (eficiência por ângulo relativo ao vento):

| vela | 0° | 45° | 90° | 135° | 180° | b_fixo | b_curva |
|---|---|---|---|---|---|---|---|
| quadrada | 0,00 | 0,07 | 0,45 | 0,88 | 1,00 | 0,40 | 0,00 |
| latina | **1,30** | 1,38 | 1,18 | 0,80 | 0,70 | 0,20 | 0,10 |
| carangueja | 0,70 | 0,80 | 0,95 | 0,90 | 0,80 | 0,25 | 0,15 |
| estai | 0,60 | 0,70 | 0,90 | 0,93 | 0,85 | 0,10 | **0,35** |
| topo_quadrada | 0,00 | 0,00 | 0,20 | 0,82 | **1,25** | 0,15 | 0,00 |
| vela_de_asa | 0,00 | 0,00 | 0,00 | 1,00 | **2,00** | 0,05 | 0,00 |

> **`estai` é caso especial.** `eficiencia_vento_bruta` e `bonus_fixo_vela_bruto` pulam slots de estai — os valores de eficiência dele **nunca são lidos**. Ele só entra em `bonus_curva`. É a vela de manobra pura.

**As somas não têm teto.** Este é o fato estrutural mais importante do sistema:

| navio | Σef@0° | Σef@90° | Σef@180° |
|---|---|---|---|
| chalupa | 1,30 | 1,18 | 0,70 |
| brigantim | 1,40 | 1,90 | 1,60 |
| galeão | 0,70 | 2,30 | **3,80** |

Mais velas = mais empuxo, linearmente, para sempre. O arrasto só cresce com `area_casco`, e a raiz quadrada não fecha a conta. **Qualquer recalibração de vela precisa levar isso em conta**, senão o navio com mais slots vence em todos os ângulos.

Foi exatamente o que acontecia: o galeão somava **1,25** contra o vento (3 quadradas + carangueja + 2 topo) contra 0,85 da chalupa. Três velas ruins somadas batiam uma vela boa, e o navio de aparelho redondo era *melhor à bolina* que o de aparelho latino. A calibração atual zerou quadrada e topo na bolina e reforçou a latina, para que quantidade não engula qualidade.

**Resultado** (velas cheias, vento pleno):

| ângulo | chalupa | brigantim | galeão |
|---|---|---|---|
| 0° | **9,03** | 8,96 | 7,03 |
| 30° | 9,12 | **9,17** | 7,55 |
| 60° | 9,46 | **9,97** | 9,36 |
| 90° | 8,59 | 10,43 | **12,74** |
| 180° | 6,63 | 9,57 | **16,38** |

Cada navio manda numa faixa. É essa a intenção de design a preservar.

**Contrapesos que já existem** contra rigs grandes, e que costumam ser esquecidos:

- **Deriva lateral** = `0,05 × intensidade × num_velas × sin(ângulo)`. A 90° com 12 nós: chalupa 0,6, brigantim 1,8, galeão **4,2**. E cascos pesados corrigem a deriva mais devagar (`÷ peso`).
- **Empuxo constante** = `C_ARRASTO × área × i² / peso`. Por unidade de massa a chalupa leva mais empurrão — e como ele sempre empurra a favor do vento, **atrapalha quem navega à bolina**. É um contrapeso invertido.

### 3.2 Fuga

Requisitos: ficar acima de `ALCANCE_FUGA_ESCAPE` (800 m) por `TEMPO_FUGA_ESCAPE_SEG` (15 s), com o inimigo não estando ele mesmo em fuga. O timer **zera** a cada tick abaixo do limiar.

**O ciclo da IA.** A IA tem um atrator em `alcance_canhao_efetivo()` (550 m):

- **acima de 550 m** → persegue em linha reta, velas cheias
- **abaixo de 550 m** → troca para bordada (`rumo ± 60..120°`) e para de fechar

Isso cria um ciclo-limite. Perfil medido, brigantim fugindo de chalupa a partir de 550 m:

```
t=  0s  549m     banda da IA
t= 20s  411m     IA em bordada, jogador abre
t= 80s  587m     cruza 550m, IA reengaja em linha reta
t=160s  851m     pico
t=180s  712m     desaba
t=300s  249m     e recomeca
```

O pico do ciclo em confronto de velocidade parelha é **790–850 m**. O limiar era 900 m — acima do pico, o que tornava a fuga **matematicamente impossível** em 7 dos 9 confrontos partindo do gatilho de combate. Hoje é 800 m.

**Taxas de fuga atuais**, 16 geometrias, saindo de 750 m:

| você | inimigo | taxa |
|---|---|---|
| chalupa | galeão | 4/16 |
| brigantim | galeão | 4/16 |
| galeão | galeão | 8/16 |
| brigantim | chalupa | 16/16 |
| chalupa | brigantim | 3/16 |
| chalupa | chalupa | 4/16 |
| brigantim | brigantim | 3/16 |

**A saída que sempre funciona:** danificar vela e mastro do perseguidor. A 75% nos dois, a fuga fica viável em todos os confrontos (58–102 s). É uma mecânica boa — "para fugir, primeiro machuque o rigging" — mas **nada no jogo comunica isso**.

### 3.3 Trânsito de tripulação

Tripulante em trânsito não trabalha e o canhão dele não recarrega (`armado()` olha `efetivos`, não `tripulantes`).

| de → para | custo |
|---|---|
| canhão → canhão, mesmo bordo | 6,0 s |
| canhão → canhão, bordo oposto | 8,0 s |
| troca de tipo de tarefa | 4,0 s |
| reparo → reparo, outra parte | 0,0 s |

O custo é medido a partir do **último posto onde a pessoa efetivamente trabalhou**, não do posto atual — é isso que impede estacionar tripulantes no convés e depois alocá-los no bordo oposto de graça.

> **Lição.** `TAREFA_DIFERENTE` já foi 3,0 s. Com `BORDO_OPOSTO` em 8,0, isso violava a desigualdade triangular: trocar de bordo passando pelo reparo custava 3+3 = **6 s** em vez de 8. Chegar mais rápido parando no meio do caminho. O bug entrou num commit de balanceamento que trocou `MESMO_BORDO` e `TAREFA_DIFERENTE` de lugar — ninguém percebeu porque nenhum teste olhava a relação entre elas. Hoje olha.

### 3.4 Giro e troca de bordo

| navio | giro real | 180° | recarga | razão |
|---|---|---|---|---|
| chalupa | 65,2°/s | 2,8 s | 6,6 s | 42% |
| brigantim | 41,2°/s | 4,4 s | 13,2 s | 33% |
| galeão | 18,0°/s | 10,0 s | 16,8 s | 60% |

> **Cuidado com essa tabela.** A razão giro/recarga parece mostrar o brigantim como o mais barato para manobrar, e não é bem isso. O custo real de trocar de bordo é `max(giro, trânsito)` — a travessia do convés acontece **durante** a manobra. Quem guarnece um bordo só paga no mínimo os 8 s de trânsito, independente do leme. **Giro acima de 22,5°/s é invisível para troca de bordo.**

O que de fato determina o custo é a aritmética de tripulação:

| navio | tripulação | precisa p/ 2 bordos | consegue na base? | com upgrade? | custo real |
|---|---|---|---|---|---|
| chalupa | 2 | 2 | **sim** | sim | 2,8 s |
| brigantim | 3 | 4 | não | **sim** (120 ouro) | 4,4 s ou 8,0 s |
| galeão | 4 | 6 | não | **não** (teto é 5) | 10,0 s |

A chalupa tem bordo duplo de graça desde o início. O brigantim compra o direito com `tripulante_extra`, e fica com **zero** de reserva para bomba e reparo. O galeão nunca consegue: precisaria de 6 e o teto de `tripulante_extra` é 1 em todos os navios.

Guarnecer os dois bordos não é vantagem grátis — é trocar controle de avarias por cadência. Mas hoje é **aritmética**, não escolha: dois navios não têm a opção.

---

## 4. Balanceamentos possíveis

Ideias medidas ou identificadas, nenhuma aplicada. Em ordem aproximada de valor por risco.

### Baixo risco

**Comunicar o dano de rigging.** Fugir funciona se você atirar nas velas do perseguidor, e nada diz isso ao jogador. Uma linha no vigia ("as velas dele estão em farrapos") ou uma dica na ajuda resolveria sem tocar em número nenhum.

**`min_crew_canhao` por tipo de navio.** Hoje é 1 em todos. Subir para 2 no galeão o tornaria o único com bordada pesada de verdade, e manteria bordo duplo fora de alcance dele por **escolha de design**, não por aritmética que ninguém enxerga.

**Teto de `tripulante_extra` por tipo.** Também 1 em todos. Permitir 2 ou 3 no galeão daria a ele a opção de bordo duplo — pagando caro, como deve ser.

### Risco médio

**Espelho de chalupa e de galeão na fuga.** Os dois seguem inviáveis (pico abaixo do limiar). Resolver exige mexer em velocidade ou fazer o timer decair em vez de zerar.

**Timer de fuga com decaimento.** Hoje um único tick abaixo de 800 m apaga 15 segundos de progresso. Decair (perdendo, digamos, ao dobro da velocidade com que ganha) perdoaria uma aproximação momentânea sem tornar a fuga trivial.

**A razão giro/recarga do brigantim.** É a mais baixa dos três (33%), mas só no build com `tripulante_extra`. Medido: baixar `giro_graus_seg` de 25 para 19 **não muda taxa de fuga nenhuma** — o efeito ficaria em mira, esquiva e na decisão de bordada da IA.

### Risco alto

**Somas sem teto.** A raiz do desequilíbrio de velocidade é `eficiencia_vento_bruta` e `bonus_fixo_vela_bruto` somarem linearmente sem limite. Retornos decrescentes consertariam a causa em vez do sintoma — e mexeriam em velocidade, economia, progressão de navios e IA de uma vez só.

**O galeão a favor do vento.** 16,38 contra 9,57 do brigantim. Medido: cortar velas do galeão **não muda taxa de fuga alguma** (as fugas bem-sucedidas acontecem à bolina). É decisão de identidade, não de fuga.

---

## 5. O que nunca foi medido

Honestidade sobre os buracos:

- **Quem vence um duelo direto.** Nenhuma medição de combate navio-contra-navio até agora, só de fuga. Depois da recalibração de velas, as velocidades mudaram bastante e o equilíbrio de combate pode ter se mexido sem ninguém notar.
- **Se o galeão vale os 300 de ouro.** Ele ficou pior contra o vento. A percepção de valor dele nunca foi checada.
- **A curva de economia.** Quanto tempo leva para comprar o segundo navio, se o loot acompanha o custo dos upgrades, se alguma faixa de notoriedade é um paredão.
- **Elites.** `chance_elite` cresce com a faixa e com horas jogadas na faixa 8. Nunca foi verificado se o crescimento é justo.

Se você for mexer em qualquer um desses, **você vai ser a primeira pessoa a medir** — e vale escrever o resultado aqui.

---

## Ver também

- [README](../README.md) — visão geral e como jogar
- `pirates/constants.py` — o painel de controle, com docstrings
- `tests/` — 594 testes; vários travam invariantes de equilíbrio, não só comportamento
