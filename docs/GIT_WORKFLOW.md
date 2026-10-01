# Fluxo de trabalho Git

Uma **branch por etapa** do cronograma, sempre partindo de `main` atualizada e voltando para ela via **Pull Request**.

## Convenção de nomes

| Etapa do cronograma | Branch |
|---|---|
| 3. Setup Infra | `etapa/03-infra` |
| 4. Backend RAG + mapeamento seguro | `etapa/04-backend-rag` |
| 5. Frontend Widget (Tauri + React) | `etapa/05-frontend-widget` |
| 6. Painel no-code + busca web | `etapa/06-painel-no-code` |
| 7. Testes automatizados e CI/CD | `etapa/07-testes-ci` |

## Ciclo de cada etapa

```bash
git checkout main
git pull origin main
git checkout -b etapa/04-backend-rag

# ...trabalhe, rode os testes...
cd backend && pytest && cd ..

git add .
git commit -m "feat(backend): descrição curta do que foi feito"
git push -u origin etapa/04-backend-rag
```

Depois abra o Pull Request no GitHub (`etapa/04-backend-rag` → `main`), espere o CI ficar verde e faça o merge.

## Padrão de mensagens de commit (Conventional Commits)

- `feat:` nova funcionalidade
- `fix:` correção de bug
- `test:` testes
- `docs:` documentação
- `chore:` infra, dependências, CI
- `refactor:` reorganização sem mudar comportamento

## Regras

- Nunca commitar `.env` (contém segredos). Só o `.env.example`.
- Não commitar `backend/app/data/*.json` (dados de runtime).
- Só faça merge com o CI verde.
