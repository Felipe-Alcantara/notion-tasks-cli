"""Testes para validação de status no CLI - prevenção do problema de status inválido.

Problema identificado: CLI falhava com status que não existe no schema do database,
retornando erro genérico "Falha ao falar com o Notion" em vez de mensagem específica.

Solução implementada: Validação prévia de status contra opções disponíveis no database.
"""

from unittest.mock import Mock, patch

import pytest

from cli.notion_tasks import CLIError, cmd_concluir, cmd_criar, cmd_editar, cmd_mover


class TestStatusValidation:
    """Testa a validação de status no CLI para prevenir erro de status inválido."""

    def test_criar_com_status_valido(self):
        """Deve permitir criação com status válido."""
        mock_args = Mock()
        mock_args.nome = "Tarefa teste"
        mock_args.status = "Entrada"
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
                mock_criar.return_value = Mock(
                    id="test-id",
                    nome="Tarefa teste",
                    status="Entrada",
                    prazo=None,
                    duracao=None,
                    areas=[],
                    areas_nomes=[],
                    url="https://notion.so/test"
                )

                # Não deve levantar erro
                result = cmd_criar(mock_args, tasklist_factory=mock_tasklist_factory)
                assert result["status"] == "Entrada"

    def test_criar_com_status_invalido(self):
        """Deve rejeitar criação com status inválido."""
        mock_args = Mock()
        mock_args.nome = "Tarefa teste"
        mock_args.status = "Status Inexistente"
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

            # Deve levantar CLIError com mensagem específica
            with pytest.raises(CLIError) as exc_info:
                cmd_criar(mock_args, tasklist_factory=mock_tasklist_factory)

            assert "Status 'Status Inexistente' inválido" in str(exc_info.value)
            assert "Entrada, Assim que possível, Concluída" in str(exc_info.value)

    def test_editar_com_status_valido(self):
        """Deve permitir edição com status válido."""
        mock_args = Mock()
        mock_args.task_id = "test-id"
        mock_args.nome = None
        mock_args.status = "Concluída"
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

            with patch("cli.notion_tasks.svc.editar_tarefa") as mock_editar:
                mock_editar.return_value = Mock(
                    id="test-id",
                    nome="Tarefa atualizada",
                    status="Concluída",
                    prazo=None,
                    duracao=None,
                    areas=[],
                    areas_nomes=[],
                    url="https://notion.so/test"
                )

                # Não deve levantar erro
                result = cmd_editar(mock_args, tasklist_factory=mock_tasklist_factory)
                assert result["status"] == "Concluída"

    def test_editar_com_status_invalido(self):
        """Deve rejeitar edição com status inválido."""
        mock_args = Mock()
        mock_args.task_id = "test-id"
        mock_args.nome = None
        mock_args.status = "Status Fake"
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

            # Deve levantar CLIError com mensagem específica
            with pytest.raises(CLIError) as exc_info:
                cmd_editar(mock_args, tasklist_factory=mock_tasklist_factory)

            assert "Status 'Status Fake' inválido" in str(exc_info.value)

    def test_mover_com_status_valido(self):
        """Deve permitir mover com status válido."""
        mock_args = Mock()
        mock_args.task_id = "test-id"
        mock_args.status = "Assim que possível"

        mock_tasklist = Mock()
        mock_tasklist_factory = Mock(return_value=mock_tasklist)

        with patch("cli.notion_tasks.svc.listar_opcoes") as mock_opcoes:
            mock_opcoes.return_value = {
                "status": ["Entrada", "Assim que possível", "Concluída"],
                "duracao": ["Minutos", "Horas", "Dias"],
                "areas": []
            }

            with patch("cli.notion_tasks.svc.mover_status") as mock_mover:
                mock_mover.return_value = Mock(
                    id="test-id",
                    nome="Tarefa movida",
                    status="Assim que possível",
                    prazo=None,
                    duracao=None,
                    areas=[],
                    areas_nomes=[],
                    url="https://notion.so/test"
                )

                # Não deve levantar erro
                result = cmd_mover(mock_args, tasklist_factory=mock_tasklist_factory)
                assert result["status"] == "Assim que possível"

    def test_mover_com_status_invalido(self):
        """Deve rejeitar mover com status inválido."""
        mock_args = Mock()
        mock_args.task_id = "test-id"
        mock_args.status = "Status Que Não Existe"

        mock_tasklist = Mock()
        mock_tasklist_factory = Mock(return_value=mock_tasklist)

        with patch("cli.notion_tasks.svc.listar_opcoes") as mock_opcoes:
            mock_opcoes.return_value = {
                "status": ["Entrada", "Assim que possível", "Concluída"],
                "duracao": ["Minutos", "Horas", "Dias"],
                "areas": []
            }

            # Deve levantar CLIError com mensagem específica
            with pytest.raises(CLIError) as exc_info:
                cmd_mover(mock_args, tasklist_factory=mock_tasklist_factory)

            assert "Status 'Status Que Não Existe' inválido" in str(exc_info.value)

    def test_concluir_com_status_valido(self):
        """Deve permitir concluir com status válido."""
        mock_args = Mock()
        mock_args.task_id = "test-id"
        mock_args.status = "Concluída"

        mock_tasklist = Mock()
        mock_tasklist_factory = Mock(return_value=mock_tasklist)

        with patch("cli.notion_tasks.svc.listar_opcoes") as mock_opcoes:
            mock_opcoes.return_value = {
                "status": ["Entrada", "Assim que possível", "Concluída"],
                "duracao": ["Minutos", "Horas", "Dias"],
                "areas": []
            }

            with patch("cli.notion_tasks.svc.concluir_tarefa") as mock_concluir:
                mock_concluir.return_value = Mock(
                    id="test-id",
                    nome="Tarefa concluída",
                    status="Concluída",
                    prazo=None,
                    duracao=None,
                    areas=[],
                    areas_nomes=[],
                    url="https://notion.so/test"
                )

                # Não deve levantar erro
                result = cmd_concluir(mock_args, tasklist_factory=mock_tasklist_factory)
                assert result["status"] == "Concluída"

    def test_concluir_com_status_invalido(self):
        """Deve rejeitar concluir com status inválido."""
        mock_args = Mock()
        mock_args.task_id = "test-id"
        mock_args.status = "Finalizada"  # Status que não existe

        mock_tasklist = Mock()
        mock_tasklist_factory = Mock(return_value=mock_tasklist)

        with patch("cli.notion_tasks.svc.listar_opcoes") as mock_opcoes:
            mock_opcoes.return_value = {
                "status": ["Entrada", "Assim que possível", "Concluída"],
                "duracao": ["Minutos", "Horas", "Dias"],
                "areas": []
            }

            # Deve levantar CLIError com mensagem específica
            with pytest.raises(CLIError) as exc_info:
                cmd_concluir(mock_args, tasklist_factory=mock_tasklist_factory)

            assert "Status 'Finalizada' inválido" in str(exc_info.value)

    def test_criar_sem_status_nao_valida(self):
        """Não deve validar status quando não fornecido."""
        mock_args = Mock()
        mock_args.nome = "Tarefa sem status"
        mock_args.status = None
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
                mock_criar.return_value = Mock(
                    id="test-id",
                    nome="Tarefa sem status",
                    status=None,
                    prazo=None,
                    duracao=None,
                    areas=[],
                    areas_nomes=[],
                    url="https://notion.so/test"
                )

                # Não deve levantar erro nem chamar listar_opcoes
                result = cmd_criar(mock_args, tasklist_factory=mock_tasklist_factory)
                assert result["status"] is None
                mock_opcoes.assert_not_called()


