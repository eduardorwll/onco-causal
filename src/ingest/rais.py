# src/ingest/rais.py
from __future__ import annotations

import logging

import polars as pl

from src.core.bq_engine import BigQueryEngine
from src.core.contracts import RAIS_LINACH_CONTRACT
from src.core.lineage import LineageTracker
from src.core.settings import DomainSpec, EnvSettings

logger = logging.getLogger("onco_causal.ingest.rais")


def get_cnae_prefixes(spec: DomainSpec) -> tuple[list[str], list[str]]:
    """Extrai e segrega prefixos CNAE 2.0 por comprimento (3 ou 4 dígitos)."""
    p3: set[str] = set()
    p4: set[str] = set()
    for group in spec.cnae_linach_groups.values():
        for prefix in group.cnae_prefixes:
            clean = prefix.strip()
            if len(clean) == 3:
                p3.add(clean)
            elif len(clean) >= 4:
                p4.add(clean[:4])
    return sorted(p3), sorted(p4)


def run_rais_stage(
    env: EnvSettings,
    spec: DomainSpec,
    engine: BigQueryEngine,
    ano_inicio: int = 2015,
    ano_fim: int = 2024,
    batch_size: int = 3,
) -> pl.DataFrame:
    """Extrai série temporal de exposição ocupacional da RAIS em lotes de anos seguros."""
    env.staging_dir.mkdir(parents=True, exist_ok=True)
    sql_file = env.sql_dir / "02_rais_exposicao_linach.sql"
    cnae_3, cnae_4 = get_cnae_prefixes(spec)

    logger.info(
        f"Iniciando ingestão RAIS [{ano_inicio}-{ano_fim}] com {len(cnae_3)} prefixos 3d e {len(cnae_4)} prefixos 4d..."
    )

    dfs: list[pl.DataFrame] = []
    for start_year in range(ano_inicio, ano_fim + 1, batch_size):
        end_year = min(start_year + batch_size - 1, ano_fim)
        logger.info(f"Consultando RAIS no BigQuery para o lote {start_year}-{end_year}...")
        df_batch = engine.query_from_file(
            sql_path=sql_file,
            params={
                "ano_inicio": start_year,
                "ano_fim": end_year,
                "cnae_prefixes_3": cnae_3,
                "cnae_prefixes_4": cnae_4,
            },
            use_cache=spec.bigquery.use_cache,
        )
        dfs.append(df_batch)

    df_raw = pl.concat(dfs).sort(["id_municipio", "ano"])

    # Calcula proporção de trabalhadores expostos aos agentes LINACH
    df_calc = df_raw.with_columns(
        pl.when(pl.col("vinculos_totais") > 0)
        .then(pl.col("vinculos_linach") / pl.col("vinculos_totais"))
        .otherwise(0.0)
        .alias("prop_linach")
    )

    # 1. Validação estrita por contrato (Pilar III)
    df_valid = RAIS_LINACH_CONTRACT.enforce(df_calc)

    # 2. Persistência Parquet Zstandard (Pilar IV)
    out_path = env.staging_dir / "rais_linach_anual.parquet"
    df_valid.write_parquet(out_path, compression="zstd")
    logger.info(
        f"Artefato salvo: {out_path} ({df_valid.height:,} registros | {df_valid['ano'].n_unique()} anos)"
    )

    # 3. Registro no Manifesto de Linhagem
    tracker = LineageTracker(manifest_path=env.staging_dir / "manifest.json")
    tracker.record_artifact(
        artifact_name="rais_linach_anual",
        parquet_path=out_path,
        df=df_valid,
        sql_path=sql_file,
        parameters={"ano_inicio": ano_inicio, "ano_fim": ano_fim, "batch_size": batch_size},
    )

    return df_valid


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    env = EnvSettings()
    spec = DomainSpec.from_yaml()
    engine = BigQueryEngine(explicit_project_id=env.gcp_project_id, max_bytes_billed=spec.bigquery.max_bytes_billed)
    run_rais_stage(env, spec, engine)


if __name__ == "__main__":
    main()
