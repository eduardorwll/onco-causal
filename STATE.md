# STATE.md — Registro de Estado e Handover do Projeto `onco-causal`

> **Data do Registro:** 30 de Outubro de 2026  
> **Branch Atual:** `main`  
> **Último Commit:** `6f6df17` (`feat(stage02): multivariable BQ ingestion, internal controls and age standardization`)  
> **Tag de Pré-Registro:** [`v0.1.0-preregistration`](https://github.com/eduardorwll/onco-causal/releases/tag/v0.1.0-preregistration)  
> **Repositório Remoto:** `git@github.com:eduardorwll/onco-causal.git`  
> **Ambiente Virtual:** Python 3.14 via `uv` (`.venv/`)  
> **GCP Project ID Real:** `ai4good-513217` (resolvido deterministicamente via ADC, com trava de faturamento `max_bytes_billed = 1 GB`)

---

## 1. Visão Geral do Progresso

O projeto `onco-causal` tem como objetivo isolar o efeito causal de exposições ambientais e ocupacionais ($D_1$ agrotóxicos, $D_2$ água, $D_3$ ar, $D_4$ ocupação formal) sobre a morbimortalidade por câncer nos municípios brasileiros, controlando o viés de detecção ($Z$) e a latência biológica via inferência causal semiparamétrica (DoubleML/DoWhy) e modelos tabulares fundacionais (TabFM).

### Matriz de Status por Estágio:
- [x] **Stage 00: Arquitetura & Governança Declarativa** (Settings Pydantic, Engine BigQuery com Dry-Run, DataContracts com expurgo de sentinelas, Manifesto de Linhagem SHA-256).
- [x] **Stage 01: Malha Municipal e Amostragem Estratificada** (5.570 municípios na malha nacional e recorte analítico de 685 municípios).
- [x] **Fase 5: Hardening de Paradigma & Pré-Registro** (Tags de hipóteses congeladas, markers de pytest, separação de testes unitários herméticos).
- [x] **Stage 02A: Ingestão de Exposição e Controles + Estrato 4** (RAIS/LINACH, PAM/IBGE, CNES/SNIS, materialização dos 38 municípios de controle interno).
- [x] **Stage 02B: Ingestão SIM e Padronização Etária Direta/Indireta** (ASR OMS Mundial 100k e SMR nacional para os 5 alvos oncológicos na malha de 5.570).
- [ ] **Stage 03: Geoespacial & Suavização Bayesiana Empírica** (Geometrias IBGE, Ottobacias ANA, Suavização Linear $k=31$ no PySAL e Partição Espacial 5-Fold Nested SBCV).
- [ ] **Stage 04: Alinhamento de Latência Biológica & Feature Store** (Construção dos lags temporais $t-2..5$ e $t-10..25$ em `data/features/`).
- [ ] **Stage 05: Modelagem Preditiva & Benchmark** (TabFM In-Context Learning, TabNet, GBDT + TreeSHAP).
- [ ] **Stage 06: Inferência Causal & Simulador Contrafactual** (DoubleML, DoWhy refutations, Simulador de vidas salvas e IDV).

---

## 2. Inventário de Artefatos em Staging (`data/staging/`)

Todos os artefatos foram validados por seus respectivos [`DataContract`](file:///home/eduardorwll/Sandbox/src/onco-causal/src/core/contracts.py), compactados em Parquet com `zstd`, bloqueados do versionamento Git via `.gitignore` e catalogados deterministicamente em [`data/staging/manifest.json`](file:///home/eduardorwll/Sandbox/src/onco-causal/data/staging/manifest.json):

| Artefato Parquet | Linhas | Colunas | Escopo Temporal | Chave Primária (PK) | Descrição do Conteúdo |
| :--- | :---: | :---: | :---: | :--- | :--- |
| `diretorio_municipios_full.parquet` | 5.570 | 8 | 2022 | `id_municipio` | Malha completa nacional IBGE sem o município espúrio 5101837. |
| `municipios_recorte_tabfm.parquet` | 685 | 9 | 2022 | `id_municipio` | Recorte analítico: 27 Capitais, 13 Polos, 607 >50k hab, 38 Controles Internos. |
| `rais_linach_anual.parquet` | 11.140 | 5 | 2021–2022 | `id_municipio`, `ano` | Vínculos formais totais, vínculos LINACH (Portaria 9/2014) e proporção exposta. |
| `pam_lavouras_anual.parquet` | 16.689 | 9 | 2020–2022 | `id_municipio`, `ano` | Hectares plantados de soja, milho, algodão, cana, arroz, citros e área crítica Pignati. |
| `controles_assistenciais_snis.parquet` | 5.570 | 9 | 2020 | `id_municipio`, `ano` | UNACON/CACON, leitos, tomógrafos, mamógrafos e índices de água/esgoto SNIS. |
| `sim_taxas_padronizadas_5570.parquet` | 83.550 | 8 | 2020–2022 | `id_municipio`, `ano`, `target_cancer` | Óbitos totais, população total, $\text{ASR}$ OMS por 100k hab. e razão $\text{SMR}$. |

---

## 3. Estado Teórico e Evidências Empíricas Consolidadas

1. **Problema dos Pequenos Números na Mortalidade por Câncer:**
   - Evidência empírica obtida na auditoria do SIM (2020, Neoplasias Respiratórias):
     - Municípios $< 10\text{k}$ hab.: $49,5\%$ de taxas brutas iguais a zero, desvio padrão $\sigma = 14,59$ (maior que a média $10,97$) e pico espúrio de $\text{ASR} = 160,07$.
     - Municípios $> 100\text{k}$ hab.: apenas $0,3\%$ de zeros e variância controlada ($\sigma = 4,29$ em torno da média $11,96$).
   - **Implicação Arquitetural Mandatória:** A suavização Bayesiana linear ($k=31$ vizinhos) deve operar sobre a **malha nacional completa de 5.570 municípios** para fornecer estabilidade estatística às estimativas locais antes da filtragem para os 685 municípios do recorte.

2. **Materialização do Estrato 4 (`4_Controle_Interno`):**
   - Identificados 38 municípios de porte populacional estável ($\ge 50\text{k}$ hab.) com baixíssima carga química ambiental ($Q_{25}$ área agroquímica $\le 0,0014\text{ ha/hab}$) e ocupacional ($Q_{25}$ proporção LINACH $\le 4,9\%$).
   - Validação por teste não paramétrico de Mann-Whitney U demonstrando diferença altamente significativa ($p < 0,001$) em relação ao restante do recorte analítico.

3. **Governança de Custos e Infraestrutura BigQuery:**
   - Dry-Run obrigatório implementado em [`src/core/bq_engine.py`](file:///home/eduardorwll/Sandbox/src/onco-causal/src/core/bq_engine.py).
   - Consultas segmentadas por ano com varredura entre $130\text{ MB}$ e $380\text{ MB}$, operando muito abaixo da trava de segurança de $1.024\text{ MB}$ ($1\text{ GB}$).

---

## 4. Estado da Engenharia e Métricas de Qualidade

- **Suíte de Testes Automatizados:** 32 testes passando integralmente (`uv run pytest -v` em 0,49s).
  - Testes com marcador `@pytest.mark.unit`: executam em memória com fixtures sintéticas sem tocar em disco ou rede.
  - Testes com marcador `@pytest.mark.data_contract`: atestam integridade estrita das PKs, tipos, faixas e expurgo de sentinelas nos Parquets de `data/staging/`.
- **Análise Estática de Código:**
  - `uv run ruff check src tests`: 0 violações de linting e imports organizados.
  - `uv run mypy src tests`: 0 erros de tipagem estática em 22 arquivos fonte.
- **Grafo de Conhecimento e Topologia de Módulos (`graphify`):**
  - Grafo reconstruído com 449 nós e 721 arestas.
  - **0 ciclos de importação** entre `src.core`, `src.ingest` e `src.spatial`.
- **Rastreabilidade e Segurança:**
  - Segredos bloqueados; `.env.example` sanitizado.
  - Arquivo `data/staging/manifest.json` com SHA-256 de dados, SQLs e specs versionado no Git.

---

## 5. Próximos Passos Imediatos — Roteiro para o Stage 03

Ao retomar o desenvolvimento, o foco será a construção do **Stage 03 (Geometrias Municipais, Ottobacias ANA, Suavização Bayesiana Empírica e Validação Cruzada Espacial)**:

1. **Malha Geoespacial dos 5.570 Municípios:**
   - Ingestão das geometrias municipais oficiais do IBGE (via `geobr` ou API IBGE) projetadas para sistema de área equivalente (`SIRGAS 2000 / Brazil Albers` — `EPSG:5070` ou similar).
2. **Matriz de Vizinhança Espacial $k=31$ Vizinhos:**
   - Utilização do `libpysal` para construir pesos de vizinhança espacial $k$-nearest neighbors ($k=31$) baseados nos centróides municipais da malha completa.
3. **Cálculo da Suavização Bayesiana Empírica Linear:**
   - Implementação do algoritmo *Spatial Linear Empirical Bayes* em `src/spatial/empirical_bayes.py` sobre a $\text{SMR}$ e $\text{ASR}$ calculadas no Stage 02, encolhendo o risco relativo municipal em direção à média local ponderada pela variância do denominador populacional.
4. **Vetorização de Bacias Hidrográficas (Ottobacias Nível 4/5 da ANA):**
   - Intersecção espacial entre malha municipal e ottobacias para atribuir a chave `ottobacia_id` a cada município.
5. **Divisão Espacial Disjunta (*Nested Spatial Block Cross-Validation*):**
   - Estruturação do particionamento $40\%$ *Discovery* vs $60\%$ *Confirmation* e do $5$-fold *Nested SBCV* agrupado por blocos hidrográficos disjuntos, prevenindo *spatial data leakage*.

---

## 6. Comandos de Verificação Rápida para Retomada

Para restabelecer o contexto e atestar a integridade do ambiente ao retomar:

```bash
# 1. Ativar ambiente e sincronizar dependências
cd ~/Sandbox/src/onco-causal
uv sync

# 2. Executar a suíte completa de testes
uv run pytest -v

# 3. Rodar checagens de linter e tipagem
uv run ruff check src tests
uv run mypy src tests

# 4. Inspecionar o manifesto de linhagem e status git
cat data/staging/manifest.json | jq .updated_at
git status
```
