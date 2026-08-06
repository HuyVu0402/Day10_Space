from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime

import pandas as pd

from core.config import load_settings
from core.utils import read_json, write_csv, write_json
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records, load_raw_records


def main() -> None:
    """Run the C2 integration flow: raw -> clean -> frozen evaluation set.

    Pseudo-code:
    1. Load settings.
    2. Load hoac fetch raw records.
    3. Clean data.
    4. Save clean CSV/JSON.
    5. Build Chroma index.
    6. Tao hoac load evaluation set.
    7. Evaluate.
    8. Run quality checks va freshness report.
    9. Tao markdown report.
    10. Co the demo agent tren vai sample question.
    """
    settings = load_settings()

    if settings.refresh_source or not settings.paths.raw_records_json.exists():
        records = fetch_source_records(settings)
    else:
        records = load_raw_records(settings.paths.raw_records_json)

    if not records:
        raise RuntimeError("No raw records available. R2 must provide data/raw/crossref_records.json.")

    run_date = datetime.now(UTC)
    clean_df = build_clean_dataframe(records, run_date=run_date)
    _validate_clean_dataframe(clean_df)
    write_csv(clean_df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, clean_df.to_dict(orient="records"))

    test_set_existed = settings.paths.eval_testset.exists()
    test_set = build_test_set(clean_df, settings.paths.eval_testset)
    _validate_test_set(test_set, clean_df)

    source_summary = {
        "raw_records": len(records),
        "clean_records": len(clean_df),
        "test_set_samples": len(test_set),
        "test_set_path": str(settings.paths.eval_testset),
        "test_set_reused": test_set_existed,
        "clean_csv": str(settings.paths.clean_csv),
        "clean_json": str(settings.paths.clean_json),
    }
    write_json(settings.paths.baseline_report.parent / "c2_integration_summary.json", source_summary)

    print("C2 integration check passed.")
    print(f"raw_records={len(records)}")
    print(f"clean_records={len(clean_df)}")
    print(f"test_set_samples={len(test_set)}")
    print(f"test_set_reused={test_set_existed}")


def _validate_clean_dataframe(df: pd.DataFrame) -> None:
    required_columns = {
        "paper_id",
        "title",
        "summary",
        "published",
        "authors_joined",
        "categories_joined",
        "age_days",
        "text_for_embedding",
        "abs_url",
        "pdf_url",
    }
    missing_columns = required_columns - set(df.columns)
    if missing_columns:
        raise RuntimeError(f"Clean dataframe missing required columns: {sorted(missing_columns)}")
    if df.empty:
        raise RuntimeError("Clean dataframe is empty.")
    if df["paper_id"].isna().any() or (df["paper_id"].astype(str).str.strip() == "").any():
        raise RuntimeError("Clean dataframe contains null or empty paper_id.")
    duplicate_count = int(df["paper_id"].duplicated().sum())
    if duplicate_count:
        raise RuntimeError(f"Clean dataframe contains duplicate paper_id values: {duplicate_count}")
    if df["text_for_embedding"].isna().any() or (df["text_for_embedding"].astype(str).str.strip() == "").any():
        raise RuntimeError("Clean dataframe contains empty text_for_embedding.")


def _validate_test_set(test_set: list[dict], clean_df: pd.DataFrame) -> None:
    required_keys = {"id", "question_type", "question", "ground_truth", "ground_truth_doc_ids"}
    if not test_set:
        raise RuntimeError("Evaluation test set is empty.")

    clean_ids = set(clean_df["paper_id"].astype(str))
    bad_samples: list[str] = []
    for sample in test_set:
        missing = required_keys - set(sample)
        if missing:
            bad_samples.append(f"{sample.get('id', '<missing-id>')}: missing keys {sorted(missing)}")
            continue
        doc_ids = [str(doc_id) for doc_id in sample.get("ground_truth_doc_ids", [])]
        if not doc_ids:
            bad_samples.append(f"{sample['id']}: empty ground_truth_doc_ids")
            continue
        missing_doc_ids = [doc_id for doc_id in doc_ids if doc_id not in clean_ids]
        if missing_doc_ids:
            bad_samples.append(f"{sample['id']}: missing clean docs {missing_doc_ids}")
        if not str(sample.get("ground_truth", "")).strip():
            bad_samples.append(f"{sample['id']}: empty ground_truth")

    if bad_samples:
        raise RuntimeError("Invalid evaluation test set:\n" + "\n".join(bad_samples))
