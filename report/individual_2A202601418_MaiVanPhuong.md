# Member Role Report — Day 10: Data Pipeline & Data Observability

> Mỗi thành viên trong nhóm tự hoàn thành mẫu này để báo cáo đúng vai trò, phần việc và mức hiểu của mình. Không sao chép nguyên báo cáo chung hoặc báo cáo của thành viên khác. Thay nội dung trong dấu `[ ]` và xóa các dòng hướng dẫn không cần thiết trước khi nộp.

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Mai Văn Phương             |
| MSSV               | 2A202601418                     |
| Khóa/Lớp         | K4              |
| Tên nhóm         | Space     |
| Vai trò chính    | R5 — Evaluation, Observability & Reporting Owner                 |
| Repository         | C:\vin_ai\LAB\Day10_Space |
| Ngày hoàn thành | 2026-08-06               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái                                 |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Frozen evaluation set | `src/evaluation/testset.py` — `build_test_set()` | Clean dataframe | `data/eval/test_set.json` (10 câu hỏi factual) | Hoàn thành |
| Evaluation & scoring | `src/evaluation/metrics.py` — `evaluate_pipeline()` | Index, frozen test set | `data/results/{baseline,corrupted,repaired}_metrics.json` và `*_answers.json` | Hoàn thành |
| Data quality checks | `src/observability/quality.py` — `run_data_quality_checks()` | Dataframe ở từng trạng thái | Quality JSON (duplicate IDs, blank/short summaries, stale rows) | Hoàn thành |
| Freshness monitoring | `build_freshness_report()` | Dataframe ở từng trạng thái | Freshness JSON (stale >180 ngày) | Hoàn thành |
| Reporting | `src/observability/reporting.py` | Metrics/quality/freshness artifacts | `data/reports/phase1_report.md`, `data/reports/corruption_report.md` | Hoàn thành |

Tôi nhận clean data từ R3 và retrieval/agent output từ R4. Các artifact metrics, quality và report được R1 dùng để tích hợp baseline và corruption/repair flow.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                         | Thành viên/module được hỗ trợ | Kết quả                    |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Xác nhận `ground_truth_doc_ids` tồn tại trong clean baseline | R3 (data owner) | Tránh silent miss khi tính retrieval hit rate |
| Đối chiếu schema metrics với R4 (retrieval/agent output) | R4 | Đảm bảo `retrieved_doc_ids` khớp schema evaluator |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao       | Cách xác minh         |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Đóng băng test set 10 câu hỏi factual | `data/eval/test_set.json` | 10 samples với `id`, `question_type`, `question`, `ground_truth`, `ground_truth_doc_ids` | `uv run python script/run_phase1.py` — file được load lại, không sinh lại |
| Chạy evaluation baseline/corrupted/repaired | `data/results/*_metrics.json`, `data/results/*_answers.json` | Retrieval hit rate, Token F1, judge accuracy, mean judge score | `uv run python script/run_corruption_flow.py` |
| Sinh quality JSON 3 trạng thái | `src/observability/quality.py` | Total rows, duplicate IDs, blank/short summaries | So sánh JSON giữa baseline/corrupted/repaired |
| Sinh freshness JSON 3 trạng thái | `build_freshness_report()` | Stale rows (>180 ngày) | So sánh JSON giữa baseline/corrupted/repaired |
| Tổng hợp phase 1 và corruption reports | `data/reports/phase1_report.md`, `data/reports/corruption_report.md` | Báo cáo markdown cho nhóm | Đọc trực tiếp các file report |

Một output cụ thể mà phần việc của tôi tạo ra:

- `data/reports/phase1_report.md` và `data/reports/corruption_report.md` — báo cáo markdown tổng hợp metrics, quality và freshness cho cả ba trạng thái (baseline, corrupted, repaired), là đầu vào để R1 đối chiếu với pipeline tổng.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Phần của tôi giải quyết bài toán đo lường chất lượng retrieval/answer và quan sát chất lượng dữ liệu của pipeline RAG: cần một test set cố định để so sánh công bằng giữa baseline, corrupted và repaired; cần metric có thể tái lập để chứng minh repair có hiệu lực; và cần quality/freshness signals để tách bạch lỗi do dữ liệu với lỗi do model.

