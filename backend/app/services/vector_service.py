"""
Vector database service using Chroma for document embeddings
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
import chromadb
from chromadb.config import Settings as ChromaSettings
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from ..core.config import settings
from ..core.snowflake import generate_id
from ..models.document import DocumentChunk

logger = logging.getLogger(__name__)


class VectorDatabaseError(Exception):
    """Custom exception for vector database operations"""
    pass


class EmbeddingService:
    """Service for generating embeddings using OpenAI"""
    
    def __init__(self):
        if not settings.current_embedding_api_key:
            logger.warning(f"API key not configured for embedding provider '{settings.embedding_provider}' - embedding service will not be functional")
            self.client = None
            self.model = None
            self.dimensions = None
            return
        
        self.client = AsyncOpenAI(
            api_key=settings.current_embedding_api_key.get_secret_value(),
            base_url=settings.current_embedding_base_url
        )
        self.model = settings.current_embedding_model
        self.dimensions = settings.current_embedding_dimensions
        
    async def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts"""
        if not self.client:
            raise VectorDatabaseError("OpenAI API key not configured - cannot generate embeddings")
        
        try:
            # OpenAI API has a limit on batch size, so we process in chunks
            batch_size = 100
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                
                response = await self.client.embeddings.create(
                    model=self.model,
                    input=batch
                )
                
                batch_embeddings = [data.embedding for data in response.data]
                all_embeddings.extend(batch_embeddings)
                
                # Small delay to respect rate limits
                if len(texts) > batch_size:
                    await asyncio.sleep(0.1)
            
            logger.info(f"Generated embeddings for {len(texts)} texts")
            return all_embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise VectorDatabaseError(f"Embedding generation failed: {e}")
    
    async def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a single query text"""
        if not self.client:
            raise VectorDatabaseError("OpenAI API key not configured - cannot generate embeddings")
        
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=[text]
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {e}")
            raise VectorDatabaseError(f"Query embedding generation failed: {e}")


class ChromaVectorStore:
    """Chroma vector database wrapper with connection pooling"""
    
    def __init__(self):
        self.client = None
        self.collection = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize Chroma client and collection"""
        if self._initialized:
            return
            
        try:
            # Create Chroma client
            self.client = chromadb.PersistentClient(
                path=settings.chroma_persist_directory,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name=settings.chroma_collection_name,
                metadata={"description": "RAG system document chunks"}
            )
            
            self._initialized = True
            logger.info(f"Chroma vector store initialized with collection: {settings.chroma_collection_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize Chroma: {e}")
            raise VectorDatabaseError(f"Chroma initialization failed: {e}")
    
    async def add_documents(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict[str, Any]]
    ) -> None:
        """Add documents to the vector store"""
        await self.initialize()
        
        try:
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )
            
            logger.info(f"Added {len(ids)} documents to vector store")
            
        except Exception as e:
            logger.error(f"Failed to add documents to vector store: {e}")
            raise VectorDatabaseError(f"Failed to add documents: {e}")
    
    async def similarity_search(
        self,
        query_embedding: List[float],
        n_results: int = 10,
        where: Optional[Dict[str, Any]] = None
    ) -> Tuple[List[str], List[float], List[Dict[str, Any]]]:
        """Perform similarity search"""
        await self.initialize()
        
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                include=["documents", "distances", "metadatas"]
            )
            
            # Extract results
            documents = results["documents"][0] if results["documents"] else []
            distances = results["distances"][0] if results["distances"] else []
            metadatas = results["metadatas"][0] if results["metadatas"] else []
            
            # Convert distances to similarity scores (1 - distance)
            similarities = [1 - distance for distance in distances]
            
            logger.info(f"Found {len(documents)} similar documents")
            return documents, similarities, metadatas
            
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            raise VectorDatabaseError(f"Similarity search failed: {e}")
    
    async def delete_documents(self, ids: List[str]) -> None:
        """Delete documents from vector store"""
        await self.initialize()
        
        try:
            self.collection.delete(ids=ids)
            logger.info(f"Deleted {len(ids)} documents from vector store")
            
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
            raise VectorDatabaseError(f"Failed to delete documents: {e}")
    
    async def get_collection_stats(self) -> Dict[str, Any]:
        """Get collection statistics"""
        await self.initialize()
        
        try:
            count = self.collection.count()
            return {
                "total_documents": count,
                "collection_name": settings.chroma_collection_name
            }
            
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {"error": str(e)}


