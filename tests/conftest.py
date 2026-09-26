"""Configuração de testes: adiciona a raiz do repositório ao ``sys.path``
para importar o pacote de topo ``cli`` sem instalação."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_STARTER_SRC = _ROOT.parent / "notion-starter" / "src"

if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
if _STARTER_SRC.exists() and str(_STARTER_SRC) not in sys.path:
    sys.path.insert(0, str(_STARTER_SRC))

from notion_starter.services.backups import VARIAVEL_DIRETORIO_BACKUP  # noqa: E402

from core import workspaces  # noqa: E402


@pytest.fixture(autouse=True)
def backups_isolados(tmp_path_factory, monkeypatch):
    """Manda os backups em JSON de ``reordenar-bloco`` para uma pasta temporária.

    O backup deixou de cair no diretório corrente (onde acabava versionado
    num repositório git) e passou para a pasta de estado do usuário. Sem esta
    fixture, a suíte gravaria nessa pasta real a cada teste de reordenação.
    """

    monkeypatch.setenv(VARIAVEL_DIRETORIO_BACKUP, str(tmp_path_factory.mktemp("backups")))


@pytest.fixture(autouse=True)
def perfis_isolados(tmp_path, monkeypatch):
    """Impede que o perfil REAL da máquina vaze para dentro dos testes.

    O store de perfis (`.notion-workspaces.json`) mora ao lado do pacote. Se o
    arquivo existir na máquina de quem roda a suíte, `aplicar_perfil` exporta
    token e `NOTION_DATABASE_ID` de verdade no ambiente do processo, e testes
    que só queriam um double passam a falar com a configuração real — falhando
    (ou pior, passando) por um motivo que não tem nada a ver com o código.

    Foi exatamente o que aconteceu ao copiar o store para o diretório do módulo
    durante uma validação manual: três testes ficaram vermelhos sem nenhuma
    mudança de comportamento. O padrão aponta para o mesmo tipo de defeito de
    isolamento já visto em outros projetos do ecossistema.
    """

    monkeypatch.setattr(workspaces, "ARQUIVO_PADRAO", tmp_path / "workspaces.json")
    for variavel in (workspaces.ENV_TOKEN, workspaces.ENV_DATABASE, workspaces.ENV_PERFIL):
        monkeypatch.delenv(variavel, raising=False)