### Cách triển khai

- **Frozen test set:** `build_test_set()` sinh 10 câu hỏi factual từ clean dataframe; nếu `data/eval/test_set.json` đã tồn tại, pipeline chỉ đọc lại — đảm bảo baseline, corrupted và repaired dùng cùng 10 câu hỏi và cùng ground truth.
- **Retrieval hit:** đếm khi `retrieved_doc_ids` chứa ít nhất một `ground_truth_doc_ids` (set intersection).
- **Answer quality:** Token F1 (token-level overlap giữa prediction và ground truth), judge accuracy (LLM judge hoặc heuristic fallback), mean judge score (0–5).
- **Quality checks:** đếm duplicate IDs, blank/short summaries, stale rows (>180 ngày) trên từng trạng thái; đánh FAIL nếu bất kỳ check nào vi phạm.
- **Freshness monitoring:** cờ stale cho rows có `published_date` cũ hơn 180 ngày so với thời điểm chạy.
- **Cấu hình so sánh:** document-level chunking, MiniLM embedding, `top_k=4` — giữ cố định giữa ba trạng thái.

### Input, output và contract

| Thành phần                   | Mô tả                                     |
| ------------------------------ | ------------------------------------------- |
| Input                          | Clean/corrupted/repaired dataframe (từ R3), retrieval + agent output (từ R4) |
| Output                         | `data/eval/test_set.json`, `data/results/*_metrics.json`, `data/results/*_answers.json`, `data/results/*_quality.json`, `data/results/*_freshness.json`, `data/reports/phase1_report.md`, `data/reports/corruption_report.md` |
| Module phụ thuộc             | R3 (clean data), R4 (retrieval/agent output) |
| Module sử dụng output        | R1 (tích hợp pipeline tổng), group report |
| Điều kiện lỗi cần xử lý | LLM judge không khả dụng → heuristic fallback; test set đã tồn tại → không sinh lại; ground truth ID không có trong index → tính miss thay vì crash |

### Cách xác minh

```powershell
cd C:\vin_ai\LAB\Day10_Space
uv sync
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** `data/reports/phase1_report.md` và `data/reports/corruption_report.md` được sinh ra với metrics/quality/freshness cho ba trạng thái.
- **Kết quả thực tế:** Cả hai report được sinh đúng schema; retrieval hit rate 1.00 cả ba trạng thái; Token F1/Judge accuracy giảm còn 0.70 ở corrupted và phục hồi về 1.00 ở repaired; quality baseline/repaired vẫn FAIL do 2 stale rows có sẵn trong clean snapshot.
- **Artifact/log:** `data/results/baseline_metrics.json`, `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`, `data/reports/phase1_report.md`, `data/reports/corruption_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần đảm bảo ba trạng thái (baseline, corrupted, repaired) dùng cùng bộ câu hỏi và cùng ground truth để so sánh retrieval/answer quality là công bằng.
- **Các phương án đã cân nhắc:**
  1. Sinh test set mới mỗi lần chạy từ clean dataframe (đơn giản nhưng không ổn định).
  2. Sinh test set một lần, lưu `data/eval/test_set.json`, các lần chạy sau chỉ đọc lại (ổn định, tái lập).
