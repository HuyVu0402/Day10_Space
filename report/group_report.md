# Báo cáo nhóm - Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4 |
| Tên nhóm | Space |
| Repository | `https://github.com/HuyVu0402/Day10_Space` |
| Ngày chạy artifact gần nhất | 2026-08-06 |

## 2. Thành viên và phân công

| Thành viên | Vai trò | Module / deliverable sở hữu |
| --- | --- | --- |
| Vũ Quang Huy | R1 - Integration & Release Owner | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, scripts, tích hợp và release |
| Mạnh | R2 - Source Ingestion Owner | `src/ingestion/crossref.py`, raw response và raw records |
| Ánh | R3 - Cleaning, Corruption & Repair Owner | `src/ingestion/cleaning.py`, `src/ingestion/corruption.py`, clean/corrupted/repaired datasets |
| Sơn | R4 - Retrieval & RAG Owner | `src/retrieval/`, ChromaDB index, answer-level artifacts |
| Phương | R5 - Evaluation, Observability & Reporting Owner | `src/evaluation/`, `src/observability/`, test set, metrics, quality reports |

## 3. Tổng quan pipeline

Nhóm xây dựng pipeline Data Quality cho RAG dựa trên metadata paper từ Crossref. Pipeline đi theo luồng:

```text
Crossref API
-> raw response + raw records
-> clean dataset
-> MiniLM embeddings + ChromaDB index
-> frozen test set
-> RAG answers
-> metrics + quality/freshness reports
-> corruption
-> re-index/evaluate
-> repair from raw snapshot
-> comparison report
```

Ba trạng thái dữ liệu được đánh giá:

| Trạng thái | Ý nghĩa |
| --- | --- |
| Baseline | Dữ liệu sạch sau cleaning, dùng làm mốc so sánh |
| Corrupted | Dữ liệu bị làm hỏng có kiểm soát để quan sát tác động lên RAG |
| Repaired | Dữ liệu được phục hồi bằng cách chạy lại cleaning từ raw snapshot |

Tất cả trạng thái dùng cùng frozen test set, cùng embedding model, cùng chiến thuật chunking và cùng cấu hình retrieval để đảm bảo so sánh công bằng.

## 4. Data contract

### Raw record

Raw data do R2 bàn giao gồm hai artifact chính:

- `data/raw/crossref_response.json`: raw response từ Crossref, có lineage envelope để audit nguồn dữ liệu.
- `data/raw/crossref_records.json`: danh sách paper records đã parse phẳng để R3 làm sạch và repair offline.

Các trường quan trọng:

```text
paper_id, title, summary, authors, categories, published, updated, abs_url, pdf_url
```

`paper_id` là khóa liên kết xuyên suốt pipeline và phải non-null, unique.

### Clean record

Clean data do R3 bàn giao cho R4/R5 gồm:

```text
paper_id, title, summary, published, authors_joined,
categories_joined, age_days, text_for_embedding, abs_url, pdf_url
```

`text_for_embedding` là nội dung được đưa vào embedding/index. Mỗi paper được index như một document/chunk duy nhất.

### Evaluation sample

Frozen test set do R5 quản lý:

```json
{
  "id": "q1",
  "question_type": "factual",
  "question": "Question text",
  "ground_truth": "Expected answer",
  "ground_truth_doc_ids": ["paper_id"]
}
```

### Agent result

R4 bàn giao answer-level result cho R5:

```json
{
  "answer": "Generated answer",
  "retrieved_doc_ids": ["paper_id"],
  "contexts": ["Retrieved context"],
  "provider": "provider-name",
  "model": "model-name"
}
```

### Retrieval configuration

| Cấu hình | Giá trị |
| --- | --- |
| Chunking strategy | Document-level chunking |
| Chunk source | `text_for_embedding` |
| Document identity | `paper_id` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Retrieval top-k | `4` |

## 5. Kết quả theo checkpoint

