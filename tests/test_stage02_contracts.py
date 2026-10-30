# tests/test_stage02_contracts.py
from __future__ import annotations

import polars as pl
import pytest

from src.core.contracts import (
    CONTROLES_ASSISTENCIAIS_CONTRACT,
    PAM_LAVOURAS_CONTRACT,
    RAIS_LINACH_CONTRACT,
)
from src.core.settings import EnvSettings


@pytest.mark.unit
def test_rais_contract_unit_validation():
    df_valid = pl.DataFrame({
        "id_municipio": ["1100015", "3550308"],
        "ano": [2020, 2020],
        "vinculos_totais": [2500, 100000],
        "vinculos_linach": [100, 5000],
        "prop_linach": [0.04, 0.05],
    })
    enforced = RAIS_LINACH_CONTRACT.enforce(df_valid)
    assert enforced.height == 2

    # Teste de PK duplicada
    df_dup = pl.DataFrame({
        "id_municipio": ["1100015", "1100015"],
        "ano": [2020, 2020],
        "vinculos_totais": [2500, 2500],
        "vinculos_linach": [100, 100],
        "prop_linach": [0.04, 0.04],
    })
    with pytest.raises(ValueError, match="Violação de unicidade"):
        RAIS_LINACH_CONTRACT.enforce(df_dup)


@pytest.mark.unit
def test_pam_contract_unit_validation():
    df_valid = pl.DataFrame({
        "id_municipio": ["5107875"],
        "ano": [2020],
        "area_soja_ha": [100000.0],
        "area_milho_ha": [50000.0],
        "area_algodao_ha": [20000.0],
        "area_cana_ha": [0.0],
        "area_arroz_ha": [0.0],
        "area_citros_ha": [0.0],
        "area_total_lavouras_criticas_ha": [170000.0],
    })
    enforced = PAM_LAVOURAS_CONTRACT.enforce(df_valid)
    assert enforced.height == 1


@pytest.mark.unit
def test_controles_contract_unit_validation():
    df_valid = pl.DataFrame({
        "id_municipio": ["3550308"],
        "ano": [2020],
        "unacon_cacon_ativos": [19],
        "leitos_totais": [28000],
        "tomografos_ativos": [400],
        "mamografos_ativos": [400],
        "indice_atendimento_total_agua": [99.0],
        "indice_coleta_esgoto": [75.0],
        "indice_tratamento_esgoto": [100.0],
    })
    enforced = CONTROLES_ASSISTENCIAIS_CONTRACT.enforce(df_valid)
    assert enforced.height == 1


@pytest.mark.data_contract
def test_rais_staging_artifact(env: EnvSettings):
    path = env.staging_dir / "rais_linach_anual.parquet"
    if path.exists():
        df = pl.read_parquet(path)
        enforced = RAIS_LINACH_CONTRACT.enforce(df)
        assert enforced["id_municipio"].null_count() == 0
        assert enforced["ano"].null_count() == 0
        assert (enforced["prop_linach"] >= 0.0).all()


@pytest.mark.data_contract
def test_pam_staging_artifact(env: EnvSettings):
    path = env.staging_dir / "pam_lavouras_anual.parquet"
    if path.exists():
        df = pl.read_parquet(path)
        enforced = PAM_LAVOURAS_CONTRACT.enforce(df)
        assert enforced["id_municipio"].null_count() == 0
        assert enforced["ano"].null_count() == 0
        assert (enforced["area_total_lavouras_criticas_ha"] >= 0.0).all()


@pytest.mark.data_contract
def test_controles_staging_artifact(env: EnvSettings):
    path = env.staging_dir / "controles_assistenciais_snis.parquet"
    if path.exists():
        df = pl.read_parquet(path)
        enforced = CONTROLES_ASSISTENCIAIS_CONTRACT.enforce(df)
        assert enforced["id_municipio"].null_count() == 0
        assert enforced["ano"].null_count() == 0
        assert (enforced["indice_atendimento_total_agua"] >= 0.0).all()
