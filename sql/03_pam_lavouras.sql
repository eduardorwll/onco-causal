-- sql/03_pam_lavouras.sql
-- Extração de área plantada (hectares) das culturas críticas do Método Pignati et al. (PAM/IBGE)

WITH temp AS (
    SELECT 
        CAST(id_municipio AS STRING) AS id_municipio,
        CAST(ano AS INT64) AS ano,
        SUM(CASE WHEN LOWER(produto) LIKE '%soja%' THEN COALESCE(area_plantada, 0) ELSE 0 END) AS area_soja_ha,
        SUM(CASE WHEN LOWER(produto) LIKE '%milho%' THEN COALESCE(area_plantada, 0) ELSE 0 END) AS area_milho_ha,
        SUM(CASE WHEN LOWER(produto) LIKE '%algod%' THEN COALESCE(area_plantada, 0) ELSE 0 END) AS area_algodao_ha,
        SUM(CASE WHEN LOWER(produto) LIKE '%cana%' THEN COALESCE(area_plantada, 0) ELSE 0 END) AS area_cana_ha,
        SUM(CASE WHEN LOWER(produto) LIKE '%arroz%' THEN COALESCE(area_plantada, 0) ELSE 0 END) AS area_arroz_ha
    FROM `basedosdados.br_ibge_pam.lavoura_temporaria`
    WHERE ano BETWEEN @ano_inicio AND @ano_fim
      AND id_municipio IS NOT NULL
    GROUP BY id_municipio, ano
),
perm AS (
    SELECT 
        CAST(id_municipio AS STRING) AS id_municipio,
        CAST(ano AS INT64) AS ano,
        SUM(CASE WHEN LOWER(produto) LIKE '%laranja%' OR LOWER(produto) LIKE '%lim%' THEN COALESCE(area_destinada_colheita, 0) ELSE 0 END) AS area_citros_ha
    FROM `basedosdados.br_ibge_pam.lavoura_permanente`
    WHERE ano BETWEEN @ano_inicio AND @ano_fim
      AND id_municipio IS NOT NULL
    GROUP BY id_municipio, ano
)
SELECT 
    COALESCE(t.id_municipio, p.id_municipio) AS id_municipio,
    COALESCE(t.ano, p.ano) AS ano,
    CAST(COALESCE(t.area_soja_ha, 0) AS FLOAT64) AS area_soja_ha,
    CAST(COALESCE(t.area_milho_ha, 0) AS FLOAT64) AS area_milho_ha,
    CAST(COALESCE(t.area_algodao_ha, 0) AS FLOAT64) AS area_algodao_ha,
    CAST(COALESCE(t.area_cana_ha, 0) AS FLOAT64) AS area_cana_ha,
    CAST(COALESCE(t.area_arroz_ha, 0) AS FLOAT64) AS area_arroz_ha,
    CAST(COALESCE(p.area_citros_ha, 0) AS FLOAT64) AS area_citros_ha,
    CAST((
        COALESCE(t.area_soja_ha, 0) + 
        COALESCE(t.area_milho_ha, 0) + 
        COALESCE(t.area_algodao_ha, 0) + 
        COALESCE(t.area_cana_ha, 0) + 
        COALESCE(t.area_arroz_ha, 0) + 
        COALESCE(p.area_citros_ha, 0)
    ) AS FLOAT64) AS area_total_lavouras_criticas_ha
FROM temp t
FULL OUTER JOIN perm p 
    ON t.id_municipio = p.id_municipio AND t.ano = p.ano
ORDER BY id_municipio, ano
