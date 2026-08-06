# Báo cáo cá nhân - Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Vũ Quang Huy |
| MSSV | 2A202601412 |
| Khóa/Lớp | K4 |
| Tên nhóm | Space |
| Vai trò chính | R1 - Integration & Release Owner |
| Repository | `https://github.com/HuyVu0402/Day10_Space` |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

Vai trò R1 chịu trách nhiệm tích hợp các phần của R2, R3, R4 và R5 thành pipeline chạy được end-to-end. Phạm vi chính của tôi gồm:

| Module / deliverable | File / artifact liên quan | Kết quả bàn giao |
| --- | --- | --- |
| Phân công và contract nhóm | `PHAN_CONG_CONG_VIEC.md`, `report/group_report.md` | Chốt role, data contract, artifact paths và checklist nghiệm thu |
| Baseline pipeline | `src/pipelines/phase1.py`, `script/run_phase1.py` | Chạy raw -> clean -> index -> eval -> quality -> report |
| Corruption/repair pipeline | `src/pipelines/corruption_flow.py`, `script/run_corruption_flow.py` | Chạy corrupted -> evaluate -> repair from raw -> evaluate -> compare |
| Release evidence | `data/reports/phase1_report.md`, `data/reports/corruption_report.md`, JSON metrics | Đối chiếu artifact thật để hoàn thiện báo cáo nhóm |
| Kiểm tra trước nộp | `git status`, artifact scan, secret scan | Xác nhận repo không track `.env`, không còn TODO trong `src`/`script` |

Ngoài phạm vi R1, tôi cũng hỗ trợ kiểm tra contract bàn giao của các role khác: raw lineage của R2, clean schema của R3, answer schema của R4, test set/metrics/quality của R5.

## 3. Kết quả theo checkpoint

| Checkpoint | Việc đã thực hiện với vai trò R1 | Kết quả |
| --- | --- | --- |
| C0 - Setup | Đọc cấu trúc repo, rà TODO/NotImplemented, xác định file theo owner | Không còn `TODO(student)`/`NotImplementedError` trong `src` và `script` |
| C1 - Contract | Chốt contract raw, clean, evaluation, agent result, metrics và retrieval config | `paper_id` được dùng làm khóa xuyên suốt; `top_k=4`; document-level chunking |
| C2 - Data & Frozen Eval | Kiểm tra raw -> clean -> frozen eval, xác minh ground truth IDs | 24 clean records, 10 eval samples, không có missing ground-truth docs |
| C3 - Baseline | Chạy baseline pipeline end-to-end | Có baseline answers, metrics, quality/freshness và phase1 report |
| C4 - Corruption & Repair | Chạy corruption/repair flow ba trạng thái | Có corrupted/repaired data, corruption log, metrics và comparison report |
| C5 - Submission | Tổng hợp report, đối chiếu metrics JSON, kiểm tra trạng thái repo | Group report và individual report hoàn thiện |

## 4. Artifact đã tạo hoặc xác minh

| Nhóm artifact | File |
| --- | --- |
| Raw data | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` |
| Clean data | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` |
| Frozen eval | `data/eval/test_set.json` |
| Baseline | `data/results/baseline_answers.json`, `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption/Repair | `data/results/corruption_log.json`, `corrupted_*`, `repaired_*`, `data/reports/corruption_report.md` |
| Quality/Freshness | `data/quality/baseline_quality.json`, `corrupted_quality.json`, `repaired_quality.json`, freshness reports |
| Báo cáo | `report/group_report.md`, `report/individual_2A202601412_VuQuangHuy.md` |

## 5. Lệnh đã chạy để xác minh

Baseline pipeline:

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe script\run_phase1.py
```

Kết quả:

```text
Baseline pipeline complete.
Metrics: data/results/baseline_metrics.json
Report: data/reports/phase1_report.md
```

