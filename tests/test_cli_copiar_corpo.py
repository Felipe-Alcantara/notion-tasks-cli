"""``copiar-corpo`` delega ao serviço do starter e mostra o que copiou e ignorou.

A regra de conversão é testada no ``notion-starter``; aqui só a borda: flags,
envelope, saída humana e a recusa amigável quando o starter instalado ainda
não tem o serviço (a CI usa o starter do PyPI).
"""

from __future__ import annotations

import importlib
import importlib.util
from typing import Any

import pytest

from cli import notion_tasks as cli

ORIGEM = "3ab91f95-497e-8190-9d77-fba045d775a8"
DESTINO = "3ab91f95-497e-817b-97fd-c8f79374e7d9"

precisa_do_servico = pytest.mark.skipif(
    importlib.util.find_spec("notion_starter.services.copia_corpo") is None,
    reason="notion-starter instalado ainda sem services.copia_corpo",
)


def _texto(conteudo: str) -> dict[str, Any]:
    return {"type": "text", "text": {"content": conteudo, "link": None},
            "plain_text": conteudo, "href": None}


class ClienteCopia:
    """Origem com um parágrafo, um to_do e uma subpágina; destino configurável."""

    def __init__(self, destino: list[dict[str, Any]] | None = None) -> None:
        self.destino = list(destino or [])
        self.anexos: list[tuple[str, list[dict[str, Any]]]] = []
        self._seq = 0

    def ler_blocos(self, block_id: str, buscar_todos: bool = False, recursivo: bool = False):
        if block_id == ORIGEM:
            return [
                {"id": "p1", "type": "paragraph", "has_children": False,
                 "paragraph": {"rich_text": [_texto("oi")], "icon": None}},
                {"id": "t1", "type": "to_do", "has_children": False,
                 "to_do": {"rich_text": [_texto("fazer")], "checked": True}},
                {"id": "c1", "type": "child_page", "has_children": False,
                 "child_page": {"title": "Filha"}},
            ]
        if block_id == DESTINO:
            return list(self.destino)
        return []

    def anexar_blocos(self, block_id: str, blocos: list[dict[str, Any]], **_: Any):
        self.anexos.append((block_id, blocos))
        criados = []
        for bloco in blocos:
            self._seq += 1
            criados.append({"id": f"novo-{self._seq}", **bloco})
        self.destino.extend(criados)
        return {"results": criados}


def _executar(args: list[str], cliente: Any) -> tuple[int, Any]:
    return cli.executar(args, tasklist_factory=lambda: None, client_factory=lambda: cliente)


@precisa_do_servico
def test_copia_e_lista_o_que_ficou_de_fora():
    cliente = ClienteCopia()

    codigo, saida = _executar(["--json", "copiar-corpo", ORIGEM, DESTINO], cliente)

    assert codigo == 0, saida
    dados = saida["dados"]
    assert dados["por_tipo"] == {"paragraph": 1, "to_do": 1}
    assert dados["blocos_de_topo"] == 2
    assert [b["tipo"] for b in dados["ignorados"]] == ["child_page"]
    gravados = cliente.anexos[0][1]
    assert "icon" not in gravados[0]["paragraph"]
    assert "plain_text" not in gravados[0]["paragraph"]["rich_text"][0]


@precisa_do_servico
def test_so_se_vazio_nao_escreve_em_destino_com_conteudo():
    cliente = ClienteCopia(destino=[{"id": "x", "type": "paragraph", "paragraph": {}}])

    codigo, saida = _executar(["--json", "copiar-corpo", ORIGEM, DESTINO, "--so-se-vazio"], cliente)

    assert codigo == 0
    assert saida["dados"]["pulado"] is True
    assert cliente.anexos == []


@precisa_do_servico
def test_dry_run_humano_resume_sem_escrever():
    cliente = ClienteCopia()

    codigo, saida = _executar(["copiar-corpo", ORIGEM, DESTINO, "--dry-run"], cliente)

    assert codigo == 0
    assert saida.startswith("Seriam copiados 2 blocos")
    assert "- ignorado child_page (c1)" in saida
    assert cliente.anexos == []


@precisa_do_servico
def test_mesma_pagina_e_recusada_como_validacao():
    codigo, saida = _executar(["--json", "copiar-corpo", ORIGEM, ORIGEM], ClienteCopia())

    assert codigo == 2
    assert saida["erro"]["codigo"] == "validacao"


def test_starter_sem_o_servico_recusa_com_configuracao(monkeypatch):
    original = importlib.import_module

    def sem_servico(nome: str, *args: Any, **kwargs: Any):
        if nome == "notion_starter.services.copia_corpo":
            raise ImportError(nome)
        return original(nome, *args, **kwargs)

    monkeypatch.setattr(cli.importlib, "import_module", sem_servico)
    cliente = ClienteCopia()

    codigo, saida = _executar(["--json", "copiar-corpo", ORIGEM, DESTINO], cliente)

    assert codigo == 2
    assert saida["erro"]["codigo"] == "configuracao"
    assert cliente.anexos == []
