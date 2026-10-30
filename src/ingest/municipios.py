# src/ingest/municipios.py
from __future__ import annotations

import logging

import polars as pl

from src.core.bq_engine import BigQueryEngine
from src.core.contracts import DataContract
from src.core.settings import DomainSpec, EnvSettings

logger = logging.getLogger("onco_causal.ingest.municipios")

MUNICIPIOS_CONTRACT = DataContract(
    name="diretorio_municipios",
    primary_keys=("id_municipio",),
    required_schema={
        "id_municipio": pl.String,
        "id_municipio_6": pl.String,
        "nome_municipio": pl.String,
        "sigla_uf": pl.String,
        "id_mesorregiao": pl.String,
        "id_microrregiao": pl.String,
        "populacao_estimada": pl.Int64,
        "perfil_amostral": pl.String,
    },
    sentinel_null_values={
        "id_municipio_6": ["", "0", "999999", "IGN"],
        "id_mesorregiao": ["", "0", "9999"],
        "id_microrregiao": ["", "0", "99999"],
    },
)


def run_municipios_stage(
    env: EnvSettings,
    spec: DomainSpec,
    engine: BigQueryEngine,
) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Executa o Stage 01: extração, validação por contrato e persistência da malha municipal."""
    env.staging_dir.mkdir(parents=True, exist_ok=True)
    sql_file = env.sql_dir / "01_diretorio_amostra.sql"

    logger.info("Executando extração de municípios no BigQuery...")
    df_raw = engine.query_from_file(
        sql_path=sql_file,
        params={
            "base_year_pop": spec.sampling.base_year_pop,
            "min_populacao": spec.sampling.min_population,
            "polos_estrategicos": spec.sampling.all_hub_ids,
            "excluded_municipios": spec.sampling.excluded_municipios,
        },
        use_cache=spec.bigquery.use_cache,
    )

    # 1. Validação estrita por contrato (Pilar III)
    df_valid = MUNICIPIOS_CONTRACT.enforce(df_raw)

    # 2. Persistência da malha completa (Nível I: N = 5.570 para Spatial Empirical Bayes)
    full_path = env.staging_dir / "diretorio_municipios_full.parquet"
    df_valid.write_parquet(full_path, compression="zstd")
    logger.info(f"Artefato salvo: {full_path} ({df_valid.height:,} municípios)")

    # 3. Filtragem e persistência do recorte analítico TabFM (Nível II: Capitais + Polos + >= 50k)
    df_sample = df_valid.filter(pl.col("perfil_amostral") != "4_Pequeno_Porte")
    df_sample = MUNICIPIOS_CONTRACT.enforce(df_sample)
    sample_path = env.staging_dir / "municipios_recorte_tabfm.parquet"
    df_sample.write_parquet(sample_path, compression="zstd")
    logger.info(
        f"Artefato salvo: {sample_path} ({df_sample.height:,} municípios selecionados)"
    )

    logger.info(
        f"Stage 01 concluído com sucesso: {df_valid.height} municípios na malha total | "
        f"{df_sample.height} no recorte analítico TabFM."
    )
    return df_valid, df_sample


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    )
    env = EnvSettings()
    spec = DomainSpec.from_yaml()
    engine = BigQueryEngine(
        explicit_project_id=env.gcp_project_id,
        max_bytes_billed=spec.bigquery.max_bytes_billed,
    )
    run_municipios_stage(env, spec, engine)


if __name__ == "__main__":
    main()
