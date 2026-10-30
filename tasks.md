# tasks.md — Plano de Execução: Auditoria, Hardening e Stage 02 (Ingestão Multissetorial BigQuery & Padronização Etária)

> **Status Global:** ⏸️ AGUARDANDO CONFIRMAÇÃO DO USUÁRIO (STOP-AND-ASK GATE)  
> **Escopo:** Hardening de Paradigma (Fase 5), Stage 02A (Controles, PAM, RAIS/LINACH e Estrato 4 - Fase 6) e Stage 02B (SIM e Padronização Etária - Fase 7).  
> **Conformidade:** @AGENTS.md, @PROJECT_SPEC.md, @OBJETIVO.md e @METODOLOGIA.md.

---

## Histórico de Fases Concluídas (Stage 01)

- [x] **Fase 0: Descoberta e Verificação Prévia de Skills** (`planning-and-task-breakdown`, `scientific-critical-thinking`, `statistical-analysis`, `graphify`, `graft`, `security-audit`).
- [x] **Fase 1: Auditoria de Confiabilidade Científica** (Trava de Sapezal-MT = `5107875`, validação de DV IBGE módulo 10, recorte analítico de 685 municípios).
- [x] **Fase 2: Rotina de Engenharia e Qualidade Estrutural** (0 ciclos de importação no `graphify`, expurgo de hardcoding de defaults, conformidade com `ruff`, 19 testes passando).
- [x] **Fase 3: Auditoria de Segurança e Blindagem do `.gitignore`** (Expurgo de segredos, criação de `.env.example`, `.gitkeep` nas camadas Medallion, bloqueio de Parquets e arquivos de agentes).
- [x] **Fase 4: Versionamento Git e Conexão Remota** (Commits convencionais `1159677` e push para `origin/main` no GitHub).

---

## Fase 5: Hardening de Paradigma e Pré-Registro Científico (Pós-Stage 01)

### Tarefa 5.1: Higiene de Pacotes, Remoção de Stubs e Ferramental de Tipagem
- **Descrição:** Limpar stubs legados do scaffold inicial, organizar a hierarquia de pacotes Python sob `src/` e enriquecer a governança estática adicionando `ruff` e `mypy` no grupo de desenvolvimento.
- **Critérios de Aceite:**
  - [x] Adicionar `__init__.py` em `src/`, `src/core/`, `src/ingest/`, `src/utils/`, `src/spatial/`, `src/features/` e `src/models/`.
  - [x] Excluir a pasta residual `src/onco_causal/` e remover o entrypoint obsoleto `[project.scripts] onco-causal = ...` do `pyproject.toml`.
  - [x] Adicionar `ruff>=0.9.0` e `mypy>=1.14.0` ao grupo `dev` via `uv add --dev ruff mypy`.
  - [x] Executar checagem estática limpa: `uv run ruff check src tests` e `uv run mypy src`.
- **Verificação:** `uv run ruff check src tests && uv run mypy src`
- **Dependências:** Nenhuma.
- **Arquivos impactados:** `pyproject.toml`, `src/**/__init__.py`, deleção de `src/onco_causal/`.
- **Escopo estimado:** S (3–5 arquivos).

### Tarefa 5.2: Manifesto de Linhagem e Reprodutibilidade (`src/core/lineage.py`)
- **Descrição:** Implementar módulo determinístico de auditoria e linhagem de dados integrado ao ciclo de salvamento de artefatos Parquet, registrando metadados rastreáveis e versionáveis no Git (`data/staging/manifest.json`).
- **Critérios de Aceite:**
  - [x] Criar classe `LineageTracker` em `src/core/lineage.py`.
  - [x] Calcular e registrar deterministicamente:
    - SHA-256 do arquivo Parquet gerado em disco (`data/staging/*.parquet`).
    - Número de linhas e colunas do dataset aprovado no `DataContract`.
    - Hash SHA-256 do arquivo de query SQL (`sql/*.sql`) utilizado na extração.
    - Hash SHA-256 da especificação de domínio (`configs/domain_spec.yaml`).
    - Commit SHA e branch Git atual (via `git rev-parse HEAD`).
    - Timestamp ISO-8601 da extração.
  - [x] Salvar e atualizar atomicamente `data/staging/manifest.json`.
  - [x] Conectar o registro no `run_municipios_stage()` e nos novos orquestradores de ingestão.
  - [x] Garantir no `.gitignore` que `data/staging/manifest.json` **seja versionado no Git** (exceção à regra de ignorar arquivos em `data/staging/`).
