"""Constrói e valida um executável nativo da matriz oficial.

O workflow chama este script uma vez por alvo. A lógica fica em Python para que
nomes de assets, versão embutida, checksum e smoke permaneçam iguais em todos
os runners, inclusive no Windows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
ENTRADA = Path(__file__).with_name("native_entrypoint.py")
VERSAO_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


@dataclass(frozen=True)
class Alvo:
    """Nome e extensão do executável produzidos para um runner."""

    identificador: str
    asset: str
    extensao: str = ""


ALVOS = {
    "windows-x64": Alvo("windows-x64", "notion-automacoes-windows-x64.exe", ".exe"),
    "macos-x64": Alvo("macos-x64", "notion-automacoes-macos-x64"),
    "macos-arm64": Alvo("macos-arm64", "notion-automacoes-macos-arm64"),
    "linux-x64": Alvo("linux-x64", "notion-automacoes-linux-x64"),
}


def normalizar_versao(valor: str) -> str:
    """Aceita somente tags SemVer estáveis no formato vX.Y.Z."""

    correspondencia = VERSAO_RE.fullmatch(valor.strip())
    if not correspondencia:
        raise ValueError(f"Versão inválida: {valor!r}; use vX.Y.Z.")
    return ".".join(correspondencia.groups())


def obter_alvo(identificador: str) -> Alvo:
    """Retorna um alvo documentado ou falha antes de iniciar o build."""

    try:
        return ALVOS[identificador]
    except KeyError as exc:
        aceitos = ", ".join(ALVOS)
        raise ValueError(f"Alvo inválido: {identificador!r}; aceitos: {aceitos}.") from exc


def sha256(caminho: Path) -> str:
    """Calcula o digest sem carregar o executável inteiro na memória."""

    digest = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1024 * 1024), b""):
            digest.update(bloco)
    return digest.hexdigest()


def caminho_checksum(caminho: Path) -> Path:
    """Retorna o asset irmão usado pelo updater nativo."""

    return caminho.with_name(f"{caminho.name}.sha256")


def construir_comando(
    alvo: Alvo,
    versao: str,
    diretorio_saida: Path,
    diretorio_trabalho: Path,
) -> list[str]:
    """Monta o comando PyInstaller sem depender do shell do runner."""

    arquivo_versao = diretorio_trabalho / "notion-automacoes-version.txt"
    diretorio_spec = diretorio_trabalho / "spec"
    return [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        "--clean",
        "--onefile",
        "--name",
        alvo.asset.removesuffix(alvo.extensao),
        "--distpath",
        str(diretorio_saida),
        "--workpath",
        str(diretorio_trabalho / "work"),
        "--specpath",
        str(diretorio_spec),
        "--add-data",
        f"{arquivo_versao}{os.pathsep}cli",
        "--copy-metadata",
        "notion-automacoes",
        "--collect-submodules",
        "notion_starter",
        str(ENTRADA),
    ]


def construir(identificador: str, versao: str, diretorio_saida: Path) -> dict[str, object]:
    """Executa o build, escreve o checksum e devolve o manifesto do asset."""

    alvo = obter_alvo(identificador)
    versao_normalizada = normalizar_versao(versao)
    saida = Path(diretorio_saida).resolve()
    trabalho = saida.parent / f".native-build-{alvo.identificador}"
    trabalho.mkdir(parents=True, exist_ok=True)
    saida.mkdir(parents=True, exist_ok=True)
    (trabalho / "spec").mkdir(parents=True, exist_ok=True)
    (trabalho / "notion-automacoes-version.txt").write_text(
        versao_normalizada + "\n", encoding="utf-8"
    )

    comando = construir_comando(alvo, versao_normalizada, saida, trabalho)
    subprocess.run(comando, cwd=RAIZ, check=True)

    executavel = saida / alvo.asset
    if not executavel.is_file():
        raise RuntimeError(f"PyInstaller não produziu o asset esperado: {executavel}.")
    if not alvo.extensao:
        modo = executavel.stat().st_mode
        executavel.chmod(modo | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    digest = sha256(executavel)
    arquivo_checksum = caminho_checksum(executavel)
    arquivo_checksum.write_text(f"{digest}  {executavel.name}\n", encoding="utf-8")
    manifesto = {
        "alvo": asdict(alvo),
        "versao": versao_normalizada,
        "executavel": str(executavel),
        "checksum": str(arquivo_checksum),
        "sha256": digest,
        "comando": comando,
    }
    print(json.dumps(manifesto, ensure_ascii=False, indent=2, sort_keys=True))
    return manifesto


def construir_parser() -> argparse.ArgumentParser:
    """Monta a interface usada localmente e no workflow."""

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", dest="alvo", choices=tuple(ALVOS), required=True)
    parser.add_argument("--version", dest="versao", required=True, help="tag vX.Y.Z")
    parser.add_argument("--output", dest="saida", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Executa o build do alvo solicitado."""

    args = construir_parser().parse_args(argv)
    construir(args.alvo, args.versao, args.saida)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
