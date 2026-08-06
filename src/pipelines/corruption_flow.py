"""Corruption, repair and fair three-state comparison orchestration."""

from __future__ import annotations

import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from pipelines.phase1 import _validate_clean_dataframe, _validate_frozen_test_set
from retrieval.index import LocalEmbeddingIndex


def _read_clean_dataset(path, *, label: str) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{label} is missing: {path}. Run the baseline pipeline first.")
    df = pd.read_csv(path)
    _validate_clean_dataframe(df, label=label)
    return df


def _evaluate_state(settings, df: pd.DataFrame, *, state: str, embeddings_path, metrics_path, answers_path):
    index = LocalEmbeddingIndex.build(df, settings, embeddings_path)
    bundle = evaluate_pipeline(settings, index, settings.paths.eval_testset, metrics_path, answers_path)
    metrics = {
        **bundle.summary,
        "dataset_state": state,
        "question_count": bundle.summary.get("samples", 0),
    }
    write_json(metrics_path, metrics)
    return metrics


def main() -> None:
    """Evaluate corrupted and repaired datasets against the frozen baseline set."""
    settings = load_settings()
    baseline_df = _read_clean_dataset(settings.paths.clean_csv, label="Baseline clean dataset")
    _validate_frozen_test_set(settings.paths.eval_testset, baseline_df)

    if not settings.paths.baseline_metrics.exists():
        raise FileNotFoundError(
            f"Baseline metrics are missing: {settings.paths.baseline_metrics}. Run run_phase1.py first."
        )
    baseline_metrics = read_json(settings.paths.baseline_metrics)

    corrupted_df = corrupt_clean_dataframe(baseline_df, settings.paths.corruption_log)
    if corrupted_df.empty:
        raise ValueError("Corruption produced an empty dataset; cannot evaluate it.")
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))
    corrupted_metrics = _evaluate_state(
        settings, corrupted_df, state="corrupted",
        embeddings_path=settings.paths.corrupted_embeddings_json,
        metrics_path=settings.paths.corrupted_metrics,
        answers_path=settings.paths.corrupted_answers,
    )
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted_quality")
    corrupted_freshness = build_freshness_report(
        corrupted_df, settings, settings.paths.quality_dir / "corrupted_freshness_report.json"
    )

    # Repair is deliberately offline: reconstruct clean data only from the raw snapshot.
    raw_records = load_raw_records(settings.paths.raw_records_json)
    if not raw_records:
        raise ValueError("Raw snapshot is empty; repair must not refetch Crossref data.")
    repaired_df = build_clean_dataframe(raw_records, run_date=now_utc())
    _validate_clean_dataframe(repaired_df, label="Repaired clean dataset")
    _validate_frozen_test_set(settings.paths.eval_testset, repaired_df)
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))
    repaired_metrics = _evaluate_state(
        settings, repaired_df, state="repaired",
        embeddings_path=settings.paths.repaired_embeddings_json,
        metrics_path=settings.paths.repaired_metrics,
        answers_path=settings.paths.repaired_answers,
    )
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired_quality")
    repaired_freshness = build_freshness_report(
        repaired_df, settings, settings.paths.quality_dir / "repaired_freshness_report.json"
    )

    generate_corruption_report(
        settings.paths.comparison_report,
        baseline_metrics,
        corrupted_metrics,
        repaired_metrics,
        corrupted_quality,
        repaired_quality,
        corrupted_freshness,
        repaired_freshness,
    )
    print(f"Corruption/repair comparison complete. Report: {settings.paths.comparison_report}")