- **Verificação:** `uv run python -c "from src.core.lineage import LineageTracker; print(LineageTracker)"` e teste unitário.
- **Dependências:** 5.1.
- **Arquivos impactados:** `src/core/lineage.py`, `src/ingest/municipios.py`, `.gitignore`.
- **Escopo estimado:** S (2–3 arquivos).

### Tarefa 5.3: Desacoplamento de Testes em Pirâmide (`pytest` markers)
- **Descrição:** Estruturar a suíte de testes com separação estrita entre testes unitários rápidos baseados em mocks/fixtures em memória (aptos para rodar em CI/CD sem acesso aos arquivos Parquet do disco nem ao BigQuery) e testes de integração de dados reais marcados.
- **Critérios de Aceite:**
  - [x] Configurar markers no `pyproject.toml` (`[tool.pytest.ini_options]`):
    - `unit`: Testes unitários com dados sintéticos sem IO de dados reais.
    - `data_contract`: Testes de integridade sobre artefatos Parquet reais em `data/staging/`.
    - `integration`: Testes ponta-a-ponta de engine e queries.
  - [x] Refatorar `tests/test_municipios_contract.py` para aplicar os markers adequados.
  - [x] Criar fixture sintética (`tests/conftest.py`) simulando DataFrames válidos e inválidos em memória.
  - [x] Garantir que `uv run pytest -m "unit"` execute em menos de 1 segundo sem requerer os Parquets do disco.
- **Verificação:** `uv run pytest -m "unit" -v && uv run pytest -m "data_contract" -v`
- **Dependências:** 5.1.
- **Arquivos impactados:** `pyproject.toml`, `tests/conftest.py`, `tests/test_municipios_contract.py`.
- **Escopo estimado:** S (3 arquivos).

### Tarefa 5.4: Pré-Registro Anti-*p-hacking* (Tag Git `v0.1.0-preregistration`)
- **Descrição:** Congelar formalmente o desenho do estudo, hipóteses $H_1\text{–}H_4$, janelas de latência biológica e subgrupos topográficos da CID-10 antes do processamento dos dados de mortalidade do SIM, garantindo integridade epistemológica conforme @OBJETIVO.md e @METODOLOGIA.md.
- **Critérios de Aceite:**
  - [x] Criar arquivo de pré-registro `docs/PREREGISTRATION.md` indexando o estado congelado de `OBJETIVO.md`, `METODOLOGIA.md` e `configs/domain_spec.yaml`.
  - [x] Realizar commit com mensagem convencional: `chore(preregistration): freeze hypotheses H1-H4 and latency windows`.
  - [x] Criar tag Git anotada e assinada: `git tag -a v0.1.0-preregistration -m "Pre-registration of hypotheses, target groups and biological latency windows"`.
  - [x] Enviar a tag ao repositório remoto: `git push origin v0.1.0-preregistration`.
- **Verificação:** `git tag -v v0.1.0-preregistration` ou `git describe --tags`.
- **Dependências:** 5.1, 5.2, 5.3.
- **Arquivos impactados:** `docs/PREREGISTRATION.md`.
- **Escopo estimado:** XS (1 arquivo + tag git).

### Checkpoint de Paradigma 5
- [x] Relatório de melhorias de arquitetura, linhagem e reprodutibilidade emitido.
- [x] Revisão e validação com o usuário antes de avançar para a ingestão massiva do Stage 02A.

---

## Fase 6: Stage 02A — Controles Assistenciais/Saneamento, PAM e RAIS/LINACH + Estrato 4

