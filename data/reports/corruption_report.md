# Corruption and Repair Comparison Report

## Metrics Comparison

| metric | baseline | corrupted | repaired |
| --- | --- | --- | --- |
| retrieval_hit_rate | 1.0000 | 1.0000 | 1.0000 |
| mean_token_f1 | 1.0000 | 0.7000 | 1.0000 |
| judge_accuracy | 1.0000 | 0.7000 | 1.0000 |
| mean_judge_score | 5 | 3.8000 | 5 |

## Corrupted Quality

Overall status: FAIL

| name | dimension | passed | value | expected |
| --- | --- | --- | --- | --- |
| required_columns_present | schema | True | [] | no missing required columns |
| row_count_positive | completeness | True | 26 | > 0 |
| paper_id_non_null | completeness | True | 0 | 0 null or empty paper_id |
| paper_id_unique | uniqueness | False | 2 | 0 duplicate paper_id |
| title_non_empty | completeness | True | 0 | 0 empty title |
| summary_non_empty | completeness | False | 3 | 0 empty summary |
| published_non_empty | completeness | True | 0 | 0 empty published |
| text_for_embedding_non_empty | completeness | True | 0 | 0 empty text_for_embedding |
| abs_url_non_empty | completeness | True | 0 | 0 empty abs_url |
| summary_min_length | validity | False | 3 | 0 summaries shorter than 100 chars |
| published_iso_date | validity | True | 0 | 0 invalid YYYY-MM-DD dates |
| freshness_threshold | freshness | False | 4 | 0 rows older than 180 days |

## Repaired Quality

Overall status: FAIL

| name | dimension | passed | value | expected |
| --- | --- | --- | --- | --- |
| required_columns_present | schema | True | [] | no missing required columns |
| row_count_positive | completeness | True | 24 | > 0 |
| paper_id_non_null | completeness | True | 0 | 0 null or empty paper_id |
| paper_id_unique | uniqueness | True | 0 | 0 duplicate paper_id |
| title_non_empty | completeness | True | 0 | 0 empty title |
| summary_non_empty | completeness | True | 0 | 0 empty summary |
| published_non_empty | completeness | True | 0 | 0 empty published |
| text_for_embedding_non_empty | completeness | True | 0 | 0 empty text_for_embedding |
| abs_url_non_empty | completeness | True | 0 | 0 empty abs_url |
| summary_min_length | validity | True | 0 | 0 summaries shorter than 100 chars |
| published_iso_date | validity | True | 0 | 0 invalid YYYY-MM-DD dates |
| freshness_threshold | freshness | False | 2 | 0 rows older than 180 days |

## Corrupted Freshness

| field | value |
| --- | --- |
| latest_published | 2026-08-01 |
| oldest_published | 1970-01-01 |
| stale_rows | 4 |
| total_rows | 26 |
| freshness_threshold_days | 180 |
| is_fresh | False |

## Repaired Freshness

| field | value |
| --- | --- |
| latest_published | 2026-08-01 |
| oldest_published | 2026-01-01 |
| stale_rows | 2 |
| total_rows | 24 |
| freshness_threshold_days | 180 |
| is_fresh | False |

## Interpretation

The comparison uses the same frozen 10-question evaluation set, document-level
chunking, `sentence-transformers/all-MiniLM-L6-v2`, and `top_k=4` for all three
states. Therefore the changes below are attributable to the dataset state rather
than a changed evaluation setup.

- **Corruption impact:** retrieval hit rate stayed at 1.00 because the affected
  papers remained indexed, but answer quality fell: Token F1 and judge accuracy
  both dropped from 1.00 to 0.70, while mean judge score dropped from 5.0 to 3.8.
- **Quality signals:** the corrupted dataset contains 26 rows, including 2
  duplicate `paper_id` values, 3 blank/short summaries, and 4 stale rows.
- **Repair result:** rebuilding the clean dataset from the raw snapshot restored
  row count to 24, removed duplicate IDs and blank/short summaries, and restored
  all answer metrics to baseline.
- **Remaining limitation:** baseline already contains 2 records older than the
  180-day freshness threshold. Repair correctly restores that baseline state, so
  repaired freshness remains FAIL; it is not a failure introduced by corruption.

## Evidence and reproducibility

- Metrics: `data/results/baseline_metrics.json`,
  `data/results/corrupted_metrics.json`, and `data/results/repaired_metrics.json`.
- Answer-level evidence: corresponding `*_answers.json` files in `data/results/`.
- Corruption audit trail: `data/results/corruption_log.json`; it affects 5 frozen
  ground-truth documents.

```powershell
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```
