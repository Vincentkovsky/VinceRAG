# RAG System Frontend

A modern Vue.js 3 frontend for the RAG (Retrieval-Augmented Generation) system, built with TypeScript and shadcn/ui components.

## Features

- **Document Management**: Upload and manage various document formats (PDF, DOCX, TXT, MD, PPTX, XLSX, CSV, RTF)
- **Web Content Processing**: Add and crawl web pages with configurable options
- **Intelligent Chat**: Ask questions about your documents with streaming responses
- **Modern UI**: Built with shadcn/ui components and Tailwind CSS
- **Responsive Design**: Works on desktop, tablet, and mobile devices
- **Real-time Updates**: Live progress tracking for document processing
- **Type Safety**: Full TypeScript support throughout the application

## Tech Stack

- **Vue.js 3** with Composition API
- **TypeScript** for type safety
- **Pinia** for state management
- **Vue Router** for navigation
- **Tailwind CSS** for styling
- **shadcn/ui** for UI components
- **Axios** for API communication
- **Vite** for build tooling

## Getting Started

### Prerequisites

- Node.js 18+ 
- npm or yarn

### Installation

1. Install dependencies:
```bash
npm install
```

2. Copy environment configuration:
```bash
cp .env.example .env
```

3. Update the `.env` file with your API endpoint:
```env
VITE_API_BASE_URL=http://localhost:8000/api
```

### Development

Start the development server:
```bash
npm run dev
```

The application will be available at `http://localhost:3000`.

### Building for Production

Build the application:
```bash
npm run build
```

Preview the production build:
```bash
npm run preview
```

## Project Structure

```
src/
├── api/           # API client and service modules
├── assets/        # Static assets and global styles
├── components/    # Reusable Vue components
│   ├── ui/        # shadcn/ui base components
│   ├── documents/ # Document management components
│   └── chat/      # Chat interface components
├── lib/           # Utility functions
├── router/        # Vue Router configuration
├── stores/        # Pinia stores
├── types/         # TypeScript type definitions
├── views/         # Page components
└── main.ts        # Application entry point
```

## Key Components

### Document Management
- **DocumentUpload**: Drag-and-drop file upload with progress tracking
- **DocumentList**: Searchable, filterable document list with status indicators
- **UrlInput**: Web URL processing with crawling options

### Chat Interface
- **ChatInput**: Message input with quick actions and document filtering
- **Message display**: Streaming responses with source citations

### State Management
- **documentsStore**: Document and chunk management
- **chatStore**: Chat messages and session handling
- **appStore**: Global application state and notifications

## API Integration

The frontend communicates with the backend API through:

- **Document API**: Upload, list, delete documents and chunks
- **Chat API**: Send messages and receive responses with sources
- **Streaming**: Real-time message streaming via Server-Sent Events

## Configuration

Environment variables in `.env`:

- `VITE_API_BASE_URL`: Backend API endpoint
- `VITE_ENABLE_STREAMING`: Enable streaming chat responses
- `VITE_ENABLE_WEB_SCRAPING`: Enable web content processing
- `VITE_MAX_FILE_SIZE`: Maximum file upload size in bytes

## Development Guidelines

### Component Structure
- Use Composition API with `<script setup>`
- Implement proper TypeScript typing
- Follow shadcn/ui component patterns
- Use Pinia stores for state management

### Styling
- Use Tailwind CSS utility classes
- Follow shadcn/ui design system
- Implement responsive design patterns
- Support both light and dark themes

### Error Handling
- Use try-catch blocks for async operations
- Display user-friendly error messages
- Implement proper loading states
- Handle network connectivity issues

## Contributing

1. Follow the existing code style and patterns
2. Add TypeScript types for new features
3. Test components thoroughly
4. Update documentation as needed

## License

This project is part of the RAG System and follows the same license terms.