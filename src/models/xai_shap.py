# src/models/xai_shap.py
"""Módulo de Explicabilidade Global/Local via TreeSHAP e Limiares Toxicológicos SHAP=0 (Stage 04C).

Implementa:
- Explicação por valores de Shapley (shap.TreeExplainer) sobre o modelo campeão do benchmark.
- Curvas de dependência parcial (PDP/ICE) para os vetores de exposição D1 e D4.
- Determinação matemática do ponto de inflexão onde SHAP(D) = 0 (transição para risco acelerador).
- Persistência e rastreabilidade em data/features/shap_inflection_thresholds.parquet.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import polars as pl
import shap
from sklearn.preprocessing import StandardScaler

from src.core.lineage import LineageTracker

logger = logging.getLogger("onco_causal.models.xai_shap")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

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

EXPOSURE_FEATURES_TO_ANALYZE = [
    "prop_lavouras_criticas_mean",
    "prop_lavouras_criticas_trend",
    "prop_linach_mean",
    "prop_linach_trend",
    "prop_floresta_mean",
    "prop_urbanizada_mean",
]


def find_zero_crossing_threshold(
    raw_feature_values: np.ndarray,
    feature_shap_values: np.ndarray,
    window_fraction: float = 0.05,
) -> tuple[float, float, float]:
    """Calcula matematicamente o ponto de corte onde a curva média SHAP cruza o limiar zero (SHAP = 0).

    Retorna: (threshold_x, shap_at_min, shap_at_max)
    """
    sort_idx = np.argsort(raw_feature_values)
    x_sorted = raw_feature_values[sort_idx]
    s_sorted = feature_shap_values[sort_idx]

    shap_at_min = float(s_sorted[: max(10, int(len(s_sorted) * 0.02))].mean())
    shap_at_max = float(s_sorted[-max(10, int(len(s_sorted) * 0.02)) :].mean())

    window_size = max(20, int(len(x_sorted) * window_fraction))
    rolling_shap = np.convolve(s_sorted, np.ones(window_size) / window_size, mode="valid")
    x_window = x_sorted[window_size - 1 :]

    # Detectar transição de sinal (zero-crossing)
    sign_changes = np.where(np.diff(np.sign(rolling_shap)))[0]

    if len(sign_changes) > 0:
        first_idx = sign_changes[0]
        threshold = float(x_window[first_idx])
    else:
        # Se for estritamente monótono, estimar via interpolação linear ponderada
        if s_sorted.min() <= 0.0 <= s_sorted.max():
            threshold = float(np.interp(0.0, s_sorted, x_sorted))
        elif s_sorted.min() > 0.0:
            threshold = float(x_sorted.min())
        else:
            threshold = float(x_sorted.max())

    return threshold, shap_at_min, shap_at_max


def compute_shap_thresholds(
    data_dir: Path | str | None = None,
    output_path: Path | str | None = None,
    manifest_path: Path | str | None = None,
) -> pl.DataFrame:
    """Treina o modelo campeão, computa atribuições TreeSHAP e resolve os limiares de inflexão."""
    base_dir = Path(data_dir) if data_dir else Path("data")
    feat_dir = base_dir / "features"
    stag_dir = base_dir / "staging"
    feat_dir.mkdir(parents=True, exist_ok=True)

    panel_path = feat_dir / "master_analytical_panel.parquet"
    out_path = Path(output_path) if output_path else feat_dir / "shap_inflection_thresholds.parquet"
    mnf_path = Path(manifest_path) if manifest_path else stag_dir / "manifest.json"

    logger.info("--- Iniciando Stage 04C: TreeSHAP e Limiares Toxicológicos SHAP=0 ---")
    panel = pl.read_parquet(panel_path)

    x_raw = panel.select(FEATURE_COLUMNS).to_numpy()
    y = panel["smr_suavizada_eb"].to_numpy()

    scaler = StandardScaler().fit(x_raw)
    x_scaled = scaler.transform(x_raw)

    logger.info("Ajustando modelo campeão LightGBM sobre a coorte completa (%d linhas)...", len(y))
    model = lgb.LGBMRegressor(n_estimators=150, learning_rate=0.05, random_state=42, verbose=-1)
    model.fit(x_scaled, y)

    logger.info("Computando TreeSHAP (shap.TreeExplainer)...")
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(x_scaled)

    mean_abs_shap = np.abs(shap_values).mean(axis=0)
    feat_importance = dict(zip(FEATURE_COLUMNS, mean_abs_shap, strict=False))

    records: list[dict[str, Any]] = []

    # 1. Limiares Globais (ALL Cancers)
    for feat_name in EXPOSURE_FEATURES_TO_ANALYZE:
        f_idx = FEATURE_COLUMNS.index(feat_name)
        raw_vals = x_raw[:, f_idx]
        s_vals = shap_values[:, f_idx]

        thresh, s_min, s_max = find_zero_crossing_threshold(raw_vals, s_vals)
        importance = float(feat_importance[feat_name])

        interp = (
            f"Risco acelerador para {feat_name} > {thresh:.4f} "
            f"(SHAP min={s_min:+.4f}, max={s_max:+.4f}, imp={importance:.4f})"
        )

        records.append({
            "feature_name": feat_name,
            "target_cancer": "ALL",
            "inflection_threshold": thresh,
            "shap_at_min": s_min,
            "shap_at_max": s_max,
            "mean_abs_shap": importance,
            "interpretation": interp,
        })
        logger.info("Limiar Global [%-28s]: %10.4f | SHAP: [%+.4f -> %+.4f]", feat_name, thresh, s_min, s_max)

    # 2. Limiares Específicos por Alvo Oncológico
    cancer_targets = sorted(panel["target_cancer"].unique().to_list())
    for target in cancer_targets:
        t_mask = (panel["target_cancer"] == target).to_numpy()
        x_raw_t = x_raw[t_mask]
        shap_t = shap_values[t_mask]

        for feat_name in EXPOSURE_FEATURES_TO_ANALYZE:
            f_idx = FEATURE_COLUMNS.index(feat_name)
            raw_vals_t = x_raw_t[:, f_idx]
            s_vals_t = shap_t[:, f_idx]

            thresh_t, s_min_t, s_max_t = find_zero_crossing_threshold(raw_vals_t, s_vals_t)
            imp_t = float(np.abs(s_vals_t).mean())

            interp_t = f"Limiar para {target} em {feat_name} > {thresh_t:.4f} (SHAP max={s_max_t:+.4f})"

            records.append({
                "feature_name": feat_name,
                "target_cancer": target,
                "inflection_threshold": thresh_t,
                "shap_at_min": s_min_t,
                "shap_at_max": s_max_t,
                "mean_abs_shap": imp_t,
                "interpretation": interp_t,
            })

    df_thresholds = pl.DataFrame(records)
    df_thresholds.write_parquet(out_path, compression="zstd")
    logger.info("Limiares salvos em: %s", out_path)

    lineage = LineageTracker(manifest_path=mnf_path)
    lineage.record_artifact(
        artifact_name="shap_inflection_thresholds",
        parquet_path=out_path,
        df=df_thresholds,
        parameters={
            "model_type": "LightGBMRegressor",
            "features_analyzed": EXPOSURE_FEATURES_TO_ANALYZE,
            "targets_count": len(cancer_targets),
        },
    )
    logger.info("Linhagem do artefato SHAP registrada com sucesso no manifest.json.")

    return df_thresholds


if __name__ == "__main__":
    compute_shap_thresholds()
