# RAG System Backend

A professional RAG (Retrieval-Augmented Generation) system built with FastAPI, LangChain, and modern Python technologies.

## 🚀 Features

- **Advanced RAG Query System** with LangChain LCEL patterns
- **Chat System** with conversation management and streaming responses
- **Vector Database Integration** with Chroma and similarity search
- **Document Processing** supporting multiple formats (PDF, DOCX, TXT, etc.)
- **Web Scraping** capabilities for URL-based content
- **Query Optimization** with caching and result ranking
- **Comprehensive Testing** with 44+ test cases

## 📋 Requirements

- Python 3.9+
- OpenAI API key (for embeddings and LLM)
- PostgreSQL (for relational data)
- Redis (for caching and background tasks)

## 🛠️ Installation

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Run database migrations:**
   ```bash
   alembic upgrade head
   ```

## 🧪 Testing

### Quick Test Run (Recommended)

Use the provided test runner scripts that suppress dependency warnings for cleaner output:

**Linux/macOS:**
```bash
# Run all tests
./run_tests.sh

# Run specific test file
./run_tests.sh tests/test_rag_service.py

# Run specific test
./run_tests.sh tests/test_advanced_rag_features.py::TestQueryCache::test_cache_initialization
```

**Windows:**
```cmd
# Run all tests
run_tests.bat

# Run specific test file
run_tests.bat tests/test_rag_service.py
```

### Manual Test Run

If you prefer to run tests manually:

```bash
# With warnings suppressed (recommended)
PYTHONWARNINGS=ignore python -m pytest tests/ -v

# With all output (including warnings)
python -m pytest tests/ -v

# Run specific test categories
python -m pytest tests/ -v -m "not slow"  # Skip slow tests
python -m pytest tests/ -v -m "unit"      # Run only unit tests
```

### Test Categories

- **Unit Tests**: Fast, isolated tests for individual components
- **Integration Tests**: Tests that verify component interactions
- **Slow Tests**: Tests that may take longer (marked with `@pytest.mark.slow`)

## 📁 Project Structure

```
backend/
├── app/
│   ├── api/v1/          # API endpoints
│   ├── core/            # Core configuration and utilities
│   ├── models/          # Database models
│   └── services/        # Business logic services
├── tests/               # Test files
├── requirements.txt     # Python dependencies
├── pytest.ini         # Pytest configuration
├── pyproject.toml      # Project configuration
└── run_tests.sh        # Test runner script
```

## 🔧 Configuration

The project uses modern Python configuration standards:

- **pytest.ini**: Test configuration and warning filters
- **pyproject.toml**: Project metadata and tool configurations
- **requirements.txt**: Pinned dependency versions for stability

## 🐛 Troubleshooting

### Pydantic Warnings

If you see deprecation warnings from Pydantic v1, use the provided test runner scripts or set the environment variable:

```bash
export PYTHONWARNINGS=ignore
```

### Dependency Issues

Make sure you're using the specified versions in `requirements.txt`. The versions are pinned to ensure compatibility with Python 3.13 and modern LangChain.

## 🚀 Running the Application

```bash
# Development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Production server
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

## 📚 API Documentation

Once the server is running, visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## 🤝 Contributing

1. Run tests before submitting changes:
   ```bash
   ./run_tests.sh
   ```

2. Follow the code style:
   ```bash
   black app/ tests/
   isort app/ tests/
   flake8 app/ tests/
   ```

3. Add tests for new features

## 📄 License

This project is licensed under the MIT License.