Corruption/repair pipeline:

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe script\run_corruption_flow.py
```

Kết quả:

```text
Corruption/repair comparison complete.
Report: data/reports/corruption_report.md
```

Lệnh Git Bash tương đương:

```bash
PYTHONPATH=src ./.venv/Scripts/python.exe script/run_phase1.py
PYTHONPATH=src ./.venv/Scripts/python.exe script/run_corruption_flow.py
```

## 6. Metrics và phân tích kết quả

| Metric / Signal | Baseline | Corrupted | Repaired | Nhận xét |
| --- | ---: | ---: | ---: | --- |
| Rows | 24 | 26 | 24 | Corruption thêm duplicate rows, repair đưa về baseline |
| Quality status | PASS | FAIL | PASS | Corrupted fail do duplicate ID và summary rỗng/ngắn |
| Retrieval hit rate | 1.00 | 1.00 | 1.00 | Tài liệu ground truth vẫn còn trong index |
| Mean Token F1 | 1.00 | 0.70 | 1.00 | Answer quality giảm rõ khi dữ liệu bị hỏng |
| Judge accuracy | 1.00 | 0.70 | 1.00 | Judge cũng phản ánh suy giảm chất lượng |
| Mean judge score | 5.00 | 3.80 | 5.00 | Repair phục hồi score về baseline |
| Duplicate paper IDs | 0 | 2 | 0 | Quality check bắt được corruption |
| Blank/short summaries | 0 | 3 | 0 | Summary bị hỏng làm answer metric giảm |
| Stale rows | 2 | 4 | 2 | Freshness được báo riêng với quality |

Kết quả chính là corrupted data làm giảm chất lượng câu trả lời dù retrieval hit rate không đổi. Điều này cho thấy RAG evaluation không nên chỉ nhìn hit rate; cần theo dõi thêm Token F1, judge score và data quality signals. Sau repair từ raw snapshot, metrics phục hồi về baseline, chứng minh raw snapshot có vai trò quan trọng trong khả năng tái lập và phục hồi dữ liệu.

## 7. Quyết định kỹ thuật quan trọng

### Giữ frozen test set xuyên suốt C3/C4

Nếu mỗi lần đánh giá lại tạo câu hỏi mới, metrics baseline/corrupted/repaired sẽ không còn so sánh công bằng. Vì vậy pipeline luôn dùng `data/eval/test_set.json` đã đóng băng từ C2. R1 kiểm tra mọi `ground_truth_doc_ids` đều tồn tại trong clean data trước khi chạy evaluation.

### Giữ cùng retrieval config

Tất cả trạng thái dùng document-level chunking, `text_for_embedding`, embedding model `sentence-transformers/all-MiniLM-L6-v2` và `top_k=4`. Nhờ vậy, thay đổi metric phản ánh thay đổi dữ liệu chứ không phải thay đổi cấu hình retrieval.

### Repair từ raw snapshot, không fetch lại API

Corruption flow không gọi lại Crossref API khi repair. Repaired dataset được dựng lại từ `data/raw/crossref_records.json`, giúp so sánh công bằng và đảm bảo có thể audit.

## 8. Blocker đã xử lý

### Lỗi chạy Python trong Git Bash

Lệnh Windows-style:

```bash
.\.venv\Scripts\python.exe script\run_phase1.py
```

không chạy đúng trong Git Bash. Cách chạy đúng là:

```bash
PYTHONPATH=src ./.venv/Scripts/python.exe script/run_phase1.py
```

### Lỗi mạng khi load embedding model trong sandbox

Khi chạy pipeline, `sentence-transformers` cần truy cập/cache model từ HuggingFace. Trong sandbox, lệnh có thể lỗi socket. Tôi đã chạy lại ngoài sandbox để xác minh end-to-end và cả hai pipeline đều hoàn thành.

## 9. Hiểu biết về luồng end-to-end

1. R2 lấy dữ liệu từ Crossref và lưu raw snapshot. Raw response dùng để audit lineage, raw records dùng để R3 clean và repair offline.
2. R3 clean dữ liệu thành schema ổn định, giữ `paper_id`, tạo `text_for_embedding` và loại bỏ duplicate.
3. R4 dùng `text_for_embedding` để tạo embedding MiniLM, lưu vào ChromaDB, sau đó truy xuất `top_k=4` documents cho từng câu hỏi.
4. R5 dùng frozen test set để tính retrieval hit rate, Token F1, judge metrics, quality và freshness.
5. R1 tích hợp toàn bộ thành hai entrypoint: baseline pipeline và corruption/repair pipeline, sau đó đối chiếu report với artifact thật.

## 10. Bài học rút ra

1. `paper_id` là khóa quan trọng nhất của pipeline. Nếu `paper_id` null hoặc duplicate thì raw, clean, index, eval và answers không còn liên kết đáng tin cậy.
2. Frozen test set giúp kết quả C3/C4 có ý nghĩa so sánh. Không được sửa test set giữa các trạng thái.
3. Data quality signal và RAG metric cần được đọc cùng nhau. Corruption có thể không làm hit rate giảm nhưng vẫn làm answer quality giảm.
4. Raw snapshot không chỉ là dữ liệu đầu vào mà còn là cơ chế phục hồi và audit.
5. Vai trò R1 cần kiểm bằng artifact thật, không chỉ dựa vào terminal báo thành công.

## 11. Cam kết cá nhân

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end từ Crossref đến RAG metrics.
- [x] Các kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo cá nhân không sao chép nguyên văn báo cáo nhóm.

**Họ và tên:** Vũ Quang Huy  
**Ngày xác nhận:** 2026-08-06
