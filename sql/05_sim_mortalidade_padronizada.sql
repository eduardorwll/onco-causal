-- sql/05_sim_mortalidade_padronizada.sql
-- Extração de óbitos oncológicos por residência e denominadores demográficos por faixa etária (SIM & População IBGE)

WITH obitos AS (
    SELECT 
        CAST(id_municipio AS STRING) AS id_municipio,
        CAST(ano AS INT64) AS ano,
        CASE
            WHEN SUBSTR(causa_basica, 1, 3) IN ('C81','C82','C83','C84','C85','C86','C88','C90','C91','C92','C93','C94','C95','C96') 
                 OR (idade < 20 AND SUBSTR(causa_basica, 1, 1) = 'C') THEN 'hematologico_infantojuvenil'
            WHEN SUBSTR(causa_basica, 1, 3) = 'C34' THEN 'respiratorio'
            WHEN SUBSTR(causa_basica, 1, 3) IN ('C15','C16','C17','C18','C19','C20','C21','C22','C23','C24','C25','C26') THEN 'digestivo'
            WHEN SUBSTR(causa_basica, 1, 3) IN ('C43','C44') THEN 'pele_melanoma'
            WHEN SUBSTR(causa_basica, 1, 3) IN ('C50','C53','C61','C67','C73') THEN 'hormoniodependente_urogenital'
            ELSE NULL
        END AS target_cancer,
        CASE
            WHEN idade BETWEEN 0 AND 4 THEN '0-4 anos'
            WHEN idade BETWEEN 5 AND 9 THEN '5-9 anos'
            WHEN idade BETWEEN 10 AND 14 THEN '10-14 anos'
            WHEN idade BETWEEN 15 AND 19 THEN '15-19 anos'
            WHEN idade BETWEEN 20 AND 24 THEN '20-24 anos'
            WHEN idade BETWEEN 25 AND 29 THEN '25-29 anos'
            WHEN idade BETWEEN 30 AND 34 THEN '30-34 anos'
            WHEN idade BETWEEN 35 AND 39 THEN '35-39 anos'
            WHEN idade BETWEEN 40 AND 44 THEN '40-44 anos'
            WHEN idade BETWEEN 45 AND 49 THEN '45-49 anos'
            WHEN idade BETWEEN 50 AND 54 THEN '50-54 anos'
            WHEN idade BETWEEN 55 AND 59 THEN '55-59 anos'
            WHEN idade BETWEEN 60 AND 64 THEN '60-64 anos'
            WHEN idade BETWEEN 65 AND 69 THEN '65-69 anos'
            WHEN idade BETWEEN 70 AND 74 THEN '70-74 anos'
            WHEN idade BETWEEN 75 AND 79 THEN '75-79 anos'
            WHEN idade >= 80 THEN '80-mais'
            ELSE 'Ignorado'
        END AS grupo_idade,
        SUM(numero_obitos) AS obitos
    FROM `basedosdados.br_ms_sim.municipio_causa_idade`
    WHERE ano = @ano AND id_municipio IS NOT NULL
    GROUP BY 1, 2, 3, 4
),
pop AS (
    SELECT 
        CAST(id_municipio AS STRING) AS id_municipio,
        CAST(ano AS INT64) AS ano,
        grupo_idade,
        SUM(COALESCE(populacao, 0)) AS populacao
    FROM `basedosdados.br_ms_populacao.municipio`
    WHERE ano = @ano
    GROUP BY 1, 2, 3
),
targets AS (
    SELECT t FROM UNNEST([
        'hematologico_infantojuvenil', 
        'respiratorio', 
        'digestivo', 
        'pele_melanoma', 
        'hormoniodependente_urogenital'
    ]) AS t
),
grid AS (
    SELECT 
        p.id_municipio, 
        p.ano, 
        t.t AS target_cancer, 
        p.grupo_idade, 
        p.populacao
    FROM pop p
    CROSS JOIN targets t
    WHERE p.id_municipio NOT IN UNNEST(@excluded_municipios)
)
SELECT 
    g.id_municipio,
    g.ano,
    g.target_cancer,
    g.grupo_idade,
    CAST(g.populacao AS INT64) AS populacao,
    CAST(COALESCE(o.obitos, 0) AS INT64) AS obitos
FROM grid g
LEFT JOIN obitos o 
    ON g.id_municipio = o.id_municipio 
   AND g.ano = o.ano 
   AND g.target_cancer = o.target_cancer 
   AND g.grupo_idade = o.grupo_idade
ORDER BY g.id_municipio, g.target_cancer, g.grupo_idade
