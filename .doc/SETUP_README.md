# LINE Group RAG System - 專案自動建立工具

## 📦 檔案說明

本工具會自動為您建立完整的 LINE Group RAG 系統專案結構，包含所有必要的目錄和檔案。

## 🚀 快速開始

### 1. 下載並執行設定腳本

```powershell
# 下載 setup_complete.py 後執行
python setup_complete.py
```

### 2. 專案會自動建立以下內容

✅ **完整目錄結構**

- 70+ 個目錄
- 適用於 Windows 11 環境

✅ **所有必要檔案**

- `.env.example` - 環境變數範本
- `pyproject.toml` - uv 套件管理設定
- 所有 Python 模組檔案
- Windows 批次檔 (.bat)

✅ **預設程式碼**

- FastAPI 應用程式架構
- API 路由端點
- 資料庫連線設定
- 基礎測試檔案

## 📋 設定完成後的步驟

### 1. 進入專案目錄

```powershell
cd line-group-rag
```

### 2. 設定環境變數

```powershell
copy .env.example .env
notepad .env
```

在 `.env` 檔案中填入：

- PostgreSQL 資料庫連線資訊
- OpenAI API Key
- Qdrant 設定（如果不是預設值）

### 3. 安裝 Python 套件

**選項 A: 使用 uv (推薦)**

```powershell
# 安裝 uv
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# 安裝專案依賴
uv sync
```

**選項 B: 使用 pip**

```powershell
pip install -r requirements.txt
```

### 4. 安裝並啟動資料庫服務

**PostgreSQL:**

- 下載: https://www.postgresql.org/download/windows/
- 安裝後記住密碼
- 建立資料庫: `line_rag_db`

**Qdrant (使用 Docker):**

```powershell
docker pull qdrant/qdrant
docker run -p 6333:6333 qdrant/qdrant
```

### 5. 初始化資料庫

```powershell
# 初始化 PostgreSQL 表格
python scripts\init_db.py

# 初始化 Qdrant 集合
python scripts\init_qdrant.py
```

### 6. 啟動開發伺服器

```powershell
# 方法 1: 使用 uv
uv run uvicorn app.main:app --reload

# 方法 2: 使用批次檔
start_dev.bat

# 方法 3: 直接使用 Python
python -m uvicorn app.main:app --reload
```

### 7. 存取系統

- API 文檔: http://localhost:8200/docs
- 健康檢查: http://localhost:8200/health
- 主要 API: http://localhost:8200/api/v1/

### 8. 建立或調整資料表

使用 Alembic 來管理資料表結構。

- 產生 migration 檔（根據目前的 SQLAlchemy models，自動產生變更草稿）：

```powershell
# 在專案目錄下，啟用專案環境後執行（使用 `uv run`）
uv run alembic revision --autogenerate -m "create line_groups and line_messages"
uv run alembic revision --autogenerate -m "create chunk_message_summaries"
```

- 手動檢視並調整 `app/db/migrations/versions/<rev>_*.py`（特別注意複雜的 schema 或資料遷移步驟）。

- 套用 migration（在本機或目標資料庫）：

```powershell
uv run alembic upgrade head
```

## 🛠️ Windows 批次檔說明

專案包含以下批次檔方便 Windows 用戶使用：

- `setup.bat` - 完整設定（安裝依賴、初始化資料庫）
- `start_dev.bat` - 啟動開發伺服器
- `test.bat` - 執行測試
- `install_pip.bat` - 使用 pip 安裝依賴

## 📂 專案結構說明

```
line-group-rag/
├── app/                    # 主應用程式
│   ├── api/               # API 端點
│   ├── agents/            # LangChain Agents
│   ├── tools/             # Agent 工具集
│   ├── models/            # 資料庫模型
│   ├── schemas/           # Pydantic schemas
│   ├── services/          # 商業邏輯
│   └── repositories/      # 資料存取層
├── config/                # 設定檔
├── scripts/               # 工具腳本
├── tests/                 # 測試檔案
├── data/                  # 資料目錄
├── logs/                  # 日誌目錄
└── docs/                  # 文檔
```

## ⚠️ 注意事項

1. **Python 版本**: 需要 Python 3.11 或更高版本
2. **資料庫**: 確保 PostgreSQL 和 Qdrant 正在執行
3. **API Key**: 記得在 .env 中設定 OpenAI API Key
4. **防火牆**: 可能需要允許 localhost:8200 和 6333 端口

## 🆘 常見問題

### Q: PostgreSQL 連線失敗

A: 檢查 PostgreSQL 服務是否啟動，並確認 .env 中的連線字串正確

### Q: Qdrant 連線失敗

A: 確認 Docker Desktop 已啟動，且 Qdrant 容器正在執行

### Q: 找不到 uv 指令

A: 重新開啟 PowerShell 或手動將 uv 加入 PATH

### Q: pip install 失敗

A: 嘗試使用管理員權限執行，或建立虛擬環境：

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## 📝 補充說明

此專案遵循您的架構規格：

- ✅ 基於 LangChain 1.0.x
- ✅ 五層架構設計
- ✅ 單一 Agent + 多 Tool 設計
- ✅ 包含 requirements.txt
- ✅ 適用於 Windows 11 環境

---

如有任何問題，請參考專案中的 `docs/` 目錄或查看 API 文檔。
