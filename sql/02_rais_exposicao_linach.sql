-- sql/02_rais_exposicao_linach.sql
-- Extração de vínculos empregatícios formais e exposição ocupacional LINACH (CNAE 2.0) por município e ano

SELECT 
    CAST(id_municipio AS STRING) AS id_municipio,
    CAST(ano AS INT64) AS ano,
    CAST(SUM(COALESCE(quantidade_vinculos_ativos, 0)) AS INT64) AS vinculos_totais,
    CAST(SUM(CASE 
        WHEN SUBSTR(cnae_2, 1, 3) IN UNNEST(@cnae_prefixes_3) 
          OR SUBSTR(cnae_2, 1, 4) IN UNNEST(@cnae_prefixes_4) 
        THEN COALESCE(quantidade_vinculos_ativos, 0) 
        ELSE 0 
    END) AS INT64) AS vinculos_linach
FROM `basedosdados.br_me_rais.microdados_estabelecimentos`
WHERE ano BETWEEN @ano_inicio AND @ano_fim
  AND id_municipio IS NOT NULL
GROUP BY id_municipio, ano
ORDER BY id_municipio, ano
