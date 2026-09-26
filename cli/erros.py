"""Envelope de erro da CLI: toda falha vira um código estável, não só um texto.

Quem opera a CLI é, na maior parte das vezes, um modelo de IA. Com só uma
mensagem em português, decidir o próximo passo exigia interpretar o texto
("Recurso não encontrado." e "Tarefa não encontrada." eram o mesmo caso, com
códigos de saída diferentes). Aqui cada exceção vira um :class:`ErroClassificado`
com um ``codigo`` estável, o status HTTP e o ``code`` do Notion quando existem,
um ``proximo_passo`` quando há um comando óbvio e os ``detalhes`` estruturados
(IDs criados, apagados, pendentes…).

A classificação vem do **tipo** da exceção e dos campos estruturados
(``status_code``, ``codigo`` do corpo do Notion) — nunca do texto da mensagem.
É regra de apresentação da borda: a biblioteca levanta exceções tipadas e a CLI
decide como mostrá-las. O vocabulário reaproveita os códigos que o
``notion-workspace-app`` já usa na API (``validacao``, ``nao_encontrado``,
``erro_upstream``, ``erro_interno``) e acrescenta só os que faltavam.

Código de saída: ``0`` sucesso; ``2`` uso inválido ou recusa antes de qualquer
escrita (nada mudou); ``1`` falha da API, da rede, no meio de uma escrita ou
interna.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any, Literal, get_args

from notion_starter.exceptions import (
    BlocoSemTextoError,
    ConteudoInvalidoError,
    EdicaoDeBlocoError,
    EdicaoMultiblocoError,
    EscritaAbaixoDeDatabaseError,
    EscritaParcialError,
    ExclusaoArriscadaError,
    IdNotionInvalidoError,
    LimpezaIncompletaError,
    NotionAPIError,
    NotionConfigurationError,
    NotionEscritaSalvaError,
    NotionHTTPError,
    NotionSchemaError,
    NotionSyncError,
    PerdaDeFormatacaoError,
    RichTextNaoRegravavelError,
    TrechoAmbiguoError,
    TrechoAtravessaItensError,
    TrechoNaoEncontradoError,
    TrocaDeTipoError,
)
from notion_starter.services.ingestao import ChaveDePlanilhaInvalidaError
from notion_starter.services.relacoes import RelacaoGrandeDemaisError
from notion_starter.services.reordenacao import (
    BlocoComFilhosError,
    BlocoNaoReordenavelError,
    ReordenacaoIncompletaError,
    ReordenacaoRecusadaError,
)

from core import workspaces as perfis_workspace

CodigoErro = Literal[
    # Entrada e uso (saída 2: nada foi alterado)
    "validacao",
    "uso_invalido",
    "id_invalido",
    "configuracao",
    "conteudo_invalido",
    "escrita_abaixo_de_database",
    "schema_incompativel",
    "bloco_nao_reordenavel",
    "exclusao_arriscada",
    "edicao_multibloco",
    "troca_de_tipo",
    "perda_de_formatacao",
    "bloco_sem_texto",
    "trecho_nao_encontrado",
    "trecho_ambiguo",
    "trecho_atravessa_itens",
    "texto_nao_regravavel",
    "edicao_recusada",
    # Respostas do Notion
    "nao_encontrado",
    "sem_acesso",
    "validacao_notion",
    "conflito",
    "limite_de_taxa",
    "erro_upstream",
    # Escritas que começaram e não terminaram (saída 1)
    "escrita_salva",
    "escrita_parcial",
    "limpeza_incompleta",
    "reordenacao_incompleta",
    "criacao_incompleta",
    "restauracao_falhou",
    # Demais falhas
    "erro_operacao",
    "erro_interno",
]

#: Todos os códigos possíveis, na ordem acima — o ``guia`` os lista.
CODIGOS_ERRO: tuple[str, ...] = get_args(CodigoErro)

#: Uso inválido ou recusa antes de escrever: nada mudou no Notion.
SAIDA_USO = 2
#: Falha da API, da rede, no meio de uma escrita ou interna.
SAIDA_FALHA = 1


class CLIError(NotionSyncError, RuntimeError):
    """Erro esperado de uso/configuração, seguro para exibir ao consumidor.

    Deriva de ``NotionSyncError`` (padrão do ecossistema) e continua sendo um
    ``RuntimeError``, o tipo que tinha antes.

    Attributes:
        codigo: Código estável do envelope (padrão ``validacao``).
        saida: Código de saída do processo (padrão 2, uso inválido).
        proximo_passo: Comando sugerido, quando há um óbvio.
        detalhes: Dados estruturados para quem lê o JSON.
    """

    def __init__(
        self,
        mensagem: str,
        *,
        codigo: CodigoErro = "validacao",
        saida: int = SAIDA_USO,
        proximo_passo: str | None = None,
        detalhes: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(mensagem)
        self.codigo: CodigoErro = codigo
        self.saida = saida
        self.proximo_passo = proximo_passo
        self.detalhes: dict[str, Any] = dict(detalhes or {})


@dataclass(frozen=True)
class ErroClassificado:
    """Uma falha pronta para o envelope ``{"ok": false, "erro": {...}}``."""

    codigo: CodigoErro
    mensagem: str
    saida: int
    proximo_passo: str | None = None
    http_status: int | None = None
    notion_code: str | None = None
    detalhes: dict[str, Any] = field(default_factory=dict)

    def para_dict(self) -> dict[str, Any]:
        """O objeto ``erro`` do envelope — sempre com as mesmas chaves."""

        return {
            "codigo": self.codigo,
            "mensagem": self.mensagem,
            "proximo_passo": self.proximo_passo,
            "http_status": self.http_status,
            "notion_code": self.notion_code,
            "detalhes": dict(self.detalhes),
        }


# -- Mensagens do Notion ---------------------------------------------------------


def detalhe_notion(corpo: str) -> str:
    """Extrai o ``message`` do corpo de erro do Notion, com o cru de reserva."""

    texto = (corpo or "").strip()
    if not texto:
        return "sem detalhe na resposta"
    try:
        dados = json.loads(texto)
    except ValueError:
        return texto
    if isinstance(dados, dict):
        mensagem = str(dados.get("message") or "").strip()
        codigo = str(dados.get("code") or "").strip()
        if mensagem:
            return f"{mensagem} [{codigo}]" if codigo else mensagem
    return texto


def sufixo_perfil_ativo() -> str:
    """Nomeia o perfil ativo junto de um 404.

    "ID válido devolvendo 404 quase nunca é permissão — é o perfil salvo
    apontando para outro workspace, e ele vence o NOTION_TOKEN do ambiente em
    silêncio". Com o nome junto do erro, confirmar a suspeita não custa outra
    chamada (``perfis listar``).

    Best-effort: uma falha ao ler o arquivo de perfis (ausente, corrompido) não
    pode esconder o 404 original atrás de um traceback novo.
    """

    try:
        alias = perfis_workspace.carregar_store().ativo
    except Exception:  # noqa: BLE001 - o 404 original é o que importa
        return ""
    if not alias:
        return ""
    return (
        f" Perfil ativo: '{alias}' — se o ID existe noutro workspace, confira "
        "com 'perfis listar' antes de investigar compartilhamento com a integração."
    )


def mensagem_erro_notion(exc: NotionAPIError) -> str:
    """Traduz a falha da API numa mensagem que diz o que fazer a seguir.

    A resposta 400 do Notion nomeia exatamente a propriedade recusada; ela
    chega inteira a quem lê, em vez de um genérico "falhou".
    """

    if isinstance(exc, NotionEscritaSalvaError):
        return str(exc)
    if not isinstance(exc, NotionHTTPError):
        return "Falha ao falar com o Notion."
    if exc.status_code == 404:
        return f"Recurso não encontrado.{sufixo_perfil_ativo()}"
    return f"Notion recusou a requisição (HTTP {exc.status_code}): {detalhe_notion(exc.body)}"


def _codigo_http(status: int) -> CodigoErro:
    if status == 404:
        return "nao_encontrado"
    if status in (401, 403):
        return "sem_acesso"
    if status == 400:
        return "validacao_notion"
    if status == 409:
        return "conflito"
    if status == 429:
        return "limite_de_taxa"
    return "erro_upstream"


def _causa_http(exc: BaseException | None) -> NotionHTTPError | None:
    """A primeira ``NotionHTTPError`` na cadeia de causas, se houver."""

    vistos: set[int] = set()
    atual = exc
    while atual is not None and id(atual) not in vistos:
        if isinstance(atual, NotionHTTPError):
            return atual
        vistos.add(id(atual))
        atual = getattr(atual, "causa", None) or atual.__cause__
    return None


def _texto_causa(causa: BaseException | None) -> str:
    if causa is None:
        return ""
    if isinstance(causa, NotionAPIError):
        return mensagem_erro_notion(causa)
    return str(causa)


def _pares(itens: list[tuple[str, str]]) -> list[dict[str, str]]:
    return [{"id": bloco_id, "tipo": tipo} for bloco_id, tipo in itens]


def comando_restaurar(ids: list[str]) -> str:
    """O comando que desfaz a exclusão destes blocos."""

    return "notion-tasks restaurar-bloco " + " ".join(ids)


#: Blocos que ``restaurar-bloco`` (PATCH /blocks/{id}) não traz de volta. A
#: documentação de "Delete a block" manda restaurar bloco de página por "Update
#: page", e a API respondeu 400 "Updating a page via the blocks endpoint
#: unsupported" (medido para child_page); child_database vai junto por analogia.
TIPOS_SEM_RESTAURACAO_POR_BLOCO = frozenset({"child_page", "child_database"})

_COMO_RESTAURAR_PAGINA = (
    "Subpágina e database não voltam por 'restaurar-bloco': a API só os restaura "
    "pelo endpoint de página/database, que a biblioteca ainda não expõe. Restaure "
    "pela Lixeira do Notion."
)


def dados_desfazer(apagados: list[tuple[str, str]]) -> dict[str, Any]:
    """``desfazer`` (comando pronto) para os blocos e ``desfazer_manual`` para páginas."""

    sem_bloco = TIPOS_SEM_RESTAURACAO_POR_BLOCO
    blocos = [bloco_id for bloco_id, tipo in apagados if tipo not in sem_bloco]
    paginas = [bloco_id for bloco_id, tipo in apagados if tipo in sem_bloco]
    dados: dict[str, Any] = {}
    if blocos:
        dados["desfazer"] = comando_restaurar(blocos)
    if paginas:
        dados["desfazer_manual"] = {"ids": paginas, "como": _COMO_RESTAURAR_PAGINA}
    return dados


# -- Escritas que começaram --------------------------------------------------------


def _escrita_parcial(exc: EscritaParcialError) -> ErroClassificado:
    mensagem = str(exc)
    if isinstance(exc.causa, NotionAPIError):
        # A biblioteca cita o erro cru ("Notion HTTP 400: {json}"); a borda
        # troca pela mensagem legível do Notion.
        mensagem = mensagem.replace(str(exc.causa), _texto_causa(exc.causa))
    sobrou = bool(exc.criados) or exc.lote_incerto
    if not sobrou:
        mensagem += " Nada do conteúdo novo ficou na página: corrija a causa e repita o comando."
    http = _causa_http(exc)
    detalhes: dict[str, Any] = {
        "page_id": exc.page_id,
        "total": exc.total,
        "blocos_criados": _pares(exc.criados),
        "desfeitos": list(exc.desfeitos),
        "lote_incerto": exc.lote_incerto,
        "substituicao": exc.substituicao,
    }
    if isinstance(exc.causa, NotionEscritaSalvaError):
        # O 503 de escrita salva diz quais blocos o lote incerto criou.
        detalhes["filhos_criados_no_lote_incerto"] = list(exc.causa.filhos_criados)
    return ErroClassificado(
        codigo="escrita_parcial",
        mensagem=mensagem,
        saida=SAIDA_FALHA,
        proximo_passo=f"notion-tasks blocos {exc.page_id}" if sobrou else None,
        http_status=http.status_code if http else None,
        notion_code=http.codigo if http else None,
        detalhes=detalhes,
    )


def _limpeza_incompleta(exc: LimpezaIncompletaError) -> ErroClassificado:
    apagados = [bloco_id for bloco_id, _ in exc.apagados]
    desfazer = dados_desfazer(exc.apagados)
    pendentes = [bloco_id for bloco_id, _ in exc.pendentes]
    mensagem = (
        f"A limpeza parou no meio ({_texto_causa(exc.causa) or 'causa desconhecida'}). "
        f"Já na lixeira: {', '.join(apagados) or 'nenhum'}. "
        f"Ainda na página: {', '.join(pendentes) or 'nenhum'}."
    )
    if exc.blocos_novos:
        mensagem += f" O conteúdo novo já foi escrito ({len(exc.blocos_novos)} blocos)."
    mensagem += (
        " Para desfazer, restaure os apagados com 'restaurar-bloco' (voltam no fim da "
        "página); para concluir, repita o comando."
    )
    http = _causa_http(exc)
    return ErroClassificado(
        codigo="limpeza_incompleta",
        mensagem=mensagem,
        saida=SAIDA_FALHA,
        proximo_passo=desfazer.get("desfazer"),
        http_status=http.status_code if http else None,
        notion_code=http.codigo if http else None,
        detalhes={
            "blocos_apagados_ids": _pares(exc.apagados),
            "pendentes": _pares(exc.pendentes),
            "blocos_novos": list(exc.blocos_novos),
            **desfazer,
        },
    )


def _reordenacao_incompleta(exc: ReordenacaoIncompletaError) -> ErroClassificado:
    if exc.etapa == "excluir":
        proximo: str | None = f"notion-tasks apagar-bloco {exc.bloco_id_antigo} --sim"
    else:
        proximo = None
    http = _causa_http(exc)
    return ErroClassificado(
        codigo="reordenacao_incompleta",
        mensagem=str(exc),
        saida=SAIDA_FALHA,
        proximo_passo=proximo,
        http_status=http.status_code if http else None,
        notion_code=http.codigo if http else None,
        detalhes={
            "etapa": exc.etapa,
            "bloco_id_antigo": exc.bloco_id_antigo,
            "bloco_id_novo": exc.bloco_id_novo,
            "backup_path": exc.backup_path,
            "original_intacto": exc.original_intacto,
            "copia_incerta": exc.copia_incerta,
        },
    )


# -- Recusas antes de escrever ------------------------------------------------------


def _recusa_de_edicao(exc: EdicaoDeBlocoError) -> ErroClassificado:
    """Recusas de ``editar_bloco``/``trocar_trecho`` — nada foi alterado."""

    codigo: CodigoErro = "edicao_recusada"
    detalhes: dict[str, Any] = {}
    if isinstance(exc, EdicaoMultiblocoError):
        codigo, detalhes = "edicao_multibloco", {"quantidade": exc.quantidade}
    elif isinstance(exc, TrocaDeTipoError):
        codigo = "troca_de_tipo"
        detalhes = {"tipo_atual": exc.tipo_atual, "tipo_pedido": exc.tipo_pedido}
    elif isinstance(exc, PerdaDeFormatacaoError):
        codigo, detalhes = "perda_de_formatacao", {"perdas": list(exc.perdas)}
    elif isinstance(exc, BlocoSemTextoError):
        codigo, detalhes = "bloco_sem_texto", {"tipo": exc.tipo}
    elif isinstance(exc, TrechoNaoEncontradoError):
        codigo, detalhes = "trecho_nao_encontrado", {"trecho": exc.trecho}
    elif isinstance(exc, TrechoAmbiguoError):
        codigo, detalhes = "trecho_ambiguo", {"ocorrencias": exc.ocorrencias}
    elif isinstance(exc, TrechoAtravessaItensError):
        codigo = "trecho_atravessa_itens"
    return ErroClassificado(codigo=codigo, mensagem=str(exc), saida=SAIDA_USO, detalhes=detalhes)


def _recusa_de_reordenacao(exc: ReordenacaoRecusadaError) -> ErroClassificado:
    detalhes: dict[str, Any] = {}
    if isinstance(exc, BlocoComFilhosError):
        detalhes = {"bloco_id": exc.bloco_id, "tipo": exc.tipo, "tem_filhos": True}
    elif isinstance(exc, BlocoNaoReordenavelError):
        detalhes = {"tipo": exc.tipo}
    return ErroClassificado(
        codigo="bloco_nao_reordenavel", mensagem=str(exc), saida=SAIDA_USO, detalhes=detalhes
    )


def _erro_de_valor(exc: ValueError) -> ErroClassificado:
    """Entrada inválida (``ValueError`` e derivadas sem código próprio)."""

    if isinstance(exc, IdNotionInvalidoError):
        return ErroClassificado(
            codigo="id_invalido",
            mensagem=str(exc),
            saida=SAIDA_USO,
            proximo_passo="notion-tasks buscar <termo>",
            detalhes={"valor": exc.valor},
        )
    if isinstance(exc, ConteudoInvalidoError):
        return ErroClassificado(
            codigo="conteudo_invalido",
            mensagem=str(exc),
            saida=SAIDA_USO,
            detalhes={"problemas": list(exc.problemas)},
        )
    if isinstance(exc, EdicaoDeBlocoError):
        return _recusa_de_edicao(exc)
    if isinstance(exc, RichTextNaoRegravavelError):
        return ErroClassificado(
            codigo="texto_nao_regravavel",
            mensagem=str(exc),
            saida=SAIDA_USO,
            detalhes={"tipo": exc.tipo},
        )
    if isinstance(exc, ExclusaoArriscadaError):
        return ErroClassificado(
            codigo="exclusao_arriscada",
            mensagem=str(exc),
            saida=SAIDA_USO,
            detalhes={"tipo": exc.tipo, "titulo": exc.titulo},
        )
    if isinstance(exc, ReordenacaoRecusadaError):
        return _recusa_de_reordenacao(exc)
    if isinstance(exc, perfis_workspace.WorkspaceConfigError):
        return ErroClassificado(codigo="configuracao", mensagem=str(exc), saida=SAIDA_USO)
    detalhes: dict[str, Any] = {}
    if isinstance(exc, ChaveDePlanilhaInvalidaError):
        detalhes = {"problemas": list(exc.problemas)}
    elif isinstance(exc, RelacaoGrandeDemaisError):
        detalhes = {"page_id": exc.page_id, "coluna": exc.coluna, "tamanho": exc.tamanho}
    return ErroClassificado(
        codigo="validacao", mensagem=str(exc), saida=SAIDA_USO, detalhes=detalhes
    )


def _erro_do_notion(exc: NotionAPIError) -> ErroClassificado:
    """Resposta de erro, rede ou resposta inválida do Notion."""

    if isinstance(exc, NotionEscritaSalvaError):
        # Não é recusa: o Notion GRAVOU e não conseguiu responder. Repetir duplica.
        return ErroClassificado(
            codigo="escrita_salva",
            mensagem=str(exc),
            saida=SAIDA_FALHA,
            http_status=exc.status_code,
            notion_code=exc.codigo,
            detalhes={"recurso_id": exc.recurso_id, "filhos_criados": list(exc.filhos_criados)},
        )
    if isinstance(exc, NotionHTTPError):
        detalhes = {"dados_adicionais": exc.dados_adicionais} if exc.dados_adicionais else {}
        return ErroClassificado(
            codigo=_codigo_http(exc.status_code),
            mensagem=mensagem_erro_notion(exc),
            saida=SAIDA_FALHA,
            proximo_passo="notion-tasks perfis listar" if exc.status_code == 404 else None,
            http_status=exc.status_code,
            notion_code=exc.codigo,
            detalhes=detalhes,
        )
    return ErroClassificado(
        codigo="erro_upstream", mensagem=mensagem_erro_notion(exc), saida=SAIDA_FALHA
    )


def classificar_erro(exc: BaseException) -> ErroClassificado:
    """Converte qualquer exceção levantada por um comando num :class:`ErroClassificado`.

    A ordem importa: subclasses antes das bases (``NotionEscritaSalvaError``
    antes de ``NotionHTTPError``; recusas tipadas antes de ``ValueError``).
    """

    if isinstance(exc, CLIError):
        http = _causa_http(exc.__cause__)
        return ErroClassificado(
            codigo=exc.codigo,
            mensagem=str(exc),
            saida=exc.saida,
            proximo_passo=exc.proximo_passo,
            http_status=http.status_code if http else None,
            notion_code=http.codigo if http else None,
            detalhes=exc.detalhes,
        )
    if isinstance(exc, EscritaAbaixoDeDatabaseError):
        databases = [
            {"id": database_id, "titulo": titulo or "(sem título)"}
            for database_id, titulo in exc.databases
        ]
        return ErroClassificado(
            codigo="escrita_abaixo_de_database",
            mensagem=str(exc),
            saida=SAIDA_USO,
            proximo_passo=f"notion-tasks linhas {databases[0]['id']}" if databases else None,
            detalhes={"databases_dentro": databases},
        )
    if isinstance(exc, NotionSchemaError):
        return ErroClassificado(
            codigo="schema_incompativel",
            mensagem=f"{exc} — rode 'schema <database_id>' para ver as colunas reais.",
            saida=SAIDA_USO,
            proximo_passo="notion-tasks schema <database_id>",
            detalhes={
                "faltando": list(exc.faltando),
                "tipo_errado": [list(item) for item in exc.tipo_errado],
            },
        )
    if isinstance(exc, EscritaParcialError):
        return _escrita_parcial(exc)
    if isinstance(exc, LimpezaIncompletaError):
        return _limpeza_incompleta(exc)
    if isinstance(exc, ReordenacaoIncompletaError):
        return _reordenacao_incompleta(exc)
    if isinstance(exc, ValueError):
        return _erro_de_valor(exc)
    if isinstance(exc, NotionAPIError):
        return _erro_do_notion(exc)
    if isinstance(exc, NotionConfigurationError):
        return ErroClassificado(
            codigo="configuracao", mensagem="Configuração do Notion inválida.", saida=SAIDA_USO
        )
    if isinstance(exc, NotionSyncError):
        return ErroClassificado(codigo="erro_operacao", mensagem=str(exc), saida=SAIDA_FALHA)
    return ErroClassificado(
        codigo="erro_interno",
        mensagem=f"Erro interno inesperado ({type(exc).__name__}): {exc}",
        saida=SAIDA_FALHA,
        detalhes={"tipo": type(exc).__name__},
    )
