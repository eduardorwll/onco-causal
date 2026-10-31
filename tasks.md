# tasks.md — Plano de Execução: Stage 04 (Engenharia de Lags Biológicos e Benchmark Preditivo Multi-Paradigma)

> **Status Global:** ✅ STAGES 01, 02, 03 E 04 CONCLUÍDOS | PRONTO PARA STAGE 05 (INFERÊNCIA CAUSAL DOUBLEML/DOWHY)  
> **Escopo:** Fase 12 (Stage 04A: Backfill Histórico de Exposições 1998–2020), Fase 13 (Stage 04B: Engenharia de Lags e Master Panel), Fase 14 (Stage 04C: Benchmark Multi-Paradigma TabFM/TabNet/GBDT + TreeSHAP) e Fase 15 (Stage 04D: Auditoria Científica e Qualidade).  
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
  - [x] Criar query SQL parametrizada `sql/02_rais_exposicao_linach.sql` utilizando agregação por `id_municipio` e `ano`, cruzando vínculos com prefixos CNAE 2.0 parametrizados via `@cnae_prefixes`.
  - [x] Criar orquestrador `src/ingest/rais.py` consumindo `BigQueryEngine` com Dry-Run e Storage API.
  - [x] Definir contrato de dados `RAIS_LINACH_CONTRACT` em `src/core/contracts.py`:
    - PK composta: `("id_municipio", "ano")`.
    - Colunas obrigatórias: `id_municipio` (7 dígitos), `ano` (Int64), `vinculos_totais` (Int64), `vinculos_linach` (Int64), `prop_linach` (Float64).
    - Sentinelas mapeados para conversão em `null`.
  - [x] Persistir em `data/staging/rais_linach_anual.parquet` (`zstd`) e registrar no `manifest.json`.
- **Verificação:** `uv run python -m src.ingest.rais` e teste com `pytest`.
- **Dependências:** Fase 5.
- **Arquivos impactados:** `sql/02_rais_exposicao_linach.sql`, `src/ingest/rais.py`, `src/core/contracts.py`.
- **Escopo estimado:** M (3 arquivos).

### Tarefa 6.2: Ingestão PAM/IBGE — Intensidade Agroquímica Histórica (`Vetor D1`)
- **Descrição:** Extrair da Produção Agrícola Municipal (`basedosdados.br_ibge_pam`) a área plantada (hectares) das seis culturas-âncora do método de Pignati et al. (soja, milho, algodão, cana-de-açúcar, arroz e citros) para todos os municípios brasileiros entre 1996 e 2024.
- **Critérios de Aceite:**
  - [x] Criar query SQL parametrizada `sql/03_pam_lavouras.sql` agregando hectares por `id_municipio` e `ano` para lavouras temporárias e permanentes.
  - [x] Criar orquestrador `src/ingest/pam.py` consumindo `BigQueryEngine`.
  - [x] Definir contrato de dados `PAM_LAVOURAS_CONTRACT`:
    - PK composta: `("id_municipio", "ano")`.
    - Colunas: `id_municipio` (7 dígitos), `ano` (Int64), áreas individuais por cultura e `area_total_lavouras_criticas_ha` (Float64/Int64).
    - Tratamento de valores nulos/sentinelas (ausência de plantio = 0 ha vs ausência de dado = null).
  - [x] Persistir em `data/staging/pam_lavouras_anual.parquet` (`zstd`) e registrar no `manifest.json`.
- **Verificação:** `uv run python -m src.ingest.pam` e teste com `pytest`.
- **Dependências:** Fase 5.
- **Arquivos impactados:** `sql/03_pam_lavouras.sql`, `src/ingest/pam.py`, `src/core/contracts.py`.
- **Escopo estimado:** M (3 arquivos).

### Tarefa 6.3: Ingestão de Controles Assistenciais e Sanitários (`Vetor Z` — CNES e SNIS)
- **Descrição:** Extrair variáveis municipais de oferta hospitalar especializada em oncologia e saneamento básico para viabilizar a ortogonalização do viés de detecção (Pilar III de @OBJETIVO.md).
- **Critérios de Aceite:**
  - [x] Criar query SQL parametrizada `sql/04_cnes_snis_controles.sql`:
    - CNES (`basedosdados.br_ms_cnes`): Presença binária de estabelecimento habilitado como UNACON/CACON, contagem de leitos oncológicos/clínicos e equipamentos diagnósticos de alta complexidade (tomógrafos, mamógrafos) por `id_municipio` e `ano`.
    - SNIS (`basedosdados.br_mdr_snis`): Indicadores de cobertura de água tratada (`IN055`), índice de coleta de esgoto (`IN056`) e índice de tratamento de esgoto (`IN046`).
  - [x] Criar orquestrador `src/ingest/controles.py` com `BigQueryEngine`.
  - [x] Definir contrato `CONTROLES_ASSISTENCIAIS_CONTRACT`:
    - PK composta: `("id_municipio", "ano")`.
    - Schema estrito e expurgo de sentinelas (`-1`, `999.0` para null).
  - [x] Persistir em `data/staging/controles_assistenciais_snis.parquet` (`zstd`) e registrar no `manifest.json`.
- **Verificação:** `uv run python -m src.ingest.controles` e teste com `pytest`.
- **Dependências:** Fase 5.
- **Arquivos impactados:** `sql/04_cnes_snis_controles.sql`, `src/ingest/controles.py`, `src/core/contracts.py`.
- **Escopo estimado:** M (3 arquivos).

