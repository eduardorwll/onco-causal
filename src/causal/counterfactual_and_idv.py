# src/causal/counterfactual_and_idv.py
"""Simulador Contrafactual de Óbitos Evitáveis e Índice de Divergência de Vigilância (IDV).

Implementa:
1. Motor contrafactual de políticas públicas sob dois cenários regulatórios:
   - Cenário 1: Redução de 1 IQR na exposição ambiental/química (com truncamento físico em zero).
   - Cenário 2: Adequação estrita ao limiar seguro derivado do XAI (SHAP = 0).
2. Índice de Divergência de Vigilância (IDV) para identificação dos Pontos Cegos de
   Vigilância Onco-Ambiental (Silent Hotspots) no território brasileiro.
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import polars as pl
from scipy.stats import rankdata

from src.core.contracts import (
    COUNTERFACTUAL_SIMULATION_CONTRACT,
    IDV_SILENT_HOTSPOTS_CONTRACT,
)
from src.core.lineage import LineageTracker
from src.core.settings import DomainSpec, EnvSettings

logger = logging.getLogger("onco_causal.counterfactual_and_idv")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class CounterfactualAndIDVEngine:
    """Motor analítico de simulação contrafactual e cálculo do IDV."""

    def __init__(self, spec: DomainSpec | None = None, env: EnvSettings | None = None) -> None:
        self.spec = spec or DomainSpec.from_yaml()
        self.env = env or EnvSettings()
        self.agro_col = self.spec.causal.exposures.agro
        self.linach_col = self.spec.causal.exposures.linach

    def load_data(self) -> tuple[pl.DataFrame, pl.DataFrame, pl.DataFrame]:
        """Carrega o painel mestre, estimativas causais e limiares SHAP."""
        panel_path = self.env.features_dir / "master_analytical_panel.parquet"
        est_path = self.env.features_dir / "causal_estimates_plr.parquet"
        shap_path = self.env.features_dir / "shap_inflection_thresholds.parquet"

        if not panel_path.exists():
            raise FileNotFoundError(f"Painel mestre ausente: {panel_path}")
        if not est_path.exists():
            raise FileNotFoundError(f"Estimativas causais ausentes: {est_path}")
        if not shap_path.exists():
            raise FileNotFoundError(f"Limiares SHAP ausentes: {shap_path}")

        df_panel = pl.read_parquet(panel_path)
        df_est = pl.read_parquet(est_path)
        df_shap = pl.read_parquet(shap_path)
        return df_panel, df_est, df_shap

    def simulate_counterfactuals(
        self,
        df_panel: pl.DataFrame,
        df_est: pl.DataFrame,
        df_shap: pl.DataFrame,
    ) -> pl.DataFrame:
        """Executa a simulação contrafactual nos Cenários 1 e 2 respeitando conservação física."""
        logger.info("Executando simulação contrafactual de políticas públicas...")

        # Mapeamento de thetas causais por target para a exposição agroquímica principal
        est_agro = df_est.filter(pl.col("exposure_variable") == self.agro_col)
        thetas: dict[str, float] = {
            str(t): float(val) for t, val in zip(est_agro["target_cancer"].to_list(), est_agro["theta_dml"].to_list())
        }

        # Mapeamento de limiares SHAP = 0
        shap_agro = df_shap.filter(pl.col("feature_name") == self.agro_col)
        thresholds: dict[str, float] = {
            str(t): float(val)
            for t, val in zip(shap_agro["target_cancer"].to_list(), shap_agro["inflection_threshold"].to_list())
        }
        default_threshold: float = float(thresholds.get("ALL", 0.043927))

        rows: list[dict[str, Any]] = []
        scenarios = ["cenario_1_iqr", "cenario_2_shap_threshold"]

        for target, theta in thetas.items():
            sub = df_panel.filter(pl.col("target_cancer") == target)
            d_vals = sub[self.agro_col].to_numpy()
            iqr_d = float(np.percentile(d_vals, 75) - np.percentile(d_vals, 25))
            thresh: float = float(thresholds.get(target, default_threshold))

            o_vals = sub["obitos_observados"].to_numpy()
            e_vals = sub["obitos_esperados"].to_numpy()
            smr_vals = sub["smr_suavizada_eb"].to_numpy()

            for scenario in scenarios:
                if scenario == "cenario_1_iqr":
                    # Cenário 1: Truncamento em zero D_cf = max(0, D - IQR), delta = min(D, IQR)
                    d_cf = np.maximum(0.0, d_vals - iqr_d)
                    delta_d = np.minimum(d_vals, iqr_d)
                else:
                    # Cenário 2: Adequação ao limiar seguro SHAP=0
                    d_cf = np.minimum(d_vals, thresh)
                    delta_d = np.maximum(0.0, d_vals - thresh)

                # Redução na Razão de Mortalidade Padronizada (delta SMR)
                if theta > 0:
                    delta_smr = theta * delta_d
                else:
                    delta_smr = np.zeros_like(delta_d)

                smr_cf = np.maximum(0.0, smr_vals - delta_smr)

                # Óbitos evitáveis com conservação física (Delta O >= 0 e Delta O <= O_obs)
                preventable_deaths = np.clip(delta_smr * e_vals, a_min=0.0, a_max=o_vals.astype(float))
                pct_preventable = np.where(
                    o_vals > 0,
                    (preventable_deaths / np.maximum(1.0, o_vals.astype(float))) * 100.0,
                    0.0,
                )

                sub_records = sub.select([
                    "id_municipio",
                    "ano",
                    "nome_municipio",
                    "sigla_uf",
                    "ottobacia_id",
                ]).to_dicts()

                for idx, rec in enumerate(sub_records):
                    rows.append({
                        "id_municipio": str(rec["id_municipio"]),
                        "ano": int(rec["ano"]),
                        "target_cancer": target,
                        "cenario": scenario,
                        "nome_municipio": str(rec["nome_municipio"]),
                        "sigla_uf": str(rec["sigla_uf"]),
                        "ottobacia_id": str(rec["ottobacia_id"]),
                        "exposure_variable": self.agro_col,
                        "exposure_observed": round(float(d_vals[idx]), 6),
                        "exposure_counterfactual": round(float(d_cf[idx]), 6),
                        "delta_exposure": round(float(delta_d[idx]), 6),
                        "smr_observed": round(float(smr_vals[idx]), 6),
                        "smr_counterfactual": round(float(smr_cf[idx]), 6),
                        "delta_smr": round(float(delta_smr[idx]), 6),
                        "obitos_observados": int(o_vals[idx]),
                        "obitos_esperados": round(float(e_vals[idx]), 4),
                        "obitos_evitaveis": round(float(preventable_deaths[idx]), 4),
                        "pct_obitos_evitaveis": round(float(pct_preventable[idx]), 4),
                    })

        df_sim = pl.DataFrame(rows)
        logger.info("Aplicando contrato COUNTERFACTUAL_SIMULATION_CONTRACT...")
        df_sim = COUNTERFACTUAL_SIMULATION_CONTRACT.enforce(df_sim)
        return df_sim

    def compute_idv_silent_hotspots(self, df_panel: pl.DataFrame) -> pl.DataFrame:
        """Calcula o Índice de Divergência de Vigilância (IDV) e mapeia os Silent Hotspots."""
        logger.info("Calculando Índice de Divergência de Vigilância (IDV)...")

        # Agregação municipal no triênio 2020-2022
        mun_agg = df_panel.group_by("id_municipio").agg([
            pl.col("nome_municipio").first(),
            pl.col("sigla_uf").first(),
            pl.col("ottobacia_id").first(),
            pl.col("populacao_estimada").mean().cast(pl.Int64),
            pl.col("unacon_cacon_ativos").mean().cast(pl.Int64),
            pl.col("leitos_pc_100k").mean(),
            pl.col("tomografos_pc_100k").mean(),
            pl.col("mamografos_pc_100k").mean(),
            pl.col(self.agro_col).mean(),
            pl.col(self.linach_col).mean(),
        ])

        n_mun = len(mun_agg)

        # Ranking percentil de capacidade diagnóstica (quanto maior, melhor a infraestrutura)
        r_unacon = rankdata(mun_agg["unacon_cacon_ativos"].to_numpy()) / n_mun
        r_leitos = rankdata(mun_agg["leitos_pc_100k"].to_numpy()) / n_mun
        r_tomo = rankdata(mun_agg["tomografos_pc_100k"].to_numpy()) / n_mun
        r_mamo = rankdata(mun_agg["mamografos_pc_100k"].to_numpy()) / n_mun
        rank_diag = (r_unacon + r_leitos + r_tomo + r_mamo) / 4.0

        # Ranking percentil de risco por carga química e ocupacional
        r_agro = rankdata(mun_agg[self.agro_col].to_numpy()) / n_mun
        r_linach = rankdata(mun_agg[self.linach_col].to_numpy()) / n_mun
        rank_exp = (r_agro + r_linach) / 2.0

        # Razão de divergência (IDV)
        eps = 0.05
        idv_scores = (rank_exp + 0.01) / (rank_diag + eps)
        idv_percentiles = (rankdata(idv_scores) / n_mun) * 100.0

        mun_df = mun_agg.with_columns([
            pl.Series("rank_exposure_risk", np.round(rank_exp, 4)),
            pl.Series("rank_diag_capacity", np.round(rank_diag, 4)),
            pl.Series("idv_score", np.round(idv_scores, 4)),
            pl.Series("idv_percentile", np.round(idv_percentiles, 2)),
            pl.Series("is_silent_hotspot", idv_percentiles >= 90.0),
        ])

        mun_df = mun_df.with_columns(
            pl.when((pl.col("is_silent_hotspot")) & (pl.col("unacon_cacon_ativos") == 0))
            .then(pl.lit("PONTO_CEGO_CRITICO"))
            .when(pl.col("is_silent_hotspot"))
            .then(pl.lit("PONTO_CEGO_ALTO"))
            .when(pl.col("idv_percentile") >= 40.0)
            .then(pl.lit("EQUILIBRADO"))
            .otherwise(pl.lit("BAIXO_RISCO_ALTA_COBERTURA"))
            .alias("risk_category")
        )

        logger.info("Aplicando contrato IDV_SILENT_HOTSPOTS_CONTRACT...")
        mun_df = IDV_SILENT_HOTSPOTS_CONTRACT.enforce(mun_df)
        return mun_df

    def run(self) -> tuple[pl.DataFrame, pl.DataFrame]:
        """Executa simulação contrafactual e cálculo do IDV, salvando artefatos e linhagem."""
        df_panel, df_est, df_shap = self.load_data()

        df_sim = self.simulate_counterfactuals(df_panel, df_est, df_shap)
        df_idv = self.compute_idv_silent_hotspots(df_panel)

        out_sim_path = self.env.features_dir / "counterfactual_simulations.parquet"
        out_idv_path = self.env.features_dir / "idv_silent_hotspots.parquet"

        df_sim.write_parquet(out_sim_path, compression="zstd")
        df_idv.write_parquet(out_idv_path, compression="zstd")
        logger.info("Artefatos salvos em %s e %s", out_sim_path, out_idv_path)

        tracker = LineageTracker(self.env.staging_dir / "manifest.json")
        tracker.record_artifact(
            artifact_name="counterfactual_simulations",
            parquet_path=out_sim_path,
            df=df_sim,
        )
        tracker.record_artifact(
            artifact_name="idv_silent_hotspots",
            parquet_path=out_idv_path,
            df=df_idv,
        )

        return df_sim, df_idv


def main() -> None:
    """Entry point para o simulador contrafactual e cálculo do IDV."""
    engine = CounterfactualAndIDVEngine()
    df_sim, df_idv = engine.run()

    # Sumário dos Cenários Contrafactuais
    summary = df_sim.group_by("cenario").agg([
        pl.col("obitos_evitaveis").sum().round(1).alias("total_obitos_evitaveis"),
        pl.col("obitos_observados").sum().alias("total_obitos_observados"),
    ]).with_columns([
        ((pl.col("total_obitos_evitaveis") / pl.col("total_obitos_observados")) * 100.0).round(2).alias("pct_evitaveis")
    ])
    print("\n--- Sumário de Vidas Salvas por Cenário Regulatório (Triênio 2020-2022) ---")
    print(summary)

    # Top 15 Silent Hotspots Nacionais
    top15 = df_idv.sort("idv_score", descending=True).head(15)
    print("\n--- Top 15 Silent Hotspots Nacionais (Índice de Divergência de Vigilância) ---")
    print(top15.select([
        "id_municipio", "nome_municipio", "sigla_uf", "populacao_estimada", "idv_score",
        "idv_percentile", "unacon_cacon_ativos", "risk_category"
    ]))


if __name__ == "__main__":
    main()
