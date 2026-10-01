# OnPremise-Sector-Hub

Assistente corporativo baseado em IA, **100% on-premise (zero-cloud)**, personalizável por setor (jurídico, saúde, RH, militar, alimentício, etc.). Combina um Small Language Model local (Ollama + Qwen 2.5 3B) com um pipeline **RAG** (Qdrant) para responder dúvidas de colaboradores com base nos manuais e diretrizes internas da empresa, reduzindo interrupções (*context switching*) e mantendo os dados dentro da rede local (adequação à LGPD).

> Projeto acadêmico .

## Sumário

- [Arquitetura](#arquitetura)
- [Requisitos](#requisitos)
- [Instalação e execução](#instalação-e-execução)
- [Endpoints](#endpoints)
- [Testes automatizados](#testes-automatizados)
- [Segurança](#segurança)
- [Boas práticas de consumo de recursos](#boas-práticas-de-consumo-de-recursos)
- [Fluxo de trabalho Git](#fluxo-de-trabalho-git)
- [Roadmap](#roadmap)

## Arquitetura

```
 Widget Desktop (Tauri + React)  ──HTTP──►  FastAPI (Docker, :8000)
                                               │
                     ┌─────────────────────────┼──────────────────────────┐
                     ▼                         ▼                          ▼
              Qdrant (Docker)        Ollama (nativo no Windows)     Arquivos locais
              busca vetorial         LLM Qwen 2.5 3B + embeddings   (allowlist/blocklist)
                                     nomic-embed-text
```

- **Ollama roda fora do Docker** (nativo no Windows) por consumir menos RAM que em container.
- **Qdrant** roda em Docker com limite de memória (`mem_limit`).
- A configuração do setor é **persistida em JSON local** (`backend/app/data/active_config.json`) — existe uma única configuração ativa por instalação, então um banco relacional seria complexidade desnecessária.

### Estrutura do backend

```
backend/
├── app/
│   ├── main.py              # Entrada, CORS restrito, lifespan, /health
│   ├── core/                # Settings, segurança (chave do gestor), injeção de dependências
│   ├── api/                 # Rotas: chat, config, document, feedback, it_support
│   ├── models/              # Esquemas Pydantic
│   ├── services/            # RAG, leitor seguro de arquivos, scraper, mailer, persistência, cliente LLM
│   └── data/                # Dados de runtime (não versionados)
├── tests/                   # Suíte pytest (Qdrant/Ollama mockados)
├── Dockerfile
├── requirements.txt / requirements-dev.txt
└── .env.example
```

## Requisitos

- Docker Desktop
- [Ollama](https://ollama.com) instalado nativamente, com os modelos:
  ```bash
  ollama pull qwen2.5:3b
  ollama pull nomic-embed-text
  ```
- Python 3.12 (apenas para rodar testes/desenvolvimento fora do Docker)

## Instalação e execução

1. Copie o arquivo de ambiente e preencha:
   ```bash
   cp backend/.env.example backend/.env
   ```
2. Gere o hash da chave do gestor e cole em `MANAGER_KEY_HASH`:
   ```bash
   python -c "import hashlib; print(hashlib.sha256(b'SUA_CHAVE_AQUI').hexdigest())"
   ```
3. Confirme que o Ollama está rodando (`ollama list`).
4. Suba os serviços:
   ```bash
   docker compose up -d --build
   ```
5. Verifique: `http://localhost:8000/health` e a documentação interativa em `http://localhost:8000/docs`.

## Endpoints

| Método | Rota | Proteção | Descrição |
|---|---|---|---|
| GET | `/health` | — | Estado da API, Qdrant e Ollama |
| POST | `/api/v1/config/save` | `X-Manager-Key` | Salva config do setor e inicia indexação em segundo plano |
| GET | `/api/v1/config/active` | — | Config pública (setor, paleta) — sem expor caminhos locais |
| POST | `/api/v1/document/sync` | `X-Manager-Key` | Ressincroniza pastas autorizadas |
| POST | `/api/v1/chat/query` | — | Pergunta do colaborador (RAG + LLM) |
| POST | `/api/v1/it-support/query` | — | Dúvidas básicas de TI (universal, sem RAG); `simplify=true` reescreve mais simples |
| POST | `/api/v1/feedback/submit` | — | Estrelas (1–5) + comentário opcional |

## Testes automatizados

Os testes **não dependem** de Qdrant nem Ollama (tudo é mockado), então rodam em qualquer máquina e no CI.

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements-dev.txt
pytest -v
pytest --cov=app --cov-report=term-missing   # com cobertura
```

Estado atual: 24 testes, ~80% de cobertura. Áreas ainda com cobertura baixa: `web_scraper`, caminho SMTP do `mailer` e a rota `/document/sync` — bons candidatos para a próxima etapa.

O CI (`.github/workflows/ci.yml`) roda a suíte e o build do Docker a cada push e Pull Request.

## Segurança

- **Allowlist/Blocklist de arquivos**: o `SafeDocumentReader` só lê dentro das pastas permitidas; a **blocklist sempre vence** em caso de conflito.
- **Chave do gestor**: rotas de configuração exigem o cabeçalho `X-Manager-Key`. Só o **hash SHA-256** fica no `.env`; a comparação usa `hmac.compare_digest`. Sem chave configurada, as rotas ficam **bloqueadas** (fail-safe).
- **CORS restrito** às origens do widget (Tauri/Vite), sem wildcard.
- **Sem telemetria**; o feedback por e-mail é opt-out (`FEEDBACK_ENABLED=false`) e sempre tem cópia local em JSONL.
- **Web controlada**: o bot só consulta URLs explicitamente cadastradas pelo gestor; não navega livremente.
- Container executa como **usuário não-root**.

**Limitação conhecida:** a chave é compartilhada por setor. Se for necessário separar permissões entre pessoas, o próximo passo é autenticação por usuário (JWT).

## Boas práticas de consumo de recursos

- Um único `httpx.AsyncClient` e uma única instância do `RAGEngine` por processo (não por request).
- IDs de chunk **determinísticos** (uuid5): reindexar o mesmo conteúdo atualiza em vez de duplicar.
- Limite de tamanho de arquivo (`MAX_FILE_SIZE_MB`) e de texto extraído de páginas web.
- Limites de memória nos containers (`mem_limit`).
- Modelo local pequeno (Qwen 2.5 3B); prefira a variante quantizada disponibilizada pelo Ollama.

## Fluxo de trabalho Git

Uma branch por etapa do cronograma, integrada via Pull Request. Detalhes em [`docs/GIT_WORKFLOW.md`](docs/GIT_WORKFLOW.md).

## Roadmap

- [x] Infra (Docker, FastAPI, Qdrant, Ollama)
- [x] Backend RAG + mapeamento híbrido seguro + testes + CI
- [ ] Frontend: Widget Desktop (Tauri + React)
- [ ] Painel no-code do gestor + busca web regulada
- [ ] Testes com dados reais e implantação em ambiente experimental
