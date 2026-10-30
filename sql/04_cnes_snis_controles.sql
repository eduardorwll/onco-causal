-- sql/04_cnes_snis_controles.sql
-- Extração de variáveis assistenciais (CNES) e saneamento (SNIS) para ortogonalização do viés de detecção (Vetor Z)

WITH hab AS (
    SELECT 
        CAST(id_municipio AS STRING) AS id_municipio,
        CAST(@ano AS INT64) AS ano,
        COUNT(DISTINCT id_estabelecimento_cnes) AS unacon_cacon_ativos
    FROM `basedosdados.br_ms_cnes.habilitacao`
    WHERE ano = @ano
      AND tipo_habilitacao LIKE '17%'
    GROUP BY id_municipio
),
leito AS (
    SELECT 
        CAST(id_municipio AS STRING) AS id_municipio,
        CAST(@ano AS INT64) AS ano,
        SUM(COALESCE(quantidade_leito_cirurgico, 0) + COALESCE(quantidade_leito_clinico, 0) + COALESCE(quantidade_leito_complementar, 0)) AS leitos_totais
    FROM `basedosdados.br_ms_cnes.estabelecimento`
    WHERE ano = @ano 
      AND mes = 12
    GROUP BY id_municipio
),
equip AS (
    SELECT 
        CAST(id_municipio AS STRING) AS id_municipio,
        CAST(@ano AS INT64) AS ano,
        SUM(CASE WHEN id_equipamento = '11' THEN COALESCE(quantidade_equipamentos_ativos, 0) ELSE 0 END) AS tomografos_ativos,
        SUM(CASE WHEN id_equipamento IN ('2', '3', '17') THEN COALESCE(quantidade_equipamentos_ativos, 0) ELSE 0 END) AS mamografos_ativos
    FROM `basedosdados.br_ms_cnes.equipamento`
    WHERE ano = @ano 
      AND mes = 12
    GROUP BY id_municipio
),
snis AS (
    SELECT 
        CAST(id_municipio AS STRING) AS id_municipio,
        CAST(@ano AS INT64) AS ano,
        AVG(COALESCE(indice_atendimento_total_agua, 0)) AS indice_atendimento_total_agua,
        AVG(COALESCE(indice_coleta_esgoto, 0)) AS indice_coleta_esgoto,
        AVG(COALESCE(indice_tratamento_esgoto, 0)) AS indice_tratamento_esgoto
    FROM `basedosdados.br_mdr_snis.municipio_agua_esgoto`
    WHERE ano = @ano
    GROUP BY id_municipio
),
mun_grid AS (
    SELECT 
        CAST(d.id_municipio AS STRING) AS id_municipio,
        CAST(@ano AS INT64) AS ano
    FROM `basedosdados.br_bd_diretorios_brasil.municipio` d
    WHERE d.id_municipio NOT IN UNNEST(@excluded_municipios)
)
SELECT 
    m.id_municipio,
    m.ano,
    CAST(COALESCE(h.unacon_cacon_ativos, 0) AS INT64) AS unacon_cacon_ativos,
    CAST(COALESCE(l.leitos_totais, 0) AS INT64) AS leitos_totais,
    CAST(COALESCE(e.tomografos_ativos, 0) AS INT64) AS tomografos_ativos,
    CAST(COALESCE(e.mamografos_ativos, 0) AS INT64) AS mamografos_ativos,
    CAST(COALESCE(s.indice_atendimento_total_agua, 0.0) AS FLOAT64) AS indice_atendimento_total_agua,
    CAST(COALESCE(s.indice_coleta_esgoto, 0.0) AS FLOAT64) AS indice_coleta_esgoto,
    CAST(COALESCE(s.indice_tratamento_esgoto, 0.0) AS FLOAT64) AS indice_tratamento_esgoto
FROM mun_grid m
LEFT JOIN hab h ON m.id_municipio = h.id_municipio
LEFT JOIN leito l ON m.id_municipio = l.id_municipio
LEFT JOIN equip e ON m.id_municipio = e.id_municipio
LEFT JOIN snis s ON m.id_municipio = s.id_municipio
ORDER BY m.id_municipio, m.ano
