"""Preflight de projeto para criar e editar linhas de tarefas.

O workspace usa a URL de referência como identidade externa do repositório e a
coluna ``Projeto`` como relação para a database ``GITHUB``. Este módulo mantém
essa regra específica do CLI fora da borda de argumentos e fora do serviço
genérico de edição de propriedades.

O preflight é somente leitura. A relação é aplicada pela borda, depois que a
linha existe, usando o serviço ``relacionar`` e uma releitura de confirmação.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import unquote, urlsplit

from notion_starter import NotionClient, readers

COLUNA_PROJETO = "Projeto"
COLUNA_URL_REFERENCIA = "URL de referência"
COLUNA_URL_PROJETO = "URL"


@dataclass(frozen=True)
class RepositorioGitHub:
    """Identidade canônica de um repositório GitHub."""

    proprietario: str
    nome: str

    @property
    def identificador(self) -> str:
        """Devolve ``proprietario/nome`` sem variações de URL."""

        return f"{self.proprietario}/{self.nome}"

    @property
    def chave(self) -> str:
        """Chave insensível a maiúsculas, como o GitHub trata a URL."""

        return self.identificador.casefold()

    @property
    def url_canonica(self) -> str:
        """Devolve a URL raiz, sem ``.git``, caminho, query ou fragmento."""

        return f"https://github.com/{self.identificador}"


@dataclass(frozen=True)
class ProjetoResolvido:
    """Linha única da database ``GITHUB`` encontrada para um repositório."""

    id: str
    titulo: str
    url: str
    repositorio: RepositorioGitHub

    def para_dict(self) -> dict[str, Any]:
        """Forma estável para o envelope JSON da CLI."""

        return {
            "id": self.id,
            "titulo": self.titulo,
            "url": self.url,
            "repositorio": self.repositorio.identificador,
        }


@dataclass
class ResultadoPreflight:
    """Plano de validação e escrita preparado sem alterar o Notion."""

    valores: dict[str, str]
    repositorio: RepositorioGitHub | None = None
    projeto: ProjetoResolvido | None = None
    coluna_relacao: str | None = None
    remover_relacoes: list[str] = field(default_factory=list)
    titulo_valido: bool | None = None
    prefixo_titulo: str | None = None
    resolvido: bool = False
    motivo: str | None = None
    avisos: list[str] = field(default_factory=list)
    estrito: bool = False

    def para_dict(self) -> dict[str, Any]:
        """Converte o resultado para dados JSON sem expor o JSON cru do Notion."""

        dados: dict[str, Any] = {
            "estrito": self.estrito,
            "resolvido": self.resolvido,
            "valores": dict(self.valores),
            "avisos": list(self.avisos),
        }
        if self.repositorio is not None:
            dados["repositorio"] = self.repositorio.identificador
            dados["url_canonica"] = self.repositorio.url_canonica
        if self.projeto is not None:
            dados["projeto"] = self.projeto.para_dict()
        if self.coluna_relacao is not None:
            dados["coluna_relacao"] = self.coluna_relacao
        if self.remover_relacoes:
            dados["remover_relacoes"] = list(self.remover_relacoes)
        if self.titulo_valido is not None:
            dados["titulo_valido"] = self.titulo_valido
        if self.prefixo_titulo is not None:
            dados["prefixo_titulo"] = self.prefixo_titulo
        if self.motivo is not None:
            dados["motivo"] = self.motivo
        return dados


def parsear_url_github(valor: str | None) -> RepositorioGitHub | None:
    """Extrai ``owner/repo`` de uma URL GitHub.

    São aceitos ``http``/``https``, host com ou sem ``www``, ``.git``,
    subcaminho, query e fragmento. O restante da URL não participa da
    identidade. Retorna ``None`` para URL externa, perfil ou formato inválido.
    """

    texto = str(valor or "").strip()
    if not texto:
        return None
    candidato = texto if "://" in texto else f"https://{texto}"
    try:
        partes = urlsplit(candidato)
        host = (partes.hostname or "").casefold()
    except ValueError:
        return None
    if partes.scheme.casefold() not in {"http", "https"}:
        return None
    if host not in {"github.com", "www.github.com"}:
        return None

    segmentos = [unquote(segmento) for segmento in partes.path.split("/") if segmento]
    if len(segmentos) < 2:
        return None
    proprietario, nome = segmentos[0], segmentos[1]
    if nome.casefold().endswith(".git"):
        nome = nome[:-4]
    if not proprietario or not nome:
        return None
    if any(
        not re.fullmatch(r"[\w.-]+", segmento, flags=re.UNICODE)
        for segmento in (proprietario, nome)
    ):
        return None
    return RepositorioGitHub(proprietario=proprietario, nome=nome)


# Nome alternativo útil para consumidores que chamam o conceito de repositório
# em vez de URL. Mantém a API pequena sem duplicar o parser.
parsear_repositorio_github = parsear_url_github


def _nome_titulo(propriedades: dict[str, Any]) -> str:
    for propriedade in propriedades.values():
        if isinstance(propriedade, dict) and propriedade.get("type") == "title":
            return readers.ler_title(propriedade)
    return ""


def _nome_coluna(
    propriedades: dict[str, Any], preferidas: tuple[str, ...], tipo: str | None = None
) -> str | None:
    for nome in preferidas:
        info = propriedades.get(nome)
        if isinstance(info, dict) and (tipo is None or info.get("type") == tipo):
            return nome
    for nome, info in propriedades.items():
        if isinstance(info, dict) and (tipo is None or info.get("type") == tipo):
            return nome
    return None


def _propriedade_por_nome(
    propriedades: dict[str, Any], nome: str | None, preferido: str
) -> tuple[str | None, dict[str, Any] | None]:
    if nome and nome in propriedades:
        return nome, propriedades[nome]
    if preferido in propriedades:
        return preferido, propriedades[preferido]
    alvo = preferido.casefold()
    for chave, valor in propriedades.items():
        if str(chave).casefold() == alvo:
            return chave, valor
    return nome, None


def _valor_simples(propriedade: dict[str, Any] | None) -> Any:
    if not isinstance(propriedade, dict):
        return None
    tipo = propriedade.get("type")
    if tipo == "title":
        return readers.ler_title(propriedade)
    if tipo == "url":
        return readers.ler_url(propriedade)
    if tipo == "relation":
        return readers.ler_relation(propriedade)
    return readers.ler_propriedade(propriedade)


def _valor_informado(
    valores: dict[str, str], coluna: str | None, preferido: str
) -> tuple[str | None, bool]:
    if coluna and coluna in valores:
        return valores[coluna], True
    if preferido in valores:
        return valores[preferido], True
    alvo = preferido.casefold()
    for nome, valor in valores.items():
        if str(nome).casefold() == alvo:
            return valor, True
    return None, False


def _ids_relacao(propriedade: dict[str, Any] | None) -> list[str]:
    if not isinstance(propriedade, dict):
        return []
    valor = propriedade.get("relation")
    if isinstance(valor, list):
        return [str(item.get("id")) for item in valor if isinstance(item, dict) and item.get("id")]
    if isinstance(valor, (tuple, set)):
        return [str(item) for item in valor if item]
    return []


def ids_relacao(propriedade: dict[str, Any] | None) -> list[str]:
    """Lê os IDs de uma relação para confirmar o resultado de um PATCH."""

    return _ids_relacao(propriedade)


def _itens_csv(valor: str | None) -> list[str]:
    return [item.strip() for item in str(valor or "").split(",") if item.strip()]


def _normalizar_nome(nome: str) -> str:
    decomposicao = unicodedata.normalize("NFKD", nome)
    sem_acentos = "".join(
        caractere for caractere in decomposicao if not unicodedata.combining(caractere)
    )
    texto = sem_acentos.casefold()
    return re.sub(r"[^a-z0-9]+", "-", texto).strip("-")


def _prefixo_titulo(nome: str) -> str | None:
    prefixo, separador, restante = nome.partition("/")
    if not separador or not prefixo.strip() or not restante.strip():
        return None
    return prefixo.strip()


def _alias_compativel(prefixo: str, alias: str) -> bool:
    esquerdo = _normalizar_nome(prefixo)
    direito = _normalizar_nome(alias)
    if not esquerdo or not direito:
        return False
    if esquerdo == direito:
        return True
    # O nome humano pode encurtar o slug ("Automações" para
    # "Automa-es-do-Notion"). A URL já foi resolvida por identidade exata;
    # esta tolerância serve apenas para validar o rótulo visível da tarefa.
    menor = min(len(esquerdo), len(direito))
    return menor >= 6 and SequenceMatcher(None, esquerdo, direito).ratio() >= 0.80


def _titulo_compativel(nome: str, projeto: ProjetoResolvido) -> tuple[bool, str | None]:
    prefixo = _prefixo_titulo(nome)
    if prefixo is None:
        return False, None
    restante = nome.partition("/")[2]
    contexto, separador, descricao = restante.partition("—")
    if not separador or not contexto.strip() or not descricao.strip():
        return False, prefixo
    aliases = {
        projeto.repositorio.nome,
        projeto.repositorio.identificador,
        projeto.titulo,
        projeto.titulo.rsplit("/", 1)[-1],
    }
    for alias in tuple(aliases):
        partes = [parte for parte in re.split(r"[-_\s]+", alias) if parte]
        aliases.update("-".join(partes[:quantidade]) for quantidade in range(2, len(partes) + 1))
    return any(_alias_compativel(prefixo, alias) for alias in aliases), prefixo


def _linhas_database(cliente: NotionClient, database_id: str) -> list[dict[str, Any]]:
    """Consulta linhas usando data sources quando o cliente os expõe."""

    listar_fontes = getattr(cliente, "listar_data_sources", None)
    consultar_fonte = getattr(cliente, "consultar_data_source", None)
    if callable(listar_fontes) and callable(consultar_fonte):
        fontes = listar_fontes(database_id)
        if fontes:
            linhas: list[dict[str, Any]] = []
            for fonte in fontes:
                fonte_id = fonte.get("id") if isinstance(fonte, dict) else None
                if fonte_id:
                    linhas.extend(consultar_fonte(fonte_id, buscar_todos=True))
            return linhas

    consultar = getattr(cliente, "consultar_database", None)
    if not callable(consultar):
        raise ValueError(
            f"Não foi possível listar as linhas do database de projetos {database_id}."
        )
    return consultar(database_id, buscar_todos=True)


def _resolver_repositorio(
    repositorio: RepositorioGitHub,
    *,
    cliente: NotionClient,
    database_id: str,
    propriedades_database: dict[str, Any],
    coluna_relacao: str = COLUNA_PROJETO,
) -> ProjetoResolvido | None:
    relacao = propriedades_database.get(coluna_relacao)
    if not isinstance(relacao, dict) or relacao.get("type") != "relation":
        raise ValueError(
            f"O database de tarefas não possui a coluna de relação '{coluna_relacao}'. "
            "Use 'schema <database_id>' para conferir o contrato."
        )
    database_projetos = (relacao.get("relation") or {}).get("database_id")
    if not database_projetos:
        raise ValueError(
            f"A relação '{coluna_relacao}' não informa o database de projetos; "
            "não é seguro adivinhar a relation."
        )

    schema_projetos = cliente.get_database(database_projetos)
    props_projetos = schema_projetos.get("properties") or {}
    coluna_url = _nome_coluna(
        props_projetos, (COLUNA_URL_PROJETO, "Url", "url"), tipo="url"
    )
    if coluna_url is None:
        raise ValueError(
            f"O database de projetos {database_projetos} não possui coluna do tipo URL; "
            "não foi criada nenhuma relação."
        )

    linhas = _linhas_database(cliente, database_projetos)
    encontrados: list[ProjetoResolvido] = []
    for linha in linhas:
        props = linha.get("properties") or {}
        url = _valor_simples(props.get(coluna_url))
        candidato = parsear_url_github(url if isinstance(url, str) else None)
        if candidato is None or candidato.chave != repositorio.chave:
            continue
        identificador = str(linha.get("id") or "").strip()
        if not identificador:
            continue
        encontrados.append(
            ProjetoResolvido(
                id=identificador,
                titulo=_nome_titulo(props) or str(linha.get("titulo") or ""),
                url=str(url or ""),
                repositorio=candidato,
            )
        )

    if len(encontrados) > 1:
        detalhes = ", ".join(f"{item.id} ({item.titulo or 'sem título'})" for item in encontrados)
        raise ValueError(
            f"A URL GitHub '{repositorio.identificador}' encontrou mais de uma linha "
            f"na database de projetos: {detalhes}. Resolva a duplicidade antes de usar "
            "--strict."
        )
    return encontrados[0] if encontrados else None


def resolver_projeto_por_url(
    url: str,
    *,
    cliente: NotionClient,
    database_id: str,
    propriedades_database: dict[str, Any] | None = None,
    coluna_relacao: str = COLUNA_PROJETO,
) -> ProjetoResolvido | None:
    """Resolve uma URL GitHub para exatamente uma linha de projeto."""

    repositorio = parsear_url_github(url)
    if repositorio is None:
        return None
    propriedades = propriedades_database
    if propriedades is None:
        propriedades = (cliente.get_database(database_id).get("properties") or {})
    return _resolver_repositorio(
        repositorio,
        cliente=cliente,
        database_id=database_id,
        propriedades_database=propriedades,
        coluna_relacao=coluna_relacao,
    )


def _resultado_sem_contexto(
    valores: dict[str, str], *, estrito: bool, motivo: str
) -> ResultadoPreflight:
    return ResultadoPreflight(
        valores=dict(valores), estrito=estrito, motivo=motivo, avisos=[]
    )


def _avaliar(
    nome: str,
    valores: dict[str, str],
    acrescentos: dict[str, str],
    *,
    propriedades_database: dict[str, Any],
    propriedades_atuais: dict[str, Any] | None,
    cliente: NotionClient,
    database_id: str | None,
    estrito: bool,
) -> ResultadoPreflight:
    atuais = propriedades_atuais or {}
    valores_saida = dict(valores)
    coluna_url = _nome_coluna(
        propriedades_database,
        (COLUNA_URL_REFERENCIA, "URL de referência", "url de referência"),
        tipo="url",
    ) or _nome_coluna(
        atuais,
        (COLUNA_URL_REFERENCIA, "URL de referência", "url de referência"),
        tipo="url",
    )
    coluna_relacao = _nome_coluna(
        propriedades_database, (COLUNA_PROJETO,), tipo="relation"
    ) or _nome_coluna(atuais, (COLUNA_PROJETO,), tipo="relation")
    url_atual = _valor_simples(atuais.get(coluna_url)) if coluna_url else None
    url_informada, tem_url_informada = _valor_informado(
        valores, coluna_url, COLUNA_URL_REFERENCIA
    )
    url_efetiva = url_informada if tem_url_informada else url_atual
    if url_efetiva is not None:
        url_efetiva = str(url_efetiva).strip()

    projeto_atual = _ids_relacao(atuais.get(coluna_relacao)) if coluna_relacao else []
    projeto_informado, tem_projeto_informado = _valor_informado(
        valores, coluna_relacao, COLUNA_PROJETO
    )
    projetos_informados = _itens_csv(projeto_informado) if tem_projeto_informado else []

    projeto_url: str | None = None
    projeto_repo: RepositorioGitHub | None = None
    ids_legados: list[str] = []
    for item in projetos_informados:
        candidato = parsear_url_github(item)
        if candidato is not None:
            if projeto_url is not None:
                raise ValueError(
                    "A coluna 'Projeto' recebeu mais de uma URL GitHub; informe uma "
                    "única URL ou IDs de páginas separados por vírgula."
                )
            projeto_url = item
            projeto_repo = candidato
            continue
        if re.match(r"^(?:https?://|github\.com/|www\.github\.com/)", item, re.I):
            raise ValueError(
                f"A URL '{item}' em 'Projeto' não é um repositório GitHub válido ou "
                "não foi resolvida. Use o ID da linha GITHUB ou corrija a URL."
            )
        ids_legados.append(item)

    url_repo = parsear_url_github(url_efetiva)
    if projeto_repo is not None and url_repo is not None and projeto_repo.chave != url_repo.chave:
        if estrito:
            raise ValueError(
                "URL de referência e Projeto apontam para repositórios GitHub diferentes; "
                "corrija os dois valores antes de gravar."
            )
        projeto_repo = url_repo

    repositorio = url_repo or projeto_repo
    if repositorio is None:
        if estrito and (ids_legados or projeto_atual):
            raise ValueError(
                "--strict exige uma URL GitHub resolvível para validar a relação "
                "'Projeto'. Tarefas pessoais ficam permitidas quando não têm URL "
                "GitHub nem Projeto."
            )
        return _resultado_sem_contexto(
            valores_saida,
            estrito=estrito,
            motivo="sem URL GitHub nem URL de Projeto; exceção pessoal ou referência externa",
        )

    if database_id is None:
        raise ValueError(
            "Não foi possível descobrir o database da linha de tarefas para resolver "
            "'Projeto'. Use um TaskList configurado com NOTION_DATABASE_ID."
        )

    projeto = _resolver_repositorio(
        repositorio,
        cliente=cliente,
        database_id=database_id,
        propriedades_database=propriedades_database,
        coluna_relacao=COLUNA_PROJETO,
    )
    if projeto is None:
        mensagem = (
            f"A URL GitHub '{repositorio.identificador}' não foi encontrada na database "
            "GITHUB; nenhuma relation foi adivinhada. Sincronize/crie a linha do projeto "
            "ou use a exceção pessoal sem --strict."
        )
        if estrito:
            raise ValueError(mensagem)
        if projeto_url is not None:
            # Uma URL em Projeto é uma intenção de resolução, não um valor
            # aceito pelo payload de relation. Nunca repasse a URL (nem IDs
            # acompanhantes) ao editor genérico quando ela não foi catalogada.
            for chave in list(valores_saida):
                if chave == coluna_relacao or chave.casefold() == COLUNA_PROJETO.casefold():
                    valores_saida.pop(chave, None)
        return ResultadoPreflight(
            valores=valores_saida,
            repositorio=repositorio,
            resolvido=False,
            motivo="URL GitHub não encontrada na GITHUB",
            avisos=[mensagem],
            estrito=estrito,
        )

    titulo_valido, prefixo = _titulo_compativel(nome, projeto)
    if not titulo_valido:
        mensagem = (
            "O título precisa seguir '<projeto>/<contexto> — descrição' e começar "
            f"pelo projeto canônico ({projeto.repositorio.nome} ou alias humano equivalente)."
        )
        if estrito:
            raise ValueError(mensagem)

    esperado = projeto.id
    esperado_normalizado = esperado.replace("-", "").casefold()
    informados_diferentes = [
        item
        for item in ids_legados
        if item.replace("-", "").casefold() != esperado_normalizado
    ]
    if projeto_url is not None and not ids_legados:
        informados_diferentes = []
    projeto_id_informado_incorreto = any(
        item.replace("-", "").casefold() != esperado_normalizado
        for item in ids_legados
    )
    if tem_projeto_informado and projeto_url is None and (
        informados_diferentes or len(ids_legados) != 1 or projeto_id_informado_incorreto
    ):
        if estrito:
            raise ValueError(
                f"Projeto informado não é o projeto canônico da URL; use a linha {esperado}."
            )

    # A coluna de relação não passa pelo editor genérico: o chamador a aplica
    # por ``relacionar``. Remover a chave evita que uma URL ou ID conflitante
    # seja enviada diretamente para o PATCH.
    for chave in list(valores_saida):
        if chave == coluna_relacao or chave.casefold() == COLUNA_PROJETO.casefold():
            valores_saida.pop(chave, None)

    remover = [
        item
        for item in projeto_atual
        if item.replace("-", "").casefold() != esperado.replace("-", "").casefold()
    ]
    avisos: list[str] = []
    if not titulo_valido:
        avisos.append(
            "Título fora do padrão canônico; use --strict para bloquear antes da escrita."
        )
    if tem_projeto_informado and (informados_diferentes or len(ids_legados) != 1):
        avisos.append("Projeto foi normalizado para a única linha resolvida pela URL GitHub.")
    return ResultadoPreflight(
        valores=valores_saida,
        repositorio=repositorio,
        projeto=projeto,
        coluna_relacao=coluna_relacao,
        remover_relacoes=remover,
        titulo_valido=titulo_valido,
        prefixo_titulo=prefixo,
        resolvido=True,
        motivo="URL GitHub resolvida para uma única linha GITHUB",
        avisos=avisos,
        estrito=estrito,
    )


def preflight_criar(
    nome: str,
    valores: dict[str, str],
    *,
    cliente: NotionClient,
    database_id: str | None,
    estrito: bool = False,
) -> ResultadoPreflight:
    """Valida uma criação sem chamar ``criar_pagina``."""

    if database_id is None and not any(
        chave.casefold() in {COLUNA_URL_REFERENCIA.casefold(), COLUNA_PROJETO.casefold()}
        for chave in valores
    ):
        return _resultado_sem_contexto(
            valores, estrito=estrito, motivo="sem URL GitHub nem Projeto"
        )
    propriedades_database: dict[str, Any] = {}
    if database_id is not None:
        propriedades_database = cliente.get_database(database_id).get("properties") or {}
    return _avaliar(
        nome,
        dict(valores),
        {},
        propriedades_database=propriedades_database,
        propriedades_atuais=None,
        cliente=cliente,
        database_id=database_id,
        estrito=estrito,
    )


def preflight_editar(
    page_id: str,
    valores: dict[str, str],
    acrescentos: dict[str, str],
    *,
    cliente: NotionClient,
    estrito: bool = False,
) -> ResultadoPreflight:
    """Valida uma edição a partir da página atual, sem fazer PATCH."""

    pagina = cliente.obter_pagina(page_id)
    atuais = pagina.get("properties") or {}
    pai = pagina.get("parent") or {}
    database_id = pai.get("database_id") if pai.get("type") == "database_id" else None
    propriedades_database: dict[str, Any] = {}
    if database_id:
        propriedades_database = cliente.get_database(database_id).get("properties") or {}
    if not propriedades_database:
        propriedades_database = atuais

    coluna_titulo = _nome_coluna(propriedades_database, (), tipo="title") or _nome_coluna(
        atuais, (), tipo="title"
    )
    titulo_atual = _valor_simples(atuais.get(coluna_titulo)) if coluna_titulo else ""
    titulo_informado, tem_titulo = _valor_informado(valores, coluna_titulo, "Tarefa")
    titulo_efetivo = str(titulo_informado) if tem_titulo else str(titulo_atual or "")
    if not tem_titulo and coluna_titulo in acrescentos:
        titulo_efetivo += acrescentos[coluna_titulo]

    return _avaliar(
        titulo_efetivo,
        dict(valores),
        dict(acrescentos),
        propriedades_database=propriedades_database,
        propriedades_atuais=atuais,
        cliente=cliente,
        database_id=database_id,
        estrito=estrito,
    )
