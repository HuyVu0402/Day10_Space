from __future__ import annotations

from typing import Any

from core.utils import write_text


def generate_phase1_report(
    report_path,
    source_summary: dict[str, Any],
    metrics: dict[str, Any],
    quality: dict[str, Any],
    freshness: dict[str, Any],
) -> None:
    """Write the baseline phase Markdown report.

    Pseudo-code:
    1. Gom source summary.
    2. In metrics retrieval/evaluation.
    3. In data quality va freshness.
    4. Ghi markdown vao report_path.
    """
    lines = [
        "# Phase 1 Baseline Report",
        "",
        "## Source Summary",
        "",
        _markdown_table(source_summary),
        "",
        "## Evaluation Metrics",
        "",
        _markdown_table(metrics),
        "",
        "## Data Quality",
        "",
        f"Overall status: {'PASS' if quality.get('passed') else 'FAIL'}",
        "",
        _checks_table(quality.get("checks", [])),
        "",
        "## Freshness",
        "",
        _markdown_table(freshness),
        "",
    ]
    write_text(report_path, "\n".join(lines))


def generate_corruption_report(
    report_path,
    baseline_metrics: dict[str, Any],
    corrupted_metrics: dict[str, Any],
    repaired_metrics: dict[str, Any],
    corrupted_quality: dict[str, Any],
    repaired_quality: dict[str, Any],
    corrupted_freshness: dict[str, Any],
    repaired_freshness: dict[str, Any],
) -> None:
    """Write the baseline/corrupted/repaired comparison report."""
    comparison_rows = []
    metric_names = [
        "retrieval_hit_rate",
        "mean_token_f1",
        "judge_accuracy",
        "mean_judge_score",
    ]
    for metric in metric_names:
        comparison_rows.append(
            {
                "metric": metric,
                "baseline": baseline_metrics.get(metric),
                "corrupted": corrupted_metrics.get(metric),
                "repaired": repaired_metrics.get(metric),
            }
        )

    lines = [
        "# Corruption and Repair Comparison Report",
        "",
        "## Metrics Comparison",
        "",
        _rows_table(comparison_rows, ["metric", "baseline", "corrupted", "repaired"]),
        "",
        "## Corrupted Quality",
        "",
        f"Overall status: {'PASS' if corrupted_quality.get('passed') else 'FAIL'}",
        "",
        _checks_table(corrupted_quality.get("checks", [])),
        "",
        "## Repaired Quality",
        "",
        f"Overall status: {'PASS' if repaired_quality.get('passed') else 'FAIL'}",
        "",
        _checks_table(repaired_quality.get("checks", [])),
        "",
        "## Corrupted Freshness",
        "",
        _markdown_table(corrupted_freshness),
        "",
        "## Repaired Freshness",
        "",
        _markdown_table(repaired_freshness),
        "",
    ]
    write_text(report_path, "\n".join(lines))


def _markdown_table(payload: dict[str, Any]) -> str:
    if not payload:
        return "_No data._"
    rows = [{"field": key, "value": _format_value(value)} for key, value in payload.items()]
    return _rows_table(rows, ["field", "value"])


def _checks_table(checks: list[dict[str, Any]]) -> str:
    if not checks:
        return "_No checks available._"
    return _rows_table(checks, ["name", "dimension", "passed", "value", "expected"])


def _rows_table(rows: list[dict[str, Any]], columns: list[str]) -> str:
    if not rows:
        return "_No rows._"
    header = "| " + " | ".join(columns) + " |"
    separator = "| " + " | ".join("---" for _ in columns) + " |"
    body = [
        "| " + " | ".join(_format_value(row.get(column, "")) for column in columns) + " |"
        for row in rows
    ]
    return "\n".join([header, separator, *body])


def _format_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.4f}"
    if isinstance(value, (dict, list)):
        return str(value).replace("|", "\\|")
    return str(value).replace("|", "\\|")
