#!/usr/bin/env python3
"""
LINE Group RAG System - Complete Project Setup Script for Windows 11
自動建立完整專案目錄結構和所有檔案
執行方式: python setup_complete.py
"""

import os
import sys
from pathlib import Path


def create_project_structure():
    """建立專案目錄結構"""

    # 專案根目錄
    base_dir = Path("line-group-rag")

    # 建立目錄結構
    directories = [
        # app 主目錄
        "app",
        "app/api",
        "app/api/v1",
        "app/api/v1/routers",
        # 核心模組
        "app/core",
        "app/db",
        "app/db/migrations",
        "app/db/migrations/versions",
        # 資料模型
        "app/models",
        "app/schemas",
        "app/services",
        "app/repositories",
        # Agent 和工具
        "app/agents",
        "app/tools",
        "app/tools/retrieval",
        "app/tools/analysis",
        "app/tools/extraction",
        "app/tools/formatting",
        "app/tool_schemas",
        # RAG 元件
        "app/rag",
        "app/rag/chains",
        "app/rag/retrievers",
        # Prompts
        "app/prompts",
        "app/prompts/agent_prompts",
        "app/prompts/tool_prompts",
        # 其他功能模組
        "app/orchestration",
        "app/embeddings",
        "app/vector_store",
        "app/search",
        "app/parsers",
        "app/utils",
        # 腳本
        "scripts",
        # 測試
        "tests",
        "tests/unit",
        "tests/unit/test_agents",
        "tests/unit/test_tools",
        "tests/unit/test_embeddings",
        "tests/unit/test_parsers",
        "tests/unit/test_search",
        "tests/unit/test_services",
        "tests/unit/test_api",
        "tests/integration",
        "tests/integration/test_api",
        "tests/integration/test_rag_pipeline",
        "tests/integration/test_vector_store",
        "tests/fixtures",
        "tests/fixtures/sample_excel",
        # 設定檔
        "config",
        # 資料和日誌
        "data",
        "data/uploads",
        "data/processed",
        "data/indexes",
        "logs",
        # 文檔
        "docs",
    ]

    # 建立所有目錄
    for dir_path in directories:
        full_path = base_dir / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        print(f"✓ Created directory: {full_path}")

    return base_dir


