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

## Repaired Quality

Overall status: PASS

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
