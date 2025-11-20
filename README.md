# LINE Group RAG System

基於 LangChain 1.0.x 的 LINE 群組對話 RAG 系統

## 🚀 快速開始 (Windows 11)

### 環境需求

- Windows 11
- Python 3.11+
- PostgreSQL 15+
- Qdrant Vector Database

### 安裝步驟

1. **安裝 Python 3.11+**

   ```powershell
   # 從 Microsoft Store 安裝或從 python.org 下載
   python --version  # 確認版本
   ```

2. **安裝 uv (Package Manager)**

   ```powershell
   # 使用 PowerShell 安裝
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

3. **安裝 PostgreSQL**

   - 下載: https://www.postgresql.org/download/windows/
   - 安裝時記住設定的密碼

4. **安裝 Qdrant**
   ```powershell
   # 使用 Docker Desktop for Windows
   docker pull qdrant/qdrant
   docker run -p 6333:6333 qdrant/qdrant
   ```

### 專案設定

1. **執行設定腳本**

   ```powershell
   python setup_complete.py
   cd line-group-rag
   ```

2. **設定環境變數**

   ```powershell
   copy .env.example .env
   # 使用記事本或 VSCode 編輯 .env 填入您的設定
   notepad .env
   ```

3. **安裝依賴**

   ```powershell
   # 安裝 uv
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

   # 安裝專案依賴
   uv sync
   ```

4. **初始化資料庫（使用 Alembic 管理 schema，建議流程）**

   ```powershell
   # 初始化 PostgreSQL 表格
   python scripts\init_db.py

   # 初始化 Qdrant 集合
   python scripts\init_qdrant.py
   ```

   使用 Alembic 來管理資料表結構：

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

   - 若你在本機或測試環境只是要快速建立表，也可以在暫時情況下使用 `create_all()`（不推薦作為長期做法）。

   - 如有建立新的 model，記得加入該 model 到 models 目錄下的 **init**.py，以免 relationship 無法正確建立。

5. **啟動服務**

   ```powershell
   # 開發模式（建議使用批次檔，它會在啟動前自動套用 migrations）
   start_dev.bat

   # 或直接手動啟動（若你想手動控制 migrations）：
   uv run alembic upgrade head
   uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8200
   ```

## 📚 API 文檔

啟動服務後訪問：

- Swagger UI: http://localhost:8200/docs
- ReDoc: http://localhost:8200/redoc

## 🧪 測試

```powershell
# 執行所有測試
uv run pytest

# 測試覆蓋率
uv run pytest --cov=app tests/

# 或使用批次檔
test.bat
```

## 📖 專案結構

- `app/` - 主應用程式
  - `api/` - API 路由
  - `agents/` - LangChain Agents
  - `tools/` - Agent 工具
  - `models/` - 資料庫模型
  - `schemas/` - Pydantic schemas
  - `services/` - 商業邏輯
  - `repositories/` - 資料存取層
- `config/` - 設定檔
- `scripts/` - 工具腳本
- `tests/` - 測試檔案
- `docs/` - 文檔

## 🗄️ Logging Configuration

配置 logging 設定（console 與 file）

```
# 根日誌等級
LOG_LEVEL=INFO

# 是否輸出到 console (true|false)
LOG_CONSOLE=true
# console 專用等級 (若空則使用 LOG_LEVEL)
LOG_CONSOLE_LEVEL=

# 是否輸出到檔案 (true|false)
LOG_FILE=true
# 檔案日誌等級 (若空則使用 LOG_LEVEL)
LOG_FILE_LEVEL=DEBUG

# 日誌檔案根目錄 (預設: logs)
LOG_DIR=logs

# 日誌保留天數 (預設: 7)
LOG_RETENTION_DAYS=14
```

行為說明：

- 當 `LOG_FILE=true` 時，日誌會寫到 `logs/YYYY-MM-DD/HH.log`（以日期為資料夾、以小時為檔案）。
- `LOG_RETENTION_DAYS` 決定會刪除多少天以前的日誌資料夾。
- 建議在開發環境把 `LOG_CONSOLE=true`、`LOG_LEVEL=DEBUG`；在 production 把 `LOG_FILE=true` 並將 `LOG_CONSOLE=false`。

## 📝 License

MIT License