class TestMensagensErroMelhoradas:
    """Testa que as mensagens de erro são específicas e úteis."""

    def test_mensagem_erro_inclui_opcoes_disponiveis(self):
        """Mensagem de erro deve incluir opções disponíveis."""
        mock_args = Mock()
        mock_args.task_id = "test-id"
        mock_args.status = "Status Fake"

        mock_tasklist = Mock()
        mock_tasklist_factory = Mock(return_value=mock_tasklist)

        with patch("cli.notion_tasks.svc.listar_opcoes") as mock_opcoes:
            mock_opcoes.return_value = {
                "status": ["Entrada", "Urgente", "Concluída", "Agendada"],
                "duracao": ["Minutos", "Horas", "Dias"],
                "areas": []
            }

            with pytest.raises(CLIError) as exc_info:
                cmd_mover(mock_args, tasklist_factory=mock_tasklist_factory)

            error_msg = str(exc_info.value)
            assert "Status 'Status Fake' inválido" in error_msg
            assert "Entrada, Urgente, Concluída, Agendada" in error_msg

    def test_mensagem_erro_formato_correto(self):
        """Mensagem deve ter formato claro e útil."""
        mock_args = Mock()
        mock_args.nome = "Tarefa teste"
        mock_args.status = "Status Inexistente"
        mock_args.prazo = None
        mock_args.duracao = None
        mock_args.area = None

        mock_tasklist = Mock()
        mock_tasklist_factory = Mock(return_value=mock_tasklist)

        with patch("cli.notion_tasks.svc.listar_opcoes") as mock_opcoes:
            mock_opcoes.return_value = {
                "status": ["Entrada", "Concluída"],
                "duracao": [],
                "areas": []
            }

            with pytest.raises(CLIError) as exc_info:
                cmd_criar(mock_args, tasklist_factory=mock_tasklist_factory)

            error_msg = str(exc_info.value)
            # Deve ser específico e útil
            assert "inválido" in error_msg.lower()
            assert "opções disponíveis" in error_msg.lower()
            assert "Entrada" in error_msg
            assert "Concluída" in error_msg