# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Đức Mạnh |
| MSSV               | 2A202601176 |
| Khóa/Lớp         | K4 |
| Tên nhóm         | Space |
| Vai trò chính    | R2 - Source Ingestion Owner |
| Repository         | https://github.com/HuyVu0402/Day10_Space.git |
| Ngày hoàn thành | 2026-8-6 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Crossref ingestion | `src/ingestion/crossref.py` / `fetch_source_records`, `parse_crossref_payload`, `load_raw_records` | `settings.source_query`, `settings.source_filter`, Crossref API payload | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Hướng dẫn raw schema và `paper_id` | `src/ingestion/cleaning.py` (Role 3 - Ánh) | Giúp Role 3 dùng raw snapshot để clean và repair |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Implement Crossref ingestion | `src/ingestion/crossref.py` | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | `uv run python -c "from src.core.config import load_settings; from src.ingestion.crossref import load_raw_records; s=load_settings(); recs=load_raw_records(s.paths.raw_records_json); print('total', len(recs))"` |
| Verify raw snapshot consistency | `src/ingestion/crossref.py` | 24 raw records, no duplicate `paper_id`, all records have title and summary | `uv run python -c "from src.core.config import load_settings; from src.ingestion.crossref import load_raw_records; s=load_settings(); recs=load_raw_records(s.paths.raw_records_json); ids=[r.paper_id for r in recs]; print('duplicate_count', len(ids)-len(set(ids))); print('missing_title', sum(1 for r in recs if not r.title)); print('missing_summary', sum(1 for r in recs if not r.summary))"` |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

Tạo raw ingestion artifact gồm `data/raw/crossref_response.json` và `data/raw/crossref_records.json` với 24 bản ghi hợp lệ, `paper_id` ổn định từ DOI và logic parse đủ `title`/`summary`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Role 2 cần đảm bảo dữ liệu nguồn được lấy từ Crossref và lưu lại dưới dạng raw snapshot đủ để downstream cleaning và repair, đồng thời giữ traceability của source.

### Cách triển khai

Tôi triển khai module lấy dữ liệu Crossref bằng cách gọi `https://api.crossref.org/works` với tham số `query.bibliographic`, `filter` và `rows` từ `Settings`. Dữ liệu trả về được lưu nguyên vào `data/raw/crossref_response.json`, sau đó parse thành danh sách `PaperRecord` và lưu ra `data/raw/crossref_records.json`.

Các rules chính:
- `paper_id` dùng DOI, không dùng vị trí thứ tự trong kết quả.
- Bỏ record thiếu `title` hoặc `summary`/abstract.
- Không làm sạch quá mức raw stage; chỉ chuẩn hóa whitespace và unwrap HTML tag nhẹ nhàng nếu cần cho các trường đã parse.
- Retry với exponential backoff cho status 429/500/502/503/504.
- `load_raw_records()` đọc lại JSON snapshot để hỗ trợ repair offline.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Crossref API JSON payload; `source_query`, `source_filter`, `max_results` từ `Settings` |
| Output                         | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` |
| Module phụ thuộc             | `src/core/config.py`                         |
| Module sử dụng output        | `src/ingestion/cleaning.py`, `src/pipelines/phase1.py` |
| Điều kiện lỗi cần xử lý | API timeout, retryable status codes, thiếu DOI/title/summary trong item |

### Cách xác minh

```bash
uv run python -c "from src.core.config import load_settings; from src.ingestion.crossref import load_raw_records; s=load_settings(); recs=load_raw_records(s.paths.raw_records_json); print('total', len(recs)); ids=[r.paper_id for r in recs]; print('duplicate_count', len(ids)-len(set(ids))); print('missing_title', sum(1 for r in recs if not r.title)); print('missing_summary', sum(1 for r in recs if not r.summary))"
```

- **Kết quả mong đợi:** `total 24`, `duplicate_count 0`, `missing_title 0`, `missing_summary 0`.
- **Kết quả thực tế:** Đã xác minh 24 bản ghi raw, không duplicate, không thiếu title/summary.
- **Artifact/log:** `data/raw/crossref_response.json`, `data/raw/crossref_records.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần quyết định cách đặt `paper_id` và mức độ làm sạch ở tầng raw.
- **Các phương án đã cân nhắc:**
  - Dùng DOI làm `paper_id` ổn định hoặc dùng chỉ số thứ tự của bản ghi.
  - Loại bỏ toàn bộ HTML/XML ngay ở tầng raw hoặc chỉ parse tối thiểu và để cleaning xử lý sau.
