# Engenharia Preditiva e Inferência Causal na Epidemiologia Ambiental e Oncológica (`onco-causal`)

> **Diretrizes de Implementação com Modelos de Fundação Tabulares (TabFM), Arquiteturas Interpretáveis (TabNet/GBDT+SHAP) e Econometria Espacial (Double Machine Learning)**

---

## 1. Visão Geral e Mudança de Paradigma Analítico

A transição de análises ecológicas exploratórias sobre saúde ambiental no Brasil para um sistema de inteligência epidemiológica auditável, palpável e de elevado impacto institucional (SUS, VSPEA, RENAST/CEREST e Ministério Público) exige a superação de **quatro barreiras metodológicas históricas** da ciência de dados aplicada à saúde pública:

1. **Instabilidade Estatística em Pequenos Municípios:** Municípios com pequenos denominadores populacionais ($< 10.000$ hab.) sofrem flutuações severas nas taxas por 100.000 habitantes com a variação de um único óbito.
2. **O Paradoxo da Subnotificação e Acesso à Saúde (Viés de Detecção):** Cidades mais ricas e com melhor infraestrutura hospitalar (UNACON/CACON) diagnosticam e notificam mais casos de câncer do que municípios vulneráveis, gerando correlações espúrias onde "saneamento ou renda parecem causar câncer" se não houver controle pelo local de residência e pela oferta assistencial.
3. **Vazamento de Dados por Dependência Espacial (Spatial Data Leakage):** Municípios contíguos partilham bacias hidrográficas, lençóis freáticos, regimes de ventos e matrizes produtivas. Validações cruzadas aleatórias (*random k-fold*) inflam artificialmente métricas preditivas por simples interpolação geográfica de vizinhos.
4. **Confusão entre Correlação Preditiva e Atribuição Causal (Endogeneidade e Latência):** Cruzar poluição contemporânea com incidência oncológica do mesmo ano viola a biologia tumoral. Além disso, modelos puramente preditivos não isolam o efeito líquido de carcinógenos frente a fatores de confusão demográficos (envelhecimento populacional) e socioeconômicos.

Este projeto implementa uma **Arquitetura Orientada a Contratos e Metadados (Declarative Contract-Driven Pipeline)** estruturada em quatro estágios sequenciais para isolar o efeito causal de múltiplos vetores ambientais e ocupacionais sobre a morbimortalidade oncológica no Brasil.

---

## 2. Objetivos do Projeto

### 2.1. Objetivo Geral
Construir uma plataforma reproduzível de engenharia de dados geoespaciais, predição zero-shot/supervisionada e inferência causal semiparamétrica capaz de quantificar o impacto líquido de exposições agroquímicas, hídricas, atmosféricas e ocupacionais sobre taxas padronizadas de câncer nos municípios brasileiros, gerando insumos acionáveis para vigilância ativa e intervenção regulatória.

### 2.2. Objetivos Específicos e Entregáveis Tangíveis
1. **Matriz Espaço-Temporal Harmonizada e Defasada:** Consolidar uma base nacional (indexada por `id_municipio` IBGE de 7 dígitos) integrando mortalidade/incidência por residência (SIM/PAINEL-Oncologia), uso do solo e agrotóxicos (PAM/IBGE, IBAMA, MapBiomas), qualidade da água (SISAGUA), poluição atmosférica e radiação (SISAM/INPE, SEEG, LABREN) e estrutura ocupacional/industrial (RAIS/CNAE 2.0, ANEEL), respeitando janelas biológicas estritas de latência oncológica.
2. **Benchmark Preditivo Multi-Paradigma:** Avaliar comparativamente três famílias de algoritmos sobre blocos espaciais disjuntos:
   * **Paradigma Foundation In-Context:** Google Research **TabFM** (400M parâmetros, `TabFM+` e `TabFM-Auto`) e **TabPFN v2**.
   * **Paradigma Deep Learning com Atenção Sequencial:** Google **TabNet** para geração de máscaras de importância por instância/município.
   * **Paradigma GBDT + XAI:** **XGBoost, LightGBM e CatBoost** acoplados a **SHAP** (*SHapley Additive exPlanations*) para curvas não-lineares de dose-resposta.
