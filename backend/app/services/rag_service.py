"""
RAG (Retrieval-Augmented Generation) service using LangChain LCEL patterns
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator, Tuple
from datetime import datetime, timedelta
import json
import hashlib
import pickle

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_core.retrievers import BaseRetriever
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.messages import HumanMessage, AIMessage
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..services.vector_service import chunk_storage_manager
from ..models.chat import ChatSession, ChatMessage
from ..core.snowflake import generate_id

logger = logging.getLogger(__name__)


class RAGError(Exception):
    """Custom exception for RAG operations"""
    pass


class StreamingCallbackHandler(AsyncCallbackHandler):
    """Callback handler for streaming responses"""
    
    def __init__(self):
        self.tokens = []
        self.is_streaming = False
    
    async def on_llm_new_token(self, token: str, **kwargs) -> None:
        """Handle new token from LLM"""
        self.tokens.append(token)
        self.is_streaming = True
    
    def get_tokens(self) -> List[str]:
        """Get accumulated tokens"""
        return self.tokens.copy()
    
    def clear_tokens(self):
        """Clear accumulated tokens"""
        self.tokens.clear()
        self.is_streaming = False


class CustomRetriever(BaseRetriever):
    """Custom retriever that uses our vector service"""
    
    document_id: Optional[int] = None
    similarity_threshold: float = 0.7
    
    def __init__(self, document_id: Optional[int] = None, similarity_threshold: float = 0.7):
        super().__init__(document_id=document_id, similarity_threshold=similarity_threshold)
    
    async def _aget_relevant_documents(self, query: str) -> List[Document]:
        """Retrieve relevant documents asynchronously"""
        try:
            # Use our vector service for similarity search
            results = await chunk_storage_manager.similarity_search(
                query=query,
                n_results=10,
                document_id=self.document_id,
                similarity_threshold=self.similarity_threshold
            )
            
            # Convert to LangChain Document format
            documents = []
            for result in results:
                metadata = result["metadata"].copy()
                metadata.update({
                    "similarity": result["similarity"],
                    "chunk_id": result["chunk_id"],
                    "document_id": result["document_id"],
                    "chunk_index": result["chunk_index"]
                })
                
                doc = Document(
                    page_content=result["content"],
                    metadata=metadata
                )
                documents.append(doc)
            
            logger.info(f"Retrieved {len(documents)} relevant documents for query")
            return documents
            
        except Exception as e:
            logger.error(f"Failed to retrieve documents: {e}")
            raise RAGError(f"Document retrieval failed: {e}")
    
    def _get_relevant_documents(self, query: str) -> List[Document]:
        """Synchronous version (not used in async context)"""
        raise NotImplementedError("Use async version _aget_relevant_documents")


class QueryCache:
    """Simple in-memory cache for query results"""
    
    def __init__(self, max_size: int = 100, ttl_minutes: int = 30):
        self.cache = {}
        self.max_size = max_size
        self.ttl = timedelta(minutes=ttl_minutes)
    
    def _generate_key(self, query: str, document_id: Optional[int], similarity_threshold: float) -> str:
        """Generate cache key from query parameters"""
        key_data = f"{query}:{document_id}:{similarity_threshold}"
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def get(self, query: str, document_id: Optional[int], similarity_threshold: float) -> Optional[Dict[str, Any]]:
        """Get cached result if available and not expired"""
        key = self._generate_key(query, document_id, similarity_threshold)
        
        if key in self.cache:
            result, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                logger.info(f"Cache hit for query: {query[:50]}...")
                return result
            else:
                # Remove expired entry
                del self.cache[key]
        
        return None
    
    def set(self, query: str, document_id: Optional[int], similarity_threshold: float, result: Dict[str, Any]):
        """Cache query result"""
        key = self._generate_key(query, document_id, similarity_threshold)
        
        # Remove oldest entries if cache is full
        if len(self.cache) >= self.max_size:
            oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k][1])
            del self.cache[oldest_key]
        
        self.cache[key] = (result, datetime.now())
        logger.info(f"Cached result for query: {query[:50]}...")
    
    def clear(self):
        """Clear all cached results"""
        self.cache.clear()
        logger.info("Query cache cleared")


class RAGQueryService:
    """Service for handling RAG queries using LangChain LCEL patterns"""
    
    def __init__(self):
        if not settings.openai_api_key:
            raise ValueError("OpenAI API key is required for RAG queries")
        
        # Initialize LLM
        self.llm = ChatOpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            model="gpt-3.5-turbo",
            temperature=0.1,
            streaming=True
        )
        
        # Initialize non-streaming LLM for regular queries
        self.llm_non_streaming = ChatOpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            model="gpt-3.5-turbo",
            temperature=0.1,
            streaming=False
        )
        
        # Initialize query cache
        self.cache = QueryCache()
        
        # Create prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """You are a helpful AI assistant that answers questions based on the provided context documents. 

