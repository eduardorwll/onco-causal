# src/core/bq_engine.py
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import google.auth
import polars as pl
from google.cloud import bigquery

logger = logging.getLogger("onco_causal.bq_engine")


class BigQueryEngine:
    """Motor desacoplado de governança e consulta no BigQuery via Arrow Storage API (Pilar II)."""

    def __init__(
        self,
        explicit_project_id: str | None = None,
        *,
        max_bytes_billed: int,
    ):
        credentials, project_id = self._resolve_credentials_and_project(
            explicit_project_id
        )
        self.credentials = credentials
        self.project_id = project_id
        self.max_bytes_billed = max_bytes_billed
        self.client = bigquery.Client(
            project=self.project_id, credentials=self.credentials
        )
        logger.info(
            f"BigQueryEngine inicializado com sucesso [Projeto GCP: '{self.project_id}' | "
            f"Trava Max Billed: {self.max_bytes_billed / (1024**2):.1f} MB]"
        )

    @classmethod
    def _resolve_credentials_and_project(
        cls, explicit_project_id: str | None = None
    ) -> tuple[Any, str]:
        """Resolve o Project ID real via Google Auth ADC, expurgando o alias 'ai4good'."""
        credentials, adc_project = google.auth.default()

        # 1. Se explicit_project_id for válido e não for o alias 'ai4good', prioriza-o
        if explicit_project_id and explicit_project_id.strip():
            candidate = explicit_project_id.strip()
            if candidate.lower() != "ai4good":
                return credentials, candidate

        # 2. Verifica se as credenciais possuem quota_project_id real
        quota_proj = getattr(credentials, "quota_project_id", None)
        if quota_proj and str(quota_proj).strip().lower() != "ai4good":
            return credentials, str(quota_proj).strip()

        # 3. Verifica adc_project
        if adc_project and str(adc_project).strip().lower() != "ai4good":
            return credentials, str(adc_project).strip()

        # 4. Inspeciona o arquivo application_default_credentials.json diretamente
        adc_file = (
            Path.home() / ".config" / "gcloud" / "application_default_credentials.json"
        )
        if adc_file.exists():
            try:
                data = json.loads(adc_file.read_text(encoding="utf-8"))
                for key in ("quota_project_id", "project_id"):
                    val = data.get(key)
                    if val and str(val).strip().lower() != "ai4good":
                        return credentials, str(val).strip()
            except (OSError, ValueError) as err:
                logger.warning(f"Falha ao ler {adc_file}: {err}")

        # Se não encontrou projeto alternativo, usa adc_project se existir
        if adc_project:
            return credentials, str(adc_project).strip()

        raise RuntimeError(
            "Project ID real do GCP não localizado no ADC. Configure via 'gcloud config set project <PROJECT_ID>'."
        )

    @staticmethod
    def _build_bq_params(
        params: dict[str, Any],
    ) -> list[bigquery.ArrayQueryParameter | bigquery.ScalarQueryParameter]:
        """Mapeia parâmetros Python nativos para QueryParameters do BigQuery."""
        bq_params: list[
            bigquery.ArrayQueryParameter | bigquery.ScalarQueryParameter
        ] = []
        for name, value in params.items():
            if isinstance(value, (list, tuple, set)):
                bq_params.append(
                    bigquery.ArrayQueryParameter(
                        name, "STRING", [str(v) for v in value]
                    )
                )
            elif isinstance(value, int):
                bq_params.append(bigquery.ScalarQueryParameter(name, "INT64", value))
            elif isinstance(value, float):
                bq_params.append(bigquery.ScalarQueryParameter(name, "FLOAT64", value))
            elif isinstance(value, bool):
                bq_params.append(bigquery.ScalarQueryParameter(name, "BOOL", value))
            else:
                bq_params.append(
                    bigquery.ScalarQueryParameter(name, "STRING", str(value))
                )
        return bq_params

    def query_from_file(
        self,
        sql_path: Path,
        params: dict[str, Any] | None = None,
        use_cache: bool = True,
    ) -> pl.DataFrame:
        """Executa consulta com Dry-Run obrigatório e Arrow Storage API."""
        if not sql_path.exists():
            raise FileNotFoundError(f"Arquivo SQL não encontrado: {sql_path}")

        sql = sql_path.read_text(encoding="utf-8")
        bq_params = self._build_bq_params(params or {})

        # 1. Dry-Run Obrigatório (Governança de Custos)
        dry_cfg = bigquery.QueryJobConfig(
            query_parameters=bq_params,
            dry_run=True,
            use_query_cache=use_cache,
        )
        dry_job = self.client.query(sql, job_config=dry_cfg)
        bytes_processed = dry_job.total_bytes_processed or 0
        mb_processed = bytes_processed / (1024**2)

        logger.info(
            f"[{sql_path.name}] Dry-Run validado com sucesso: {mb_processed:.2f} MB "
            f"({bytes_processed:,} bytes estimados)."
        )

        if bytes_processed > self.max_bytes_billed:
            raise ValueError(
                f"[{sql_path.name}] Query cancelada por exceder a trava de segurança: "
                f"{bytes_processed:,} bytes estimados > {self.max_bytes_billed:,} bytes permitidos."
            )

        # 2. Execução Vetorial com Trava de Bytes Billed e Arrow Storage API
        run_cfg = bigquery.QueryJobConfig(
            query_parameters=bq_params,
            use_query_cache=use_cache,
            maximum_bytes_billed=self.max_bytes_billed,
        )
        query_job = self.client.query(sql, job_config=run_cfg)
        arrow_table = query_job.to_arrow(create_bqstorage_client=True)

        df = pl.from_arrow(arrow_table)
        if isinstance(df, pl.Series):
            df = df.to_frame()

        logger.info(
            f"[{sql_path.name}] Dados transferidos via Arrow: {df.height:,} linhas carregadas."
        )
        return df
