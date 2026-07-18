# ✅ Qualidade — notion-tasks-cli

Este documento registra o gate de qualidade do módulo e as exceções motivadas ao
[Felixo System Design](https://github.com/Felipe-Alcantara/Felixo-System-Design).

## Gate local

Execute na raiz do repositório:

```bash
python -m ruff check .
python -m pytest
```

Os testes usam integrações mockadas e não exigem token real. A CI em
`.github/workflows/ci.yml` executa o mesmo gate em Python 3.10–3.13 para pushes no
`main` e pull requests.

## Critério de pronto

Uma mudança está pronta quando:

- lint e suíte automatizada passam;
- o envelope JSON, o `--help` e os contratos dos subcomandos foram preservados ou
  documentados;
- nenhum segredo, ID real ou perfil local foi versionado;
- README, `IA.md` e testes foram atualizados quando afetados;
- riscos ou limitações restantes foram registrados.

## Exceção motivada: versões mínimas

As dependências versionadas pelo `pyproject.toml` usam limites mínimos (`>=`).
Esta é uma exceção deliberada à recomendação geral de pinagem: o CLI é instalado
via pip no ambiente de outras ferramentas, e pins exatos poderiam causar
conflitos com bibliotecas já usadas pela pessoa.

A compatibilidade é verificada continuamente pela matriz da CI em Python
3.10–3.13. Quem precisar de um ambiente totalmente reproduzível deve fixar a
resolução no ambiente consumidor.
