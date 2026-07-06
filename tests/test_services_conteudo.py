"""Testes do serviço de conteúdo (append de blocos).

Cobrem o fatiamento em lotes de 100 (limite do Notion por requisição) e a
verificação de escrita parcial. Cliente double, sem rede.
"""

from __future__ import annotations

import pytest

from services import conteudo as svc


class FakeClient:
    def __init__(self, *, parcial: bool = False) -> None:
        self.lotes: list[int] = []
        self.parcial = parcial

    def anexar_blocos(self, block_id, blocos):
        self.lotes.append(len(blocos))
        criados = blocos[:-1] if self.parcial else blocos
        return {"results": criados}


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
