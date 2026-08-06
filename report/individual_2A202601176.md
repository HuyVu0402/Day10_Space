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
| Implement Crossref ingestion + lineage envelope (C5) | `src/ingestion/crossref.py` | `data/raw/crossref_response.json` (wrapped), `data/raw/crossref_records.json` | `PYTHONPATH=src ./.venv/Scripts/python.exe -c "import json; from core.config import load_settings; from ingestion.crossref import verify_raw_response; s=load_settings(); print(json.dumps(verify_raw_response(s.paths.raw_api_response), indent=2))"` |
| Verify raw snapshot consistency + checksum | `src/ingestion/crossref.py::verify_raw_response` | Envelope integrity: `checksum_ok=true`, `has_lineage_envelope=true`, 24 records, 0 dup | Output của lệnh trên: `checksum_ok: true`, `duplicate_paper_ids: 0` |
| Offline replay từ sealed payload | `src/ingestion/crossref.py::rebuild_records_from_snapshot` | 24 records replay trùng với saved `crossref_records.json` | `PYTHONPATH=src ./.venv/Scripts/python.exe -c "from dataclasses import asdict; from core.config import load_settings; from ingestion.crossref import rebuild_records_from_snapshot, load_raw_records; s=load_settings(); rebuilt=[asdict(r) for r in rebuild_records_from_snapshot(s.paths.raw_api_response)]; saved=[asdict(r) for r in load_raw_records(s.paths.raw_records_json)]; print('replay==saved:', rebuilt==saved, len(rebuilt))"` |
| Bảo vệ data/raw/ khỏi corruption | `src/ingestion/crossref.py::raw_snapshot_fingerprint` | File-level sha256 trước/sau corruption giống nhau | Chạy corruption flow và so sánh fingerprint trước/sau |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:

`data/raw/crossref_response.json` hiện là lineage envelope với schema version 1.0, gồm block `lineage` (request/response metadata + checksum) và `payload` (HTTP JSON nguyên bản). Envelope này migrate in-place từ snapshot cũ mà không refetch API; checksum sha256 xác minh payload không bị sửa, và replay offline từ sealed payload cho đúng 24 records trùng với `crossref_records.json`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Role 2 cần đảm bảo dữ liệu nguồn được lấy từ Crossref và lưu lại dưới dạng raw snapshot đủ để downstream cleaning và repair, đồng thời giữ traceability của source. Checkpoint 5 yêu cầu bổ sung lineage wrapper cho raw snapshot để R1/R3 xác minh source lineage và replay offline.

### Cách triển khai

Tôi triển khai module lấy dữ liệu Crossref bằng cách gọi `https://api.crossref.org/works` với tham số `query.bibliographic`, `filter` và `rows` từ `Settings`. 

**Lineage envelope (C5):** Thay vì lưu payload HTTP trần, `data/raw/crossref_response.json` được bọc trong một lineage envelope:

```json
{
  "schema_version": "1.0",
  "artifact": "crossref_raw_response",
  "lineage": {
    "owner_role": "R2 - Source Ingestion Owner",
    "source_api": "Crossref REST API",
    "fetched_at": "2026-08-06T08:31:40Z",
    "fetched_by": "src/ingestion/crossref.py::fetch_source_records",
    "request": { "method": "GET", "url": "...", "params": {...} },
    "response": { "http_status": 200, "items_returned": 24, ... },
    "parsing": { "records_parsed": 24, "paper_id_strategy": "lowercased Crossref DOI", ... },
    "integrity": { "checksum_algorithm": "sha256", "payload_sha256": "..." }
  },
  "payload": { <raw Crossref JSON> }
}
```

