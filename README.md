# RAG System

A professional RAG (Retrieval-Augmented Generation) system built with LangChain and Vue.js.

## Architecture

- **Frontend**: Vue.js 3 with TypeScript and shadcn/ui components
- **Backend**: FastAPI with async support
- **Database**: PostgreSQL for relational data
- **Vector Database**: Chroma for embeddings
- **Cache**: Redis for caching and background tasks
- **Authentication**: JWT-based authentication
- **ID Generation**: Snowflake algorithm for distributed unique IDs

## Features

- Document upload and processing (PDF, DOCX, TXT, MD, PPTX, XLSX, CSV, RTF)
- Web page scraping with intelligent crawling
- Vector-based document search and retrieval
- Chat interface with source citations
- Real-time processing status updates
- Comprehensive error handling and monitoring

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+
- Node.js 18+

### Development Setup

1. Clone the repository:
```bash
git clone <repository-url>
cd rag-system
```

2. Copy environment configuration:
```bash
cp backend/.env.example backend/.env
```

3. Start the development environment:
```bash
docker-compose up -d
```

4. Run database migrations:
```bash
cd backend
alembic upgrade head
```

5. Access the application:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/api/v1/docs

## Project Structure

```
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/            # API routes
│   │   ├── core/           # Core functionality
│   │   ├── models/         # SQLAlchemy models
│   │   ├── schemas/        # Pydantic schemas
│   │   └── main.py         # Application entry point
│   ├── alembic/            # Database migrations
│   ├── tests/              # Test files
│   └── requirements.txt    # Python dependencies
├── frontend/               # Vue.js frontend (placeholder)
├── docker-compose.yml      # Development environment
└── README.md              # This file
```

## API Endpoints

### Authentication
- `POST /api/v1/auth/register` - User registration
- `POST /api/v1/auth/login` - User login
- `POST /api/v1/auth/token` - OAuth2 token endpoint

### Documents
- `GET /api/v1/documents/` - List documents
- `POST /api/v1/documents/` - Upload document
- `GET /api/v1/documents/{id}` - Get document details
- `DELETE /api/v1/documents/{id}` - Delete document

### Chat
- `GET /api/v1/chat/sessions` - List chat sessions
- `POST /api/v1/chat/sessions` - Create chat session
- `POST /api/v1/chat/sessions/{id}/messages` - Send message
- `GET /api/v1/chat/sessions/{id}/messages` - Get messages

### Admin
- `GET /api/v1/admin/users` - List users (admin only)
- `GET /api/v1/admin/stats` - System statistics (admin only)

## Database Schema

The system uses Snowflake IDs (64-bit integers) for all primary keys to ensure distributed uniqueness.

### Key Tables
- `users` - User authentication and profiles
- `documents` - Document metadata and processing status
- `document_chunks` - Text chunks with vector references
- `chat_sessions` - Chat conversation sessions
- `chat_messages` - Individual chat messages with sources

## Development

### Backend Development

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Running Tests

```bash
cd backend
pytest
```

### Database Migrations

```bash
cd backend
alembic revision --autogenerate -m "Description"
alembic upgrade head
```

## Configuration

Key environment variables:

- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `SECRET_KEY` - JWT secret key
- `OPENAI_API_KEY` - OpenAI API key (for embeddings/LLM)
- `DEBUG` - Enable debug mode

See `backend/.env.example` for full configuration options.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License.# VinceRAG
