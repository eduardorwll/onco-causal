# src/ingest/sim.py
from __future__ import annotations

import logging
from collections.abc import Sequence

import polars as pl

from src.core.bq_engine import BigQueryEngine
from src.core.contracts import SIM_MORTALIDADE_CONTRACT
from src.core.lineage import LineageTracker
from src.core.settings import DomainSpec, EnvSettings
from src.spatial.age_standardization import compute_standardized_rates

logger = logging.getLogger("onco_causal.ingest.sim")


def run_sim_stage(
    env: EnvSettings,
    spec: DomainSpec,
    engine: BigQueryEngine,
    anos: Sequence[int] = (2020, 2021, 2022),
) -> pl.DataFrame:
    """Extrai óbitos e denominadores etários do SIM/População e calcula taxas padronizadas."""
    env.staging_dir.mkdir(parents=True, exist_ok=True)
    sql_file = env.sql_dir / "05_sim_mortalidade_padronizada.sql"

    logger.info(
        f"Iniciando ingestão SIM e Padronização Etária para anos {list(anos)}..."
    )
    standardized_dfs: list[pl.DataFrame] = []

    for ano in anos:
        logger.info(f"Extraindo dados estratificados SIM/IBGE para o ano {ano}...")
        df_strata = engine.query_from_file(
            sql_path=sql_file,
            params={
                "ano": ano,
                "excluded_municipios": spec.sampling.excluded_municipios,
            },
            use_cache=spec.bigquery.use_cache,
        )

        logger.info(
            f"Calculando ASR (OMS Mundial) e SMR para o ano {ano} ({df_strata.height:,} estratos)..."
        )
        df_rates_ano = compute_standardized_rates(df_strata)
        standardized_dfs.append(df_rates_ano)

    df_combined = pl.concat(standardized_dfs).sort(["id_municipio", "ano", "target_cancer"])

    # 1. Validação estrita por contrato (Pilar III)
    df_valid = SIM_MORTALIDADE_CONTRACT.enforce(df_combined)

    # 2. Persistência Parquet Zstandard (Pilar IV)
    out_path = env.staging_dir / "sim_taxas_padronizadas_5570.parquet"
    df_valid.write_parquet(out_path, compression="zstd")
    logger.info(
        f"Artefato salvo: {out_path} ({df_valid.height:,} registros | {df_valid['ano'].n_unique()} anos | {df_valid['id_municipio'].n_unique()} municípios)"
    )

    # 3. Registro no Manifesto de Linhagem
    tracker = LineageTracker(manifest_path=env.staging_dir / "manifest.json")
    tracker.record_artifact(
        artifact_name="sim_taxas_padronizadas_5570",
        parquet_path=out_path,
        df=df_valid,
        sql_path=sql_file,
        parameters={"anos": list(anos)},
    )

    return df_valid


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    env = EnvSettings()
    spec = DomainSpec.from_yaml()
    engine = BigQueryEngine(explicit_project_id=env.gcp_project_id, max_bytes_billed=spec.bigquery.max_bytes_billed)
    # Por padrão executa o triênio 2020-2022
    run_sim_stage(env, spec, engine, anos=[2020, 2021, 2022])


if __name__ == "__main__":
    main()
