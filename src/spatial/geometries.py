# src/spatial/geometries.py
from __future__ import annotations

import io
import logging
import time
import zipfile
from pathlib import Path

import geopandas as gpd
import httpx

from src.core.settings import DomainSpec, EnvSettings

logger = logging.getLogger("onco_causal.spatial.geometries")

IBGE_LOCALIDADES_URL = (
    "https://geoftp.ibge.gov.br/organizacao_do_territorio/estrutura_territorial/"
    "localidades/Localidades_do_Brasil/2022/Localidades_Brasil_shp.zip"
)
ANA_OTTOBACIAS_URL = (
    "https://metadados.snirh.gov.br/files/32e309da-a8c1-443f-90ac-0cd79ce6a33d/"
    "geoft_bho_ach_otto_nivel_04.gpkg"
)


def ensure_ibge_sedes_downloaded(raw_dir: Path) -> Path:
    """Garante que a malha oficial de Localidades/Sedes do IBGE esteja presente em disco."""
    geom_dir = raw_dir / "geometries"
    geom_dir.mkdir(parents=True, exist_ok=True)
    shp_path = geom_dir / "ibge_localidades_2022" / "BR_localidades_2022.shp"

    if shp_path.exists():
        logger.info(f"Sedes do IBGE já disponíveis em: {shp_path}")
        return shp_path

    logger.info(f"Baixando malha oficial de localidades do IBGE de: {IBGE_LOCALIDADES_URL}")
    with httpx.Client(follow_redirects=True, timeout=120.0) as client:
        resp = client.get(IBGE_LOCALIDADES_URL)
        resp.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
            dest_dir = geom_dir / "ibge_localidades_2022"
            dest_dir.mkdir(parents=True, exist_ok=True)
            z.extractall(dest_dir)

    logger.info(f"Sedes do IBGE extraídas com sucesso para {shp_path.parent}")
    return shp_path


def ensure_ana_ottobacias_downloaded(raw_dir: Path) -> Path:
    """Garante que a malha vetorial de Ottobacias Nível 4 da ANA esteja presente em disco."""
    geom_dir = raw_dir / "geometries"
    geom_dir.mkdir(parents=True, exist_ok=True)
    gpkg_path = geom_dir / "geoft_bho_ach_otto_nivel_04.gpkg"

    if gpkg_path.exists() and gpkg_path.stat().st_size > 100_000_000:
        logger.info(f"Ottobacias Nível 4 da ANA já disponíveis em: {gpkg_path}")
        return gpkg_path

    logger.info(f"Baixando Ottobacias Nível 4 da ANA (BHO 6) de: {ANA_OTTOBACIAS_URL}")
    t0 = time.time()
    with (
        httpx.Client(follow_redirects=True, timeout=600.0) as client,
        client.stream("GET", ANA_OTTOBACIAS_URL) as r,
        open(gpkg_path, "wb") as f,
    ):
        r.raise_for_status()
        f.writelines(r.iter_bytes(chunk_size=1024 * 1024 * 5))
    logger.info(
        f"Ottobacias da ANA baixadas com sucesso em {time.time() - t0:.1f}s: {gpkg_path}"
    )
    return gpkg_path


def load_municipal_seats(spec: DomainSpec, env: EnvSettings) -> gpd.GeoDataFrame:
    """Carrega as sedes municipais oficiais do IBGE para os 5.570 municípios na projeção informada."""
    shp_path = ensure_ibge_sedes_downloaded(env.raw_dir)
    logger.info(f"Lendo shapefile de localidades: {shp_path}")
    gdf = gpd.read_file(shp_path)

    # 1. Filtra cidades e Fernando de Noronha (distrito estadual)
    mask = (gdf["CT_LOCALID"] == "Cidade") | (gdf["CD_MUN"].astype(str) == "2605459")
    sedes = gdf[mask].drop_duplicates(subset=["CD_MUN"], keep="first").copy()

    # 2. Expurgo declarativo de municípios fora da coorte (ex.: Boa Esperança do Norte)
    excluded = set(spec.sampling.excluded_municipios)
    sedes = sedes[~sedes["CD_MUN"].astype(str).isin(excluded)].copy()

    # 3. Padronização de identificadores e atributos
    sedes["id_municipio"] = sedes["CD_MUN"].astype(str).str.strip()
    sedes["nome_municipio"] = sedes["NM_MUN"].astype(str).str.strip()
    sedes["sigla_uf"] = sedes["SIGLA_UF"].astype(str).str.strip()
    sedes["latitude_sede"] = sedes["LAT_LOCALI"].astype(float)
    sedes["longitude_sede"] = sedes["LONG_LOCAL"].astype(float)

    # 4. Reprojeção para sistema de área equivalente (Padrão: EPSG:5070)
    target_crs = spec.spatial.crs_proj
    logger.info(f"Reprojetando sedes municipais de {sedes.crs} para {target_crs}")
    sedes = sedes.to_crs(target_crs)
    sedes["x_proj_5070"] = sedes.geometry.x
    sedes["y_proj_5070"] = sedes.geometry.y

    cols_order = [
        "id_municipio",
        "nome_municipio",
        "sigla_uf",
        "latitude_sede",
        "longitude_sede",
        "x_proj_5070",
        "y_proj_5070",
        "geometry",
    ]
    sedes = sedes[cols_order].sort_values("id_municipio").reset_index(drop=True)
    logger.info(f"Sedes municipais carregadas: {len(sedes)} municípios indexados.")
    return sedes


def load_ottobacias_level4(spec: DomainSpec, env: EnvSettings) -> gpd.GeoDataFrame:
    """Carrega os polígonos oficiais das Ottobacias Nível 4 da ANA reprojetados."""
    gpkg_path = ensure_ana_ottobacias_downloaded(env.raw_dir)
    logger.info(f"Lendo GeoPackage das Ottobacias Nível 4 da ANA: {gpkg_path}")
    ottos = gpd.read_file(gpkg_path)

    # Padroniza coluna identificadora da Ottobacia
    ottos = ottos.rename(columns={"wts_cd_pfafstetterbasin": "ottobacia_id"})
    ottos["ottobacia_id"] = ottos["ottobacia_id"].astype(str).str.strip()

    target_crs = spec.spatial.crs_proj
    if str(ottos.crs) != target_crs:
        logger.info(f"Reprojetando Ottobacias de {ottos.crs} para {target_crs}")
        ottos = ottos.to_crs(target_crs)

    cols = ["ottobacia_id", "geometry"]
    if "wts_gm_area" in ottos.columns:
        ottos = ottos.rename(columns={"wts_gm_area": "area_km2_bacia"})
        cols.insert(1, "area_km2_bacia")

    ottos = ottos[cols].reset_index(drop=True)
    logger.info(f"Ottobacias Nível 4 carregadas: {len(ottos)} bacias poligonais.")
    return ottos
