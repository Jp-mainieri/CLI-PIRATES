# Contribuindo

Obrigado pelo interesse. Este guia cobre o fluxo, as convenções e — a parte que mais importa neste projeto — como propor uma mudança de equilíbrio.

---

## Começando

```bash
git clone https://github.com/Jp-mainieri/CLI-PIRATES.git
cd CLI-PIRATES
python3 main.py                  # jogar
python3 -m pytest tests/ -q      # 614 testes, < 1s
```

Não há nada a instalar para rodar o jogo — só a biblioteca padrão. Para os testes, `pip install pytest`.

Requer **Python 3.10+** e um terminal real (TTY), com pelo menos ~100×45.

Antes de mexer em qualquer coisa, leia [docs/ARQUITETURA.md](docs/ARQUITETURA.md) — em especial os quatro conceitos do início. Sem eles o código parece arbitrário.

---

## Fluxo

1. Fork, e branch a partir de `main`
2. Rode os testes **antes** de mexer, para saber que estavam passando
3. Faça a mudança, com testes
4. Rode os testes de novo
5. Abra um PR dizendo **o que mudou e por quê**

Prefixos de branch usados no repositório:

| prefixo | para |
|---|---|
| `feat/` | funcionalidade nova |
| `fix/` | correção de bug |
| `balance/` | ajuste de equilíbrio |
| `docs/` | documentação |
| `mod/` | mudança estrutural grande |

---

## Convenções de código

**Português.** Nomes, docstrings e comentários. Mantenha — mistura fica pior que qualquer das duas escolhas.

**Comentário explica decisão, não mecânica.**

```python
# ruim:  incrementa o indice
# bom:   histerese aqui senao a IA troca de modo a cada tick na fronteira
```

**Constante nova precisa de docstring**, logo abaixo, dizendo o que é e — se for o caso — de quais outras constantes ela depende. `constants.py` é o painel de controle do jogo; quem chega lá precisa entender sem abrir mais nada.

**Sem dependências novas.** O jogo roda com a biblioteca padrão e é assim que ele se distribui. `pytest` é a única exceção, e só para desenvolvimento.

**Falha visível vence fallback silencioso.** Um valor não mapeado deve parecer desconhecido, não se disfarçar de válido. Um fallback plausível demais esconde bug.

---

## Testes

Todo PR precisa passar os 614. Se você adiciona comportamento, adicione teste.

Os testes constroem `Estado`/`EstadoMundo` reais e inspecionam strings ou estado — **não há mock de curses**. É por isso que um jogo de terminal consegue ter 600+ testes rodando em menos de um segundo. Siga o padrão: `tests/test_hud.py` e `tests/test_zoom_navegacao.py` são bons modelos.

### Teste de invariante

Além de "isto funciona", vale travar "esta relação precisa valer". Se você adiciona uma tabela indexada por tipo de navio, adicione o teste que verifica que ela cobre **todos** os tipos:

```python
def test_todo_tipo_de_navio_tem_simbolo(self):
    assert set(NAVIO_TIPOS) == set(SIMBOLO_TIPO_NAVIO)
```

Esse é o teste que pega o bug que ninguém estava procurando.

### Teste de invariante precisa ser visto falhando

Um teste que nunca falhou não provou nada. Ao escrever um, quebre de propósito o que ele protege e confirme que a mensagem aponta o problema certo. Depois desfaça.

---

## Mudanças de equilíbrio

Esta é a parte específica deste projeto. **Equilíbrio não se avalia por intuição** — o jogo é determinístico o bastante para simular.

Leia [docs/BALANCEAMENTO.md](docs/BALANCEAMENTO.md) antes. Ele tem a metodologia, as armadilhas de medição e o que já foi medido — inclusive vários "medido: não muda nada", que economizam seu tempo.

Um PR de equilíbrio deve trazer:

1. **O número antes e depois**, medido — não estimado
2. **Sobre qual cenário**, com quantas amostras
3. **O que você NÃO mediu**

O terceiro item é tão importante quanto os outros. Uma mudança de velocidade validada em fuga mas não em duelo direto é exatamente isso, e a mensagem de commit deve dizer.

> **Cuidado com constantes acopladas.** Algumas não são independentes: mexer numa sem olhar a outra reabre bug. As conhecidas estão na tabela de [BALANCEAMENTO](docs/BALANCEAMENTO.md#constantes-acopladas), cada uma com o teste que a trava. Se um desses testes falhar depois da sua mudança, **leia a mensagem** — não relaxe o teste sem entender a regra.

---

## Mensagens de commit

Imperativo na primeira linha, com prefixo de escopo:

```
fix(hotkeys): aceita = e _ no zoom, e conserta a tecla = inerte
```

No corpo, o **porquê**. O *o quê* já está no diff; o que se perde é a razão. Um bom corpo responde:

- Qual era o problema, concretamente
- Por que esta solução, e não a óbvia
- O que foi medido, e o que não foi
- Que armadilha o próximo a mexer aqui deve conhecer

Se a mudança corrige algo que já quebrou antes, diga — é o que evita a terceira vez.

Commits devem ser **independentes**: cada um passa a suíte sozinho. Se sua mudança tem partes separáveis, separe.

---

## Documentação

Mudança que o jogador percebe atualiza a documentação junto, no mesmo PR:

| mudou | atualize também |
|---|---|
| comando ou hotkey | `COMO_JOGAR_TEXTO` em `constants.py`, README, [docs/COMO_JOGAR.md](docs/COMO_JOGAR.md) |
| símbolo de mapa | a legenda em `hud.py`, ajuda in-game, [docs/COMO_JOGAR.md](docs/COMO_JOGAR.md) |
| estatística de navio | README e ajuda in-game |
| equilíbrio | [docs/BALANCEAMENTO.md](docs/BALANCEAMENTO.md) |
| estrutura do código | [docs/ARQUITETURA.md](docs/ARQUITETURA.md) |

A ajuda dentro do jogo já divergiu do código antes — dizia que o galeão tinha 7 tripulantes quando tem 4. Documentação errada é pior que documentação ausente.

---

## Reportando bugs

Abra uma issue com:

- O que você esperava e o que aconteceu
- Como reproduzir — incluindo **a seed do mundo**, se for no mundo aberto (fica no save, em `saves/<capitao>.json`)
- Tipo de navio, e o que estava na tela

Bug de equilíbrio ("X está forte demais") é bem-vindo, mas vale mais com um número junto.

---

## Ver também

- [README](README.md) — visão geral
- [docs/ARQUITETURA.md](docs/ARQUITETURA.md) — como o código funciona
- [docs/BALANCEAMENTO.md](docs/BALANCEAMENTO.md) — como medir uma mudança
- [docs/COMO_JOGAR.md](docs/COMO_JOGAR.md) — os instrumentos, do lado do jogador
