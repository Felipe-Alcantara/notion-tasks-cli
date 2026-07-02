"""Testes de integração para validação de status - testa o fluxo completo.

Testa a validação funcionando com serviços reais (mockados) para garantir
que o problema de status inválido não ocorra novamente.
"""

from unittest.mock import Mock, patch

import pytest

from cli.notion_tasks import CLIError, cmd_criar, cmd_mover


class TestIntegrationStatusValidation:
    """Testes de integração para validação de status."""

    def test_integracao_criar_status_valido(self):
        """Testa fluxo completo de criação com status válido."""
        mock_args = Mock()
        mock_args.nome = "Tarefa de integração"
        mock_args.status = "Entrada"
        mock_args.prazo = None
        mock_args.duracao = None
        mock_args.area = None

        # Mock da tasklist real
        mock_tasklist = Mock()
        mock_tasklist.listar_opcoes = Mock(return_value={
            "status": ["Entrada", "Assim que possível", "Concluída"],
            "duracao": ["Minutos", "Horas", "Dias"],
            "areas": []
        })
        mock_tasklist.criar = Mock(return_value=Mock(
            id="integration-id",
            nome="Tarefa de integração",
            status="Entrada",
            prazo=None,
            duracao=None,
            areas=[],
            areas_nomes=[],
            url="https://notion.so/integration"
        ))

        mock_tasklist_factory = Mock(return_value=mock_tasklist)

        # Mock do service que usa a tasklist real
        with patch("cli.notion_tasks.svc.listar_opcoes") as mock_svc_opcoes:
            mock_svc_opcoes.return_value = {
                "status": ["Entrada", "Assim que possível", "Concluída"],
                "duracao": ["Minutos", "Horas", "Dias"],
                "areas": []
            }

            with patch("cli.notion_tasks.svc.criar_tarefa") as mock_svc_criar:
                mock_svc_criar.return_value = Mock(
                    id="integration-id",
                    nome="Tarefa de integração",
                    status="Entrada",
                    prazo=None,
                    duracao=None,
                    areas=[],
                    areas_nomes=[],
                    url="https://notion.so/integration"
                )

                # Fluxo deve funcionar sem erro
                result = cmd_criar(mock_args, tasklist_factory=mock_tasklist_factory)
                assert result["status"] == "Entrada"
                mock_svc_criar.assert_called_once()

    def test_integracao_criar_status_invalido_previne_chamada_api(self):
        """Testa que status inválido previne chamada à API."""
        mock_args = Mock()
        mock_args.nome = "Tarefa com status inválido"
        mock_args.status = "Status Que Não Existe"
        mock_args.prazo = None
        mock_args.duracao = None
        mock_args.area = None

        mock_tasklist = Mock()
        mock_tasklist_factory = Mock(return_value=mock_tasklist)

        with patch("cli.notion_tasks.svc.listar_opcoes") as mock_opcoes:
            mock_opcoes.return_value = {
                "status": ["Entrada", "Assim que possível", "Concluída"],
                "duracao": ["Minutos", "Horas", "Dias"],
                "areas": []
            }

            with patch("cli.notion_tasks.svc.criar_tarefa") as mock_criar:
                # Deve levantar erro antes de chamar criar_tarefa
                with pytest.raises(CLIError):
                    cmd_criar(mock_args, tasklist_factory=mock_tasklist_factory)

                # Não deve ter chamado a API
                mock_criar.assert_not_called()

    def test_integracao_simula_erro_api_status_invalido(self):
        """Simula o erro que ocorria antes da validação."""
        mock_args = Mock()
        mock_args.task_id = "test-id"
        mock_args.status = "Status Inexistente"

        mock_tasklist = Mock()
        mock_tasklist_factory = Mock(return_value=mock_tasklist)

        # Simula o erro da API do Notion
        with patch("cli.notion_tasks.svc.listar_opcoes") as mock_opcoes:
            mock_opcoes.return_value = {
                "status": ["Entrada", "Assim que possível", "Concluída"],
                "duracao": ["Minutos", "Horas", "Dias"],
                "areas": []
            }

            # Antes da validação, isso causaria erro da API
            # Agora a validação previne que chegue na API
            with pytest.raises(CLIError) as exc_info:
                cmd_mover(mock_args, tasklist_factory=mock_tasklist_factory)

            # Mensagem deve ser específica e útil
            assert "inválido" in str(exc_info.value).lower()
            assert "opções disponíveis" in str(exc_info.value).lower()

    def test_integracao_com_multiplos_status_validos(self):
        """Testa com diferentes status válidos."""
        status_test_cases = [
            ("Entrada", True),
            ("Assim que possível", True),
            ("Concluída", True),
            ("Status Fake", False),  # Deve falhar
            ("", True),  # String vazia deve passar (None após normalização)
            (None, True),  # None deve passar (sem validação)
        ]

        for status, should_pass in status_test_cases:
            mock_args = Mock()
            mock_args.nome = f"Teste status: {status}"
            mock_args.status = status
            mock_args.prazo = None
            mock_args.duracao = None
            mock_args.area = None

            mock_tasklist = Mock()
            mock_tasklist_factory = Mock(return_value=mock_tasklist)

            with patch("cli.notion_tasks.svc.listar_opcoes") as mock_opcoes:
                mock_opcoes.return_value = {
                    "status": ["Entrada", "Assim que possível", "Concluída", "Urgente"],
                    "duracao": ["Minutos", "Horas", "Dias"],
                    "areas": []
                }

                with patch("cli.notion_tasks.svc.criar_tarefa") as mock_criar:
                    if should_pass:
                        mock_criar.return_value = Mock(
                            id="test-id",
                            nome=f"Teste status: {status}",
                            status=status if status != "" else None,  # String vazia → None
                            prazo=None,
                            duracao=None,
                            areas=[],
                            areas_nomes=[],
                            url="https://notion.so/test"
                        )
                        # Deve passar
                        result = cmd_criar(mock_args, tasklist_factory=mock_tasklist_factory)
                        # Para string vazia, o status será None após normalização
                        expected_status = None if status == "" else status
                        assert result["status"] == expected_status
                    else:
                        # Deve falhar com erro específico
                        with pytest.raises(CLIError):
                            cmd_criar(mock_args, tasklist_factory=mock_tasklist_factory)

    def test_integracao_erro_api_ainda_handle_corretamente(self):
        """Testa que outros erros da API ainda são tratados corretamente."""
        mock_args = Mock()
        mock_args.task_id = "test-id"
        mock_args.status = "Concluída"  # Status válido

        mock_tasklist = Mock()
        mock_tasklist_factory = Mock(return_value=mock_tasklist)

        with patch("cli.notion_tasks.svc.listar_opcoes") as mock_opcoes:
            mock_opcoes.return_value = {
                "status": ["Entrada", "Assim que possível", "Concluída"],
                "duracao": ["Minutos", "Horas", "Dias"],
                "areas": []
            }

            # Simula outro erro da API (não relacionado a status)
            with patch("cli.notion_tasks.svc.mover_status") as mock_mover:
                mock_mover.side_effect = Exception("Erro de conexão")

                # Deve propagar o erro normalmente
                with pytest.raises(Exception) as exc_info:
                    cmd_mover(mock_args, tasklist_factory=mock_tasklist_factory)

                assert "Erro de conexão" in str(exc_info.value)