Payload HTTP gốc được giữ nguyên dưới key `payload`; block `lineage` ghi lại request/response metadata, số record parsed, và checksum toàn vẹn. Downstream dùng `load_raw_response(path)` để unwrap và replay offline. Snapshot hiện tại đã được migrate in-place mà không refetch API.

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
| Output                         | `data/raw/crossref_response.json` (lineage envelope), `data/raw/crossref_records.json` |
| Module phụ thuộc             | `src/core/config.py`                         |
| Module sử dụng output        | `src/ingestion/cleaning.py`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` |
| Điều kiện lỗi cần xử lý | API timeout, retryable status codes, thiếu DOI/title/summary trong item, payload checksum mismatch |

**Helper functions cho downstream (C5):**
- `load_raw_response(path) -> (payload, lineage)` — unwrap envelope, tương thích snapshot cũ
- `verify_raw_response(path) -> dict` — audit envelope + checksum + counts
- `assert_raw_snapshot_intact(settings) -> dict` — fail nếu checksum sai
- `raw_snapshot_fingerprint(settings) -> dict` — sha256 cả hai file raw, dùng trước/sau corruption
- `rebuild_records_from_snapshot(path) -> list[PaperRecord]` — replay offline, no API

### Cách xác minh

Audit raw snapshot và lineage envelope:

```bash
PYTHONPATH=src ./.venv/Scripts/python.exe -c "import json; from core.config import load_settings; from ingestion.crossref import verify_raw_response; s=load_settings(); print(json.dumps(verify_raw_response(s.paths.raw_api_response), indent=2))"
```

- **Kết quả mong đợi:** `has_lineage_envelope=true`, `checksum_ok=true`, `items_in_payload=24`, `records_parsed=24`, `duplicate_paper_ids=0`.
- **Kết quả thực tế:**

```text
has_lineage_envelope: true
schema_version: 1.0
fetched_at: 2026-08-06T08:31:40Z
source_api: Crossref REST API
http_status: 200
items_in_payload: 24
records_parsed: 24
records_declared: 24
duplicate_paper_ids: 0
checksum_expected: 14da9d8c8dedee06909679099bfda743fc03ec1bd3e08aaedb4d40976b6b2817
checksum_actual:   14da9d8c8dedee06909679099bfda743fc03ec1bd3e08aaedb4d40976b6b2817
checksum_ok: true
```

- **Artifact/log:** `data/raw/crossref_response.json`, `data/raw/crossref_records.json`.

Xác minh replay offline và raw snapshot không bị corruption sửa:

```text
--- offline replay from sealed payload (no API)
rebuilt == crossref_records.json: True (24 records)

