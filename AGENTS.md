# AGENTS.md — Constituição Operacional e Diretrizes Mandatórias para Agentes Autônomos

> **Escopo de Execução:** `~/Sandbox/src/onco-causal`  
> **Nível de Conformidade:** ESTRITO / MANDATÓRIO (Zero desvios arquiteturais permitidos)

Você está operando dentro do repositório `onco-causal`, inserido no ecossistema `~/Sandbox`. Antes de planejar, editar código, rodar queries ou executar experimentos científicos, você **DEVE** carregar o contexto documental base e acionar as *skills* locais do Sandbox conforme determinado neste documento.

---

## 1. Leitura de Contexto e Uso Mandatório de Skills do Sandbox (`~/Sandbox`)

Nenhuma tarefa de engenharia de dados, modelagem ou inferência causal pode ser iniciada às cegas. O seu fluxo de inicialização em qualquer sessão exige:

### 1.1. Leitura da Tríade Documental
1. **`PROJECT_SPEC.md`:** Especificação técnica da arquitetura de dados, fontes oficiais e stack tecnológico.
2. **`OBJETIVO.md`:** Fundamentação conceitual, problema epidemiológico (viés de detecção, latência biológica) e produtos acionáveis (Simulador Contrafactual e IDV).
3. **`METODOLOGIA.md`:** Formulação matemática exata (Padronização Etária, *Spatial Linear Empirical Bayes* $k=31$, *Nested Spatial Block CV*, `TabFM`, `TabNet`, `GBDT+SHAP` e `DoubleML` / `DoWhy`).

### 1.2. Invocação Obrigatória de Skills (`graft`, `graphify` e Skills Científicas)
O ambiente `~/Sandbox` provê *skills* especializadas que **DEVEM** ser utilizadas de forma mandatória sempre que a tarefa tocar seus respectivos domínios:

* **`graphify` (Mapeamento Estrutural, Linhagem e DAGs Causais — MANDATÓRIO):**
  * **Quando usar:** Antes de refatorar módulos interdependentes, ao desenhar o fluxo de dados da arquitetura Medallion (`raw -> staging -> features`) e, obrigatoriamente, na construção e validação dos **Grafos Acíclicos Direcionados (DAGs)** epidemiológicos para o `DoWhy` / `DoubleML`.
  * **Ação exigida:** Invoque o `graphify` para explicitar grafos de dependência de código e grafos causais (identificando caminhos *backdoor*, colisores e mediadores entre exposições $D_1\dots D_4$, confundidores $Z$ e desfecho $Y$). Nunca assuma uma topologia causal ou de pipeline sem antes representá-la e verificá-la via `graphify`.
* **`graft` (Integração Cirúrgica, Composição de Pipelines e Patching Estruturado — MANDATÓRIO):**
  * **Quando usar:** Ao acoplar novos extratores, enxertar transformações de atributos (como os pipelines evolutivos do `TabFM-Auto`), integrar sub-grafos de dados externos (SISAGUA, IBAMA, SISAM/INPE) à espinha dorsal do BigQuery ou realizar modificações transversais entre `configs/domain_spec.yaml`, `sql/` e `src/`.
  * **Ação exigida:** Utilize a skill `graft` para garantir que modificações e enxertos de código/dados preservem a integridade das interfaces, contratos e árvores de dependência sem quebrar estágios a jusante (*downstream*).
* **Skills Especializadas em Ciência e Pesquisa do Sandbox (MANDATÓRIO):**
  * Sempre que implementar rotinas estatísticas, econométricas, geoespaciais ou de *Machine Learning* (suavização Bayesiana no `PySAL`, testes de hipóteses, cálculo de $\text{VIF}$, estimação `MGWR`, *Cross-Fitting* no `DoubleML` ou testes de refutação no `DoWhy`), acione as **skills científicas** disponíveis no ambiente `~/Sandbox` para validar o rigor matemático, checar premissas de distribuição, evitar *p-hacking* e garantir reprodutibilidade determinística (seeds fixas, intervalos de confiança válidos e controle de vazamento de dados).

---

## 2. Os Quatro Pilares de Engenharia de Software (Proibições e Deveres)

Todo código escrito ou modificado em `~/Sandbox/src/onco-causal` deve obedecer sem exceções ao paradigma **Declarative Contract-Driven Pipeline**:

### Pilar I: Proibição Absoluta de Hardcoding (`Config-as-Code`)
* **PROIBIDO:** Declarar códigos IBGE de municípios, listas de polos estratégicos, prefixos da CID-10, códigos CNAE 2.0, janelas de *lag* temporal, limites populacionais ($50.000$ hab.) ou tetos de faturamento do BigQuery diretamente dentro de arquivos `.py`.
* **OBRIGATÓRIO:** Todo parâmetro de domínio ou de infraestrutura deve residir em `configs/domain_spec.yaml` e ser consumido exclusivamente através dos objetos validados pelo `Pydantic` em `src/core/settings.py` (`DomainSpec` e `EnvSettings`).

