# OBJETIVO.md — Fundamentação Conceitual, Científica e Institucional da Pesquisa

> **Título do Projeto:** Engenharia Preditiva e Inferência Causal na Epidemiologia Ambiental e Oncológica: Modelagem Espaço-Temporal de Carcinógenos Múltiplos no Brasil via Modelos de Fundação Tabulares (TabFM) e Econometria Semiparamétrica

---

## 1. Contextualização e Problema de Pesquisa

O Brasil experimenta uma transição epidemiológica complexa na qual o câncer consolidou-se como uma das principais causas de morbimortalidade no Sistema Único de Saúde (SUS). Paralelamente à urbanização acelerada e à coexistência de parques industriais pesados (petroquímicos, siderúrgicos e de mineração), o território nacional abriga um dos maiores sistemas de produção agropecuária intensiva em monoculturas do mundo, sustentado pelo uso maciço de agrotóxicos, fertilizantes químicos e queima de combustíveis fósseis.

Apesar das evidências toxicológicas e mecanísticas acumuladas pela Agência Internacional de Pesquisa em Câncer (IARC/OMS) sobre o potencial carcinogênico de pesticidas, metais pesados, subprodutos de desinfecção hídrica e material particulado fino ($\text{PM}_{2.5}$), a vigilância epidemiológica brasileira permanece predominantemente passiva, fragmentada e descritiva. Estudos ecológicos tradicionais esbarram em cinco entraves estruturais que impedem a conversão de dados públicos em políticas regulatórias e probatórias eficazes:

1. **A Falácia Ecológica e o Confundimento Socioeconômico:** A incapacidade de isolar a parcela do risco oncológico atribuível diretamente à degradação ambiental frente a variáveis demográficas (envelhecimento populacional) e determinantes sociais de saúde (renda, escolaridade e saneamento básico).
2. **O Paradoxo do Viés de Detecção Assistencial:** Municípios economicamente desenvolvidos e dotados de Centros e Unidades de Assistência de Alta Complexidade em Oncologia (CACON/UNACON) diagnosticam e registram substancialmente mais neoplasias per capita do que municípios rurais ou periféricos desassistidos. Em modelagens ingênuas, esse fenômeno produz associações paradoxais onde infraestrutura hospitalar e saneamento aparentam "elevar" o risco de câncer, mascarando zonas reais de sacrifício ambiental onde ocorrem óbitos sem diagnóstico etiológico ou migração forçada de pacientes.
3. **A Cegueira Temporal (Desalinhamento de Latência Biológica):** Análises transversais que correlacionam exposições ambientais contemporâneas com taxas de mortalidade do mesmo ano civil ignoram a história natural da carcinogênese — cujos períodos de iniciação, promoção e progressão tumoral exigem de 2 a 5 anos para neoplasias hematológicas e pediátricas, e de 10 a 35 anos para tumores sólidos epiteliais e mesenquimais em adultos.
4. **A Instabilidade Estatística de Pequenas Áreas e o Vazamento Espacial:** Em mais de 70% dos municípios brasileiros (com populações reduzidas), a ocorrência de um ou dois óbitos adicionais altera drasticamente as taxas brutas por 100.000 habitantes. Adicionalmente, a avaliação de algoritmos de *Machine Learning* sem bloqueio geográfico permite que modelos memorizem coordenadas e interpolem valores de municípios vizinhos (autocorrelação espacial), gerando métricas preditivas ilusórias.
5. **O Colapso da Vigilância Passiva (Subnotificação Crônica no SINAN):** Em polos críticos do agronegócio e da indústria, a razão entre agravos oficialmente notificados e casos reais chega a ser inferior a 1:70 — ou atinge 100% de omissão oficial —, invisibilizando o nexo técnico epidemiológico e paralisando a atuação do Ministério Público e dos órgãos de fiscalização.

---

## 2. Pergunta Central e Hipóteses Científicas

