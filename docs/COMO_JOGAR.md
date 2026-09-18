# Como jogar — instrumentos e leitura de tela

Tudo no CLI PIRATES acontece enquanto você lê. Este guia explica cada painel da tela, o que cada símbolo significa, e como ler os instrumentos juntos para tomar decisões.

Se você ainda não rodou o jogo, comece pelo [README](../README.md).

---

## As duas telas

O jogo tem dois modos, e a tela muda entre eles:

| | Navegação | Combate |
|---|---|---|
| Mapa central | Mapa de navegação (zoom manual `+`/`-`) | Minimapa (zoom automático) |
| Visão do capitão | Inimigo mais próximo no horizonte | Inimigo do combate + arcos de tiro |
| Vigia | Distância ao inimigo mais próximo | Distância ao inimigo engajado |
| Painel de fuga | — | Aparece se você digitou `fugir` |

Todo o resto — navio, canhões, velas, porão, tripulação, bússola — é igual nos dois.

---

## Painel a painel

### Cabeçalho

```
CLI PIRATES | BRIGANTIM | tempo: 87.5s
```

O relógio é da **partida de combate atual**, não da sessão — ele zera a cada novo combate.

### SEU NAVIO

```
CASCO  [######----]  62.0%
MASTRO [##########] 100.0%
VELA   [########--]  80.0%
RODA   [##########] 100.0%
AGUA   [#---------]  18.0%
MORAL  [##########] 100.0%
VENTO  [NE / SW  9.4]
VEL    [######]
RUMO   [/ NE  45.0 ->   0.0] (ZM)
```

**As quatro partes** são reparáveis com o comando `reparar`. Não são cosméticas:

| parte | o que quebra quando cai |
|---|---|
| **casco** | entra água (exponencialmente) e o reparo de tudo fica mais lento |
| **mastro** | velocidade — entra no `fator_dano` |
| **vela** | velocidade — junto com o mastro, **multiplicando** |
| **roda** | o leme |

> Vela e mastro multiplicam: 70% e 70% dão **49%** da velocidade, não 70%. É por isso que atirar no rigging inimigo é a forma mais rápida de deixá-lo para trás.

**AGUA** é o único medidor em que subir é ruim. A 100% você afunda. A entrada cresce **exponencialmente** com o dano no casco — com dano leve as bombas seguram; com casco destruído, nem toda a tripulação nas bombas impede o naufrágio.

**MORAL** afeta a recarga dos canhões e a eficiência de reparo e bombas.

**VENTO** mostra `[para onde / de onde  intensidade]`. Direção e intensidade mudam devagar ao longo da partida.

**RUMO** mostra `[seta  rumo_atual -> rumo_alvo] (zona)`. Quando os dois números diferem, o leme ainda está girando. A **zona** entre parênteses é a mais importante da linha:

| zona | ângulo ao vento | significado |
|---|---|---|
| `ZM` | 0–45° | zona morta — vento quase de proa |
| `B` | 45–90° | bolina |
| `T` | 90–135° | través |
| `P` | 135–180° | popa — vento por trás |

Qual zona é boa **depende das suas velas**. Com latina você voa na ZM e arrasta na P; com quadrada é o inverso.

### CANHOES

```
  E1 [######] mira:300m PRONTO
  E2 [######] sem mira
  B1 [######] sem mira
  B2 [######] sem mira
```

`E` é estibordo (direita), `B` é bombordo (esquerda). A barra é a **recarga**: cheia significa pronto para disparar.

Estados possíveis: `PRONTO`, `sem mira` (sem tripulação ou sem alvo), tempo restante de recarga, e aviso de munição acabando.

> Um canhão **sem mira não recarrega**. A recarga fica congelada até você armá-lo. Não adianta deixar o bordo ocioso "esfriando".

Canhão consome **1 pólvora + 1 bola** por tiro.

### VELAS

```
  0 proa      |#->
 >1 principal {#-7
  2 popa      {#-7
  3 aux-1     ----
  4 aux-2     ----
```

O `>` marca o slot selecionado (tecla `Q` circula, `W`/`S` mudam o nível).

