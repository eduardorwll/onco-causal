# src/core/contracts.py
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

import polars as pl


@dataclass(frozen=True)
class DataContract:
    """Contrato imutável de governança, tipagem e qualidade para artefatos Parquet (Pilar III)."""

    name: str
    primary_keys: tuple[str, ...]
    required_schema: Mapping[str, pl.DataType | type[pl.DataType]]
    sentinel_null_values: Mapping[str, list[Any]] = field(default_factory=dict)

    def enforce(self, df: pl.DataFrame) -> pl.DataFrame:
        """Aplica validação estrita de schema, expurgo de sentinelas e integridade de PK."""
        if df.is_empty():
            raise ValueError(f"[{self.name}] Violação de contrato: DataFrame vazio.")

        # 1. Verifica presença de todas as colunas obrigatórias
        for col_name in self.required_schema:
            if col_name not in df.columns:
                raise ValueError(
                    f"[{self.name}] Coluna obrigatória ausente: '{col_name}'"
                )

        # 2. Converte tipos conforme schema estrito
        cast_exprs = [
            pl.col(col).cast(dtype) for col, dtype in self.required_schema.items()
        ]
        df = df.with_columns(cast_exprs)

        # 3. Limpeza semântica anti-cegueira: substitui valores sentinela por Null explícito
        sentinel_exprs = []
        for col, raw_vals in self.sentinel_null_values.items():
            if col in df.columns:
                col_type = df.schema[col]
                typed_vals: list[Any] = []
                for v in raw_vals:
                    try:
                        if col_type in (pl.Int64, pl.Int32, pl.Int16, pl.Int8):
                            typed_vals.append(int(v))
                        elif col_type in (pl.Float64, pl.Float32):
                            typed_vals.append(float(v))
                        else:
                            typed_vals.append(str(v))
                    except ValueError, TypeError:
                        typed_vals.append(v)
                sentinel_exprs.append(
                    pl.when(pl.col(col).is_in(typed_vals))
                    .then(None)
                    .otherwise(pl.col(col))
                    .alias(col)
                )

        if sentinel_exprs:
            df = df.with_columns(sentinel_exprs)

        # 4. Validação estrita da Chave Primária (Universal PK)
        for pk in self.primary_keys:
            if pk not in df.columns:
                raise ValueError(
                    f"[{self.name}] Coluna de Chave Primária ausente: '{pk}'"
                )

            null_count = df[pk].null_count()
            if null_count > 0:
                raise ValueError(
                    f"[{self.name}] Chave primária '{pk}' contém {null_count} valores nulos."
                )

            # Regra universal: id_municipio deve ter exatamente 7 dígitos numéricos
            if pk == "id_municipio" and df.schema["id_municipio"] == pl.String:
                invalid_len = df.filter(
                    pl.col("id_municipio").str.len_bytes() != 7
                ).height
                if invalid_len > 0:
                    raise ValueError(
                        f"[{self.name}] '{pk}' contém {invalid_len} registros fora do padrão IBGE de 7 dígitos."
                    )
                non_numeric = df.filter(
                    ~pl.col("id_municipio").str.contains(r"^[0-9]{7}$")
                ).height
                if non_numeric > 0:
                    raise ValueError(
                        f"[{self.name}] '{pk}' contém {non_numeric} registros com caracteres não numéricos."
                    )

        # 5. Validação de unicidade da chave primária (individual ou composta)
        if df.select(list(self.primary_keys)).is_duplicated().any():
            dup_count = df.select(list(self.primary_keys)).is_duplicated().sum()
            raise ValueError(
                f"[{self.name}] Violação de unicidade: {dup_count} registros duplicados para PK {self.primary_keys}."
            )

        return df


# --- Contratos Declarativos Oficiais do Pipeline (Pilares III & IV) ---

RAIS_LINACH_CONTRACT = DataContract(
    name="rais_linach_anual",
    primary_keys=("id_municipio", "ano"),
    required_schema={
        "id_municipio": pl.String,
        "ano": pl.Int64,
        "vinculos_totais": pl.Int64,
        "vinculos_linach": pl.Int64,
        "prop_linach": pl.Float64,
    },
    sentinel_null_values={
        "vinculos_totais": [-1, 999999],
        "vinculos_linach": [-1, 999999],
    },
)

PAM_LAVOURAS_CONTRACT = DataContract(
    name="pam_lavouras_anual",
    primary_keys=("id_municipio", "ano"),
    required_schema={
        "id_municipio": pl.String,
        "ano": pl.Int64,
        "area_soja_ha": pl.Float64,
        "area_milho_ha": pl.Float64,
        "area_algodao_ha": pl.Float64,
        "area_cana_ha": pl.Float64,
        "area_arroz_ha": pl.Float64,
        "area_citros_ha": pl.Float64,
        "area_total_lavouras_criticas_ha": pl.Float64,
    },
    sentinel_null_values={
        "area_total_lavouras_criticas_ha": [-1.0, 999999.0],
    },
)

CONTROLES_ASSISTENCIAIS_CONTRACT = DataContract(
    name="controles_assistenciais_snis",
    primary_keys=("id_municipio", "ano"),
    required_schema={
        "id_municipio": pl.String,
        "ano": pl.Int64,
        "unacon_cacon_ativos": pl.Int64,
        "leitos_totais": pl.Int64,
        "tomografos_ativos": pl.Int64,
        "mamografos_ativos": pl.Int64,
        "indice_atendimento_total_agua": pl.Float64,
        "indice_coleta_esgoto": pl.Float64,
        "indice_tratamento_esgoto": pl.Float64,
    },
    sentinel_null_values={
        "indice_atendimento_total_agua": [-1.0, 999.0, 9999.0],
        "indice_coleta_esgoto": [-1.0, 999.0, 9999.0],
        "indice_tratamento_esgoto": [-1.0, 999.0, 9999.0],
    },
)

SIM_MORTALIDADE_CONTRACT = DataContract(
    name="sim_taxas_padronizadas",
    primary_keys=("id_municipio", "ano", "target_cancer"),
    required_schema={
        "id_municipio": pl.String,
        "ano": pl.Int64,
        "target_cancer": pl.String,
        "obitos_totais": pl.Int64,
        "populacao_total": pl.Int64,
        "asr_omsworld_100k": pl.Float64,
        "obitos_esperados_smr": pl.Float64,
        "smr_razao": pl.Float64,
    },
    sentinel_null_values={
        "obitos_totais": [-1],
    },
)