### Tarefa 6.4: Parametrização e Materialização do Estrato 4 (`4_Controle_Interno`)
- **Descrição:** Aplicar a skill `scientific-critical-thinking` e `statistical-analysis` para definir, com base em evidências numéricas, os critérios de classificação do **Estrato 4 ("Controles Internos")** previsto em `METODOLOGIA.md` §1.2.
- **Critérios de Aceite:**
  - [x] Definir regras no `configs/domain_spec.yaml` sob `sampling.internal_controls`:
    - População $\ge 50.000$ habitantes (estabilidade demográfica).
    - Não ser Capital estadual nem Polo Estratégico.
    - Situar-se no quantil inferior (ex.: $P \le 25$) de área agrícola temporária por habitante (PAM) e no quantil inferior de densidade proporcional LINACH (RAIS).
  - [x] Criar rotina analítica em `src/ingest/municipios.py` para classificar o estrato `4_Controle_Interno` e recalcular `perfil_amostral` (tornando o antigo pequeno porte em `5_Pequeno_Porte` ou mantendo a hierarquia declarativa).
  - [x] Regenerar `municipios_recorte_tabfm.parquet` contendo os 4 estratos de interesse: `1_Capital`, `2_Polo_Estrategico`, `3_Acima_50k` e `4_Controle_Interno`.
  - [x] Criar teste estatístico específico em `tests/test_municipios_contract.py` atestando que os municípios de controle interno possuem médias de exposição química estatisticamente inferiores às do restante do recorte ($p < 0,01$, teste de Mann-Whitney U).
- **Verificação:** `uv run pytest -k "test_estrato_4"`
- **Dependências:** 6.1, 6.2, 6.3.
- **Arquivos impactados:** `configs/domain_spec.yaml`, `src/ingest/municipios.py`, `tests/test_municipios_contract.py`.
- **Escopo estimado:** M (3 arquivos).

### Checkpoint de Paradigma 6
- [x] Relatório de melhorias de engenharia de dados, particionamento temporal e validade dos controles emitido.
- [x] Revisão e validação com o usuário antes de avançar para a Fase 7.

---

## Fase 7: Stage 02B — Desfecho Oncológico (SIM) e Padronização Etária Direta/Indireta

### Tarefa 7.1: Ingestão SIM por Residência e Denominadores Etários
- **Descrição:** Extrair os microdados/agregações de mortalidade do Sistema de Informações sobre Mortalidade (SIM / BigQuery `basedosdados.br_ms_sim.municipio_causa`) filtrados estritamente pelo **Município de Residência** (`id_municipio_residencia`) e códigos CID-10 dos 5 subgrupos de `domain_spec.yaml`.
- **Critérios de Aceite:**
  - [x] Criar query SQL `sql/05_sim_mortalidade_padronizada.sql` realizando a extração de contagem de óbitos $O_{i,c,a}$ por município de residência $i$, subgrupo oncológico $c$ e faixa etária $a$ (1996–2024).
  - [x] Cruzar com as pirâmides etárias municipais do IBGE para obter as populações expostas $P_{i,a}$.
  - [x] Criar orquestrador `src/ingest/sim.py` integrado ao `BigQueryEngine`.
  - [x] Definir contrato `SIM_MORTALIDADE_CONTRACT` validando unicidade da PK `("id_municipio", "ano", "target_cancer")` e sem óbitos negativos.
  - [x] Persistir em `data/staging/sim_taxas_padronizadas_5570.parquet`.
- **Verificação:** `uv run python -m src.ingest.sim`
- **Dependências:** Fase 6.
- **Arquivos impactados:** `sql/05_sim_mortalidade_padronizada.sql`, `src/ingest/sim.py`, `src/core/contracts.py`.
- **Escopo estimado:** M (3 arquivos).

### Tarefa 7.2: Cálculo da Padronização Etária Direta ($\text{ASR}$) e Indireta ($\text{SMR}$)
- **Descrição:** Implementar motor matemático em Polars para cálculo da Taxa Padronizada por Idade ($\text{ASR}$ por 100k hab. usando os pesos mundiais Segi/OMS $w_a$) e a Razão de Mortalidade Padronizada ($\text{SMR} = O / E$) na malha integral de 5.570 municípios, preparando a entrada para a suavização Bayesiana $k=31$ (Stage 03).
- **Critérios de Aceite:**
  - [x] Criar módulo matemático `src/spatial/age_standardization.py`:
    - Função `compute_standardized_rates(df_strata) -> pl.DataFrame` (calculando $\text{ASR}$ mundial direta e $\text{SMR}$ indireta com taxas de referência nacionais).
  - [x] Validar que nenhum município possui $\text{ASR} < 0$.
  - [x] Validar que municípios sem óbitos notificados possuem $\text{ASR} = 0.0$ e $E_{i,c} > 0$.
  - [x] Persistir o dataset de taxas padronizadas em `data/staging/sim_taxas_padronizadas_5570.parquet` (`zstd`).
  - [x] Registrar no `manifest.json`.
- **Verificação:** `uv run pytest -k "test_age_standardization"`
- **Dependências:** 7.1.
- **Arquivos impactados:** `src/spatial/age_standardization.py`, `tests/test_age_standardization.py`.
- **Escopo estimado:** M (2 arquivos).

### Tarefa 7.3: Auditoria Tripla Final do Stage 02, Blindagem e Deploy
- **Descrição:** Executar o protocolo completo de auditoria (Ciência, Engenharia e Segurança), regenerar o grafo de conhecimento AST via `graphify`, atualizar linhagem e publicar no repositório GitHub.
- **Critérios de Aceite:**
  - [x] **Ciência:** Avaliar estabilidade das taxas $\text{ASR}$ entre municípios grandes vs pequenos (comprovando empiricamente a necessidade da suavização Bayesiana $k=31$ para pequenos denominadores).
  - [x] **Engenharia:** Rodar `uvx --from graphifyy graphify update .` (0 ciclos de importação) e `uv run ruff check src tests` (0 erros).
  - [x] **Segurança:** Varredura de segredos e checagem de que nenhum Parquet foi adicionado ao Git (`git status --ignored`).
  - [x] **Testes:** 100% de aprovação na suíte completa (`uv run pytest -v`).
  - [x] **Deploy:** Commit atômico convencional (`feat(stage02): multivariable BQ ingestion, internal controls and age standardization`), tag de release e push para `origin/main`.
- **Verificação:** `git log -n 1 --stat && git status`
- **Dependências:** 7.1, 7.2.
- **Arquivos impactados:** Todo o repositório.
- **Escopo estimado:** S.

### Checkpoint de Paradigma 7
- [x] Relatório final de melhorias no paradigma de desenvolvimento do projeto para subsidiar o início do Stage 03 (Geoespacial e Suavização Bayesiana Empírica $k=31$).

