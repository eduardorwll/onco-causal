# src/core/settings.py
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class BigQueryConfig(BaseModel):
    max_bytes_billed: int = Field(gt=0)
    use_cache: bool


class InternalControlsConfig(BaseModel):
    min_population: int = 50_000
    max_prop_linach_quantile: float = 0.25
    max_agro_ha_pc_quantile: float = 0.25


class SamplingConfig(BaseModel):
    min_population: int = Field(ge=0)
    base_year_pop: int = Field(ge=1996)
    excluded_municipios: list[str] = Field(default_factory=list)
    strategic_hubs: dict[str, list[str]] = Field(default_factory=dict)
    internal_controls: InternalControlsConfig = Field(
        default_factory=InternalControlsConfig
    )

    @property
    def all_hub_ids(self) -> list[str]:
        seen = set()
        result = []
        for group in self.strategic_hubs.values():
            for mun_id in group:
                clean_id = str(mun_id).strip()
                if clean_id not in seen:
                    seen.add(clean_id)
                    result.append(clean_id)
        return result


class TargetSpec(BaseModel):
    name: str | None = None
    cid10_prefixes: list[str]
    lag_window_years: tuple[int, int]
    description: str | None = None


class CnaeLinachGroup(BaseModel):
    name: str
    cnae_prefixes: list[str]


class DomainSpec(BaseModel):
    bigquery: BigQueryConfig
    sampling: SamplingConfig
    oncology_targets: dict[str, TargetSpec]
    cnae_linach_groups: dict[str, CnaeLinachGroup] = Field(default_factory=dict)

    @classmethod
    def from_yaml(cls, path: Path | None = None) -> DomainSpec:
        cfg_path = path or (PROJECT_ROOT / "configs" / "domain_spec.yaml")
        if not cfg_path.exists():
            raise FileNotFoundError(
                f"Arquivo de especificação não encontrado: {cfg_path}"
            )
        with open(cfg_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return cls.model_validate(data)


class EnvSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    gcp_project_id: str | None = Field(default=None, alias="GOOGLE_CLOUD_PROJECT")
    raw_dir: Path = PROJECT_ROOT / "data" / "raw"
    staging_dir: Path = PROJECT_ROOT / "data" / "staging"
    features_dir: Path = PROJECT_ROOT / "data" / "features"
    sql_dir: Path = PROJECT_ROOT / "sql"
