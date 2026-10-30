# METODOLOGIA.md — Desenho Metodológico, Formulação Matemática, Hipóteses e Resultados Esperados

> **Projeto:** Engenharia Preditiva e Inferência Causal na Epidemiologia Ambiental e Oncológica (`onco-causal`)  
> **Escopo Metodológico:** Estudo ecológico espaço-temporal longitudinal retroativo e prospectivo com desenho quase-experimental, acoplando Suavização Bayesiana Empírica Espacial, Modelos de Fundação Tabulares (*In-Context Learning*), Aprendizagem Profunda Interpretável e Econometria Semiparamétrica (*Double/Debiased Machine Learning*).

---

## 1. Desenho do Estudo e População de Referência

### 1.1. Tipologia Epidemiológica e Econométrica
O estudo configura-se como uma análise ecológica longitudinal multiescala de base populacional (coorte territorial retrospectiva cobrindo o intervalo 1985–2025), estruturada sob um **desenho quase-experimental de inferência causal**. A unidade primária de agregação analítica é o município brasileiro ($N = 5.570$, indexado pelo código IBGE de 7 dígitos), avaliado em recortes transversais empilhados e janelas temporais defasadas (*distributed lag windows*), agrupados geograficamente por sub-bacias hidrográficas (Ottobacias Nível 4/5 da Agência Nacional de Águas — ANA) e mesorregiões produtivas.

### 1.2. Estratégia de Dupla Malha (Malha de Suavização vs. Recorte Analítico Estratificado)
Para resolver o conflito clássico entre **completude de vizinhança espacial** e **estabilidade de variância estatística**, a metodologia opera em dois níveis sequenciais:

1. **Nível I — Malha Nacional Integral ($N = 5.570$ municípios):** Utilizada exclusivamente na fase de geoprocessamento para cálculo de distâncias euclidianas/geodésicas em projeção de área equivalente (`EPSG:5070` / `SIRGAS 2000 Albers Equal Area`), construção da matriz de pesos espaciais dos $k = 31$ vizinhos mais próximos e aplicação da Suavização Bayesiana Empírica Espacial. Isso impede o "efeito de borda" (*edge effect*) ou buracos topológicos ao redor dos polos agrícolas e industriais.
2. **Nível II — Recorte Analítico Estratificado ($n \approx 700 \text{ a } 1.500$ municípios):** Aplicado na fase de modelagem preditiva (`TabFM`, `TabNet`, `GBDT`) e estimação causal (`DoubleML`). Seleciona municípios com estabilidade demográfica comprovada ou relevância etiológica crítica, divididos em quatro estratos:
   * **Estrato 1 (`1_Capital`):** As 27 capitais estaduais e núcleos metropolitanos primários.
   * **Estrato 2 (`2_Polo_Estrategico`):** Municípios de pequeno, médio ou grande porte caracterizados como hiperpolos do agronegócio intensivo em monoculturas (ex.: Sapezal-MT, Campo Novo do Parecis-MT, Campos de Júlio-MT, Sorriso-MT, Lucas do Rio Verde-MT, Barreiras-BA, Luís Eduardo Magalhães-BA) e polos petroquímicos, siderúrgicos ou de mineração (ex.: Cubatão-SP, Camaçari-BA, Triunfo-RS, Volta Redonda-RJ, Paulínia-SP, Ipatinga-MG).
   * **Estrato 3 (`3_Acima_50k`):** Todos os municípios brasileiros com população residente $\ge 50.000$ habitantes.
   * **Estrato 4 (`Controles Internos`):** Subconjunto de municípios de médio porte ($\ge 50.000$ hab.) com baixa densidade industrial carcinogênica (CNAE/LINACH residual) e baixa intensidade agroquímica, atuando como linha de base contrafactual.

---

## 2. Levantamento Formal de Hipóteses e Critérios de Decisão Estatística

Cada hipótese do projeto é formulada de modo a ser falsificável empiricamente por meio de métricas preditivas fora da amostra (*out-of-sample*) e testes de hipóteses econométricos:

### Hipótese 1 ($H_1$): Especificidade Topográfica e Alinhamento de Latência Biológica
* **Hipótese Nula ($H_{0,1}$):** A defasagem temporal histórica das exposições ambientais ($t - \text{lag}$) não produz ganho estatisticamente significativo no poder explicativo ($\Delta R^2_{\text{spatial}} \le 0$) nem na importância de permutação (`%IncMSE` e $|\text{SHAP}|$) em relação à exposição contemporânea ($t_0$) para os subgrupos topográficos da CID-10.
* **Hipótese Alternativa ($H_{A,1}$):** O pareamento estrito entre agente etiológico, sítio anatômico e janela biológica de latência maximiza a razão sinal-ruído:
  * **Regime de Curta Latência ($t-2$ a $t-5$ anos):** Maximiza a explicação da variância para **Neoplasias Hematológicas (`C81–C96`)** e **Infantojuvenis ($0\text{–}19$ anos)** frente à exposição a benzeno/solventes (RAIS/CNAE) e deriva de agrotóxicos.
  * **Regime de Longa Latência ($t-10$ a $t-25$ anos):** Maximiza a explicação da variância para **Tumores Sólidos**, especificamente Trato Respiratório (`C34`) frente a $\text{PM}_{2.5}$ e termelétricas; Trato Digestivo (`C15–C26`) frente a trihalometanos (THM-anos), metais pesados e agrotóxicos na água (SISAGUA); Pele/Melanoma (`C43–C44`) frente à radiação UV (LABREN/INPE); e Tumores Hormoniodependentes (`C50, C53, C61`) frente a disruptores endócrinos.
* **Critério de Validação:** Comparação de modelos pareados via teste de Diebold-Mariano nos resíduos da validação cruzada espacial e avaliação de estabilidade por bootstrap em blocos ($B = 1.000$ reamostragens).

### Hipótese 2 ($H_2$): Desempenho Zero-Shot e In-Context de Modelos de Fundação Tabulares sob Bloqueio Espacial
* **Hipótese Nula ($H_{0,2}$):** Sob Validação Cruzada Aninhada em Blocos Espaciais (5-fold Nested SBCV), o modelo de fundação tabular **TabFM** (e suas variantes `TabFM+` e `TabFM-Auto`) apresenta erro preditivo superior ($\text{RMSE}_{\text{TabFM}} \ge \text{RMSE}_{\text{GBDT}}$) aos modelos supervisionados ajustados por busca de hiperparâmetros (`XGBoost`, `LightGBM`, `CatBoost` e `TabNet`).
* **Hipótese Alternativa ($H_{A,2}$):** Graças aos *Learned Fourier Cell Embeddings* e à atenção bidimensional alternada pré-treinada em milhões de grafos causais sintéticos (SCMs), o `TabFM-Auto` supera ou iguala estatisticamente os GBDTs e o `TabNet` em regimes de generalização geográfica pura (previsão de bacias hidrográficas inteiras omitidas do contexto), reduzindo o sobreajuste espacial.
* **Critério de Validação:** Teste não-paramétrico de Friedman seguido de pós-teste de Nemenyi sobre os 5 folds espaciais externos para as métricas $\text{RMSE}$, $\text{MAE}$, $R^2$ e $\text{ROC-AUC}$ (para discretização em quartis de risco).

### Hipótese 3 ($H_3$): Persistência Causal Pós-Ortogonalização do Viés de Detecção Assistencial
* **Hipótese Nula ($H_{0,3}$):** Após controlar não-parametricamente para a infraestrutura diagnóstica hospitalar (presença de UNACON/CACON e leitos/equipamentos no CNES), renda per capita, escolaridade, cobertura de saneamento (SNIS) e estrutura etária via *Double/Debiased Machine Learning* (DML), o Efeito Médio do Tratamento ($\text{ATE}$, $\theta$) dos vetores ambientais converge para zero ($\hat{\theta} = 0, p \ge 0,05$).
* **Hipótese Alternativa ($H_{A,3}$):** O controle ortogonalizado expurga o paradoxo da subnotificação (invertendo o sinal espúrio positivo de variáveis de riqueza/infraestrutura) e revela um efeito causal líquido positivo e estatisticamente significativo ($\hat{\theta} > 0, p < 0,05$) para a intensidade agroquímica, contaminação hídrica no SISAGUA, concentração de $\text{PM}_{2.5}$ e densidade de vínculos laborais na LINACH.
* **Critério de Validação:** Intervalos de confiança assintoticamente normais de 95% baseados no escore ortogonal de Neyman com erros-padrão clusterizados por sub-bacia hidrográfica, combinados à aprovação nos três testes de refutação do `DoWhy` ($p_{\text{refutação}} > 0,05$).