Cada barra tem quatro caracteres: **borda + abertura + borda**. As bordas identificam o **tipo** de vela, a abertura mostra o **nível**:

| abertura | nível |
|---|---|
| `--` | 0 — vela ferrada |
| `#-` | 1 — meio pau |
| `##` | 2 — pano cheio |

| bordas | tipo | é boa em |
|---|---|---|
| `/ ... \|` | latina | contra o vento |
| `{ ... 7` | carangueja | través, boa em tudo |
| `[ ... ]` | quadrada | a favor do vento |
| `\| ... >` | estai | **nada** — só dá giro |
| `= ... =` | topo quadrada | a favor (auxiliar) |
| `\| ... D` | vela de asa | só a favor (auxiliar extrema) |

`----` é slot vazio. Os auxiliares começam todos vazios — é o seu espaço de customização, preenchido na Loja de Navios.

> **O estai não dá velocidade nenhuma.** Ele existe só para o `bonus_curva` — é a vela de manobra. Não adianta abrir estai esperando ir mais rápido.

### PORAO

```
(6/9 slots)
  polvora 2b [##########] 50/50u
  bolas   2b [##########] 50/50u
  tabuas  2b [##########] 50/50u
  ouro    0b [----------]  0u
```

`2b` = dois barris daquele tipo. Slots são finitos e o **ouro ocupa espaço como qualquer carga** — não existe banco. Tecla `V` abre o inventário, onde você move e descarta barris.

### TRIPULACAO

```
T1   canhao: canhao E1
T2   bomba: porao
T3   ocioso: conves
```

Cada tripulante tem um posto. Quem está **em trânsito** aparece marcado — e, enquanto atravessa o convés, **não trabalha**:

| de → para | tempo |
|---|---|
| canhão → canhão, mesmo bordo | 6 s |
| canhão → canhão, bordo oposto | 8 s |
| trocar de tipo de tarefa | 4 s |
| reparo → reparo, outra parte | grátis |

Ao pedir tripulantes sem ter gente livre, o jogo puxa primeiro dos canhões, depois do reparo. **A bomba nunca é tocada automaticamente** — se você quer alguém fora da bomba, tire manualmente.

### VISAO DO CAPITAO

```
~~~~~~~~|~~~~~~~|~~~~~~~~~~~<[||]>~~~~~~~|~~~~~~~~|
P           B           ^            E           P
```

A régua de baixo é o horizonte em 360° ao redor da sua **proa**: `^` é a frente, `E` estibordo, `B` bombordo, `P` popa (nas duas pontas).

Os `|` na linha d'água marcam os **limites dos arcos de tiro** — 60° a 120° de cada bordo. Seus canhões só atiram entre esses marcadores. Colocar o inimigo entre dois `|` é a coisa mais importante do combate.

O **tamanho do ícone do inimigo indica a distância**:

| ícone | distância |
|---|---|
| `<[||]>` | < 300 m |
| `<\|\|>` | < 500 m |
| `oo` | < 700 m |
| `..` | mais longe |

### BUSSOLA

```
S....S|W....W....N|W....N.....N|E....E....S|E.....
                  |<<<
```

Rosa dos ventos deslizante, centrada no seu rumo. A segunda linha aparece quando o leme está girando e mostra para que lado — quanto mais setas, mais longe do rumo alvo.

### MAPA

Em combate é o **minimapa de arena**, com zoom automático pela distância ao inimigo, e o inimigo aparece como `[` genérico. Fora de combate é o **mapa de navegação**, com zoom manual (`+`/`=` aproxima, `-`/`_` afasta), e aí os inimigos vêm marcados por tipo:

```
{^  você                  [P  porto
*^  chalupa inimiga       ##  ilha
:^  brigantim inimigo     -x  destroço com loot
%^  galeão inimigo        -*  seu naufrágio
(^  inimigo fugindo
```

Dois caracteres, duas informações. **O primeiro é o porte** — `*` chalupa, `:` brigantim, `%` galeão — então dá para saber o que vem vindo sem entrar em combate. Um `%` no horizonte é hora de decidir se vale a briga.