### Pilar II: SQL Desacoplado e Governança de Custos no BigQuery
* **PROIBIDO:** Escrever queries SQL embutidas em strings Python (`f"""SELECT ..."""`), concatenar variáveis via interpolação de strings no SQL ou instanciar `bigquery.Client()` diretamente nos scripts de ingestão.
* **OBRIGATÓRIO:**
  1. Toda query SQL reside em um arquivo dedicado dentro de `sql/*.sql` utilizando parâmetros nativos (`@param` e `UNNEST(@array_param)`).
  2. Toda execução no BigQuery passa obrigatoriamente por `src/core/bq_engine.py` (`BigQueryEngine.query_from_file()`), que resolve o `project_id` real via Google Auth ADC (nunca confiando no alias de exibição `"ai4good"`), executa um **Dry-Run obrigatório** registrando o consumo em MB no log, aplica a trava `maximum_bytes_billed` e transfere os dados via **BigQuery Storage Read API (Apache Arrow $\to$ Polars)**.
  3. **Particionamento Anual Preventivo:** Tabelas públicas massivas (ex.: `br_ms_cnes`) devem ser consultadas ano a ano em laços determinísticos quando a estimativa de múltiplos anos combinados exceder $500\text{ MB}$, garantindo operação estrita dentro do teto seguro de $1.073.741.824$ bytes ($1\text{ GB}$).

### Pilar III: Contratos de Dados Imutáveis e Expurgo de Sentinelas (`DataContract`)
* **PROIBIDO:** Salvar qualquer `pl.DataFrame` em `data/staging/` ou `data/features/` sem antes submetê-lo a um `DataContract.enforce(df)` (`src/core/contracts.py`).
* **OBRIGATÓRIO:**
  1. **Chave Primária Universal:** No nível municipal, a chave primária é sempre `id_municipio` (`pl.String`, **7 dígitos IBGE**) combinada com `ano` (`pl.Int64`) quando aplicável. Códigos de 6 dígitos oriundos do DATASUS/SINAN devem ser convertidos deterministicamente na entrada usando o diretório oficial.
  2. **Limpeza Semântica Anti-Cegueira (Pré-TabFM):** Bancos públicos brasileiros (DATASUS, SIM, SINAN, SISAGUA) usam números mágicos como `9`, `99`, `999`, `9999`, `-1` ou `0` implausível para indicar dado ignorado/ausente. Todo `DataContract` deve mapear `sentinel_null_values` para converter esses códigos em `null` explícito antes de qualquer agregação ou envio aos *Fourier Cell Embeddings* do TabFM.
  3. **Motor de Processamento:** Utilize **`polars`** e **`duckdb`** como motores padrão de manipulação tabular em memória. O uso de `pandas` só é permitido na fronteira estrita onde bibliotecas legadas (`geopandas`, `libpysal`, `doubleml`, `econml`) exigirem conversão pontual.
  4. **Manifesto Criptográfico de Linhagem (`manifest.json`):** Toda persistência de Parquet em `data/staging/` ou `data/features/` deve acionar o `LineageTracker` (`src/core/lineage.py`), registrando deterministicamente no arquivo versionado `manifest.json` os hashes SHA-256 do arquivo gerado, do arquivo `.sql` executado e de `configs/domain_spec.yaml`, além de número de linhas, colunas, commit SHA e branch Git. O `manifest.json` é versionado obrigatoriamente no Git.

### Pilar IV: Arquitetura Medallion e Gerenciamento de Ambiente (`uv`)
* **Ambiente Python:** Nunca use `pip` ou `conda` diretamente. Toda gestão de pacotes e execução de comandos deve usar **`uv`** (`uv add <pacote>`, `uv run python -m ...`, `uv run pytest`).
* **Configuração de Pacote em Repositórios de Aplicação:** Repositórios de pipeline analítico puro sem pacote distribuível devem manter `[tool.uv] package = false` em `pyproject.toml` para assegurar o funcionamento limpo de comandos `uv run` e ferramentas estáticas.
* **Imutabilidade de Camadas em Parquet (`compression="zstd"`):**
  * `data/raw/`: Artefatos brutos baixados (CSVs do SISAGUA, planilhas IBAMA, `.dbc` do SINAN, Shapefiles ANA). Somente leitura após download.
  * `data/staging/`: Tabelas limpas, tipadas e aprovadas por `DataContract`, normalizadas para `id_municipio` (7 dígitos).
  * `data/features/`: Matrizes analíticas prontas para modelagem, contendo taxas padronizadas por idade ($\text{ASR}/\text{SMR}$), suavização espacial (`Spatial EB`), identificadores de blocos hidrográficos (`ottobacia_id`) e variáveis de exposição defasadas no tempo (*lags*).

---

## 3. Regras Invioláveis de Rigor Epidemiológico e Espacial

Qualquer agente implementando scripts em `src/spatial/`, `src/features/` ou `src/models/` incorrerá em **falha crítica de validade científica** se violar qualquer uma das cinco regras abaixo:

