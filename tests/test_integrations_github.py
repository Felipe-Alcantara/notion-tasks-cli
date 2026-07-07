"""Testes do parsing de login do GitHub (URL de perfil, @handle ou nome puro)."""

from __future__ import annotations

import pytest

from integrations.github import GitHubClient, extrair_login


@pytest.mark.parametrize(
    "entrada, esperado",
    [
        ("Felipe-Alcantara", "Felipe-Alcantara"),
        ("  Felipe-Alcantara  ", "Felipe-Alcantara"),
        ("@Felipe-Alcantara", "Felipe-Alcantara"),
        ("https://github.com/Felipe-Alcantara", "Felipe-Alcantara"),
        ("https://github.com/Felipe-Alcantara/", "Felipe-Alcantara"),
        ("github.com/Felipe-Alcantara", "Felipe-Alcantara"),
        ("https://github.com/Felipe-Alcantara?tab=repositories", "Felipe-Alcantara"),
        ("", ""),
    ],
)
def test_extrair_login(entrada, esperado):
    assert extrair_login(entrada) == esperado


def test_validar_usuario_aceita_url_de_perfil():
    # A URL é normalizada para o login antes de validar.
    assert GitHubClient._validar_usuario("https://github.com/Felipe-Alcantara") == (
        "Felipe-Alcantara"
    )


def test_validar_usuario_rejeita_login_invalido():
    with pytest.raises(ValueError):
        GitHubClient._validar_usuario("nome invalido/com barra")