### Hipótese 4 ($H_4$): Sinergia e Modificação de Efeito por Vulnerabilidade Socioassistencial
* **Hipótese Nula ($H_{0,4}$):** O impacto marginal dos carcinógenos ambientais é homogêneo entre os municípios ($\theta(X_i) = \theta, \forall i$), não dependendo da infraestrutura sanitária ou assistencial local.
* **Hipótese Alternativa ($H_{A,4}$):** A estimação de *Causal Forests* (`EconML`) demonstrará heterogeneidade significativa ($\text{Var}[\hat{\theta}(X_i)] > 0$), onde municípios situados no quartil inferior de cobertura de saneamento básico e desprovidos de rede oncológica (UNACON/CACON) exibem um Efeito Condicional do Tratamento ($\text{CATE}$) substancialmente mais letal para a mesma dose de exposição química.

---

## 3. Formulação Matemática e Parametrização das Variáveis

### 3.1. Variável Dependente ($Y$): Padronização Etária e Suavização Bayesiana Empírica
Para cada município $i \in \{1, \dots, 5570\}$, subgrupo topográfico $c$ e período alvo $T_{\text{alvo}}$ (ex.: quinquênio 2020–2024), extrai-se o número de óbitos (SIM) ou casos diagnosticados (PAINEL-Oncologia) **exclusivamente por município de residência** na faixa etária $a \in \{1, \dots, A\}$, denotado por $O_{i,c,a}$, e a respectiva população residente $P_{i,a}$.

1. **Taxa Padronizada por Idade (Método Direto — $\text{ASR}_{i,c}$):**
   Utilizando os pesos da População Padrão Mundial (OMS/Segi) $w_a$ (onde $\sum_{a=1}^A w_a = 100.000$):
   $$\text{ASR}_{i,c} = \sum_{a=1}^{A} \left( \frac{O_{i,c,a}}{P_{i,a}} \right) \cdot w_a$$

2. **Razão de Mortalidade Padronizada (Método Indireto — $\text{SMR}_{i,c}$):**
   Sendo $R_{c,a} = \frac{\sum_i O_{i,c,a}}{\sum_i P_{i,a}}$ a taxa específica nacional na faixa etária $a$, o número de óbitos esperados no município $i$ é $E_{i,c} = \sum_{a=1}^A P_{i,a} \cdot R_{c,a}$, resultando na razão bruta $r_{i,c} = \frac{O_{i,c}}{E_{i,c}}$ (ou taxa bruta $r_{i,c} = \frac{O_{i,c}}{P_i}$).

3. **Suavização Bayesiana Empírica Espacial Linear (*Spatial Linear Empirical Bayes* — PySAL):**
   Para eliminar a instabilidade de pequenos denominadores ($P_i < 10.000$ ou $E_{i,c} < 3$), define-se a vizinhança espacial $\mathcal{N}_k(i)$ composta pelos **$k = 31$ municípios mais próximos** (distância entre centroides das sedes em projeção de área equivalente). Seja $\mu_{\mathcal{N}(i)}$ a média prior local e $\sigma^2_{\mathcal{N}(i)}$ a variância prior na vizinhança $\mathcal{N}_k(i)$. A taxa suavizada $\hat{Y}_{i,c}^{\text{EB}}$ é calculada por:
   $$\hat{Y}_{i,c}^{\text{EB}} = w_i \cdot r_{i,c} + (1 - w_i) \cdot \mu_{\mathcal{N}(i)}$$
   onde o fator de encolhimento (*shrinkage weight*) $w_i \in [0, 1]$ é dado por:
   $$w_i = \frac{\sigma^2_{\mathcal{N}(i)}}{\sigma^2_{\mathcal{N}(i)} + \frac{\mu_{\mathcal{N}(i)}}{P_i}}$$
   Quando $P_i \to \infty$ (ex.: São Paulo, Rio de Janeiro), $w_i \to 1$ e a taxa observada é preservada. Quando $P_i$ é pequeno, $w_i \to 0$ e a estimativa converge para o comportamento epidemiológico da sub-bacia/microrregião, reduzindo o $\text{RMSE}$ empírico de $0,640$ para $0,498$.

