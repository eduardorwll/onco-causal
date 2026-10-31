# src/ingest/mapbiomas.py
from __future__ import annotations

import logging

import polars as pl

from src.core.bq_engine import BigQueryEngine
from src.core.contracts import MAPBIOMAS_COBERTURA_CONTRACT
from src.core.lineage import LineageTracker
from src.core.settings import DomainSpec, EnvSettings

logger = logging.getLogger("onco_causal.ingest.mapbiomas")


def run_mapbiomas_stage(
    env: EnvSettings | None = None,
    spec: DomainSpec | None = None,
    engine: BigQueryEngine | None = None,
    ano_inicio: int = 1998,
    ano_fim: int = 2022,
) -> pl.DataFrame:
    """Extrai séries históricas de cobertura e uso do solo (MapBiomas Estatísticas)."""
    env = env or EnvSettings()
    spec = spec or DomainSpec.from_yaml()
    engine = engine or BigQueryEngine(
        explicit_project_id=env.gcp_project_id,
        max_bytes_billed=spec.bigquery.max_bytes_billed,
    )

    env.staging_dir.mkdir(parents=True, exist_ok=True)
    sql_file = env.sql_dir / "06_mapbiomas_cobertura.sql"

    logger.info(f"Iniciando ingestão MapBiomas [{ano_inicio}-{ano_fim}]...")
    df_raw = engine.query_from_file(
        sql_path=sql_file,
        params={
            "ano_inicio": ano_inicio,
            "ano_fim": ano_fim,
        },
        use_cache=spec.bigquery.use_cache,
    )

    # 1. Validação estrita por contrato (Pilar III)
    df_valid = MAPBIOMAS_COBERTURA_CONTRACT.enforce(df_raw)

    # 2. Persistência Parquet Zstandard (Pilar IV)
    out_path = env.staging_dir / "mapbiomas_cobertura_anual.parquet"
    df_valid.write_parquet(out_path, compression="zstd")
    logger.info(
        f"Artefato salvo: {out_path} ({df_valid.height:,} registros | {df_valid['ano'].n_unique()} anos)"
    )

    # 3. Registro no Manifesto de Linhagem
    tracker = LineageTracker(manifest_path=env.staging_dir / "manifest.json")
    spec_path = spec.configs_path if hasattr(spec, "configs_path") else None
    tracker.record_artifact(
        artifact_name="mapbiomas_cobertura_anual",
        parquet_path=out_path,
        df=df_valid,
        sql_path=sql_file,
        parameters={"ano_inicio": ano_inicio, "ano_fim": ano_fim},
        domain_spec_path=spec_path,
    )

    return df_valid


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    env = EnvSettings()
    spec = DomainSpec.from_yaml()
    engine = BigQueryEngine(
        explicit_project_id=env.gcp_project_id,
        max_bytes_billed=spec.bigquery.max_bytes_billed,
    )
    run_mapbiomas_stage(env, spec, engine, ano_inicio=1998, ano_fim=2022)


if __name__ == "__main__":
    main()
