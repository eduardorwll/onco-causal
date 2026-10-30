-- sql/01_diretorio_amostra.sql
-- Extração da Malha Municipal Nacional e Classificação Estratificada (Stage 01)

WITH pop_recente AS (
    SELECT 
        id_municipio,
        CAST(populacao AS INT64) AS populacao,
        CAST(ano AS INT64) AS ano_populacao,
        ROW_NUMBER() OVER(PARTITION BY id_municipio ORDER BY ano DESC) AS rn
    FROM `basedosdados.br_ibge_populacao.municipio`
    WHERE ano >= @base_year_pop AND populacao IS NOT NULL
)
SELECT 
    CAST(d.id_municipio AS STRING) AS id_municipio,
    CAST(d.id_municipio_6 AS STRING) AS id_municipio_6,
    CAST(d.nome AS STRING) AS nome_municipio,
    CAST(d.sigla_uf AS STRING) AS sigla_uf,
    CAST(d.id_mesorregiao AS STRING) AS id_mesorregiao,
    CAST(d.id_microrregiao AS STRING) AS id_microrregiao,
    COALESCE(p.populacao, 0) AS populacao_estimada,
    CASE 
        WHEN d.capital_uf = 1 THEN '1_Capital'
        WHEN d.id_municipio IN UNNEST(@polos_estrategicos) THEN '2_Polo_Estrategico'
        WHEN COALESCE(p.populacao, 0) >= @min_populacao THEN '3_Acima_50k'
        ELSE '4_Pequeno_Porte'
    END AS perfil_amostral
FROM `basedosdados.br_bd_diretorios_brasil.municipio` AS d
LEFT JOIN pop_recente AS p 
    ON d.id_municipio = p.id_municipio AND p.rn = 1
WHERE d.id_municipio NOT IN UNNEST(@excluded_municipios)
ORDER BY d.id_municipio