### Tarefa 6.1: Ingestão RAIS/LINACH — Exposição Ocupacional (`Vetor D4`)
- **Descrição:** Extrair do BigQuery (`basedosdados.br_me_rais`) séries temporais municipais (1996–2024) de vínculos empregatícios formais totais e vínculos em setores com carcinógenos humanos da Portaria Interministerial nº 9/2014 (LINACH / IARC Grupo 1), mapeados pelos prefixos CNAE 2.0 em `domain_spec.yaml`.
- **Critérios de Aceite:**
  - [ ] Criar query SQL parametrizada `sql/02_rais_exposicao_linach.sql` utilizando agregação por `id_municipio` e `ano`, cruzando vínculos com prefixos CNAE 2.0 parametrizados via `@cnae_prefixes`.
  - [ ] Criar orquestrador `src/ingest/rais.py` consumindo `BigQueryEngine` com Dry-Run e Storage API.
  - [ ] Definir contrato de dados `RAIS_LINACH_CONTRACT` em `src/core/contracts.py`:
    - PK composta: `("id_municipio", "ano")`.
    - Colunas obrigatórias: `id_municipio` (7 dígitos), `ano` (Int64), `vinculos_totais` (Int64), `vinculos_linach` (Int64), `prop_linach` (Float64).
    - Sentinelas mapeados para conversão em `null`.
  - [ ] Persistir em `data/staging/rais_linach_anual.parquet` (`zstd`) e registrar no `manifest.json`.
- **Verificação:** `uv run python -m src.ingest.rais` e teste com `pytest`.
- **Dependências:** Fase 5.
- **Arquivos impactados:** `sql/02_rais_exposicao_linach.sql`, `src/ingest/rais.py`, `src/core/contracts.py`.
- **Escopo estimado:** M (3 arquivos).

### Tarefa 6.2: Ingestão PAM/IBGE — Intensidade Agroquímica Histórica (`Vetor D1`)
- **Descrição:** Extrair da Produção Agrícola Municipal (`basedosdados.br_ibge_pam`) a área plantada (hectares) das seis culturas-âncora do método de Pignati et al. (soja, milho, algodão, cana-de-açúcar, arroz e citros) para todos os municípios brasileiros entre 1996 e 2024.
- **Critérios de Aceite:**
  - [ ] Criar query SQL parametrizada `sql/03_pam_lavouras.sql` agregando hectares por `id_municipio` e `ano` para lavouras temporárias e permanentes.
  - [ ] Criar orquestrador `src/ingest/pam.py` consumindo `BigQueryEngine`.
  - [ ] Definir contrato de dados `PAM_LAVOURAS_CONTRACT`:
    - PK composta: `("id_municipio", "ano")`.
    - Colunas: `id_municipio` (7 dígitos), `ano` (Int64), áreas individuais por cultura e `area_total_lavouras_criticas_ha` (Float64/Int64).
    - Tratamento de valores nulos/sentinelas (ausência de plantio = 0 ha vs ausência de dado = null).
  - [ ] Persistir em `data/staging/pam_lavouras_anual.parquet` (`zstd`) e registrar no `manifest.json`.
- **Verificação:** `uv run python -m src.ingest.pam` e teste com `pytest`.
- **Dependências:** Fase 5.
- **Arquivos impactados:** `sql/03_pam_lavouras.sql`, `src/ingest/pam.py`, `src/core/contracts.py`.
- **Escopo estimado:** M (3 arquivos).

