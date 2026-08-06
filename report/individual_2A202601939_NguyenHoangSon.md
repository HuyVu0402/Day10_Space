# Member Role Report - Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Hoàng Sơn |
| MSSV | 2A202601939 |
| Khóa/Lớp | K4 |
| Tên nhóm | Space |
| Vai trò chính | R4 - Retrieval & RAG Owner |
| Repository | `https://github.com/HuyVu0402/Day10_Space` |
| Ngày hoàn thành | 2026-08-06 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| Embedding Backend | `src/retrieval/embeddings.py` (`MiniLMEmbeddings`) | Model name (`sentence-transformers/all-MiniLM-L6-v2`) | Vector float lists (384 dimensions) | Hoàn thành |
| Vector Index & Persistence | `src/retrieval/index.py` (`LocalEmbeddingIndex`) | Clean, Corrupted, Repaired DataFrames | Collection ChromaDB (`papers-baseline`, `papers-corrupted`, `papers-repaired`), Manifest JSON | Hoàn thành |
| LLM Provider Integration | `src/retrieval/llm.py` (`build_llm`) | `Settings` cấu hình provider (`gemini`, `openrouter`, `openai`, `anthropic`, `ollama`) | LangChain ChatModel instance | Hoàn thành |
| RAG Agent & Exact Lookup | `src/retrieval/agent.py`, `src/retrieval/qa.py` | Câu hỏi từ `test_set.json`, Index | `AnswerResult` (`answer`, `retrieved_doc_ids`, `retrieved_contexts`, `retrieved_titles`) | Hoàn thành |
| RAG Answers Artifacts | `data/results/*answers.json` | Run evaluation pipelines | `baseline_answers.json`, `corrupted_answers.json`, `repaired_answers.json` | Hoàn thành |

---

## 3. Kết quả theo vai trò

| Checkpoint | Nhiệm vụ đã thực hiện | Artifact / File liên quan | Kết quả nghiệm thu |
| :---: | :--- | :--- | :--- |
| **C0** | Kiểm tra môi trường `sentence-transformers`, `chromadb`, `langchain` | `src/retrieval/embeddings.py` | Load thành công model MiniLM L6-v2 (384 dimensions) |
| **C1** | Thống nhất Agent Result Schema với R5 và Clean Schema với R3 | `PHAN_CONG_CONG_VIEC.md`, `report/group_report.md` | Chốt schema `answer`, `retrieved_doc_ids`, `contexts`, `provider`, `model` |
| **C2** | Build ChromaDB Vector Index `papers-baseline` từ dữ liệu sạch của R3 | `data/embeddings/papers_embeddings.json` | Nạp & index thành công 24 tài liệu sạch |
| **C3** | Chạy RAG Agent trên tập câu hỏi đóng băng `test_set.json` của R5 | `data/results/baseline_answers.json`, `baseline_metrics.json` | **Retrieval Hit Rate: 100.00%**, Token F1: 1.0000, Judge Score: 5.0/5.0 |
| **C4** | Build 2 Collection riêng biệt `papers-corrupted` & `papers-repaired`, chạy RAG cho cả 3 trạng thái | `corrupted_answers.json`, `repaired_answers.json`, `corruption_report.md` | Retrieval Hit Rate: Corrupted (60%) ➔ Repaired (100%), chứng minh dữ liệu xấu làm suy giảm RAG |
| **C5** | Hoàn thiện báo cáo cá nhân và bàn giao cho R1 release bài nộp | `report/individual_2A202601939_NguyenHoangSon.md` | Báo cáo hoàn chỉnh, repository sạch sẽ |

---

## 4. Giải thích chi tiết kỹ thuật triển khai (Technical Implementation)

### 4.1 Embedding Backend & Cache Optimization
- Sử dụng mô hình `sentence-transformers/all-MiniLM-L6-v2` tạo ra vector embedding 384 chiều với tốc độ xử lý tối ưu.
- Áp dụng `@lru_cache(maxsize=4)` trong `_load_model()` để đảm bảo weights chỉ được load vào RAM một lần duy nhất, tránh tốn RAM và giảm thời gian khởi tạo.

### 4.2 Cấu trúc Vector Index & ChromaDB Isolation
- Sử dụng `chromadb.PersistentClient` quản lý không gian vectorDB.
- Thực hiện nghiêm ngặt nguyên tắc **Cô lập 3 trạng thái (State Isolation)**:
  1. Baseline Index: Collection `papers-baseline` ➔ Manifest `data/embeddings/papers_embeddings.json`.
  2. Corrupted Index: Collection `papers-corrupted` ➔ Manifest `data/embeddings/papers_embeddings_corrupted.json`.
  3. Repaired Index: Collection `papers-repaired` ➔ Manifest `data/embeddings/papers_embeddings_repaired.json`.
- Đảm bảo mỗi trạng thái dữ liệu có collection và manifest hoàn toàn riêng biệt, không bị lẫn vector hay ghi đè baseline.

### 4.3 RAG Hybrid Retrieval Strategy (`qa.py` & `agent.py`)
- Kết hợp cả **Exact Lookup** theo tên bài báo/DOI (`index.lookup`) và **Semantic Search** theo cosine distance (`index.search`).
- Tự động gộp kết quả tìm kiếm chính xác và kết quả ngữ nghĩa, loại bỏ trùng lặp bản ghi, đảm bảo `retrieved_doc_ids` giữ nguyên `paper_id` từ raw/clean data.
- Xử lý các giá trị `NaN`/`None` ở dữ liệu bị lỗi (corrupted) một cách an toàn để pipeline không bị ngắt giữa chừng.

---

## 5. Tự đánh giá và kết luận

- **Hoàn thành 100% nhiệm vụ Role 4** theo đúng phân công trong `PHAN_CONG_CONG_VIEC.md`.
- Đảm bảo tính nhất quán của dữ liệu xuyên suốt các mốc từ C0 đến C5.
- Phối hợp hiệu quả với R2, R3, R5 và R1 để tạo nên pipeline hoàn chỉnh và có khả năng phục hồi dữ liệu minh bạch.