### 3.2. Vetores de Exposição Ambiental e Ocupacional ($D_1, D_2, D_3, D_4$) e Janelas de Latência
Dado um ano de desfecho $t$ e uma janela biológica de latência $[L_{\min}, L_{\max}]$ específica do subgrupo oncológico $c$ (conforme Tabela de Latência: $[2, 5]$ anos para hematológicos/pediátricos e $[10, 25]$ anos para tumores sólidos), toda variável de exposição $D_{i,k}$ é agregada retrospectivamente sobre o operador de defasagem temporal:
$$\bar{D}_{i,k}^{(t - L_{\max} : t - L_{\min})} = \frac{1}{L_{\max} - L_{\min} + 1} \sum_{\tau = t - L_{\max}}^{t - L_{\min}} D_{i,k,\tau}$$

* **Vetor $D_1$ (Intensidade Agroquímica — Método de Pignati et al. e Deriva MapBiomas):**
  Para as culturas agrícolas $m \in \{\text{soja, milho, algodão, cana-de-açúcar, arroz, citros}\}$, multiplica-se a área plantada municipal $H_{i,m,\tau}$ (em hectares, extraída da PAM/IBGE) pelo coeficiente técnico médio de utilização de ingredientes ativos $\alpha_{m, \text{UF}, \tau}$ (litros/ha), calibrado pelo volume total comercializado na respectiva Unidade da Federação nos boletins anuais do IBAMA:
  $$V_{i,\tau}^{\text{agro}} = \sum_{m} H_{i,m,\tau} \cdot \alpha_{m, \text{UF}, \tau}, \quad D_{1,i,\tau} = \frac{V_{i,\tau}^{\text{agro}}}{\text{Área Territorial}_i \text{ (ou População}_i\text{)}}$$
  Complementarmente, extrai-se do MapBiomas a proporção da mancha urbana municipal situada a uma distância crítica de **90 a 300 metros** de polígonos de lavoura temporária.

* **Vetor $D_2$ (Contaminação Química Hídrica — SISAGUA / Portaria GM/MS nº 888/2021):**
  A partir dos registros do Controle Semestral do SISAGUA para o conjunto de contaminantes químicos $q \in \mathcal{Q}$ (27 agrotóxicos, arsênio, cádmio, chumbo, mercúrio e trihalometanos totais — THM), calcula-se a razão de excedência do Valor Máximo Permitido ($\text{VMP}_q$) e a exposição cumulativa em $\text{THM-anos}$:
  $$D_{2,i,\tau}^{(q)} = \frac{1}{N_{\text{amostras}, i, \tau}} \sum_{s=1}^{N_{\text{amostras}}} \mathbb{I}\left( C_{i,s,q,\tau} > \text{VMP}_q \right) \quad \text{e} \quad \bar{C}_{i,q,\tau} = \text{Média/P95}\left(\frac{C_{i,s,q,\tau}}{\text{VMP}_q}\right)$$

* **Vetor $D_3$ (Poluição Atmosférica, Termelétricas e Radiação UV — SISAM/INPE, SEEG, ANEEL, LABREN):**
  Concentração média anual e sazonal (inverno/inversão térmica) de $\text{PM}_{2.5}$ ($\mu\text{g/m}^3$), $\text{NO}_2$, $\text{SO}_2$, $\text{CO}$ e $\text{O}_3$; somatório de emissões industriais e energéticas de GEE/poluentes em toneladas (SEEG); potência fiscalizada instalada (MW) de usinas termelétricas movidas a carvão mineral, óleo combustível e óleo diesel num raio de influência municipal (SIGEL/ANEEL); e média histórica do Índice UV e irradiação global horizontal (LABREN/INPE).

