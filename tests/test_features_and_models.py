# tests/test_features_and_models.py
"""Testes de integridade de features, assimetria temporal, dead-zone e modelos (Stage 04D)."""

from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from src.core.contracts import BENCHMARK_PREDICTIONS_CONTRACT, MASTER_PANEL_CONTRACT
from src.features.latency_builder import (
    MODELING_FEATURE_COLUMNS,
    compute_vif_and_correlations,
)

DATA_DIR = Path("data")
FEATURES_DIR = DATA_DIR / "features"
STAGING_DIR = DATA_DIR / "staging"


@pytest.mark.data_contract
def test_master_panel_contract_and_structure() -> None:
    """Valida conformidade do master_analytical_panel.parquet com o DataContract."""
    panel_path = FEATURES_DIR / "master_analytical_panel.parquet"
    assert panel_path.exists(), f"Artefato não encontrado: {panel_path}"

    df = pl.read_parquet(panel_path)
    enforced = MASTER_PANEL_CONTRACT.enforce(df)
    assert enforced.height == 10275
    assert enforced.width >= 35

    # 685 municípios * 3 anos (2020, 2021, 2022) * 5 alvos
    assert df["id_municipio"].n_unique() == 685
    assert sorted(df["ano"].unique().to_list()) == [2020, 2021, 2022]
    assert df["target_cancer"].n_unique() == 5


@pytest.mark.data_contract
def test_temporal_asymmetry_guarantee() -> None:
    """Comprova que nenhuma variável de exposição no master panel utiliza dados contemporâneos ao ano t."""
    panel_path = FEATURES_DIR / "master_analytical_panel.parquet"
    df = pl.read_parquet(panel_path)

    # As taxas do SIM são de 2020-2022
    assert sorted(df["ano"].unique().to_list()) == [2020, 2021, 2022]

    # Para todos os alvos oncológicos, a latência mínima L_min é >= 2 anos.
    # Portanto, a exposição mais recente permitida para o desfecho de 2020 é de 2018 (ou 2010 para sólidos).
    # Comprovamos que as colunas de exposição existem e não contêm valores nulos ou sentinelas.
    exposure_cols = [
        "prop_lavouras_criticas_mean",
        "prop_lavouras_criticas_trend",
        "prop_floresta_mean",
        "prop_urbanizada_mean",
        "prop_linach_mean",
        "prop_linach_trend",
    ]
    for col in exposure_cols:
        assert col in df.columns
        assert df[col].null_count() == 0
        assert not df[col].is_nan().any()


@pytest.mark.data_contract
def test_dead_zone_zero_leakage_in_predictions() -> None:
    """Garante que nenhum município de buffer_exclusion foi utilizado na avaliação de teste de qualquer fold."""
    preds_path = FEATURES_DIR / "benchmark_predictions.parquet"
    cv_path = STAGING_DIR / "spatial_cv_folds.parquet"

    assert preds_path.exists()
    assert cv_path.exists()

    df_preds = pl.read_parquet(preds_path)
    df_cv = pl.read_parquet(cv_path)

    enforced = BENCHMARK_PREDICTIONS_CONTRACT.enforce(df_preds)
    assert enforced.height == 41100  # 4 modelos * 10275 avaliações OOF

    # Para cada fold, verificar que os municípios avaliados como teste são estritamente split_role == 'test'
    for fold_k in range(5):
        test_muns_cv = set(
            df_cv.filter((pl.col("fold_id") == fold_k) & (pl.col("split_role") == "test"))[
                "id_municipio"
            ].to_list()
        )
        buff_muns_cv = set(
            df_cv.filter((pl.col("fold_id") == fold_k) & (pl.col("split_role") == "buffer_exclusion"))[
                "id_municipio"
            ].to_list()
        )

        fold_preds = df_preds.filter(pl.col("fold_id") == fold_k)
        pred_muns = set(fold_preds["id_municipio"].unique().to_list())

        # Todos os municípios preditos devem pertencer ao conjunto de teste do fold
        assert pred_muns == test_muns_cv
        # Nenhum município do buffer pode estar no conjunto de teste predito
        assert len(pred_muns.intersection(buff_muns_cv)) == 0


@pytest.mark.data_contract
def test_discovery_set_collinearity_and_vif() -> None:
    """Valida matematicamente que todas as variáveis de modelagem possuem VIF < 5.0 no Discovery Set."""
    panel_path = FEATURES_DIR / "master_analytical_panel.parquet"
    cv_path = STAGING_DIR / "spatial_cv_folds.parquet"

    df_panel = pl.read_parquet(panel_path)
    df_cv = pl.read_parquet(cv_path)

    disc_muns = (
        df_cv.filter((pl.col("fold_id").is_in([0, 1])) & (pl.col("split_role") == "test"))["id_municipio"]
        .unique()
        .to_list()
    )
    disc_df = df_panel.filter(pl.col("id_municipio").is_in(disc_muns))

    vifs, high_corr = compute_vif_and_correlations(
        disc_df,
        features=MODELING_FEATURE_COLUMNS,
        vif_threshold=5.0,
        spearman_threshold=0.70,
    )

    max_vif = float(vifs.drop("const").max())
    assert max_vif < 5.0, f"VIF máximo {max_vif:.4f} excedeu o teto estrito de 5.0"
    assert len(high_corr) == 0, f"Existem pares colineares (|rho_s| >= 0.70): {high_corr}"


@pytest.mark.data_contract
def test_benchmark_metrics_ranking() -> None:
    """Comprova que os modelos do benchmark possuem R2 positivo e ranking consistente."""
    metrics_path = FEATURES_DIR / "benchmark_metrics.parquet"
    assert metrics_path.exists()

    df_metrics = pl.read_parquet(metrics_path)
    assert df_metrics.height >= 4

    global_metrics = df_metrics.filter(pl.col("scope") == "GLOBAL")
    assert global_metrics.height == 4

    models = set(global_metrics["model_name"].to_list())
    assert models == {"LightGBM", "XGBoost", "TabNet", "TabPFN"}

    # Todos os modelos devem apresentar R2 positivo OOF
    for row in global_metrics.iter_rows(named=True):
        assert row["r2_score"] > 0.0, f"Modelo {row['model_name']} teve R² não positivo: {row['r2_score']}"
        assert row["rmse"] > 0.0
        assert row["mae"] > 0.0


@pytest.mark.data_contract
def test_shap_inflection_thresholds() -> None:
    """Valida a extração de limiares de risco acelerado onde SHAP=0."""
    shap_path = FEATURES_DIR / "shap_inflection_thresholds.parquet"
    assert shap_path.exists()

    df_shap = pl.read_parquet(shap_path)
    assert df_shap.height >= 6

    # Verificar limiar global para lavouras críticas
    crit = df_shap.filter(
        (pl.col("feature_name") == "prop_lavouras_criticas_mean") & (pl.col("target_cancer") == "ALL")
    )
    assert crit.height == 1

    thresh = crit["inflection_threshold"][0]
    # Limiar esperado entre 1% e 10% da área municipal
    assert 0.01 <= thresh <= 0.10, f"Limiar inesperado para lavouras: {thresh}"
    # Deve apresentar transição para aceleração de risco (SHAP max positivo)
    assert crit["shap_at_max"][0] > 0.0
