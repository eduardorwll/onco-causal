# tasks.md — Plano de Execução: Auditoria Científica, Engenharia, Segurança e Versionamento

> **Status Global:** ✅ Fases 1–3 concluídas; Fase 4 em execução (Fase 0 concluída: skills localizadas/instaladas em ~/Sandbox/.agents/skills: planning-and-task-breakdown, scientific-critical-thinking, statistical-analysis, graphify, graft, security-audit)  
> **Escopo:** Consolidação do Stage 01, Auditoria Tripla (Ciência, Engenharia, Segurança), Blindagem Git e Preparação do Stage 02.

---

## Fase 0: Descoberta e Verificação Prévia de Skills (`HARD STOP GATE`)
- [x] **0.1.** Inspecionar o ambiente `~/Sandbox` para localizar os caminhos exatos das skills requeridas:
  - Skill de Planejamento e Checklist (Pacote de Engenharia)
  - Skill Especializada em Ciência / Pesquisa Científica
  - Rotina de Engenharia (`graphify` + `graft` + Linting/Typecheck)
  - Skill de Auditoria de Segurança (*Security Audit*)
- [x] **0.2. [REGRA DE BLOQUEIO]:** Caso QUALQUER uma das skills acima não seja encontrada ou apresente ambiguidade de nome/caminho, **INTERROMPER IMEDIATAMENTE** a execução e perguntar ao usuário antes de tocar em qualquer arquivo.

## Fase 1: Auditoria de Confiabilidade Científica (Skill de Ciência)
- [x] **1.1.** Executar a skill científica sobre os artefatos gerados no Stage 01 (`diretorio_municipios_full.parquet` e `municipios_recorte_tabfm.parquet`) e sobre `configs/domain_spec.yaml`.
- [x] **1.2.** Auditar a integridade dos códigos IBGE de 7 dígitos nos polos estratégicos (Sapezal-MT: o diretório oficial BigQuery/IBGE traz `5107875`; `5107877` NÃO existe — mantido `5107875`; validar o dígito verificador módulo 10 e validar o tratamento de municípios emancipados pós-1996 vs. `5101837`).
- [x] **1.3.** Verificar a representatividade estatística dos 685 municípios do recorte (`1_Capital`: 27, `2_Polo_Estrategico`: 13, `3_Acima_50k`: 645) frente à distribuição das sub-bacias hidrográficas para garantir ausência de viés de seleção regional.
- [x] **1.4. [ Checkpoint de Paradigma 1 ]:** Emitir parecer com melhorias científicas para o acoplamento do Stage 02 (Padronização Etária e Suavização Espacial $k=31$).

## Fase 2: Rotina de Engenharia e Qualidade Estrutural (Pacote de Engenharia)
- [x] **2.1.** Re-executar `graphify` para confirmar 0 ciclos de importação e atualizar o grafo da AST pós-testes.
- [x] **2.2.** Executar validação estática estrita na árvore `src/` e `tests/` via `uv` (`ruff check`, `ruff format --check` e checagem de tipos).
- [x] **2.3.** Rodar a suíte `uv run pytest -v` garantindo 100% de aprovação determinística.
- [x] **2.4. [ Checkpoint de Paradigma 2 ]:** Propor melhorias de engenharia no paradigma *Declarative Contract-Driven* (ex.: cache de metadados de Dry-Run, hashes SHA-256 de artefatos Parquet).

## Fase 3: Auditoria de Segurança e Blindagem do `.gitignore` (Skill de Security Audit)
- [x] **3.1.** Executar a skill de *Security Audit* varrendo todo o repositório `~/Sandbox/src/onco-causal`.
- [x] **3.2.** Verificar ausência absoluta de vazamento de segredos, tokens OAuth, chaves JSON de Service Accounts do GCP, variáveis de `.env` ou Project IDs sensíveis hardcoded no histórico ou staging.
- [x] **3.3.** Atualizar e blindar o arquivo `.gitignore` bloqueando:
  - Artefatos de dados pesados e camadas Medallion (`data/raw/*`, `data/staging/*.parquet`, `data/features/*.parquet`, mantendo apenas `.gitkeep`).
  - Credenciais e configurações locais (`.env`, `.env.*`, `*.json` de credenciais GCP, `.gcloud/`).
  - Ambientes virtuais e caches Python/IDE (`.venv/`, `__pycache__/`, `.pytest_cache/`, `.ruff_cache/`, `.mypy_cache/`).
  - Caches temporários de agentes e grafos locais que não devam ir para produção.
- [x] **3.4. [ Checkpoint de Paradigma 3 ]:** Propor melhorias de governança de dados e segurança (ex.: hooks `pre-commit`, isolamento de credenciais ADC).

## Fase 4: Versionamento Git e Conexão Remota (`GitHub`)
- [x] **4.1.** Inicializar o repositório Git local (`git init -b main`), caso ainda não inicializado, e verificar `git status` para garantir que nenhum `.parquet` ou `.env` entrou no índice.
- [x] **4.2.** Configurar o repositório remoto apontando para `git@github.com:eduardorwll/onco-causal.git` (validando se o remote `origin` já existe ou adicionando-o).
- [x] **4.3.** Realizar o commit estruturado seguindo *Conventional Commits*: `feat(stage01): implement declarative core, BigQuery engine and municipality sampling`.
- [ ] **4.4.** Testar conectividade SSH e realizar o push inicial (`git push -u origin main`).
- [ ] **4.5. [ Checkpoint de Paradigma 4 ]:** Propor diretrizes de CI/CD e versionamento de dados científicos (DVC / metadados de linhagem) para os próximos estágios.
