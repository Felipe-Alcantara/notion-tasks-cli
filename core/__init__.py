"""Camada ``core`` do servidor — config, logging e token.

Tudo que é transversal e não conhece HTTP nem regra de negócio vive aqui.
A configuração é lida do ambiente (``core.config``); o logging reaproveita o do
``notion_starter`` para manter um único padrão no projeto.
"""

from __future__ import annotations

from .config import Config, carregar_config, carregar_env_file

__all__ = ["Config", "carregar_config", "carregar_env_file"]
