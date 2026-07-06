"""Testes do serviço de edição de propriedades de linha de database.

Usam um cliente double: sem token, sem rede e sem tocar no Notion real.
"""

from __future__ import annotations

import pytest

from services import propriedades as svc


class FakeClient:
    def __init__(self, props: dict) -> None:
        self.props = props
        self.patch: dict | None = None

    def obter_pagina(self, page_id):
        return {"id": page_id, "properties": self.props}

    def atualizar_pagina(self, page_id, propriedades):
        self.patch = propriedades
        return {"id": page_id, "properties": propriedades}


def _client(**tipos):
    return FakeClient({nome: {"type": tipo, tipo: None} for nome, tipo in tipos.items()})


def test_converte_cada_tipo_para_o_payload_certo():
    client = _client(
        Titulo="title",
        Texto="rich_text",
        Peso="number",
        Feito="checkbox",
        Etapa="select",
        Situacao="status",
        Tags="multi_select",
        Rel="relation",
        Quando="date",
        Mail="email",
        Link="url",
    )
    resultado = svc.editar_linha(
        "pg",
        {
            "Titulo": "Oi",
            "Texto": "corpo",
            "Peso": "2.5",
            "Feito": "sim",
            "Etapa": "A fazer",
            "Situacao": "Feito",
            "Tags": "a, b ,c",
            "Rel": "id1,id2",
            "Quando": "2026-07-01..2026-07-05",
            "Mail": "a@b.com",
            "Link": "https://x.dev",
        },
        cliente=client,
    )
    p = client.patch
    assert p["Titulo"] == {"title": [{"text": {"content": "Oi"}}]}
    assert p["Peso"] == {"number": 2.5}
    assert p["Feito"] == {"checkbox": True}
    assert p["Etapa"] == {"select": {"name": "A fazer"}}
    assert p["Situacao"] == {"status": {"name": "Feito"}}
    assert p["Tags"] == {"multi_select": [{"name": "a"}, {"name": "b"}, {"name": "c"}]}
    assert p["Rel"] == {"relation": [{"id": "id1"}, {"id": "id2"}]}
    assert p["Quando"] == {"date": {"start": "2026-07-01", "end": "2026-07-05"}}
    assert p["Mail"] == {"email": "a@b.com"}
    assert p["Link"] == {"url": "https://x.dev"}
    assert resultado["atualizadas"]["Peso"] == "number"


def test_valor_vazio_limpa_a_coluna():
    client = _client(Tags="multi_select", Peso="number", Quando="date", Etapa="select")
    svc.editar_linha(
        "pg",
        {"Tags": "", "Peso": "", "Quando": "", "Etapa": ""},
        cliente=client,
    )
    assert client.patch["Tags"] == {"multi_select": []}
    assert client.patch["Peso"] == {"number": None}
    assert client.patch["Quando"] == {"date": None}
    assert client.patch["Etapa"] == {"select": None}


def test_numero_invalido_erra_sem_patch():
    client = _client(Peso="number")
    with pytest.raises(ValueError, match="número"):
        svc.editar_linha("pg", {"Peso": "abc"}, cliente=client)
    assert client.patch is None


def test_status_vazio_erra():
    client = _client(Situacao="status")
    with pytest.raises(ValueError, match="status"):
        svc.editar_linha("pg", {"Situacao": ""}, cliente=client)


def test_sem_valores_erra():
    client = _client(Titulo="title")
    with pytest.raises(ValueError):
        svc.editar_linha("pg", {}, cliente=client)