class VectorService:
    """Main vector service for hybrid SQL + Vector database operations"""
    
    def __init__(self):
        self.embedding_service = EmbeddingService()
        self.vector_store = ChromaVectorStore()
        
    async def store_chunks(
        self,
        db: AsyncSession,
        document_id: int,
        chunks: List[Dict[str, Any]]
    ) -> List[DocumentChunk]:
        """Store chunks in both SQL and vector databases"""
        if not chunks:
            logger.warning(f"No chunks provided for document {document_id}")
            return []
        
        # Validate chunk data
        for i, chunk in enumerate(chunks):
            if not isinstance(chunk, dict) or "content" not in chunk:
                raise VectorDatabaseError(f"Invalid chunk data at index {i}: missing 'content' field")
            if not chunk["content"].strip():
                raise VectorDatabaseError(f"Empty content in chunk at index {i}")
        
        try:
            # Generate embeddings for all chunks
            chunk_texts = [chunk["content"] for chunk in chunks]
            embeddings = await self.embedding_service.embed_documents(chunk_texts)
            
            # Create DocumentChunk objects
            db_chunks = []
            vector_ids = []
            vector_embeddings = []
            vector_documents = []
            vector_metadatas = []
            
            for i, (chunk_data, embedding) in enumerate(zip(chunks, embeddings)):
                # Generate unique ID for this chunk
                chunk_id = generate_id()
                vector_id = str(chunk_id)
                
                # Create SQL record
                db_chunk = DocumentChunk(
                    id=chunk_id,
                    document_id=document_id,
                    chunk_index=i,
                    vector_id=vector_id,
                    content=chunk_data["content"],
                    start_char=chunk_data.get("start_char", 0),
                    end_char=chunk_data.get("end_char", len(chunk_data["content"])),
                    token_count=chunk_data.get("token_count", 0)
                )
                
                db_chunks.append(db_chunk)
                db.add(db_chunk)
                
                # Prepare vector data
                vector_ids.append(vector_id)
                vector_embeddings.append(embedding)
                vector_documents.append(chunk_data["content"])
                vector_metadatas.append({
                    "document_id": document_id,
                    "chunk_id": chunk_id,
                    "chunk_index": i,
                    "start_char": chunk_data.get("start_char", 0),
                    "end_char": chunk_data.get("end_char", len(chunk_data["content"])),
                    "token_count": chunk_data.get("token_count", 0)
                })
            
            # Commit SQL changes first
            await db.commit()
            
            # Store in vector database
            await self.vector_store.add_documents(
                ids=vector_ids,
                embeddings=vector_embeddings,
                documents=vector_documents,
                metadatas=vector_metadatas
            )
            
            logger.info(f"Stored {len(db_chunks)} chunks for document {document_id}")
            return db_chunks
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to store chunks: {e}")
            raise VectorDatabaseError(f"Chunk storage failed: {e}")
    
    async def delete_chunks(
        self,
        db: AsyncSession,
        document_id: int
    ) -> None:
        """Delete all chunks for a document from both databases"""
        try:
            # Get all chunks for this document
            result = await db.execute(
                select(DocumentChunk).where(DocumentChunk.document_id == document_id)
            )
            chunks = result.scalars().all()
            
            if not chunks:
                logger.info(f"No chunks found for document {document_id}")
                return
            
            # Extract vector IDs
            vector_ids = [chunk.vector_id for chunk in chunks]
            
            # Delete from vector database first
            await self.vector_store.delete_documents(vector_ids)
            
            # Delete from SQL database
            await db.execute(
                delete(DocumentChunk).where(DocumentChunk.document_id == document_id)
            )
            
            await db.commit()
            
            logger.info(f"Deleted {len(chunks)} chunks for document {document_id}")
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to delete chunks: {e}")
            raise VectorDatabaseError(f"Chunk deletion failed: {e}")
    
    async def similarity_search(
        self,
        query: str,
        n_results: int = 10,
        document_id: Optional[int] = None,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks"""
        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.embed_query(query)
            
            # Prepare filter
            where_filter = None
            if document_id:
                where_filter = {"document_id": document_id}
            
            # Perform similarity search
            documents, similarities, metadatas = await self.vector_store.similarity_search(
                query_embedding=query_embedding,
                n_results=n_results,
                where=where_filter
            )
            
            # Filter by similarity threshold and format results
            results = []
            for doc, similarity, metadata in zip(documents, similarities, metadatas):
                if similarity >= similarity_threshold:
                    results.append({
                        "content": doc,
                        "similarity": similarity,
                        "metadata": metadata,
                        "chunk_id": metadata.get("chunk_id"),
                        "document_id": metadata.get("document_id"),
                        "chunk_index": metadata.get("chunk_index")
                    })
            
            logger.info(f"Found {len(results)} similar chunks above threshold {similarity_threshold}")
            return results
            
        except Exception as e:
            logger.error(f"Similarity search failed: {e}")
            raise VectorDatabaseError(f"Similarity search failed: {e}")
    
    async def get_chunk_by_id(
        self,
        db: AsyncSession,
        chunk_id: int
    ) -> Optional[DocumentChunk]:
        """Get a specific chunk by ID"""
        try:
            result = await db.execute(
                select(DocumentChunk).where(DocumentChunk.id == chunk_id)
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Failed to get chunk {chunk_id}: {e}")
            return None
    
    async def update_chunk(
        self,
        db: AsyncSession,
        chunk_id: int,
        content: str
    ) -> Optional[DocumentChunk]:
        """Update chunk content and re-embed"""
        try:
            # Get existing chunk
            chunk = await self.get_chunk_by_id(db, chunk_id)
            if not chunk:
                return None
            
            # Generate new embedding
            embedding = await self.embedding_service.embed_query(content)
            
            # Update vector database first
            await self.vector_store.delete_documents([chunk.vector_id])
            
            # Update SQL record
            chunk.content = content
            chunk.token_count = len(content.split())  # Simple token count
            
            # Add updated document to vector database
            await self.vector_store.add_documents(
                ids=[chunk.vector_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[{
                    "document_id": chunk.document_id,
                    "chunk_id": chunk.id,
                    "chunk_index": chunk.chunk_index,
                    "start_char": chunk.start_char,
                    "end_char": chunk.end_char,
                    "token_count": chunk.token_count
                }]
            )
            
            # Commit SQL changes last
            await db.commit()
            
            logger.info(f"Updated chunk {chunk_id}")
            return chunk
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to update chunk {chunk_id}: {e}")
            raise VectorDatabaseError(f"Chunk update failed: {e}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        try:
            vector_stats = await self.vector_store.get_collection_stats()
            return {
                "vector_database": vector_stats,
                "ai_provider": settings.ai_provider,
                "embedding_model": settings.current_embedding_model,
                "chat_model": settings.current_chat_model,
                "chunk_size": settings.chunk_size,
                "chunk_overlap": settings.chunk_overlap
            }
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {"error": str(e)}
    
    async def get_collection_info(self) -> Dict[str, Any]:
        """Get vector database collection information for health checks"""
        try:
            # Check if embedding service is available
            if not self.embedding_service.client:
                return {
                    "status": "degraded",
                    "collection_stats": {},
                    "embedding_model": None,
                    "error": "OpenAI API key not configured"
                }
            
            stats = await self.get_stats()
            
            # Check for errors in stats
            if "error" in stats:
                return {
                    "status": "unhealthy",
                    "collection_stats": {},
                    "embedding_model": stats.get("embedding_model"),
                    "error": stats["error"]
                }
            
            return {
                "status": "healthy",
                "collection_stats": stats.get("vector_database", {}),
                "embedding_model": stats.get("embedding_model"),
                "error": None
            }
        except Exception as e:
            logger.error(f"Vector service health check failed: {e}")
            return {
                "status": "unhealthy", 
                "error": str(e),
                "collection_stats": {},
                "embedding_model": None
            }
    
    async def search_similar_chunks(
        self,
        query: str,
        n_results: int = 10,
        document_id: Optional[int] = None,
        similarity_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search for similar document chunks (alias for similarity_search)"""
        return await self.similarity_search(
            query=query,
            n_results=n_results,
            document_id=document_id,
            similarity_threshold=similarity_threshold
        )
    
    async def store_document_chunks(
        self,
        db: AsyncSession,
        document_id: int,
        chunks: List[Dict[str, Any]]
    ) -> List[DocumentChunk]:
        """Store document chunks in vector database (alias for store_chunks)"""
        return await self.store_chunks(db, document_id, chunks)
    
    async def delete_document_chunks(
        self,
        db: AsyncSession,
        document_id: int
    ) -> None:
        """Delete all chunks for a document (alias for delete_chunks)"""
        await self.delete_chunks(db, document_id)
    
    async def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive vector service statistics (alias for get_stats)"""
        return await self.get_stats()


# Global instances
vector_service = VectorService()
# For backward compatibility
chunk_storage_manager = vector_service