* **Vetor $D_4$ (Risco Ocupacional Carcinogênico — RAIS / CNAE 2.0 / LINACH):**
  Seja $\mathcal{C}_{\text{LINACH}}$ o subconjunto de classes CNAE 2.0 e ocupações CBO associadas à manipulação ou exposição a agentes cancerígenos do Grupo 1 da IARC listados na Portaria Interministerial nº 9/2014 (benzeno e homólogos em combustíveis/petroquímica, sílica cristalina, asbesto/amianto, agrotóxicos, fumos metálicos/siderurgia e emissões de motores diesel) sob os Grupos I e II de Schilling:
  $$D_{4,i,\tau} = \frac{\sum_{c \in \mathcal{C}_{\text{LINACH}}} \text{Vínculos Ativos}_{i,c,\tau}}{\text{Total de Vínculos Formais}_{i,\tau}} \times 100$$

* **Síntese Multidimensional via Autoencoder (Índice de Toxicidade Ambiental — $\text{ATI}$):**
  Para sumarizar a carga combinada de múltiplos poluentes correlacionados ($D = [D_1, D_2, D_3, D_4] \in \mathbb{R}^p$), treina-se uma rede neural não-supervisionada do tipo *Bottleneck Autoencoder* ($f_{\text{enc}}: \mathbb{R}^p \to \mathbb{R}^1$ e $f_{\text{dec}}: \mathbb{R}^1 \to \mathbb{R}^p$) minimizando o erro de reconstrução $\mathcal{L} = \| D - f_{\text{dec}}(f_{\text{enc}}(D)) \|_2^2$. A variável latente contínua $z_i = f_{\text{enc}}(D_i)$ é auditada por *Permutation Feature Importance* (PFI) e particionada via algoritmo K-Means em **5 Níveis de Toxicidade Ambiental ($\text{ATI} \in \{1, 2, 3, 4, 5\}$)**.

### 3.3. Vetor de Variáveis de Confusão e Controle Assistencial ($Z$)
Para bloquear caminhos *backdoor* no Grafo Acíclico Direcionado (DAG) e neutralizar o viés de detecção:
* **Controle Assistencial e Diagnóstico (CNES / DATASUS):** Presença binária e densidade regional de CACON/UNACON, número de leitos clínicos/cirúrgicos e equipamentos de imagem (tomógrafos, mamógrafos) por 100.000 habitantes, e cobertura da Atenção Primária à Saúde.
* **Controle Sanitário e Socioeconômico (SNIS / Censo IBGE / IPEA):** Percentual de atendimento urbano e total de água tratada (`IN055`), índice de coleta e tratamento de esgoto (`IN056`, `IN046`), destinação de resíduos sólidos (existência de lixões a céu aberto), renda domiciliar per capita, taxa de analfabetismo, Índice de Vulnerabilidade Social (IVS) e proporção de domicílios com cobertura histórica de fibrocimento/amianto.
* **Controle Demográfico Residual:** Proporção de residentes com idade $\ge 60$ anos, razão de sexos e composição racial (% autodeclarados pretos, pardos e indígenas).

---

## 4. Etapas Sequenciais de Execução do Pipeline

### Etapa 1: Ingestão Orientada a Contratos, Limpeza Semântica e Harmonização
1. Execução automatizada de queries parametrizadas no Google Cloud BigQuery (`basedosdados`) via `BigQueryEngine` (com verificação prévia por *Dry-Run* e leitura colunar via *Arrow Storage API*) e coleta assíncrona de APIs governamentais (`SISAGUA`, `IBAMA`, `SISAM/INPE`, `ANEEL`, `SINAN`).
2. Aplicação estrita dos objetos `DataContract` em `Polars`: padronização de chaves primárias para `id_municipio` (7 dígitos) e conversão determinística de todos os códigos sentinelas de erro/ausência do DATASUS e SISAGUA (`0` implausível, `9`, `99`, `999`, `-1`, `IGN`) para valores nulos explícitos (`null` / `NaN`), prevenindo a corrupção numérica nos embeddings de Fourier do TabFM.
3. Cálculo das taxas padronizadas ($\text{ASR}$ e $\text{SMR}$), execução da suavização espacial no `PySAL` ($k = 31$) e consolidação da matriz histórica defasada em formato Apache Parquet (`Zstd`).

