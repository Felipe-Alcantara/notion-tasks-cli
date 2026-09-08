"""Testes puros do contrato de empacotamento nativo."""

from __future__ import annotations

import hashlib
import os

import pytest

from scripts import build_native


def test_normaliza_apenas_tags_staveis():
    assert build_native.normalizar_versao("v0.4.0") == "0.4.0"
    assert build_native.normalizar_versao("0.4.1") == "0.4.1"
    with pytest.raises(ValueError, match="Versão inválida"):
        build_native.normalizar_versao("v0.4.0-rc1")


def test_matriz_tem_os_quatro_assets_do_updater():
    assert [alvo.asset for alvo in build_native.ALVOS.values()] == [
        "notion-automacoes-windows-x64.exe",
        "notion-automacoes-macos-x64",
        "notion-automacoes-macos-arm64",
        "notion-automacoes-linux-x64",
    ]


def test_comando_embute_versao_e_metadata(tmp_path):
    alvo = build_native.obter_alvo("linux-x64")
    comando = build_native.construir_comando(
        alvo, "0.4.0", tmp_path / "dist", tmp_path / "work"
    )
    assert "--onefile" in comando
    assert "--copy-metadata" in comando
    assert "notion-automacoes" in comando
    arquivo_versao = tmp_path / "work" / "notion-automacoes-version.txt"
    assert f"{arquivo_versao}{os.pathsep}cli" in comando


def test_sha256_e_checksum_irmão(tmp_path):
    arquivo = tmp_path / "notion-automacoes-linux-x64"
    arquivo.write_bytes(b"binario")
    esperado = hashlib.sha256(b"binario").hexdigest()
    assert build_native.sha256(arquivo) == esperado
    assert build_native.caminho_checksum(arquivo).name == f"{arquivo.name}.sha256"