- **Phương án đã chọn:** Phương án 2 — đóng băng test set.
- **Lý do:** Trade-off ưu tiên correctness và reproducibility: nếu test set thay đổi giữa các lần chạy, mọi so sánh metric đều có nhiễu và không thể kết luận repair có hiệu lực. Frozen set đảm bảo mọi thay đổi metric đến từ dữ liệu, không từ test set.
- **Bằng chứng quyết định phù hợp:** `data/eval/test_set.json` được load lại giữa ba trạng thái; retrieval hit rate giữ nguyên 1.00 giữa baseline/repaired chứng minh test set ổn định; chênh lệch Token F1 (1.00 → 0.70 → 1.00) phản ánh đúng tác động của corruption/repair lên câu trả lời.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Retrieval hit rate giữ nguyên 1.00 ở cả corrupted, dẫn đến nghi ngờ "corruption không ảnh hưởng retrieval" và có thể bị đọc nhầm là repair không cần thiết.
- **Lệnh hoặc bước tái hiện:** So sánh `data/results/baseline_metrics.json` và `data/results/corrupted_metrics.json` cho trường `retrieval_hit_rate`.
- **Nguyên nhân gốc:** Các paper bị corruption vẫn có mặt trong index (chỉ summary/metadata bị hỏng), nên retrieval vẫn trả về đúng document; vấn đề nằm ở answer quality (Token F1, judge accuracy), không phải retrieval.
- **Cách xử lý:** Bổ sung nhận định trong report: retrieval hit rate một mình không đủ để đánh giá chất lượng RAG; phải kết hợp answer-level metrics (Token F1, judge accuracy, mean judge score) và quality signals (duplicate IDs, blank summaries) để phát hiện tác động thực sự của corruption.
- **Cách xác minh sau khi sửa:** Đối chiếu Token F1/Judge accuracy ở ba trạng thái (1.00 → 0.70 → 1.00) cho thấy corruption ảnh hưởng rõ answer quality; kết hợp quality JSON (duplicate IDs tăng từ 0 → 2, blank summaries tăng từ 0 → 3) xác nhận nguyên nhân dữ liệu.
- **Điều học được:** Retrieval hit rate chỉ đo "tìm được đúng tài liệu", không đo "trả lời đúng". Pipeline observability cần song song hai lớp: retrieval quality (hit rate) và answer quality (Token F1, judge), cùng với data quality signals.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?** Crossref API được gọi để lấy metadata các paper (R2) → clean dataframe được R3 xử lý (loại trùng ID, chuẩn hóa summary, chuẩn hóa metadata) → chunking theo document-level → embedding bằng MiniLM → lưu vào vector index (R4).
2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?** Frozen test set 10 câu hỏi factual được sinh từ clean dataframe; mỗi câu có `ground_truth_doc_ids` đã kiểm tra tồn tại trong baseline. Retrieval hit rate đếm khi `retrieved_doc_ids` chứa ít nhất một ground truth doc ID; answer quality dùng Token F1 và LLM judge so với `ground_truth` text.
3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?** Quality checks kiểm tra tính hợp lệ của dữ liệu tại thời điểm chạy (duplicate IDs, blank/short summaries); freshness monitoring kiểm tra dữ liệu có bị cũ quá hạn (stale >180 ngày) hay không. Quality là lỗi cấu trúc, freshness là lỗi thời gian.
4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?** Để cô lập biến duy nhất là trạng thái dữ liệu; nếu test set thay đổi, mọi chênh lệch metric có thể đến từ test set chứ không phải từ corruption/repair.
5. **Repair được xem là thành công dựa trên artifact và metric nào?** Dựa trên (a) metrics answer quality phục hồi về baseline (Token F1 = 1.00, judge accuracy = 1.00, mean judge score = 5.00), (b) quality signals phục hồi (duplicate IDs về 0, blank summaries về 0), (c) freshness trở về mức baseline (stale rows = 2, giống baseline). Artifact: `data/results/repaired_metrics.json`, `data/results/repaired_quality.json`, `data/results/repaired_freshness.json`.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |      1.00 |       1.00 |      1.00 | Không đổi vì các paper bị ảnh hưởng vẫn có trong index; retrieval một mình không phát hiện được corruption |
| `mean_token_f1`      |      1.00 |       0.70 |      1.00 | Giảm 0.30 khi summary/metadata hỏng; phục hồi sau repair cho thấy raw snapshot đầy đủ |
| `judge_accuracy`     |      1.00 |       0.70 |      1.00 | Cùng xu hướng với Token F1; 7/10 câu vẫn trả lời đúng ở corrupted, 3 câu bị ảnh hưởng bởi context hỏng |
| `mean_judge_score`   |      5.00 |       3.80 |      5.00 | Điểm trung bình giảm 1.2 ở corrupted; phục hồi hoàn toàn sau repair |
| Quality checks         |      FAIL |       FAIL |      FAIL | Baseline/repaired FAIL do 2 stale rows có sẵn trong clean snapshot; corrupted FAIL thêm vì duplicate IDs và blank summaries |
| Freshness status       |      2 stale |       4 stale |      2 stale | Corrupted có thêm 2 stale rows do corruption gây ra; repair khôi phục về baseline 2 stale |

