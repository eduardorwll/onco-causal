# src/models/benchmark_runner.py
"""Motor de Validação Cruzada 5-Fold Nested SBCV e Benchmark Multi-Paradigma (Stage 04C).

Implementa:
- Paradigma 1 (Foundation In-Context Learning): TabPFNRegressor.
- Paradigma 2 (Deep Learning Interpretável): TabNetRegressor (pytorch-tabnet).
- Paradigma 3 (GBDTs Otimizados): LightGBMRegressor e XGBoostRegressor.
- Salvaguarda 3: Isolamento estrito da Dead-Zone de 30 km (0 linhas buffer_exclusion em treino/teste/val/scaler).
- Persistência e validação por contrato das predições OOF e métricas comparativas.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.preprocessing import StandardScaler

from src.core.contracts import BENCHMARK_PREDICTIONS_CONTRACT
from src.core.lineage import LineageTracker

logger = logging.getLogger("onco_causal.models.benchmark")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Features utilizadas na modelagem
FEATURE_COLUMNS = [
    "prop_lavouras_criticas_mean",
    "prop_lavouras_criticas_trend",
    "prop_floresta_mean",
    "prop_urbanizada_mean",
    "prop_linach_mean",
    "prop_linach_trend",
    "unacon_cacon_ativos",
    "leitos_pc_100k",
    "tomografos_pc_100k",
    "mamografos_pc_100k",
    "indice_atendimento_total_agua",
    "indice_coleta_esgoto",
    "indice_tratamento_esgoto",
]


def run_benchmark(
    data_dir: Path | str | None = None,
    output_dir: Path | str | None = None,
    manifest_path: Path | str | None = None,
    tabpfn_max_support: int = 250,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Executa o benchmark completo de 5-Fold SBCV avaliando os 3 paradigmas de modelagem."""
    base_dir = Path(data_dir) if data_dir else Path("data")
    feat_dir = Path(output_dir) if output_dir else base_dir / "features"
    stag_dir = base_dir / "staging"
    feat_dir.mkdir(parents=True, exist_ok=True)

    panel_path = feat_dir / "master_analytical_panel.parquet"
    cv_path = stag_dir / "spatial_cv_folds.parquet"
    mnf_path = Path(manifest_path) if manifest_path else stag_dir / "manifest.json"

    logger.info("--- Iniciando Stage 04C: Benchmark Preditivo Multi-Paradigma ---")
    panel = pl.read_parquet(panel_path)
    cv = pl.read_parquet(cv_path)

    folds = sorted(cv["fold_id"].unique().to_list())
    logger.info("Folds detectados: %s na coorte analítica (%d linhas no painel)", folds, panel.height)

    # Import lazy dos modelos para otimizar tempo de carga
    import lightgbm as lgb
    import xgboost as xgb
    from pytorch_tabnet.tab_model import TabNetRegressor
    from tabpfn import TabPFNRegressor

    model_names = ["LightGBM", "XGBoost", "TabNet", "TabPFN"]
    all_oof_predictions: list[dict[str, Any]] = []

    for fold_k in folds:
        logger.info("=== Executando Fold %d / %d ===", fold_k, len(folds) - 1)
        f_info = cv.filter(pl.col("fold_id") == fold_k)

        # Salvaguarda 3: Isolamento estrito da Dead-Zone
        train_muns = f_info.filter(pl.col("split_role") == "train")["id_municipio"].to_list()
        test_muns = f_info.filter(pl.col("split_role") == "test")["id_municipio"].to_list()
        buff_muns = f_info.filter(pl.col("split_role") == "buffer_exclusion")["id_municipio"].to_list()

        logger.info(
            "Fold %d: %d municípios treino (>30km), %d teste, %d buffer_exclusion descartados",
            fold_k,
            len(train_muns),
            len(test_muns),
            len(buff_muns),
        )

        df_train = panel.filter(pl.col("id_municipio").is_in(train_muns))
        df_test = panel.filter(pl.col("id_municipio").is_in(test_muns))

        # Garantia de zero vazamento: verificar que nenhum município do buffer está no treino ou teste
        overlap_train_buff = set(train_muns).intersection(set(buff_muns))
        overlap_test_buff = set(test_muns).intersection(set(buff_muns))
        if overlap_train_buff or overlap_test_buff:
            raise ValueError(f"Violação de dead-zone no Fold {fold_k}: municípios de buffer no treino/teste!")

        # Extrair matrizes de features e desfecho
        x_tr_raw = df_train.select(FEATURE_COLUMNS).to_numpy()
        y_tr = df_train["smr_suavizada_eb"].to_numpy()

        x_te_raw = df_test.select(FEATURE_COLUMNS).to_numpy()
        y_te = df_test["smr_suavizada_eb"].to_numpy()

        # Ajuste de pré-processamento estritamente no conjunto de treino limpo
        scaler = StandardScaler().fit(x_tr_raw)
        x_tr = scaler.transform(x_tr_raw)
        x_te = scaler.transform(x_te_raw)

        test_records = df_test.select(["id_municipio", "ano", "target_cancer"]).to_dicts()

        # 1. Paradigma 3A: LightGBM
        m_lgb = lgb.LGBMRegressor(n_estimators=150, learning_rate=0.05, random_state=42 + fold_k, verbose=-1)
        m_lgb.fit(x_tr, y_tr)
        pred_lgb = m_lgb.predict(x_te)

        # 2. Paradigma 3B: XGBoost
        m_xgb = xgb.XGBRegressor(
            n_estimators=150, learning_rate=0.05, max_depth=4, random_state=42 + fold_k, verbosity=0
        )
        m_xgb.fit(x_tr, y_tr)
        pred_xgb = m_xgb.predict(x_te)

        # 3. Paradigma 2: TabNet (Deep Learning com atenção esparsa)
        m_tabnet = TabNetRegressor(seed=42 + fold_k, verbose=0)
        m_tabnet.fit(
            x_tr.astype(np.float32),
            y_tr.reshape(-1, 1).astype(np.float32),
            max_epochs=20,
            batch_size=256,
        )
        pred_tabnet = m_tabnet.predict(x_te.astype(np.float32)).flatten()

        # 4. Paradigma 1: Foundation TabPFN (In-Context Learning zero-shot)
        rng = np.random.RandomState(42 + fold_k)
        sub_size = min(tabpfn_max_support, len(x_tr))
        idx_sub = rng.choice(len(x_tr), sub_size, replace=False)
        m_tabpfn = TabPFNRegressor(model_path="tabpfn-v2-regressor.ckpt", device="cpu", n_estimators=1)
        m_tabpfn.fit(x_tr[idx_sub], y_tr[idx_sub])
        pred_tabpfn = m_tabpfn.predict(x_te)

        # Registrar predições OOF de cada modelo
        preds_dict = {
            "LightGBM": pred_lgb,
            "XGBoost": pred_xgb,
            "TabNet": pred_tabnet,
            "TabPFN": pred_tabpfn,
        }

        for m_name, preds in preds_dict.items():
            for rec, y_val, p_val in zip(test_records, y_te, preds, strict=False):
                p_float = float(p_val)
                y_float = float(y_val)
                all_oof_predictions.append({
                    "id_municipio": str(rec["id_municipio"]),
                    "ano": int(rec["ano"]),
                    "target_cancer": str(rec["target_cancer"]),
                    "model_name": m_name,
                    "fold_id": fold_k,
                    "y_true": y_float,
                    "y_pred": p_float,
                    "residual": float(y_float - p_float),
                })

    df_preds = pl.DataFrame(all_oof_predictions)
    logger.info("Total de predições OOF geradas: %d", df_preds.height)

    # Validação do DataContract para as predições
    logger.info("Validando contrato BENCHMARK_PREDICTIONS_CONTRACT...")
    df_preds = BENCHMARK_PREDICTIONS_CONTRACT.enforce(df_preds)
    preds_out_path = feat_dir / "benchmark_predictions.parquet"
    df_preds.write_parquet(preds_out_path, compression="zstd")
    logger.info("Predições salvas em: %s", preds_out_path)

    # Cálculo consolidado das métricas de generalização
    metrics_list: list[dict[str, Any]] = []

    # 1. Métricas Globais por Modelo
    for m_name in model_names:
        sub_m = df_preds.filter(pl.col("model_name") == m_name)
        y_true = sub_m["y_true"].to_numpy()
        y_pred = sub_m["y_pred"].to_numpy()

        r2 = float(r2_score(y_true, y_pred))
        rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
        mae = float(mean_absolute_error(y_true, y_pred))

        metrics_list.append({
            "model_name": m_name,
            "scope": "GLOBAL",
            "target_cancer": "ALL",
            "r2_score": r2,
            "rmse": rmse,
            "mae": mae,
            "n_samples": len(y_true),
        })

    # 2. Métricas por Alvo Oncológico
    cancer_targets = sorted(df_preds["target_cancer"].unique().to_list())
    for target in cancer_targets:
        for m_name in model_names:
            sub_mt = df_preds.filter((pl.col("model_name") == m_name) & (pl.col("target_cancer") == target))
            y_t = sub_mt["y_true"].to_numpy()
            y_p = sub_mt["y_pred"].to_numpy()

            r2_t = float(r2_score(y_t, y_p))
            rmse_t = float(np.sqrt(mean_squared_error(y_t, y_p)))
            mae_t = float(mean_absolute_error(y_t, y_p))

            metrics_list.append({
                "model_name": m_name,
                "scope": "BY_TARGET",
                "target_cancer": target,
                "r2_score": r2_t,
                "rmse": rmse_t,
                "mae": mae_t,
                "n_samples": len(y_t),
            })

    df_metrics = pl.DataFrame(metrics_list).sort(by=["scope", "r2_score"], descending=[False, True])
    metrics_out_path = feat_dir / "benchmark_metrics.parquet"
    df_metrics.write_parquet(metrics_out_path, compression="zstd")
    logger.info("Métricas salvas em: %s", metrics_out_path)

    # Registro de linhagem
    lineage = LineageTracker(manifest_path=mnf_path)
    lineage.record_artifact(
        artifact_name="benchmark_predictions",
        parquet_path=preds_out_path,
        df=df_preds,
        parameters={"models": model_names, "n_folds": len(folds)},
    )
    lineage.record_artifact(
        artifact_name="benchmark_metrics",
        parquet_path=metrics_out_path,
        df=df_metrics,
        parameters={"models": model_names, "n_folds": len(folds)},
    )

    logger.info("=== Ranking Global do Benchmark Multi-Paradigma ===")
    global_rank = df_metrics.filter(pl.col("scope") == "GLOBAL").select([
        "model_name",
        "r2_score",
        "rmse",
        "mae",
    ])
    for row in global_rank.iter_rows(named=True):
        logger.info(
            "Modelo: %-12s | R²: %+.4f | RMSE: %.4f | MAE: %.4f",
            row["model_name"],
            row["r2_score"],
            row["rmse"],
            row["mae"],
        )

    return df_metrics, df_preds


if __name__ == "__main__":
    run_benchmark()
