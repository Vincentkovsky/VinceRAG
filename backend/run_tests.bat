@echo off
REM RAG System Test Runner for Windows
REM This script runs tests with warnings suppressed for cleaner output

echo 🧪 Running RAG System Tests...
echo ================================

REM Set environment variable to suppress warnings
set PYTHONWARNINGS=ignore

REM Run tests with clean output
if "%~1"=="" (
    echo Running all tests...
    python -m pytest tests/ -v --tb=short
) else (
    echo Running specific tests: %*
    python -m pytest %* -v --tb=short
)

echo ================================
echo ✅ Test run completed!
pause