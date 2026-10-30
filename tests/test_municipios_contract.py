# tests/test_municipios_contract.py
from __future__ import annotations

import polars as pl
import pytest

from src.core.contracts import DataContract
from src.core.settings import DomainSpec, EnvSettings
from src.ingest.municipios import MUNICIPIOS_CONTRACT


@pytest.fixture(scope="module")
def env() -> EnvSettings:
    return EnvSettings()


@pytest.fixture(scope="module")
def spec() -> DomainSpec:
    return DomainSpec.from_yaml()


@pytest.fixture(scope="module")
def df_full(env: EnvSettings) -> pl.DataFrame:
    path = env.staging_dir / "diretorio_municipios_full.parquet"
    assert path.exists(), (
        f"Artefato não encontrado: {path}. Execute o stage 01 antes dos testes."
    )
    return pl.read_parquet(path)


@pytest.fixture(scope="module")
def df_recorte(env: EnvSettings) -> pl.DataFrame:
    path = env.staging_dir / "municipios_recorte_tabfm.parquet"
    assert path.exists(), (
        f"Artefato não encontrado: {path}. Execute o stage 01 antes dos testes."
    )
    return pl.read_parquet(path)


class TestDiretorioMunicipiosFull:
    """Validações da Malha Nacional Integral (Nível I: N = 5.570 municípios)."""

    def test_municipios_full_exact_count(self, df_full: pl.DataFrame):
        """Garante que a malha nacional possui exatamente 5.570 municípios para o Spatial EB."""
        assert df_full.height == 5570, (
            f"Esperado 5.570 municípios, obtido {df_full.height}"
        )

    def test_municipios_full_pk_integrity(self, df_full: pl.DataFrame):
        """Valida que id_municipio é estritamente não-nulo, único e possui 7 dígitos IBGE."""
        assert df_full["id_municipio"].null_count() == 0, (
            "Chave primária contém valores nulos."
        )
        assert df_full["id_municipio"].n_unique() == 5570, (
            "Chave primária possui duplicatas."
        )

        # Todos os códigos devem ter exatamente 7 caracteres numéricos
        invalid_len = df_full.filter(pl.col("id_municipio").str.len_bytes() != 7)
        assert invalid_len.height == 0, (
            f"{invalid_len.height} municípios com código diferente de 7 dígitos."
        )

        non_digits = df_full.filter(~pl.col("id_municipio").str.contains(r"^[0-9]{7}$"))
        assert non_digits.height == 0, (
            f"{non_digits.height} municípios com caracteres não numéricos."
        )

    def test_municipios_full_passes_contract(self, df_full: pl.DataFrame):
        """Verifica se o artefato atende 100% das regras do DataContract."""
        enforced = MUNICIPIOS_CONTRACT.enforce(df_full)
        assert enforced.height == 5570
        assert set(MUNICIPIOS_CONTRACT.required_schema.keys()).issubset(
            set(enforced.columns)
        )

    def test_excluded_municipio_not_present(
        self, df_full: pl.DataFrame, spec: DomainSpec
    ):
        """Garante que municípios excluídos da série histórica (ex: Boa Esperança do Norte) não constam."""
        for ex_id in spec.sampling.excluded_municipios:
            found = df_full.filter(pl.col("id_municipio") == ex_id)
            assert found.height == 0, (
                f"Município excluído {ex_id} não deveria constar na malha 5.570."
            )


class TestMunicipiosRecorteTabFM:
    """Validações do Recorte Analítico TabFM (Nível II: Capitais, Polos e >= 50k hab.)."""

    def test_recorte_isolates_strata_strictly(self, df_recorte: pl.DataFrame):
        """Garante que apenas os estratos 1_Capital, 2_Polo_Estrategico e 3_Acima_50k estão presentes."""
        perfil_vals = set(df_recorte["perfil_amostral"].unique().to_list())
        expected_strata = {"1_Capital", "2_Polo_Estrategico", "3_Acima_50k"}
        assert perfil_vals == expected_strata, (
            f"Estratos divergentes: {perfil_vals} != {expected_strata}"
        )
        assert "4_Pequeno_Porte" not in perfil_vals, (
            "Recorte TabFM não deve conter municípios de pequeno porte."
        )

    def test_recorte_capitais_count(self, df_recorte: pl.DataFrame):
        """Garante a inclusão de exatamente todas as 27 capitais estaduais/DF."""
        capitais = df_recorte.filter(pl.col("perfil_amostral") == "1_Capital")
        assert capitais.height == 27, (
            f"Esperado 27 capitais, encontrado {capitais.height}"
        )

    def test_recorte_strategic_hubs_included(
        self, df_recorte: pl.DataFrame, spec: DomainSpec
    ):
        """Garante que todos os polos agroquímicos e industriais estão no recorte."""
        recorte_ids = set(df_recorte["id_municipio"].to_list())
        for hub_id in spec.sampling.all_hub_ids:
            assert hub_id in recorte_ids, (
                f"Polo estratégico {hub_id} ausente do recorte TabFM."
            )

    def test_recorte_population_threshold_for_stratum_3(
        self, df_recorte: pl.DataFrame, spec: DomainSpec
    ):
        """Garante que o estrato 3_Acima_50k respeita o piso populacional configurado."""
        acima_50k = df_recorte.filter(pl.col("perfil_amostral") == "3_Acima_50k")
        below_min = acima_50k.filter(
            pl.col("populacao_estimada") < spec.sampling.min_population
        )
        assert below_min.height == 0, (
            f"{below_min.height} municípios no estrato 3_Acima_50k possuem população "
            f"abaixo do piso de {spec.sampling.min_population} hab."
        )

    def test_recorte_pk_integrity_and_contract(self, df_recorte: pl.DataFrame):
        """Valida que o recorte analítico passa integralmente no DataContract."""
        assert df_recorte["id_municipio"].null_count() == 0
        assert df_recorte["id_municipio"].n_unique() == df_recorte.height
        enforced = MUNICIPIOS_CONTRACT.enforce(df_recorte)
        assert enforced.height == df_recorte.height


