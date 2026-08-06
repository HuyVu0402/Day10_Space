# Member Role Report - Day 10: Data Pipeline & Data Observability

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

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Contract và phân công nhóm | `report/group_report.md` | `PHAN_CONG_CONG_VIEC.md`, yêu cầu lab | Phân công role, data contract, artifact paths | Hoàn thành C1 |
| C2 integration orchestration | `src/pipelines/phase1.py`, `script/run_phase1.py` | Raw records từ R2, clean logic từ R3, testset logic từ R5 | Raw -> clean -> frozen test set validation | Hoàn thành C2 |
| Release evidence | `data/reports/c2_integration_summary.json` | Output C2 pipeline | Summary số record và trạng thái reuse test set | Hoàn thành C2 |
| Corruption flow integration | `src/pipelines/corruption_flow.py` | Metrics, corrupted/repaired datasets | Comparison flow ba trạng thái | Chưa thực hiện, thuộc C4 |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Kiểm tra R2 C1 | R2 - Source Ingestion | Xác nhận raw records pass contract tối thiểu, phát hiện source lineage wrapper/date/category cần sửa |
| Kiểm tra R3 C1 | R3 - Cleaning/Corruption | Xác nhận clean schema pass, phát hiện `categories_joined` fallback và `text_for_embedding` cần thống nhất |
| Kiểm tra R4 C1 | R4 - Retrieval/RAG | Xác nhận embedding/index baseline có artifact, phát hiện agent result thiếu `provider`, `model` |
| Triển khai R5 C1 | R5 - Evaluation/Observability | Tạo test set builder, quality/freshness checks và report functions; sinh `test_set.json`, quality/freshness artifacts |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Chốt contract C1 | `report/group_report.md` | Raw, Clean, Evaluation, Agent Result, Metrics schema; quy tắc `paper_id` non-null/unique | Đọc mục C1 trong `report/group_report.md` |
| Ghép C2 raw -> clean -> test set | `src/pipelines/phase1.py` | Entry point C2 chạy được bằng một lệnh | `PYTHONPATH=src ./.venv/Scripts/python.exe script/run_phase1.py` |
| Xác minh frozen test set không bị ghi đè | `data/eval/test_set.json` | `test_set_reused=true` | `data/reports/c2_integration_summary.json` |
| Xác minh ground truth IDs | `data/eval/test_set.json`, `data/clean/papers_clean.csv` | Không có `ground_truth_doc_ids` thiếu trong clean data | Script validation trong C2 |

Output cụ thể đã tạo/giúp xác minh:

```text
data/reports/c2_integration_summary.json
raw_records=24
clean_records=24
test_set_samples=10
test_set_reused=true
```

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Vai trò R1 cần đảm bảo các phần do R2, R3 và R5 bàn giao có thể nối với nhau thành một luồng có kiểm chứng. Ở C2, trọng tâm là không chạy toàn bộ RAG/LLM ngay, mà xác minh contract quan trọng nhất: raw records đọc được, clean data đúng schema, frozen evaluation set tồn tại, và mọi `ground_truth_doc_ids` đều liên kết được với `paper_id` trong clean data.

### Cách triển khai

`src/pipelines/phase1.py` hiện thực hiện luồng C2:

1. Load settings.
2. Load `data/raw/crossref_records.json`, hoặc fetch lại nếu `REFRESH_SOURCE=true`.
3. Gọi `build_clean_dataframe()` để tạo clean dataframe.
4. Validate clean dataframe: đủ cột, không rỗng, `paper_id` non-null/unique, `text_for_embedding` không rỗng.
5. Lưu `data/clean/papers_clean.csv` và `data/clean/papers_clean.json`.
6. Gọi `build_test_set()`. Nếu `data/eval/test_set.json` đã tồn tại thì load lại, không ghi đè.
7. Validate test set: đủ key bắt buộc, ground truth không rỗng, mọi `ground_truth_doc_ids` tồn tại trong clean data.
8. Ghi `data/reports/c2_integration_summary.json`.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `data/raw/crossref_records.json` với `paper_id`, `title`, `summary`, `authors`, `published`, `abs_url` |
| Output | `papers_clean.csv`, `papers_clean.json`, `test_set.json`, `c2_integration_summary.json` |
| Module phụ thuộc | `ingestion.crossref`, `ingestion.cleaning`, `evaluation.testset`, `core.config` |
| Module sử dụng output | R4 dùng clean data để build index; R5 dùng test set để evaluate |
| Điều kiện lỗi cần xử lý | Raw rỗng, clean data rỗng, thiếu cột clean, duplicate/null `paper_id`, test set thiếu doc ID |

### Cách xác minh

```bash
PYTHONPATH=src ./.venv/Scripts/python.exe script/run_phase1.py
```

- Kết quả mong đợi: pipeline C2 chạy qua, không ghi đè frozen test set, không có missing ground-truth docs.
- Kết quả thực tế:

```text
C2 integration check passed.
raw_records=24
clean_records=24
test_set_samples=10
test_set_reused=True
```

