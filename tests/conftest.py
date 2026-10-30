# tests/conftest.py
from __future__ import annotations

import polars as pl
import pytest

from src.core.settings import DomainSpec, EnvSettings


@pytest.fixture(scope="session")
def env() -> EnvSettings:
    return EnvSettings()


@pytest.fixture(scope="session")
def spec() -> DomainSpec:
    return DomainSpec.from_yaml()


@pytest.fixture
def synthetic_valid_municipios_df() -> pl.DataFrame:
    """Fixture sintética em memória de municípios válidos (para testes unitários rápidos sem IO)."""
    return pl.DataFrame({
        "id_municipio": ["1100015", "1100023", "3550308", "5107875", "4322004"],
        "id_municipio_6": ["110001", "110002", "355030", "510787", "432200"],
        "nome_municipio": [
            "Alta Floresta D'Oeste",
            "Ariquemes",
            "São Paulo",
            "Sapezal",
            "Triunfo",
        ],
        "sigla_uf": ["RO", "RO", "SP", "MT", "RS"],
        "id_mesorregiao": ["1102", "1102", "3515", "5103", "4305"],
        "id_microrregiao": ["11006", "11003", "35061", "51009", "43027"],
        "populacao_estimada": [22728, 107863, 12396372, 25882, 29856],
        "perfil_amostral": [
            "4_Pequeno_Porte",
            "3_Acima_50k",
            "1_Capital",
            "2_Polo_Estrategico",
            "2_Polo_Estrategico",
        ],
    })


@pytest.fixture
def synthetic_sentinel_df() -> pl.DataFrame:
    """Fixture sintética contendo valores sentinela do DATASUS/SNIS a serem expurgados."""
    return pl.DataFrame({
        "id_municipio": ["1100015", "1100023", "3550308"],
        "id_municipio_6": ["110001", "0", "IGN"],
        "nome_municipio": ["Alta Floresta", "Ariquemes", "São Paulo"],
        "sigla_uf": ["RO", "RO", "SP"],
        "id_mesorregiao": ["1102", "9999", "3515"],
        "id_microrregiao": ["11006", "0", "35061"],
        "populacao_estimada": [22728, 107863, 12396372],
        "perfil_amostral": ["4_Pequeno_Porte", "3_Acima_50k", "1_Capital"],
    })
