# tests/test_age_standardization.py
from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from src.core.contracts import SIM_MORTALIDADE_CONTRACT
from src.spatial.age_standardization import (
    WHO_WORLD_WEIGHTS,
    compute_standardized_rates,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent


@pytest.mark.unit
def test_compute_standardized_rates_math():
    """Valida a precisão matemática do cálculo direto de ASR e indireto de SMR."""
    # Município 1 e Município 2 com 2 faixas etárias
    df_synthetic = pl.DataFrame({
        "id_municipio": ["1100015", "1100015", "1100023", "1100023"],
        "ano": [2020, 2020, 2020, 2020],
        "target_cancer": ["respiratorio", "respiratorio", "respiratorio", "respiratorio"],
        "grupo_idade": ["0-4 anos", "80-mais", "0-4 anos", "80-mais"],
        "populacao": [1000, 500, 2000, 1000],
        "obitos": [2, 5, 4, 10],
    })

    df_rates = compute_standardized_rates(df_synthetic)
    assert df_rates.height == 2
    assert "asr_omsworld_100k" in df_rates.columns
    assert "smr_razao" in df_rates.columns

    # As taxas específicas são idênticas nos dois municípios:
    # 0-4 anos: 2/1000 = 4/2000 = 0.002
    # 80-mais: 5/500 = 10/1000 = 0.010
    # Portanto, a taxa nacional de referência é exatamente igual à taxa de cada município,
    # resultando em SMR = 1.0 para ambos.
    smr_vals = df_rates["smr_razao"].to_list()
    for s in smr_vals:
        assert pytest.approx(s, rel=1e-3) == 1.0

    # ASR esperada: 0.002 * w_0_4 + 0.010 * w_80
    expected_asr = (0.002 * WHO_WORLD_WEIGHTS["0-4 anos"]) + (
        0.010 * WHO_WORLD_WEIGHTS["80-mais"]
    )
    for asr in df_rates["asr_omsworld_100k"].to_list():
        assert pytest.approx(asr, rel=1e-3) == round(expected_asr, 4)


@pytest.mark.unit
def test_compute_standardized_rates_zero_deaths():
    """Valida que municípios sem óbitos possuem ASR = 0.0 e SMR = 0.0."""
    df_synthetic = pl.DataFrame({
        "id_municipio": ["1100015", "1100023"],
        "ano": [2020, 2020],
        "target_cancer": ["pele_melanoma", "pele_melanoma"],
        "grupo_idade": ["0-4 anos", "0-4 anos"],
        "populacao": [1000, 2000],
        "obitos": [0, 4],  # M1 tem 0 óbitos, M2 tem 4
    })

    df_rates = compute_standardized_rates(df_synthetic)
    m1 = df_rates.filter(pl.col("id_municipio") == "1100015")
    assert m1["obitos_totais"][0] == 0
    assert m1["asr_omsworld_100k"][0] == 0.0
    assert m1["smr_razao"][0] == 0.0


@pytest.mark.unit
def test_compute_standardized_rates_missing_cols():
    """Valida que ausência de colunas obrigatórias levanta ValueError."""
    df_bad = pl.DataFrame({
        "id_municipio": ["1100015"],
        "ano": [2020],
    })
    with pytest.raises(ValueError, match="Colunas ausentes"):
        compute_standardized_rates(df_bad)


@pytest.mark.data_contract
def test_sim_staging_parquet_contract():
    """Validação estrita do artefato gerado data/staging/sim_taxas_padronizadas_5570.parquet."""
    parquet_path = PROJECT_ROOT / "data" / "staging" / "sim_taxas_padronizadas_5570.parquet"
    if not parquet_path.exists():
        pytest.skip(f"Artefato {parquet_path} ainda não foi gerado.")

    df = pl.read_parquet(parquet_path)
    enforced = SIM_MORTALIDADE_CONTRACT.enforce(df)

    assert enforced.height > 0
    # 5.570 municípios presentes
    assert enforced["id_municipio"].n_unique() == 5570
    # 5 alvos oncológicos
    assert enforced["target_cancer"].n_unique() == 5
    # Taxas padronizadas não negativas
    assert (enforced["asr_omsworld_100k"] >= 0.0).all()
    assert (enforced["smr_razao"] >= 0.0).all()
