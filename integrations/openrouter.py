"""Compatibilidade para o adaptador OpenRouter consolidado no ``notion_starter``."""

import importlib
import sys
from pathlib import Path

try:
    _modulo = importlib.import_module("notion_starter.openrouter")
except ModuleNotFoundError:
    starter_src = Path(__file__).resolve().parents[2] / "notion-starter" / "src"
    if starter_src.exists() and str(starter_src) not in sys.path:
        sys.path.insert(0, str(starter_src))
    import notion_starter

    starter_pkg = starter_src / "notion_starter"
    if starter_pkg.exists() and str(starter_pkg) not in notion_starter.__path__:
        notion_starter.__path__.append(str(starter_pkg))
    _modulo = importlib.import_module("notion_starter.openrouter")

globals().update(vars(_modulo))
_CACHE_PATH = _modulo._CACHE_PATH


def carregar_modelos(forcar_atualizacao: bool = False, timeout: float = 10.0):
    """Proxy que preserva monkeypatch local de ``_CACHE_PATH``."""

    _modulo._CACHE_PATH = _CACHE_PATH
    return _modulo.carregar_modelos(
        forcar_atualizacao=forcar_atualizacao,
        timeout=timeout,
    )
