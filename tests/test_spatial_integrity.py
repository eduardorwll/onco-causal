# tests/test_spatial_integrity.py
from __future__ import annotations

import geopandas as gpd
import libpysal
import numpy as np
import polars as pl
import pytest
from esda.moran import Moran
from scipy.spatial.distance import cdist
from shapely.geometry import Point
from sklearn.linear_model import Ridge

from src.core.contracts import (
    SIM_TAXAS_SUAVIZADAS_EB_CONTRACT,
    SPATIAL_CV_FOLDS_CONTRACT,
    SPATIAL_GEOMETRIES_CONTRACT,
)
from src.core.settings import DomainSpec, EnvSettings


@pytest.fixture(scope="module")
def env() -> EnvSettings:
    return EnvSettings()


@pytest.fixture(scope="module")
def spec() -> DomainSpec:
    return DomainSpec.from_yaml()


@pytest.fixture(scope="module")
def df_geo(env: EnvSettings) -> pl.DataFrame:
    path = env.staging_dir / "spatial_municipios_ottobacias.parquet"
    assert path.exists(), f"Artefato não encontrado: {path}"
    return pl.read_parquet(path)


@pytest.fixture(scope="module")
def df_eb(env: EnvSettings) -> pl.DataFrame:
    path = env.staging_dir / "sim_taxas_suavizadas_eb.parquet"
    assert path.exists(), f"Artefato não encontrado: {path}"
    return pl.read_parquet(path)


@pytest.fixture(scope="module")
def df_folds(env: EnvSettings) -> pl.DataFrame:
    path = env.staging_dir / "spatial_cv_folds.parquet"
    assert path.exists(), f"Artefato não encontrado: {path}"
    return pl.read_parquet(path)


@pytest.mark.data_contract
def test_spatial_geometries_contract(df_geo: pl.DataFrame) -> None:
    """Valida o contrato de dados das Sedes Municipais e Ottobacias Nível 4."""
    # 1. Aplicação do contrato estrito
    validated = SPATIAL_GEOMETRIES_CONTRACT.enforce(df_geo)
    assert validated.height == 5570, "A malha nacional deve conter exatamente 5.570 municípios."

    # 2. Ausência total de nulos nas colunas geoespaciais
    assert df_geo["ottobacia_id"].null_count() == 0, "Nenhum município pode ter ottobacia_id nulo."
    assert df_geo["latitude_sede"].null_count() == 0
    assert df_geo["longitude_sede"].null_count() == 0
    assert df_geo["x_proj_5070"].null_count() == 0
    assert df_geo["y_proj_5070"].null_count() == 0

    # 3. Unicidade de chave primária
    assert df_geo["id_municipio"].n_unique() == 5570

    # 4. Verificação de cobertura de bacias hidrográficas
    num_bacias = df_geo["ottobacia_id"].n_unique()
    assert num_bacias >= 500, f"Esperado ao menos 500 Ottobacias Nível 4 no Brasil, obtido {num_bacias}"


@pytest.mark.data_contract
def test_empirical_bayes_variance_reduction(
    df_eb: pl.DataFrame, env: EnvSettings
) -> None:
    """Comprova a redução de variância e o encolhimento para prior regional via PySAL."""
    # 1. Validação contratual
    validated = SIM_TAXAS_SUAVIZADAS_EB_CONTRACT.enforce(df_eb)
    assert validated.height == 83550  # 5570 mun * 3 anos * 5 targets

    # 2. Ausência de valores infinitos ou nulos
    assert not np.any(np.isnan(df_eb["smr_suavizada_eb"].to_numpy()))
    assert not np.any(np.isinf(df_eb["smr_suavizada_eb"].to_numpy()))
    min_val: float = float(df_eb.select(pl.col("smr_suavizada_eb").min()).item())
    assert min_val >= 0.0

    # 3. Pesos de encolhimento limitados no intervalo [0, 1]
    w_vals = df_eb["peso_encolhimento_w"].to_numpy()
    assert np.all(w_vals >= 0.0)
    assert np.all(w_vals <= 1.0)

    # 4. Prova Empírica: Redução substancial de variância em pequenos municípios (<10k hab)
    df_pop = pl.read_parquet(env.staging_dir / "diretorio_municipios_full.parquet").select(
        ["id_municipio", "populacao_estimada"]
    )
    df_merged = df_eb.join(df_pop, on="id_municipio", how="left")

    small_mun = df_merged.filter(pl.col("populacao_estimada") < 10000)
    large_mun = df_merged.filter(pl.col("populacao_estimada") > 100000)

    std_crude_small: float = float(small_mun.select(pl.col("smr_bruta").std()).item())
    std_eb_small: float = float(small_mun.select(pl.col("smr_suavizada_eb").std()).item())

    # A variância da SMR suavizada deve ser expressivamente menor que a da SMR bruta em pequenos municípios
    assert std_eb_small < std_crude_small
    reduc_pct = (1.0 - (std_eb_small / std_crude_small)) * 100.0
    assert reduc_pct > 50.0, f"Redução de desvio padrão em pequenas áreas foi de {reduc_pct:.1f}%, esperado > 50%"

    # O peso médio de encolhimento em cidades grandes deve ser superior ao de cidades pequenas
    mean_w_small: float = float(small_mun.select(pl.col("peso_encolhimento_w").mean()).item())
    mean_w_large: float = float(large_mun.select(pl.col("peso_encolhimento_w").mean()).item())
    assert mean_w_large > mean_w_small, f"Esperado w_large ({mean_w_large:.3f}) > w_small ({mean_w_small:.3f})"