### Etapa 2: Bloqueio Geográfico Anti-Vazamento e Triagem Multiescala (Discovery vs. Confirmation)
1. Interseção espacial (*Spatial Join* em `GeoPandas` na projeção `EPSG:5070`) dos municípios com os polígonos das Ottobacias da ANA para atribuição do identificador de bloco hidrográfico (`ottobacia_id`).
2. **Partição Geográfica Disjunta (`spatial-kfold`):** Divisão dos blocos hidrográficos em dois macro-conjuntos independentes:
   * **Conjunto de Descoberta (*Discovery Set* — 40% dos blocos):** Utilizado exclusivamente para diagnóstico de multicolinearidade — exigindo Fator de Inflação da Variância **$\text{VIF} < 5$** e correlação par-a-par de Spearman **$|\rho_s| < 0,70$** —, seleção de variáveis por estabilidade de bootstrap espacial (`Random Forest %IncMSE` + `LASSO`) e evolução de engenharia de atributos do `TabFM-Auto`.
   * **Conjunto de Confirmação (*Confirmation Set* — 60% dos blocos):** Mantido isolado para estimação econométrica confirmatória via Mínimos Quadrados Ordinários/Ponderados (OLS/WLS), Regressão Geograficamente Ponderada (GWR) e **GWR Multiescala (MGWR)**. No MGWR, a largura de banda ótima (*bandwidth* $bw_k$) selecionada via critério $\text{AIC}_c$ quantifica o raio de ação física de cada vetor (distinguindo efeitos ultralocais de 90–300m da deriva agrícola de efeitos macrorregionais de bacias hidrográficas e dispersão de $\text{PM}_{2.5}$).

### Etapa 3: Treinamento, Inferência em Contexto (TabFM) e Explicabilidade (XAI)
Sob um protocolo separado de **Validação Cruzada Aninhada em 5 Blocos Espaciais (5-fold Nested SBCV)**, três paradigmas algorítmicos são executados sobre os mesmos folds geográficos:
1. **Paradigma Foundation In-Context (`TabFM`, `TabFM+`, `TabFM-Auto` e `TabPFN v2`):**
   * Passagem direta (*single forward pass*) na janela nativa de até 16.384 linhas do TabFM (400M parâmetros, *Fourier cell embeddings* + 24 camadas de atenção em contexto).
   * Execução da expansão em 32 visões com SVD, cruzamentos de atributos, ponderação via NNLS e calibração pós-hoc de Platt (`TabFM+`).
   * Orquestração em sandbox de validação cruzada de 3 folds internos do agente `TabFM-Auto` (`preprocess()`, `engineer()`, `sample()`, `postprocess()`) sem acesso ao fold espacial de teste.
   * Na versão em nuvem/produção institucional, execução nativa via SQL no Google Cloud BigQuery utilizando as funções `AI.PREDICT` e `AI.EVALUATE`.
2. **Paradigma Deep Learning com Atenção Esparsa (`TabNet`):**
   * Treinamento com *Sequential Attention* (`sparsemax` / `entmax`) para extrair as matrizes de máscara de seleção de atributos $M_{\text{agg}} \in \mathbb{R}^{N \times p}$, revelando quais fatores (agroquímicos, hídricos, atmosféricos ou ocupacionais) dominam a predição especificamente em cada município.
3. **Paradigma GBDT + SHAP (`XGBoost`, `LightGBM`, `CatBoost`):**
   * Ajuste de hiperparâmetros estritamente dentro dos folds espaciais internos e extração exata de valores `TreeSHAP`.
   * Geração de curvas **PDP** (*Partial Dependence Plots*), **ICE** (*Individual Conditional Expectation*) e identificação algorítmica do **Limiar Crítico de Transição ($\text{SHAP} = 0$)** — o valor exato de concentração de poluente ou distância de lavoura a partir do qual a contribuição marginal para a mortalidade por câncer torna-se estritamente positiva.

