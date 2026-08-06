# Phase 1 Baseline Report

## Source Summary

| field | value |
| --- | --- |
| source | Crossref REST API |
| query | agentic retrieval augmented generation large language model |
| filter | from-pub-date:2026-02-07,has-abstract:true |
| raw_record_count | 24 |
| clean_record_count | 24 |
| embedding_model | sentence-transformers/all-MiniLM-L6-v2 |
| top_k | 4 |

## Evaluation Metrics

| field | value |
| --- | --- |
| samples | 10 |
| retrieval_hit_rate | 1.0000 |
| mean_token_f1 | 1.0000 |
| judge_accuracy | 1.0000 |
| mean_judge_score | 5 |
| ragas | {'skipped': 'Set RUN_RAGAS=1 to enable the slower Ragas pass.'} |
| dataset_state | baseline |
| question_count | 10 |

## Data Quality

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

## Freshness

| field | value |
| --- | --- |
| latest_published | 2026-08-01 |
| oldest_published | 2026-01-01 |
| stale_rows | 2 |
| total_rows | 24 |
| freshness_threshold_days | 180 |
| is_fresh | False |