@pytest.mark.data_contract
def test_nested_spatial_block_cv_integrity(df_folds: pl.DataFrame) -> None:
    """Valida a independência topológica das Ottobacias e balanceamento dos estratos no 5-Fold SBCV."""
    # 1. Contrato
    validated = SPATIAL_CV_FOLDS_CONTRACT.enforce(df_folds)
    assert validated.height == 685 * 5

    # 2. Disjunção estrita de bacias em cada fold
    for fold_id in range(5):
        fold_data = df_folds.filter(pl.col("fold_id") == fold_id)
        test_bacias = set(fold_data.filter(pl.col("split_role") == "test")["ottobacia_id"])
        train_bacias = set(fold_data.filter(pl.col("split_role") == "train")["ottobacia_id"])

        overlap = test_bacias.intersection(train_bacias)
        assert len(overlap) == 0, (
            f"[Fold {fold_id}] Vazamento topológico: {len(overlap)} bacias compartilhadas entre treino e teste."
        )

        # 3. Representatividade de estratos analíticos no conjunto de teste
        test_estratos = set(fold_data.filter(pl.col("split_role") == "test")["perfil_amostral"])
        assert "1_Capital" in test_estratos
        assert "2_Polo_Estrategico" in test_estratos
        assert "3_Acima_50k" in test_estratos
        assert "4_Controle_Interno" in test_estratos


@pytest.mark.data_contract
def test_dead_zone_buffer_and_spatial_leakage(
    df_folds: pl.DataFrame, df_geo: pl.DataFrame, df_eb: pl.DataFrame
) -> None:
    """Comprova matematicamente que a Dead-Zone de 30 km anula o vazamento de contiguidade imediata."""
    # Avalia os 5 folds
    for fold_id in range(5):
        fold_df = df_folds.filter(pl.col("fold_id") == fold_id)

        # 1. Todo município em 'train' deve ter distância mínima >= 30.0 km do teste
        train_dists = fold_df.filter(pl.col("split_role") == "train")["dist_km_fronteira_teste"].to_numpy()
        assert np.all(train_dists >= 30.0), f"[Fold {fold_id}] Violação da dead-zone: existem pontos de treino a <30km"

        # 2. Todo município em 'buffer_exclusion' deve estar no raio < 30.0 km
        buffer_dists = fold_df.filter(pl.col("split_role") == "buffer_exclusion")["dist_km_fronteira_teste"].to_numpy()
        assert np.all(buffer_dists < 30.0), f"[Fold {fold_id}] Município marcado indevidamente no buffer"
        assert len(buffer_dists) > 0, f"[Fold {fold_id}] Dead-zone deve conter municípios excluídos"

    # 3. Teste de Autocorrelação Residual e Spillover Espacial (Fold 0)
    fold_0 = (
        df_folds.filter(pl.col("fold_id") == 0)
        .join(df_geo, on="id_municipio", how="inner")
        .join(
            df_eb.filter(
                (pl.col("ano") == 2022)
                & (pl.col("target_cancer") == "hematologico_infantojuvenil")
            ),
            on="id_municipio",
            how="inner",
        )
    )

    test = fold_0.filter(pl.col("split_role") == "test")
    clean_train = fold_0.filter(pl.col("split_role") == "train")
    buffer_pts = fold_0.filter(pl.col("split_role") == "buffer_exclusion")

    test_coords = test[["x_proj_5070", "y_proj_5070"]].to_numpy()
    clean_coords = clean_train[["x_proj_5070", "y_proj_5070"]].to_numpy()
    buffer_coords = buffer_pts[["x_proj_5070", "y_proj_5070"]].to_numpy()

    # Distância mínima do teste para o buffer imediato vs para o treino limpo
    min_dist_buffer = cdist(test_coords, buffer_coords).min() / 1000.0
    min_dist_clean = cdist(test_coords, clean_coords).min() / 1000.0

    assert min_dist_buffer < 15.0, "O buffer de teste deve capturar a contiguidade física imediata (<15km)."
    assert min_dist_clean >= 30.0, "O treino limpo deve estar rigorosamente a >= 30 km do teste."

    # 4. Teste de I de Moran sobre os resíduos do modelo no conjunto de teste
    # Ajusta modelo Ridge com coordenadas espaciais
    X_train = clean_train[["x_proj_5070", "y_proj_5070"]].to_numpy()
    y_train = clean_train["smr_suavizada_eb"].to_numpy()

    X_test = test[["x_proj_5070", "y_proj_5070"]].to_numpy()
    y_test = test["smr_suavizada_eb"].to_numpy()

    model = Ridge().fit(X_train, y_train)
    res_test = y_test - model.predict(X_test)

    # Constrói pesos espaciais nos resíduos de teste
    pts_test = [Point(xy) for xy in zip(test["x_proj_5070"], test["y_proj_5070"])]
    gdf_test = gpd.GeoDataFrame(test.to_pandas(), geometry=pts_test, crs="EPSG:5070")
    w_test = libpysal.weights.KNN.from_dataframe(gdf_test, k=4, silence_warnings=True)
    w_test.transform = "R"

    mi = Moran(res_test, w_test)
    # Comprova que o Moran residual na escala local é baixo (I < 0.45) e controlado
    assert abs(mi.I) < 0.45, f"Moran I excessivo nos resíduos: {mi.I}"
