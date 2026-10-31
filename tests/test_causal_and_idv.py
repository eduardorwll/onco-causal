# tests/test_causal_and_idv.py
"""Suíte de Testes Automatizados para Inferência Causal, Refutação e IDV (Stage 05)."""

from __future__ import annotations

import numpy as np
import polars as pl
import pytest

from src.core.contracts import (
    CAUSAL_ESTIMATES_CONTRACT,
    COUNTERFACTUAL_SIMULATION_CONTRACT,
    DETECTION_BIAS_CONTRACT,
    IDV_SILENT_HOTSPOTS_CONTRACT,
    REFUTATION_RESULTS_CONTRACT,
)
from src.core.settings import EnvSettings


@pytest.fixture
def env() -> EnvSettings:
    return EnvSettings()


def test_01_neyman_orthogonalization_and_detection_bias(env: EnvSettings) -> None:
    """Teste 1: Valida que a ortogonalização de Neyman expurga o viés de detecção."""
    bias_path = env.features_dir / "detection_bias_experiment.parquet"
    assert bias_path.exists(), f"Artefato ausente: {bias_path}"

    df_bias = pl.read_parquet(bias_path)
    assert len(df_bias) > 0

    # Comprova que o viés de detecção foi comprovado para exposições ocupacionais/industriais
    linach_rows = df_bias.filter(pl.col("exposure_variable") == "prop_linach_mean")
    assert linach_rows.height > 0
    # Naive OLS deve ter sido atenuado/ajustado significativamente após controle de CNES/SNIS
    assert any(linach_rows["detection_bias_proven"].to_list())

    # Comprova que theta_dml diverge de theta_naive
    delta_pcts = [abs(x) for x in linach_rows["delta_pct"].to_list()]
    assert max(delta_pcts) > 10.0, "Ortogonalização não produziu divergência em relação ao modelo ingênuo!"


def test_02_dead_zone_isolation_in_dml(env: EnvSettings) -> None:
    """Teste 2: Comprova que exatamente 0 linhas de buffer_exclusion foram usadas no treino dos nuisances."""
    folds_path = env.staging_dir / "spatial_cv_folds.parquet"
    df_folds = pl.read_parquet(folds_path)

    for k in range(5):
        fold_k = df_folds.filter(pl.col("fold_id") == k)
        buffer_mun = fold_k.filter(pl.col("split_role") == "buffer_exclusion")
        train_mun = fold_k.filter(pl.col("split_role") == "train")
        test_mun = fold_k.filter(pl.col("split_role") == "test")

        buffer_set = set(buffer_mun["id_municipio"].to_list())
        train_set = set(train_mun["id_municipio"].to_list())
        test_set = set(test_mun["id_municipio"].to_list())

        # Disjunção absoluta
        assert len(buffer_set.intersection(train_set)) == 0, f"Vazamento de dead-zone no treino do fold {k}!"
        assert len(buffer_set.intersection(test_set)) == 0, f"Vazamento de dead-zone no teste do fold {k}!"
        assert len(train_set.intersection(test_set)) == 0, f"Vazamento entre treino e teste no fold {k}!"


def test_03_cluster_robust_inference(env: EnvSettings) -> None:
    """Teste 3: Valida cálculo de covariância sanduíche clusterizada por bacia hidrográfica."""
    est_path = env.features_dir / "causal_estimates_plr.parquet"
    assert est_path.exists()
    df_est = pl.read_parquet(est_path)

    for row in df_est.iter_rows(named=True):
        assert row["se_cluster"] > 0, f"Erro-padrão não positivo para {row['target_cancer']}"
        assert row["n_clusters"] > 100, f"Número insuficiente de clusters: {row['n_clusters']}"
        assert row["ci_lower"] < row["ci_upper"]
        assert row["iqr_ate"] >= 0.0


def test_04_refutation_battery_passed(env: EnvSettings) -> None:
    """Teste 4: Comprova aprovação nos testes formais de refutação (Placebo e Random Common Cause)."""
    ref_path = env.features_dir / "causal_refutation_results.parquet"
    assert ref_path.exists()
    df_ref = pl.read_parquet(ref_path)

    # Placebo Treatment: refutation_estimate deve estar estatisticamente indistinguível de zero (p > 0.05)
    placebo_rows = df_ref.filter(pl.col("test_type") == "placebo_treatment")
    for r in placebo_rows.iter_rows(named=True):
        assert r["refutation_p_value"] > 0.05, f"Placebo apresentou significância estatística espúria: {r}"
        assert r["passed"] is True

    # Random Common Cause para alvo primário hematológico: variação < 5%
    rcc_hemato = df_ref.filter(
        (pl.col("target_cancer") == "hematologico_infantojuvenil")
        & (pl.col("exposure_variable") == "prop_lavouras_criticas_mean")
        & (pl.col("test_type") == "random_common_cause")
    )
    assert rcc_hemato.height == 1
    assert rcc_hemato["delta_relative"][0] < 0.05, "Variação sob causa comum aleatória excedeu 5%!"
    assert rcc_hemato["passed"][0] is True


def test_05_counterfactual_physical_conservation(env: EnvSettings) -> None:
    """Teste 5: Garante conservação física e não-negatividade nos óbitos evitáveis."""
    sim_path = env.features_dir / "counterfactual_simulations.parquet"
    assert sim_path.exists()
    df_sim = pl.read_parquet(sim_path)

    # Monotonicidade e limites físicos
    delta_d = df_sim["delta_exposure"].to_numpy()
    delta_smr = df_sim["delta_smr"].to_numpy()
    o_prev = df_sim["obitos_evitaveis"].to_numpy()
    o_obs = df_sim["obitos_observados"].to_numpy()

    assert np.all(delta_d >= 0.0), "Exposição contrafactual violou não-negatividade de redução!"
    assert np.all(delta_smr >= 0.0), "Redução de SMR negativa encontrada!"
    assert np.all(o_prev >= 0.0), "Óbitos evitáveis negativos encontrados!"
    assert np.all(o_prev <= o_obs.astype(float)), "Óbitos evitáveis excederam os óbitos observados!"


def test_06_data_contracts_validation(env: EnvSettings) -> None:
    """Teste 6: Aplica enforce() em 100% dos datasets gerados no Stage 05."""
    est_df = pl.read_parquet(env.features_dir / "causal_estimates_plr.parquet")
    CAUSAL_ESTIMATES_CONTRACT.enforce(est_df)

    bias_df = pl.read_parquet(env.features_dir / "detection_bias_experiment.parquet")
    DETECTION_BIAS_CONTRACT.enforce(bias_df)

    ref_df = pl.read_parquet(env.features_dir / "causal_refutation_results.parquet")
    REFUTATION_RESULTS_CONTRACT.enforce(ref_df)

    sim_df = pl.read_parquet(env.features_dir / "counterfactual_simulations.parquet")
    COUNTERFACTUAL_SIMULATION_CONTRACT.enforce(sim_df)

    idv_df = pl.read_parquet(env.features_dir / "idv_silent_hotspots.parquet")
    IDV_SILENT_HOTSPOTS_CONTRACT.enforce(idv_df)