class TestEdgeCases:
    """Testa casos de borda da validação de status."""

    def test_status_case_sensitive(self):
        """Validação deve ser case-sensitive (Notion API é case-sensitive)."""
        mock_args = Mock()
        mock_args.nome = "Teste case"
        mock_args.status = "entrada"  # lowercase - deve falhar
        mock_args.prazo = None
        mock_args.duracao = None
        mock_args.area = None

        mock_tasklist = Mock()
        mock_tasklist_factory = Mock(return_value=mock_tasklist)

        with patch("cli.notion_tasks.svc.listar_opcoes") as mock_opcoes:
            mock_opcoes.return_value = {
                "status": ["Entrada", "Assim que possível", "Concluída"],  # Capitalizado
                "duracao": ["Minutos", "Horas", "Dias"],
                "areas": []
            }

            # Deve falhar porque "entrada" != "Entrada"
            with pytest.raises(CLIError):
                cmd_criar(mock_args, tasklist_factory=mock_tasklist_factory)

    def test_lista_opcoes_vazia(self):
        """Testa comportamento quando lista de opções está vazia."""
        mock_args = Mock()
        mock_args.nome = "Teste opções vazias"
        mock_args.status = "Qualquer Status"
        mock_args.prazo = None
        mock_args.duracao = None
        mock_args.area = None

        mock_tasklist = Mock()
        mock_tasklist_factory = Mock(return_value=mock_tasklist)

        with patch("cli.notion_tasks.svc.listar_opcoes") as mock_opcoes:
            mock_opcoes.return_value = {
                "status": [],  # Lista vazia
                "duracao": [],
                "areas": []
            }

            # Qualquer status deve falhar com lista vazia
            with pytest.raises(CLIError) as exc_info:
                cmd_criar(mock_args, tasklist_factory=mock_tasklist_factory)

            assert "inválido" in str(exc_info.value).lower()

    def test_timeout_listar_opcoes(self):
        """Testa comportamento quando listar_opcoes falha."""
        mock_args = Mock()
        mock_args.nome = "Teste timeout"
        mock_args.status = "Entrada"
        mock_args.prazo = None
        mock_args.duracao = None
        mock_args.area = None

        mock_tasklist = Mock()
        mock_tasklist_factory = Mock(return_value=mock_tasklist)

        # Simula timeout na consulta de opções
        with patch("cli.notion_tasks.svc.listar_opcoes") as mock_opcoes:
            mock_opcoes.side_effect = Exception("Timeout")

            # Deve propagar o erro
            with pytest.raises(Exception) as exc_info:
                cmd_criar(mock_args, tasklist_factory=mock_tasklist_factory)

            assert "Timeout" in str(exc_info.value)