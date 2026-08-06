from __future__ import annotations

import json
from pathlib import Path
import random

import numpy as np
import pandas as pd


def corrupt_clean_dataframe(
    df: pd.DataFrame,
    output_log_path: str | Path,
    seed: int = 42
) -> pd.DataFrame:
    """Simulate data corruption across multiple scenarios and output a detailed audit log.

    Scenarios:
    1. Blank Summary & Text Embedding: Erase summary and ruin text_for_embedding.
    2. Title Truncation & Noise Injection: Truncate title and inject garbage tokens.
    3. Stale/Corrupted Date: Alter published date to ancient timestamp and distort age_days.
    4. Duplicate Row Injection: Duplicate existing rows without deduplication.

    All corruption events are tracked and saved to `output_log_path`.
    """
    if df.empty:
        log_path = Path(output_log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "w", encoding="utf-8") as f:
            json.dump([], f, indent=2)
        return df.copy()

    random.seed(seed)
    np.random.seed(seed)

    df_corrupted = df.copy()
    logs: list[dict] = []
    n_rows = len(df_corrupted)

    # 1. Scenario 1: Blank Summary for ~15% of records
    scenario1_count = max(1, int(n_rows * 0.15))
    indices_s1 = random.sample(range(n_rows), min(scenario1_count, n_rows))
    for idx in indices_s1:
        paper_id = df_corrupted.at[idx, "paper_id"]
        orig_summary = df_corrupted.at[idx, "summary"]
        orig_text_emb = df_corrupted.at[idx, "text_for_embedding"]

        corrupted_summary = ""
        title = df_corrupted.at[idx, "title"]
        authors = df_corrupted.at[idx, "authors_joined"]
        corrupted_text_emb = f"Title: {title} | Authors: {authors} | Summary: "

        df_corrupted.at[idx, "summary"] = corrupted_summary
        df_corrupted.at[idx, "text_for_embedding"] = corrupted_text_emb

        logs.append({
            "paper_id": paper_id,
            "scenario": "Scenario 1: Blank Summary",
            "field": "summary",
            "original_value": orig_summary,
            "corrupted_value": corrupted_summary,
        })
        logs.append({
            "paper_id": paper_id,
            "scenario": "Scenario 1: Blank Summary",
            "field": "text_for_embedding",
            "original_value": orig_text_emb,
            "corrupted_value": corrupted_text_emb,
        })

    # 2. Scenario 2: Title Truncation & Noise Injection for ~15% of records (distinct from S1 if possible)
    remaining_indices = [i for i in range(n_rows) if i not in indices_s1]
    scenario2_count = max(1, int(n_rows * 0.15))
    sample_pool = remaining_indices if len(remaining_indices) >= scenario2_count else list(range(n_rows))
    indices_s2 = random.sample(sample_pool, min(scenario2_count, len(sample_pool)))

    for idx in indices_s2:
        paper_id = df_corrupted.at[idx, "paper_id"]
        orig_title = df_corrupted.at[idx, "title"]
        orig_text_emb = df_corrupted.at[idx, "text_for_embedding"]

        noise = f" [CORRUPTED_NOISE_{random.randint(1000, 9999)}]"
        corrupted_title = (orig_title[:10] + noise) if len(orig_title) > 10 else (orig_title + noise)
        authors = df_corrupted.at[idx, "authors_joined"]
        summary = df_corrupted.at[idx, "summary"]
        corrupted_text_emb = f"Title: {corrupted_title} | Authors: {authors} | Summary: {summary}"

        df_corrupted.at[idx, "title"] = corrupted_title
        df_corrupted.at[idx, "text_for_embedding"] = corrupted_text_emb

        logs.append({
            "paper_id": paper_id,
            "scenario": "Scenario 2: Title Truncation & Noise Injection",
            "field": "title",
            "original_value": orig_title,
            "corrupted_value": corrupted_title,
        })
        logs.append({
            "paper_id": paper_id,
            "scenario": "Scenario 2: Title Truncation & Noise Injection",
            "field": "text_for_embedding",
            "original_value": orig_text_emb,
            "corrupted_value": corrupted_text_emb,
        })

    # 3. Scenario 3: Stale/Corrupted Date for ~10% of records
    scenario3_count = max(1, int(n_rows * 0.10))
    indices_s3 = random.sample(range(n_rows), min(scenario3_count, n_rows))
    for idx in indices_s3:
        paper_id = df_corrupted.at[idx, "paper_id"]
        orig_published = df_corrupted.at[idx, "published"]
        orig_age = df_corrupted.at[idx, "age_days"]

        corrupted_published = "1970-01-01"
        corrupted_age = 99999

        df_corrupted.at[idx, "published"] = corrupted_published
        df_corrupted.at[idx, "age_days"] = corrupted_age

        logs.append({
            "paper_id": paper_id,
            "scenario": "Scenario 3: Stale/Corrupted Date",
            "field": "published",
            "original_value": str(orig_published),
            "corrupted_value": corrupted_published,
        })
        logs.append({
            "paper_id": paper_id,
            "scenario": "Scenario 3: Stale/Corrupted Date",
            "field": "age_days",
            "original_value": int(orig_age),
            "corrupted_value": corrupted_age,
        })

    # 4. Scenario 4: Duplicate Row Injection (select 2 rows and append them)
    if n_rows >= 2:
        dup_indices = random.sample(range(n_rows), 2)
        dup_rows = df_corrupted.iloc[dup_indices].copy()
        df_corrupted = pd.concat([df_corrupted, dup_rows], ignore_index=True)
        for idx in dup_indices:
            paper_id = df.at[idx, "paper_id"]
            logs.append({
                "paper_id": paper_id,
                "scenario": "Scenario 4: Duplicate Row Injection",
                "field": "dataframe_row_count",
                "original_value": "single_row",
                "corrupted_value": "duplicated_row",
            })

    # Save corruption logs to output_log_path
    log_path = Path(output_log_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(logs, f, indent=2, ensure_ascii=False)

    return df_corrupted

