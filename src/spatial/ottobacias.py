# src/spatial/ottobacias.py
from __future__ import annotations

import logging

import geopandas as gpd
import polars as pl

from src.core.contracts import SPATIAL_GEOMETRIES_CONTRACT
from src.core.lineage import LineageTracker
from src.core.settings import DomainSpec, EnvSettings
from src.spatial.geometries import load_municipal_seats, load_ottobacias_level4

logger = logging.getLogger("onco_causal.spatial.ottobacias")


def assign_ottobacias(
    gdf_sedes: gpd.GeoDataFrame, gdf_ottobacias: gpd.GeoDataFrame
) -> pl.DataFrame:
    """Executa Spatial Join estrito entre as Sedes Municipais e as Ottobacias Nível 4 da ANA."""
    logger.info(
        f"Iniciando Spatial Join: {len(gdf_sedes)} sedes x {len(gdf_ottobacias)} bacias hidrográficas"
    )

    # 1. Spatial Join com predicado 'within' (Sede municipal dentro da Ottobacia)
    ottos_subset = gdf_ottobacias[["ottobacia_id", "geometry"]]
    joined = gpd.sjoin(gdf_sedes, ottos_subset, how="left", predicate="within")

    # 2. Tratamento determinístico para municípios insulares/costeiros fora da malha fluvial
    unmatched_mask = joined["ottobacia_id"].isna()
    n_unmatched = unmatched_mask.sum()

    if n_unmatched > 0:
        logger.info(
            f"Resolvendo {n_unmatched} sedes municipais costeiras/insulares via sjoin_nearest..."
        )
        unmatched_sedes = gdf_sedes[unmatched_mask].copy()
        nearest_matches = gpd.sjoin_nearest(
            unmatched_sedes, ottos_subset, how="left"
        )
        # Substitui os valores nulos com as bacias costeiras de menor distância
        for idx, row in nearest_matches.iterrows():
            joined.loc[idx, "ottobacia_id"] = row["ottobacia_id"]

    # 3. Validação de integridade e unicidade
    if joined["ottobacia_id"].isna().any():
        n_remaining = joined["ottobacia_id"].isna().sum()
        raise ValueError(
            f"Falha no Spatial Join: {n_remaining} municípios permaneceram sem ottobacia_id."
        )

    # Remove duplicatas se houver sobreposição exata de borda
    joined = joined.drop_duplicates(subset=["id_municipio"], keep="first")

    # 4. Conversão para Polars DataFrame
    records = {
        "id_municipio": joined["id_municipio"].astype(str).tolist(),
        "nome_municipio": joined["nome_municipio"].astype(str).tolist(),
        "sigla_uf": joined["sigla_uf"].astype(str).tolist(),
        "ottobacia_id": joined["ottobacia_id"].astype(str).tolist(),
        "latitude_sede": joined["latitude_sede"].astype(float).tolist(),
        "longitude_sede": joined["longitude_sede"].astype(float).tolist(),
        "x_proj_5070": joined["x_proj_5070"].astype(float).tolist(),
        "y_proj_5070": joined["y_proj_5070"].astype(float).tolist(),
    }
    df = pl.DataFrame(records).sort("id_municipio")
    return df


def run_ottobacias_stage(
    env: EnvSettings | None = None,
    spec: DomainSpec | None = None,
) -> pl.DataFrame:
    """Orquestra a carga de geometrias, spatial join e persistência do artefato com contrato."""
    env = env or EnvSettings()
    spec = spec or DomainSpec.from_yaml()

    # Carrega malhas na projeção EPSG:5070
    gdf_sedes = load_municipal_seats(spec, env)
    gdf_ottobacias = load_ottobacias_level4(spec, env)

    # Executa cruzamento espacial
    df = assign_ottobacias(gdf_sedes, gdf_ottobacias)

    # Aplica contrato estrito
    logger.info("Aplicando SPATIAL_GEOMETRIES_CONTRACT...")
    df_valid = SPATIAL_GEOMETRIES_CONTRACT.enforce(df)

    # Persistência em disco
    dest_path = env.staging_dir / "spatial_municipios_ottobacias.parquet"
    logger.info(f"Persistindo artefato aprovado em: {dest_path}")
    df_valid.write_parquet(dest_path, compression="zstd")

    # Registro no manifesto de linhagem
    tracker = LineageTracker(env.staging_dir / "manifest.json")
    spec_path = spec.configs_path if hasattr(spec, "configs_path") else None
    tracker.record_artifact(
        artifact_name="spatial_municipios_ottobacias",
        parquet_path=dest_path,
        df=df_valid,
        parameters={
            "stage": "03A",
            "crs_proj": spec.spatial.crs_proj,
            "ottobacias_level": spec.spatial.ottobacias_level,
            "total_bacias_unicas": df_valid["ottobacia_id"].n_unique(),
        },
        domain_spec_path=spec_path,
    )

    logger.info(
        f"Stage 03A concluído: {df_valid.height} municípios associados a {df_valid['ottobacia_id'].n_unique()} Ottobacias Nível 4."
    )
    return df_valid


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_ottobacias_stage()