| Checkpoint | Kết quả |
| --- | --- |
| C0 - Setup | Hoàn thành. Repo có đủ cấu trúc, dependencies, `.env.example`, không còn `TODO(student)`/`NotImplementedError` trong `src` và `script`. |
| C1 - Contract | Hoàn thành. Nhóm đã chốt role, artifact paths, raw/clean/eval/agent/metrics schema và quy tắc dùng chung `paper_id`. |
| C2 - Data & Frozen Eval | Hoàn thành. Có raw response, raw records, clean CSV/JSON và frozen test set 10 câu. Tất cả `ground_truth_doc_ids` đều tồn tại trong clean data. |
| C3 - Baseline | Hoàn thành. Baseline pipeline chạy end-to-end và sinh answers, metrics, quality/freshness, phase1 report. |
| C4 - Corruption & Repair | Hoàn thành. Corruption flow tạo corrupted/repaired data, log corruption, metrics 3 trạng thái và comparison report. |
| C5 - Submission | Hoàn thành. Group report và individual reports đã có, metrics trong report lấy từ JSON artifact thật. |

## 6. Artifact evidence

| Nhóm artifact | File |
| --- | --- |
| Raw data | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` |
| Clean data | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` |
| Evaluation | `data/eval/test_set.json` |
| Embeddings | `data/embeddings/papers_embeddings.json`, `papers_embeddings_corrupted.json`, `papers_embeddings_repaired.json` |
| Baseline results | `data/results/baseline_answers.json`, `data/results/baseline_metrics.json` |
| Corrupted results | `data/results/corrupted_answers.json`, `data/results/corrupted_metrics.json` |
| Repaired results | `data/results/repaired_answers.json`, `data/results/repaired_metrics.json` |
| Quality/Freshness | `data/quality/baseline_quality.json`, `corrupted_quality.json`, `repaired_quality.json`, freshness reports |
| Reports | `data/reports/phase1_report.md`, `data/reports/corruption_report.md`, `report/group_report.md`, individual reports |

## 7. Baseline result

Baseline được chạy bằng lệnh:

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe script\run_phase1.py
```

Kết quả:

| Metric | Giá trị |
| --- | ---: |
| Dataset state | baseline |
| Question count | 10 |
| Retrieval hit rate | 1.00 |
| Mean Token F1 | 1.00 |
| Judge accuracy | 1.00 |
| Mean judge score | 5.00 |

Quality baseline PASS. Freshness được báo riêng; baseline có 2 stale records theo ngưỡng 180 ngày, nhưng đây là tín hiệu freshness của source data, không phải lỗi pipeline.

## 8. Corruption và repair result

Corruption/repair flow được chạy bằng lệnh:

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe script\run_corruption_flow.py
```

Corruption scenarios:

| Scenario | Mô tả |
| --- | --- |
| Blank Summary | Xóa summary ở một số records |
| Title Truncation & Noise Injection | Cắt ngắn title và chèn noise token |
| Stale/Corrupted Date | Đổi ngày published thành giá trị stale |
| Duplicate Row Injection | Tạo duplicate `paper_id` có chủ đích |

`data/results/corruption_log.json` ghi lại record bị tác động, field bị sửa, giá trị trước/sau và scenario. Corruption chạm vào 5 frozen ground-truth documents, nên có tác động thật lên bộ câu hỏi đánh giá.

## 9. So sánh ba trạng thái

| Metric / Signal | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| Rows | 24 | 26 | 24 |
| Quality status | PASS | FAIL | PASS |
| Retrieval hit rate | 1.00 | 1.00 | 1.00 |
| Mean Token F1 | 1.00 | 0.70 | 1.00 |
| Judge accuracy | 1.00 | 0.70 | 1.00 |
| Mean judge score | 5.00 | 3.80 | 5.00 |
| Duplicate paper IDs | 0 | 2 | 0 |
| Blank/short summaries | 0 | 3 | 0 |
| Stale rows | 2 | 4 | 2 |

Kết quả cho thấy corrupted data làm giảm chất lượng câu trả lời: Token F1 và judge accuracy giảm từ 1.00 xuống 0.70, mean judge score giảm từ 5.00 xuống 3.80. Retrieval hit rate vẫn giữ 1.00 vì tài liệu ground truth vẫn còn trong index, nhưng nội dung bị hỏng làm answer quality giảm. Điều này cho thấy chỉ dùng retrieval hit rate là chưa đủ để đánh giá chất lượng RAG.

