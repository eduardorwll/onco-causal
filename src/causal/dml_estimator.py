# src/causal/dml_estimator.py
"""Inferência Causal Semiparamétrica via Double Machine Learning (DML) e PLR.

Implementa o estimador Partially Linear Regression (PLR) de Robinson (1988) com
dupla robustez (Neyman Orthogonalization), Spatial Cross-Fitting em 5 folds com
isolamento estrito de dead-zone (< 30 km) e erros-padrão clusterizados por bacia
hidrográfica (ottobacia_id).
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import polars as pl
import statsmodels.api as sm
from lightgbm import LGBMRegressor

from src.core.contracts import CAUSAL_ESTIMATES_CONTRACT, DETECTION_BIAS_CONTRACT
from src.core.lineage import LineageTracker
from src.core.settings import DomainSpec, EnvSettings

logger = logging.getLogger("onco_causal.dml_estimator")
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")


class SpatialDoubleMLPLR:
    """Estimador Semiparamétrico DML PLR com Spatial Cross-Fitting e Dead-Zone Isolation."""

    def __init__(self, spec: DomainSpec | None = None, env: EnvSettings | None = None) -> None:
        self.spec = spec or DomainSpec.from_yaml()
        self.env = env or EnvSettings()
        self.confounders = self.spec.causal.confounders.all_confounders
        self.agro_col = self.spec.causal.exposures.agro
        self.linach_col = self.spec.causal.exposures.linach
        self.cluster_col = self.spec.causal.cluster_col

    def load_data(self) -> tuple[pl.DataFrame, pl.DataFrame]:
        """Carrega o painel analítico mestre e as partições espaciais."""
        panel_path = self.env.features_dir / "master_analytical_panel.parquet"
        folds_path = self.env.staging_dir / "spatial_cv_folds.parquet"

        if not panel_path.exists():
            raise FileNotFoundError(f"Painel mestre não encontrado em {panel_path}")
        if not folds_path.exists():
            raise FileNotFoundError(f"Partições espaciais não encontradas em {folds_path}")

        df_panel = pl.read_parquet(panel_path)
        df_folds = pl.read_parquet(folds_path)
        return df_panel, df_folds

    def estimate_target(
        self,
        target_cancer: str,
        df_target: pl.DataFrame,
        df_folds: pl.DataFrame,
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Executa a estimação causal DML para um alvo oncológico específico."""
        logger.info("Iniciando DML PLR para o alvo: %s (N=%d)", target_cancer, len(df_target))

        estimates: list[dict[str, Any]] = []
        bias_experiments: list[dict[str, Any]] = []

        exposures_to_eval = [
            (self.agro_col, self.linach_col, "Exposição Agroquímica (Lavouras Críticas)"),
            (self.linach_col, self.agro_col, "Exposição Ocupacional LINACH (Benzeno/Química)"),
        ]

        for exp_name, co_exp_name, desc in exposures_to_eval:
            all_y_test: list[np.ndarray] = []
            all_g_hat: list[np.ndarray] = []
            all_d_test: list[np.ndarray] = []
            all_m_hat: list[np.ndarray] = []
            all_clusters: list[np.ndarray] = []
            all_unacon: list[np.ndarray] = []
            all_agua: list[np.ndarray] = []

            # 5-Fold Spatial Cross-Fitting
            for k in range(5):
                fold_k = df_folds.filter(pl.col("fold_id") == k).select(["id_municipio", "split_role"])
                sub_k = df_target.join(fold_k, on="id_municipio", how="inner")

                train_df = sub_k.filter(pl.col("split_role") == "train")
                test_df = sub_k.filter(pl.col("split_role") == "test")
                # Buffer exclusion rows (< 30km) são estritamente excluídas do treinamento

                X_cols = self.confounders + [co_exp_name]
                X_train = train_df.select(X_cols).to_pandas().values
                X_test = test_df.select(X_cols).to_pandas().values

                y_train = train_df["smr_suavizada_eb"].to_numpy()
                y_test = test_df["smr_suavizada_eb"].to_numpy()

                d_train = train_df[exp_name].to_numpy()
                d_test = test_df[exp_name].to_numpy()

                # Ajuste de funções nuisance g(Z, co_d) para desfecho
                g_model = LGBMRegressor(
                    n_estimators=100,
                    max_depth=3,
                    learning_rate=0.05,
                    random_state=42 + k,
                    verbose=-1,
                )
                g_model.fit(X_train, y_train)
                g_pred = np.asarray(g_model.predict(X_test), dtype=np.float64)

                # Ajuste de funções nuisance m(Z, co_d) para exposição (propensão)
                m_model = LGBMRegressor(
                    n_estimators=100,
                    max_depth=3,
                    learning_rate=0.05,
                    random_state=42 + k,
                    verbose=-1,
                )
                m_model.fit(X_train, d_train)
                m_pred = np.asarray(m_model.predict(X_test), dtype=np.float64)

                all_y_test.append(y_test)
                all_g_hat.append(g_pred)
                all_d_test.append(d_test)
                all_m_hat.append(m_pred)
                all_clusters.append(test_df[self.cluster_col].to_numpy())
                all_unacon.append(test_df["unacon_cacon_ativos"].to_numpy())
                all_agua.append(test_df["indice_atendimento_total_agua"].to_numpy())

            y_arr = np.concatenate(all_y_test)
            g_arr = np.concatenate(all_g_hat)
            d_arr = np.concatenate(all_d_test)
            m_arr = np.concatenate(all_m_hat)
            clusters_arr = np.concatenate(all_clusters)
            unacon_arr = np.concatenate(all_unacon)
            agua_arr = np.concatenate(all_agua)

            # Resíduos de Neyman Ortogonalizados
            y_res = y_arr - g_arr
            d_res = d_arr - m_arr

            # Estimação Causal Neyman PLR com Erros Clusterizados
            X_plr = sm.add_constant(d_res)
            ols_plr = sm.OLS(y_res, X_plr).fit(cov_type="cluster", cov_kwds={"groups": clusters_arr})

            theta = float(ols_plr.params[1])
            se = float(ols_plr.bse[1])
            t_stat = float(ols_plr.tvalues[1])
            pval = float(ols_plr.pvalues[1])
            ci_lower = theta - 1.96 * se
            ci_upper = theta + 1.96 * se

            # Impacto padronizado: IQR-ATE
            iqr_d = float(np.percentile(d_arr, 75) - np.percentile(d_arr, 25))
            mean_y = float(np.mean(y_arr))
            iqr_ate = (abs(theta) / max(1e-5, mean_y)) * iqr_d

            status = "SIGNIFICANT_P05" if pval < 0.05 else "NOT_SIGNIFICANT"

            # Modelo CATE: Heterogeneidade por vulnerabilidade socioassistencial
            sem_unacon = (unacon_arr == 0).astype(float)
            deficit_agua = (agua_arr < np.median(agua_arr)).astype(float)
            X_cate = np.column_stack([d_res, d_res * sem_unacon, d_res * deficit_agua])
            X_cate = sm.add_constant(X_cate)
            ols_cate = sm.OLS(y_res, X_cate).fit(cov_type="cluster", cov_kwds={"groups": clusters_arr})

            gamma_sem_unacon = float(ols_cate.params[2])
            pval_sem_unacon = float(ols_cate.pvalues[2])
            gamma_deficit_agua = float(ols_cate.params[3])
            pval_deficit_agua = float(ols_cate.pvalues[3])

            estimates.append({
                "target_cancer": target_cancer,
                "exposure_variable": exp_name,
                "theta_dml": round(theta, 6),
                "se_cluster": round(se, 6),
                "t_stat": round(t_stat, 4),
                "p_value": round(pval, 8),
                "ci_lower": round(ci_lower, 6),
                "ci_upper": round(ci_upper, 6),
                "iqr_ate": round(iqr_ate, 6),
                "gamma_sem_unacon": round(gamma_sem_unacon, 6),
                "p_value_sem_unacon": round(pval_sem_unacon, 8),
                "gamma_deficit_saneamento": round(gamma_deficit_agua, 6),
                "p_value_deficit_saneamento": round(pval_deficit_agua, 8),
                "n_obs": len(y_arr),
                "n_clusters": len(np.unique(clusters_arr)),
                "status": status,
            })

            # Modelo Ingênuo (sem controle de viés de detecção / assistencial)
            ols_naive = sm.OLS(y_arr, sm.add_constant(d_arr)).fit(
                cov_type="cluster", cov_kwds={"groups": clusters_arr}
            )
            theta_naive = float(ols_naive.params[1])
            se_naive = float(ols_naive.bse[1])
            pval_naive = float(ols_naive.pvalues[1])

            delta_pct = ((theta - theta_naive) / max(1e-5, abs(theta_naive))) * 100.0
            proven = abs(delta_pct) >= 5.0 or (pval < 0.05 and pval_naive >= 0.05)
            summary_msg = (
                f"Controle assistencial/sanitário ajustou o efeito em {delta_pct:+.1f}%. "
                f"Naive: {theta_naive:.4f} (p={pval_naive:.3e}) -> DML: {theta:.4f} (p={pval:.3e})"
            )

            bias_experiments.append({
                "target_cancer": target_cancer,
                "exposure_variable": exp_name,
                "theta_naive": round(theta_naive, 6),
                "se_naive": round(se_naive, 6),
                "p_value_naive": round(pval_naive, 8),
                "theta_dml": round(theta, 6),
                "se_dml": round(se, 6),
                "p_value_dml": round(pval, 8),
                "delta_pct": round(delta_pct, 4),
                "detection_bias_proven": bool(proven),
                "mechanism_summary": summary_msg,
            })

            logger.info(
                "[%s | %s] DML theta=%.4f (se=%.4f, p=%.3e) | Naive theta=%.4f (p=%.3e) | IQR-ATE=%.4f",
                target_cancer,
                exp_name,
                theta,
                se,
                pval,
                theta_naive,
                pval_naive,
                iqr_ate,
            )

        return estimates, bias_experiments

    def run(self) -> tuple[pl.DataFrame, pl.DataFrame]:
        """Executa a estimação DML e experimento de viés para todos os alvos oncológicos."""
        logger.info("Carregando datasets para estimação causal...")
        df_panel, df_folds = self.load_data()

        targets = self.spec.oncology_targets.keys()
        all_estimates: list[dict[str, Any]] = []
        all_bias: list[dict[str, Any]] = []

        for target in targets:
            df_tgt = df_panel.filter(pl.col("target_cancer") == target)
            tgt_estimates, tgt_bias = self.estimate_target(target, df_tgt, df_folds)
            all_estimates.extend(tgt_estimates)
            all_bias.extend(tgt_bias)

        df_res_estimates = pl.DataFrame(all_estimates)
        df_res_bias = pl.DataFrame(all_bias)

        # Aplicar contratos de dados
        logger.info("Aplicando contratos de dados...")
        df_res_estimates = CAUSAL_ESTIMATES_CONTRACT.enforce(df_res_estimates)
        df_res_bias = DETECTION_BIAS_CONTRACT.enforce(df_res_bias)

        out_estimates_path = self.env.features_dir / "causal_estimates_plr.parquet"
        out_bias_path = self.env.features_dir / "detection_bias_experiment.parquet"

        df_res_estimates.write_parquet(out_estimates_path, compression="zstd")
        df_res_bias.write_parquet(out_bias_path, compression="zstd")
        logger.info("Artefatos salvos em %s e %s", out_estimates_path, out_bias_path)

        # Registrar no manifesto
        tracker = LineageTracker(self.env.staging_dir / "manifest.json")
        tracker.record_artifact(
            artifact_name="causal_estimates_plr",
            parquet_path=out_estimates_path,
            df=df_res_estimates,
        )
        tracker.record_artifact(
            artifact_name="detection_bias_experiment",
            parquet_path=out_bias_path,
            df=df_res_bias,
        )

        return df_res_estimates, df_res_bias


def main() -> None:
    """Entry point para execução isolada do estimador causal."""
    estimator = SpatialDoubleMLPLR()
    df_est, df_bias = estimator.run()
    print("\n--- Estimativas Causais PLR (DoubleML) ---")
    print(df_est.select([
        "target_cancer", "exposure_variable", "theta_dml", "se_cluster", "p_value", "iqr_ate", "status"
    ]))
    print("\n--- Experimento do Viés de Detecção (Naive vs DML) ---")
    print(df_bias.select([
        "target_cancer", "exposure_variable", "theta_naive", "theta_dml", "delta_pct", "detection_bias_proven"
    ]))


if __name__ == "__main__":
    main()
