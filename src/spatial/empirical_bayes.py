# src/spatial/empirical_bayes.py
from __future__ import annotations

import logging
from typing import Any

import geopandas as gpd
import libpysal
import numpy as np
import polars as pl
from esda.smoothing import Spatial_Rate, slag
from shapely.geometry import Point

from src.core.contracts import SIM_TAXAS_SUAVIZADAS_EB_CONTRACT
from src.core.lineage import LineageTracker
from src.core.settings import DomainSpec, EnvSettings

logger = logging.getLogger("onco_causal.spatial.empirical_bayes")


def build_knn_weights_matrix(
    df_geo: pl.DataFrame, k: int = 31, crs_proj: str = "EPSG:5070"
) -> libpysal.weights.W:
    """Constrói a matriz de pesos espaciais KNN (k=31) baseada nas Sedes Municipais projetadas."""
    logger.info(
        f"Construindo matriz de pesos espaciais KNN k={k} sobre {df_geo.height} Sedes Municipais..."
    )
    geometry = [Point(xy) for xy in zip(df_geo["x_proj_5070"], df_geo["y_proj_5070"])]
    gdf = gpd.GeoDataFrame(df_geo.to_pandas(), geometry=geometry, crs=crs_proj)
    gdf = gdf.set_index("id_municipio")
    id_list = [str(i) for i in gdf.index.tolist()]
    w = libpysal.weights.KNN.from_dataframe(gdf, k=k, ids=id_list)
    return w


def smooth_smr_spatial_eb(
    e: np.ndarray, b: np.ndarray, w: libpysal.weights.W
) -> tuple[np.ndarray, np.ndarray]:
    """Aplica a Suavização Bayesiana Empírica Espacial Linear (PySAL) sobre a SMR.

    Retorna a taxa SMR suavizada e o fator de encolhimento w_i in [0, 1].
    """
    e_col = np.asarray(e, dtype=float).reshape(-1, 1)
    b_col = np.asarray(b, dtype=float).reshape(-1, 1)

    # Evita divisão por zero em municípios com população/esperados residuais
    b_col = np.where(b_col <= 0, 1e-6, b_col)

    r_mean = Spatial_Rate(e_col, b_col, w).r
    rate = e_col * 1.0 / b_col
    r_var_left = np.ones_like(e_col) * 1.0
    ngh_num = np.ones_like(e_col)
    bi = slag(w, b_col) + b_col

    for i, idv in enumerate(w.id_order):
        ngh = list(w[idv].keys()) + [idv]
        nghi = [w.id2i[k] for k in ngh]
        ngh_num[i] = len(nghi)
        v = sum(np.square(rate[nghi] - r_mean[i]) * b_col[nghi])
        r_var_left[i] = v

    r_var_left = r_var_left / bi
    r_var_right = r_mean / (bi / ngh_num)
    r_var = r_var_left - r_var_right
    r_var[r_var < 0] = 0.0

    denom = r_var + (r_mean / b_col)
    w_weights = np.divide(r_var, denom, out=np.zeros_like(r_var), where=denom > 0)
    w_weights = np.clip(w_weights, 0.0, 1.0)

    r_smoothed = r_mean + (rate - r_mean) * w_weights
    return r_smoothed.flatten(), w_weights.flatten()


def run_empirical_bayes_stage(
    env: EnvSettings | None = None,
    spec: DomainSpec | None = None,
) -> pl.DataFrame:
    """Orquestra a suavização Bayesiana da SMR em toda a malha municipal do Stage 02B."""
    env = env or EnvSettings()
    spec = spec or DomainSpec.from_yaml()

    geo_path = env.staging_dir / "spatial_municipios_ottobacias.parquet"
    sim_path = env.staging_dir / "sim_taxas_padronizadas_5570.parquet"

    if not geo_path.exists():
        raise FileNotFoundError(f"Arquivo geoespacial não encontrado: {geo_path}")
    if not sim_path.exists():
        raise FileNotFoundError(f"Arquivo SIM padronizado não encontrado: {sim_path}")

    df_geo = pl.read_parquet(geo_path).sort("id_municipio")
    df_sim = pl.read_parquet(sim_path)

    k_neighbors = spec.spatial.knn_neighbors
    w = build_knn_weights_matrix(df_geo, k=k_neighbors, crs_proj=spec.spatial.crs_proj)

    geo_ordered_ids = df_geo["id_municipio"].to_list()
    years = sorted(df_sim["ano"].unique().to_list())
    targets = sorted(df_sim["target_cancer"].unique().to_list())

    logger.info(
        f"Iniciando suavização Bayesiana para {len(years)} anos x {len(targets)} alvos oncológicos..."
    )

    all_records: list[dict[str, Any]] = []

    for ano in years:
        for tgt in targets:
            sub = df_sim.filter(
                (pl.col("ano") == ano) & (pl.col("target_cancer") == tgt)
            )
            # Garante que os dados estejam estritamente alinhados com geo_ordered_ids
            merged = df_geo.select("id_municipio").join(
                sub, on="id_municipio", how="left"
            )

            e = (
                merged["obitos_totais"]
                .fill_null(0)
                .to_numpy()
                .astype(float)
            )
            b = (
                merged["obitos_esperados_smr"]
                .fill_null(1e-6)
                .to_numpy()
                .astype(float)
            )

            smr_smooth, w_weights = smooth_smr_spatial_eb(e, b, w)

            obitos_obs = e.astype(int)
            obitos_esp = b
            smr_bruta = np.where(b > 0, e / b, 0.0)

            for i, mun_id in enumerate(geo_ordered_ids):
                all_records.append(
                    {
                        "id_municipio": mun_id,
                        "ano": int(ano),
                        "target_cancer": tgt,
                        "obitos_observados": int(obitos_obs[i]),
                        "obitos_esperados": float(obitos_esp[i]),
                        "smr_bruta": float(smr_bruta[i]),
                        "smr_suavizada_eb": float(smr_smooth[i]),
                        "peso_encolhimento_w": float(w_weights[i]),
                    }
                )

    df_result = pl.DataFrame(all_records).sort(["id_municipio", "ano", "target_cancer"])

    logger.info("Aplicando SIM_TAXAS_SUAVIZADAS_EB_CONTRACT...")
    df_valid = SIM_TAXAS_SUAVIZADAS_EB_CONTRACT.enforce(df_result)

    dest_path = env.staging_dir / "sim_taxas_suavizadas_eb.parquet"
    logger.info(f"Persistindo taxas suavizadas em: {dest_path}")
    df_valid.write_parquet(dest_path, compression="zstd")

    # Registro de linhagem
    tracker = LineageTracker(env.staging_dir / "manifest.json")
    spec_path = spec.configs_path if hasattr(spec, "configs_path") else None
    tracker.record_artifact(
        artifact_name="sim_taxas_suavizadas_eb",
        parquet_path=dest_path,
        df=df_valid,
        parameters={
            "stage": "03B",
            "knn_k": k_neighbors,
            "smoothing_method": "Spatial Linear Empirical Bayes",
            "num_targets": len(targets),
            "num_years": len(years),
        },
        domain_spec_path=spec_path,
    )

    logger.info(
        f"Stage 03B concluído com sucesso: {df_valid.height} registros suavizados gerados."
    )
    return df_valid


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_empirical_bayes_stage()
