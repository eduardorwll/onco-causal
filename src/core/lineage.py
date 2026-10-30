# src/core/lineage.py
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import logging
from pathlib import Path
import subprocess
from typing import Any
import polars as pl
from src.core.settings import PROJECT_ROOT

logger = logging.getLogger("onco_causal.core.lineage")


def compute_file_sha256(path: Path) -> str:
    """Calcula o hash SHA-256 de um arquivo em disco em blocos de 64KB."""
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado para cálculo de hash: {path}")
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_git_metadata() -> dict[str, str]:
    """Obtém commit hash e branch Git atual via subprocesso, com fallback seguro."""
    try:
        commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=PROJECT_ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        commit = "unknown"

    try:
        branch = subprocess.check_output(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=PROJECT_ROOT,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
    except Exception:
        branch = "unknown"

    return {"commit": commit, "branch": branch}


class LineageTracker:
    """Registrador determinístico de linhagem e integridade de artefatos (Pilar III & IV)."""

    def __init__(self, manifest_path: Path | None = None):
        self.manifest_path = manifest_path or (
            PROJECT_ROOT / "data" / "staging" / "manifest.json"
        )

    def load_manifest(self) -> dict[str, Any]:
        """Lê o manifesto existente ou retorna estrutura inicial vazia."""
        if self.manifest_path.exists():
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        return data
            except Exception as err:
                logger.warning(
                    f"Falha ao carregar manifesto existente em {self.manifest_path}: {err}. Reiniciando."
                )
        return {
            "version": "1.0",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "artifacts": {},
        }

    def record_artifact(
        self,
        artifact_name: str,
        parquet_path: Path,
        df: pl.DataFrame | None = None,
        sql_path: Path | None = None,
        parameters: dict[str, Any] | None = None,
        domain_spec_path: Path | None = None,
    ) -> dict[str, Any]:
        """Calcula hashes, dimensões e git metadata, gravando a entrada atomicamente no manifesto."""
        if not parquet_path.exists():
            raise FileNotFoundError(
                f"Artefato Parquet não encontrado: {parquet_path}"
            )

        parquet_hash = compute_file_sha256(parquet_path)
        file_size_bytes = parquet_path.stat().st_size

        sql_hash = compute_file_sha256(sql_path) if sql_path and sql_path.exists() else None
        spec_path = domain_spec_path or (PROJECT_ROOT / "configs" / "domain_spec.yaml")
        spec_hash = compute_file_sha256(spec_path) if spec_path.exists() else None

        git_meta = get_git_metadata()

        try:
            rel_path = str(parquet_path.relative_to(PROJECT_ROOT))
        except ValueError:
            rel_path = str(parquet_path)

        entry: dict[str, Any] = {
            "artifact_name": artifact_name,
            "relative_path": rel_path,
            "sha256": parquet_hash,
            "size_bytes": file_size_bytes,
            "num_rows": df.height if df is not None else None,
            "num_columns": df.width if df is not None else None,
            "columns": df.columns if df is not None else None,
            "sql_file": str(sql_path.name) if sql_path else None,
            "sql_sha256": sql_hash,
            "domain_spec_sha256": spec_hash,
            "parameters": parameters or {},
            "git_commit": git_meta["commit"],
            "git_branch": git_meta["branch"],
            "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        }

        manifest = self.load_manifest()
        manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
        if "artifacts" not in manifest or not isinstance(manifest["artifacts"], dict):
            manifest["artifacts"] = {}
        manifest["artifacts"][artifact_name] = entry

        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.manifest_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        temp_path.replace(self.manifest_path)

        logger.info(
            f"Linhagem registrada com sucesso: '{artifact_name}' [{parquet_hash[:12]}...] "
            f"em {self.manifest_path.name}"
        )
        return entry
