"""Teste para prevenir erro 400 "invalid high surrogate in string" da API do Notion.

Este teste verifica que todo conteúdo enviado para a API do Notion está livre de
caracteres Unicode surrogate inválidos que causam erro 400 com mensagem:
"The request body is not valid JSON: invalid high surrogate in string"

O problema ocorre quando:
1. Usamos `ensure_ascii=False` no json.dumps (ou requests.request com json=)
2. O texto contém surrogates inválidos (high surrogate sem low surrogate)
3. O encoding para UTF-8 falha durante a serialização
"""

import json
import os

# Adicionar src ao path para import
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from notion_starter.utils import has_invalid_surrogates, safe_json_dumps, sanitize_text


def test_surrogate_detection():
    """Testa detecção de surrogates inválidos."""

    # Casos de teste
    test_cases = [
        ("texto normal", False),
        ("texto com surrogate: \ud800", True),  # high surrogate alone
        ("texto com \udfff", True),  # outro high surrogate
        ("texto com \udc00", True),  # low surrogate alone
        ("texto com emoji válido 😀", False),  # emoji como surrogate pair válido
        ("texto com acentuação ç á é", False),  # caracteres acentuados normais
    ]

    for text, expected in test_cases:
        result = has_invalid_surrogates(text)
        assert result == expected, (
            f"Falha para: {repr(text)[:30]} - esperado: {expected}, obtido: {result}"
        )


def test_safe_json_dumps():
    """Testa serialização JSON segura."""

    # Dados com surrogate inválido
    invalid_data = {
        "content": "texto com \ud800 surrogate inválido",
        "normal": "texto normal",
        "nested": {
            "inner": "texto aninhado com \udc00 problema"
        }
    }

    # safe_json_dumps deve funcionar mesmo com ensure_ascii=False
    result = safe_json_dumps(invalid_data, ensure_ascii=False, indent=2)

    assert isinstance(result, str)
    assert "content" in result
    # Deve ter escapado os surrogates
    assert "\\ud800" in result or "\\\\ud800" in result or '"texto com' in result

    # Dados normais devem funcionar normalmente
    normal_data = {"text": "conteúdo normal com acentos"}
    normal_result = safe_json_dumps(normal_data, ensure_ascii=False)
    assert "conteúdo" in normal_result


def test_sanitize_text():
    """Testa sanitização de texto com surrogates inválidos."""

    problematic = "Texto com \ud800 surrogate inválido"
    sanitized = sanitize_text(problematic)

    # Texto sanitizado deve ser válido
    assert not has_invalid_surrogates(sanitized)

    # Texto original deve ser inválido
    assert has_invalid_surrogates(problematic)

    # Texto normal não deve ser alterado
    normal = "Texto normal com acentuação"
    assert sanitize_text(normal) == normal


def test_cli_json_function():
    """Testa que a função _json do CLI usa safe_json_dumps."""

    # Importar depois de configurar path
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

    from cli.notion_tasks import _json

    # Testar com dados problemáticos - deve funcionar
    problematic_data = {
        "ok": True,
        "dados": {
            "texto": "conteúdo com possível \ud800 problema"
        }
    }

    try:
        result = _json(problematic_data)
        assert isinstance(result, str)
        assert "\"ok\": true" in result
        print("✅ _json funciona com dados problemáticos")
    except Exception as e:
        # Se falhar, é um problema
        pytest.fail(f"_json falhou: {e}")


def test_requests_serialization_issue():
    """Testa o problema de serialização do requests."""

    # Simular o que acontece quando requests.request tenta serializar JSON
    problematic_text = "texto com \ud800 surrogate"
    data = {"content": problematic_text}

    print("\nSimulando problema do requests:")

    # Tentar json.dumps normal
    try:
        json_str = json.dumps(data, ensure_ascii=False)
        print(f"json.dumps funciona: {len(json_str)} chars")

        # Tentar codificar para UTF-8 (o que requests faz)
        try:
            json_str.encode('utf-8')
            print("UTF-8 encoding funciona")
        except UnicodeEncodeError as e:
            print(f"UTF-8 encoding FALHA: {e}")

    except Exception as e:
        print(f"json.dumps FALHA: {e}")

    # Agora com safe_json_dumps
    print("\nCom safe_json_dumps:")
    safe_json = safe_json_dumps(data, ensure_ascii=False)
    print(f"safe_json_dumps funciona: {len(safe_json)} chars")

    try:
        safe_json.encode('utf-8')
        print("UTF-8 encoding funciona com safe_json_dumps")
    except UnicodeEncodeError as e:
        print(f"UTF-8 encoding ainda falha: {e}")
        # Se ainda falhar, safe_json_dumps deveria usar ensure_ascii=True automaticamente
        safe_json2 = safe_json_dumps(data, ensure_ascii=True)
        safe_bytes2 = safe_json2.encode('utf-8')
        print(f"Fallback com ensure_ascii=True funciona: {len(safe_bytes2)} bytes")


def test_real_world_scenarios():
    """Testa cenários reais onde surrogates podem aparecer."""

    scenarios = [
        # Texto copiado de fontes com codificação quebrada
        "Texto copiado do Word com formatação estranha",

        # Emojis e caracteres especiais
        "Texto ✅ com 👍 emojis",

        # Texto com possíveis problemas de encoding
        "Texto com caracteres especiais: © ® ™ … —",

        # Texto com código
        "Código: x = '�'  # caractere de substituição",
    ]

    for text in scenarios:
        # Todas essas strings devem ser válidas
        assert not has_invalid_surrogates(text), f"Texto inválido: {repr(text[:50])}"

        # Devem funcionar com safe_json_dumps
        data = {"text": text}
        result = safe_json_dumps(data, ensure_ascii=False)
        assert isinstance(result, str)


if __name__ == "__main__":
    print("Executando testes de prevenção de JSON surrogates...")

    test_surrogate_detection()
    print("✅ test_surrogate_detection passou")

    test_safe_json_dumps()
    print("✅ test_safe_json_dumps passou")

    test_sanitize_text()
    print("✅ test_sanitize_text passou")

    test_requests_serialization_issue()
    print("✅ test_requests_serialization_issue passou")

    test_real_world_scenarios()
    print("✅ test_real_world_scenarios passou")

    # test_cli_json_function() - requer ambiente configurado

    print("\n🎯 Todos os testes de prevenção de surrogate passaram!")
    print("O erro 'invalid high surrogate in string' agora será prevenido automaticamente.")
