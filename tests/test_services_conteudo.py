"""Testes do serviço de conteúdo (append de blocos).

Cobrem o fatiamento em lotes de 100 (limite do Notion por requisição) e a
verificação de escrita parcial. Cliente double, sem rede.
"""

from __future__ import annotations

import pytest

from services import conteudo as svc


class FakeClient:
    def __init__(self, *, parcial: bool = False, blocos: list | None = None) -> None:
        self.lotes: list[int] = []
        self.parcial = parcial
        self.blocos = blocos if blocos is not None else []
        self.apagados: list[str] = []

    def anexar_blocos(self, block_id, blocos):
        self.lotes.append(len(blocos))
        criados = blocos[:-1] if self.parcial else blocos
        return {"results": criados}

    def ler_blocos(self, block_id, page_size=100, buscar_todos=False, recursivo=False):
        return self.blocos

    def excluir_bloco(self, block_id):
        self.apagados.append(block_id)
        return {"id": block_id, "archived": True}


def _paragrafo(block_id: str, texto: str) -> dict:
    return {
        "id": block_id,
        "type": "paragraph",
        "paragraph": {"rich_text": [{"plain_text": texto}]},
    }


def test_escrever_fatia_em_lotes_de_100():
    markdown = "\n\n".join(f"linha {i}" for i in range(250))
    client = FakeClient()
    total = svc.escrever_conteudo("pg", markdown, cliente=client)
    assert total == 250
    assert client.lotes == [100, 100, 50]


def test_escrever_um_lote_quando_cabe():
    client = FakeClient()
    total = svc.escrever_conteudo("pg", "a\n\nb\n\nc", cliente=client)
    assert total == 3
    assert client.lotes == [3]


def test_escrever_detecta_escrita_parcial():
    markdown = "\n\n".join(f"linha {i}" for i in range(5))
    client = FakeClient(parcial=True)
    with pytest.raises(RuntimeError, match="parcial"):
        svc.escrever_conteudo("pg", markdown, cliente=client)


def test_escrever_conteudo_vazio_erra():
    client = FakeClient()
    with pytest.raises(ValueError):
        svc.escrever_conteudo("pg", "   ", cliente=client)
    assert client.lotes == []


def test_listar_blocos_expoe_id_tipo_e_preview():
    titulo = {
        "id": "b1",
        "type": "heading_1",
        "heading_1": {"rich_text": [{"plain_text": "Título"}]},
    }
    client = FakeClient(blocos=[titulo, _paragrafo("b2", "corpo da nota")])
    blocos = svc.listar_blocos("pg", cliente=client)
    assert blocos == [
        {"id": "b1", "tipo": "heading_1", "preview": "# Título"},
        {"id": "b2", "tipo": "paragraph", "preview": "corpo da nota"},
    ]


def test_listar_blocos_trunca_preview_longo():
    texto = "x" * 500
    client = FakeClient(blocos=[_paragrafo("b1", texto)])
    preview = svc.listar_blocos("pg", cliente=client)[0]["preview"]
    assert preview.endswith("…")
    assert len(preview) <= 100


def test_limpar_conteudo_apaga_todos_os_blocos_de_topo():
    client = FakeClient(blocos=[_paragrafo("b1", "a"), _paragrafo("b2", "b")])
    total = svc.limpar_conteudo("pg", cliente=client)
    assert total == 2
    assert client.apagados == ["b1", "b2"]


def test_limpar_conteudo_ignora_blocos_sem_id():
    client = FakeClient(blocos=[{"type": "paragraph", "paragraph": {"rich_text": []}}])
    total = svc.limpar_conteudo("pg", cliente=client)
    assert total == 0
    assert client.apagados == []


def test_escrever_substituir_apaga_antes_de_anexar():
    client = FakeClient(blocos=[_paragrafo("velho", "lixo antigo")])
    total = svc.escrever_conteudo("pg", "novo\n\nconteúdo", substituir=True, cliente=client)
    assert total == 2
    assert client.apagados == ["velho"]  # limpou o corpo antigo
    assert client.lotes == [2]  # e escreveu o novo


def test_escrever_substituir_valida_antes_de_apagar():
    # Entrada vazia deve erguer ValueError SEM apagar nada (não zera a página).
    client = FakeClient(blocos=[_paragrafo("velho", "conteúdo que não pode sumir")])
    with pytest.raises(ValueError):
        svc.escrever_conteudo("pg", "   ", substituir=True, cliente=client)
    assert client.apagados == []
