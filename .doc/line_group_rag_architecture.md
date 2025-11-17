# LINE 群組 RAG 系統架構規格書

## 📋 目錄

1. [系統概述](#系統概述)
2. [技術規格](#技術規格)
3. [專案目錄結構](#專案目錄結構)
4. [五層架構設計](#五層架構設計)
5. [LangChain Agent 架構](#langchain-agent-架構)
6. [API 規格](#api-規格)
7. [資料流程](#資料流程)
8. [開發指南](#開發指南)
9. [待辦事項](#待辦事項)

---

## 🎯 系統概述

### 系統目標

開發一套基於 LangChain 1.0.x 的 LINE 群組 RAG（Retrieval-Augmented Generation）系統，支援：

- 上傳 LINE 群組匯出的 Excel 訊息檔
- 向量化儲存於 Qdrant
- 原始對話儲存於 PostgreSQL
- BM25 索引支援關鍵字查詢
- 智能 Agent 處理多樣化查詢需求

### 核心功能

1. **資料匯入**：解析 LINE Excel 檔案並進行向量化處理
2. **混合搜尋**：結合向量搜尋與 BM25 關鍵字搜尋
3. **智能查詢**：使用 LangChain Agent 處理各類查詢
4. **分數融合**：多維度評分機制確保結果品質

---

## 🛠️ 技術規格

| 技術項目            | 版本/規格       | 用途                   |
| ------------------- | --------------- | ---------------------- |
| **Python**          | 3.11+           | 主要開發語言           |
| **Package Manager** | uv              | 套件管理與 auto-reload |
| **Web Framework**   | FastAPI         | REST API 服務          |
| **ORM**             | SQLAlchemy 2.0+ | 資料庫 ORM             |
| **Database**        | PostgreSQL 15+  | 主要資料儲存           |
| **Vector DB**       | Qdrant          | 向量資料庫             |
| **AI Framework**    | LangChain 1.0.x | RAG Pipeline & Agent   |
| **LLM**             | OpenAI GPT-4    | 語言模型               |
| **Search**          | BM25            | 關鍵字搜尋             |

---

## 📁 專案目錄結構

```
line-group-rag/
├── .env.example                    # 環境變數範本
├── .gitignore                      # Git 忽略檔案
├── pyproject.toml                  # uv 專案設定檔
├── README.md                       # 專案說明文件
│
├── app/                            # 主應用程式目錄
│   ├── __init__.py
│   ├── main.py                     # FastAPI 應用程式進入點
│   │
│   ├── api/                        # API 層
│   │   ├── __init__.py
│   │   ├── dependencies.py         # API 共用相依性注入
│   │   └── v1/                     # API v1 版本
│   │       ├── __init__.py
│   │       ├── routers/            # 路由控制器
│   │       │   ├── __init__.py
│   │       │   ├── messages.py     # Excel 上傳端點
│   │       │   ├── query.py        # RAG 查詢端點
│   │       │   ├── groups.py       # LINE 群組管理端點
│   │       │   └── health.py       # 健康檢查端點
│   │       └── endpoints.py        # 路由註冊彙總
│   │
│   ├── core/                       # 核心設定與工具
│   │   ├── __init__.py
│   │   ├── config.py               # 系統設定管理
│   │   ├── logging.py              # 日誌設定
│   │   ├── exceptions.py           # 自定義例外
│   │   └── constants.py            # 系統常數定義
│   │
│   ├── db/                         # 資料庫層
│   │   ├── __init__.py
│   │   ├── base.py                 # SQLAlchemy Base
│   │   ├── session.py              # 資料庫連線管理
│   │   └── migrations/             # Alembic 遷移檔案
│   │       ├── alembic.ini
│   │       └── versions/            # 遷移版本目錄
│   │
│   ├── models/                     # ORM 資料模型
│   │   ├── __init__.py
│   │   ├── line_group.py           # LINE 群組模型
│   │   ├── message.py              # 訊息模型
│   │   ├── embedding.py            # Embedding 記錄模型
│   │   ├── user.py                 # 使用者模型
│   │   └── query_log.py            # 查詢記錄模型
│   │
│   ├── schemas/                    # Pydantic 資料結構
│   │   ├── __init__.py
│   │   ├── upload.py               # 上傳相關 schema
│   │   ├── query.py                # 查詢相關 schema
│   │   ├── message.py              # 訊息 schema
│   │   ├── group.py                # 群組 schema
│   │   └── response.py             # 統一回應格式
│   │
│   ├── services/                   # 商業邏輯層
│   │   ├── __init__.py
│   │   ├── upload_service.py       # Excel 上傳處理服務
│   │   ├── embedding_service.py    # Embedding 處理服務
│   │   ├── query_service.py        # 查詢處理服務
│   │   ├── scoring_service.py      # 分數融合服務
│   │   └── group_service.py        # 群組管理服務
│   │
│   ├── repositories/               # 資料存取層
│   │   ├── __init__.py
│   │   ├── base.py                 # 基礎 Repository
│   │   ├── message_repo.py         # 訊息資料存取
│   │   ├── group_repo.py           # 群組資料存取
│   │   ├── user_repo.py            # 使用者資料存取
│   │   └── query_log_repo.py       # 查詢記錄存取
│   │
│   ├── agents/                     # LangChain Agent 核心
│   │   ├── __init__.py
│   │   ├── main_agent.py           # 主 Agent 建立與管理
│   │   ├── agent_factory.py        # Agent 工廠方法
│   │   └── agent_config.py         # Agent 設定管理
│   │
│   ├── tools/                      # Agent 工具集合
│   │   ├── __init__.py
│   │   ├── base_tool.py            # Tool 基礎類別
│   │   │
│   │   ├── retrieval/              # 檢索相關工具
│   │   │   ├── __init__.py
│   │   │   ├── date_range_tool.py  # 日期範圍查詢工具
│   │   │   ├── keyword_search_tool.py   # 關鍵字查詢工具
│   │   │   ├── semantic_search_tool.py  # 語意查詢工具
│   │   │   └── hybrid_search_tool.py    # 混合查詢工具
│   │   │
│   │   ├── analysis/               # 分析相關工具
│   │   │   ├── __init__.py
│   │   │   ├── statistics_tool.py  # 統計分析工具
│   │   │   ├── aggregation_tool.py # 聚合運算工具
│   │   │   ├── trend_analysis_tool.py   # 趨勢分析工具
│   │   │   └── frequency_tool.py   # 頻率分析工具
│   │   │
│   │   ├── extraction/             # 資訊萃取工具
│   │   │   ├── __init__.py
│   │   │   ├── entity_extraction_tool.py # 實體萃取工具
│   │   │   ├── topic_extraction_tool.py  # 主題萃取工具
│   │   │   └── sentiment_tool.py   # 情感分析工具
│   │   │
│   │   └── formatting/             # 格式化工具
│   │       ├── __init__.py
│   │       ├── summary_tool.py     # 摘要生成工具
│   │       ├── table_formatter_tool.py  # 表格格式化工具
│   │       └── timeline_tool.py    # 時間軸生成工具
│   │
│   ├── tool_schemas/               # Tool 參數結構定義
│   │   ├── __init__.py
│   │   ├── date_range_schema.py    # 日期範圍參數
│   │   ├── statistics_schema.py    # 統計參數
│   │   └── search_params_schema.py # 搜尋參數
│   │
│   ├── rag/                        # RAG 核心元件
│   │   ├── __init__.py
│   │   ├── pipeline.py             # LangChain RAG pipeline
│   │   ├── chains/                 # LangChain chains
│   │   │   ├── __init__.py
│   │   │   ├── retrieval_chain.py  # 檢索鏈
│   │   │   └── qa_chain.py         # 問答鏈
│   │   └── retrievers/             # 檢索器
│   │       ├── __init__.py
│   │       ├── vector_retriever.py # 向量檢索器
│   │       └── hybrid_retriever.py # 混合檢索器
│   │
│   ├── prompts/                    # Prompt 模板
│   │   ├── __init__.py
│   │   ├── agent_prompts/          # Agent 相關 prompts
│   │   │   ├── __init__.py
│   │   │   ├── system_prompt.py    # Agent 系統 prompt
│   │   │   ├── tool_selection_prompt.py # 工具選擇指引
│   │   │   └── reasoning_prompt.py # 推理指引
│   │   └── tool_prompts/           # 工具相關 prompts
│   │       ├── __init__.py
│   │       └── analysis_prompts.py # 分析工具 prompts
│   │
│   ├── orchestration/              # 協調層
│   │   ├── __init__.py
│   │   ├── query_classifier.py     # 查詢分類器
│   │   ├── tool_selector.py        # 工具選擇器
│   │   └── result_combiner.py      # 結果組合器
│   │
│   ├── embeddings/                 # Embedding 處理
│   │   ├── __init__.py
│   │   ├── base.py                 # Embedding 基礎類別
│   │   ├── openai_embedder.py      # OpenAI embedding
│   │   ├── local_embedder.py       # 本地 embedding 模型
│   │   └── chunking.py             # 文本分塊策略
│   │
│   ├── vector_store/               # 向量資料庫
│   │   ├── __init__.py
│   │   ├── qdrant_client.py        # Qdrant 客戶端封裝
│   │   ├── collection_manager.py   # 集合管理
│   │   └── vector_operations.py    # 向量操作
│   │
│   ├── search/                     # 搜尋元件
│   │   ├── __init__.py
│   │   ├── bm25_index.py           # BM25 索引管理
│   │   ├── hybrid_search.py        # 混合搜尋實作
│   │   └── reranker.py             # 結果重排序
│   │
│   ├── parsers/                    # 檔案解析器
│   │   ├── __init__.py
│   │   ├── excel_parser.py         # Excel 解析
│   │   ├── line_format.py          # LINE 格式處理
│   │   └── validators.py           # 資料驗證
│   │
│   └── utils/                      # 工具函式
│       ├── __init__.py
│       ├── datetime_utils.py       # 日期時間處理
│       ├── text_utils.py           # 文字處理
│       ├── score_utils.py          # 分數計算工具
│       └── cache_utils.py          # 快取管理
│
├── scripts/                        # 執行腳本
│   ├── __init__.py
│   ├── init_db.py                  # 初始化資料庫
│   ├── init_qdrant.py              # 初始化 Qdrant
│   ├── rebuild_index.py            # 重建 BM25 索引
│   └── migrate.py                  # 資料遷移
│
├── tests/                          # 測試目錄
│   ├── __init__.py
│   ├── conftest.py                 # pytest 設定
│   ├── unit/                       # 單元測試
│   │   ├── __init__.py
│   │   ├── test_agents/            # Agent 測試
│   │   ├── test_tools/             # Tool 測試
│   │   ├── test_embeddings/        # Embedding 測試
│   │   ├── test_parsers/           # Parser 測試
│   │   ├── test_search/            # Search 測試
│   │   └── test_services/          # Service 測試
│   ├── integration/                # 整合測試
│   │   ├── __init__.py
│   │   ├── test_api/               # API 測試
│   │   ├── test_rag_pipeline/      # RAG Pipeline 測試
│   │   └── test_vector_store/      # Vector Store 測試
│   └── fixtures/                   # 測試資料
│       ├── __init__.py
│       ├── sample_excel/           # 範例 Excel 檔
│       └── mock_data.py            # 模擬資料
│
├── config/                         # 設定檔目錄
│   ├── __init__.py
│   ├── agent_config.yaml           # Agent 設定
│   ├── database.yaml               # 資料庫設定
│   └── embedding.yaml              # Embedding 設定
│
├── data/                           # 資料目錄
│   ├── uploads/                    # 上傳暫存
│   ├── processed/                  # 處理後資料
│   └── indexes/                    # BM25 索引檔案
│
├── logs/                           # 日誌目錄
│   ├── app.log                     # 應用程式日誌
│   ├── error.log                   # 錯誤日誌
│   └── query.log                   # 查詢日誌
│
└── docs/                           # 文件目錄
    ├── api.md                      # API 文件
    ├── architecture.md             # 架構說明
    ├── deployment.md               # 部署指南
    └── development.md              # 開發指南
```

---

## 🏗️ 五層架構設計

### 架構層級關係

```
┌─────────────────────────────────────────────────────────┐
│                     FastAPI Router                       │
│                   (API Endpoint 層)                      │
└────────────────────────┬────────────────────────────────┘
                         │ 依賴注入
                         ▼
┌─────────────────────────────────────────────────────────┐
│                      Services                           │
│                   (商業邏輯層)                           │
└────────────────────────┬────────────────────────────────┘
                         │ 調用
                         ▼
┌─────────────────────────────────────────────────────────┐
│                    Repositories                         │
│                   (資料存取層)                           │
└────────────────────────┬────────────────────────────────┘
                         │ 操作
                         ▼
┌─────────────────────────────────────────────────────────┐
│                       Models                            │
│                  (ORM 資料模型層)                        │
└────────────────────────┬────────────────────────────────┘
                         │ 映射
                         ▼
┌─────────────────────────────────────────────────────────┐
│                         DB                              │
│                   (實體資料庫)                           │
└─────────────────────────────────────────────────────────┘

         ◄──── Schemas (Pydantic) 貫穿所有層 ────►
```

### 各層職責說明

| 層級             | 位置                | 主要職責                 | 特點                   |
| ---------------- | ------------------- | ------------------------ | ---------------------- |
| **DB**           | `app/db/`           | 資料庫連線管理、遷移控制 | 實際的 PostgreSQL 實例 |
| **Models**       | `app/models/`       | 定義資料表結構、關聯關係 | SQLAlchemy ORM 模型    |
| **Schemas**      | `app/schemas/`      | API 資料驗證、序列化     | Pydantic 模型          |
| **Repositories** | `app/repositories/` | 封裝資料庫操作 (CRUD)    | 資料存取抽象層         |
| **Services**     | `app/services/`     | 實作商業邏輯、協調各元件 | 不直接操作資料庫       |

### 依賴原則

```
Router → Service → Repository → Model → DB
         ↑                        ↑
         └──────Schema───────────┘
```

- **單向依賴**：上層依賴下層，下層不知道上層存在
- **關注點分離**：每層專注特定職責
- **可測試性**：每層可獨立測試
- **可替換性**：易於更換實作（如更換資料庫）

---

## 🤖 LangChain Agent 架構

### Agent 執行流程

```
使用者查詢
    │
    ▼
┌─────────────────────────────┐
│      Query Classifier       │ ← 分析查詢類型
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│        Main Agent           │ ← 決策中心
│   - 理解使用者意圖         │
│   - 制定執行計畫           │
│   - 選擇工具組合           │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│      Tool Execution         │ ← 工具執行
│   - Date Range Tool         │
│   - Statistics Tool         │
│   - Semantic Search Tool    │
│   - Summary Tool            │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│     Result Combiner         │ ← 結果整合
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│      Final Response         │ ← 生成回答
└─────────────────────────────┘
```

### Tool 分類架構

| 工具類別       | 工具名稱               | 處理範例              |
| -------------- | ---------------------- | --------------------- |
| **檢索工具**   | date_range_tool        | 「上週討論了什麼？」  |
|                | keyword_search_tool    | 「關於產品 A 的討論」 |
|                | semantic_search_tool   | 「大家對提案的看法」  |
|                | hybrid_search_tool     | 複合條件查詢          |
| **分析工具**   | statistics_tool        | 「本月討論統計」      |
|                | aggregation_tool       | 「預算總額計算」      |
|                | trend_analysis_tool    | 「討論熱度趨勢」      |
|                | frequency_tool         | 「最常討論的主題」    |
| **萃取工具**   | entity_extraction_tool | 「提取人名、產品名」  |
|                | topic_extraction_tool  | 「識別討論主題」      |
|                | sentiment_tool         | 「分析討論氛圍」      |
| **格式化工具** | summary_tool           | 「總結本月重點」      |
|                | table_formatter_tool   | 「製作統計表格」      |
|                | timeline_tool          | 「生成時間軸」        |

### Tool 協作模式

#### 串行模式 (Sequential)

```
範例：「上週小明提到的產品問題」

執行順序：
1. date_range_tool → 篩選上週訊息
2. entity_extraction_tool → 找出小明的發言
3. topic_extraction_tool → 識別產品問題
4. summary_tool → 整理結果
```

#### 並行模式 (Parallel)

```
範例：「本月會議統計和重要決議」

並行執行：
├─ statistics_tool → 會議次數、參與人數
├─ entity_extraction_tool → 決議事項
└─ sentiment_tool → 討論氛圍
```

#### 條件模式 (Conditional)

```
範例：「有討論過預算嗎？如果有，統計金額」

條件執行：
1. keyword_search_tool → 搜尋「預算」
2. IF 有結果：
   → aggregation_tool → 統計金額
   ELSE：
   → 回報無相關討論
```

---

## 📡 API 規格

### API 端點設計

| 端點                           | 方法 | 功能描述        | Request                  | Response            |
| ------------------------------ | ---- | --------------- | ------------------------ | ------------------- |
| `/api/v1/upload`               | POST | 上傳 LINE Excel | MultipartForm + Metadata | UploadResponse      |
| `/api/v1/query`                | POST | RAG 查詢        | QueryRequest             | QueryResponse       |
| `/api/v1/groups`               | GET  | 列出群組        | -                        | GroupListResponse   |
| `/api/v1/groups/{id}`          | GET  | 群組詳情        | -                        | GroupDetailResponse |
| `/api/v1/groups/{id}/messages` | GET  | 群組訊息        | Pagination               | MessageListResponse |
| `/api/v1/health`               | GET  | 健康檢查        | -                        | HealthResponse      |

### Request/Response Schema 結構

```python
# 架構示意（非實作）

# 上傳請求
UploadRequest:
  - file: UploadFile
  - group_name: str
  - description: Optional[str]
  - metadata: Optional[Dict]

# 查詢請求
QueryRequest:
  - group_id: str
  - question: str
  - date_range: Optional[DateRange]
  - search_type: Literal["hybrid", "vector", "keyword"]
  - top_k: int = 50

# 查詢回應
QueryResponse:
  - answer: str
  - sources: List[MessageSource]
  - confidence: float
  - execution_path: List[ToolExecution]
  - metadata: Dict
```

---

## 🔄 資料流程

### 上傳流程

```
Excel 檔案上傳
    │
    ▼
┌─────────────────────────────┐
│      Excel Parser           │ ← 解析 LINE 格式
└──────────────┬──────────────┘
               │
    ┌──────────┴──────────┐
    ▼                     ▼
┌──────────┐         ┌──────────┐
│ Chunking │         │ Validate │
└────┬─────┘         └────┬─────┘
     │                     │
     ▼                     ▼
┌──────────┐         ┌──────────┐
│Embedding │         │ Save DB  │
└────┬─────┘         └──────────┘
     │
     ├─────────────┬──────────┐
     ▼             ▼          ▼
┌─────────┐  ┌─────────┐  ┌───────┐
│ Qdrant  │  │Postgres │  │ BM25  │
└─────────┘  └─────────┘  └───────┘
```

### 查詢流程

```
使用者查詢
    │
    ▼
┌─────────────────────────────┐
│    Query Classification     │
└──────────────┬──────────────┘
               │
    ┌──────────┴──────────┐
    ▼                     ▼
┌──────────┐         ┌──────────┐
│ Qdrant   │         │  BM25    │
│ Search   │         │  Search  │
└────┬─────┘         └────┬─────┘
     │                     │
     └──────────┬──────────┘
                ▼
┌─────────────────────────────┐
│      Score Fusion           │
│ α×cosine + β×bm25 + γ×time │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│    Filter (score > 0.3)     │
└──────────────┬──────────────┘
               │
               ▼
┌─────────────────────────────┐
│   LangChain RAG Pipeline    │
└──────────────┬──────────────┘
               │
               ▼
         生成回答
```

### 分數融合公式

```
score_final = α × norm(cosine_similarity) +
              β × norm(bm25_score) +
              γ × recency_boost

where:
- α + β + γ = 1.0
- recency_boost = exp(-λ × days_old) × boost_factor
- boost_factor: 0.05 ~ 0.15 (for messages within 30 days)
```

---

## 💻 開發指南

### 環境設定

```bash
# 1. 安裝 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. 初始化專案
uv init
uv sync

# 3. 設定環境變數
cp .env.example .env
# 編輯 .env 檔案填入必要資訊

# 4. 初始化資料庫
uv run python scripts/init_db.py

# 5. 初始化 Qdrant
uv run python scripts/init_qdrant.py
```

### 開發模式啟動

```bash
# 啟動 FastAPI (支援 auto-reload)
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# 或使用自定義啟動腳本
uv run python -m app.main
```

### 測試執行

```bash
# 執行所有測試
uv run pytest

# 執行單元測試
uv run pytest tests/unit

# 執行整合測試
uv run pytest tests/integration

# 測試覆蓋率
uv run pytest --cov=app tests/
```

### 程式碼風格

```bash
# 格式化
uv run black app/ tests/
uv run isort app/ tests/

# 檢查
uv run flake8 app/ tests/
uv run mypy app/
```

---

## 📋 待辦事項

### Phase 1: 基礎建設 ✅

- [x] 專案 scaffolding 與目錄架構確認
- [x] 五層架構設計
- [x] LangChain Agent 架構規劃

### Phase 2: 資料層設計

- [ ] **Postgres + SQLAlchemy 模型規劃**
  - [ ] LINE 群組資料表設計
  - [ ] 訊息資料表設計
  - [ ] 使用者資料表設計
  - [ ] Embedding 記錄表設計
  - [ ] 查詢記錄表設計
  - [ ] 關聯關係定義
  - [ ] 索引設計

### Phase 3: 資料處理

- [ ] **Excel 解析模組規劃**
  - [ ] LINE 匯出格式分析
  - [ ] 欄位對應設計
  - [ ] 資料驗證規則
  - [ ] 批次處理策略
  - [ ] 錯誤處理機制

### Phase 4: 向量處理

- [ ] **Embedding pipeline 與 Qdrant schema**
  - [ ] Embedding 模型選擇（OpenAI/Local）
  - [ ] Chunking 策略設計
  - [ ] Qdrant collection 結構
  - [ ] Metadata 設計
  - [ ] 批次向量化流程
  - [ ] 向量維度管理

### Phase 5: 搜尋系統

- [ ] **BM25 index 設計**
  - [ ] 索引結構規劃
  - [ ] 更新策略
  - [ ] 查詢優化
  - [ ] 與向量搜尋整合
  - [ ] 中文分詞處理

### Phase 6: 評分系統

- [ ] **資料融合分數邏輯（score fusion）**
  - [ ] Cosine similarity 正規化
  - [ ] BM25 分數正規化
  - [ ] 時間衰減函數設計（recency_boost）
  - [ ] 權重參數配置（α, β, γ）
  - [ ] 閾值設定（score_final < 0.3）
  - [ ] A/B 測試框架

### Phase 7: RAG Pipeline

- [ ] **LangChain RAG pipeline 結構**
  - [ ] Retriever 設計
  - [ ] Chain 架構
  - [ ] Prompt engineering
  - [ ] Context window 管理
  - [ ] Response generation
  - [ ] Streaming 支援

### Phase 8: Agent 系統

- [ ] **LangChain Agent 實作**
  - [ ] Main Agent 建立
  - [ ] Tool 實作（15+ tools）
  - [ ] Tool 選擇邏輯
  - [ ] 執行策略（串行/並行/條件）
  - [ ] 錯誤處理與降級
  - [ ] Agent 記憶機制

### Phase 9: API 層

- [ ] **FastAPI API 端點與 schema**
  - [ ] Upload API 實作
  - [ ] Query API 實作
  - [ ] Group management API
  - [ ] WebSocket 支援（即時查詢）
  - [ ] Rate limiting
  - [ ] API 文檔（Swagger/ReDoc）

### Phase 10: 系統設定

- [ ] **系統設定與部署**
  - [ ] 環境變數管理
  - [ ] 設定檔架構（YAML）
  - [ ] Docker 化
  - [ ] Kubernetes 部署檔
  - [ ] CI/CD pipeline

### Phase 11: 監控與維護

- [ ] **系統監控與日誌**
  - [ ] 結構化日誌（JSON）
  - [ ] APM 整合（Datadog/New Relic）
  - [ ] 錯誤追蹤（Sentry）
  - [ ] 效能監控
  - [ ] 查詢分析儀表板

### Phase 12: 測試與品質

- [ ] **測試策略**
  - [ ] 單元測試（>80% 覆蓋率）
  - [ ] 整合測試
  - [ ] E2E 測試
  - [ ] 效能測試
  - [ ] 負載測試

---

## 📊 系統規格摘要

### 效能目標

- **上傳處理**：10,000 訊息/分鐘
- **查詢回應**：< 2 秒（p95）
- **並發支援**：100 concurrent users
- **向量搜尋**：< 100ms（50 筆結果）
- **可用性**：99.9% uptime

### 資源需求

- **CPU**：8 cores minimum
- **RAM**：16 GB minimum
- **Storage**：100 GB SSD
- **Qdrant**：4 GB RAM per million vectors
- **PostgreSQL**：連線池 20-50

### 安全性

- API Key 認證
- Rate limiting
- 資料加密（at rest & in transit）
- SQL Injection 防護
- XSS 防護

---

## 📝 版本資訊

- **文件版本**：1.0.0
- **最後更新**：2024-11-14
- **作者**：System Architect Team
- **審核狀態**：Draft

---

## 📚 參考資源

- [LangChain 1.0.x Documentation](https://python.langchain.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [SQLAlchemy 2.0 Documentation](https://docs.sqlalchemy.org/)
- [BM25 Algorithm](https://en.wikipedia.org/wiki/Okapi_BM25)

---

## 📄 授權

本專案採用 MIT License
