# PREREGISTRATION.md — Pré-Registro Epistemológico e Científico do Estudo `onco-causal`

> **Data de Congelamento:** 2026-10-30  
> **Versão / Tag Git:** `v0.1.0-preregistration`  
> **Status:** CONGELADO / IMUTÁVEL (Anti-*p-hacking* Protocol)

Este documento atua como pré-registro público e determinístico do arcabouço conceitual, hipóteses estatísticas, janelas temporais de latência biológica, subgrupos oncológicos e critérios de decisão causal antes do cruzamento com os microdados do Sistema de Informações sobre Mortalidade (SIM).

---

## 1. Pergunta Central de Pesquisa
*"Qual é o efeito causal líquido, isolado de fatores de confusão demográficos, socioeconômicos e de viés de acesso diagnóstico hospitalar, exercido pela exposição histórica acumulada a múltiplos vetores carcinogênicos (agroquímico, hídrico, atmosférico e ocupacional) sobre as taxas padronizadas por idade e espacialmente suavizadas de mortalidade por subgrupos topográficos de câncer nos municípios brasileiros?"*

---

## 2. Hipóteses Falsificáveis ($H_1 \text{ a } H_4$)

### $H_1$ — Especificidade Etiológica e Janelas Biológicas de Latência
- **$H_{0,1}$:** A defasagem temporal histórica ($t - \text{lag}$) não produz ganho preditivo ($\Delta R^2_{\text{spatial}} \le 0$) nem alteração de sinal frente à exposição contemporânea ($t_0$).
- **$H_{A,1}$:** O pareamento biológico estrito maximiza a razão sinal-ruído:
  - **Curta Latência ($t-2$ a $t-5$ anos):** Neoplasias Hematológicas e Infantojuvenis (`C81–C96`) frente a benzeno/solventes (RAIS/LINACH) e deriva agroquímica aérea.
  - **Longa Latência ($t-10$ a $t-25$ anos):** Tumores Sólidos — Pulmão/Respiratório (`C34`) frente a $\text{PM}_{2.5}$ e queima fóssil/termelétricas; Digestivo (`C15–C26`) frente a contaminantes hídricos no SISAGUA (trihalometanos, metais pesados, agrotóxicos); Pele/Melanoma (`C43–C44`) frente a radiação UV; Hormoniodependentes (`C50, C53, C61, C67, C73`) frente a disruptores endócrinos.

### $H_2$ — Aprendizagem em Contexto sob Bloqueio Espacial Anti-Vazamento
- **$H_{0,2}$:** Em 5-fold Nested Spatial Block CV ancorado em Ottobacias hidrográficas disjuntas, o Google TabFM / TabPFN v2 não supera nem iguala modelos supervisionados GBDT (XGBoost, LightGBM, CatBoost) e TabNet.
- **$H_{A,2}$:** A atenção bidimensional e Fourier Cell Embeddings do TabFM superam ou igualam GBDTs na predição zero-shot de territórios de bacias omitidas, reduzindo o sobreajuste espacial.

### $H_3$ — Persistência Causal Pós-Ortogonalização de Neyman
- **$H_{0,3}$:** Após ortogonalizar o viés de detecção assistencial (leitos, equipamentos e UNACON/CACON no CNES), saneamento (SNIS) e demografia via Double/Debiased Machine Learning (DML), o Efeito Médio do Tratamento dos carcinógenos converge para zero ($\hat{\theta} = 0, p \ge 0,05$).
- **$H_{A,3}$:** O estimador ortogonalizado expurga o paradoxo assistencial e revela efeito causal líquido positivo e estatisticamente significante ($\hat{\theta} > 0, p < 0,05$) com aprovação nos 3 testes de refutação do DoWhy ($p_{\text{placebo}} > 0,05$).

### $H_4$ — Modificação de Efeito por Vulnerabilidade Socioassistencial
- **$H_{0,4}$:** O impacto marginal dos carcinógenos é homogêneo ($\theta(X_i) = \theta$).
- **$H_{A,4}$:** A estimativa de Causal Forests (EconML) demonstrará variância estritamente positiva ($\text{Var}[\hat{\theta}(X_i)] > 0$), indicando letalidade amplificada em municípios com déficit de saneamento e desprovidos de cobertura UNACON/CACON.

---

## 3. Protocolo de Dupla Malha e Variáveis de Desfecho ($Y$)
1. **Malha Nacional Completa ($N = 5.570$ municípios):** Base universal de cálculo para matriz de vizinhança $k = 31$ mais próximos e Suavização Bayesiana Empírica Linear (Spatial EB PySAL).
2. **Recorte Analítico Estratificado:**
   - `1_Capital` (27 capitais/DF).
   - `2_Polo_Estrategico` (13 polos agroquímicos e petroquímicos/industriais de referência).
   - `3_Acima_50k` (municípios $\ge 50.000$ hab.).
   - `4_Controle_Interno` (municípios $\ge 50.000$ hab. com quantil inferior de densidade agrícola e industrial).
3. **Métrica $Y$:** Taxa Padronizada por Idade ($\text{ASR}$ por 100k hab., padrão mundial Segi/OMS) e Razão de Mortalidade Padronizada ($\text{SMR} = O_{i,c} / E_{i,c}$). É terminantemente proibido o uso de contagens absolutas ou taxas brutas simples como desfecho final.

---

## 4. Reprodutibilidade e Integridade Criptográfica
Todas as transformações, queries SQL e artefatos gerados são registrados no manifesto auditável `data/staging/manifest.json` com seus respectivos hashes SHA-256 e commits Git associados.