1. **Filtro Estrito por Residência e Controle de Viés de Detecção:**
   * Dados de morbimortalidade (SIM, SIHSUS, PAINEL-Oncologia) **DEVEM** ser filtrados pelo **Município de Residência** (nunca por local de ocorrência/internação).
   * Nenhum modelo causal ou preditivo pode ser rodado sem incluir no vetor de controle $Z$ as variáveis assistenciais do **CNES** (presença de UNACON/CACON, leitos/equipamentos diagnósticos por 100k hab.) e de saneamento do **SNIS**.
2. **Proibição de Taxas Brutas como Variável Alvo ($Y$):**
   * O alvo $Y$ nunca é a contagem absoluta de óbitos nem a taxa bruta simples. $Y$ deve ser obrigatoriamente a **Taxa Padronizada por Idade ($\text{ASR}$)** ou **Razão de Mortalidade Padronizada ($\text{SMR}$)** submetida à **Suavização Bayesiana Empírica Espacial Linear (`PySAL`, $k = 31$ vizinhos)**.
   * **Regra da Dupla Malha (Prova Empírica de Estabilidade Espacial):** Conforme comprovado na auditoria do SIM, municípios com $<10\text{k}$ habitantes possuem $49,5\%$ de taxas brutas nulas e inflação artificial de variância ($\sigma = 14,59$ vs $\sigma = 4,29$ em cidades $>100\text{k}$). A matriz de $k = 31$ vizinhos e a suavização Bayesiana ocorrem **sempre** sobre a malha nacional completa (`5.570` municípios em `diretorio_municipios_full.parquet`). O filtro para o recorte analítico (`municipios_recorte_tabfm.parquet`: $> 50\text{k}$ hab. + Capitais + Polos Estratégicos + Controles Internos) só é aplicado **após** a suavização espacial e o cálculo de *lags*.
3. **Alinhamento Biológico de Latência (Proibição de Cruzamento Contemporâneo Puro):**
   * É proibido prever ou inferir causalidade cruzando exposição ambiental do ano $t$ exclusivamente com mortalidade por câncer no mesmo ano $t$.
   * As features de exposição ($D_1, D_2, D_3, D_4$) devem respeitar as janelas definidas em `configs/domain_spec.yaml`: **$t-2$ a $t-5$ anos** para neoplasias hematológicas (`C81–C96`) e infantojuvenis ($0\text{–}19$ anos), e **$t-10$ a $t-25$ anos** para tumores sólidos (`C34`, `C15–C26`, `C43–C44`, `C50`, `C53`, `C61`).
4. **Prevenção de Vazamento Geográfico (*Spatial Data Leakage*):**
   * É proibido usar `train_test_split` aleatório ou `KFold` padrão do `scikit-learn`.
   * Toda divisão de dados (40% *Discovery* vs. 60% *Confirmation*, 5-fold *Nested SBCV* e *Cross-Fitting* do `DoubleML`) deve ser agrupada pelos blocos espaciais disjuntos de sub-bacias hidrográficas (`ottobacia_id` em projeção de área equivalente `EPSG:5070` / `SIRGAS 2000 Albers`) usando `spatial-kfold`.
   * No **TabFM**, nenhuma linha do conjunto de suporte (*in-context support set*) pode pertencer ao mesmo bloco hidrográfico das linhas de consulta (*query/test set*).
5. **Conformidade de Licenciamento do TabFM:**
   * Os pesos auto-hospedados via Hugging Face (`tabfm_v1_0_0.load()`) possuem licença `tabfm-non-commercial-v1.0` e só podem ser usados em scripts locais de pesquisa acadêmica/benchmark (`src/models/tabfm_runner.py`).
   * Pipelines destinados a deploy institucional/produção devem utilizar o módulo SQL nativo do BigQuery (`AI.PREDICT` e `AI.EVALUATE`).

---

## 4. Protocolo de Verificação Pré-Commit (Checklist do Agente)

Antes de declarar qualquer tarefa como concluída, o agente **DEVE** executar e comprovar os seguintes passos:

1. **Verificação Estrutural (`graphify` & `graft`):** O enxerto de código/dados manteve a coerência do grafo do repositório e do DAG causal?
2. **Zero Hardcoding:** Todas as constantes novas foram adicionadas em `configs/domain_spec.yaml` e tipadas em `src/core/settings.py`?
3. **Execução e Contrato:** O módulo roda limpa e deterministicamente via `uv run python -m ...` e o artefato gerado passa no `.enforce()` do seu `DataContract` sem `nulls` em chaves primárias e sem códigos sentinela residuais?
4. **Linhagem e Rastreabilidade:** O manifesto `data/staging/manifest.json` foi atualizado pelo `LineageTracker` com os novos hashes SHA-256 e incluído no commit Git, assegurando que nenhum arquivo `.parquet` ou segredo tenha sido rastreado?
5. **Testes Automatizados:** Os testes de integridade em `tests/` passam integralmente (`uv run pytest`)?
