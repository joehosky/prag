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
   # 使用 uv (推薦)
   uv sync
   
   # 或使用 pip
   pip install -r requirements.txt
   ```

4. **初始化資料庫**
   ```powershell
   uv run python scripts\init_db.py
   uv run python scripts\init_qdrant.py
   ```

5. **啟動服務**
   ```powershell
   # 開發模式（支援 auto-reload）
   uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   
   # 或使用批次檔
   start_dev.bat
   ```

## 📚 API 文檔

啟動服務後訪問：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

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

## 📝 License

MIT License