def get_all_files():
    """取得所有要建立的檔案內容"""

    files = {
        # ========== 根目錄檔案 ==========
        ".env.example": """# LINE Group RAG System - Environment Variables

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/line_rag_db
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# Qdrant Vector Database
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_COLLECTION_NAME=line_messages
QDRANT_API_KEY=

# OpenAI API
OPENAI_API_KEY=your_api_key_here
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small

# Application
APP_ENV=development
APP_HOST=127.0.0.1
APP_PORT=8200
APP_RELOAD=true

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Security
SECRET_KEY=your_secret_key_here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# File Upload
MAX_UPLOAD_SIZE=104857600  # 100MB
ALLOWED_EXTENSIONS=xlsx,xls,csv

# BM25 Index
BM25_INDEX_PATH=data/indexes/bm25_index.pkl
BM25_K1=1.5
BM25_B=0.75

# Score Fusion Weights
SCORE_WEIGHT_ALPHA=0.5  # Cosine similarity weight
SCORE_WEIGHT_BETA=0.3   # BM25 weight
SCORE_WEIGHT_GAMMA=0.2  # Recency boost weight
SCORE_THRESHOLD=0.3     # Minimum score threshold

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=3600  # 1 hour in seconds
""",
        ".gitignore": """# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
env/
venv/
ENV/
env.bak/
venv.bak/
.venv/

# IDEs
.idea/
.vscode/
*.swp
*.swo
*~
.DS_Store
Thumbs.db

# Environment variables
.env
.env.local
.env.*.local

# Logs
logs/
*.log

# Data
data/uploads/*
data/processed/*
data/indexes/*
!data/uploads/.gitkeep
!data/processed/.gitkeep
!data/indexes/.gitkeep

# Database
*.db
*.sqlite
*.sqlite3

# Jupyter Notebook
.ipynb_checkpoints

# pyenv
.python-version

# uv
.venv/

# pytest
.pytest_cache/
htmlcov/
.coverage
coverage.xml
""",
        "pyproject.toml": """[project]
name = "line-group-rag"
version = "0.1.0"
description = "LINE Group RAG System with LangChain 1.0.x"
readme = "README.md"
requires-python = ">=3.11"

dependencies = [
    "fastapi>=0.110.0",
    "uvicorn[standard]>=0.29.0",
    "python-multipart>=0.0.9",
    "python-dotenv>=1.0.0",
    "sqlalchemy>=2.0.28",
    "alembic>=1.13.1",
    "psycopg2-binary>=2.9.9",
    "asyncpg>=0.29.0",
    "qdrant-client>=1.8.0",
    "langchain>=1.0.0",
    "langchain-openai>=1.0.0",
    "langchain-community>=0.3.0,<1.0.0",
    "langgraph>=0.0.30",
    "openai>=1.12.0",
    "pandas>=2.2.0",
    "openpyxl>=3.1.2",
    "numpy>=1.26.0",
    "tiktoken>=0.6.0",
    "rank-bm25>=0.2.2",
    "jieba>=0.42.1",
    "pydantic>=2.6.0",
    "pydantic-settings>=2.2.0",
    "redis>=5.0.1",
    "httpx>=0.27.0",
    "tenacity>=8.2.3",
    "structlog>=24.1.0",
    "pyyaml>=6.0.1",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-cov>=4.1.0",
    "black>=24.2.0",
    "isort>=5.13.0",
    "flake8>=7.0.0",
    "mypy>=1.8.0",
    "pre-commit>=3.6.0",
    "ipython>=8.20.0",
]

[build-system]
requires = ["setuptools>=69.0.0", "wheel"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["app*", "config*"]
exclude = ["tests*", "data*", "logs*", "scripts*"]

[tool.black]
line-length = 88
target-version = ['py311']

[tool.isort]
profile = "black"
line_length = 88

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-v --tb=short"

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
ignore_missing_imports = true
fastapi==0.110.0
uvicorn[standard]==0.29.0
python-multipart==0.0.9
python-dotenv==1.0.0

# Database
sqlalchemy==2.0.28
alembic==1.13.1
psycopg2-binary==2.9.9
asyncpg==0.29.0

# Vector Database
qdrant-client==1.8.0

# LangChain Ecosystem (1.0.x)
langchain==1.0.0
langchain-openai==1.0.0
langchain-community==1.0.0
langgraph==0.0.30

# AI/ML
openai==1.12.0
tiktoken==0.6.0
numpy==1.26.0

# Data Processing
pandas==2.2.0
openpyxl==3.1.2

# Search
rank-bm25==0.2.2
jieba==0.42.1  # Chinese text segmentation

# API & Validation
pydantic==2.6.0
pydantic-settings==2.2.0

# Utilities
redis==5.0.1
httpx==0.27.0
tenacity==8.2.3
structlog==24.1.0
pyyaml==6.0.1

# Development (optional)
pytest==8.0.0
pytest-asyncio==0.23.0
pytest-cov==4.1.0
black==24.2.0
isort==5.13.0
flake8==7.0.0
mypy==1.8.0
pre-commit==3.6.0
ipython==8.20.0
""",
        "README.md": """# LINE Group RAG System

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
   # 使用 uv
   uv sync

   ```

4. **初始化資料庫**
   ```powershell
   uv run python scripts\\init_db.py
   uv run python scripts\\init_qdrant.py
   ```

5. **啟動服務**
   ```powershell
   # 開發模式（支援 auto-reload）
    uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8200

   # 或使用批次檔
   start_dev.bat
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

## 📝 License

MIT License
""",
        # ========== Windows 批次檔 ==========
        "start_dev.bat": """@echo off
echo Starting LINE Group RAG System (Development Mode)...
echo.
python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8200
pause
""",
        "setup.bat": """@echo off
echo Setting up LINE Group RAG System...
echo.
echo Installing dependencies with uv...
uv sync
echo.
echo Copying environment file...
copy .env.example .env
echo.
echo Initializing database...
uv run python scripts\\init_db.py
echo.
echo Initializing Qdrant...
uv run python scripts\\init_qdrant.py
echo.
echo Setup complete! Please edit .env file with your configuration.
pause
""",
        "test.bat": """@echo off
echo Running tests...
uv run pytest
pause
""",
        # ========== App 主檔案 ==========
        "app/__init__.py": '"""LINE Group RAG System - Main Application Package"""',
        "app/main.py": '''"""
FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.endpoints import router as api_router

# Create FastAPI instance
app = FastAPI(
    title="LINE Group RAG System",
    description="RAG system for LINE group chat analysis",
    version="0.1.0",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(api_router, prefix="/api/v1")

@app.get("/")
async def root():
    return {"message": "LINE Group RAG System API", "version": "0.1.0"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
''',
        # ========== Core 設定 ==========
        "app/core/config.py": '''"""
Application Configuration
"""
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://user:password@localhost:5432/line_rag_db"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection_name: str = "line_messages"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"

    # Application
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8200

    # Score Fusion Weights
    score_weight_alpha: float = 0.5  # Cosine similarity
    score_weight_beta: float = 0.3   # BM25
    score_weight_gamma: float = 0.2  # Recency boost
    score_threshold: float = 0.3

    class Config:
        env_file = ".env"

settings = Settings()
''',
        # ========== API 端點 ==========
        "app/api/v1/endpoints.py": '''"""
API v1 Router Registration
"""
from fastapi import APIRouter
from app.api.v1.routers import messages, query, groups, health

router = APIRouter()

router.include_router(messages.router, prefix="/messages", tags=["messages"])
router.include_router(query.router, prefix="/query", tags=["query"])
router.include_router(groups.router, prefix="/groups", tags=["groups"])
router.include_router(health.router, prefix="/health", tags=["health"])
''',
        "app/api/v1/routers/health.py": '''"""
Health Check Endpoint
"""
from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def health_check():
    return {"status": "healthy", "service": "LINE Group RAG System"}
''',
        "app/api/v1/routers/messages.py": '''"""
Messages Upload Router
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from typing import Optional

router = APIRouter()

@router.post("/")
async def upload_excel(
    file: UploadFile = File(...),
    group_name: Optional[str] = None
):
    """Upload LINE group Excel file (messages router template)"""
    # Validate file extension
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files are supported")

    # TODO: Implement upload logic
    return {
        "status": "success",
        "message": f"File {file.filename} uploaded successfully",
        "group_name": group_name
    }
''',
        "app/api/v1/routers/query.py": '''"""
RAG Query Router
"""
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, Dict

router = APIRouter()

class QueryRequest(BaseModel):
    group_id: str
    question: str
    search_type: str = "hybrid"
    top_k: int = 50

class QueryResponse(BaseModel):
    answer: str
    confidence: float
    metadata: Optional[Dict] = None

@router.post("/", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """Execute RAG query"""
    # TODO: Implement query logic
    return QueryResponse(
        answer="This is a placeholder response for your query.",
        confidence=0.95,
        metadata={"query": request.question}
    )
''',
        "app/api/v1/routers/groups.py": '''"""
LINE Groups Management Router
"""
from fastapi import APIRouter
from typing import List, Dict

router = APIRouter()

@router.get("/", response_model=List[Dict])
async def list_groups():
    """List all LINE groups"""
    # TODO: Implement groups listing
    return [
        {"id": "1", "name": "Sample Group 1"},
        {"id": "2", "name": "Sample Group 2"}
    ]

@router.get("/{group_id}")
async def get_group(group_id: str):
    """Get specific group details"""
    # TODO: Implement group details
    return {
        "id": group_id,
        "name": f"Group {group_id}",
        "message_count": 0
    }
''',
        # ========== 資料庫相關 ==========
        "app/db/base.py": '''"""
SQLAlchemy Base Class
"""
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
''',
        "app/db/session.py": '''"""
Database Session Management
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
''',
        # ========== 腳本 ==========
        "scripts/init_db.py": '''"""
Initialize PostgreSQL Database
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from app.db.base import Base
from app.core.config import settings

def init_database():
    """Initialize database tables"""
    print("Initializing database...")
    print(f"Database URL: {settings.database_url}")

    try:
        engine = create_engine(settings.database_url)
        Base.metadata.create_all(bind=engine)
        print("✓ Database initialized successfully!")
    except Exception as e:
        print(f"✗ Error initializing database: {e}")
        print("Please make sure PostgreSQL is running and credentials are correct.")
        return False

    return True

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
''',
        "scripts/init_qdrant.py": '''"""
Initialize Qdrant Vector Database
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from app.core.config import settings

def init_qdrant():
    """Initialize Qdrant collections"""
    print("Initializing Qdrant...")
    print(f"Qdrant host: {settings.qdrant_host}:{settings.qdrant_port}")

    try:
        client = QdrantClient(
            host=settings.qdrant_host,
            port=settings.qdrant_port
        )

        # Create collection for LINE messages
        collection_name = settings.qdrant_collection_name

        # Check if collection exists
        collections = client.get_collections()
        if any(col.name == collection_name for col in collections.collections):
            print(f"Collection '{collection_name}' already exists")
            client.delete_collection(collection_name=collection_name)
            print(f"Deleted existing collection '{collection_name}'")

        # Create new collection
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=1536,  # OpenAI embedding dimension
                distance=Distance.COSINE
            ),
        )
        print(f"✓ Qdrant collection '{collection_name}' initialized successfully!")

    except Exception as e:
        print(f"✗ Error initializing Qdrant: {e}")
        print("Please make sure Qdrant is running.")
        return False

    return True

if __name__ == "__main__":
    success = init_qdrant()
    sys.exit(0 if success else 1)
''',
        # ========== Agent 配置 ==========
        "config/agent_config.yaml": """# Agent Configuration
agent:
  model: "gpt-4o-mini"
  temperature: 0.1
  max_iterations: 10

system_prompt:
  role: "LINE 群組對話分析專家"
  capabilities:
    - 時間範圍查詢
    - 統計分析
    - 主題萃取
    - 趨勢分析

tools:
  date_range_search:
    enabled: true
    max_range_days: 365

  statistics_analysis:
    enabled: true
    min_data_points: 5

  semantic_qa:
    enabled: true
    context_window: 4000

execution:
  timeout: 30
  parallel_limit: 3
  cache_enabled: true
""",
        # ========== 測試配置 ==========
        "tests/conftest.py": '''"""
Pytest Configuration
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)
''',
        "tests/unit/test_api/test_health.py": '''"""
Test Health Endpoint
"""

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/api/v1/health/")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_root_endpoint(client):
    """Test root endpoint"""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()
''',
    }

    return files


