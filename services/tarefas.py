"""Compatibilidade para `services.tarefas` consolidado no `notion_starter`."""

import importlib
import sys
from pathlib import Path

try:
    _modulo = importlib.import_module("notion_starter.services.tarefas")
except ModuleNotFoundError:
    starter_src = Path(__file__).resolve().parents[2] / "notion-starter" / "src"
    if starter_src.exists() and str(starter_src) not in sys.path:
        sys.path.insert(0, str(starter_src))
    import notion_starter

    starter_pkg = starter_src / "notion_starter"
    if starter_pkg.exists() and str(starter_pkg) not in notion_starter.__path__:
        notion_starter.__path__.append(str(starter_pkg))
    _modulo = importlib.import_module("notion_starter.services.tarefas")

globals().update(vars(_modulo))
sys.modules[__name__] = _modulo
