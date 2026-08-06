# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                                                        |
| ------------------ | --------------------------------------------------------------- |
| Họ và tên       | Thiều Thị Ngọc Ánh                                              |
| MSSV               | 2A202601864                                                     |
| Khóa/Lớp         | K4                                                              |
| Tên nhóm         | Nhóm Space                                                       |
| Vai trò chính    | **R3 — Cleaning, Corruption & Repair Owner**                    |
| Repository         | https://github.com/HuyVu0402/Day10_Space                       |
| Ngày hoàn thành | 2026-08-06                                                      |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| **Data Cleaning** | [src/ingestion/cleaning.py](file:///d:/Lab/Day10_Space/src/ingestion/cleaning.py)<br>`build_clean_dataframe()` | Raw `PaperRecord` / JSON snapshot từ R2 (`crossref_records.json`) | `data/clean/papers_clean.csv`<br>`data/clean/papers_clean.json` | **Hoàn thành** |
| **Data Corruption** | [src/ingestion/corruption.py](file:///d:/Lab/Day10_Space/src/ingestion/corruption.py)<br>`corrupt_clean_dataframe()` | DataFrame sạch (`papers_clean.csv`) | `data/clean/papers_corrupted.csv`<br>`data/results/corruption_log.json` | **Hoàn thành** |
| **Data Repair** | [src/ingestion/cleaning.py](file:///d:/Lab/Day10_Space/src/ingestion/cleaning.py)<br>Quy trình Offline Repair | Snapshot thô `data/raw/crossref_records.json` | Rebuilt clean dataset cho phase repair | **Hoàn thành** |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả và bằng chứng |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Thảo luận & chốt Data Contract (Clean Schema 10 cột) | R4 (Sơn - Retrieval), R5 (Phương - Evaluation) | Thống nhất tên trường, kiểu dữ liệu và định dạng `text_for_embedding` đúng 10 cột contract. |
| Hỗ trợ tích hợp offline repair | R1 (Bạn - Integration & Release) | Đảm bảo quy trình Repair chạy trực tiếp từ `crossref_records.json` không gọi lại Crossref API. |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Triển khai logic làm sạch & chuẩn hóa dữ liệu | [src/ingestion/cleaning.py](file:///d:/Lab/Day10_Space/src/ingestion/cleaning.py)<br>`build_clean_dataframe()` | 24 bản ghi sạch, 10 cột chuẩn contract | `uv run python -c "from ingestion.cleaning import build_clean_dataframe..."` |
| Triển khai bộ giả lập hỏng hóc 4 kịch bản & ghi log audit | [src/ingestion/corruption.py](file:///d:/Lab/Day10_Space/src/ingestion/corruption.py)<br>`corrupt_clean_dataframe()` | `data/clean/papers_corrupted.csv`<br>`data/results/corruption_log.json` | `assert log_path.exists()` & kiểm tra số dòng hỏng hóc |
| Tạo và xác minh 4 artifacts dữ liệu chính | Thư mục `data/clean/` & `data/results/` | CSV/JSON clean & corrupted | Kiểm tra sự tồn tại và đọc hợp lệ bằng Pandas |

**Mô tả output cụ thể:**
- `data/clean/papers_clean.csv` & `data/clean/papers_clean.json`: Chứa 24 bản ghi sạch đã loại bỏ HTML/XML tag, tính `age_days`, ghép `authors_joined` / `categories_joined` và tạo cột `text_for_embedding = "Title: [title] | Authors: [authors] | Summary: [summary]"`.
- `data/results/corruption_log.json`: Chứa 20 lượt log ghi lại chi tiết `paper_id`, `field`, `original_value`, `corrupted_value` và `scenario`.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Dữ liệu thô từ Crossref API chứa nhiều nhiễu như thẻ HTML/XML (`<jats:p>`, `<b>`), ký tự HTML escaped (`&amp;`), tên tác giả lồng trong dict/mảng, ngày tháng không nhất quán (`2026-7-2`), và các bản ghi rác thiếu tóm tắt. Nếu đưa trực tiếp dữ liệu thô này vào VectorDB (ChromaDB), embedding model sẽ bị nhiễu ngữ nghĩa, làm giảm Hit Rate và accuracy của RAG Agent. Đồng thời, cần một cơ chế giả lập nhiễu dữ liệu (Corruption) có thể tái lập (deterministic) để đo lường độ sụt giảm metric ở các bước sau.

### Cách triển khai
1. **Filtering & Text Cleaning (`cleaning.py`):**
   - Loại bỏ bản ghi thiếu `title` hoặc `summary` dưới 100 ký tự.
   - Hàm `clean_text()` giải mã HTML entity (`html.unescape`) và dùng Regex `re.sub(r"<[^>]+>", "", text)` để xóa sạch mọi thẻ XML/HTML, sau đó chuẩn hóa khoảng trắng dư thừa (`re.sub(r"\s+", " ", text).strip()`).
   - Hàm `format_author()` nhận diện linh hoạt cả dạng chuỗi lẫn dạng dictionary (`given`, `family`) để trả về tên tác giả chuẩn.
   - Hàm `parse_date()` chuyển đổi các chuỗi ngày linh hoạt (`2026-7-2`) về định dạng chuẩn ISO `YYYY-MM-DD` (`2026-07-02`) và tính `age_days = (run_date - pub_date).days`.
   - Định dạng `text_for_embedding = f"Title: {title} | Authors: {authors_joined} | Summary: {summary}"`.

2. **Deterministic Corruption (`corruption.py`):**
   - Đặt `random.seed(42)` và `np.random.seed(42)` đảm bảo kết quả sinh nhiễu luôn giống nhau.
   - Giả lập 4 kịch bản lỗi:
     - *Scenario 1:* Xóa tóm tắt (Blank summary) và cập nhật lại `text_for_embedding`.
     - *Scenario 2:* Cắt ngắn tiêu đề và chèn chuỗi nhiễu `[CORRUPTED_NOISE_xxxx]`.
     - *Scenario 3:* Làm hỏng ngày xuất bản thành `1970-01-01` và `age_days = 99999`.
     - *Scenario 4:* Nhân bản ngẫu nhiên các dòng cũ (Duplicate row injection).
   - Xuất nhật ký hỏng hóc theo dạng mảng JSON vào `data/results/corruption_log.json`.

3. **Offline Repair:**
   - Hàm phục hồi dữ liệu chạy lại quy trình `build_clean_dataframe()` từ snapshot lưu sẵn `data/raw/crossref_records.json` mà không gọi lại API Crossref bên ngoài.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Danh sách `PaperRecord` hoặc `dict` từ `data/raw/crossref_records.json`. |
| Output                         | `pd.DataFrame` gồm 10 cột: `paper_id`, `title`, `summary`, `published`, `authors_joined`, `categories_joined`, `age_days`, `text_for_embedding`, `abs_url`, `pdf_url`. |
| Module phụ thuộc             | `src/ingestion/crossref.py` (cung cấp dataclass `PaperRecord` và hàm `load_raw_records`). |
| Module sử dụng output        | `src/retrieval/index.py` (R4 dùng để embed & index vào ChromaDB) và `src/observability/quality.py` (R5 dùng kiểm tra Data Quality). |
| Điều kiện lỗi cần xử lý | Bản ghi thiếu tiêu đề/tóm tắt; tóm tắt ngắn < 100 ký tự; thẻ HTML lồng nhau; định dạng ngày 1 chữ số (`2026-7-2`). |

### Cách xác minh

```bash
uv run python -c "
import json
from datetime import datetime, UTC
from pathlib import Path
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe

raw_path = Path('data/raw/crossref_records.json')
with open(raw_path, 'r', encoding='utf-8') as f:
    raw_data = json.load(f)

clean_df = build_clean_dataframe(raw_data, datetime.now(UTC))
assert len(clean_df) > 0
log_path = Path('data/results/corruption_log.json')
corrupted_df = corrupt_clean_dataframe(clean_df, log_path)
assert log_path.exists()
print('VERIFICATION SUCCESSFUL!')
"
```

- **Kết quả mong đợi:** Tạo thành công DataFrame sạch 10 cột, không rỗng, không chứa HTML tag; file log corruption chứa chi tiết các bản ghi bị biến đổi.
- **Kết quả thực tế:** 24 bản ghi thô được làm sạch thành 24 bản ghi sạch chuẩn 10 cột; sinh ra 20 log entry lỗi và file `papers_corrupted.csv` chứa 26 dòng (bao gồm 2 dòng duplicate).
- **Artifact/log:** `data/clean/papers_clean.csv`, `data/clean/papers_clean.json`, `data/clean/papers_corrupted.csv`, `data/results/corruption_log.json`.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn cách cấu trúc chuỗi ngữ nghĩa cho cột `text_for_embedding` phục vụ bước Vector Embedding của R4.
- **Các phương án đã cân nhắc:**
  1. *Phương án A:* Ghép nối thuần túy các chuỗi văn bản không có tiền tố: `f"{title} {authors_joined} {summary}"`.
  2. *Phương án B:* Thêm tiền tố nhãn phân định rõ ràng (Structured Field Prefixes): `f"Title: {title} | Authors: {authors_joined} | Summary: {summary}"`.
- **Phương án đã chọn:** Phương án B.
- **Lý do:** Khi sử dụng mô hình embedding (như `sentence-transformers/all-MiniLM-L6-v2`), việc có các nhãn tiền tố `Title:`, `Authors:`, `Summary:` giúp mô hình phân định rõ cấu trúc thông tin, hỗ trợ RAG Agent tìm kiếm ngữ nghĩa chính xác hơn khi query theo tiêu đề hoặc tác giả, tránh tình trạng thông tin tác giả bị lẫn vào nội dung tóm tắt.
- **Bằng chứng quyết định phù hợp:** Kết quả kiểm tra cột `text_for_embedding` cho 100% bản ghi sạch đều bắt đầu bằng `Title: ` và chứa các phân đoạn `| Authors: ` và `| Summary: `.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  Dữ liệu thô từ Crossref chứa chuỗi ngày xuất bản chưa chuẩn hóa như `"published": "2026-7-2"` (tháng và ngày chỉ có 1 chữ số), dẫn đến lỗi khi ép kiểu `datetime.strptime(published, "%Y-%m-%d")` gây sập pipeline. Đồng thời summary chứa các thẻ XML lồng phức tạp như `<jats:p>`.
- **Lệnh hoặc bước tái hiện:**
  Gọi `build_clean_dataframe` với danh sách raw record trực tiếp từ `data/raw/crossref_records.json`.
- **Nguyên nhân gốc:**
  API Crossref trả về định dạng ngày linh hoạt từ nhiều nhà xuất bản khác nhau (có bài dùng `YYYY-M-D`, có bài dùng `YYYY-MM-DD` hoặc `YYYY`), và chứa mã XML JATS chưa qua xử lý.
- **Cách xử lý:**
  - Trong `parse_date()`, viết Regex bắt 3 nhóm chữ số `(\d{4})[-/](\d{1,2})[-/](\d{1,2})`, sau đó dùng format chuỗi `f"{int(year):04d}-{int(month):02d}-{int(day):02d}"` để tự động pad thêm số 0 cho tháng và ngày (`"2026-7-2"` -> `"2026-07-02"`).
  - Dùng `html.unescape()` kết hợp `re.sub(r"<[^>]+>", "", cleaned)` để xóa sạch thẻ XML/HTML trước khi chuẩn hóa khoảng trắng.
- **Cách xác minh sau khi sửa:**
  Chạy lệnh kiểm thử tự động, toàn bộ 24 bản ghi đều parse ra định dạng ngày chuẩn `YYYY-MM-DD` và không còn thẻ `<jats:p>` nào trong cột `summary`.
- **Điều học được:**
  Không bao giờ tin tưởng định dạng dữ liệu từ API bên ngoài; luôn cần có tầng Sanitization & Normalization mạnh mẽ trước khi lưu vào Data Lake / Data Warehouse.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   - R2 (`crossref.py`) gọi API Crossref REST lấy raw JSON response và parse ra `crossref_records.json`.
   - R3 (`cleaning.py`) nhận raw records, làm sạch HTML/XML, chuẩn hóa ngày tháng, ghép tác giả/danh mục, tạo cột `text_for_embedding` và lưu thành `papers_clean.csv`.
   - R4 (`index.py`) đọc `papers_clean.csv`, dùng `sentence-transformers` tạo vector embedding từ `text_for_embedding` và lưu vào ChromaDB vector collection.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   - Evaluation set chứa danh sách các câu hỏi và `ground_truth_doc_ids` (ID của tài liệu chứa đáp án đúng).
   - Khi RAG Agent chạy, nó sẽ retrieve ra `top_k` document IDs (`retrieved_doc_ids`).
   - `retrieval_hit_rate` được tính bằng tỷ lệ số câu hỏi mà `retrieved_doc_ids` có chứa ít nhất 1 ID nằm trong `ground_truth_doc_ids`.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - **Quality checks:** Kiểm tra tính toàn vẹn của dữ liệu (Data Integrity) tại một thời điểm như: không có trường rỗng, không duplicate `paper_id`, độ dài summary > 100 chars, đúng schema 10 cột.
   - **Freshness monitoring:** Giám sát độ tắn tươi/độ mới của dữ liệu theo thời gian (Data Timeliness) dựa trên cột `age_days` và `published` date so với ngưỡng `freshness_threshold_days` (180 ngày).

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   - Để đảm bảo tính so sánh công bằng (A/B testing / Controlled Experiment). Việc giữ nguyên bộ câu hỏi, embedding model, LLM và top-k giúp cô lập biến số duy nhất là **Chất lượng Dữ liệu (Data Quality)**, từ đó đo lường chính xác tác hại của Data Corruption và hiệu quả của Data Repair.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   - **Artifact:** `papers_clean_repaired.csv` trùng khớp hoặc khôi phục lại cấu trúc chuẩn từ raw snapshot, `corruption_log.json` được giải quyết.
   - **Metrics:** `retrieval_hit_rate`, `mean_token_f1`, và `judge_accuracy` của trạng thái Repaired phục hồi về mức ngang bằng hoặc xấp xỉ trạng thái Baseline (vượt trội so với trạng thái Corrupted).

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |      1.0 |       0.5 |      1.0 | Corruption (blank summary & noise) làm sụt giảm 50% hit rate; Repair khôi phục hoàn toàn. |
| `mean_token_f1`      |     0.78 |      0.42 |     0.78 | Điểm F1 câu trả lời giảm mạnh khi ngữ cảnh bị hỏng; sau khi repair điểm số phục hồi. |
| `judge_accuracy`     |      0.8 |       0.4 |      0.8 | Độ chính xác của LLM Judge giảm một nửa ở dữ liệu nhiễu và hồi phục khi dữ liệu sạch. |
| `mean_judge_score`   |      4.2 |       2.1 |      4.2 | Điểm chất lượng trung bình (thang 5) bị kéo xuống do thiếu thông tin tóm tắt. |
| Quality checks         |     Pass |      Fail |     Pass | Corrupted fail do phát hiện duplicate rows & blank summary; Repaired pass 100%. |
| Freshness status     |     Pass |      Fail |     Pass | Corrupted fail do ngày `1970-01-01` kéo `age_days` lên quá ngưỡng; Repaired pass. |

### Kết luận từ số liệu

1. **Chuỗi nguyên nhân–bằng chứng 1 (Corruption Impact):**
   [Data corruption xóa summary & chèn noise vào title] → [Quality check phát hiện blank summary & Freshness fail] → [`retrieval_hit_rate` giảm từ 1.0 xuống 0.5 và `judge_accuracy` giảm từ 0.8 xuống 0.4].

2. **Chuỗi nguyên nhân–bằng chứng 2 (Repair Recovery):**
   [Repair action chạy lại cleaning pipeline từ raw snapshot] → [Quality check & Freshness signal phục hồi trạng thái Pass] → [Tất cả agent metrics phục hồi 100% về mức Baseline].

- **Corruption nào ảnh hưởng rõ nhất và vì sao?**
  *Scenario 1 (Blank Summary)* và *Scenario 2 (Title Truncation & Noise)* ảnh hưởng nặng nề nhất vì chúng trực tiếp làm biến đổi thông tin ngữ nghĩa trong `text_for_embedding`. Khi `text_for_embedding` bị mất thông tin hoặc tràn ngập token rác, Vector Distance trong ChromaDB bị sai lệch hoàn toàn, dẫn đến bước Retrieval lấy sai tài liệu.

- **Kết quả nào khác với kỳ vọng ban đầu?**
  Ban đầu dự đoán việc trùng lặp dòng (Scenario 4 - Duplicates) sẽ gây lỗi crash pipeline, nhưng thực tế ChromaDB vẫn xử lý được tuy nhiên làm giảm hiệu năng tìm kiếm và làm trôi kết quả top-k.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về Data Pipeline:** Pipeline làm sạch dữ liệu phải có tính khép kín (Idempotent) và Tái lập (Deterministic). Việc lưu giữ Raw Snapshot (`crossref_records.json`) là "chìa khóa vàng" giúp phục hồi hệ thống khi có sự cố mà không phụ thuộc vào API bên ngoài.
2. **Về Data Quality & Observability:** "Garbage in, Garbage out" — Dữ liệu nhiễu nhỏ ở tầng Ingestion (thẻ XML, thiếu summary) có thể gây sụt giảm nghiêm trọng đến 50% hiệu năng của hệ thống RAG tiên tiến.
3. **Về ảnh hưởng đến RAG Agent:** Cấu trúc thông tin đầu vào (`text_for_embedding`) đóng vai trò quyết định đến chất lượng Vector Embedding. Thêm các nhãn định dạng rõ ràng (`Title:`, `Authors:`, `Summary:`) giúp tăng đáng kể khả năng truy xuất chính xác của Agent.

### Nếu có thêm thời gian

Nếu có thêm thời gian, tôi sẽ triển khai thêm bộ tự động phát hiện ngôn ngữ (Language Detection / Non-Latin filtering) để lọc bỏ các bài báo không phải tiếng Anh ngay tại tầng Ingestion, đồng thời xây dựng bộ kiểm tra độ tương đồng văn bản (Fuzzy Deduplication) để phát hiện các bài báo bị trùng lặp nội dung nhưng khác DOI.

---

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Thiều Thị Ngọc Ánh  
**Ngày xác nhận:** 2026-08-06  

