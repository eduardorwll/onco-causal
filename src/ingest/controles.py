# src/ingest/controles.py
from __future__ import annotations

import logging

import polars as pl

from src.core.bq_engine import BigQueryEngine
from src.core.contracts import CONTROLES_ASSISTENCIAIS_CONTRACT
from src.core.lineage import LineageTracker
from src.core.settings import DomainSpec, EnvSettings

logger = logging.getLogger("onco_causal.ingest.controles")


def run_controles_stage(
    env: EnvSettings,
    spec: DomainSpec,
    engine: BigQueryEngine,
    ano_inicio: int = 2020,
    ano_fim: int = 2022,
) -> pl.DataFrame:
    """Extrai controles assistenciais e de saneamento (Vetor Z) em consultas anuais seguras."""
    env.staging_dir.mkdir(parents=True, exist_ok=True)
    sql_file = env.sql_dir / "04_cnes_snis_controles.sql"

    logger.info(
        f"Iniciando ingestão de controles CNES/SNIS [{ano_inicio}-{ano_fim}] ano a ano..."
    )
    dfs: list[pl.DataFrame] = []
    for ano in range(ano_inicio, ano_fim + 1):
        logger.info(f"Consultando controles CNES/SNIS para o ano {ano}...")
        df_year = engine.query_from_file(
            sql_path=sql_file,
            params={
                "ano": ano,
                "excluded_municipios": spec.sampling.excluded_municipios,
            },
            use_cache=spec.bigquery.use_cache,
        )
        dfs.append(df_year)

    df_raw = pl.concat(dfs).sort(["id_municipio", "ano"])

    # 1. Validação estrita por contrato (Pilar III)
    df_valid = CONTROLES_ASSISTENCIAIS_CONTRACT.enforce(df_raw)

    # 2. Persistência Parquet Zstandard (Pilar IV)
    out_path = env.staging_dir / "controles_assistenciais_snis.parquet"
    df_valid.write_parquet(out_path, compression="zstd")
    logger.info(
        f"Artefato salvo: {out_path} ({df_valid.height:,} registros | {df_valid['ano'].n_unique()} anos)"
    )

    # 3. Registro no Manifesto de Linhagem
    tracker = LineageTracker(manifest_path=env.staging_dir / "manifest.json")
    tracker.record_artifact(
        artifact_name="controles_assistenciais_snis",
        parquet_path=out_path,
        df=df_valid,
        sql_path=sql_file,
        parameters={"ano_inicio": ano_inicio, "ano_fim": ano_fim},
    )

    return df_valid


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    env = EnvSettings()
    spec = DomainSpec.from_yaml()
    engine = BigQueryEngine(explicit_project_id=env.gcp_project_id, max_bytes_billed=spec.bigquery.max_bytes_billed)
    run_controles_stage(env, spec, engine)


if __name__ == "__main__":
    main()