3. **Isolamento do Efeito Causal (Double/Debiased Machine Learning):** Estimar o Efeito Médio do Tratamento ($\text{ATE}$) e o Efeito Condicional ($\text{CATE}$) via regressão parcialmente linear ortogonalizada (`DoubleML` e `EconML`) e validação por testes de refutação (`DoWhy`).
4. **Produtos Institucionais Acionáveis:**
   * **Simulador Contrafactual Causal (ICE/DML):** Quantificação de óbitos evitáveis sob cenários de redução de 1 IQR em poluentes, imposição de zonas de amortecimento (*buffer zones* de 300m) e adequação aos limites da Portaria GM/MS nº 888/2021.
   * **Índice de Divergência de Vigilância (IDV):** Ranking automatizado de *Silent Hotspots* (municípios com altíssima assinatura de risco ambiental/ocupacional, mas notificação nula ou residual no SINAN) para auditoria do CEREST e Ministério Público do Trabalho (MPT).
   * **Protocolo Técnico-Jurídico e Clínico:** Subsídio quantitativo para Nexo Técnico Epidemiológico Previdenciário (Grupo II de Schilling / auxílio B91) e antecipação da idade de rastreamento oncológico no SUS em zonas de sacrifício ambiental.

---

## 3. Desenho Epidemiológico e Controle de Vieses

### 3.1. Estratificação Topográfica do Desfecho ($Y$) e Janelas de Latência
"Câncer" não é modelado como entidade única. O pipeline separa obrigatoriamente os desfechos pelo local de **Residência** do paciente e aplica janelas históricas de exposição ($X$ medido em $t - \text{lag}$) pareadas com o desfecho recente ($Y$ medido em 2020–2025):

| Subgrupo Oncológico (Target $Y$) | Códigos CID-10 | Vetores Etiológicos Primários ($D$) | Janela de Latência Biológica (Lag de $X$) |
| :--- | :--- | :--- | :--- |
| **1. Neoplasias Hematológicas e Infantojuvenis** | `C81–C96` (e faixa 0–19 anos) | Benzeno/solventes (CNAE combustíveis/química), agrotóxicos organofosforados e herbicidas, deriva aérea (90–300m). | **Curta Latência:** Exposição acumulada/média móvel de **$t - 2$ a $t - 5$ anos** (extensível a 10 anos). |
| **2. Trato Respiratório e Intratorácico** | `C34` (Pulmão e Brônquios) | Material particulado fino ($\text{PM}_{2.5}$, $\text{PM}_{10}$), queima de diesel/biomassa, termelétricas a carvão/óleo, sílica, asbesto/amianto e metais pesados. | **Longa Latência:** Exposição histórica acumulada de **$t - 10$ a $t - 25$ anos**. |
| **3. Trato Digestivo e Órgãos Anexos** | `C15–C26` (Esôfago, Estômago, Cólon/Reto, Fígado, Pâncreas) | Contaminantes químicos na água (SISAGUA: trihalometanos [THM-anos], agrotóxicos, arsênio, chumbo), deriva agrícola em monoculturas. | **Longa Latência:** Exposição histórica acumulada de **$t - 10$ a $t - 20$ anos**. |
| **4. Pele e Melanoma** | `C43–C44` | Irradiação solar global e Índice UV extremo (LABREN/INPE) combinados ao trabalho rural a céu aberto e exposição a arsênio/agrotóxicos. | **Longa Latência:** Exposição histórica acumulada de **$t - 10$ a $t - 20$ anos**. |
| **5. Tumores Hormoniodependentes e Urogenitais** | `C50` (Mama), `C53` (Colo do Útero), `C61` (Próstata), `C67` (Bexiga), `C73` (Tireoide) | Agrotóxicos Disruptores Endócrinos (quartis de intensidade), aminas aromáticas, poluição atmosférica urbana ($\text{PM}_{2.5}$). | **Longa Latência:** Exposição histórica acumulada de **$t - 10$ a $t - 25$ anos**. |

