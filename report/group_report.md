# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4 |
| Tên nhóm | Space |
| Repository | `https://github.com/HuyVu0402/Day10_Space` |
| Ngày chạy artifact gần nhất | 2026-08-06 |

### Thành viên và phân công

| Thành viên | Vai trò | Module/deliverable sở hữu |
| --- | --- | --- |
| Vũ Quang Huy | R1 — Integration & Release Owner | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, scripts, tích hợp/release |
| Mạnh | R2 — Source Ingestion Owner | `src/ingestion/crossref.py`, raw response/records |
| Ánh | R3 — Cleaning, Corruption & Repair Owner | `src/ingestion/cleaning.py`, `src/ingestion/corruption.py` |
| Sơn | R4 — Retrieval & RAG Owner | `src/retrieval/`, ChromaDB và answer-level artifacts |
| Phương | R5 — Evaluation, Observability & Reporting Owner | `src/evaluation/`, `src/observability/`, test set/metrics/reports |

## 2. Tóm tắt kết quả

Nhóm đã chạy thành công baseline và corruption/repair flow trên 24 paper records
từ Crossref. Baseline tạo raw/clean data, embedding manifest, frozen test set 10
câu, answer-level artifacts, metrics, quality/freshness report và Markdown report.
Kịch bản corruption tạo summary rỗng, title bị cắt/nhiễu, ngày stale và duplicate
rows. Nó làm Token F1 và judge accuracy giảm từ 1.00 xuống 0.70, mean judge score
giảm từ 5.0 xuống 3.8; retrieval hit rate vẫn 1.00 vì tài liệu bị ảnh hưởng vẫn
còn trong index. Repair chạy lại cleaning từ raw snapshot, không gọi lại API, và
phục hồi các metric trả lời về baseline. Hạn chế còn lại là 2/24 baseline records
đã vượt ngưỡng freshness 180 ngày; do đó quality baseline/repaired chưa PASS toàn
bộ. Không coi đây là kết quả giả hay đã được xử lý xong.

## 3. Kiến trúc và data contract

```text
Crossref API → raw response/records → clean dataset → MiniLM + ChromaDB
→ frozen evaluation set → baseline evaluation/quality report
→ corruption → re-index/evaluate → repair from raw snapshot → comparison report
```

| Artifact | Contract chính | Owner → người nhận |
| --- | --- | --- |
| Raw record | `paper_id` ổn định, title, summary, authors, published, URLs | R2 → R3/R1 |
| Clean record | `paper_id`, title, summary, published, authors/categories, `age_days`, `text_for_embedding`, URLs | R3 → R4/R5/R1 |
| Evaluation sample | `id`, `question_type`, question, ground truth, `ground_truth_doc_ids` | R5 → R1/R4 |
| Agent result | answer, retrieved document IDs, contexts | R4 → R5/R1 |
| Aggregate metrics | state, question count, hit rate, Token F1, judge metrics | R5 → R1 |

Các trạng thái dùng cùng frozen test set, document-level chunking,
`sentence-transformers/all-MiniLM-L6-v2`, `top_k=4` và evaluator. `paper_id`
được giữ xuyên raw → clean → index → test set → answers. Repair chỉ đọc
`data/raw/crossref_records.json`.

## 4. Cách tái hiện

```powershell
uv sync
Copy-Item .env.example .env
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```

Cấu hình LLM/API key nằm trong `.env` và không được commit. Raw snapshot và frozen
test set được tái sử dụng ở các lần chạy bình thường; không xóa hay sinh lại
`data/eval/test_set.json` khi so sánh ba trạng thái.

## 5. Baseline evidence

| Artifact | Trạng thái |
| --- | --- |
| `data/raw/crossref_response.json`, `crossref_records.json` | Có; 24 records |
| `data/clean/papers_clean.csv`, `.json` | Có; 24 records |
| `data/embeddings/papers_embeddings.json` | Có |
| `data/eval/test_set.json` | Có; frozen, 10 questions |
| `data/results/baseline_metrics.json`, `baseline_answers.json` | Có |
| `data/quality/baseline_quality.json`, `freshness_report.json` | Có; freshness FAIL |
| `data/reports/phase1_report.md` | Có |

| Metric | Baseline |
| --- | ---: |
| Retrieval hit rate | 1.00 |
| Mean Token F1 | 1.00 |
| Judge accuracy | 1.00 |
| Mean judge score | 5.00 |
| Ragas | Skipped (`RUN_RAGAS` chưa bật) |

Baseline schema, completeness, uniqueness và validity đều PASS. Freshness FAIL vì
2/24 records vượt threshold 180 ngày (`oldest_published: 2026-01-01`).

## 6. Corruption, repair và comparison

| Metric/signal | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| Rows | 24 | 26 | 24 |
| Retrieval hit rate | 1.00 | 1.00 | 1.00 |
| Mean Token F1 | 1.00 | 0.70 | 1.00 |
| Judge accuracy | 1.00 | 0.70 | 1.00 |
| Mean judge score | 5.00 | 3.80 | 5.00 |
| Duplicate paper IDs | 0 | 2 | 0 |
| Blank/short summaries | 0 | 3 | 0 |
| Stale rows | 2 | 4 | 2 |

`corruption_log.json` ghi rõ record, field, giá trị trước/sau và scenario. Có 5
document IDs trong frozen ground truth bị ảnh hưởng. Corruption làm giảm chất lượng
câu trả lời dù hit rate không giảm; điều này cho thấy chỉ số retrieval một mình
không đủ để phản ánh tác động của data quality. Repair từ raw snapshot phục hồi
Token F1, judge accuracy và judge score về baseline, đồng thời xóa duplicates và
khôi phục summaries. Freshness repaired vẫn FAIL vì nó tái tạo đúng baseline có 2
record stale.

## 7. Giới hạn và việc cần làm trước khi nộp

| Giới hạn | Ảnh hưởng | Hướng xử lý |
| --- | --- | --- |
| 2 baseline records stale | Baseline/repaired quality không PASS toàn bộ | R2/R3 lọc hoặc thay bằng source records trong 180 ngày, sau đó chạy lại cả hai flow |
| Ragas chưa bật | Không có điểm Ragas | Bật `RUN_RAGAS=1` nếu provider/dependency phù hợp |
| LLM judge có thể fallback khi provider lỗi | Kết quả judge cần ghi rõ cơ chế | Giữ `.env` hợp lệ và ghi nhận provider/model ở lần chạy nộp |

## 8. Checklist trước khi nộp

- [x] Baseline và corruption/repair pipelines đã chạy.
- [x] Metrics, answers, quality/freshness và Markdown reports đã có.
- [x] Ba trạng thái dùng cùng frozen evaluation set.
- [x] Metrics trong báo cáo đọc từ JSON artifact thực tế.
- [x] Repair dùng raw snapshot, không refetch API.
- [ ] Xử lý 2 baseline stale records và chạy lại để baseline/repaired quality PASS.
- [ ] Điền MSSV của các thành viên còn lại nếu yêu cầu nộp.
- [ ] Kiểm tra `.env`/API key không nằm trong Git trước khi nộp.
