# src/models/run_stage04.py
"""Orquestrador CLI Unificado do Stage 04 (Engenharia de Lags, Benchmark Preditivo e XAI).

Executa sequencialmente:
1. Stage 04B: Engenharia de Lags Biológicos e Painel Analítico Mestre (latency_builder).
2. Stage 04C: Benchmark 5-Fold SBCV Multi-Paradigma TabFM/TabNet/GBDT (benchmark_runner).
3. Stage 04C: Explicabilidade TreeSHAP e Limiares Toxicológicos SHAP=0 (xai_shap).
"""

from __future__ import annotations

import logging
import time

import polars as pl

from src.features.latency_builder import build_master_panel
from src.models.benchmark_runner import run_benchmark
from src.models.xai_shap import compute_shap_thresholds

logger = logging.getLogger("onco_causal.stage04")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def run_stage04() -> None:
    """Entrypoint principal do pipeline do Stage 04."""
    start_time = time.perf_counter()
    logger.info("======================================================================")
    logger.info("INICIANDO STAGE 04: DISTRIBUTED LAGS, BENCHMARK MULTI-PARADIGMA E XAI")
    logger.info("======================================================================")

    # Passo 1: Construção do Painel Mestre
    logger.info("\n>>> PASSO 1/3: Construção do Painel Analítico Mestre com Lags...")
    df_panel = build_master_panel()
    logger.info("Painel Mestre concluído: %d linhas, %d colunas.", df_panel.height, df_panel.width)

    # Passo 2: Benchmark 5-Fold SBCV
    logger.info("\n>>> PASSO 2/3: Executando Benchmark 5-Fold SBCV nos 3 Paradigmas...")
    df_metrics, df_preds = run_benchmark()
    logger.info(
        "Benchmark concluído: %d predições OOF geradas em 5 folds disjuntos.",
        df_preds.height,
    )

    # Passo 3: TreeSHAP e Limiares Toxicológicos
    logger.info("\n>>> PASSO 3/3: Computando TreeSHAP e Limiares SHAP=0...")
    df_shap = compute_shap_thresholds()
    logger.info("Limiares SHAP=0 computados: %d registros.", df_shap.height)

    elapsed = time.perf_counter() - start_time
    logger.info("\n======================================================================")
    logger.info("STAGE 04 CONCLUÍDO COM SUCESSO EM %.2f SEGUNDOS", elapsed)
    logger.info("======================================================================")

    # Exibição dos Relatórios Consolidados no Console
    print("\n" + "=" * 80)
    print("📊 TABELA 1: RANKING GLOBAL DO BENCHMARK PREDITIVO (5-FOLD NESTED SBCV)")
    print("=" * 80)
    global_metrics = df_metrics.filter(pl.col("scope") == "GLOBAL").select([
        "model_name",
        "r2_score",
        "rmse",
        "mae",
        "n_samples",
    ])
    for row in global_metrics.iter_rows(named=True):
        print(
            f"  • {row['model_name']:<12} | R²: {row['r2_score']:+.4f} | "
            f"RMSE: {row['rmse']:.4f} | MAE: {row['mae']:.4f} | N: {row['n_samples']}"
        )

    print("\n" + "=" * 80)
    print("🔬 TABELA 2: LIMIARES TOXICOLÓGICOS DE INFLEXÃO (SHAP = 0)")
    print("=" * 80)
    crit_thresholds = df_shap.filter(
        pl.col("feature_name").is_in(["prop_lavouras_criticas_mean", "prop_linach_mean"])
    ).select([
        "feature_name",
        "target_cancer",
        "inflection_threshold",
        "shap_at_min",
        "shap_at_max",
        "mean_abs_shap",
    ])
    for row in crit_thresholds.iter_rows(named=True):
        feat = "Vetor D1 (Agrotóxicos)" if "lavouras" in row["feature_name"] else "Vetor D4 (LINACH)"
        print(
            f"  • [{feat:<22}] {row['target_cancer']:<30} | "
            f"Limiar: {row['inflection_threshold']:.4f} | "
            f"SHAP: [{row['shap_at_min']:+.4f} -> {row['shap_at_max']:+.4f}]"
        )
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_stage04()