### 3.2. Padronização Demográfica e Suavização Espacial Bayesiana
1. **Padronização Etária Direta e Indireta (SMR):** Para neutralizar o fator de confusão do envelhecimento demográfico, as contagens de óbitos/casos são convertidas em **Taxas de Mortalidade/Incidência Padronizadas por Idade** (por 100.000 habitantes) utilizando a pirâmide etária municipal do Censo/IBGE.
2. **Suavização Bayesiana Empírica Espacial Linear (`Spatial Empirical Bayes` - PySAL):** Calculada sobre a malha nacional completa (5.570 municípios) utilizando matriz de vizinhança constante de **$k = 31$ vizinhos mais próximos** (ou largura de banda adaptativa de no mínimo $10.000$ habitantes). Isso reduz o RMSE das estimativas em pequenas áreas de $0,640$ para $0,498$ (equivalente ao modelo hierárquico completo de Besag-York-Mollié via MCMC, a uma fração do custo computacional).

### 3.3. Estratégia de Amostragem Estratificada (Recorte TabFM)
Após o cálculo das variáveis espaciais na malha de 5.570 municípios, o dataset de treinamento/inferência em contexto pode ser operado no recorte estratégico de alta estabilidade estatística (cerca de 700 a 1.500 municípios), composto por:
* **Cluster 1 (`1_Capital`):** Todas as 27 capitais estaduais e núcleos metropolitanos.
* **Cluster 2 (`2_Polo_Estrategico`):** Municípios de referência crítica em exposição agroquímica intensiva (ex.: Sapezal-MT, Campo Novo do Parecis-MT, Campos de Júlio-MT, Sorriso-MT, Lucas do Rio Verde-MT, Barreiras-BA) e polos petroquímicos/siderúrgicos/mineração (ex.: Cubatão-SP, Camaçari-BA, Triunfo-RS, Volta Redonda-RJ, Paulínia-SP, Ipatinga-MG), independentemente do porte populacional.
* **Cluster 3 (`3_Acima_50k`):** Todos os municípios brasileiros com população estimada $\ge 50.000$ habitantes (incluindo controles urbanos de baixa atividade industrial/monocultura).

---

## 4. Arquitetura de Dados e Fontes Oficiais

A chave primária universal do projeto é a tupla `("id_municipio", "ano")`, onde `id_municipio` segue o padrão IBGE de **7 dígitos** (`STRING`). Códigos DATASUS de 6 dígitos são convertidos deterministicamente na camada de staging.

### 4.1. Ingestão via Google Cloud BigQuery (`basedosdados`)
* **Diretórios e População:** `basedosdados.br_bd_diretorios_brasil.municipio`, `basedosdados.br_ibge_populacao.municipio` e `basedosdados.br_ibge_censo_2022`.
* **Mortalidade Oncológica (SIM):** `basedosdados.br_ms_sim.municipio_causa` e microdados filtrados por residência e capítulos CID-10 `C00–C97` (1996–2024).
* **Produção Agrícola Municipal (PAM/IBGE):** `basedosdados.br_ibge_pam.municipio_lavouras_temporarias` e `permanentes` (hectares plantados de soja, milho, algodão, cana-de-açúcar, arroz e citros).
* **Exposição Ocupacional e Industrial (RAIS):** `basedosdados.br_me_rais.microdados_vinculos` agregada por CNAE 2.0 e CBO, cruzada com a **LINACH** (Portaria Interministerial nº 9/2014 — agentes Grupo 1 da IARC: benzeno, asbesto, sílica, agrotóxicos, emissões diesel, metais pesados) e **Grupos de Schilling (I, II e III)**.
* **Controles Assistenciais e Saneamento (Viés de Detecção):** `basedosdados.br_ms_cnes.estabelecimento` (presença de UNACON/CACON, leitos e equipamentos diagnósticos por 100k hab.) e `basedosdados.br_mdr_snis` (cobertura de água tratada e coleta/tratamento de esgoto).

