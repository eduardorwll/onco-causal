# src/ingest/municipios.py
from __future__ import annotations

import logging

import polars as pl

from src.core.bq_engine import BigQueryEngine
from src.core.contracts import DataContract
from src.core.lineage import LineageTracker
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


def apply_internal_controls(
    df: pl.DataFrame,
    env: EnvSettings,
    spec: DomainSpec,
) -> pl.DataFrame:
    """Classifica o Estrato 4 ('4_Controle_Interno') cruzando RAIS e PAM se disponíveis."""
    rais_p = env.staging_dir / "rais_linach_anual.parquet"
    pam_p = env.staging_dir / "pam_lavouras_anual.parquet"

    if not (rais_p.exists() and pam_p.exists()):
        return df

    rais_df = pl.read_parquet(rais_p)
    pam_df = pl.read_parquet(pam_p)

    r_avg = rais_df.group_by("id_municipio").agg(
        pl.col("prop_linach").mean().alias("prop_linach_mean")
    )
    p_avg = pam_df.group_by("id_municipio").agg(
        pl.col("area_total_lavouras_criticas_ha").mean().alias("area_agro_mean")
    )

    enriched = (
        df.join(r_avg, on="id_municipio", how="left")
        .join(p_avg, on="id_municipio", how="left")
        .fill_null(0.0)
    )
    enriched = enriched.with_columns(
        (pl.col("area_agro_mean") / pl.col("populacao_estimada")).alias(
            "agro_ha_pc"
        )
    )

    candidatos = enriched.filter(pl.col("perfil_amostral") == "3_Acima_50k")
    if candidatos.is_empty():
        return df

    q_linach = candidatos["prop_linach_mean"].quantile(
        spec.sampling.internal_controls.max_prop_linach_quantile
    )
    q_agro = candidatos["agro_ha_pc"].quantile(
        spec.sampling.internal_controls.max_agro_ha_pc_quantile
    )

    if q_linach is None or q_agro is None:
        return df

    ctrl_ids = set(
        enriched.filter(
            (pl.col("perfil_amostral") == "3_Acima_50k")
            & (pl.col("prop_linach_mean") <= q_linach)
            & (pl.col("agro_ha_pc") <= q_agro)
        )["id_municipio"].to_list()
    )

    logger.info(
        f"Estrato 4 ('4_Controle_Interno') materializado: {len(ctrl_ids)} municípios "
        f"[Q25 LINACH: {q_linach:.4f} | Q25 Agro ha/hab: {q_agro:.4f}]"
    )

    return df.with_columns(
        pl.when(pl.col("id_municipio").is_in(list(ctrl_ids)))
        .then(pl.lit("4_Controle_Interno"))
        .otherwise(pl.col("perfil_amostral"))
        .alias("perfil_amostral")
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
    df_valid = apply_internal_controls(df_valid, env, spec)
    df_valid = MUNICIPIOS_CONTRACT.enforce(df_valid)

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

    # 4. Registro no Manifesto de Linhagem (Pilar III & Reprodutibilidade)
    tracker = LineageTracker(manifest_path=env.staging_dir / "manifest.json")
    tracker.record_artifact(
        artifact_name="diretorio_municipios_full",
        parquet_path=full_path,
        df=df_valid,
        sql_path=sql_file,
        parameters={
            "base_year_pop": spec.sampling.base_year_pop,
            "min_populacao": spec.sampling.min_population,
            "excluded_municipios": spec.sampling.excluded_municipios,
        },
    )
    tracker.record_artifact(
        artifact_name="municipios_recorte_tabfm",
        parquet_path=sample_path,
        df=df_sample,
        sql_path=sql_file,
        parameters={
            "base_year_pop": spec.sampling.base_year_pop,
            "min_populacao": spec.sampling.min_population,
            "polos_estrategicos": spec.sampling.all_hub_ids,
        },
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
