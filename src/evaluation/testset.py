from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path) -> list[dict[str, Any]]:
    """Build or load the frozen evaluation set from the cleaned dataframe.

    Pseudo-code:
    1. Kiem tra so luong document toi thieu.
    2. Chon mot so paper dai dien.
    3. Tao nhieu loai cau hoi:
       - summary
       - authors
       - date
       - categories
    4. Moi row can co:
       - id
       - question_type
       - question
       - ground_truth
       - ground_truth_doc_ids
    5. Ghi file JSON vao output_path.
    """
    path = Path(output_path)
    if path.exists():
        import json

        return json.loads(path.read_text(encoding="utf-8"))

    required = {"paper_id", "title", "summary", "published", "authors_joined", "categories_joined"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Clean dataframe is missing required columns for test set: {sorted(missing)}")
    if len(df) < 5:
        raise ValueError("Need at least 5 clean documents to build a frozen evaluation set.")

    candidates = df.copy()
    candidates = candidates[
        candidates["paper_id"].notna()
        & candidates["title"].notna()
        & candidates["summary"].notna()
        & (candidates["summary"].astype(str).str.len() >= 100)
    ].head(10)
    if len(candidates) < 5:
        raise ValueError("Need at least 5 valid clean documents with non-empty title and summary.")

    samples: list[dict[str, Any]] = []
    for idx, row in enumerate(candidates.itertuples(index=False), start=1):
        paper_id = str(row.paper_id)
        title = str(row.title)
        summary = str(row.summary)
        authors = str(row.authors_joined)
        published = str(row.published)
        categories = str(row.categories_joined)

        if idx % 3 == 1:
            question_type = "factual_summary"
            question = f"What is the main idea of the paper '{title}'?"
            ground_truth = first_sentence(summary)
        elif idx % 3 == 2:
            question_type = "factual_authors"
            question = f"Who authored the paper '{title}'?"
            ground_truth = authors
        else:
            question_type = "factual_date"
            question = f"When was the paper '{title}' published?"
            ground_truth = published

        if not ground_truth.strip() and categories.strip():
            question_type = "factual_categories"
            question = f"What categories are associated with the paper '{title}'?"
            ground_truth = categories

        samples.append(
            {
                "id": f"q{idx:02d}",
                "question_type": question_type,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [paper_id],
            }
        )

    write_json(path, samples)
    return samples
