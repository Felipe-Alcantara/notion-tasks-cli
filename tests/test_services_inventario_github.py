"""Testes do filtro de repositórios arquivados na coleta do inventário GitHub."""

from __future__ import annotations

from integrations.github import RepoInfo
from services import inventario_github as svc


class _GitHubFake:
    """GitHubClient mínimo: devolve os repos passados por conta ou por repo completo."""

    def __init__(
        self,
        por_conta: dict[str, list[RepoInfo]],
        por_repo_completo: dict[str, RepoInfo] | None = None,
    ):
        self._por_conta = por_conta
        self._por_repo_completo = por_repo_completo or {}

    def listar_repos(self, conta: str) -> list[RepoInfo]:
        return self._por_conta.get(conta, [])

    def detalhar_repo(self, repo_completo: str) -> RepoInfo:
        return self._por_repo_completo[repo_completo]


def _repo(nome: str, *, arquivado: bool = False, atualizado_em: str | None = None) -> RepoInfo:
    return RepoInfo(
        nome=nome,
        nome_completo=f"conta/{nome}",
        url_html=f"https://github.com/conta/{nome}",
        arquivado=arquivado,
        atualizado_em=atualizado_em,
    )


def _pagina_com_data(data_iso: str | None) -> dict:
    """Simula uma página existente com a coluna 'Atualizado em' preenchida."""

    campo = svc.CamposGitHub().atualizado_em
    date_val = {"type": "date", "date": {"start": data_iso}} if data_iso else None
    return {"id": "page-1", "properties": {campo: date_val}}


def test_coletar_repos_inclui_arquivados_por_padrao():
    gh = _GitHubFake({"conta": [_repo("ativo"), _repo("velho", arquivado=True)]})
    resumo = svc.ResumoInventario()

    nomes = [r.nome for r in svc._coletar_repos(["conta"], gh, resumo)]

    assert nomes == ["ativo", "velho"]
    assert resumo.repos_encontrados == 2


def test_coletar_repos_ignora_arquivados_quando_pedido():
    gh = _GitHubFake({"conta": [_repo("ativo"), _repo("velho", arquivado=True)]})
    resumo = svc.ResumoInventario()

    nomes = [
        r.nome
        for r in svc._coletar_repos(["conta"], gh, resumo, ignorar_arquivados=True)
    ]

    assert nomes == ["ativo"]
    # Arquivado pulado não entra na contagem.
    assert resumo.repos_encontrados == 1


# -- repositório específico (owner/repo), sem importar a conta inteira ----


def test_repo_completo_da_entrada_reconhece_owner_repo():
    assert svc._repo_completo_da_entrada("dono/projeto") == "dono/projeto"


def test_repo_completo_da_entrada_reconhece_url_de_repo():
    assert (
        svc._repo_completo_da_entrada("https://github.com/dono/projeto")
        == "dono/projeto"
    )
    assert (
        svc._repo_completo_da_entrada("https://github.com/dono/projeto.git")
        == "dono/projeto"
    )


def test_repo_completo_da_entrada_none_para_conta():
    assert svc._repo_completo_da_entrada("dono") is None
    assert svc._repo_completo_da_entrada("@dono") is None
    assert svc._repo_completo_da_entrada("https://github.com/dono") is None
    assert svc._repo_completo_da_entrada("https://github.com/dono/") is None


def test_coletar_repos_aceita_repositorio_especifico():
    repo = _repo("projeto")
    gh = _GitHubFake({}, {"dono/projeto": repo})
    resumo = svc.ResumoInventario()

    encontrados = list(svc._coletar_repos(["dono/projeto"], gh, resumo))

    assert encontrados == [repo]
    assert resumo.repos_encontrados == 1


def test_coletar_repos_combina_conta_e_repositorio_especifico_sem_duplicar():
    repo_da_conta = _repo("ja-listado")
    repo_avulso = _repo("avulso")
    gh = _GitHubFake(
        {"conta": [repo_da_conta]},
        {"conta/ja-listado": repo_da_conta, "outro/avulso": repo_avulso},
    )
    resumo = svc.ResumoInventario()

    nomes = [
        r.nome
        for r in svc._coletar_repos(["conta", "conta/ja-listado", "outro/avulso"], gh, resumo)
    ]

    # "conta/ja-listado" já veio pela conta — não duplica por causa da chave por URL.
    assert nomes == ["ja-listado", "avulso"]
    assert resumo.repos_encontrados == 2


# -- detecção de mudança (sync incremental) -------------------------------


def test_repo_mudou_quando_updated_at_avancou():
    repo = _repo("app", atualizado_em="2026-07-07T15:00:00Z")
    pagina = _pagina_com_data("2026-07-06T10:00:00.000+00:00")

    assert svc._repo_mudou_desde_pagina(repo, pagina, svc.CamposGitHub()) is True


def test_repo_nao_mudou_quando_data_igual_apesar_do_formato():
    # GitHub usa 'Z'; o Notion devolve '+00:00' — o mesmo instante não deve
    # contar como mudança.
    repo = _repo("app", atualizado_em="2026-07-06T10:00:00Z")
    pagina = _pagina_com_data("2026-07-06T10:00:00.000+00:00")

    assert svc._repo_mudou_desde_pagina(repo, pagina, svc.CamposGitHub()) is False


def test_repo_mudou_na_duvida_sem_data_gravada():
    repo = _repo("app", atualizado_em="2026-07-06T10:00:00Z")
    pagina = _pagina_com_data(None)

    # Página sem data: na dúvida, atualiza (não pula por engano).
    assert svc._repo_mudou_desde_pagina(repo, pagina, svc.CamposGitHub()) is True
