"""O que o ``pyproject.toml`` declara precisa bater com o código que a suíte testa.

A suíte roda contra o starter vizinho (``tests/conftest.py`` põe
``../notion-starter/src`` na frente do ``sys.path``) ou contra o instalado. Quem
instala a CLI recebe o que a faixa do ``pyproject.toml`` permite. Se as duas
coisas divergem, a suíte fica verde testando um starter que nenhum usuário tem.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import notion_starter
import pytest
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
from packaging.version import Version

from cli import versao

if sys.version_info >= (3, 11):
    import tomllib
else:  # Python 3.10: o pytest já instala o tomli nessa versão.
    import tomli as tomllib

RAIZ = Path(__file__).resolve().parents[1]


def _projeto() -> dict[str, Any]:
    dados = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))
    return dados["project"]


def test_versao_fonte_e_a_do_pyproject():
    """``--version`` cai em ``VERSAO_FONTE`` quando o pacote não está instalado."""

    assert versao.VERSAO_FONTE == _projeto()["version"]


def _requisito(nome: str) -> Requirement:
    for texto in _projeto()["dependencies"]:
        requisito = Requirement(texto)
        if canonicalize_name(requisito.name) == canonicalize_name(nome):
            return requisito
    pytest.fail(f"'{nome}' não está em [project].dependencies do pyproject.toml")


def test_faixa_do_starter_aceita_o_starter_testado():
    testado = Version(notion_starter.__version__)
    requisito = _requisito("notion-starter")

    assert requisito.specifier.contains(testado, prereleases=True), (
        f"A suíte testa o notion-starter {testado}, mas a CLI declara "
        f"'{requisito}'. Publique o starter e ajuste a faixa no mesmo passo."
    )


def test_piso_do_starter_e_a_serie_testada():
    """Com o piso numa série anterior, o pip aceita um starter publicado sem as
    APIs que a CLI importa no topo. Foi o que aconteceu com ``>=0.3.0,<0.4.0``:
    com o 0.3.1 do PyPI, a CLI inteira não importava (nem ``--help``)."""

    testado = Version(notion_starter.__version__)
    pisos = [
        Version(clausula.version)
        for clausula in _requisito("notion-starter").specifier
        if clausula.operator in (">=", "==", "~=")
    ]

    assert pisos, "A faixa do notion-starter precisa de um piso (>=)."
    assert max(pisos).release[:2] == testado.release[:2], (
        f"O piso {max(pisos)} é de outra série que o starter testado ({testado})."
    )
