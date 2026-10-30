# src/spatial/cross_validation.py
from __future__ import annotations

import logging
from typing import Any

import polars as pl
from scipy.spatial.distance import cdist
from sklearn.model_selection import StratifiedGroupKFold

from src.core.contracts import SPATIAL_CV_FOLDS_CONTRACT
from src.core.lineage import LineageTracker
from src.core.settings import DomainSpec, EnvSettings

logger = logging.getLogger("onco_causal.spatial.cross_validation")


def generate_nested_spatial_block_cv(
    df_cohort: pl.DataFrame,
    df_geo: pl.DataFrame,
    n_splits: int = 5,
    dead_zone_buffer_km: float = 30.0,
    random_state: int = 42,
) -> pl.DataFrame:
    """Gera índices do 5-Fold Nested Spatial Block CV com zona de amortecimento (Dead-Zone)."""
    # 1. Cruzamento do recorte analítico com geometrias e coordenadas projetadas
    df_merged = df_cohort.join(
        df_geo.select(["id_municipio", "ottobacia_id", "x_proj_5070", "y_proj_5070"]),
        on="id_municipio",
        how="inner",
    ).sort("id_municipio")

    if df_merged.height != df_cohort.height:
        raise ValueError(
            f"Divergência de municípios: esperado {df_cohort.height}, obtido {df_merged.height}"
        )

    logger.info(
        f"Iniciando 5-Fold Nested SBCV para {df_merged.height} municípios e "
        f"{df_merged['ottobacia_id'].n_unique()} Ottobacias Nível 4..."
    )

    df_pd = df_merged.to_pandas()
    y_strat = df_pd["perfil_amostral"].tolist()
    groups_bacia = df_pd["ottobacia_id"].tolist()

    sgkf = StratifiedGroupKFold(
        n_splits=n_splits, shuffle=True, random_state=random_state
    )

    buffer_meters = dead_zone_buffer_km * 1000.0
    all_fold_records: list[dict[str, Any]] = []

    for fold_id, (train_idx, test_idx) in enumerate(sgkf.split(df_pd, y_strat, groups_bacia)):
        test_df = df_pd.iloc[test_idx]
        train_df = df_pd.iloc[train_idx]

        # Validação mandatória: disjunção topológica estrita de bacias
        overlap = set(test_df["ottobacia_id"]).intersection(set(train_df["ottobacia_id"]))
        if overlap:
            raise ValueError(
                f"[Fold {fold_id}] Violação topológica: {len(overlap)} bacias compartilhadas entre treino e teste."
            )

        test_coords = test_df[["x_proj_5070", "y_proj_5070"]].to_numpy()
        train_coords = train_df[["x_proj_5070", "y_proj_5070"]].to_numpy()

        # Calcula matriz de distâncias euclidianas entre todos os municípios de treino e os de teste
        dists = cdist(train_coords, test_coords)  # shape: (N_train, N_test)
        min_dists_to_test = dists.min(axis=1)

        # Registra municípios do conjunto de teste
        for _, row in test_df.iterrows():
            all_fold_records.append(
                {
                    "id_municipio": str(row["id_municipio"]),
                    "fold_id": int(fold_id),
                    "split_role": "test",
                    "ottobacia_id": str(row["ottobacia_id"]),
                    "perfil_amostral": str(row["perfil_amostral"]),
                    "dist_km_fronteira_teste": 0.0,
                }
            )

        # Registra municípios de treino e marca a dead-zone de amortecimento
        n_buffer = 0
        n_clean_train = 0
        for i, (_, row) in enumerate(train_df.iterrows()):
            dist_m = float(min_dists_to_test[i])
            dist_km = dist_m / 1000.0

            if dist_m < buffer_meters:
                split_role = "buffer_exclusion"
                n_buffer += 1
            else:
                split_role = "train"
                n_clean_train += 1

            all_fold_records.append(
                {
                    "id_municipio": str(row["id_municipio"]),
                    "fold_id": int(fold_id),
                    "split_role": split_role,
                    "ottobacia_id": str(row["ottobacia_id"]),
                    "perfil_amostral": str(row["perfil_amostral"]),
                    "dist_km_fronteira_teste": float(dist_km),
                }
            )

        logger.info(
            f"Fold {fold_id}: Test={len(test_df)} | Treino Efetivo (>={dead_zone_buffer_km}km)={n_clean_train} | "
            f"Dead-Zone Excluída (<{dead_zone_buffer_km}km)={n_buffer}"
        )

    df_folds = pl.DataFrame(all_fold_records).sort(["fold_id", "id_municipio"])
    return df_folds


def run_cross_validation_stage(
    env: EnvSettings | None = None,
    spec: DomainSpec | None = None,
) -> pl.DataFrame:
    """Orquestra a geração da validação cruzada aninhada em blocos e salva com contrato."""
    env = env or EnvSettings()
    spec = spec or DomainSpec.from_yaml()

    cohort_path = env.staging_dir / "municipios_recorte_tabfm.parquet"
    geo_path = env.staging_dir / "spatial_municipios_ottobacias.parquet"

    if not cohort_path.exists():
        raise FileNotFoundError(f"Arquivo de coorte analítica não encontrado: {cohort_path}")
    if not geo_path.exists():
        raise FileNotFoundError(f"Arquivo de geometrias não encontrado: {geo_path}")

    df_cohort = pl.read_parquet(cohort_path)
    df_geo = pl.read_parquet(geo_path)

    dead_zone_km = spec.spatial.dead_zone_buffer_km
    df_folds = generate_nested_spatial_block_cv(
        df_cohort=df_cohort,
        df_geo=df_geo,
        n_splits=5,
        dead_zone_buffer_km=dead_zone_km,
        random_state=42,
    )

    logger.info("Aplicando SPATIAL_CV_FOLDS_CONTRACT...")
    df_valid = SPATIAL_CV_FOLDS_CONTRACT.enforce(df_folds)

    dest_path = env.staging_dir / "spatial_cv_folds.parquet"
    logger.info(f"Persistindo índices de validação cruzada em: {dest_path}")
    df_valid.write_parquet(dest_path, compression="zstd")

    # Registro de linhagem
    tracker = LineageTracker(env.staging_dir / "manifest.json")
    spec_path = spec.configs_path if hasattr(spec, "configs_path") else None
    tracker.record_artifact(
        artifact_name="spatial_cv_folds",
        parquet_path=dest_path,
        df=df_valid,
        parameters={
            "stage": "03C",
            "n_splits": 5,
            "dead_zone_buffer_km": dead_zone_km,
            "total_records": df_valid.height,
        },
        domain_spec_path=spec_path,
    )

    logger.info(
        f"Stage 03C concluído com sucesso: {df_valid.height} atribuições de fold geradas."
    )
    return df_valid


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_cross_validation_stage()
