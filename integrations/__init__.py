"""Camada ``integrations`` — adaptadores para serviços externos.

Isola o mundo de fora (Notion, e futuramente GitHub e OpenRouter) do resto do
servidor. Hoje expõe o ``notion_starter`` já existente como ``integrations.notion``;
o Agente Integrações adiciona ``github`` e o Agente IA adiciona ``openrouter`` aqui.
"""
