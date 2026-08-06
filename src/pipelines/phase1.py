"""Baseline pipeline orchestration.

This module intentionally owns orchestration only.  Domain logic remains in
the ingestion, retrieval, evaluation and observability modules.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.config import Settings, load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex


REQUIRED_CLEAN_COLUMNS = {
    "paper_id", "title", "summary", "published", "authors_joined",
    "categories_joined", "age_days", "text_for_embedding", "abs_url", "pdf_url",
}


def _validate_clean_dataframe(df: pd.DataFrame, *, label: str) -> None:
    missing = sorted(REQUIRED_CLEAN_COLUMNS - set(df.columns))
    if missing:
        raise ValueError(f"{label} is missing required clean-data columns: {missing}")
    if df.empty:
        raise ValueError(f"{label} is empty; cannot build an index or evaluate it.")
    ids = df["paper_id"].fillna("").astype(str).str.strip()
    if not ids.ne("").all():
        raise ValueError(f"{label} contains empty paper_id values.")
    if ids.duplicated().any():
        raise ValueError(f"{label} contains duplicate paper_id values.")


def _validate_frozen_test_set(test_set_path: Path, df: pd.DataFrame) -> list[dict[str, Any]]:
    if not test_set_path.exists():
        raise FileNotFoundError(f"Frozen evaluation set was not created: {test_set_path}")
    test_set = read_json(test_set_path)
    if not isinstance(test_set, list) or not test_set:
        raise ValueError(f"Frozen evaluation set is empty or invalid: {test_set_path}")

    required = {"id", "question_type", "question", "ground_truth", "ground_truth_doc_ids"}
    available_ids = set(df["paper_id"].astype(str))
    for position, item in enumerate(test_set, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"Evaluation sample #{position} is not a JSON object.")
        missing = sorted(required - set(item))
        if missing:
            raise ValueError(f"Evaluation sample #{position} is missing fields: {missing}")
        doc_ids = item["ground_truth_doc_ids"]
        if not isinstance(doc_ids, list) or not doc_ids:
            raise ValueError(f"Evaluation sample #{position} has no ground_truth_doc_ids.")
        unknown = set(map(str, doc_ids)) - available_ids
        if unknown:
            raise ValueError(
                f"Evaluation sample #{position} references document IDs absent from clean data: {sorted(unknown)}"
            )
    return test_set


def _source_summary(settings: Settings, record_count: int, clean_count: int) -> dict[str, Any]:
    return {
        "source": settings.source_api,
        "query": settings.source_query,
        "filter": settings.source_filter,
        "raw_record_count": record_count,
        "clean_record_count": clean_count,
        "embedding_model": settings.embedding_model,
        "top_k": settings.top_k,
    }


def main() -> None:
    """Run the clean baseline from source snapshot through evidence artifacts."""
    settings = load_settings()

    # A saved raw snapshot makes ordinary reruns deterministic and auditable.
    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        records = fetch_source_records(settings)
    else:
        records = load_raw_records(settings.paths.raw_records_json)
    if not records:
        raise ValueError("No raw records are available; fetch Crossref data before running the baseline.")

    clean_df = build_clean_dataframe(records, run_date=now_utc())
    _validate_clean_dataframe(clean_df, label="Baseline clean dataset")
    write_csv(clean_df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, clean_df.to_dict(orient="records"))

    # build_test_set loads an existing file.  Do not overwrite a frozen set.
    build_test_set(clean_df, settings.paths.eval_testset)
    _validate_frozen_test_set(settings.paths.eval_testset, clean_df)

    index = LocalEmbeddingIndex.build(clean_df, settings, settings.paths.embeddings_json)
    bundle = evaluate_pipeline(
        settings, index, settings.paths.eval_testset,
        settings.paths.baseline_metrics, settings.paths.baseline_answers,
    )
    metrics = {
        **bundle.summary,
        "dataset_state": "baseline",
        "question_count": bundle.summary.get("samples", 0),
    }
    write_json(settings.paths.baseline_metrics, metrics)

    quality = run_data_quality_checks(clean_df, settings, "baseline_quality")
    freshness = build_freshness_report(clean_df, settings, settings.paths.freshness_report)
    generate_phase1_report(
        settings.paths.baseline_report,
        _source_summary(settings, len(records), len(clean_df)),
        metrics,
        quality,
        freshness,
    )
    print(f"Baseline pipeline complete. Metrics: {settings.paths.baseline_metrics}")
    print(f"Baseline report: {settings.paths.baseline_report}")
