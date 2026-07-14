#!/usr/bin/env python3
"""
CLI PIRATES – ponto de entrada direto (alternativa ao comando instalado).

Execute com:
    python3 main.py

Para instalar como comando de sistema:
    pip install -e .
    cli-pirates

Requer Python 3.10+ e um terminal real (TTY).
Recomenda-se uma janela de ~100 colunas × 45 linhas.
"""

import sys

try:
    import curses
except ImportError:
    print("O modulo 'curses' nao esta disponivel neste ambiente.")
    sys.exit(1)

from pirates.game import run

if __name__ == "__main__":
    run()
