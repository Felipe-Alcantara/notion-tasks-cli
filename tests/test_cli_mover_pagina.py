"""``mover-pagina`` prevê as colunas, recusa perda sem aceite e confere o pai.

A regra vive em ``notion_starter.services.movimentacao``; estes testes só
exercitam a borda com um double de cliente, sem rede. O serviço entrou no
starter depois do último release publicado: com o starter do PyPI, os testes
que dependem dele ficam de fora e o teste do fim confere a recusa amigável.
"""

from __future__ import annotations

import importlib
import importlib.util
from typing import Any

import pytest

from cli import notion_tasks as cli

PAGINA = "3ab91f95-497e-8190-9d77-fba045d775a8"
DATABASE = "30296e2d-cd39-4cf3-8bbd-3fb2f53c0195"
FONTE = "38e91f95-497e-818b-ab08-ff19918d6c7c"

TEM_SERVICO = importlib.util.find_spec("notion_starter.services.movimentacao") is not None
precisa_do_servico = pytest.mark.skipif(
    not TEM_SERVICO, reason="notion-starter instalado ainda sem services.movimentacao"
)


class ClienteMovimento:
    """Linha de um database indo para outro database com uma fonte."""

    def __init__(self, *, com_relacao: bool = True, fontes: int = 1) -> None:
        self.movimentos: list[tuple[str, str, str]] = []
        self.fontes = fontes
        self.propriedades: dict[str, Any] = {
            "Nome": {"type": "title", "title": [{"plain_text": "Ideia"}]},
            "Tema/Pilar": {"type": "multi_select", "multi_select": [{"name": "IA"}]},
        }
        if com_relacao:
            self.propriedades["Projeto"] = {"type": "relation", "relation": [{"id": "p1"}]}

    def obter_pagina(self, page_id: str) -> dict[str, Any]:
        return {
            "id": page_id,
            "parent": {"type": "database_id", "database_id": "origem"},
            "properties": self.propriedades,
        }

    def resolver_data_source(self, database_id: str) -> str:
        from notion_starter.exceptions import FonteDeDadosIndefinidaError

        if self.fontes != 1:
            raise FonteDeDadosIndefinidaError(
                database_id, [(f"ds-{i}", f"Fonte {i}") for i in range(self.fontes)]
            )
        return FONTE

    def get_data_source(self, data_source_id: str) -> dict[str, Any]:
        return {"id": data_source_id, "properties": {"Título": {"type": "title", "title": {}}}}

    def mover_pagina(self, page_id: str, novo_pai_id: str, *, tipo_pai: str) -> dict[str, Any]:
        self.movimentos.append((page_id, novo_pai_id, tipo_pai))
        return {"id": page_id, "parent": {"type": "database_id", "database_id": DATABASE}}


def _executar(args: list[str], cliente: Any) -> tuple[int, Any]:
    return cli.executar(args, tasklist_factory=lambda: None, client_factory=lambda: cliente)


@precisa_do_servico
def test_dry_run_mostra_colunas_criadas_e_valores_perdidos_sem_mover():
    cliente = ClienteMovimento()

    codigo, saida = _executar(
        ["--json", "mover-pagina", PAGINA, DATABASE, "--tipo-pai", "database_id", "--dry-run"],
        cliente,
    )

    assert codigo == 0, saida
    dados = saida["dados"]
    assert cliente.movimentos == []
    assert dados["movido"] is False and dados["dry_run"] is True
    assert [c["nome"] for c in dados["colunas_acrescentadas_no_destino"]] == ["Tema/Pilar"]
    assert [c["nome"] for c in dados["valores_perdidos"]] == ["Projeto"]


@precisa_do_servico
def test_perda_sem_aceite_e_recusada_com_o_comando_pronto():
    cliente = ClienteMovimento()

    codigo, saida = _executar(
        ["--json", "mover-pagina", PAGINA, DATABASE, "--tipo-pai", "database_id"], cliente
    )

    assert codigo == 2
    assert cliente.movimentos == []
    erro = saida["erro"]
    assert erro["codigo"] == "validacao"
    assert erro["proximo_passo"].endswith("--aceitar-perdas")
    assert erro["detalhes"]["valores_perdidos"][0]["nome"] == "Projeto"


@precisa_do_servico
def test_com_aceite_move_para_a_fonte_e_avisa_as_colunas_criadas():
    cliente = ClienteMovimento()

    codigo, saida = _executar(
        [
            "--json", "mover-pagina", PAGINA, DATABASE,
            "--tipo-pai", "database_id", "--aceitar-perdas",
        ],
        cliente,
    )

    assert codigo == 0, saida
    assert cliente.movimentos == [(PAGINA, FONTE, "data_source_id")]
    dados = saida["dados"]
    assert dados["movido"] is True
    assert dados["pai_novo"]["database_id"] == DATABASE
    assert "Tema/Pilar" in dados["aviso"]


@precisa_do_servico
def test_database_com_varias_fontes_pede_a_fonte():
    cliente = ClienteMovimento(fontes=2)

    codigo, saida = _executar(
        ["--json", "mover-pagina", PAGINA, DATABASE, "--tipo-pai", "database_id"], cliente
    )

    assert codigo == 2
    erro = saida["erro"]
    assert [f["id"] for f in erro["detalhes"]["data_sources"]] == ["ds-0", "ds-1"]
    assert "--tipo-pai data_source_id" in erro["proximo_passo"]
    assert cliente.movimentos == []


@precisa_do_servico
def test_saida_humana_lista_colunas_e_perdas():
    cliente = ClienteMovimento()

    codigo, saida = _executar(
        ["mover-pagina", PAGINA, DATABASE, "--tipo-pai", "database_id", "--dry-run"], cliente
    )

    assert codigo == 0
    assert "Simulação" in saida
    assert "+ coluna nova no destino: Tema/Pilar" in saida
    assert "- valor perdido: Projeto" in saida


def test_starter_sem_o_servico_recusa_sem_fingir_movimento(monkeypatch):
    original = importlib.import_module

    def sem_movimentacao(nome: str, *args: Any, **kwargs: Any):
        if nome == "notion_starter.services.movimentacao":
            raise ImportError(nome)
        return original(nome, *args, **kwargs)

    monkeypatch.setattr(cli.importlib, "import_module", sem_movimentacao)
    cliente = ClienteMovimento()

    codigo, saida = _executar(["--json", "mover-pagina", PAGINA, DATABASE], cliente)

    assert codigo == 2
    assert saida["erro"]["codigo"] == "configuracao"
    assert "notion_starter.services.movimentacao" in saida["erro"]["mensagem"]
    assert cliente.movimentos == []