### Kết luận từ số liệu

Hai chuỗi nguyên nhân–bằng chứng:

1. **[Corruption]** (xóa summary + làm hỏng metadata) → **[quality/freshness signal thay đổi]** (duplicate IDs 0→2, blank summaries 0→3, stale rows 2→4) → **[agent metric thay đổi]** (Token F1 1.00→0.70, judge accuracy 1.00→0.70, mean judge score 5.00→3.80).
2. **[Repair action]** (khôi phục từ raw snapshot) → **[quality/freshness signal phục hồi]** (duplicate IDs về 0, blank summaries về 0, stale rows về 2) → **[agent metric phục hồi]** (Token F1 0.70→1.00, judge accuracy 0.70→1.00, mean judge score 3.80→5.00).

**Corruption nào ảnh hưởng rõ nhất và vì sao?**

Corruption trên summary/metadata ảnh hưởng rõ nhất đến answer quality vì agent dựa vào nội dung document để sinh câu trả lời. Khi summary bị xóa hoặc metadata bị hỏng, retrieved context vẫn đúng (hit rate giữ 1.00) nhưng nội dung truyền vào prompt bị suy giảm, kéo theo Token F1 và judge accuracy giảm 0.30.

**Kết quả nào khác với kỳ vọng ban đầu?**

Hai điểm: (1) Retrieval hit rate không đổi qua corruption — ban đầu kỳ vọng retrieval sẽ giảm, nhưng thực tế index không bị mất document nên hit rate giữ 1.00; điều này cho thấy retrieval hit rate là metric cần thiết nhưng chưa đủ. (2) Quality baseline/repaired vẫn FAIL vì clean snapshot có sẵn 2 records cũ hơn 180 ngày — đây là giới hạn dữ liệu nguồn, không phải metric giả; đã ghi minh bạch trong freshness artifact và report.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Frozen test set là điều kiện tiên quyết để so sánh metric giữa các trạng thái dữ liệu; không có nó, mọi kết luận về repair đều có nhiễu.
2. Data observability cần hai lớp: data quality (duplicate IDs, blank summaries) để phát hiện lỗi cấu trúc và freshness (stale rows) để phát hiện lỗi thời gian; kết hợp cả hai mới tách bạch được nguyên nhân.
3. Retrieval hit rate chỉ đo "tìm được đúng tài liệu", không đo "trả lời đúng"; answer-level metrics (Token F1, judge) mới phản ánh chất lượng RAG end-to-end.

### Nếu có thêm thời gian

1. Thay hoặc lọc hai raw records stale để baseline/repaired quality PASS toàn bộ, sau đó chạy lại hai pipeline và so sánh report; đo cải thiện bằng cách quality status đổi từ FAIL → PASS đồng thời metrics answer quality vẫn giữ baseline.
2. Bật `RUN_RAGAS=1` khi môi trường/provider hỗ trợ để bổ sung đánh giá Ragas (faithfulness, answer relevancy) — đo cải thiện bằng việc bổ sung được hai cột metric mới trong report.
3. Ghi rõ provider/model của lần chạy nộp bài trong report nếu LLM judge được dùng, để người đọc lập lại được cùng điều kiện.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Mai Văn Phương
**Ngày xác nhận:** 2026-08-06