### 2.1. Pergunta de Pesquisa
> *"Qual é o efeito causal líquido, isolado de fatores de confusão demográficos, socioeconômicos e de viés de acesso diagnóstico, exercido pela exposição histórica acumulada a múltiplos vetores carcinogênicos — deriva agroquímica, contaminantes químicos na água de abastecimento, poluição atmosférica e matriz ocupacional de risco — sobre as taxas padronizadas e espacialmente suavizadas de incidência e mortalidade por subgrupos topográficos de câncer nos municípios brasileiros?"*

### 2.2. Hipóteses de Investigação
* **$H_1$ (Especificidade Etiológica e Defasagem Temporal):** A capacidade preditiva e a significância estatística dos vetores ambientais aumentam substancialmente quando o desfecho oncológico é desagregado por topografia (CID-10) e pareado com sua respectiva janela biológica de latência:
  * Exposições de curta latência ($t-2$ a $t-5$ anos) a agrotóxicos e benzeno associam-se primariamente a neoplasias hematológicas (`C81–C96`) e tumores infantojuvenis ($0\text{–}19$ anos).
  * Exposições crônicas de longa latência ($t-10$ a $t-25$ anos) a $\text{PM}_{2.5}$ e emissões industriais/termelétricas impactam seletivamente neoplasias do trato respiratório (`C34`, notadamente adenocarcinomas), enquanto contaminantes hídricos (trihalometanos, agrotóxicos e metais pesados no SISAGUA) e disruptores endócrinos associam-se a tumores do trato digestivo (`C15–C26`) e hormoniodependentes (`C50, C53, C61`).
* **$H_2$ (Superioridade de Modelos de Fundação Tabulares sob Bloqueio Espacial):** Em regimes de validação cruzada estrita em blocos geográficos disjuntos (bacias hidrográficas), a arquitetura de Aprendizagem em Contexto (*In-Context Learning*) do **Google TabFM** (potencializada por expansão multi-visão `TabFM+` e engenharia semântica automatizada `TabFM-Auto`) iguala ou supera modelos supervisionados baseados em árvores (XGBoost/LightGBM/CatBoost) e atenção sequencial (TabNet) na generalização fora da amostra para territórios não monitorados.
* **$H_3$ (Persistência do Sinal Causal Pós-Ortogonalização):** Após a remoção não-paramétrica do viés de detecção assistencial (CNES/UNACON), estrutura etária e saneamento (SNIS) via *Double/Debiased Machine Learning* (DML), persiste um Efeito Médio do Tratamento ($\text{ATE} > 0$, $p < 0,05$) estatisticamente robusto e resistente a testes de refutação por variáveis placebo, confirmando a causalidade ambiental e ocupacional.
* **$H_4$ (Amplificação por Vulnerabilidade Socioassistencial — Efeito Heterogêneo):** A análise de Efeitos Condicionais do Tratamento ($\text{CATE}$ via *Causal Forests*) demonstrará que a letalidade carcinogênica da exposição química é sinergicamente amplificada em municípios com déficit de saneamento básico e ausência de cobertura oncológica especializada.

---

## 3. Objetivos da Pesquisa

### 3.1. Objetivo Geral
Desenvolver um arcabouço metodológico, computacional e econométrico de fronteira que integre *Modelos de Fundação Tabulares (TabFM)*, *Inteligência Artificial Explicável (XAI)* e *Inferência Causal Semiparamétrica (Double Machine Learning)* para estimar o risco preditivo e quantificar o impacto causal de exposições ambientais e ocupacionais sobre a morbimortalidade por câncer no Brasil, convertendo grandes bases públicas do SUS e do meio ambiente em instrumentos de intervenção clínica, regulatória e jurídica.

### 3.2. Objetivos Específicos