def create_files(base_dir, files):
    """建立所有檔案"""
    for file_path, content in files.items():
        full_path = base_dir / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text(content, encoding="utf-8")
        print(f"✓ Created file: {full_path}")


def create_init_files(base_dir):
    """建立所有 __init__.py 檔案"""
    init_files = [
        "app/api/__init__.py",
        "app/api/v1/__init__.py",
        "app/api/v1/routers/__init__.py",
        "app/core/__init__.py",
        "app/db/__init__.py",
        "app/db/migrations/__init__.py",
        "app/models/__init__.py",
        "app/schemas/__init__.py",
        "app/services/__init__.py",
        "app/repositories/__init__.py",
        "app/agents/__init__.py",
        "app/tools/__init__.py",
        "app/tools/retrieval/__init__.py",
        "app/tools/analysis/__init__.py",
        "app/tools/extraction/__init__.py",
        "app/tools/formatting/__init__.py",
        "app/tool_schemas/__init__.py",
        "app/rag/__init__.py",
        "app/rag/chains/__init__.py",
        "app/rag/retrievers/__init__.py",
        "app/prompts/__init__.py",
        "app/prompts/agent_prompts/__init__.py",
        "app/prompts/tool_prompts/__init__.py",
        "app/orchestration/__init__.py",
        "app/embeddings/__init__.py",
        "app/vector_store/__init__.py",
        "app/search/__init__.py",
        "app/parsers/__init__.py",
        "app/utils/__init__.py",
        "scripts/__init__.py",
        "tests/__init__.py",
        "tests/unit/__init__.py",
        "tests/unit/test_api/__init__.py",
        "tests/integration/__init__.py",
        "tests/fixtures/__init__.py",
        "config/__init__.py",
    ]

    for init_file in init_files:
        full_path = base_dir / init_file
        full_path.parent.mkdir(parents=True, exist_ok=True)
        full_path.write_text('"""Package initialization"""', encoding="utf-8")
        print(f"✓ Created init: {full_path}")


