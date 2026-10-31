# src/features/latency_builder.py
"""Módulo de Engenharia de Atributos Defasados (Distributed Lags) e Painel Analítico Mestre (Stage 04B).

Implementa:
- Janelas de latência biológica [t - L_max, t - L_min] específicas por alvo oncológico.
- Normalização relativa de intensidade agroquímica e de solo (ha / área municipal) e tendência OLS.
- Assimetria temporal estrita (proibição de exposição contemporânea ao ano t).
- Triagem de colinearidade no Discovery Set (VIF < 5.0 e |rho_s| < 0.70).
- Construção, validação por DataContract e persistência do master_analytical_panel.parquet.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
import polars as pl
from statsmodels.stats.outliers_influence import variance_inflation_factor
from statsmodels.tools.tools import add_constant

from src.core.contracts import MASTER_PANEL_CONTRACT
from src.core.lineage import LineageTracker
from src.core.settings import DomainSpec

logger = logging.getLogger("onco_causal.features.latency")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Features utilizadas na modelagem e na validação de VIF/Spearman
MODELING_FEATURE_COLUMNS = [
    "prop_lavouras_criticas_mean",
    "prop_lavouras_criticas_trend",
    "prop_floresta_mean",
    "prop_urbanizada_mean",
    "prop_linach_mean",
    "prop_linach_trend",
    "unacon_cacon_ativos",
    "leitos_pc_100k",
    "tomografos_pc_100k",
    "mamografos_pc_100k",
    "indice_atendimento_total_agua",
    "indice_coleta_esgoto",
    "indice_tratamento_esgoto",
]


def compute_vif_and_correlations(
    df_discovery: pl.DataFrame,
    features: list[str] | None = None,
    vif_threshold: float = 5.0,
    spearman_threshold: float = 0.70,
) -> tuple[pd.Series, list[tuple[str, str, float]]]:
    """Calcula VIF e correlação par-a-par de Spearman no Discovery Set, validando ausência de colinearidade."""
    feat_cols = features or MODELING_FEATURE_COLUMNS
    pdf = df_discovery.select(feat_cols).to_pandas().dropna()

    # VIF
    x_matrix = add_constant(pdf)
    vifs = pd.Series(
        [variance_inflation_factor(x_matrix.values, i) for i in range(x_matrix.shape[1])],
        index=x_matrix.columns,
    )
    max_vif = float(vifs.drop("const").max())
    logger.info("VIF Máximo no Discovery Set: %.4f (Teto: < %.1f)", max_vif, vif_threshold)

    if max_vif >= vif_threshold:
        raise ValueError(
            f"Violação de colinearidade no Discovery Set: VIF máximo de {max_vif:.4f} excede teto {vif_threshold}"
        )

    # Spearman
    corr = pdf.corr(method="spearman")
    high_corr: list[tuple[str, str, float]] = []
    for i in range(len(corr.columns)):
        for j in range(i + 1, len(corr.columns)):
            c1, c2 = corr.columns[i], corr.columns[j]
            val = float(abs(corr.iloc[i, j]))
            if val >= spearman_threshold:
                high_corr.append((c1, c2, val))

    logger.info("Pares com |rho_s| >= %.2f no Discovery Set: %d", spearman_threshold, len(high_corr))
    if high_corr:
        raise ValueError(f"Violação de redundância no Discovery Set: {high_corr}")

    return vifs, high_corr


def build_master_panel(
    data_dir: Path | str | None = None,
    output_path: Path | str | None = None,
    manifest_path: Path | str | None = None,
) -> pl.DataFrame:
    """Orquestra a construção do Painel Analítico Mestre com lags distribuídos e controles contemporâneos."""
    base_dir = Path(data_dir) if data_dir else Path("data")
    staging_dir = base_dir / "staging"
    features_dir = base_dir / "features"
    features_dir.mkdir(parents=True, exist_ok=True)

    dest_path = Path(output_path) if output_path else features_dir / "master_analytical_panel.parquet"
    mnf_path = Path(manifest_path) if manifest_path else staging_dir / "manifest.json"

    logger.info("--- Iniciando Stage 04B: Engenharia de Lags e Master Panel ---")
    domain_spec = DomainSpec.from_yaml()

    # 1. Carregar artefatos de base
    recorte = pl.read_parquet(staging_dir / "municipios_recorte_tabfm.parquet")
    m_ids = recorte["id_municipio"].to_list()
    pop_dict = dict(zip(recorte["id_municipio"].to_list(), recorte["populacao_estimada"].to_list(), strict=False))

    spatial = pl.read_parquet(staging_dir / "spatial_municipios_ottobacias.parquet")
    pam = pl.read_parquet(staging_dir / "pam_lavouras_anual.parquet")
    mb = pl.read_parquet(staging_dir / "mapbiomas_cobertura_anual.parquet")
    rais = pl.read_parquet(staging_dir / "rais_linach_anual.parquet")
    ctrl = pl.read_parquet(staging_dir / "controles_assistenciais_snis.parquet").filter(
        pl.col("id_municipio").is_in(m_ids)
    )
    sim = pl.read_parquet(staging_dir / "sim_taxas_suavizadas_eb.parquet")
    cv = pl.read_parquet(staging_dir / "spatial_cv_folds.parquet")

    # 2. Computar área total média por município via MapBiomas (hectares)
    mb_area = mb.with_columns(
        (
            pl.col("area_agricultura_ha")
            + pl.col("area_pastagem_ha")
            + pl.col("area_silvicultura_ha")
            + pl.col("area_urbanizada_ha")
            + pl.col("area_floresta_ha")
        ).alias("area_total_ha")
    )
    mun_area_df = mb_area.group_by("id_municipio").agg(pl.col("area_total_ha").mean().alias("area_mun_ha"))
    area_dict = dict(zip(mun_area_df["id_municipio"].to_list(), mun_area_df["area_mun_ha"].to_list(), strict=False))

    # 3. Construir grade anual integral (1998–2022) para todos os 685 municípios analíticos
    years = list(range(1998, 2023))
    grid = pl.DataFrame({"id_municipio": m_ids}).join(pl.DataFrame({"ano": years}), how="cross")

    annual = grid.join(pam, on=["id_municipio", "ano"], how="left")
    annual = annual.join(mb, on=["id_municipio", "ano"], how="left")
    annual = annual.join(rais, on=["id_municipio", "ano"], how="left")

    annual = annual.with_columns([
        pl.col("area_total_lavouras_criticas_ha").fill_null(0.0),
        pl.col("area_floresta_ha").fill_null(0.0),
        pl.col("area_urbanizada_ha").fill_null(0.0),
        pl.col("vinculos_totais").fill_null(0),
        pl.col("vinculos_linach").fill_null(0),
        pl.col("id_municipio").replace_strict(pop_dict).cast(pl.Float64).alias("pop"),
        pl.col("id_municipio").replace_strict(area_dict).cast(pl.Float64).alias("area_ha"),
    ])

    # Salvaguarda 2: Intensidade Relativa (proporção da área territorial do município)
    annual = annual.with_columns([
        (pl.col("area_total_lavouras_criticas_ha") / pl.col("area_ha")).clip(0.0, 1.0).alias("prop_lavouras_criticas"),
        (pl.col("area_floresta_ha") / pl.col("area_ha")).clip(0.0, 1.0).alias("prop_floresta"),
        (pl.col("area_urbanizada_ha") / pl.col("area_ha")).clip(0.0, 1.0).alias("prop_urbanizada"),
        pl.when(pl.col("vinculos_totais") > 0)
        .then(pl.col("vinculos_linach") / pl.col("vinculos_totais"))
        .otherwise(0.0)
        .alias("prop_linach"),
    ])

    # 4. Processamento dos lags biológicos por alvo oncológico e triênio de desfecho (2020–2022)
    feature_cols = ["prop_lavouras_criticas", "prop_floresta", "prop_urbanizada", "prop_linach"]
    outcome_years = [2020, 2021, 2022]

    panels: list[pl.DataFrame] = []
    for target_key, target_info in domain_spec.oncology_targets.items():
        l_min, l_max = target_info.lag_window_years[0], target_info.lag_window_years[1]
        for t in outcome_years:
            tau_min = t - l_max
            tau_max = t - l_min

            # Filtrar intervalo defasado sem exposição contemporânea
            sub = annual.filter((pl.col("ano") >= tau_min) & (pl.col("ano") <= tau_max))

            aggs = []
            for col in feature_cols:
                aggs.append(pl.col(col).mean().fill_null(0.0).alias(f"{col}_mean"))
                aggs.append(pl.col(col).max().fill_null(0.0).alias(f"{col}_max"))
                # Tendência OLS: Cov(ano, X) / Var(ano)
                aggs.append((pl.cov("ano", col) / pl.var("ano")).fill_null(0.0).alias(f"{col}_trend"))

            grp = (
                sub.group_by("id_municipio")
                .agg(aggs)
                .with_columns([
                    pl.lit(t).cast(pl.Int64).alias("ano"),
                    pl.lit(target_key).alias("target_cancer"),
                ])
            )
            panels.append(grp)

    lag_panel = pl.concat(panels)

    # 5. Normalizar controles contemporâneos (CNES/SNIS 2020)
    ctrl_norm = ctrl.with_columns([
        (
            pl.col("leitos_totais")
            / (pl.col("id_municipio").replace_strict(pop_dict).cast(pl.Float64) / 100000.0)
        ).alias("leitos_pc_100k"),
        (
            pl.col("tomografos_ativos")
            / (pl.col("id_municipio").replace_strict(pop_dict).cast(pl.Float64) / 100000.0)
        ).alias("tomografos_pc_100k"),
        (
            pl.col("mamografos_ativos")
            / (pl.col("id_municipio").replace_strict(pop_dict).cast(pl.Float64) / 100000.0)
        ).alias("mamografos_pc_100k"),
        pl.col("indice_atendimento_total_agua").fill_null(pl.col("indice_atendimento_total_agua").median()),
        pl.col("indice_coleta_esgoto").fill_null(pl.col("indice_coleta_esgoto").median()),
        pl.col("indice_tratamento_esgoto").fill_null(pl.col("indice_tratamento_esgoto").median()),
    ]).select([
        "id_municipio",
        "unacon_cacon_ativos",
        "leitos_pc_100k",
        "tomografos_pc_100k",
        "mamografos_pc_100k",
        "indice_atendimento_total_agua",
        "indice_coleta_esgoto",
        "indice_tratamento_esgoto",
    ])

    # 6. Desfechos SIM EB
    sim_cohort = sim.filter(
        (pl.col("id_municipio").is_in(m_ids)) & (pl.col("ano").is_in(outcome_years))
    ).select([
        "id_municipio",
        "ano",
        "target_cancer",
        "smr_suavizada_eb",
        "smr_bruta",
        "obitos_observados",
        "obitos_esperados",
        "peso_encolhimento_w",
    ])

    # 7. Metadados espaciais e demográficos
    recorte_meta = recorte.select([
        "id_municipio",
        "nome_municipio",
        "sigla_uf",
        "perfil_amostral",
        "populacao_estimada",
    ])
    spatial_meta = spatial.select([
        "id_municipio",
        "ottobacia_id",
        "latitude_sede",
        "longitude_sede",
        "x_proj_5070",
        "y_proj_5070",
    ])
    area_meta = mun_area_df.select(["id_municipio", "area_mun_ha"])

    # 8. Montagem do Painel Analítico Mestre
    master_df = sim_cohort.join(lag_panel, on=["id_municipio", "ano", "target_cancer"], how="inner")
    master_df = master_df.join(ctrl_norm, on="id_municipio", how="left")
    master_df = master_df.join(recorte_meta, on="id_municipio", how="left")
    master_df = master_df.join(spatial_meta, on="id_municipio", how="left")
    master_df = master_df.join(area_meta, on="id_municipio", how="left")

    logger.info("Painel Mestre montado: %d linhas, %d colunas", master_df.height, master_df.width)

    # 9. Triagem de colinearidade estrita no Discovery Set (Folds 0 e 1, 40% das bacias)
    disc_muns = (
        cv.filter((pl.col("fold_id").is_in([0, 1])) & (pl.col("split_role") == "test"))["id_municipio"]
        .unique()
        .to_list()
    )
    disc_df = master_df.filter(pl.col("id_municipio").is_in(disc_muns))
    logger.info("Avaliando colinearidade no Discovery Set (%d municípios)...", len(disc_muns))
    vifs, _ = compute_vif_and_correlations(disc_df, vif_threshold=5.0, spearman_threshold=0.70)

    # 10. Validação do DataContract
    logger.info("Validando contrato MASTER_PANEL_CONTRACT...")
    master_df = MASTER_PANEL_CONTRACT.enforce(master_df)

    # 11. Persistência em Parquet e Manifesto
    master_df.write_parquet(dest_path, compression="zstd")
    logger.info("Painel Mestre salvo com sucesso em: %s", dest_path)

    lineage = LineageTracker(manifest_path=mnf_path)
    entry = lineage.record_artifact(
        artifact_name=MASTER_PANEL_CONTRACT.name,
        parquet_path=dest_path,
        df=master_df,
        parameters={
            "outcome_years": outcome_years,
            "cancer_targets": list(domain_spec.oncology_targets.keys()),
            "analytical_cohort_size": len(m_ids),
            "discovery_set_size": len(disc_muns),
            "max_discovery_vif": float(vifs.drop("const").max()),
        },
    )
    logger.info("Linhagem criptográfica registrada no manifest.json (SHA-256: %s)", entry["sha256"][:12])

    return master_df


if __name__ == "__main__":
    build_master_panel()
