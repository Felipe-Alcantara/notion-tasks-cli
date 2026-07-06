"""Edição de propriedades (colunas) de uma linha genérica de database.

Ao trabalhar numa página que é linha de um database, o recomendado é começar
pelas **propriedades** (as colunas: status, datas, seleções, relações…) e só
depois preencher o **conteúdo** (os blocos do corpo da página). Este módulo
cobre a parte de propriedades, que faltava na CLI: os comandos de `tarefa`
editam só o modelo de tarefas, e os de bloco mexem no conteúdo — para uma linha
qualquer não havia caminho, forçando o uso direto da API.

O fluxo é simples: lê a página (a resposta já traz o ``type`` de cada coluna),
converte os valores informados para o formato da API do Notion e faz um único
PATCH com todas as mudanças.
"""

from __future__ import annotations

from typing import Any

from notion_starter import NotionClient
from notion_starter import properties as prop

# Tipos calculados/gerenciados pelo Notion: não aceitam escrita via API.
_SOMENTE_LEITURA = frozenset(
    {
        "formula",
        "rollup",
        "created_time",
        "created_by",
        "last_edited_time",
        "last_edited_by",
        "unique_id",
        "button",
    }
)


def _cliente_padrao() -> NotionClient:
    """Resolve o :class:`NotionClient` a partir da configuração do servidor.

    Import tardio de propósito: evita acoplar a camada de casos de uso ao Django
    no import — a config só é tocada quando nenhum cliente é injetado.
    """

    from integrations.notion import criar_cliente

    return criar_cliente()


def _numero(texto: str) -> float | int:
    """Converte texto em ``int`` quando inteiro, senão ``float``."""

    try:
        return int(texto)
    except ValueError:
        return float(texto)


def _lista(texto: str) -> list[str]:
    """Divide um texto CSV em itens não vazios."""

    return [parte.strip() for parte in texto.split(",") if parte.strip()]


def _para_valor(tipo: str, texto: str) -> dict[str, Any]:
    """Converte ``texto`` no payload de propriedade do ``tipo`` informado.

    Um texto vazio limpa a propriedade quando o tipo permite. Levanta
    ``ValueError`` para tipos ainda não suportados ou valores inválidos.
    """

    texto = texto.strip()
    vazio = texto == ""

    if tipo == "title":
        return {"title": []} if vazio else prop.title(texto)
    if tipo == "rich_text":
        return {"rich_text": []} if vazio else prop.rich_text(texto)
    if tipo == "number":
        if vazio:
            return {"number": None}
        try:
            return prop.number(_numero(texto))
        except ValueError as exc:
            raise ValueError(f"'{texto}' não é um número válido.") from exc
    if tipo == "checkbox":
        return prop.checkbox(texto.casefold() in {"true", "1", "sim", "yes", "x", "✓"})
    if tipo == "select":
        return {"select": None} if vazio else prop.select(texto)
    if tipo == "status":
        if vazio:
            raise ValueError("Uma propriedade 'status' não pode ficar vazia.")
        return prop.status(texto)
    if tipo == "multi_select":
        return prop.multi_select(_lista(texto))
    if tipo == "relation":
        return prop.relation(_lista(texto))
    if tipo == "people":
        return {"people": [{"id": id_} for id_ in _lista(texto)]}
    if tipo == "date":
        if vazio:
            return {"date": None}
        # Aceita intervalo no formato "inicio..fim".
        inicio, _, fim = texto.partition("..")
        return prop.date(inicio.strip(), fim.strip() or None)
    if tipo == "email":
        return {"email": texto or None}
    if tipo == "phone_number":
        return {"phone_number": texto or None}
    if tipo == "url":
        return {"url": texto or None}

    raise ValueError(f"Tipo '{tipo}' ainda não é suportado por editar-linha.")


def editar_linha(
    page_id: str,
    valores: dict[str, str],
    *,
    cliente: NotionClient | None = None,
) -> dict[str, Any]:
    """Edita propriedades de uma linha de database em um único PATCH.

    Args:
        page_id: ID da página (linha) a editar.
        valores: Mapa ``{nome_da_coluna: valor}``. O valor é texto; a conversão
            para o formato certo é inferida do ``type`` real da coluna.
        cliente: Cliente opcional; injete um double em testes.

    Returns:
        ``{"id": page_id, "atualizadas": {coluna: tipo, ...}}``.

    Raises:
        ValueError: coluna inexistente, tipo somente leitura/insuportado ou
            valor inválido — sempre com uma mensagem acionável.
    """

    if not valores:
        raise ValueError(
            'Informe ao menos uma propriedade para editar (ex.: --set "Status=Feito").'
        )

    cliente = cliente or _cliente_padrao()
    pagina = cliente.obter_pagina(page_id)
    props = pagina.get("properties", {})

    payload: dict[str, dict[str, Any]] = {}
    atualizadas: dict[str, str] = {}
    for nome, texto in valores.items():
        if nome not in props:
            disponiveis = ", ".join(sorted(props)) or "(nenhuma)"
            raise ValueError(
                f"Propriedade '{nome}' não existe nesta linha. Disponíveis: {disponiveis}"
            )
        tipo = props[nome].get("type", "")
        if tipo in _SOMENTE_LEITURA:
            raise ValueError(
                f"Propriedade '{nome}' é do tipo '{tipo}', calculada pelo Notion, "
                "e não pode ser editada."
            )
        payload[nome] = _para_valor(tipo, texto)
        atualizadas[nome] = tipo

    cliente.atualizar_pagina(page_id, payload)
    return {"id": page_id, "atualizadas": atualizadas}