Instructions:
1. Use only the information from the provided context documents to answer questions
2. If the context doesn't contain enough information to answer the question, say so clearly
3. Always cite which documents you're referencing in your answer
4. Be concise but comprehensive in your responses
5. If multiple documents contain relevant information, synthesize the information appropriately

Context Documents:
{context}

Remember to base your answer only on the provided context."""),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}")
        ])
        
        # Create output parser
        self.output_parser = StrOutputParser()
    
    async def query(
        self,
        question: str,
        document_id: Optional[int] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
        similarity_threshold: float = 0.7,
        enable_query_optimization: bool = True,
        enable_result_ranking: bool = True,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """Process a RAG query and return structured response"""
        try:
            start_time = datetime.now()
            
            # Check cache first (only for queries without chat history to avoid stale context)
            if use_cache and not chat_history:
                cached_result = self.cache.get(question, document_id, similarity_threshold)
                if cached_result:
                    cached_result["from_cache"] = True
                    cached_result["processing_time"] = (datetime.now() - start_time).total_seconds()
                    return cached_result
            
            # Optimize query if enabled
            optimized_question = question
            if enable_query_optimization:
                optimized_question = await self.optimize_query(question, chat_history)
            
            # Create retriever
            retriever = CustomRetriever(
                document_id=document_id,
                similarity_threshold=similarity_threshold
            )
            
            # Retrieve relevant documents
            documents = await retriever._aget_relevant_documents(optimized_question)
            
            # Handle no results case
            if not documents:
                no_results_response = await self.handle_no_results(question, document_id)
                return {
                    "answer": no_results_response["message"],
                    "sources": [],
                    "confidence": 0.0,
                    "processing_time": (datetime.now() - start_time).total_seconds(),
                    "retrieved_documents": 0,
                    "suggestions": no_results_response.get("suggestions", []),
                    "alternative_queries": no_results_response.get("alternative_queries", []),
                    "tips": no_results_response.get("tips", [])
                }
            
            # Convert documents to result format for ranking
            results = []
            for doc in documents:
                result = {
                    "content": doc.page_content,
                    "similarity": doc.metadata.get("similarity", 0.0),
                    "metadata": doc.metadata,
                    "chunk_id": doc.metadata.get("chunk_id"),
                    "document_id": doc.metadata.get("document_id"),
                    "chunk_index": doc.metadata.get("chunk_index")
                }
                results.append(result)
            
            # Rank results if enabled
            if enable_result_ranking:
                results = await self.rank_results(results, question)
            
            # Format context from ranked documents
            context = "\n\n".join([
                f"Document {i+1} (Similarity: {result['similarity']:.2f}):\n{result['content']}"
                for i, result in enumerate(results)
            ])
            
            # Format chat history
            formatted_history = []
            if chat_history:
                for msg in chat_history:
                    if msg["role"] == "user":
                        formatted_history.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        formatted_history.append(AIMessage(content=msg["content"]))
            
            # Create the prompt with context
            messages = self.prompt.format_messages(
                context=context,
                chat_history=formatted_history,
                input=question
            )
            
            # Get LLM response
            response = await self.llm_non_streaming.ainvoke(messages)
            end_time = datetime.now()
            
            # Extract source information from ranked results
            sources = []
            for result in results:
                source_info = {
                    "chunk_id": result["chunk_id"],
                    "document_id": result["document_id"],
                    "chunk_index": result["chunk_index"],
                    "similarity": result["similarity"],
                    "enhanced_score": result.get("enhanced_score", result["similarity"]),
                    "content": result["content"][:500] + "..." if len(result["content"]) > 500 else result["content"]
                }
                sources.append(source_info)
            
            # Calculate confidence based on enhanced scores
            confidence = 0.0
            if sources:
                if enable_result_ranking:
                    avg_score = sum(s.get("enhanced_score", s["similarity"]) for s in sources) / len(sources)
                else:
                    avg_score = sum(s["similarity"] for s in sources) / len(sources)
                confidence = min(avg_score, 1.0)
            
            processing_time = (end_time - start_time).total_seconds()
            
            result = {
                "answer": response.content,
                "sources": sources,
                "confidence": confidence,
                "processing_time": processing_time,
                "retrieved_documents": len(sources),
                "query_optimized": optimized_question != question,
                "original_query": question if optimized_question != question else None,
                "from_cache": False
            }
            
            # Add performance metrics
            if processing_time > 5.0:
                result["performance_warning"] = "Query took longer than expected. Consider using more specific terms."
            
            # Cache result if enabled and no chat history
            if use_cache and not chat_history:
                # Create a copy without processing_time for caching
                cache_result = result.copy()
                cache_result.pop("processing_time", None)
                cache_result.pop("from_cache", None)
                self.cache.set(question, document_id, similarity_threshold, cache_result)
            
            return result
            
        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            raise RAGError(f"Query processing failed: {e}")
    
    async def stream_query(
        self,
        question: str,
        document_id: Optional[int] = None,
        chat_history: Optional[List[Dict[str, str]]] = None,
        similarity_threshold: float = 0.7
    ) -> AsyncGenerator[str, None]:
        """Process a RAG query with streaming response"""
        try:
            # Create retriever
            retriever = CustomRetriever(
                document_id=document_id,
                similarity_threshold=similarity_threshold
            )
            
            # Retrieve relevant documents
            documents = await retriever._aget_relevant_documents(question)
            
            # Format context from documents
            context = "\n\n".join([
                f"Document {i+1} (Similarity: {doc.metadata.get('similarity', 0.0):.2f}):\n{doc.page_content}"
                for i, doc in enumerate(documents)
            ])
            
            # Format chat history
            formatted_history = []
            if chat_history:
                for msg in chat_history:
                    if msg["role"] == "user":
                        formatted_history.append(HumanMessage(content=msg["content"]))
                    elif msg["role"] == "assistant":
                        formatted_history.append(AIMessage(content=msg["content"]))
            
            # Create the prompt with context
            messages = self.prompt.format_messages(
                context=context,
                chat_history=formatted_history,
                input=question
            )
            
            # Stream LLM response
            async for chunk in self.llm.astream(messages):
                if hasattr(chunk, 'content') and chunk.content:
                    yield chunk.content
            
        except Exception as e:
            logger.error(f"Streaming RAG query failed: {e}")
            raise RAGError(f"Streaming query processing failed: {e}")
    
    async def get_query_suggestions(
        self,
        document_id: Optional[int] = None,
        limit: int = 5
    ) -> List[str]:
        """Generate query suggestions based on available documents"""
        try:
            # Base suggestions
            base_suggestions = [
                "What is the main topic of the documents?",
                "Can you summarize the key points?",
                "What are the most important findings?",
                "Are there any recommendations mentioned?",
                "What conclusions can be drawn from the content?"
            ]
            
            # Document-specific suggestions
            if document_id:
                doc_suggestions = [
                    f"What are the key insights from document {document_id}?",
                    f"Can you explain the main concepts in document {document_id}?",
                    f"What are the important details in document {document_id}?",
                    f"How does document {document_id} relate to other documents?",
                    f"What questions does document {document_id} answer?"
                ]
                # Mix base and document-specific suggestions
                all_suggestions = doc_suggestions + base_suggestions
            else:
                all_suggestions = base_suggestions
            
            return all_suggestions[:limit]
            
        except Exception as e:
            logger.error(f"Failed to generate suggestions: {e}")
            return []
    
    async def handle_no_results(
        self,
        query: str,
        document_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Handle cases where no relevant content is found"""
        try:
            # Analyze the query to provide helpful suggestions
            analysis = await self.analyze_query_complexity(query)
            
            suggestions = []
            
            # Suggest query refinements based on analysis
            if "factual" in analysis.get("question_types", []):
                suggestions.extend([
                    "Try rephrasing your question with different keywords",
                    "Ask about specific topics or concepts",
                    "Use more general terms if your query is very specific"
                ])
            
            if "explanatory" in analysis.get("question_types", []):
                suggestions.extend([
                    "Break down complex questions into simpler parts",
                    "Ask about specific aspects of the topic",
                    "Try asking 'what', 'where', or 'when' questions first"
                ])
            
            if analysis.get("complexity") == "complex":
                suggestions.extend([
                    "Try simplifying your question",
                    "Focus on one aspect at a time",
                    "Use fewer technical terms"
                ])
            
            # Get general query suggestions
            general_suggestions = await self.get_query_suggestions(document_id, limit=3)
            
            return {
                "message": "I couldn't find relevant information for your query.",
                "suggestions": suggestions[:3],
                "alternative_queries": general_suggestions,
                "tips": [
                    "Make sure your documents contain information related to your question",
                    "Try using different keywords or synonyms",
                    "Check if your question is too specific or too broad"
                ]
            }
            
        except Exception as e:
            logger.error(f"Failed to handle no results: {e}")
            return {
                "message": "I couldn't find relevant information for your query.",
                "suggestions": ["Try rephrasing your question"],
                "alternative_queries": [],
                "tips": []
            }
    
    async def rank_results(
        self,
        results: List[Dict[str, Any]],
        query: str,
        boost_recent: bool = True,
        boost_document_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Advanced ranking of search results"""
        try:
            if not results:
                return results
            
            # Calculate enhanced scores
            for result in results:
                base_similarity = result.get("similarity", 0.0)
                enhanced_score = base_similarity
                
                # Boost recent documents (if timestamp available)
                if boost_recent and "created_at" in result.get("metadata", {}):
                    # Simple recency boost - in production, use more sophisticated time decay
                    enhanced_score *= 1.1
                
                # Boost specific document types
                if boost_document_type and result.get("metadata", {}).get("document_type") == boost_document_type:
                    enhanced_score *= 1.2
                
                # Boost results with query terms in title/metadata
                metadata = result.get("metadata", {})
                if "title" in metadata:
                    title_lower = metadata["title"].lower()
                    query_lower = query.lower()
                    if any(word in title_lower for word in query_lower.split()):
                        enhanced_score *= 1.15
                
                result["enhanced_score"] = enhanced_score
            
            # Sort by enhanced score
            ranked_results = sorted(results, key=lambda x: x.get("enhanced_score", 0), reverse=True)
            
            logger.info(f"Ranked {len(ranked_results)} results")
            return ranked_results
            
        except Exception as e:
            logger.error(f"Failed to rank results: {e}")
            return results
    
    async def optimize_query(
        self,
        query: str,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> str:
        """Optimize query for better retrieval"""
        try:
            # Extract key terms and expand query if needed
            optimized_query = query.strip()
            
            # Add context from recent chat history
            if chat_history and len(chat_history) > 0:
                recent_context = []
                for msg in chat_history[-3:]:  # Last 3 messages
                    if msg["role"] == "user":
                        recent_context.append(msg["content"])
                
                # Simple query expansion with context
                if recent_context:
                    context_terms = " ".join(recent_context).lower()
                    query_lower = query.lower()
                    
                    # If query is very short, add context
                    if len(query.split()) <= 2 and len(context_terms) > 0:
                        optimized_query = f"{query} {context_terms[:100]}"
            
            logger.info(f"Optimized query: '{query}' -> '{optimized_query}'")
            return optimized_query
            
        except Exception as e:
            logger.error(f"Failed to optimize query: {e}")
            return query
    
    def clear_cache(self):
        """Clear the query cache"""
        self.cache.clear()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "cache_size": len(self.cache.cache),
            "max_cache_size": self.cache.max_size,
            "ttl_minutes": self.cache.ttl.total_seconds() / 60,
            "cache_keys": list(self.cache.cache.keys())[:10]  # Show first 10 keys
        }
    
    async def analyze_query_complexity(self, question: str) -> Dict[str, Any]:
        """Analyze query complexity and provide optimization suggestions"""
        try:
            word_count = len(question.split())
            
            # Simple complexity analysis
            complexity = "simple"
            if word_count > 20:
                complexity = "complex"
            elif word_count > 10:
                complexity = "medium"
            
            # Check for question types
            question_lower = question.lower()
            question_types = []
            
            if any(word in question_lower for word in ["what", "who", "where", "when"]):
                question_types.append("factual")
            if any(word in question_lower for word in ["how", "why"]):
                question_types.append("explanatory")
            if any(word in question_lower for word in ["compare", "difference", "similar"]):
                question_types.append("comparative")
            if any(word in question_lower for word in ["summarize", "overview", "summary"]):
                question_types.append("summary")
            
            return {
                "complexity": complexity,
                "word_count": word_count,
                "question_types": question_types,
                "estimated_processing_time": word_count * 0.1  # Simple estimation
            }
            
        except Exception as e:
            logger.error(f"Query analysis failed: {e}")
            return {"complexity": "unknown", "word_count": 0, "question_types": []}


class ChatSessionManager:
    """Manager for chat sessions and conversation history"""
    
    def __init__(self, rag_service: RAGQueryService):
        self.rag_service = rag_service
    
    async def create_session(
        self,
        db: AsyncSession,
        title: Optional[str] = None
    ) -> ChatSession:
        """Create a new chat session"""
        try:
            session = ChatSession(
                title=title or "New Chat",
                is_active=True
            )
            
            db.add(session)
            await db.commit()
            await db.refresh(session)
            
            logger.info(f"Created chat session {session.id}")
            return session
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to create chat session: {e}")
            raise RAGError(f"Session creation failed: {e}")
    
    async def get_session(
        self,
        db: AsyncSession,
        session_id: int
    ) -> Optional[ChatSession]:
        """Get a chat session by ID"""
        try:
            from sqlalchemy import select
            result = await db.execute(
                select(ChatSession).where(
                    ChatSession.id == session_id,
                    ChatSession.is_active == True
                )
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            return None
    
    async def get_session_messages(
        self,
        db: AsyncSession,
        session_id: int,
        limit: int = 50
    ) -> List[ChatMessage]:
        """Get messages for a session"""
        try:
            from sqlalchemy import select
            result = await db.execute(
                select(ChatMessage)
                .where(ChatMessage.session_id == session_id)
                .order_by(ChatMessage.created_at.desc())
                .limit(limit)
            )
            messages = result.scalars().all()
            return list(reversed(messages))  # Return in chronological order
            
        except Exception as e:
            logger.error(f"Failed to get messages for session {session_id}: {e}")
            return []
    
    async def add_message(
        self,
        db: AsyncSession,
        session_id: int,
        role: str,
        content: str,
        sources: Optional[List[Dict[str, Any]]] = None
    ) -> ChatMessage:
        """Add a message to a session"""
        try:
            message = ChatMessage(
                session_id=session_id,
                role=role,
                content=content,
                sources=sources
            )
            
            db.add(message)
            await db.commit()
            await db.refresh(message)
            
            # Update session timestamp
            session = await self.get_session(db, session_id)
            if session:
                session.updated_at = datetime.now()
                await db.commit()
            
            logger.info(f"Added message to session {session_id}")
            return message
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to add message to session {session_id}: {e}")
            raise RAGError(f"Message creation failed: {e}")
    
    async def send_message(
        self,
        db: AsyncSession,
        session_id: int,
        question: str,
        document_id: Optional[int] = None,
        similarity_threshold: float = 0.7,
        enable_query_optimization: bool = True,
        enable_result_ranking: bool = True,
        use_cache: bool = False
    ) -> Dict[str, Any]:
        """Send a message and get RAG response"""
        try:
            # Get session
            session = await self.get_session(db, session_id)
            if not session:
                raise RAGError(f"Session {session_id} not found")
            
            # Get chat history
            messages = await self.get_session_messages(db, session_id, limit=10)
            chat_history = []
            for msg in messages:
                chat_history.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            # Add user message
            user_message = await self.add_message(
                db, session_id, "user", question
            )
            
            # Process RAG query
            rag_response = await self.rag_service.query(
                question=question,
                document_id=document_id,
                chat_history=chat_history,
                similarity_threshold=similarity_threshold,
                enable_query_optimization=enable_query_optimization,
                enable_result_ranking=enable_result_ranking,
                use_cache=use_cache
            )
            
            # Add assistant message
            assistant_message = await self.add_message(
                db, session_id, "assistant", 
                rag_response["answer"], 
                rag_response["sources"]
            )
            
            return {
                "session_id": session_id,
                "user_message_id": user_message.id,
                "assistant_message_id": assistant_message.id,
                "answer": rag_response["answer"],
                "sources": rag_response["sources"],
                "confidence": rag_response["confidence"],
                "processing_time": rag_response["processing_time"]
            }
            
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise RAGError(f"Message processing failed: {e}")
    
    async def stream_message(
        self,
        db: AsyncSession,
        session_id: int,
        question: str,
        document_id: Optional[int] = None,
        similarity_threshold: float = 0.7
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Send a message and stream RAG response"""
        try:
            # Get session
            session = await self.get_session(db, session_id)
            if not session:
                raise RAGError(f"Session {session_id} not found")
            
            # Get chat history
            messages = await self.get_session_messages(db, session_id, limit=10)
            chat_history = []
            for msg in messages:
                chat_history.append({
                    "role": msg.role,
                    "content": msg.content
                })
            
            # Add user message
            user_message = await self.add_message(
                db, session_id, "user", question
            )
            
            # Yield initial response
            yield {
                "type": "message_created",
                "user_message_id": user_message.id,
                "session_id": session_id
            }
            
            # Stream RAG response
            full_response = ""
            async for chunk in self.rag_service.stream_query(
                question=question,
                document_id=document_id,
                chat_history=chat_history,
                similarity_threshold=similarity_threshold
            ):
                full_response += chunk
                yield {
                    "type": "content_delta",
                    "delta": chunk
                }
            
            # Add assistant message with full response
            assistant_message = await self.add_message(
                db, session_id, "assistant", full_response
            )
            
            # Yield completion
            yield {
                "type": "message_completed",
                "assistant_message_id": assistant_message.id,
                "full_content": full_response
            }
            
        except Exception as e:
            logger.error(f"Failed to stream message: {e}")
            yield {
                "type": "error",
                "error": str(e)
            }
    
    async def delete_session(
        self,
        db: AsyncSession,
        session_id: int
    ) -> bool:
        """Delete a chat session"""
        try:
            session = await self.get_session(db, session_id)
            if not session:
                return False
            
            session.is_active = False
            await db.commit()
            
            logger.info(f"Deleted chat session {session_id}")
            return True
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to delete session {session_id}: {e}")
            return False
    
    async def update_session_title(
        self,
        db: AsyncSession,
        session_id: int,
        title: str
    ) -> Optional[ChatSession]:
        """Update session title"""
        try:
            session = await self.get_session(db, session_id)
            if not session:
                return None
            
            session.title = title
            await db.commit()
            
            logger.info(f"Updated session {session_id} title to '{title}'")
            return session
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Failed to update session title: {e}")
            return None


# Global instances
rag_service = RAGQueryService()
chat_manager = ChatSessionManager(rag_service)