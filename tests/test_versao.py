"""Testes da versão embutida no bundle PyInstaller."""

from __future__ import annotations

from pathlib import Path

from cli import versao


def test_versao_embutida_so_e_lida_em_binario(monkeypatch, tmp_path):
    """O arquivo de build não deve alterar a versão durante o desenvolvimento."""

    arquivo_cli = tmp_path / "cli"
    arquivo_cli.mkdir()
    (arquivo_cli / versao.NOME_ARQUIVO_VERSAO_NATIVA).write_text("0.4.0\n", encoding="utf-8")
    monkeypatch.setattr(versao, "__file__", str(arquivo_cli / "versao.py"))
    monkeypatch.setattr(versao.sys, "frozen", False, raising=False)
    assert versao.ler_versao_embutida() is None

    monkeypatch.setattr(versao.sys, "frozen", True, raising=False)
    assert versao.ler_versao_embutida() == "0.4.0"


def test_versao_embutida_tolera_arquivo_ausente(monkeypatch, tmp_path):
    """Bundles antigos continuam usando o fallback de metadata."""

    monkeypatch.setattr(versao, "__file__", str(Path(tmp_path) / "versao.py"))
    monkeypatch.setattr(versao.sys, "frozen", True, raising=False)
    monkeypatch.setattr(versao.sys, "_MEIPASS", str(tmp_path), raising=False)
    assert versao.ler_versao_embutida() is None