### Tarefa 6.3: Ingestão de Controles Assistenciais e Sanitários (`Vetor Z` — CNES e SNIS)
- **Descrição:** Extrair variáveis municipais de oferta hospitalar especializada em oncologia e saneamento básico para viabilizar a ortogonalização do viés de detecção (Pilar III de @OBJETIVO.md).
- **Critérios de Aceite:**
  - [ ] Criar query SQL parametrizada `sql/04_cnes_snis_controles.sql`:
    - CNES (`basedosdados.br_ms_cnes`): Presença binária de estabelecimento habilitado como UNACON/CACON, contagem de leitos oncológicos/clínicos e equipamentos diagnósticos de alta complexidade (tomógrafos, mamógrafos) por `id_municipio` e `ano`.
    - SNIS (`basedosdados.br_mdr_snis`): Indicadores de cobertura de água tratada (`IN055`), índice de coleta de esgoto (`IN056`) e índice de tratamento de esgoto (`IN046`).
  - [ ] Criar orquestrador `src/ingest/controles.py` com `BigQueryEngine`.
  - [ ] Definir contrato `CONTROLES_ASSISTENCIAIS_CONTRACT`:
    - PK composta: `("id_municipio", "ano")`.
    - Schema estrito e expurgo de sentinelas (`-1`, `999.0` para null).
  - [ ] Persistir em `data/staging/controles_assistenciais_snis.parquet` (`zstd`) e registrar no `manifest.json`.
- **Verificação:** `uv run python -m src.ingest.controles` e teste com `pytest`.
- **Dependências:** Fase 5.
- **Arquivos impactados:** `sql/04_cnes_snis_controles.sql`, `src/ingest/controles.py`, `src/core/contracts.py`.
- **Escopo estimado:** M (3 arquivos).

### Tarefa 6.4: Parametrização e Materialização do Estrato 4 (`4_Controle_Interno`)
- **Descrição:** Aplicar a skill `scientific-critical-thinking` e `statistical-analysis` para definir, com base em evidências numéricas, os critérios de classificação do **Estrato 4 ("Controles Internos")** previsto em `METODOLOGIA.md` §1.2.
- **Critérios de Aceite:**
  - [ ] Definir regras no `configs/domain_spec.yaml` sob `sampling.internal_controls`:
    - População $\ge 50.000$ habitantes (estabilidade demográfica).
    - Não ser Capital estadual nem Polo Estratégico.
    - Situar-se no quantil inferior (ex.: $P \le 25$) de área agrícola temporária por habitante (PAM) e no quantil inferior de densidade proporcional LINACH (RAIS).
  - [ ] Criar rotina analítica em `src/ingest/municipios.py` para classificar o estrato `4_Controle_Interno` e recalcular `perfil_amostral` (tornando o antigo pequeno porte em `5_Pequeno_Porte` ou mantendo a hierarquia declarativa).
  - [ ] Regenerar `municipios_recorte_tabfm.parquet` contendo os 4 estratos de interesse: `1_Capital`, `2_Polo_Estrategico`, `3_Acima_50k` e `4_Controle_Interno`.
  - [ ] Criar teste estatístico específico em `tests/test_municipios_contract.py` atestando que os municípios de controle interno possuem médias de exposição química estatisticamente inferiores às do restante do recorte ($p < 0,01$, teste de Mann-Whitney U).
- **Verificação:** `uv run pytest -k "test_estrato_4"`
- **Dependências:** 6.1, 6.2, 6.3.
- **Arquivos impactados:** `configs/domain_spec.yaml`, `src/ingest/municipios.py`, `tests/test_municipios_contract.py`.
- **Escopo estimado:** M (3 arquivos).

### Checkpoint de Paradigma 6
- [ ] Relatório de melhorias de engenharia de dados, particionamento temporal e validade dos controles emitido.
- [ ] Revisão e validação com o usuário antes de avançar para a Fase 7.

---

## Fase 7: Stage 02B — Desfecho Oncológico (SIM) e Padronização Etária Direta/Indireta

### Tarefa 7.1: Ingestão SIM por Residência e Denominadores Etários
- **Descrição:** Extrair os microdados/agregações de mortalidade do Sistema de Informações sobre Mortalidade (SIM / BigQuery `basedosdados.br_ms_sim.municipio_causa`) filtrados estritamente pelo **Município de Residência** (`id_municipio_residencia`) e códigos CID-10 dos 5 subgrupos de `domain_spec.yaml`.
- **Critérios de Aceite:**
  - [ ] Criar query SQL `sql/05_sim_mortalidade_padronizada.sql` realizando a extração de contagem de óbitos $O_{i,c,a}$ por município de residência $i$, subgrupo oncológico $c$ e faixa etária $a$ (1996–2024).
  - [ ] Cruzar com as pirâmides etárias municipais do IBGE para obter as populações expostas $P_{i,a}$.
  - [ ] Criar orquestrador `src/ingest/sim.py` integrado ao `BigQueryEngine`.
  - [ ] Definir contrato `SIM_MORTALIDADE_CONTRACT` validando unicidade da PK `("id_municipio", "ano", "target_cancer")` e sem óbitos negativos.
  - [ ] Persistir em `data/staging/sim_mortalidade_bruta.parquet`.