- **Phương án đã chọn:** Dùng DOI làm `paper_id` và chỉ chuẩn hóa nhẹ nhàng ở tầng raw.
- **Lý do:** DOI đảm bảo `paper_id` ổn định giữa các lần fetch và repair; giữ raw không quá sạch giúp bảo toàn source lineage và hỗ trợ sửa chữa khi cần.
- **Bằng chứng quyết định phù hợp:** `data/raw/crossref_records.json` có 24 bản ghi với DOI làm `paper_id`, không duplicate.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Starter code `src/ingestion/crossref.py` chỉ có `NotImplementedError` và hướng dẫn TODO, chưa có logic ingestion.
- **Lệnh hoặc bước tái hiện:** Mở `src/ingestion/crossref.py`, thấy 3 hàm chưa triển khai.
- **Nguyên nhân gốc:** Module ingest chưa được hoàn thiện trong code template.
- **Cách xử lý:** Implement `parse_crossref_payload()`, `fetch_source_records()` với retry/backoff và `load_raw_records()` để đọc snapshot.
- **Cách xác minh sau khi sửa:** Chạy kiểm tra raw records bằng `uv run python -c ...` và xác nhận 24 bản ghi, không duplicate, title/summary có.
- **Điều học được:** Với raw ingestion, việc giữ schema và traceability quan trọng hơn việc làm sạch sớm; raw stage phải đủ để repair mà không cần gọi lại API.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. Dữ liệu đi từ Crossref đến vector index như thế nào?
2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?
3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
5. Repair được xem là thành công dựa trên artifact và metric nào?

**Câu trả lời:**

Role 2 chỉ chịu trách nhiệm lấy dữ liệu từ Crossref và lưu raw snapshot trong `data/raw`. Role 3 sẽ dùng raw records này để clean, sinh `papers_clean.json`/`.csv`, sau đó tạo embedding và index. Vì vậy raw snapshot phải được giữ nguyên để repair mà không cần gọi lại API.

Quality checks xác thực dữ liệu đúng schema và không thiếu content. Freshness monitoring xác định dữ liệu còn mới so với ngưỡng thời gian. Cùng test set cho baseline/corrupted/repaired là cần thiết để so sánh công bằng. Repair thành công khi dữ liệu được phục hồi từ raw và các artifact/metrics downstream trở lại gần baseline hơn.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |      N/A |       [ ] |      [ ] | Chưa có artifact metrics để điền |
| `mean_token_f1`      |      N/A |       [ ] |      [ ] | Chưa chạy evaluation flow |
| `judge_accuracy`     |      N/A |       [ ] |      [ ] | Chưa có dữ liệu báo cáo |
| `mean_judge_score`   |      N/A |       [ ] |      [ ] | Chưa có data metrics |
| Quality checks         |      N/A |       [ ] |      [ ] | Chỉ hoàn thành phần raw ingestion |
| Freshness status       |      N/A |       [ ] |      [ ] | Freshness chưa được chạy ở phạm vi Role 2 |

### Kết luận từ số liệu

Hoàn thành hai chuỗi nguyên nhân–bằng chứng sau:

1. Data corruption → quality/freshness signal thay đổi → agent metric thay đổi.
2. Repair action → quality/freshness signal phục hồi → agent metric phục hồi hoặc chưa phục hồi.

Corruption nào ảnh hưởng rõ nhất và vì sao?

- Tạm thời chưa có số liệu cụ thể; nhưng trong pipeline này, corruption mất `summary` hoặc duplicate `paper_id` thường ảnh hưởng lớn nhất.

Kết quả nào khác với kỳ vọng ban đầu?

- Chưa chạy hết pipeline baseline/corrupted/repaired, nên chưa có số liệu so sánh.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Với Role 2, cần giữ raw data càng nguyên vẹn càng tốt và chỉ parse đủ để downstream clean.
2. Data quality cần được validated ở tầng raw bằng kiểm tra duplicate, title/summary và khả năng load lại snapshot.
3. Dữ liệu nguồn ảnh hưởng trực tiếp đến khả năng repair, nên `paper_id` phải ổn định và raw snapshot cần đủ metadata để không phải gọi lại API.

### Nếu có thêm thời gian

- Tôi sẽ bổ sung file metadata fetch và tài liệu bàn giao contract Role 2 rõ ràng hơn.
- Tôi sẽ chạy và lưu baseline/corrupted/repaired metrics để điền phần kết quả chi tiết.

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Đức Mạnh
**Ngày xác nhận:** 2026-08-06
