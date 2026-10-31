-- sql/06_mapbiomas_cobertura.sql
-- Extração de séries históricas de uso e cobertura do solo por município (MapBiomas Estatísticas)

SELECT 
    CAST(id_municipio AS STRING) AS id_municipio,
    CAST(ano AS INT64) AS ano,
    CAST(SUM(CASE WHEN nivel_2 = 'Agricultura' THEN area ELSE 0 END) AS FLOAT64) AS area_agricultura_ha,
    CAST(SUM(CASE WHEN nivel_2 = 'Pastagem' THEN area ELSE 0 END) AS FLOAT64) AS area_pastagem_ha,
    CAST(SUM(CASE WHEN nivel_2 = 'Silvicultura' THEN area ELSE 0 END) AS FLOAT64) AS area_silvicultura_ha,
    CAST(SUM(CASE WHEN nivel_2 = 'Área Urbanizada' THEN area ELSE 0 END) AS FLOAT64) AS area_urbanizada_ha,
    CAST(SUM(CASE WHEN nivel_1 = 'Floresta' THEN area ELSE 0 END) AS FLOAT64) AS area_floresta_ha
FROM `basedosdados.br_mapbiomas_estatisticas.cobertura_municipio_classe`
WHERE ano BETWEEN @ano_inicio AND @ano_fim
  AND id_municipio IS NOT NULL
GROUP BY id_municipio, ano
ORDER BY id_municipio, ano
