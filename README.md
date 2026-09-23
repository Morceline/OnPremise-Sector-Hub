# OnPremise-Sector-Hub

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.141.1-00a393.svg)](https://fastapi.tiangolo.com)

## 📌 Sobre o Projeto
O **Assistente de Setor On-Premise** é uma solução de Inteligência Artificial de código aberto, projetada para solucionar a perda de produtividade causada por silos de conhecimento e dúvidas repetitivas em ambientes corporativos e órgãos públicos. 

O projeto adota uma arquitetura híbrida de Gestão de Conhecimento, operando localmente via Docker. A solução foca na privacidade total dos dados sensíveis da instituição e na operação com custo zero em APIs comerciais, respeitando normativas de proteção de dados (LGPD).

## 🏗️ Arquitetura e Tecnologias
O sistema utiliza um ecossistema RAG (*Retrieval-Augmented Generation*) rodando de forma encapsulada.

*   **Backend & Orquestração:** [FastAPI](https://fastapi.tiangolo.com/) (Python) para comunicação assíncrona, rápida e escalável.
*   **Motor Generativo (SLM):** [Ollama](https://ollama.ai/) para rodar Modelos de Linguagem Pequenos (SLMs) localmente, sem dependência de internet.
*   **Banco de Dados Vetorial:** [Qdrant](https://qdrant.tech/) para indexação ultrarrápida dos documentos e busca semântica.
*   **Integração e DevOps:** Docker e Docker Compose, garantindo deploy em ambientes locais e testes automatizados sem atrito.
*   **Processamento de Dados:** Bibliotecas de processamento como LangChain (Chunking) e PyPDF.

## 🚀 Como iniciar o projeto

### Pré-requisitos
*   [Docker](https://www.docker.com/) e Docker Compose instalados.
*   Git para clonagem do repositório.

### Instalação (Ambiente de Desenvolvimento)
1. Clone o repositório:
```bash
git clone [https://github.com/Morceline/OnPremise-Sector-Hub.git](https://github.com/Morceline/OnPremise-Sector-Hub.git)
cd OnPremise-Sector-Hub