Sau repair, các metric quay lại mức baseline. Repair không gọi lại Crossref API mà dùng raw snapshot đã lưu, đảm bảo có thể tái lập và audit.

## 10. Data quality và observability

Nhóm theo dõi các signal chính:

| Signal | Mục đích |
| --- | --- |
| Required columns | Đảm bảo schema không bị vỡ |
| Row count | Phát hiện data rỗng hoặc corruption làm tăng/giảm bất thường |
| `paper_id` non-null/unique | Bảo vệ khóa liên kết giữa raw, clean, index, eval và answers |
| Title/summary completeness | Đảm bảo document có nội dung cho RAG |
| Summary minimum length | Phát hiện summary rỗng/ngắn bất thường |
| Published ISO date | Phát hiện ngày sai format |
| Freshness | Theo dõi records stale theo ngưỡng 180 ngày |

Baseline và repaired quality PASS. Corrupted quality FAIL đúng kỳ vọng do duplicate `paper_id`, blank summaries và short summaries. Freshness report được tách riêng khỏi quality pass/fail để không nhầm stale source data với lỗi corruption.

## 11. Vai trò của raw snapshot

Raw snapshot là điểm neo quan trọng của pipeline:

1. Giúp audit dữ liệu lấy từ đâu, bằng query nào, lúc nào.
2. Giữ payload gốc để có thể parse lại offline.
3. Cho phép repair corrupted data mà không fetch lại API.
4. Bảo vệ tính công bằng khi so sánh baseline, corrupted và repaired.

Trong C4, corruption chỉ tác động vào clean/corrupted artifacts, không sửa `data/raw/`. Repair đọc lại `data/raw/crossref_records.json` và chạy cleaning để tạo `papers_clean_repaired.csv/json`.

## 12. Giới hạn

| Giới hạn | Ảnh hưởng | Cách ghi nhận |
| --- | --- | --- |
| Baseline có 2 stale records | Freshness baseline/repaired là `is_fresh=false` | Báo riêng như signal freshness của source data |
| Ragas skipped | Không có Ragas score | Metrics chính vẫn gồm hit rate, Token F1 và judge |
| Retrieval hit rate không giảm khi corrupted | Hit rate không phản ánh hết answer quality | Dùng thêm Token F1 và judge score để phân tích |

## 13. Hướng dẫn tái hiện

Với PowerShell:

```powershell
uv sync
Copy-Item .env.example .env
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe script\run_phase1.py
.\.venv\Scripts\python.exe script\run_corruption_flow.py
```

Với Git Bash:

```bash
PYTHONPATH=src ./.venv/Scripts/python.exe script/run_phase1.py
PYTHONPATH=src ./.venv/Scripts/python.exe script/run_corruption_flow.py
```

## 14. Checklist trước khi nộp

- [x] C0 setup và TODO scan hoàn thành.
- [x] C1 contract và phân công role hoàn thành.
- [x] C2 raw, clean và frozen eval artifacts tồn tại.
- [x] C3 baseline pipeline chạy thành công.
- [x] C4 corruption/repair pipeline chạy thành công.
- [x] C5 group report và individual reports đã có.
- [x] Metrics trong report khớp với JSON artifact.
- [x] Ba trạng thái dùng cùng frozen test set, embedding model và `top_k=4`.
- [x] Repair dùng raw snapshot, không refetch API.
- [x] `.env`, API key và Chroma database không bị track trong Git.

## 15. Kết luận

Nhóm đã hoàn thành pipeline Data Observability cho RAG với đầy đủ baseline, corruption, repair và comparison evidence. Kết quả chứng minh data quality có tác động trực tiếp đến answer quality của RAG: khi dữ liệu bị corrupted, quality checks FAIL và answer metrics giảm; khi repair từ raw snapshot, metrics phục hồi về baseline. Pipeline có thể chạy lại bằng một lệnh cho baseline và một lệnh cho corruption/repair, các artifact sinh ra đủ để audit và tái hiện kết quả.