---

## Fase 8: Stage 03A — Arquitetura Espacial e Malhas Base (Sedes Municipais e Ottobacias Nível 4)

### Tarefa 8.1: Governança de Dependências Geoespaciais e Parâmetros de Projeção
- **Descrição:** Auditar o ambiente de execução Python 3.14 via `uv` para assegurar o funcionamento integrado de `geopandas`, `libpysal`, `esda`, `shapely`, `pyarrow` e ferramentas de blocagem espacial. Adicionar os parâmetros da projeção de área equivalente `EPSG:5070` (Brazil Albers / SIRGAS 2000) e parâmetros de raio de vizinhança ($k=31$) na especificação de domínio `configs/domain_spec.yaml` e nos modelos tipados de `src/core/settings.py`.
- **Critérios de Aceite:**
  - [x] Verificar disponibilidade e versões de `geopandas`, `libpysal`, `esda` e `shapely` no ambiente `uv`.
  - [x] Adicionar parâmetros geoespaciais em `configs/domain_spec.yaml`:
    - `spatial.crs_proj`: `"EPSG:5070"` (SIRGAS 2000 / Brazil Albers Equal Area).
    - `spatial.knn_neighbors`: `31`.
    - `spatial.ottobacias_level`: `4`.
    - `spatial.dead_zone_buffer_km`: `30.0`.
  - [x] Tipar as configurações de geoprocessamento em `src/core/settings.py` (`DomainSpec`).
- **Verificação:** `uv run python -c "import geopandas, libpysal, esda, shapely; print('Geo stack OK')"` e `uv run pytest -m "unit"`
- **Dependências:** Fase 7.
- **Arquivos impactados:** `pyproject.toml`, `configs/domain_spec.yaml`, `src/core/settings.py`.
- **Escopo estimado:** S (3 arquivos).

### Tarefa 8.2: Ingestão, Reprojeção e Validação das Sedes Municipais e Ottobacias ANA (`src/spatial/geometries.py`)
- **Descrição:** Desenvolver o módulo reprodutível de ingestão e preparação das malhas vetoriais oficiais: as Sedes Municipais do IBGE (coordenadas pontuais oficiais dos 5.570 municípios) e as Ottobacias Nível 4 da ANA (polígonos de bacias hidrográficas). Ambas as camadas devem ser validadas e reprojetadas para `EPSG:5070`.
- **Critérios de Aceite:**
  - [x] Criar módulo `src/spatial/geometries.py` com funções determinísticas:
    - `load_municipal_seats(domain_spec) -> gpd.GeoDataFrame`: Ingestão das sedes municipais IBGE com chave `id_municipio` (7 dígitos) e geometria pontual (`Point`), reprojetada para `EPSG:5070`.
    - `load_ottobacias_level4(domain_spec) -> gpd.GeoDataFrame`: Ingestão dos polígonos das Ottobacias Nível 4 da ANA com identificador `ottobacia_id`, reprojetados para `EPSG:5070`.
  - [x] Garantir armazenamento imutável de artefatos brutos em `data/raw/geometries/`.
  - [x] Validar que exatamente 5.570 sedes municipais válidas são carregadas e indexadas.
- **Verificação:** `uv run python -m src.spatial.geometries`
- **Dependências:** 8.1.
- **Arquivos impactados:** `src/spatial/geometries.py`.
- **Escopo estimado:** M (1–2 arquivos).

### Tarefa 8.3: Spatial Join Sede-Bacia Nível 4 e Contrato Geométrico Imutável (`src/spatial/ottobacias.py`)
- **Descrição:** Executar o cruzamento espacial (*Spatial Join*) estrito baseado na decisão de fronteira da Chefia de Pesquisa: o ponto da **Sede Municipal** dentro do polígono da Ottobacia Nível 4 (`sedes within ottobacias`). Definir contrato de dados imutável, persistir em Parquet e registrar no manifesto de linhagem.
- **Critérios de Aceite:**
  - [x] Criar módulo `src/spatial/ottobacias.py` implementando `assign_ottobacias(gdf_sedes, gdf_ottobacias) -> pl.DataFrame`.
  - [x] Tratamento determinístico de exceções costeiras ou ilhas (se houver sede em polígono de borda marinha, atribuir bacia de menor distância euclidiana via `nearest_join`).
  - [x] Definir contrato de dados `SPATIAL_GEOMETRIES_CONTRACT` em `src/core/contracts.py`:
    - PK obrigatória: `("id_municipio",)`.
    - Colunas: `id_municipio` (String, 7 dígitos), `ottobacia_id` (String), `latitude_sede` (Float64), `longitude_sede` (Float64), `x_proj_5070` (Float64), `y_proj_5070` (Float64).
    - Validação de 0 nulos em `id_municipio` e `ottobacia_id`.
  - [x] Persistir em `data/staging/spatial_municipios_ottobacias.parquet` (`zstd`) com registro no `manifest.json`.
- **Verificação:** `uv run python -m src.spatial.ottobacias` e teste com `pytest`.
- **Dependências:** 8.2.
- **Arquivos impactados:** `src/spatial/ottobacias.py`, `src/core/contracts.py`.
- **Escopo estimado:** M (2 arquivos).

### Checkpoint de Paradigma 8
- [x] Sedes municipais dos 5.570 municípios mapeadas e projetadas em `EPSG:5070`.
- [x] Atribuição de Ottobacia Nível 4 aprovada no `DataContract` e registrada no `manifest.json`.

---

## Fase 9: Stage 03B — Suavização Bayesiana Empírica da SMR (A Regra da Dupla Malha $k=31$)

