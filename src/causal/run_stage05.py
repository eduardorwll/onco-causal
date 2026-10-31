# src/causal/run_stage05.py
"""Orquestrador Integrado do Stage 05 — Inferência Causal, Refutação, Contrafactual e IDV."""

from __future__ import annotations

import logging
import time

import polars as pl

from src.causal.counterfactual_and_idv import CounterfactualAndIDVEngine
from src.causal.dag import build_epidemiological_dag, validate_causal_identification
from src.causal.dml_estimator import SpatialDoubleMLPLR
from src.causal.refutation import CausalRefutationBattery
from src.core.settings import DomainSpec, EnvSettings

logger = logging.getLogger("onco_causal.run_stage05")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


def run_pipeline() -> None:
    """Executa o pipeline completo do Stage 05 em sequência determinística."""
    t0 = time.time()
    logger.info("=" * 80)
    logger.info("INICIANDO STAGE 05: INFERÊNCIA CAUSAL SEMIPARAMÉTRICA E IDV")
    logger.info("=" * 80)

    spec = DomainSpec.from_yaml()
    env = EnvSettings()

    # Passo 1: DAG Estrutural
    logger.info("\n--- [PASSO 1/4] Grafo Acíclico Direcionado (DAG) & Identificação Causal ---")
    dag = build_epidemiological_dag()
    logger.info("DAG validado com %d nós e %d arestas.", len(dag.nodes), len(dag.edges))
    panel_path = env.features_dir / "master_analytical_panel.parquet"
    if panel_path.exists():
        df_panel = pl.read_parquet(panel_path)
        sub_hemato = df_panel.filter(pl.col("target_cancer") == "hematologico_infantojuvenil")
        dag_result = validate_causal_identification(
            sub_hemato, spec.causal.exposures.agro, "smr_suavizada_eb"
        )
        logger.info("Conjunto backdoor validado pelo DoWhy: %s", dag_result["backdoor_variables"])

    # Passo 2: DML PLR com Neyman Orthogonalization e Experimento de Viés de Detecção
    logger.info("\n--- [PASSO 2/4] Estimação Semiparamétrica DML PLR & Viés de Detecção ---")
    estimator = SpatialDoubleMLPLR(spec=spec, env=env)
    df_est, df_bias = estimator.run()
    logger.info("Estimativas causais e experimento de viés persistidos.")

    # Passo 3: Bateria de Refutação Científica
    logger.info("\n--- [PASSO 3/4] Bateria de Refutação Científica (Placebo, Noise, Subsets) ---")
    battery = CausalRefutationBattery(spec=spec, env=env)
    df_ref = battery.run()
    logger.info("Bateria de refutação finalizada com sucesso.")

    # Passo 4: Simulador Contrafactual e IDV
    logger.info("\n--- [PASSO 4/4] Simulador Contrafactual e Silent Hotspots (IDV) ---")
    cf_engine = CounterfactualAndIDVEngine(spec=spec, env=env)
    df_sim, df_idv = cf_engine.run()
    logger.info("Simulações contrafactuais e índice IDV finalizados.")

    elapsed = time.time() - t0
    logger.info("=" * 80)
    logger.info("STAGE 05 CONCLUÍDO COM EXCELÊNCIA EM %.2f SEGUNDOS", elapsed)
    logger.info("=" * 80)

    # Exibição do Sumário Executivo
    print("\n" + "=" * 90)
    print("           RELATÓRIO CONSOLIDADO DE FECHAMENTO — STAGE 05           ")
    print("=" * 90)

    print("\n1. ESTIMATIVAS CAUSAIS DML (NEURÔNIO PLR / ROBINSON 1988):")
    print(df_est.select([
        "target_cancer", "exposure_variable", "theta_dml", "se_cluster", "p_value", "iqr_ate", "status"
    ]))

    print("\n2. EXPERIMENTO DO VIÉS DE DETECÇÃO (COMPROVAÇÃO EMPÍRICA DA HIPÓTESE H3):")
    print(df_bias.select([
        "target_cancer", "exposure_variable", "theta_naive", "theta_dml", "delta_pct", "detection_bias_proven"
    ]))

    print("\n3. BATERIA DE REFUTAÇÃO CIENTÍFICA (PLACEBO, COMMON CAUSE, DATA SUBSET):")
    passed_counts = df_ref.group_by("test_type").agg([
        pl.col("passed").sum().alias("passed_tests"),
        pl.len().alias("total_tests"),
    ])
    print(passed_counts)

    print("\n4. SIMULADOR CONTRAFACTUAL DE POLÍTICAS PÚBLICAS (TRIÊNIO 2020-2022):")
    sim_summary = df_sim.group_by("cenario").agg([
        pl.col("obitos_evitaveis").sum().round(1).alias("total_obitos_evitaveis"),
        pl.col("obitos_observados").sum().alias("total_obitos_observados"),
    ]).with_columns([
        ((pl.col("total_obitos_evitaveis") / pl.col("total_obitos_observados")) * 100.0).round(2).alias("pct_evitaveis")
    ])
    print(sim_summary)

    print("\n5. TOP 15 PONTOS CEGOS DE VIGILÂNCIA ONCO-AMBIENTAL (SILENT HOTSPOTS - IDV):")
    top15 = df_idv.sort("idv_score", descending=True).head(15)
    print(top15.select([
        "id_municipio", "nome_municipio", "sigla_uf", "populacao_estimada", "idv_score",
        "idv_percentile", "unacon_cacon_ativos", "risk_category"
    ]))
    print("=" * 90 + "\n")


def main() -> None:
    run_pipeline()


if __name__ == "__main__":
    main()
