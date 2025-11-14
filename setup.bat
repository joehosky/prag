@echo off
echo Setting up LINE Group RAG System...
echo.
echo Installing dependencies with uv...
uv sync
echo.
echo Copying environment file...
copy .env.example .env
echo.
echo Initializing database...
uv run python scripts\init_db.py
echo.
echo Initializing Qdrant...
uv run python scripts\init_qdrant.py
echo.
echo Setup complete! Please edit .env file with your configuration.
pause