### Tarefa 9.1: Construção da Matriz de Pesos Espaciais $W$ (KNN $k=31$ Sedes) e Suavização Bayesiana (`src/spatial/empirical_bayes.py`)
- **Descrição:** Implementar o algoritmo de Suavização Bayesiana Empírica Espacial Linear (*Spatial Linear Empirical Bayes*) aplicado estritamente sobre a **Razão de Mortalidade Padronizada (`SMR`)**, utilizando a matriz de vizinhança de $k=31$ vizinhos mais próximos construída a partir das coordenadas das **Sedes Municipais** na malha nacional integral de 5.570 municípios (Regra da Dupla Malha).
- **Critérios de Aceite:**
  - [x] Criar módulo `src/spatial/empirical_bayes.py`.
  - [x] Construir a matriz de pesos $W$ com `libpysal.weights.KNN.from_dataframe(gdf_sedes, k=31)` em `EPSG:5070`.
  - [x] Ingerir dados de `data/staging/sim_taxas_padronizadas_5570.parquet` ($O_{i,c}$, $E_{i,c}$, $\text{SMR}_{i,c}$).
  - [x] Executar o `esda.smoothing.Spatial_Empirical_Bayes(O, E, w)` para cada par `(ano, target_cancer)`.
  - [x] Extrair a taxa suavizada `smr_suavizada_eb` e o fator de encolhimento $w_i$.
  - [x] Garantir que em municípios de grande porte ($P_i > 100\text{k}$) $w_i \to 1$, e em municípios de pequeno porte ($P_i < 10\text{k}$) $w_i \to 0$, reduzindo a variância espúria.
- **Verificação:** `uv run python -m src.spatial.empirical_bayes` e inspeção de estatísticas resumo.
- **Dependências:** Fase 8, Fase 7.
- **Arquivos impactados:** `src/spatial/empirical_bayes.py`.
- **Escopo estimado:** M (1–2 arquivos).

### Tarefa 9.2: Contrato de Dados, Materialização Parquet e Rastreabilidade (`src/core/contracts.py`)
- **Descrição:** Formalizar o contrato de governança para as taxas suavizadas, persistir o artefato Parquet enriquecido e auditar a linhagem criptográfica via `LineageTracker`.
- **Critérios de Aceite:**
  - [x] Definir `SIM_TAXAS_SUAVIZADAS_EB_CONTRACT` em `src/core/contracts.py`:
    - PK composta: `("id_municipio", "ano", "target_cancer")`.
    - Colunas: `id_municipio` (String, 7 dígitos), `ano` (Int64), `target_cancer` (String), `obitos_observados` (Int64), `obitos_esperados` (Float64), `smr_bruta` (Float64), `smr_suavizada_eb` (Float64), `peso_encolhimento_w` (Float64).
    - Validação de ausência de nulos e valores plausíveis ($\text{smr} \ge 0$, $w \in [0, 1]$).
  - [x] Persistir em `data/staging/sim_taxas_suavizadas_eb.parquet` (`zstd`).
  - [x] Atualizar `data/staging/manifest.json` com SHA-256 e contagem de registros.
- **Verificação:** `uv run pytest -k "test_empirical_bayes"`
- **Dependências:** 9.1.
- **Arquivos impactados:** `src/core/contracts.py`, `src/spatial/empirical_bayes.py`.
- **Escopo estimado:** S (2 arquivos).

### Checkpoint de Paradigma 9
- [x] Suavização Bayesiana $k=31$ sobre `SMR` executada em todos os 5.570 municípios.
- [x] Artefato `sim_taxas_suavizadas_eb.parquet` validado e registrado no `manifest.json`.

---

## Fase 10: Stage 03C — Blocagem Anti-Vazamento e 5-Fold Nested SBCV com Dead-Zone

### Tarefa 10.1: Estruturação dos Blocos Hidrográficos e Estratificação Analítica (`src/spatial/cross_validation.py`)
- **Descrição:** Desenvolver o módulo de validação cruzada aninhada em blocos espaciais (*5-Fold Nested Spatial Block Cross-Validation*). O agrupamento primário é feito pelas Ottobacias Nível 4 (`ottobacia_id`), assegurando independência geométrica dos blocos e preservando a proporção balanceada dos 4 estratos analíticos (`1_Capital`, `2_Polo_Estrategico`, `3_Acima_50k`, `4_Controle_Interno`).
- **Critérios de Aceite:**
  - [x] Criar módulo `src/spatial/cross_validation.py`.
  - [x] Cruzar os 685 municípios analíticos de `municipios_recorte_tabfm.parquet` com os `ottobacia_id` de `spatial_municipios_ottobacias.parquet`.
  - [x] Particionar os blocos de Ottobacias em 5 folds disjuntos (nenhuma bacia compartilhada entre treino e teste em um mesmo split).
  - [x] Garantir que cada fold receba uma distribuição balanceada dos 4 estratos analíticos.
- **Verificação:** `uv run python -m src.spatial.cross_validation`
- **Dependências:** Fase 8, Fase 9.
- **Arquivos impactados:** `src/spatial/cross_validation.py`.
- **Escopo estimado:** M (1–2 arquivos).

### Tarefa 10.2: Implementação da Dead-Zone de Amortecimento Espacial (30 km) e Contrato de Folds
- **Descrição:** Implementar a zona de exclusão/amortecimento (*dead-zone buffer*) de 30 km nas fronteiras de cada fold de teste. Municípios do conjunto de treino cujas sedes estejam a menos de 30 km de qualquer sede do conjunto de teste são marcados como `buffer_exclusion` naquele fold específico, eliminando autocorrelação residual de vizinhança.
- **Critérios de Aceite:**
  - [x] Implementar cálculo de distâncias euclidianas em `EPSG:5070` entre sedes de treino e sedes de teste para cada fold.
  - [x] Rotular o papel de cada município em cada fold: `train`, `test` ou `buffer_exclusion`.
  - [x] Definir contrato de dados `SPATIAL_CV_FOLDS_CONTRACT` em `src/core/contracts.py`:
    - PK composta: `("id_municipio", "fold_id")`.
    - Colunas: `id_municipio` (String, 7 dígitos), `fold_id` (Int64, 0 a 4), `split_role` (String: `"train"`, `"test"`, `"buffer_exclusion"`), `ottobacia_id` (String), `perfil_amostral` (String).
  - [x] Persistir em `data/staging/spatial_cv_folds.parquet` (`zstd`) e registrar no `manifest.json`.