- **Verificação:** `uv run python -m src.ingest.sim`
- **Dependências:** Fase 6.
- **Arquivos impactados:** `sql/05_sim_mortalidade_padronizada.sql`, `src/ingest/sim.py`, `src/core/contracts.py`.
- **Escopo estimado:** M (3 arquivos).

### Tarefa 7.2: Cálculo da Padronização Etária Direta ($\text{ASR}$) e Indireta ($\text{SMR}$)
- **Descrição:** Implementar motor matemático em Polars para cálculo da Taxa Padronizada por Idade ($\text{ASR}$ por 100k hab. usando os pesos mundiais Segi/OMS $w_a$) e a Razão de Mortalidade Padronizada ($\text{SMR} = O / E$) na malha integral de 5.570 municípios, preparando a entrada para a suavização Bayesiana $k=31$ (Stage 03).
- **Critérios de Aceite:**
  - [ ] Criar módulo matemático `src/spatial/age_standardization.py`:
    - Função `compute_asr(df, pop_weights="who_world") -> pl.DataFrame`.
    - Função `compute_smr(df) -> pl.DataFrame` (calculando taxas de referência nacionais $R_{c,a}$ e óbitos esperados $E_{i,c}$).
  - [ ] Validar que nenhum município possui $\text{ASR} < 0$.
  - [ ] Validar que municípios sem óbitos notificados possuem $\text{ASR} = 0.0$ e $E_{i,c} > 0$.
  - [ ] Persistir o dataset de taxas padronizadas em `data/staging/sim_taxas_padronizadas_5570.parquet` (`zstd`).
  - [ ] Registrar no `manifest.json`.
- **Verificação:** `uv run pytest -k "test_age_standardization"`
- **Dependências:** 7.1.
- **Arquivos impactados:** `src/spatial/age_standardization.py`, `tests/test_age_standardization.py`.
- **Escopo estimado:** M (2 arquivos).

### Tarefa 7.3: Auditoria Tripla Final do Stage 02, Blindagem e Deploy
- **Descrição:** Executar o protocolo completo de auditoria (Ciência, Engenharia e Segurança), regenerar o grafo de conhecimento AST via `graphify`, atualizar linhagem e publicar no repositório GitHub.
- **Critérios de Aceite:**
  - [ ] **Ciência:** Avaliar estabilidade das taxas $\text{ASR}$ entre municípios grandes vs pequenos (comprovando empiricamente a necessidade da suavização Bayesiana $k=31$ para pequenos denominadores).
  - [ ] **Engenharia:** Rodar `uvx --from graphifyy graphify update .` (0 ciclos de importação) e `uv run ruff check src tests` (0 erros).
  - [ ] **Segurança:** Varredura de segredos e checagem de que nenhum Parquet foi adicionado ao Git (`git status --ignored`).
  - [ ] **Testes:** 100% de aprovação na suíte completa (`uv run pytest -v`).
  - [ ] **Deploy:** Commit atômico convencional (`feat(stage02): multivariable BQ ingestion, internal controls and age standardization`), tag de release e push para `origin/main`.
- **Verificação:** `git log -n 1 --stat && git status`
- **Dependências:** 7.1, 7.2.
- **Arquivos impactados:** Todo o repositório.
- **Escopo estimado:** S.

### Checkpoint de Paradigma 7
- [ ] Relatório final de melhorias no paradigma de desenvolvimento do projeto para subsidiar o início do Stage 03 (Geoespacial e Suavização Bayesiana Empírica $k=31$).