### Etapa 4: Estimação Causal Semiparamétrica (Double Machine Learning) e Auditoria de Subnotificação
1. **Estimação Ortogonalizada (PLR via `DoubleML`):**
   Para cada vetor de exposição contínua $D_k$, estima-se o modelo parcialmente linear:
   $$Y = \theta_k D_k + g(Z) + U, \quad D_k = m(Z) + V$$
   Utilizando *Cross-Fitting Espacial* em $K = 5$ blocos hidrográficos, os modelos de *machine learning* (ensembles de GBDT e TabFM) preveem fora da amostra a esperança condicional do desfecho $\hat{g}^{(-fold)}(Z_i)$ e da exposição $\hat{m}^{(-fold)}(Z_i)$. Computam-se os resíduos ortogonalizados $\tilde{Y}_i = Y_i - \hat{g}^{(-fold)}(Z_i)$ e $\tilde{D}_{k,i} = D_{k,i} - \hat{m}^{(-fold)}(Z_i)$, obtendo-se o estimador $\sqrt{n}$-consistente de Neyman:
   $$\hat{\theta}_k = \left( \frac{1}{n} \sum_{i=1}^n \tilde{D}_{k,i}^2 \right)^{-1} \left( \frac{1}{n} \sum_{i=1}^n \tilde{D}_{k,i} \tilde{Y}_i \right)$$
2. **Padronização de Impacto por Intervalo Interquartil ($\text{IQR-ATE}$):**
   Para tornar comparáveis grandezas físicas distintas (litros/ha, $\mu\text{g/m}^3$, violações VMP), o efeito causal padronizado é calculado normalizando-se pela linha de base média regional $\bar{Y}_{\text{reg}}$ e escalando pelo intervalo interquartil da exposição $\text{IQR}(D_k) = P_{75}(D_k) - P_{25}(D_k)$:
   $$\text{Impacto Causal Padronizado}_k = \left( \frac{|\hat{\theta}_k|}{\bar{Y}_{\text{reg}}} \right) \cdot \text{IQR}(D_k)$$
3. **Heterogeneidade Causal (`EconML` Causal Forests) e Testes de Refutação (`DoWhy`):**
   Estimação de $\hat{\theta}(X_i)$ para estratificar os municípios em grupos de vulnerabilidade extrema e execução da bateria de refutação: (i) substituição de $D_k$ por variável placebo aleatória ($\hat{\theta}_{\text{placebo}} \approx 0, p > 0,05$); (ii) inserção de confundidor sintético correlacionado; e (iii) reestimação em subconjuntos de 80% dos blocos espaciais.
4. **Cálculo do Índice de Divergência de Vigilância ($\text{IDV}$ — Auditoria SINAN):**
   Seja $\hat{I}_i^{\text{TabFM}}$ a incidência esperada de intoxicações exógenas e câncer ocupacional predita pelo modelo com base apenas nos vetores produtivos/ambientais $(D_1, D_2, D_3, D_4)$ e $I_i^{\text{SINAN}}$ a taxa efetivamente notificada pelo município no SINAN:
   $$\text{IDV}_i = \log_{10} \left( \frac{\hat{I}_i^{\text{TabFM}} + \epsilon}{I_i^{\text{SINAN}} + \epsilon} \right)$$
   Municípios com $\text{IDV}_i$ no decil superior ($\ge P_{90}$) são classificados automaticamente como **Pontos Cegos de Vigilância (*Silent Hotspots*)** para intervenção do CEREST e MPT.

---

## 5. Resultados Esperados e Critérios de Sucesso

Ao final da execução metodológica, espera-se obter cinco grupos de resultados quantitativos e operacionais:

1. **Demonstração Empírica da Correção do Viés de Detecção:** Comprovação numérica de que, enquanto regressões brutas apresentam correlação positiva espúria entre cobertura de saneamento/leitos hospitalares e taxas de câncer, a ortogonalização via `DoubleML` inverte ou anula esse viés e faz emergir o efeito causal real dos agrotóxicos, contaminantes do SISAGUA, $\text{PM}_{2.5}$ e agentes da LINACH.
2. **Ganho Preditivo no Benchmark Espacial:** Evidência de que a combinação de suavização Bayesiana ($k = 31$), janelas de latência biológica (2–5 anos vs. 10–25 anos) e orquestração semântica (`TabFM-Auto`) reduz significativamente o erro de generalização em bacias hidrográficas não observadas ($\text{RMSE}$ e $\text{MAE}$), superando pipelines convencionais sem bloqueio espacial.
3. **Mapeamento de Limiares Críticos ($\text{SHAP} = 0$) e Raios Espaciais (MGWR):** Determinação de pontos de corte acionáveis para políticas públicas (ex.: quantos litros de agrotóxico por hectare, quantos $\mu\text{g/m}^3$ de $\text{PM}_{2.5}$ ou quantos anos de violação de trihalometanos na água disparam o regime de risco acelerado para tumores hematológicos, respiratórios e digestivos).
4. **Quantificação de Óbitos Evitáveis no Simulador Contrafactual:** Tabelas e mapas municipais estimando o número exato de vidas salvas por década sob três cenários simulados via curvas ICE e $\hat{\theta}_{\text{DML}}$: (a) redução de 1 IQR na carga agroquímica e atmosférica; (b) imposição de zonas de amortecimento de 300 metros ao redor de áreas urbanas; e (c) cumprimento integral dos padrões de potabilidade da Portaria GM/MS nº 888/2021.
5. **Catálogo Auditável de *Silent Hotspots* ($\text{IDV}$):** Lista nominal hierarquizada dos municípios brasileiros com maior omissão epidemiológica no SINAN, acompanhada de dossiês parametrizados de Nexo Técnico Epidemiológico (CNAE $\times$ CID-10) prontos para subsidiar auditorias da RENAST/CEREST, Ações Civis Públicas do MPF/MPT e diretrizes de antecipação de rastreamento oncológico pelo INCA/SUS.