- **Verificação:** `uv run pytest -k "test_cross_validation"`
- **Dependências:** 10.1.
- **Arquivos impactados:** `src/spatial/cross_validation.py`, `src/core/contracts.py`.
- **Escopo estimado:** M (2 arquivos).

### Checkpoint de Paradigma 10
- [x] Partição de 5-Fold Nested SBCV gerada por Ottobacias Nível 4.
- [x] Dead-zone de 30 km computada e rotulada, com artefato `spatial_cv_folds.parquet` persistido e verificado por contrato.

---

## Fase 11: Stage 03D — Auditoria Científica, Orquestração e Qualidade Tripla

### Tarefa 11.1: Suíte de Testes de Integridade Espacial, Estabilidade e Moran Residual (`tests/test_spatial_integrity.py`)
- **Descrição:** Implementar testes automatizados de rigor epidemiológico e geoespacial em `tests/test_spatial_integrity.py`, cobrindo ausência de anomalias nas taxas suavizadas e comprovação de que a autocorrelação espacial (Moran's I) foi anulada pela dead-zone.
- **Critérios de Aceite:**
  - [x] **Teste 1 (Qualidade Numérica da SMR Suavizada):**
    - Verificar ausência total de nulos, `NaN` ou infinitos em `smr_suavizada_eb`.
    - Comprovar redução estatística de variância ($\sigma_{\text{EB}} < \sigma_{\text{bruta}}$) nos municípios de pequeno porte ($<10\text{k}$ hab.).
    - Comprovar que o fator de encolhimento médio em capitais e metrópoles é superior ao de cidades pequenas.
  - [x] **Teste 2 (Diagnóstico de Autocorrelação Residual via Moran's I):**
    - Comprovar matematicamente que a aplicação da dead-zone de 30 km impõe distância mínima $\ge 30\text{ km}$ e elimina a autocorrelação de contiguidade imediata na fronteira entre teste e treino limpo.
    - Demonstrar que o $I$ de Moran residual nos dados de teste sob matriz espacial $W$ controlada permanece baixo ($|I| < 0,45$).
  - [x] **Teste 3 (Validação da Blocagem e Geometrias):**
    - Verificar que 100% dos 5.570 municípios possuem coordenadas de sede válidas e pertencem a uma Ottobacia Nível 4.
    - Confirmar que nenhuma bacia de teste é compartilhada com o treino efetivo em qualquer fold.
- **Verificação:** `uv run pytest tests/test_spatial_integrity.py -v`
- **Dependências:** Fase 8, Fase 9, Fase 10.
- **Arquivos impactados:** `tests/test_spatial_integrity.py`.
- **Escopo estimado:** M (1 arquivo).

### Tarefa 11.2: Orquestrador Integrado do Stage 03 (`src/spatial/run_stage03.py`) e Rastreabilidade (`LineageTracker`)
- **Descrição:** Desenvolver o script CLI principal que orquestra ponta-a-ponta a execução sequencial do Stage 03 (`geometries` $\to$ `ottobacias` $\to$ `empirical_bayes` $\to$ `cross_validation`), registrando hashes SHA-256 e metadados no `manifest.json`.
- **Critérios de Aceite:**
  - [x] Criar entrypoint CLI `src/spatial/run_stage03.py`.
  - [x] Registrar cada artefato Parquet gerado (`spatial_municipios_ottobacias.parquet`, `sim_taxas_suavizadas_eb.parquet`, `spatial_cv_folds.parquet`) no `manifest.json` com seus respectivos hashes.
  - [x] Gerar relatório sintético no console com métricas de tempo, número de bacias, redução de variância e contagem de folds.
- **Verificação:** `uv run python -m src.spatial.run_stage03`
- **Dependências:** 11.1.
- **Arquivos impactados:** `src/spatial/run_stage03.py`.
- **Escopo estimado:** S (1 arquivo).

### Tarefa 11.3: Auditoria Tripla de Paradigma, Atualização do AST Graphify e Deploy Git
- **Descrição:** Conduzir o checklist mandatório pré-commit (Ciência, Engenharia e Segurança), atualizar o grafo de conhecimento AST do repositório via `graphify`, criar commit atômico convencional e enviar ao GitHub remoto.
- **Critérios de Aceite:**
  - [x] **Ciência:** Verificação do checklist epidemiológico (SMR, $k=31$ sedes, Ottobacias Nível 4, dead-zone 30km).
  - [x] **Engenharia:** Executar `uvx --from graphifyy graphify update .` (0 ciclos), `uv run ruff check src tests` (0 erros) e `uv run mypy src tests` (0 erros).
  - [x] **Segurança:** Validar que nenhum `.parquet`, shapefile bruto ou segredo foi indexado no Git (`git status --ignored`).
  - [x] **Testes:** 100% de sucesso na suíte de testes (`uv run pytest -v`).
  - [x] **Deploy:** Commit convencional (`feat(stage03): spatial geometries, empirical bayes SMR smoothing and nested block CV with dead-zone`) e push para `origin/main`.
- **Verificação:** `git log -n 1 --stat && git status`
- **Dependências:** 11.2.
- **Arquivos impactados:** Todo o repositório.
- **Escopo estimado:** S.

### Checkpoint de Paradigma 11
- [x] Stage 03 completamente orquestrado, testado e auditado.
- [x] Relatório final consolidado e autorização para avançar para o Stage 04 (Modelagem Preditiva e Benchmark TabFM).

---

## Fase 12: Stage 04A — Backfill Histórico de Exposições (1998–2020) e Variáveis Ambientais Complementares

### Tarefa 12.1: Governança de Dependências de Modelagem e XAI (`pyproject.toml`)
- **Descrição:** Adicionar as dependências de Machine Learning, Deep Learning Tabular e XAI ao `pyproject.toml` via `uv add`, assegurando compatibilidade com Python 3.14. Configurar tipagem estática e markers no `pytest`.
- **Critérios de Aceite:**
  - [x] Adicionar ao projeto via `uv`: `lightgbm`, `xgboost`, `shap`, `statsmodels`, `torch`, `pytorch-tabnet`, `tabpfn`.
  - [x] Configurar markers no `pyproject.toml`: `models` e `benchmark`.
  - [x] Validar importação limpa e rápida de todos os pacotes em um comando de verificação.
- **Verificação:** `uv run python -c "import lightgbm, xgboost, shap, statsmodels, torch, pytorch_tabnet, tabpfn; print('ML Stack OK')"`
- **Dependências:** Fase 11.
- **Arquivos impactados:** `pyproject.toml`, `uv.lock`.
- **Escopo estimado:** S (2 arquivos).

### Tarefa 12.2: Backfill Histórico PAM/IBGE (1998–2020) — Monoculturas Críticas (`sql/03_pam_lavouras.sql`, `src/ingest/pam.py`)
- **Descrição:** Estender a extração da Produção Agrícola Municipal (PAM/IBGE) para cobrir o intervalo histórico completo de 1998 a 2020 (viabilizando os lags de 10–25 anos para tumores sólidos). Executar no BigQuery em lotes anuais/quinquenais respeitando a trava de 1 GB do `BigQueryEngine` e a Storage API.
- **Critérios de Aceite:**
  - [x] Ajustar `sql/03_pam_lavouras.sql` para aceitar intervalo de anos `@anos_pam` ou loop anual determinístico.
  - [x] Executar o backfill em `src/ingest/pam.py` para todos os 5.570 municípios entre 1998 e 2020.
  - [x] Enriquecer `data/staging/pam_lavouras_anual.parquet` (cobrindo 1998–2022).
  - [x] Validar conformidade com `PAM_LAVOURAS_CONTRACT` e atualizar `manifest.json`.
- **Verificação:** `uv run python -m src.ingest.pam` e checagem de anos no Parquet.
- **Dependências:** 12.1.
- **Arquivos impactados:** `sql/03_pam_lavouras.sql`, `src/ingest/pam.py`.
- **Escopo estimado:** M (2 arquivos).

### Tarefa 12.3: Ingestão Histórica MapBiomas e Cobertura do Solo (`sql/06_mapbiomas_cobertura.sql`, `src/ingest/mapbiomas.py`)
- **Descrição:** Extrair do MapBiomas (`basedosdados.br_mapbiomas_estatisticas.cobertura_municipio_classe`) séries históricas anuais (1998–2020) de uso e cobertura do solo por município, isolando áreas de lavoura temporária, lavoura perene, pastagem e área urbana.
- **Critérios de Aceite:**
  - [x] Criar query SQL parametrizada `sql/06_mapbiomas_cobertura.sql`.
  - [x] Criar orquestrador `src/ingest/mapbiomas.py` consumindo `BigQueryEngine` com Dry-Run prévio.
  - [x] Definir `MAPBIOMAS_COBERTURA_CONTRACT` em `src/core/contracts.py`:
    - PK composta: `("id_municipio", "ano")`.
    - Colunas: `id_municipio`, `ano`, `area_lavoura_ha`, `area_pastagem_ha`, `area_urbana_ha`, `area_floresta_ha`.
  - [x] Persistir em `data/staging/mapbiomas_cobertura_anual.parquet` (`zstd`) e registrar no `manifest.json`.
- **Verificação:** `uv run python -m src.ingest.mapbiomas` e teste com `pytest`.
- **Dependências:** 12.1.
- **Arquivos impactados:** `sql/06_mapbiomas_cobertura.sql`, `src/ingest/mapbiomas.py`, `src/core/contracts.py`.
- **Escopo estimado:** M (3 arquivos).

### Tarefa 12.4: Backfill e Séries de Exposição Ocupacional LINACH/RAIS (`src/ingest/rais.py`)
- **Descrição:** Ingerir vínculos empregatícios formais e vínculos LINACH/CNAE 2.0 para o intervalo histórico de latência hematológica (2015–2020) via queries anuais particionadas no BigQuery (`basedosdados.br_me_rais.microdados_vinculos`).
- **Critérios de Aceite:**
  - [x] Executar loop anual em `src/ingest/rais.py` cobrindo 2015 a 2020 com Dry-Run de segurança (< 500 MB por ano).
  - [x] Atualizar `data/staging/rais_linach_anual.parquet` contendo o período 2015–2022.
  - [x] Validar conformidade com `RAIS_LINACH_CONTRACT` e atualizar `manifest.json`.
- **Verificação:** `uv run python -m src.ingest.rais` e checagem de anos no Parquet.
- **Dependências:** 12.1.
- **Arquivos impactados:** `src/ingest/rais.py`.
- **Escopo estimado:** S (1 arquivo).

### Checkpoint de Paradigma 12
- [x] Pilha de Machine Learning e XAI instalada e validada.
- [x] Backfill histórico de PAM (1998–2020), MapBiomas (1998–2020) e RAIS (2015–2020) consolidado em `data/staging/`.

---

## Fase 13: Stage 04B — Engenharia de Atributos Defasados (Distributed Lags) e Painel Analítico Mestre

### Tarefa 13.1: Motor Matemático de Lags Biológicos (`src/features/latency_builder.py`)
- **Descrição:** Desenvolver o módulo de cálculo de janelas temporais de latência biológica (*distributed lag windows*) respeitando estritamente as diretrizes de @METODOLOGIA.md e @configs/domain_spec.yaml.
- **Critérios de Aceite:**
  - [x] Para cada ano de desfecho $t \in [2020, 2022]$ e cada alvo oncológico $c$:
    - Neoplasias hematológicas e infantojuvenis (`C81–C96`): janela $[2, 5]$ anos $\to \tau \in [t - 5, t - 2]$.
    - Tumores sólidos (respiratório, digestivo, pele, hormoniodependente): janela $[10, 25]$ anos (ou $[10, 20]$ anos) $\to \tau \in [t - 25, t - 10]$.
  - [x] Calcular para cada vetor de exposição ($D_1$ agrícola, $D_4$ LINACH, MapBiomas) na respectiva janela de latência:
    - Média temporal: $\bar{D} = \frac{1}{\Delta \tau} \sum_\tau D_\tau$
    - Volume cumulativo: $\sum D = \sum_\tau D_\tau$
    - Tendência temporal / slope OLS: $\beta_{\text{trend}} = \frac{\text{Cov}(\tau, D_\tau)}{\text{Var}(\tau)}$
    - Pico / Máximo histórico: $\max_\tau D_\tau$
  - [x] **Garantia de Assimetria Temporal:** Nenhuma feature de exposição $D$ pode conter dados do ano contemporâneo $t$.
- **Verificação:** `uv run python -m src.features.latency_builder` e teste com `pytest`.
- **Dependências:** Fase 12.
- **Arquivos impactados:** `src/features/latency_builder.py`.
- **Escopo estimado:** M (1 arquivo).

### Tarefa 13.2: Triagem de Colinearidade no Discovery Set (VIF e Spearman)
- **Descrição:** Isolar o Conjunto de Descoberta (*Discovery Set* — 40% das bacias hidrográficas, folds 0 e 1 de `spatial_cv_folds.parquet`) para conduzir diagnóstico rigoroso de multicolinearidade antes da montagem final do painel mestre.
- **Critérios de Aceite:**
  - [x] Calcular a matriz de correlação par-a-par de Spearman no Discovery Set, exigindo $|\rho_s| < 0,70$.
  - [x] Calcular o Fator de Inflação da Variância ($\text{VIF}$) usando `statsmodels.stats.outliers_influence.variance_inflation_factor`, exigindo estritamente $\text{VIF} < 5,0$ para todas as variáveis retidas (VIF Máximo obtido: 2.4456).
  - [x] Emitir relatório com lista de features aprovadas e features eliminadas por redundância matemática.
- **Verificação:** Teste automatizado com assert $\text{VIF} < 5$.
- **Dependências:** 13.1.
- **Arquivos impactados:** `src/features/latency_builder.py`.
- **Escopo estimado:** S (1 arquivo).

### Tarefa 13.3: Consolidação do Painel Mestre e Contrato Imutável (`src/core/contracts.py`)
- **Descrição:** Unificar em uma única matriz analítica em nível de município-ano-alvo os desfechos suavizados ($Y_t$: `smr_suavizada_eb`), controles contemporâneos ($Z_t$: CNES/SNIS 2020), features defasadas de exposição ($D_{t-\text{lag}}$) e metadados geoespaciais dos 685 municípios analíticos.
- **Critérios de Aceite:**
  - [x] Definir `MASTER_PANEL_CONTRACT` em `src/core/contracts.py`:
    - PK composta: `("id_municipio", "ano", "target_cancer")`.
    - Colunas: PKs, desfechos ($Y$), controles ($Z$), features defasadas ($D$) e atributos espaciais (`ottobacia_id`, `perfil_amostral`, `x_proj_5070`, `y_proj_5070`).
    - Expurgo total de nulos nas features selecionadas.
  - [x] Persistir em `data/features/master_analytical_panel.parquet` (`zstd`, 10.275 linhas, 37 colunas).
  - [x] Registrar linhagem criptográfica no `manifest.json`.
- **Verificação:** `uv run pytest -k "test_master_panel"`
- **Dependências:** 13.1, 13.2.
- **Arquivos impactados:** `src/features/latency_builder.py`, `src/core/contracts.py`.
- **Escopo estimado:** M (2 arquivos).

### Checkpoint de Paradigma 13
- [x] Atributos defasados gerados com assimetria temporal estrita ($t-\text{lag}$).
- [x] $\text{VIF} < 5$ comprovado no Discovery Set (2.4456).
- [x] Artefato `master_analytical_panel.parquet` persistido e aprovado por contrato em `data/features/`.

---

## Fase 14: Stage 04C — Benchmark Preditivo Multi-Paradigma (TabFM/ICL, TabNet e GBDT + TreeSHAP)

### Tarefa 14.1: Motor de Validação Cruzada 5-Fold SBCV com Isolamento da Dead-Zone (`src/models/benchmark_runner.py`)
- **Descrição:** Desenvolver o orquestrador de modelagem preditiva que consome `master_analytical_panel.parquet` e avalia os modelos de machine learning através do 5-Fold Nested SBCV (`spatial_cv_folds.parquet`).
- **Critérios de Aceite:**
  - [x] Em cada fold $k \in \{0, 1, 2, 3, 4\}$:
    - Filtrar estritamente o conjunto de teste: `split_role == "test"`.
    - **Isolamento Mandatório da Dead-Zone:** Descartar 100% das observações de municípios marcados com `split_role == "buffer_exclusion"` (< 30 km da fronteira).
    - Conjunto de treino/suporte composto exclusivamente por `split_role == "train"` ($\ge 30\text{ km}$).
  - [x] Padronização de features ajustada exclusivamente no conjunto de treino limpo de cada fold (sem vazamento de estatísticas para teste).
- **Verificação:** `uv run python -m src.models.benchmark_runner`
- **Dependências:** Fase 13.
- **Arquivos impactados:** `src/models/benchmark_runner.py`.
- **Escopo estimado:** M (1 arquivo).

### Tarefa 14.2: Treinamento e Avaliação Comparativa dos 3 Paradigmas
- **Descrição:** Implementar os pipelines preditivos para os três paradigmas de modelagem tabular:
  - **Paradigma 1 (Foundation In-Context Learning):** `TabPFNRegressor` (ou `TabFM`), realizando inferência zero-shot a partir do conjunto de suporte limpo.
  - **Paradigma 2 (Deep Learning Interpretável):** `TabNetRegressor` (`pytorch-tabnet`), treinando rede neural com atenção sequencial esparsa e extraindo máscaras de features por município.
  - **Paradigma 3 (GBDTs Otimizados):** `LightGBMRegressor` e `XGBoostRegressor` com early stopping no fold de validação interna.
- **Critérios de Aceite:**
  - [x] Calcular métricas de generalização fora da amostra (OOF) para cada modelo: $R^2$, $\text{RMSE}$, $\text{MAE}$ (41.100 predições OOF geradas).
  - [x] Gerar ranking comparativo consolidado em `data/features/benchmark_metrics.parquet`: XGBoost ($R^2=+0.1379$) > LightGBM ($R^2=+0.1272$) > TabPFN ($R^2=+0.1053$) > TabNet ($R^2=+0.0289$).
  - [x] Persistir predições OOF em `data/features/benchmark_predictions.parquet` com contrato e registro no `manifest.json`.
- **Verificação:** Testes automatizados de métricas e convergência dos modelos.
- **Dependências:** 14.1.
- **Arquivos impactados:** `src/models/benchmark_runner.py`.
- **Escopo estimado:** L (2–3 arquivos).

### Tarefa 14.3: Explicabilidade Global e Local via TreeSHAP e Limiares $\text{SHAP} = 0$ (`src/models/xai_shap.py`)
- **Descrição:** Implementar o módulo de explicabilidade por valores de Shapley (`shap.TreeExplainer`) aplicado sobre o modelo campeão do benchmark, mapeando a importância global das variáveis e derivando limiares toxicológicos de corte.
- **Critérios de Aceite:**
  - [x] Calcular valores SHAP locais e globais para cada observação da coorte ($N=10.275$).
  - [x] Gerar curvas de dependência parcial (PDP/ICE) para os vetores de exposição ($D_1$ agrotóxicos/lavouras, $D_4$ LINACH).
  - [x] **Determinação Matemática do Limiar $\text{SHAP} = 0$:** Identificar para cada variável contínua de exposição o ponto de inflexão numérico onde a contribuição marginal de risco transita de neutra/protetora para aceleradora ($\text{SHAP}(D_k) > 0$).
  - [x] Salvar os limiares em `data/features/shap_inflection_thresholds.parquet` para alimentar o Simulador Contrafactual e o IDV.
- **Verificação:** `uv run python -m src.models.xai_shap`
- **Dependências:** 14.2.
- **Arquivos impactados:** `src/models/xai_shap.py`.
- **Escopo estimado:** M (1 arquivo).

### Checkpoint de Paradigma 14
- [x] 5-Fold Nested SBCV executado nos 3 paradigmas sem vazamento de dead-zone.
- [x] Ranking preditivo consolidado ($R^2$, $\text{RMSE}$, $\text{MAE}$).
- [x] Limiares de risco acelerado ($\text{SHAP} = 0$) calculados deterministicamente.

---

## Fase 15: Stage 04D — Auditoria Científica, Qualidade e Deploy

### Tarefa 15.1: Suíte de Testes de Integridade de Features e Modelos (`tests/test_features_and_models.py`)
- **Descrição:** Implementar suíte abrangente de testes automatizados garantindo rigor metodológico, ausência de vazamento temporal/espacial e estabilidade numérica.
- **Critérios de Aceite:**
  - [x] **Teste 1 (Assimetria Temporal):** Confirmar que nenhuma variável de exposição no master panel contém dados contemporâneos ao ano $t$.
  - [x] **Teste 2 (Isolamento de Dead-Zone):** Comprovar que exatamente 0 observações de `buffer_exclusion` foram utilizadas no treinamento ou suporte de qualquer fold.
  - [x] **Teste 3 (Colinearidade):** Validar que todas as features de modelagem apresentam $\text{VIF} < 5,0$ e $|\rho_s| < 0.70$ no Discovery Set.
  - [x] **Teste 4 (Moran Residual dos Erros):** Avaliar e certificar a independência topológica dos resíduos out-of-fold com isolamento espacial da dead-zone.
  - [x] **Teste 5 (Contratos de Dados):** Enforce de contratos em todos os artefatos de `data/features/`.
- **Verificação:** `uv run pytest tests/test_features_and_models.py -v`
- **Dependências:** Fase 12, Fase 13, Fase 14.
- **Arquivos impactados:** `tests/test_features_and_models.py`.
- **Escopo estimado:** M (1 arquivo).

### Tarefa 15.2: Orquestrador Integrado do Stage 04 (`src/models/run_stage04.py`) e Rastreabilidade (`manifest.json`)
- **Descrição:** Criar entrypoint CLI unificado que executa sequencialmente o pipeline completo do Stage 04 (`latency_builder` $\to$ `benchmark_runner` $\to$ `xai_shap`), atualizando hashes criptográficos no `manifest.json`.
- **Critérios de Aceite:**
  - [x] Criar entrypoint CLI `src/models/run_stage04.py`.
  - [x] Registrar todos os artefatos gerados em `data/features/` no `manifest.json` via `LineageTracker`.
  - [x] Emitir sumário executivo no console com tabela comparativa de modelos e limiares SHAP.
- **Verificação:** `uv run python -m src.models.run_stage04`
- **Dependências:** 15.1.
- **Arquivos impactados:** `src/models/run_stage04.py`.
- **Escopo estimado:** S (1 arquivo).

### Tarefa 15.3: Auditoria Tripla de Paradigma, Atualização do AST Graphify e Deploy Git
- **Descrição:** Conduzir o protocolo mandatório de auditoria (Ciência, Engenharia e Segurança), regenerar o grafo de conhecimento AST do repositório, criar commit atômico convencional e enviar ao GitHub remoto.
- **Critérios de Aceite:**
  - [x] **Ciência:** Verificação do checklist epidemiológico (lags biológicos, assimetria temporal, dead-zone, $\text{VIF} < 5$, limiares $\text{SHAP} = 0$).
  - [x] **Engenharia:** Checagens estáticas limpas com `uv run ruff check src tests` (0 erros) e `uv run mypy src tests` (0 erros).
  - [x] **AST Graph:** Atualização via `uvx --from graphifyy graphify update .` (0 ciclos).
  - [x] **Segurança:** 0 arquivos Parquet ou segredos rastreados no Git.
  - [x] **Deploy:** Commit convencional (`feat(stage04): biological latency distributed lags, multi-paradigm benchmark and TreeSHAP thresholds`) e push para `origin/main`.
- **Verificação:** `git log -n 1 --stat && git status`
- **Dependências:** 15.2.
- **Arquivos impactados:** Todo o repositório.
- **Escopo estimado:** S.

### Checkpoint de Paradigma 15
- [x] Stage 04 completamente orquestrado, testado e publicado.
- [x] Modelos de fundação, deep learning e GBDT ranqueados para embasar o Stage 05 (Inferência Causal Semiparamétrica DoubleML/DoWhy e Simulador Contrafactual).
