"""Configuração de testes: adiciona a raiz do repositório ao ``sys.path``
para importar o pacote de topo ``cli`` sem instalação."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]

if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
