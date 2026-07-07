"""Configuração de testes: adiciona a raiz do repositório ao ``sys.path``
para importar o pacote de topo ``cli`` sem instalação."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
_STARTER_SRC = _ROOT.parent / "notion-starter" / "src"

if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if _STARTER_SRC.exists() and str(_STARTER_SRC) not in sys.path:
    sys.path.insert(0, str(_STARTER_SRC))
