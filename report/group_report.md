# Group Report — Day 10: Data Pipeline & Data Observability

> Dùng mẫu này cho báo cáo chung của nhóm 3–5 thành viên. Thay toàn bộ nội dung trong dấu `[ ]` bằng thông tin và kết quả thực tế. Xóa các dòng hướng dẫn không còn cần thiết trước khi nộp.

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | TBD - cập nhật trước khi nộp |
| Tên nhóm         | TBD - cập nhật trước khi nộp |
| Repository         | `D:\CODE\AITHUCCHIEN\LABS\Day10_Space` |
| Ngày hoàn thành | TBD - cập nhật khi hoàn tất C5 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Huy | TBD | R1 - Integration & Release Owner | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `script/`, cấu hình tích hợp, `report/group_report.md` |
| 2 | Mạnh | TBD | R2 - Source Ingestion Owner | `src/ingestion/crossref.py`, `data/raw/crossref_response.json`, `data/raw/crossref_records.json` |
| 3 | Ánh | TBD | R3 - Cleaning, Corruption & Repair Owner | `src/ingestion/cleaning.py`, `src/ingestion/corruption.py`, clean/corrupted/repaired datasets |
| 4 | Sơn | TBD | R4 - Retrieval & RAG Owner | `src/retrieval/`, ChromaDB collections, answer-level artifacts |
| 5 | Phương | TBD | R5 - Evaluation, Observability & Reporting Owner | `src/evaluation/`, `src/observability/`, test set, metrics, quality reports |

## 2. Tóm tắt kết quả

Viết từ 150–250 từ, trả lời ngắn gọn:

- Nhóm đã hoàn thành những phần nào?
- Baseline pipeline đã tạo ra các artifact nào?
- Corruption nào ảnh hưởng rõ nhất đến data quality hoặc agent?
- Repair đã phục hồi được chỉ số nào?
- Blocker hoặc giới hạn quan trọng nhất còn lại là gì?

**Tóm tắt của nhóm:**

TBD sau khi C3 và C4 chạy xong. Tại C1, nhóm đã chốt phân công, data contracts, artifact paths và điều kiện bàn giao giữa các role. Không ghi metrics hoặc kết luận hiệu quả khi chưa có JSON artifacts sinh ra từ pipeline thật.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

Điều chỉnh sơ đồ dưới đây nếu cách triển khai thực tế của nhóm khác starter:

```text
Crossref API
    -> raw response/raw records
    -> cleaning và data modeling
    -> embedding + ChromaDB index
    -> evaluation baseline
    -> quality/freshness reports
    -> corruption
    -> re-index và re-evaluate
    -> repair từ dữ liệu nguồn
    -> comparison report
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref `/works` API | Fetch, timeout, retry/backoff, parse raw records ổn định | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Mạnh |
| Cleaning          | `data/raw/crossref_records.json` | Chuẩn hóa schema, loại record lỗi, tạo `text_for_embedding`, tính `age_days` | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Ánh |
| Embedding/index   | Clean/corrupted/repaired datasets | Embed bằng MiniLM, build ChromaDB collection riêng cho từng trạng thái | `data/chroma/`, `data/embeddings/*.json` | Sơn |
| Evaluation        | Frozen test set và agent results | Tính retrieval hit rate, Token F1, LLM judge nếu có key | `data/eval/test_set.json`, `data/results/*metrics.json`, `data/results/*answers.json` | Phương |
| Observability     | Dataset ở từng trạng thái | Completeness, uniqueness, validity, freshness checks | `data/quality/`, `data/reports/phase1_report.md` | Phương |
| Corruption/repair | Clean baseline và raw snapshot | Tạo corruption có log, repair bằng cleaning lại từ raw snapshot | `data/clean/*corrupted*`, `data/clean/*repaired*`, `data/results/corruption_log.json` | Ánh |
| Orchestration     | Artifacts từ R2-R5 | Ghép phase 1 và corruption flow, chặn input rỗng/thiếu, kiểm tra output | `script/run_phase1.py`, `script/run_corruption_flow.py`, reports cuối | Huy |

### C1 - Contract và điều kiện bàn giao

Các contract dưới đây được chốt cho C1 và không tự ý đổi sau checkpoint này nếu chưa thống nhất lại trong nhóm.

| Contract | Owner chính | Người nhận | Điều kiện bàn giao |
| --- | --- | --- | --- |
| Raw records | Mạnh | Ánh, Huy | JSON hợp lệ, `paper_id` ổn định, đủ `title`, `summary`, `authors`, `published`, `abs_url` để clean/repair offline |
| Clean records | Ánh | Sơn, Phương, Huy | Có đủ các trường bắt buộc, không duplicate `paper_id`, `text_for_embedding` không rỗng |
| Evaluation set | Phương | Sơn, Huy | `data/eval/test_set.json` có 5-10 câu factual, mọi `ground_truth_doc_ids` tồn tại trong clean data |
| Agent results | Sơn | Phương, Huy | Mỗi câu có `answer`, `retrieved_doc_ids`, `contexts`, `provider`, `model`; lỗi LLM phải có dạng có thể lưu |
| Aggregate metrics | Phương | Huy | JSON có `dataset_state`, `question_count`, `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score` |

Schema tối thiểu đã chốt:

| Artifact | Trường bắt buộc |
| --- | --- |
| Raw record | `paper_id`, `title`, `summary`, `authors`, `published`, `abs_url` |
| Clean record | `paper_id`, `title`, `summary`, `published`, `authors_joined`, `categories_joined`, `age_days`, `text_for_embedding`, `abs_url`, `pdf_url` |
| Evaluation sample | `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids` |
| Agent result | `answer`, `retrieved_doc_ids`, `contexts`, `provider`, `model` |
| Aggregate metrics | `dataset_state`, `question_count`, `retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score` |

Raw record optional fields hiện có trong `data/raw/crossref_records.json`:

```text
updated, categories, primary_category, pdf_url, comment
```

Source lineage không bắt buộc nằm trong từng raw record. Các thông tin audit sau được đọc từ `data/raw/crossref_response.json`:

```text
fetched_at, source_url, params, payload
```

Mapping từ Crossref payload gốc sang parsed raw record:

| Crossref payload | Parsed raw record | Ghi chú |
| --- | --- | --- |
| `DOI` | `paper_id` | Tạo ID ổn định từ DOI; không dùng vị trí trong danh sách |
| `title[0]` | `title` | Chuẩn hóa whitespace |
| `abstract` | `summary` | Loại markup JATS/HTML ở mức parse để R3 có text sạch tối thiểu |
| `author[]` | `authors` | Danh sách tên tác giả dạng string |
| `subject[]` | `categories` | Optional vì payload hiện tại có thể thiếu toàn bộ `subject` |
| `type` | `primary_category` | Fallback khi `subject` rỗng |
| `published`/`published-online`/`published-print`/`issued` | `published` | ISO date |
| `deposited`/`indexed` | `updated` | ISO date |
| `URL` | `abs_url` | DOI landing page |
| `link[]` PDF | `pdf_url` | Optional |

Trạng thái dataset dùng trong toàn bộ bài:

| State | Ý nghĩa | Artifact metrics |
| --- | --- | --- |
| `baseline` | Dữ liệu sạch sau ingestion và cleaning | `data/results/baseline_metrics.json` |
| `corrupted` | Dữ liệu sạch bị tạo lỗi có chủ đích, không sửa raw/baseline | `data/results/corrupted_metrics.json` |
| `repaired` | Dữ liệu được dựng lại từ `data/raw/crossref_records.json` | `data/results/repaired_metrics.json` |

Quy tắc C1 bắt buộc:

- `paper_id` giữ nguyên xuyên suốt raw -> clean -> index -> test set -> answers.
- `data/eval/test_set.json` được đóng băng từ C2; C3 và C4 chỉ load lại, không sinh lại hoặc sửa nội dung.
- Baseline, corrupted và repaired dùng cùng test set, embedding model, `top_k`, LLM model và evaluator.
- Corruption không sửa `data/raw/` hoặc clean baseline.
- Repair không gọi lại Crossref API; chỉ dùng raw snapshot đã lưu.
- Báo cáo không ghi số liệu minh họa; mọi metrics phải đọc từ JSON artifacts thực tế.

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | Theo `.env`, mặc định starter là `gemini` |
| `LLM_MODEL`                | Theo `.env`, mặc định starter là `gemini-2.5-flash` |
| Embedding model              | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | Tối đa `24` theo `Settings.max_results`; số thực tế cập nhật sau C2 |
| Retrieval`top_k`           | `4` |
| Freshness threshold          | `180` ngày |
| Random seed, nếu có        | R3 chốt seed cố định khi implement corruption |

Không dán nội dung API key hoặc file `.env` vào báo cáo.

### Lệnh cài đặt

Chỉ giữ lại cách nhóm đã dùng.

```bash
uv sync
```

Hoặc:

```bash
python -m pip install -e .
```

### Lệnh chạy

Baseline:

```bash
uv run python script/run_phase1.py
```

Hoặc với môi trường `pip` đã kích hoạt:

```bash
python script/run_phase1.py
```

Corruption flow:

```bash
uv run python script/run_corruption_flow.py
```

Hoặc với môi trường `pip` đã kích hoạt:

```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái                                    | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | [Thành công/Thất bại một phần/Thất bại] | [Thời gian]                  | [Artifact hoặc log đã che secret] |
| Corruption flow   | [Thành công/Thất bại một phần/Thất bại] | [Thời gian]                  | [Artifact hoặc log đã che secret] |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref REST API `/works` |
| Query/filter                | Query: `agentic retrieval augmented generation large language model`; filter: `from-pub-date:<today-180d>,has-abstract:true` |
| Thời điểm lấy dữ liệu | Đọc từ `data/raw/crossref_response.json.fetched_at` sau C2 |
| Số record nhận được    | Đọc từ `data/raw/crossref_records.json` sau C2 |
| Cơ chế retry/backoff      | R2 implement timeout và exponential backoff cho `429`/`5xx` |

### Raw và clean schema

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id` | string | Có trong raw/clean | Document ID ổn định xuyên pipeline | Loại record nếu không tạo được ID |
| `title` | string | Có trong raw/clean | Tiêu đề paper | Loại record nếu rỗng |
| `summary` | string | Có trong raw/clean | Nội dung chính để tạo context, parse từ Crossref `abstract` | Loại record nếu rỗng hoặc quá ngắn theo rule cleaning |
| `authors` | list[string] | Có trong raw | Danh sách tác giả đã parse từ Crossref `author[]` | R3 chuẩn hóa thành `authors_joined`; nếu thiếu thì dùng chuỗi rỗng có kiểm soát |
| `authors_joined` | string | Có trong clean | Tác giả dạng chuỗi để report/index | Sinh từ `authors` |
| `categories` | list[string] | Không | Chủ đề/lĩnh vực; payload hiện tại có thể thiếu toàn bộ `subject` | R3 chuẩn hóa thành `categories_joined`; cho phép rỗng |
| `categories_joined` | string | Có trong clean | Chủ đề dạng chuỗi để report/index | Sinh từ `categories` hoặc `primary_category` |
| `primary_category` | string | Không | Fallback category từ Crossref `type` | Dùng khi `categories` rỗng |
| `published` | ISO date string | Có trong raw/clean | Ngày xuất bản | Parse sang ISO date; record sai ngày bị loại hoặc đánh dấu invalid |
| `updated` | ISO date string | Không | Ngày cập nhật/deposit/index | Giữ để freshness lineage nếu có |
| `abs_url` | string | Có trong raw/clean | DOI landing page, parse từ Crossref `URL` | Loại hoặc đánh dấu invalid nếu rỗng tùy rule quality |
| `pdf_url` | string | Không | URL PDF nếu có | Giữ rỗng nếu source thiếu |
| `comment` | string | Không | Publisher/container/type để audit/report | Giữ rỗng nếu source thiếu |
| `age_days` | integer | Có trong clean | Tuổi dữ liệu tại thời điểm clean | Tính từ `published` và `run_date` |
| `text_for_embedding` | string | Có trong clean | Text đưa vào embedding/index | Tạo từ title, authors/categories và summary; loại nếu rỗng |

### Quy tắc cleaning

| Quy tắc                                 | Quality dimension liên quan | Số record bị tác động | Cách xác minh      |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| [Ví dụ: loại record không có title] | [Completeness/Validity/...]  |              [Số lượng] | [Artifact/kiểm tra] |
| [Quy tắc thực tế]                     | [Dimension]                  |              [Số lượng] | [Artifact/kiểm tra] |

Giải thích cách nhóm tạo `text_for_embedding`, document ID và `age_days`:

`paper_id` do R2 tạo ổn định từ DOI hoặc định danh nguồn, không dùng vị trí trong danh sách. R3 giữ nguyên `paper_id` khi clean, corrupted và repaired. `text_for_embedding` dùng mẫu thống nhất `Title: ...\nAuthors: ...\nCategories: ...\nSummary: ...` để retrieval có đủ tín hiệu tiêu đề, tác giả, lĩnh vực và nội dung. `age_days` được tính bằng số ngày giữa `run_date` của pipeline và `published`.

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 5-10 câu factual, chốt khi C2 tạo test set |
| Các`question_type`                    | Tối thiểu `factual`; có thể thêm loại khác nếu ground truth rõ |
| Ground-truth document ID                 | Mỗi ID phải tồn tại trong clean baseline trước khi đóng băng test set |
| Embedding model                          | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection                  | `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Retrieval`top_k`                       | `4` |
| LLM provider/model                       | Theo `.env`; phải giữ nguyên giữa ba trạng thái khi so sánh |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` |

Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:

Dùng cùng một frozen test set giúp phép so sánh chỉ phản ánh tác động của dữ liệu ở từng trạng thái. Nếu sinh lại câu hỏi sau corruption hoặc repair, thay đổi metric có thể đến từ câu hỏi khác hoặc ground truth khác, không còn chứng minh được quan hệ dữ liệu xấu -> retrieval/answer quality -> repair.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/`                          | [Có/Thiếu] | [Ghi chú] |
| Cleaned dataset          | `data/clean/`                        | [Có/Thiếu] | [Ghi chú] |
| Embedding manifest/index | `data/embeddings/`                   | [Có/Thiếu] | [Ghi chú] |
| Evaluation set           | `data/eval/`                         | [Có/Thiếu] | [Ghi chú] |
| Baseline metrics         | `data/results/baseline_metrics.json` | [Có/Thiếu] | [Ghi chú] |
| Quality/freshness        | `data/quality/`                      | [Có/Thiếu] | [Ghi chú] |
| Baseline report          | `data/reports/phase1_report.md`      | [Có/Thiếu] | [Ghi chú] |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` |     [Giá trị] | [Ý nghĩa trong kết quả của nhóm]  |
| `mean_token_f1`      |     [Giá trị] | [Diễn giải]                           |
| `judge_accuracy`     |     [Giá trị] | [Diễn giải]                           |
| `mean_judge_score`   |     [Giá trị] | [Diễn giải]                           |
| Ragas, nếu có        | [Giá trị/N/A] | [Diễn giải hoặc lý do không chạy] |

## 8. Data quality và freshness

### Quality checks

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline      | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| [Tên check] | [Dimension]       | [Ngưỡng]         | [Pass/Fail + giá trị] | [Artifact]   |
| [Tên check] | [Dimension]       | [Ngưỡng]         | [Pass/Fail + giá trị] | [Artifact]   |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | [Dataset/index/artifact]            |
| Timestamp mới nhất       | [Giá trị]                         |
| Ngưỡng freshness         | [Giá trị]                         |
| Trạng thái baseline      | [Fresh/Stale/Unknown]               |
| Lý do                     | [Giải thích dựa trên số liệu] |

## 9. Corruption scenarios và repair

| Corruption         | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair   |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| [Loại corruption] | [Mô tả]  |          [Số lượng] | [Kỳ vọng]              | [Artifact/metric]     | [Cách repair] |
| [Loại corruption] | [Mô tả]  |          [Số lượng] | [Kỳ vọng]              | [Artifact/metric]     | [Cách repair] |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: [Có/Thiếu]
- Nhận xét: [Log có đủ loại corruption, record bị tác động và tham số hay không?]

Giải thích cách repair đảm bảo dữ liệu được phục hồi từ nguồn đáng tin cậy thay vì chỉ che kết quả lỗi:

[Giải thích tại đây.]

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`   |      [ ] |       [ ] |      [ ] |                      [ ] |             [ ] | [Nhận xét] |
| `mean_token_f1`        |      [ ] |       [ ] |      [ ] |                      [ ] |             [ ] | [Nhận xét] |
| `judge_accuracy`       |      [ ] |       [ ] |      [ ] |                      [ ] |             [ ] | [Nhận xét] |
| `mean_judge_score`     |      [ ] |       [ ] |      [ ] |                      [ ] |             [ ] | [Nhận xét] |
| Quality checks pass/fail |      [ ] |       [ ] |      [ ] |                      [ ] |             [ ] | [Nhận xét] |
| Freshness status         |      [ ] |       [ ] |      [ ] |                      [ ] |             [ ] | [Nhận xét] |

Nêu ít nhất hai kết luận có quan hệ nhân quả được hỗ trợ bởi artifacts:

1. [Corruption/data change] → [quality/freshness signal] → [retrieval/answer metric].
2. [Repair action] → [quality/freshness recovery] → [agent metric recovery hoặc lý do chưa recovery].

Không kết luận corruption “có tác động” nếu số liệu không cho thấy thay đổi. Nếu kết quả khác kỳ vọng, mô tả giả thuyết và cách nhóm đã kiểm tra.

## 11. Vấn đề tích hợp quan trọng

Mô tả một vấn đề phát sinh khi ghép các module trong pipeline và cách nhóm xử lý:

- **Triệu chứng:** [Lỗi hoặc kết quả sai.]
- **Nguyên nhân:** [Root cause.]
- **Cách xử lý:** [Thay đổi đã thực hiện.]
- **Cách xác minh:** [Lệnh và artifact.]

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng   | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| [Giới hạn]          | [Ảnh hưởng] | [Đề xuất]                              |
| [Giới hạn]          | [Ảnh hưởng] | [Đề xuất]                              |

## 13. Checklist trước khi nộp

- [ ] Thông tin nhóm và repository chính xác.
- [ ] Phân công khớp với module, artifact và kết quả thực tế.
- [ ] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [ ] Baseline, corrupted và repaired dùng cùng evaluation set.
- [ ] Bảng metrics khớp với các file trong `data/results/`.
- [ ] Quality/freshness conclusions khớp với `data/quality/`.
- [ ] Các đường dẫn báo cáo và artifact truy cập được.
- [ ] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [ ] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