#### Dimensão I: Epidemiologia Espacial e Harmonização Bio-Temporal
1. **Mitigar a instabilidade de pequenos denominadores e o viés demográfico:** Implementar a Padronização Etária Direta/Indireta combinada à Suavização Bayesiana Empírica Espacial Linear (*Spatial Empirical Bayes* com $k = 31$ vizinhos na malha integral de 5.570 municípios), estabilizando a variância das taxas antes do recorte analítico estratificado.
2. **Reconstruir a história de exposição multivetorial (1985–2025):** Integrar séries históricas de 4 dimensões carcinogênicas:
   * *Vetor Agroquímico e Uso da Terra:* Estimativa municipal de consumo de ingredientes ativos (Método de Pignati via PAM/IBGE e IBAMA) e proximidade lavoura-perímetro urbano (MapBiomas, isolando a faixa crítica de deriva de 90 a 300 metros).
   * *Vetor de Qualidade Hídrica:* Exposição crônica a agrotóxicos, metais pesados (arsênio, chumbo, cádmio) e subprodutos da cloração (THM-anos) acima do Valor Máximo Permitido na Portaria GM/MS nº 888/2021 (SISAGUA).
   * *Vetor Atmosférico, Energético e Radiativo:* Concentrações reanalisadas de $\text{PM}_{2.5}$, $\text{NO}_2$, $\text{SO}_2$, $\text{CO}$, $\text{O}_3$ (SISAM/INPE e CAMS), inventários de emissões industriais (SEEG), presença de usinas termelétricas a combustíveis fósseis (SIGEL/ANEEL) e Índice UV extremo (LABREN/INPE).
   * *Vetor Ocupacional e Produtivo:* Densidade municipal de trabalhadores formais expostos a agentes cancerígenos da LINACH / Grupo 1 da IARC e categorias I, II e III de Schilling (cruzamento RAIS/CNAE 2.0 e CBO).

#### Dimensão II: Aprendizagem de Máquina Tabular e Explicabilidade (XAI)
3. **Estabelecer um Benchmark Competitivo sob Validação Espacial Anti-Vazamento:** Comparar o desempenho preditivo zero-shot e supervisionado entre **TabFM / TabPFN v2** (Foundation In-Context), **TabNet** (Deep Learning com Atenção Sequencial) e **GBDTs** (XGBoost, LightGBM, CatBoost) utilizando *Nested Spatial Block Cross-Validation* ancorada em sub-bacias hidrográficas (Ottobacias da ANA).
4. **Superar a Cegueira Semântica e a Opacidade de Caixa-Preta:** Implementar pipelines de limpeza semântica de valores sentinela do DATASUS e extrair curvas de dose-resposta e limiares críticos de transição ($\text{SHAP} = 0$, *Partial Dependence Plots* [PDP] e *Individual Conditional Expectation* [ICE]) conjuntamente com Regressão Geograficamente Ponderada Multiescala (MGWR) para determinar o raio espacial de atuação de cada poluente.

#### Dimensão III: Inferência Causal e Avaliação Contrafactual
5. **Isolar o Efeito Causal Líquido (ATE e CATE):** Aplicar modelos de Regressão Parcialmente Linear (PLR) via *Double/Debiased Machine Learning* com *cross-fitting* agrupado por clusters espaciais para ortogonalizar o efeito dos confundidores socioeconômicos e assistenciais, padronizando o impacto de poluentes heterogêneos pelo Intervalo Interquartil (IQR) e sintetizando-os em um Índice de Toxicidade Ambiental (ATI) via Autoencoder.
6. **Submeter as Descobertas a Refutação Formal:** Validar a integridade estrutural do Grafo Acíclico Direcionado (DAG) através de testes de tratamento placebo, adição de causas comuns aleatórias e análise de sensibilidade a variáveis omitidas (`DoWhy` / `DoubleML`).

---

## 4. Relevância Científica e Contribuições Metodológicas

Este projeto posiciona-se na interseção entre a **Ciência da Computação (Fundação Tabular e IA Causal)** e a **Saúde Coletiva (Epidemiologia Ambiental e Oncológica)**, oferecendo três contribuições originais à literatura:

1. **Pioneirismo na Aplicação de Modelos de Fundação Tabulares (TabFM) à Vigilância Epidemiológica:** Enquanto a literatura médica utiliza predominantemente regressões lineares generalizadas ou árvores de decisão convencionais, este estudo avalia empiricamente o paradigma das *Prior-Data Fitted Networks* (PFNs) com *Fourier Cell Embeddings* em dados reais e ruidosos do Sul Global, demonstrando como acoplar *In-Context Learning* a mecanismos de controle espacial.
2. **Resolução Formal do Viés de Detecção no SUS via Ortogonalização de Neyman:** Em vez de apenas discutir a subnotificação como limitação qualitativa do estudo, o projeto modela explicitamente a rede assistencial (CNES/UNACON) e de saneamento (SNIS) como funções *nuisance* de alta dimensão $\hat{g}(Z)$ e $\hat{m}(Z)$, expurgando matematicamente o viés de diagnóstico das estimativas de risco ambiental.
3. **Integração Multiescala Mecanística-Populacional:** O desenho das variáveis traduz achados da biologia molecular do Microambiente Tumoral (remodelação da matriz extracelular, ativação de HIF-1$\alpha$ por hipóxia induzida por $\text{PM}_{2.5}$ e metais, disrupção endócrina e interação genética com chumbo/agrotóxicos) em janelas parametrizadas de exposição populacional ao nível municipal e de bacia hidrográfica.

---

## 5. Impacto Tangível e Aplicabilidade Institucional (Produtos da Pesquisa)

A pesquisa foi desenhada sob a premissa de **Ciência Acionável (*Actionable Science*)**, destinando seus resultados a três frentes diretas de transformação social e governança pública:

### 5.1. Simulador Contrafactual de Políticas Públicas para Gestores do SUS
Por meio das estimativas causais ($\hat{\theta}$) e das perturbações em contexto (ICE) no BigQuery, o projeto permite simular e quantificar **quantos casos e óbitos por câncer seriam evitados por década** em cada município ou microrregião brasileira mediante três intervenções regulatórias concretas:
* **Cenário A (Restrição de Deriva):** Imposição de zonas de amortecimento (*buffer zones*) livres de pulverização de agrotóxicos de no mínimo 300 metros ao redor de perímetros urbanos, escolas e mananciais.
* **Cenário B (Descontaminação Hídrica):** Adequação estrita das estações de tratamento de água municipais aos Valores Máximos Permitidos (VMP) de agrotóxicos, metais pesados e trihalometanos da Portaria GM/MS nº 888/2021.
* **Cenário C (Transição Energética e Controle Atmosférico):** Redução de 1 Intervalo Interquartil (IQR) nas concentrações médias anuais de $\text{PM}_{2.5}$ e desativação/filtragem de fontes estacionárias críticas (termelétricas a carvão/óleo e queima de biomassa).

### 5.2. Índice de Divergência de Vigilância (IDV) para Auditoria Ativa (SINAN / CEREST)
O projeto cria uma métrica de auditoria algorítmica obtida pela razão entre a morbimortalidade/intoxicação **esperada** pelo modelo (com base exclusivamente na assinatura físico-química, agrícola e ocupacional do município) e a taxa **oficialmente notificada** no SINAN. O IDV gera um mapa nacional de *"Pontos Cegos de Vigilância" (Silent Hotspots)*, fornecendo aos Centros de Referência em Saúde do Trabalhador (CEREST/RENAST) e à Inspeção do Trabalho alvos cirúrgicos para fiscalização in loco e busca ativa de casos omitidos.

### 5.3. Protocolo de Evidência Técnico-Jurídica e Antecipação de Rastreamento Clínico
* **Frente Jurídica e Previdenciária (MPF, MPT e INSS):** Fornecimento de prova estatística ortogonalizada (com intervalos de confiança válidos e refutação de placebos) para instruir Ações Civis Públicas ambientais, fundamentar o Nexo Técnico Epidemiológico Previdenciário (Grupo II de Schilling para concessão de benefícios acidentários B91) e embasar ações regressivas do INSS contra cadeias produtivas hiperpoluidoras.
* **Frente Clínica e Assistencial (INCA / Ministério da Saúde):** Identificação quantitativa de territórios onde a carga cumulativa de exposição ambiental a $\text{PM}_{2.5}$, água contaminada ou deriva agroquímica equivale ao risco conferido pelo tabagismo pesado ou histórico familiar, subsidiando protocolos do SUS para **antecipar a idade de início do rastreamento oncológico** (tomografia de baixa dose, mamografia e colonoscopia) em populações residentes em zonas de alto risco ambiental.
