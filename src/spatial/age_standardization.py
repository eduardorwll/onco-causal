# src/spatial/age_standardization.py
from __future__ import annotations

import logging
from collections.abc import Mapping

import polars as pl

logger = logging.getLogger("onco_causal.spatial.age_standardization")

# Pesos da População Padrão Mundial (Segi 1960 / OMS 2000-2025) normalizados para exatamente 100.000 hab.
# 17 faixas etárias compatíveis com o Ministério da Saúde (DATASUS):
RAW_WHO_WEIGHTS: Mapping[str, float] = {
    "0-4 anos": 8860.0,
    "5-9 anos": 8690.0,
    "10-14 anos": 8600.0,
    "15-19 anos": 8470.0,
    "20-24 anos": 8220.0,
    "25-29 anos": 7930.0,
    "30-34 anos": 7610.0,
    "35-39 anos": 7150.0,
    "40-44 anos": 6590.0,
    "45-49 anos": 6040.0,
    "50-54 anos": 5370.0,
    "55-59 anos": 4550.0,
    "60-64 anos": 3720.0,
    "65-69 anos": 2960.0,
    "70-74 anos": 2210.0,
    "75-79 anos": 1520.0,
    "80-mais": 1515.0,
}

_WEIGHTS_SUM = sum(RAW_WHO_WEIGHTS.values())
WHO_WORLD_WEIGHTS: Mapping[str, float] = {
    k: (v / _WEIGHTS_SUM) * 100000.0 for k, v in RAW_WHO_WEIGHTS.items()
}


def compute_standardized_rates(df_strata: pl.DataFrame) -> pl.DataFrame:
    """Calcula a Taxa Padronizada por Idade (ASR Direta - OMS) e SMR (Método Indireto).

    Formulação Matemática (METODOLOGIA.md §3.1):
      1. ASR_{i,c} = sum_a ( O_{i,c,a} / P_{i,a} ) * w_a
      2. R_{c,a} = sum_i(O_{i,c,a}) / sum_i(P_{i,a})  [Taxa padrão nacional de referência]
      3. E_{i,c} = sum_a P_{i,a} * R_{c,a}             [Óbitos esperados na população municipal]
      4. SMR_{i,c} = O_{i,c} / E_{i,c}                 [Razão de Mortalidade Padronizada]
    """
    required_cols = {"id_municipio", "ano", "target_cancer", "grupo_idade", "populacao", "obitos"}
    if not required_cols.issubset(set(df_strata.columns)):
        missing = required_cols - set(df_strata.columns)
        raise ValueError(f"Colunas ausentes no cálculo de ASR/SMR: {missing}")

    # 1. Mapeia pesos da OMS para a faixa etária
    weights_df = pl.DataFrame({
        "grupo_idade": list(WHO_WORLD_WEIGHTS.keys()),
        "peso_oms": list(WHO_WORLD_WEIGHTS.values()),
    })
    df_calc = df_strata.join(weights_df, on="grupo_idade", how="left").with_columns(
        pl.col("peso_oms").fill_null(0.0)
    )

    # 2. Taxa de mortalidade específica da faixa etária (por habitante)
    df_calc = df_calc.with_columns(
        pl.when(pl.col("populacao") > 0)
        .then(pl.col("obitos") / pl.col("populacao"))
        .otherwise(0.0)
        .alias("taxa_etaria")
    )

    # Componente de ASR por faixa etária
    df_calc = df_calc.with_columns(
        (pl.col("taxa_etaria") * pl.col("peso_oms")).alias("asr_componente")
    )

    # 3. Cálculo da Taxa Padrão Nacional R_{c,a} para cálculo da SMR
    national_ref = (
        df_calc.group_by(["ano", "target_cancer", "grupo_idade"])
        .agg([
            pl.col("obitos").sum().alias("nat_obitos"),
            pl.col("populacao").sum().alias("nat_pop"),
        ])
        .with_columns(
            pl.when(pl.col("nat_pop") > 0)
            .then(pl.col("nat_obitos") / pl.col("nat_pop"))
            .otherwise(0.0)
            .alias("taxa_nacional_ref")
        )
        .select(["ano", "target_cancer", "grupo_idade", "taxa_nacional_ref"])
    )

    df_calc = df_calc.join(
        national_ref, on=["ano", "target_cancer", "grupo_idade"], how="left"
    ).with_columns(
        (pl.col("populacao") * pl.col("taxa_nacional_ref")).alias("obitos_esperados_a")
    )

    # 4. Agregação no nível municipal (id_municipio, ano, target_cancer)
    aggregated = (
        df_calc.group_by(["id_municipio", "ano", "target_cancer"])
        .agg([
            pl.col("obitos").sum().alias("obitos_totais"),
            pl.col("populacao").sum().alias("populacao_total"),
            pl.col("asr_componente").sum().round(4).alias("asr_omsworld_100k"),
            pl.col("obitos_esperados_a").sum().round(4).alias("obitos_esperados_smr"),
        ])
        .with_columns(
            pl.when(pl.col("obitos_esperados_smr") > 0)
            .then(pl.col("obitos_totais") / pl.col("obitos_esperados_smr"))
            .otherwise(1.0)
            .round(4)
            .alias("smr_razao")
        )
        .sort(["id_municipio", "ano", "target_cancer"])
    )

    return aggregated
