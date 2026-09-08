"""Leitura da versão embutida nos executáveis nativos."""

from __future__ import annotations

import sys
from pathlib import Path

VERSAO_FONTE = "0.3.0"
NOME_ARQUIVO_VERSAO_NATIVA = "notion-automacoes-version.txt"


def ler_versao_embutida() -> str | None:
    """Lê a versão adicionada pelo builder PyInstaller, quando aplicável."""

    if not getattr(sys, "frozen", False):
        return None

    candidatos = [Path(__file__).with_name(NOME_ARQUIVO_VERSAO_NATIVA)]
    pasta_temporaria = getattr(sys, "_MEIPASS", None)
    if pasta_temporaria:
        candidatos.append(Path(pasta_temporaria) / "cli" / NOME_ARQUIVO_VERSAO_NATIVA)

    for caminho in candidatos:
        try:
            valor = caminho.read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError):
            continue
        if valor:
            return valor
    return None