### 4.2. Ingestão Ambiental, Hídrica e Energética (APIs e Scrapers Especializados)
* **PCDaS / Fiocruz:** Plataforma de Ciência de Dados Aplicada à Saúde para validação cruzada dos microdados enriquecidos do SIM, SIHSUS e índice Pólis.
* **SISAGUA (Portal de Dados Abertos / MS):** Monitoramento de Controle Semestral da água para consumo humano (Portaria GM/MS nº 888/2021), extraindo concentrações e violações do Valor Máximo Permitido (VMP) para 27 agrotóxicos (glifosato, atrazina, 2,4-D, etc.), metais pesados (arsênio, chumbo, cádmio) e subprodutos da desinfecção (Trihalometanos Totais — THM).
* **IBAMA (Relatórios de Comercialização de Agrotóxicos):** Toneladas de ingredientes ativos comercializados por UF, acoplados aos hectares da PAM/IBGE para estimativa municipal de consumo agroquímico (litros/ha) via **Método de Pignati et al.**
* **SISAM / INPE & CAMS (Copernicus):** Séries históricas reanalisadas por município de $\text{PM}_{2.5}$, $\text{PM}_{10}$, $\text{NO}_2$, $\text{SO}_2$, $\text{CO}$, $\text{O}_3$, focos de queimadas e variáveis meteorológicas.
* **LABREN / INPE (Atlas Brasileiro de Energia Solar):** Irradiação solar global e Índice UV por coordenada/município.
* **MapBiomas Brasil & SEEG Municípios:** Séries históricas (desde 1985) de conversão de uso da terra, distância/buffer urbano-lavoura (faixa crítica de 90 a 300 metros) e emissões históricas de gases de efeito estufa por setor (Processos Industriais, Energia, Agropecuária, Resíduos).
* **SIGEL / ANEEL:** Georreferenciamento, potência outorgada e combustível de usinas geradoras (isolando termelétricas a carvão mineral, óleo combustível e diesel).
* **SINAN (DATASUS / PySUS):** Notificações de Intoxicações Exógenas por agrotóxicos e Câncer Relacionado ao Trabalho para modelagem da subnotificação (IDV).
* **ANA / SNIRH:** Shapefiles oficiais de Ottobacias hidrográficas para construção dos blocos espaciais disjuntos.

---

## 5. Metodologia de Modelagem, Validação Espacial e Inferência Causal

### 5.1. Validação Cruzada Aninhada em Blocos Espaciais (Nested SBCV)
* **Projeção e Blocagem:** Todos os vetores e malhas são projetados em sistema de coordenadas de área equivalente (`SIRGAS 2000 / Brazil Polyconic` ou `EPSG:5070`) e agrupados em blocos espaciais disjuntos definidos por sub-bacias hidrográficas (Ottobacias ANA) ou mesorregiões agropecuárias (`spatial-kfold`).
* **Partição Descoberta vs. Confirmação:** 40% dos blocos espaciais são alocados para a fase de *Discovery* (triagem de colinearidade exigindo $\text{VIF} < 5$ e $|\rho_{\text{Spearman}}| < 0,70$, evolução de pipelines `TabFM-Auto` e estabilidade por bootstrap espacial) e 60% retidos para *Confirmation* (OLS, WLS, GWR e **MGWR** — Regressão Geograficamente Ponderada Multiescala via AICc para medir a largura de banda espacial de cada poluente).
* **Avaliação Preditiva:** 5-fold Nested Spatial Block Cross-Validation garantindo que nenhum município de teste tenha vizinhos imediatos no conjunto de suporte/treino.

### 5.2. Motor Preditivo e Explicabilidade (Benchmark Híbrido)
1. **Google Research TabFM (`google-research/tabfm`):**
   * Arquitetura Transformer In-Context de 400M parâmetros com *Learned Fourier Cell Embeddings*, atenção alternada entre colunas (ISAB) e linhas (SAB) e janela de contexto de até 16.384 instâncias.
   * Mitigação de **Cegueira Semântica**: conversão estrita de códigos sentinela do SUS (`0`, `9`, `99`, `999` $\rightarrow$ `NaN`), expansão multi-visão de 32 projeções com SVD e NNLS (`TabFM+`) e engenharia de atributos assistida por LLM em validação cruzada isolada (`TabFM-Auto`).
   * **Conformidade de Licenciamento:** Pesos locais do Hugging Face (`tabfm-non-commercial-v1.0`) são restritos à pesquisa acadêmica e experimentação local. Para cargas de trabalho em produção institucional, a inferência é delegada nativamente ao **Google Cloud BigQuery (`AI.PREDICT` / `AI.EVALUATE`)** sob os Termos Comerciais do GCP.
2. **TabNet & GBDT (XGBoost / LightGBM / CatBoost) + SHAP:**
   * Extração de máscaras de atenção locais (TabNet) e cálculo exato de valores `SHAP` (Summary Plots, Dependence Plots e identificação do limiar de transição $\text{SHAP} = 0$) conjuntamente com curvas **ICE** (*Individual Conditional Expectation*) e **PDP** (*Partial Dependence Plots*) extraídas por perturbação contrafactual no forward pass do TabFM.