- Artifact/log: `data/reports/c2_integration_summary.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** C2 cần kiểm tra tích hợp, nhưng C3 mới là baseline đầy đủ có embedding, agent và metrics.
- **Các phương án đã cân nhắc:** Một là implement luôn full phase 1 end-to-end; hai là làm C2 guard trước để khóa raw -> clean -> frozen eval.
- **Phương án đã chọn:** Làm C2 integration flow trước.
- **Lý do:** Nếu test set bị ghi đè hoặc `ground_truth_doc_ids` không tồn tại trong clean data thì mọi metric C3/C4 sau này không đáng tin. Chặn lỗi này sớm giúp các role khác tích hợp an toàn hơn.
- **Bằng chứng quyết định phù hợp:** `test_set_reused=True`, `missing_doc_ids=[]`, `paper_id_null=0`, `paper_id_duplicates=0`.

Quyết định liên quan retrieval mà R1 cần giữ nhất quán khi tích hợp C3/C4: starter hiện dùng chiến thuật chunking ở mức document, tức mỗi paper clean là một document/chunk duy nhất lấy từ `text_for_embedding`, thay vì tách summary thành nhiều đoạn nhỏ. Cách này phù hợp với lab vì mỗi sample ground truth gắn với `paper_id`, nên retrieval hit rate có thể đo trực tiếp bằng document ID. `top_k` được cấu hình trong `Settings.top_k=4`; khi so sánh baseline, corrupted và repaired, R1 phải giữ nguyên `top_k=4`, embedding model và test set để metric phản ánh thay đổi dữ liệu chứ không phải thay đổi cấu hình retrieval.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `AttributeError: 'Paths' object has no attribute 'reports_dir'`
- **Lệnh hoặc bước tái hiện:** chạy `script/run_phase1.py`.
- **Nguyên nhân gốc:** `src/pipelines/phase1.py` tham chiếu `settings.paths.reports_dir`, nhưng `Paths` trong `src/core/config.py` không có field này.
- **Cách xử lý:** Đổi sang `settings.paths.baseline_report.parent / "c2_integration_summary.json"`.
- **Cách xác minh sau khi sửa:** chạy lại `PYTHONPATH=src ./.venv/Scripts/python.exe script/run_phase1.py`, output C2 pass.
- **Điều học được:** Khi orchestrate pipeline, R1 phải dùng path contract có sẵn trong `core.config`, không tự thêm tên field ngoài config.

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu đi từ Crossref API vào `crossref_response.json` để giữ source lineage, sau đó được parse thành `crossref_records.json`. Cleaning chuyển raw records thành clean CSV/JSON có `text_for_embedding`. R4 dùng `text_for_embedding` để tạo embedding và ChromaDB index.
2. Evaluation set gồm các câu hỏi factual và `ground_truth_doc_ids`. Khi agent trả lời, retrieval được xem là hit nếu `retrieved_doc_ids` chứa ít nhất một ground-truth document ID. Vì starter đang index mỗi paper như một chunk/document duy nhất, `ground_truth_doc_ids` có thể đối chiếu trực tiếp với `paper_id` trong Chroma metadata.
3. Quality checks kiểm schema/completeness/uniqueness/validity như `paper_id` unique hay summary đủ dài. Freshness monitoring tập trung vào tuổi dữ liệu, latest/oldest published date và số dòng stale.
4. Phải dùng cùng test set cho baseline, corrupted và repaired để khác biệt metric phản ánh thay đổi dữ liệu, không phải thay đổi câu hỏi hoặc ground truth. Tương tự, phải giữ cùng `top_k=4` và cùng embedding model trong cả ba trạng thái.
5. Repair thành công khi repaired dataset được dựng lại từ raw snapshot, quality/freshness phục hồi so với corrupted, và metrics như retrieval hit rate, token F1, judge score phục hồi gần baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | N/A | N/A | N/A | Chưa chạy C3/C4 |
| `mean_token_f1` | N/A | N/A | N/A | Chưa chạy C3/C4 |
| `judge_accuracy` | N/A | N/A | N/A | Chưa chạy C3/C4 |
| `mean_judge_score` | N/A | N/A | N/A | Chưa chạy C3/C4 |
| Quality checks | baseline freshness hiện fail | N/A | N/A | R5 quality report có `freshness_threshold` fail do 2 stale rows |
| Freshness status | `is_fresh=false` | N/A | N/A | `stale_rows=2`, threshold 180 ngày |

### Kết luận từ số liệu

1. Chưa kết luận corruption -> agent metric vì C4 chưa chạy.
2. Chưa kết luận repair -> metric recovery vì C4 chưa chạy.

Kết quả khác kỳ vọng hiện tại: baseline quality freshness đang fail vì clean data có 2 stale rows theo ngưỡng 180 ngày. Đây là tín hiệu thật từ artifact `data/quality/freshness_report.json`, không phải lỗi pipeline C2.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. `paper_id` là khóa nối toàn bộ pipeline; nếu null/duplicate thì evaluation và repair đều mất ý nghĩa.
2. Frozen test set phải được bảo vệ sớm, vì C3/C4 chỉ có ý nghĩa khi dùng cùng câu hỏi và cùng ground truth.
3. R1 không chỉ chạy lệnh cuối; R1 phải kiểm contract giữa các role bằng artifact thật trước khi nhận bàn giao.

### Nếu có thêm thời gian

Hoàn thiện C3 để `phase1.py` chạy full baseline: build Chroma index, evaluate, lưu baseline metrics/answers, chạy quality/freshness và tạo `phase1_report.md`. Cách đo là kiểm đủ `data/results/baseline_metrics.json`, `data/results/baseline_answers.json`, `data/reports/phase1_report.md`.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Huy
**Ngày xác nhận:** 2026-08-06