É por isso que a marcação existe só aqui: dentro do combate a decisão de engajar já foi tomada, e o tipo do inimigo já aparece no resto do HUD.

**O segundo é o rumo** daquele navio, então dá para ver se ele está vindo na sua direção antes de chegar.

Inimigo em fuga aparece como `(` em vez do símbolo de tipo: saber que ele está correndo vale mais do que saber o porte.

Tecla `M` alterna para o **mapa-mundo**, que mostra o quadrante de 8 km inteiro com as coordenadas no título (`MAPA MUNDO (2,3)`).

> Portos e inimigos só aparecem dentro do alcance de visão do capitão (5000 m e 3500 m). **Ilhas sempre aparecem** — são perigo físico, não informação tática.

### VIGIA

```
Vigia: "a 350m!"
```

Distância estimada, arredondada de 25 em 25 m para não ficar tremendo. Use `radar` se quiser o número exato e o rumo.

### FUGA

Só aparece depois de você digitar `fugir`:

```
FUGA: [#####-----]  7.5s/15s   850m/800m  MANTENHA!
```

Barra do timer, tempo acumulado, distância atual contra a exigida. Verde enquanto conta, amarelo com `faltam Xm` quando você está perto demais. O timer **zera** se a distância cair — o log avisa quando isso acontece.

### Rodapé

```
LOG
...
FOCO: canhao E1 trip:1 mira:300m [ATIRANDO]
> _
```

`FOCO` mostra o que as hotkeys vão afetar. O prompt aceita comandos; **TAB** completa, **ENTER vazio** repete o último.

---

## Lendo os instrumentos juntos

### Para atirar

1. **VISAO DO CAPITAO** — o inimigo está entre dois `|`?
2. **CANHOES** — o bordo daquele lado está com a barra cheia?
3. **VIGIA** — a que distância?
4. `c E1 <distância>` ou `Espaço` com o canhão em foco.

Se o inimigo não está no arco, vire — mas lembre que trocar de bordo custa 8 s de travessia da tripulação, quase uma recarga inteira.

### Para ir mais rápido

1. **RUMO** — em que zona você está?
2. **VELAS** — seus tipos são bons nessa zona?
3. Se não: mude o rumo, ou aceite a perda. Um brigantim à bolina com velas quadradas está desperdiçando o vento.
4. **VEL** confirma se funcionou.

### Para fugir

1. **SEU NAVIO** do inimigo não é visível — mas se você já acertou as velas dele, ele está mais lento do que parece.
2. Digite `fugir` e escolha o rumo pela **zona de vento em que o seu navio ganha**, não simplesmente de costas para ele.
3. **FUGA** mostra se está funcionando. Se o timer zera repetidamente, você não é rápido o bastante naquele ângulo — mude de rumo ou volte a atirar no rigging.

### Para não afundar

1. **AGUA** subindo e **CASCO** baixo é espiral da morte: casco baixo faz a água entrar mais rápido, e casco baixo também faz o reparo render menos.
2. Bomba segura o sintoma; só `reparar casco` resolve a causa.
3. Reparo consome **tábuas**. Olhe o **PORAO** antes de contar com ele.

---

## Porto

Comando `atracar`, a menos de 250 m de um `[P]`. Move o capitão com `WASD`.

| lugar | o que faz |
|---|---|
| Loja de suprimentos | compra e vende pólvora, bolas, tábuas; barris novos |
| Loja de navios | compra navio, troca o ativo, renomeia, **troca velas** |
| Upgrades | casco, recarga, porão, tripulação, velocidade/giro, alcance |
| Doca | zarpa de volta ao mundo |

Cada navio tem seus próprios tetos de upgrade. Velas auxiliares são instaladas aqui — a loja **nunca cria slot novo**, só preenche os que o navio já tem.

---

## Ver também

- [README](../README.md) — visão geral, comandos, hotkeys
- [BALANCEAMENTO](BALANCEAMENTO.md) — os números por trás de tudo isso
- `ajuda` no prompt, ou **Como Jogar** no menu — a referência rápida dentro do jogo
