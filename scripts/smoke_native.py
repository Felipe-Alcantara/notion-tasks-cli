"""Executa comandos básicos diretamente no binário, sem importar o pacote."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


def executar(executavel: Path, *argumentos: str) -> str:
    """Executa o binário e transforma uma falha em erro legível."""

    resultado = subprocess.run(
        [str(executavel), *argumentos],
        capture_output=True,
        text=True,
        check=False,
    )
    if resultado.returncode:
        raise RuntimeError(
            f"Smoke falhou em {' '.join(argumentos)} (código {resultado.returncode}): "
            f"{resultado.stdout}\n{resultado.stderr}"
        )
    return resultado.stdout


def main(argv: list[str] | None = None) -> int:
    """Confere versão, ajuda, guia legado e diagnóstico sem credenciais."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--executable", type=Path, required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args(argv)
    executavel = args.executable.resolve()
    if not executavel.is_file():
        raise FileNotFoundError(f"Executável não encontrado: {executavel}")

    versao = executar(executavel, "--version")
    versao_esperada = args.version.removeprefix("v")
    if versao_esperada not in versao:
        raise RuntimeError(
            f"Versão inesperada: {versao!r}; esperado {versao_esperada!r}."
        )
    executar(executavel, "--help")
    executar(executavel, "tasks", "--help")
    diagnostico = json.loads(executar(executavel, "--json", "doctor"))
    if diagnostico.get("ok") is not True:
        raise RuntimeError(f"Doctor do binário retornou erro: {diagnostico!r}")
    print(f"Smoke nativo aprovado: {executavel.name} ({args.version})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
