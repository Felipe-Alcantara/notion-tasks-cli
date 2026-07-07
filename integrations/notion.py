"""Adaptador do Notion — fábrica fina sobre o pacote ``notion_starter``.

O ``notion_starter`` (cliente, schema, TaskList) é a base reutilizável do projeto.
Esta camada apenas o **conecta à configuração do servidor** (``core.config``), para
que ``services`` peça um cliente/TaskList pronto sem conhecer o token nem o ambiente.
Não há regra de negócio aqui.
"""

from __future__ import annotations

from notion_starter import CamposTarefa, NotionClient, TaskList

from core.config import carregar_config


class ImproperlyConfigured(RuntimeError):
    """Configuração ausente ou inválida (equivalente local à exceção do Django)."""


def criar_cliente() -> NotionClient:
    """Cria um :class:`NotionClient` com o token resolvido pela config do servidor."""

    cfg = carregar_config()
    if not cfg.notion_token:
        raise ImproperlyConfigured(
            "NOTION_TOKEN não configurado. Defina a variável de ambiente ou use o "
            "menu (Configurar) do start_app.py."
        )
    return NotionClient(token=cfg.notion_token)


def criar_tasklist(
    database_id: str | None = None,
    campos: CamposTarefa | None = None,
) -> TaskList:
    """Cria uma :class:`TaskList` pronta para uso.

    Args:
        database_id: ID do database de tarefas. Se omitido, usa ``NOTION_DATABASE_ID``
            do ambiente.
        campos: Nomes das colunas, quando o database foge do padrão.
    """

    cfg = carregar_config()
    db_id = database_id or cfg.notion_database_id
    if not db_id:
        raise ImproperlyConfigured(
            "Database de tarefas não definido. Passe database_id ou defina "
            "NOTION_DATABASE_ID no ambiente."
        )
    return TaskList(criar_cliente(), db_id, campos)