--- corruption must not touch data/raw/
raw/ unchanged after corruption: True
```

## 4b. Vai trò của raw snapshot (C5)

`data/raw/` là điểm neo của toàn pipeline và là nguồn duy nhất để repair. Ba vai trò:

1. **Audit / source lineage.** Lineage envelope trả lời được: dữ liệu lấy từ đâu (`source_api`, `request.url`), bằng query/filter nào, lúc nào (`fetched_at`), HTTP status và số attempts của retry, bao nhiêu item trả về so với bao nhiêu record parse được. Trước C5, `crossref_response.json` chỉ là payload trần nên không trả lời được các câu hỏi này — đây chính là điểm R1 đã flag khi kiểm tra R2.
2. **Immutability.** Corruption chỉ được ghi vào `data/clean/papers_clean_corrupted.*` và `data/results/corruption_log.json`; `src/ingestion/corruption.py` không mở file nào trong `data/raw/`. `raw_snapshot_fingerprint()` cho R1/R3 chụp sha256 cả hai file raw trước/sau corruption flow để chứng minh raw không đổi. `payload_sha256` trong envelope là con dấu thứ hai, phát hiện cả trường hợp sửa tay.
3. **Offline repair.** Repair chạy lại cleaning từ `data/raw/crossref_records.json`, không gọi lại Crossref. Nếu file records bị mất, `rebuild_records_from_snapshot()` dựng lại đúng 24 record từ payload đã niêm phong — đã xác minh bằng so sánh với records hiện có, kết quả trùng khớp hoàn toàn.

Vì `paper_id` là DOI chuẩn hóa, replay nhiều lần cho cùng tập ID, nên raw → clean → index → test set → answers giữ được liên kết `paper_id` xuyên suốt.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần quyết định cách đặt `paper_id`, mức độ làm sạch ở tầng raw, và cách lưu trữ raw snapshot để R1/R3 xác minh source lineage và repair offline mà không gọi lại API.
- **Các phương án đã cân nhắc:**
  - Dùng DOI làm `paper_id` ổn định hoặc dùng chỉ số thứ tự của bản ghi.
  - Loại bỏ toàn bộ HTML/XML ngay ở tầng raw hoặc chỉ parse tối thiểu và để cleaning xử lý sau.
  - Lưu payload trần hoặc bọc trong lineage envelope với metadata + checksum.
- **Phương án đã chọn:** Dùng DOI làm `paper_id`, chỉ chuẩn hóa nhẹ nhàng ở tầng raw, và bọc payload trong lineage envelope.
- **Lý do:** 
  - DOI đảm bảo `paper_id` ổn định giữa các lần fetch và repair; giữ raw không quá sạch giúp bảo toàn source lineage và hỗ trợ sửa chữa khi cần.
  - Lineage envelope trả lời "dữ liệu từ đâu, bằng query nào, lúc nào, HTTP status" và cung cấp checksum để phát hiện sửa tay.
  - Payload HTTP gốc được giữ nguyên dưới key `payload` nên downstream vẫn replay được offline với `parse_crossref_payload()`.
- **Bằng chứng quyết định phù hợp:** 
  - `data/raw/crossref_records.json` có 24 bản ghi với DOI làm `paper_id`, không duplicate.
  - `verify_raw_response()` trả về `checksum_ok=true`, `has_lineage_envelope=true`.
  - Replay offline từ sealed payload trùng khớp 100% với saved records.
  - Corruption không làm thay đổi file-level sha256 của `data/raw/`.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Checkpoint 5 yêu cầu bổ sung lineage wrapper cho `data/raw/crossref_response.json` để giữ source lineage, nhưng file hiện có chỉ là payload trần.
- **Lệnh hoặc bước tái hiện:** Mở `data/raw/crossref_response.json`, thấy payload HTTP JSON nguyên bản không có block `lineage` hoặc `checksum`.
- **Nguyên nhân gốc:** Code C1/C2 chưa có lineage envelope; R1 đã flag khi kiểm tra R2 C1 là thiếu source lineage wrapper/date/category metadata.
- **Cách xử lý:** 
  1. Thêm constants `RAW_RESPONSE_SCHEMA_VERSION`, `INGESTION_VERSION`, `PAPER_ID_STRATEGY` vào đầu `crossref.py`.
  2. Implement `payload_checksum()`, `build_lineage_envelope()`, `write_raw_response()` để wrap payload với metadata request/response/parsing/integrity.
  3. Implement `load_raw_response()`, `unwrap_raw_response()`, `verify_raw_response()` để downstream đọc cả envelope lẫn payload trần (backward compatible).
  4. Implement `raw_snapshot_fingerprint()`, `assert_raw_snapshot_intact()`, `rebuild_records_from_snapshot()` để bảo vệ raw snapshot và replay offline.
  5. Migrate snapshot hiện có in-place bằng cách đọc payload, wrap vào envelope với `fetched_at` từ file mtime, rồi ghi lại — không refetch API.
  6. Update `fetch_source_records()` để gọi `write_raw_response()` thay vì `json.dump()` trực tiếp.
  7. Export helpers từ `src/ingestion/__init__.py` cho downstream.
- **Cách xác minh sau khi sửa:** 
  - `verify_raw_response()` trả về `has_lineage_envelope=true`, `checksum_ok=true`, `duplicate_paper_ids=0`.
  - Payload migrate trùng 100% với backup trước migration.
  - Replay offline từ sealed payload cho đúng 24 records khớp với `crossref_records.json`.
  - Corruption không làm thay đổi file-level sha256 của `data/raw/`.
- **Điều học được:** Lineage envelope không chỉ là metadata — nó là hợp đồng truy xuất nguồn. Với envelope, downstream biết dữ liệu từ đâu, lúc nào, bằng query nào; `payload_sha256` phát hiện sửa tay; và replay offline giúp repair mà không phụ thuộc API uptime. Migration in-place bảo vệ được cả snapshot cũ lẫn baseline đã chạy.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. Dữ liệu đi từ Crossref đến vector index như thế nào?
2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?
3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?
4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?
5. Repair được xem là thành công dựa trên artifact và metric nào?

**Câu trả lời:**

1. Crossref API → `data/raw/crossref_response.json` (lineage envelope) → `data/raw/crossref_records.json` → cleaning → `data/clean/papers_clean.json` có `text_for_embedding` → R4 embed mỗi paper thành một vector/document duy nhất → ChromaDB index với metadata `paper_id`. Document-level chunking nghĩa là mỗi paper = 1 chunk; không tách summary thành nhiều đoạn nhỏ.

2. Evaluation set (`data/eval/test_set.json`) gồm 10 câu hỏi factual, mỗi câu có `ground_truth_doc_ids` là list các `paper_id` chứa đáp án. Khi agent trả lời, `retrieved_doc_ids` được so với ground truth: nếu trùng ít nhất 1 ID thì retrieval hit. Token F1 và LLM judge đo chất lượng answer.

3. Quality checks (`src/observability/quality.py`) xác thực schema, completeness (non-null/non-empty), uniqueness (`paper_id`), validity (summary min length, date format) và trả về `passed` PASS/FAIL. Freshness monitoring ghi riêng ra `data/quality/*freshness_report.json` với `latest_published`, `oldest_published`, `stale_rows` và `is_fresh` theo threshold 180 ngày; nó là signal riêng, `freshness_evaluated_separately=true` nên không làm fail quality check.

4. Cùng test set → so sánh công bằng; khác biệt metric phản ánh thay đổi dữ liệu thay vì thay đổi câu hỏi. Nếu corrupted/repaired dùng test set khác thì retrieval hit rate không đo được tác động thật của corruption.

5. Repair thành công khi: (a) rebuild từ `data/raw/crossref_records.json`, không refetch API; (b) `data/clean/papers_clean_repaired.*` có 24 records như baseline; (c) quality PASS, duplicate=0, blank summary=0; (d) metrics (token F1, judge accuracy, judge score) phục hồi về baseline; (e) freshness stale rows trở lại baseline stale rows (2/24), không còn thêm row stale do corruption.

## 8. Phân tích kết quả

### Metrics chính

Số liệu đọc từ `data/results/*_metrics.json`, `data/quality/*_quality.json` và `data/quality/*freshness_report.json`.

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |     1.00 |      1.00 |     1.00 | Không giảm vì document bị corrupt vẫn còn trong index; retrieval một mình không phát hiện được data quality |
| `mean_token_f1`      |     1.00 |      0.70 |     1.00 | Giảm rõ khi summary bị xóa; phục hồi đúng baseline sau repair từ raw |
| `judge_accuracy`     |     1.00 |      0.70 |     1.00 | Cùng hướng với Token F1 |
| `mean_judge_score`   |     5.00 |      3.80 |     5.00 | Answer quality là signal nhạy nhất với corruption |
| Quality checks         |     PASS |      FAIL |     PASS | Corrupted fail 3 check: `paper_id_unique` (2 dup), `summary_non_empty` (3), `summary_min_length` (3) |
| Freshness status       | `is_fresh=false`, stale 2/24 | `is_fresh=false`, stale 4/26 | `is_fresh=false`, stale 2/24 | Baseline đã có 2 record vượt 180 ngày; repair trả về đúng mức baseline, không "sửa" freshness gốc |

### Kết luận từ số liệu

Hoàn thành hai chuỗi nguyên nhân–bằng chứng sau:

1. **Data corruption → quality/freshness signal thay đổi → agent metric thay đổi.** Corruption xóa 3 summary và thêm 2 duplicate row (24 → 26 rows). Quality chuyển PASS → FAIL tại `summary_non_empty`, `summary_min_length` và `paper_id_unique`; stale rows 2 → 4. Vì `text_for_embedding` mất phần `Summary`, agent thiếu ngữ cảnh để trả lời: Token F1 1.00 → 0.70, judge accuracy 1.00 → 0.70, mean judge score 5.00 → 3.80.
2. **Repair action → quality/freshness signal phục hồi → agent metric phục hồi.** Repair chạy lại cleaning từ `data/raw/crossref_records.json` (không refetch API), trả về 24 rows, duplicate 0, blank summary 0, quality PASS, và Token F1/judge accuracy/judge score trở lại đúng baseline. Đây là bằng chứng trực tiếp cho giá trị của raw snapshot: không có nó thì summary đã bị xóa là mất vĩnh viễn.

Corruption nào ảnh hưởng rõ nhất và vì sao?

- Xóa `summary` ảnh hưởng mạnh nhất. `text_for_embedding` được ghép từ `Title/Authors/Categories/Summary`, nên mất summary làm mất gần hết nội dung ngữ nghĩa; document vẫn được retrieve (title còn) nhưng context không còn đáp án, khiến answer metric giảm trong khi hit rate vẫn 1.00. Duplicate `paper_id` chủ yếu phá uniqueness check hơn là phá answer.

Kết quả nào khác với kỳ vọng ban đầu?

- Tôi kỳ vọng `retrieval_hit_rate` sẽ giảm khi dữ liệu bị corrupt, nhưng nó giữ 1.00 ở cả ba trạng thái. Lý do: corruption làm suy giảm nội dung chứ không xóa document khỏi index, và `paper_id` vẫn nguyên nên hit theo document ID vẫn tính là đúng. Điều này cho thấy retrieval hit rate không đủ để monitor data quality, phải kết hợp answer-level metric và quality checks.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Raw snapshot là hợp đồng giữa R2 và toàn pipeline.** Với Role 2, raw data phải đủ để R3 repair offline mà không gọi lại API. Điều này nghĩa là không chỉ parse đủ trường, mà còn phải bảo vệ tính toàn vẹn và traceability. Lineage envelope trả lời "dữ liệu này từ đâu, bằng query nào, lúc nào" — câu hỏi mà payload trần không trả lời được.
2. **Data quality cần được validated ở ngay tầng raw.** Kiểm tra duplicate `paper_id`, title/summary rỗng, và khả năng load lại snapshot trước khi bàn giao cho downstream giúp phát hiện sớm lỗi fetch hoặc parse. `verify_raw_response()` là checkpoint này; nếu `checksum_ok=false` thì raw snapshot đã bị sửa và phải refetch có kiểm soát.
3. **`paper_id` phải ổn định xuyên suốt luồng.** Dùng DOI thay vì chỉ số thứ tự giúp repair replay ra cùng ID, giữ được liên kết `paper_id` từ raw → clean → index → test set → answers. Nếu `paper_id` thay đổi giữa các lần chạy, evaluation hit rate mất ý nghĩa.

### Nếu có thêm thời gian

- **Bổ sung HTTP response headers vào lineage.** `Content-Type`, `X-RateLimit-*`, `Date` từ Crossref có thể hữu ích khi debug retry hoặc so sánh snapshot giữa các lần fetch.
- **Tạo audit trail cho mọi lần fetch.** Hiện tại mỗi fetch ghi đè snapshot cũ; nếu giữ timestamped copies (`crossref_response_2026-08-06T08-31-40Z.json`) thì có thể so sánh query/filter thay đổi theo thời gian.
- **Schema migration cho envelope.** Khi `schema_version` tăng (thêm trường `lineage` mới hoặc đổi tên field), cần helper để upgrade snapshot cũ lên version mới.

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
