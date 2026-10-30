# tests/test_lineage.py
from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest

from src.core.lineage import LineageTracker, compute_file_sha256


@pytest.mark.unit
def test_compute_file_sha256(tmp_path: Path):
    sample_file = tmp_path / "sample.txt"
    sample_file.write_text("onco-causal-deterministic-hash", encoding="utf-8")
    h1 = compute_file_sha256(sample_file)
    assert len(h1) == 64
    assert h1 == compute_file_sha256(sample_file)


@pytest.mark.unit
def test_lineage_tracker_record(tmp_path: Path):
    manifest_p = tmp_path / "manifest.json"
    tracker = LineageTracker(manifest_path=manifest_p)

    parquet_p = tmp_path / "test.parquet"
    df = pl.DataFrame({"id": ["1", "2"], "val": [10, 20]})
    df.write_parquet(parquet_p)

    sql_p = tmp_path / "test.sql"
    sql_p.write_text("SELECT 1", encoding="utf-8")

    entry = tracker.record_artifact(
        artifact_name="test_dataset",
        parquet_path=parquet_p,
        df=df,
        sql_path=sql_p,
        parameters={"param1": 100},
    )

    assert entry["artifact_name"] == "test_dataset"
    assert entry["num_rows"] == 2
    assert entry["num_columns"] == 2
    assert entry["sha256"] == compute_file_sha256(parquet_p)
    assert entry["sql_sha256"] == compute_file_sha256(sql_p)

    assert manifest_p.exists()
    with open(manifest_p, "r", encoding="utf-8") as f:
        data = json.load(f)
    assert "test_dataset" in data["artifacts"]
    assert data["artifacts"]["test_dataset"]["sha256"] == entry["sha256"]
