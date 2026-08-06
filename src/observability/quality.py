from __future__ import annotations

from typing import Any

import pandas as pd

from core.config import Settings
from core.utils import write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run data quality checks and persist the quality report.

    Pseudo-code:
    1. Check row count.
    2. Check `paper_id` not null va unique.
    3. Check `title` not null.
    4. Check do dai `summary`.
    5. Check freshness bang `age_days`.
    6. Ghi ket qua vao `data/quality/`.
    """
    required_columns = [
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
    ]
    checks: list[dict[str, Any]] = []

    def add_check(name: str, passed: bool, value: Any, expected: str, dimension: str) -> None:
        checks.append(
            {
                "name": name,
                "dimension": dimension,
                "passed": bool(passed),
                "value": value,
                "expected": expected,
            }
        )

    missing_columns = [column for column in required_columns if column not in df.columns]
    add_check("required_columns_present", not missing_columns, missing_columns, "no missing required columns", "schema")

    row_count = len(df)
    add_check("row_count_positive", row_count > 0, row_count, "> 0", "completeness")

    if "paper_id" in df.columns:
        null_ids = int(df["paper_id"].isna().sum() + (df["paper_id"].fillna("").astype(str).str.strip() == "").sum())
        duplicate_ids = int(df["paper_id"].duplicated().sum())
        add_check("paper_id_non_null", null_ids == 0, null_ids, "0 null or empty paper_id", "completeness")
        add_check("paper_id_unique", duplicate_ids == 0, duplicate_ids, "0 duplicate paper_id", "uniqueness")

    for column in ["title", "summary", "published", "text_for_embedding", "abs_url"]:
        if column in df.columns:
            empty_count = int(df[column].isna().sum() + (df[column].fillna("").astype(str).str.strip() == "").sum())
            add_check(f"{column}_non_empty", empty_count == 0, empty_count, f"0 empty {column}", "completeness")

    if "summary" in df.columns:
        short_summaries = int((df["summary"].fillna("").astype(str).str.len() < 100).sum())
        add_check("summary_min_length", short_summaries == 0, short_summaries, "0 summaries shorter than 100 chars", "validity")

    if "published" in df.columns:
        valid_dates = df["published"].fillna("").astype(str).str.match(r"^\d{4}-\d{2}-\d{2}$")
        invalid_dates = int((~valid_dates).sum())
        add_check("published_iso_date", invalid_dates == 0, invalid_dates, "0 invalid YYYY-MM-DD dates", "validity")

    if "age_days" in df.columns:
        stale_rows = int((pd.to_numeric(df["age_days"], errors="coerce") > settings.freshness_threshold_days).sum())
        add_check(
            "freshness_threshold",
            stale_rows == 0,
            stale_rows,
            f"0 rows older than {settings.freshness_threshold_days} days",
            "freshness",
        )

    report = {
        "report_name": report_name,
        "total_rows": row_count,
        "passed": all(check["passed"] for check in checks),
        "checks": checks,
    }
    write_json(settings.paths.quality_dir / f"{report_name}.json", report)
    return report


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path) -> dict[str, Any]:
    """Build and persist a freshness report for a cleaned dataset.

    Pseudo-code:
    1. Tim latest va oldest published date.
    2. Dem so dong stale.
    3. Tao payload:
       - latest_published
       - oldest_published
       - stale_rows
       - total_rows
       - is_fresh
    4. Ghi JSON report.
    """
    published = pd.to_datetime(df.get("published", pd.Series(dtype=str)), errors="coerce")
    age_days = pd.to_numeric(df.get("age_days", pd.Series(dtype=int)), errors="coerce")
    stale_rows = int((age_days > settings.freshness_threshold_days).sum()) if not age_days.empty else 0
    valid_published = published.dropna()

    report = {
        "latest_published": valid_published.max().date().isoformat() if not valid_published.empty else None,
        "oldest_published": valid_published.min().date().isoformat() if not valid_published.empty else None,
        "stale_rows": stale_rows,
        "total_rows": int(len(df)),
        "freshness_threshold_days": settings.freshness_threshold_days,
        "is_fresh": stale_rows == 0 and len(df) > 0,
    }
    write_json(report_path, report)
    return report