def create_gitkeep_files(base_dir):
    """建立 .gitkeep 檔案保持空目錄"""
    gitkeep_dirs = [
        "data/uploads",
        "data/processed",
        "data/indexes",
        "logs",
        "tests/fixtures/sample_excel",
        "app/db/migrations/versions",
        "docs",
    ]

    for gitkeep_dir in gitkeep_dirs:
        gitkeep_path = base_dir / gitkeep_dir / ".gitkeep"
        gitkeep_path.parent.mkdir(parents=True, exist_ok=True)
        gitkeep_path.write_text("", encoding="utf-8")
        print(f"✓ Created .gitkeep: {gitkeep_path}")


def main():
    """主程式"""
    print("=" * 70)
    print("   LINE Group RAG System - Complete Project Setup")
    print("   For Windows 11 Environment")
    print("=" * 70)
    print()

    try:
        # 檢查是否已存在專案目錄
        base_dir = Path("line-group-rag")
        if base_dir.exists():
            response = input(
                f"⚠️  Directory '{base_dir}' already exists. Overwrite? (y/n): "
            )
            if response.lower() != "y":
                print("Setup cancelled.")
                return

        # 建立專案結構
        print("📁 Creating project structure...")
        create_project_structure()

        # 取得所有檔案內容
        files = get_all_files()

        # 建立檔案
        print("\n📝 Creating project files...")
        create_files(base_dir, files)

        # 建立 __init__.py 檔案
        print("\n📦 Creating package files...")
        create_init_files(base_dir)

        # 建立 .gitkeep 檔案
        print("\n📌 Creating placeholder files...")
        create_gitkeep_files(base_dir)

        print("\n" + "=" * 70)
        print("   ✅ Project setup completed successfully!")
        print("=" * 70)
        print("\n📋 Next steps:\n")
        print("1. Navigate to project directory:")
        print("   cd line-group-rag\n")

        print("2. Edit environment configuration:")
        print("   notepad .env")
        print("   (Add your OpenAI API key and database credentials)\n")

        print("3. Install dependencies:")
        print("   Using uv")
        print("   uv sync")

        print("4. Start PostgreSQL and Qdrant services\n")

        print("5. Initialize databases:")
        print("   uv run python scripts\\init_db.py")
        print("   uv run python scripts\\init_qdrant.py\n")

        print("6. Start development server:")
        print("   uv run uvicorn app.main:app --reload")
        print("   Or use: start_dev.bat\n")

        print("📚 API Documentation will be available at:")
        print("   http://localhost:8200/docs\n")

        print("🔧 For Windows users, batch files are available:")
        print("   - setup.bat: Complete setup with dependencies")
        print("   - start_dev.bat: Start development server")
        print("   - test.bat: Run tests")
        print("   - install_pip.bat: Install with pip")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