---

## 6. Matriz de Síntese Metodológica (Guia de Execução)

| Fase do Pipeline | Módulos do Repositório (`src/`) | Métodos Estatísticos e Algoritmos | Parâmetros e Regras de Ouro | Métrica / Entregável de Validação |
| :--- | :--- | :--- | :--- | :--- |
| **1. Ingestão, Contratos e Suavização** | `core/bq_engine.py`<br>`core/contracts.py`<br>`spatial/eb_smoothing.py` | Padronização Etária Direta ($\text{ASR}$) e Indireta ($\text{SMR}$); *Spatial Linear Empirical Bayes* (`PySAL`). | Malha $N = 5.570$ para vizinhança $k = 31$; conversão de sentinelas (`99`, `999` $\to$ `null`); filtro para recorte analítico ($> 50\text{k}$ hab. + Polos). | Artefatos Parquet validados sem duplicatas; redução do $\text{RMSE}$ em pequenas áreas para $\approx 0,498$. |
| **2. Defasagem Temporal e Blocagem Espacial** | `features/latency_builder.py`<br>`spatial/ottobacias_blocks.py` | Médias móveis retrospectivas (`Polars`); *Spatial Join* em `EPSG:5070` com Ottobacias ANA (`spatial-kfold`); OLS, GWR e MGWR. | Lag de $2\text{–}5$ anos (`C81–C96`) e $10\text{–}25$ anos (`C15–C80`); split 40% *Discovery* ($\text{VIF} < 5, |\rho_s| < 0,70$) / 60% *Confirmation*. | Larguras de banda locais ($bw_k$) via $\text{AIC}_c$ no MGWR; ausência de vazamento geográfico entre treino e teste. |
| **3. Predição Híbrida e Explicabilidade (XAI)** | `models/tabfm_runner.py`<br>`models/baselines_xai.py` | Google `TabFM` (400M), `TabFM+` (32 visões + SVD/NNLS), `TabFM-Auto`, `TabPFN v2`, `TabNet` e `XGBoost/LightGBM/CatBoost` + `TreeSHAP`. | 5-fold Nested Spatial Block CV; contexto até 16.384 linhas; execução local (pesquisa) ou `AI.PREDICT` no BigQuery (produção). | Ranking comparativo ($\text{RMSE}$, $R^2$, $\text{ROC-AUC}$); máscaras de atenção `TabNet`; curvas PDP/ICE e limiares $\text{SHAP} = 0$. |
| **4. Inferência Causal e Vigilância Ativa** | `models/causal_dml.py`<br>`models/idv_auditor.py` | *Partially Linear Regression* (`DoubleML`), *Causal Forests* (`EconML`), Autoencoder ($\text{ATI}$) + K-Means, Refutação (`DoWhy`). | Cross-fitting agrupado por cluster espacial; padronização de $\text{ATE}$ por $\text{IQR}$; 3 testes de refutação exigindo $p > 0,05$. | Estimativas $\hat{\theta}$ ($\text{ATE}$ e $\text{CATE}$) livres de viés assistencial; Simulador Contrafactual e Ranking Nacional do $\text{IDV}$. |
