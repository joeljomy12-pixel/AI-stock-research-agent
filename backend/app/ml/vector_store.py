"""
Vector Store for Document Embeddings and Retrieval
Uses ChromaDB for local vector storage.
"""
import chromadb
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging
import uuid

from app.core.config import settings

logger = logging.getLogger(__name__)


class VectorStore:
    """Wrapper for ChromaDB vector store."""

    def __init__(self):
        self.client = None
        self.collection = None
        self._initialized = False

    def initialize(self):
        """Initialize ChromaDB client and collection."""
        if self._initialized:
            return

        try:
            self.client = chromadb.PersistentClient(
                path=settings.chroma_persist_dir,
            )

            self.collection = self.client.get_or_create_collection(
                name="financial_documents",
                metadata={"description": "Financial documents for RAG"}
            )
            self._initialized = True
            logger.info("Vector store initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize vector store: {e}")
            # Fallback to in-memory for hackathon
            self.client = chromadb.EphemeralClient()
            self.collection = self.client.get_or_create_collection(
                name="financial_documents"
            )
            self._initialized = True

    def add_documents(
        self,
        documents: List[str],
        metadatas: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ):
        """Add documents to vector store."""
        if not self._initialized:
            self.initialize()

        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]

        try:
            self.collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            logger.info(f"Added {len(documents)} documents to vector store")
        except Exception as e:
            logger.error(f"Error adding documents: {e}")

    def search(
        self,
        query: str,
        n_results: int = 5,
        where: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar documents."""
        if not self._initialized:
            self.initialize()

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where
            )

            # Format results
            formatted = []
            if results['documents'] and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    formatted.append({
                        'id': results['ids'][0][i] if results['ids'] else None,
                        'document': doc,
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else None,
                    })

            return formatted

        except Exception as e:
            logger.error(f"Error searching vector store: {e}")
            return []

    def search_by_symbol(self, symbol: str, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
        """Search documents for a specific symbol."""
        return self.search(query, n_results, where={"symbol": symbol.upper()})

    def delete_by_symbol(self, symbol: str):
        """Delete all documents for a symbol."""
        if not self._initialized:
            self.initialize()

        try:
            self.collection.delete(where={"symbol": symbol.upper()})
            logger.info(f"Deleted documents for {symbol}")
        except Exception as e:
            logger.error(f"Error deleting documents: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        if not self._initialized:
            self.initialize()

        try:
            count = self.collection.count()
            return {'document_count': count}
        except Exception:
            return {'document_count': 0}


# Global instance
vector_store = VectorStore()


def store_financial_documents(symbol: str, documents: List[Dict[str, Any]]):
    """Store financial documents for a symbol."""
    if not documents:
        return

    texts = []
    metadatas = []
    ids = []

    for doc in documents:
        texts.append(doc.get('content', ''))
        metadatas.append({
            'symbol': symbol.upper(),
            'type': doc.get('type', 'unknown'),
            'title': doc.get('title', ''),
            'source': doc.get('source', ''),
            'date': doc.get('date', datetime.now().isoformat()),
            'url': doc.get('url', ''),
        })
        ids.append(doc.get('id', str(uuid.uuid4())))

    vector_store.add_documents(texts, metadatas, ids)


async def retrieve_relevant_docs(symbol: str, query: str, n_results: int = 5) -> List[Dict[str, Any]]:
    """Retrieve relevant documents for a symbol and query."""
    return vector_store.search_by_symbol(symbol, query, n_results)