class TestDataContractRobustness:
    """Testes unitários de estresse e casos de borda do motor DataContract."""

    def test_empty_dataframe_raises(self):
        contract = DataContract("test", ("id",), {"id": pl.String})
        with pytest.raises(ValueError, match="DataFrame vazio"):
            contract.enforce(pl.DataFrame())

    def test_missing_column_raises(self):
        contract = DataContract("test", ("id",), {"id": pl.String, "val": pl.Int64})
        with pytest.raises(ValueError, match="Coluna obrigatória ausente"):
            contract.enforce(pl.DataFrame({"id": ["1234567"]}))

    def test_null_pk_raises(self):
        contract = DataContract("test", ("id_municipio",), {"id_municipio": pl.String})
        with pytest.raises(ValueError, match="contém 1 valores nulos"):
            contract.enforce(pl.DataFrame({"id_municipio": [None, "1234567"]}))

    def test_duplicate_pk_raises(self):
        contract = DataContract("test", ("id_municipio",), {"id_municipio": pl.String})
        with pytest.raises(ValueError, match="Violação de unicidade"):
            contract.enforce(pl.DataFrame({"id_municipio": ["1234567", "1234567"]}))

    def test_invalid_ibge_length_raises(self):
        contract = DataContract("test", ("id_municipio",), {"id_municipio": pl.String})
        with pytest.raises(ValueError, match="fora do padrão IBGE de 7 dígitos"):
            contract.enforce(pl.DataFrame({"id_municipio": ["123456"]}))  # 6 dígitos

    def test_sentinel_replacement(self):
        contract = DataContract(
            name="test_sentinel",
            primary_keys=("id_municipio",),
            required_schema={
                "id_municipio": pl.String,
                "status": pl.String,
                "codigo": pl.Int64,
            },
            sentinel_null_values={"status": ["IGN", "99"], "codigo": [9999, -1]},
        )
        raw_df = pl.DataFrame(
            {
                "id_municipio": ["1100015", "1100023", "1100031"],
                "status": ["OK", "IGN", "99"],
                "codigo": [10, 9999, -1],
            }
        )
        clean_df = contract.enforce(raw_df)
        assert clean_df["status"].to_list() == ["OK", None, None]
        assert clean_df["codigo"].to_list() == [10, None, None]


class TestDomainSpecValidation:
    """Garante que a configuração declarativa respeita todas as regras dos Pilares e Metodologia."""

    def test_domain_spec_structure(self, spec: DomainSpec):
        assert spec.bigquery.max_bytes_billed > 0
        assert spec.sampling.min_population == 50_000
        assert spec.sampling.base_year_pop >= 1996
        assert len(spec.sampling.all_hub_ids) >= 10

        # Subgrupos oncológicos com janelas biológicas
        assert "hematologico_infantojuvenil" in spec.oncology_targets
        assert spec.oncology_targets[
            "hematologico_infantojuvenil"
        ].lag_window_years == (2, 5)

        assert "respiratorio" in spec.oncology_targets
        assert spec.oncology_targets["respiratorio"].lag_window_years == (10, 25)

        assert "digestivo" in spec.oncology_targets
        assert spec.oncology_targets["digestivo"].lag_window_years == (10, 20)

        # Grupos CNAE/LINACH
        assert "benzeno_petroquimica" in spec.cnae_linach_groups
        assert len(spec.cnae_linach_groups["benzeno_petroquimica"].cnae_prefixes) > 0


def _ibge_check_digit(code6: str) -> int:
    """Dígito verificador IBGE (módulo 10, pesos 1-2 alternados sobre os 6 primeiros dígitos)."""
    total = 0
    for i, ch in enumerate(code6):
        prod = int(ch) * (1 if i % 2 == 0 else 2)
        total += prod // 10 + prod % 10
    return (10 - total % 10) % 10


class TestIbgeCheckDigit:
    """Auditoria científica: integridade dos códigos IBGE (Sapezal-MT = 5107875, nunca 5107877)."""

    def test_strategic_hubs_have_valid_check_digit(self, spec: DomainSpec):
        for hub_id in spec.sampling.all_hub_ids:
            assert _ibge_check_digit(hub_id[:6]) == int(hub_id[6]), (
                f"DV inválido no polo {hub_id}"
            )

    def test_sapezal_code_is_5107875(self, spec: DomainSpec, df_full: pl.DataFrame):
        assert "5107875" in spec.sampling.all_hub_ids
        assert "5107877" not in spec.sampling.all_hub_ids
        row = df_full.filter(pl.col("id_municipio") == "5107875")
        assert row.height == 1 and row["nome_municipio"][0] == "Sapezal"
        assert df_full.filter(pl.col("id_municipio") == "5107877").height == 0

    def test_full_mesh_check_digit_exceptions_are_rare(self, df_full: pl.DataFrame):
        """Poucos códigos oficiais do IBGE fogem à regra do DV; acima de 20 indica corrupção."""
        invalid = [
            i
            for i in df_full["id_municipio"].to_list()
            if _ibge_check_digit(i[:6]) != int(i[6])
        ]
        assert len(invalid) <= 20, (
            f"{len(invalid)} códigos com DV inválido: {invalid[:5]}"
        )
