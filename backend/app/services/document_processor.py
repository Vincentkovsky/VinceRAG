"""
Document processing pipeline service
"""

import os
import asyncio
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession
from langchain_text_splitters import RecursiveCharacterTextSplitter

from .text_extraction import TextExtractor, TextExtractionError
from ..models.document import Document, DocumentChunk
from ..core.database import get_db
from ..core.snowflake import generate_id


class DocumentProcessingError(Exception):
    """Custom exception for document processing errors"""
    pass


class DocumentProcessor:
    """Service for processing documents through the complete pipeline"""
    
    def __init__(self, storage_path: str = "storage/documents"):
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        self.text_extractor = TextExtractor()
        
        # Configure text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )
    
    async def process_document(self, document_id: int, file_path: str) -> Dict[str, Any]:
        """
        Process a document through the complete pipeline
        
        Args:
            document_id: Document ID from database
            file_path: Path to the uploaded file
            
        Returns:
            Processing result with statistics
        """
        try:
            # Get database session
            async for db in get_db():
                # Get document from database
                document = await self._get_document(db, document_id)
                if not document:
                    raise DocumentProcessingError(f"Document {document_id} not found")
                
                # Update status to processing
                await self._update_document_status(db, document, "processing", "Starting text extraction")
                
                # Extract text
                extraction_result = await self._extract_text(file_path, document.type)
                
                # Update status
                await self._update_document_status(db, document, "processing", "Text extracted, creating chunks")
                
                # Create chunks
                chunks = await self._create_chunks(extraction_result['text'])
                
                # Update status
                await self._update_document_status(db, document, "processing", f"Created {len(chunks)} chunks, storing in database")
                
                # Store chunks in database
                chunk_records = await self._store_chunks(db, document_id, chunks)
                
                # Update document metadata
                await self._update_document_metadata(db, document, extraction_result, len(chunks))
                
                # Update final status
                await self._update_document_status(db, document, "completed", f"Processing completed with {len(chunks)} chunks")
                
                return {
                    'success': True,
                    'document_id': document_id,
                    'chunks_created': len(chunks),
                    'total_characters': len(extraction_result['text']),
                    'file_hash': extraction_result['file_hash'],
                    'metadata': extraction_result['metadata']
                }
                
        except Exception as e:
            # Update document status to failed
            try:
                async for db in get_db():
                    document = await self._get_document(db, document_id)
                    if document:
                        await self._update_document_status(db, document, "failed", str(e))
            except:
                pass  # Don't fail if we can't update status
            
            raise DocumentProcessingError(f"Failed to process document {document_id}: {str(e)}")
    
    async def _extract_text(self, file_path: str, file_type: str) -> Dict[str, Any]:
        """Extract text from file"""
        try:
            # Run text extraction in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                self.text_extractor.extract_text, 
                file_path, 
                file_type
            )
            return result
        except TextExtractionError as e:
            raise DocumentProcessingError(f"Text extraction failed: {str(e)}")
    
    async def _create_chunks(self, text: str) -> List[Dict[str, Any]]:
        """Create text chunks using LangChain splitter"""
        if not text.strip():
            raise DocumentProcessingError("No text content to chunk")
        
        try:
            # Run chunking in thread pool
            loop = asyncio.get_event_loop()
            chunks = await loop.run_in_executor(
                None,
                self.text_splitter.split_text,
                text
            )
            
            # Create chunk data with position information
            chunk_data = []
            current_pos = 0
            
            for i, chunk_text in enumerate(chunks):
                # Find the position of this chunk in the original text
                start_pos = text.find(chunk_text, current_pos)
                if start_pos == -1:
                    # Fallback: approximate position
                    start_pos = current_pos
                
                end_pos = start_pos + len(chunk_text)
                current_pos = end_pos
                
                # Estimate token count (rough approximation: 1 token ≈ 4 characters)
                token_count = len(chunk_text) // 4
                
                chunk_data.append({
                    'chunk_index': i,
                    'content': chunk_text,
                    'start_char': start_pos,
                    'end_char': end_pos,
                    'token_count': token_count
                })
            
            return chunk_data
            
        except Exception as e:
            raise DocumentProcessingError(f"Text chunking failed: {str(e)}")
    
    async def _store_chunks(self, db: AsyncSession, document_id: int, chunks: List[Dict[str, Any]]) -> List[DocumentChunk]:
        """Store chunks in database"""
        chunk_records = []
        
        try:
            for chunk_data in chunks:
                # Generate unique vector ID (same as chunk ID for consistency)
                chunk_id = generate_id()
                vector_id = str(chunk_id)
                
                chunk_record = DocumentChunk(
                    id=chunk_id,
                    document_id=document_id,
                    chunk_index=chunk_data['chunk_index'],
                    vector_id=vector_id,
                    content=chunk_data['content'],
                    start_char=chunk_data['start_char'],
                    end_char=chunk_data['end_char'],
                    token_count=chunk_data['token_count']
                )
                
                db.add(chunk_record)
                chunk_records.append(chunk_record)
            
            await db.commit()
            
            # Refresh all records to get generated fields
            for chunk in chunk_records:
                await db.refresh(chunk)
            
            return chunk_records
            
        except Exception as e:
            await db.rollback()
            raise DocumentProcessingError(f"Failed to store chunks: {str(e)}")
    
    async def _get_document(self, db: AsyncSession, document_id: int) -> Optional[Document]:
        """Get document from database"""
        from sqlalchemy import select
        result = await db.execute(select(Document).where(Document.id == document_id))
        return result.scalar_one_or_none()
    
    async def _update_document_status(self, db: AsyncSession, document: Document, status: str, message: str = None):
        """Update document processing status"""
        document.status = status
        document.updated_at = datetime.utcnow()
        
        # Update metadata with processing info
        if not document.document_metadata:
            document.document_metadata = {}
        
        document.document_metadata['processing_status'] = status
        document.document_metadata['last_processing_message'] = message
        document.document_metadata['last_processed_at'] = datetime.utcnow().isoformat()
        
        await db.commit()
        await db.refresh(document)
    
    async def _update_document_metadata(self, db: AsyncSession, document: Document, extraction_result: Dict[str, Any], chunk_count: int):
        """Update document metadata with extraction results"""
        if not document.document_metadata:
            document.document_metadata = {}
        
        # Merge extraction metadata
        document.document_metadata.update({
            'file_hash': extraction_result['file_hash'],
            'chunk_count': chunk_count,
            'character_count': len(extraction_result['text']),
            'processing_completed_at': datetime.utcnow().isoformat(),
            'extraction_metadata': extraction_result['metadata']
        })
        
        await db.commit()
        await db.refresh(document)
    
    def save_uploaded_file(self, file_content: bytes, filename: str, document_id: int) -> str:
        """
        Save uploaded file to storage
        
        Args:
            file_content: File content as bytes
            filename: Original filename
            document_id: Document ID for organizing storage
            
        Returns:
            Path to saved file
        """
        # Create document-specific directory
        doc_dir = self.storage_path / str(document_id)
        doc_dir.mkdir(parents=True, exist_ok=True)
        
        # Save file with original name
        file_path = doc_dir / filename
        
        with open(file_path, 'wb') as f:
            f.write(file_content)
        
        return str(file_path)
    
    async def check_duplicate(self, file_hash: str) -> Optional[int]:
        """
        Check if a file with the same hash already exists
        
        Args:
            file_hash: SHA-256 hash of the file
            
        Returns:
            Document ID if duplicate found, None otherwise
        """
        try:
            async for db in get_db():
                from sqlalchemy import select, text
                
                # Query for documents with matching file hash in metadata
                result = await db.execute(
                    select(Document.id)
                    .where(text("document_metadata->>'file_hash' = :hash"))
                    .params(hash=file_hash)
                )
                
                existing_doc = result.scalar_one_or_none()
                return existing_doc
                
        except Exception:
            # If duplicate check fails, allow upload to proceed
            return None
    
    def cleanup_file(self, file_path: str):
        """Clean up temporary or failed processing files"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception:
            pass  # Ignore cleanup errors


# Global processor instance
document_processor = DocumentProcessor()