### 5.3. Inferência Causal Semiparamétrica (Double/Debiased Machine Learning)
Para isolar o efeito causal $\theta$ da exposição ambiental contínua $D$ sobre a mortalidade padronizada $Y$ na presença de confundidores de alta dimensão $Z$ (demografia, renda, saneamento SNIS e acesso oncológico CNES/UNACON), adota-se o modelo **PLR (*Partially Linear Regression*)** via `DoubleML` e `EconML`:

$$Y = \theta D + g(Z) + U, \quad \mathbb{E}[U \mid D, Z] = 0$$
$$D = m(Z) + V, \quad \mathbb{E}[V \mid Z] = 0$$

1. **Ortogonalização de Neyman com Cross-Fitting Espacial:** As funções *nuisance* $\hat{g}(Z) = \mathbb{E}[Y \mid Z]$ e $\hat{m}(Z) = \mathbb{E}[D \mid Z]$ são estimadas fora da amostra (*out-of-sample*) respeitando os clusters espaciais. O efeito causal $\hat{\theta}$ é obtido regredindo os resíduos $\tilde{Y} = Y - \hat{g}(Z)$ contra $\tilde{D} = D - \hat{m}(Z)$.
2. **Heterogeneidade do Efeito (CATE) e Padronização por IQR:** Estimação de *Causal Forests* (`EconML`) para identificar modificadores de efeito ($\theta(X)$, ex.: como a falta de saneamento ou ausência de UNACON amplifica a letalidade carcinogênica). Para comparar poluentes em diferentes escalas físicas ($\text{litros/ha}$ vs. $\mu\text{g/m}^3$), o $\text{ATE}$ é normalizado pela linha de base regional e multiplicado pelo Intervalo Interquartil ($\text{IQR}$) da exposição.
3. **Índice de Toxicidade Ambiental (ATI) e Testes de Refutação (`DoWhy`):** Compressão multidimensional de contaminantes via Autoencoder auditado por PFI e estratificado em 5 níveis de risco via K-Means. Todas as estimativas causais devem passar nos três testes de refutação do `DoWhy` (*Placebo Treatment*, *Random Common Cause* e *Data Subset Validation*, exigindo $p > 0,05$).

---

## 6. Padrões de Engenharia de Software do Repositório (Regras para Desenvolvedores e Agentes IA)

Todo código adicionado a este repositório deve obedecer estritamente aos quatro pilares abaixo:

1. **Config-as-Code (`configs/domain_spec.yaml` + `src/core/settings.py`):** É proibido declarar listas de códigos IBGE, prefixos CID-10, códigos CNAE, janelas de *lag* ou limites de faturamento hardcoded dentro de scripts Python. Toda constante epidemiológica ou operacional deve ser lida do YAML e validada via modelos `Pydantic`.
2. **SQL Desacoplado e Seguro (`sql/*.sql` + `src/core/bq_engine.py`):** Nenhuma query SQL deve ser escrita como string embutida em código Python. Queries residem em `sql/`, utilizam parâmetros nativos do BigQuery (`@param_name` / `UNNEST`) e são executadas exclusivamente através do `BigQueryEngine`, que impõe validação prévia via **Dry-Run**, trava de segurança (`maximum_bytes_billed`) e leitura colunar via **Arrow / BigQuery Storage Read API**.
3. **Contratos de Dados Imutáveis (`src/core/contracts.py`):** Todo extrator (BigQuery, API REST ou Scraper) deve passar seu DataFrame pelo método `.enforce()` de um `DataContract` antes de salvar em disco, garantindo tipagem estrita em `Polars`, conversão de valores sentinela (`99`, `999` $\rightarrow$ `null`) e integridade de chaves primárias sem duplicatas.
4. **Arquitetura Medallion em Parquet Zstd:**
   * `data/raw/`: Arquivos brutos imutáveis baixados de fontes externas.
   * `data/staging/`: Tabelas limpas, tipadas por contrato e normalizadas para `id_municipio` (7 dígitos).
   * `data/features/`: Matrizes analíticas prontas para modelagem, contendo taxas suavizadas (Spatial EB), padronização etária, blocos de Ottobacias e janelas temporais defasadas (*lags*).
