"""Vector store using ChromaDB for semantic search."""

from typing import Dict, List, Optional

import chromadb
from chromadb.config import Settings


class VectorStore:
    """Vector store for code chunks using ChromaDB."""

    def __init__(self, persist_directory: str, collection_prefix: str = "architectai"):
        """Initialize vector store.

        Args:
            persist_directory: Directory to persist ChromaDB data
            collection_prefix: Prefix for collection names
        """
        self.persist_directory = persist_directory
        self.collection_prefix = collection_prefix

        # Initialize ChromaDB client with persistence
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )

    def _get_collection_name(self, session_id: str) -> str:
        """Get collection name for a session.

        Args:
            session_id: Session identifier

        Returns:
            Collection name
        """
        return f"{self.collection_prefix}_{session_id}"

    def _get_collection(self, session_id: str):
        """Get or create collection for session.

        Args:
            session_id: Session identifier

        Returns:
            ChromaDB collection
        """
        collection_name = self._get_collection_name(session_id)

        try:
            collection = self.client.get_collection(name=collection_name)
        except Exception:
            # Collection doesn't exist, create it
            collection = self.client.create_collection(
                name=collection_name, metadata={"session_id": session_id}
            )

        return collection

    def add_chunks(self, chunks: List[Dict], session_id: str) -> None:
        """Add chunks to vector store.

        Args:
            chunks: List of chunk dictionaries with 'content', 'metadata', 'embedding'
            session_id: Session identifier
        """
        if not chunks:
            return

        collection = self._get_collection(session_id)

        # Prepare data for ChromaDB
        ids = []
        documents = []
        embeddings = []
        metadatas = []

        for i, chunk in enumerate(chunks):
            chunk_id = f"{session_id}_{i}"
            ids.append(chunk_id)
            documents.append(chunk["content"])
            embeddings.append(chunk["embedding"])

            # Prepare metadata (must be serializable)
            metadata = chunk.get("metadata", {}).copy()
            metadata["session_id"] = session_id
            metadata["chunk_index"] = i

            # Ensure all metadata values are serializable
            for key, value in list(metadata.items()):
                if not isinstance(value, (str, int, float, bool)):
                    metadata[key] = str(value)

            metadatas.append(metadata)

        # Add to collection
        collection.add(
            ids=ids, documents=documents, embeddings=embeddings, metadatas=metadatas
        )

    def search(
        self,
        query_embedding: List[float],
        session_id: str,
        n_results: int = 5,
        where: Optional[Dict] = None,
    ) -> List[Dict]:
        """Search for similar chunks.

        Args:
            query_embedding: Query embedding vector
            session_id: Session to search within
            n_results: Number of results to return
            where: Optional filter conditions

        Returns:
            List of result dictionaries
        """
        collection = self._get_collection(session_id)

        # Query collection
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"],
        )

        # Format results
        formatted_results = []
        if results["ids"] and len(results["ids"][0]) > 0:
            for i in range(len(results["ids"][0])):
                formatted_results.append(
                    {
                        "id": results["ids"][0][i],
                        "content": results["documents"][0][i]
                        if results["documents"]
                        else None,
                        "metadata": results["metadatas"][0][i]
                        if results["metadatas"]
                        else None,
                        "distance": results["distances"][0][i]
                        if results["distances"]
                        else None,
                    }
                )

        return formatted_results

    def search_by_text(
        self, query_text: str, embedding_service, session_id: str, n_results: int = 5
    ) -> List[Dict]:
        """Search using text query (embeds then searches).

        Args:
            query_text: Text query
            embedding_service: EmbeddingService instance
            session_id: Session to search within
            n_results: Number of results

        Returns:
            List of result dictionaries
        """
        # Generate embedding for query
        query_embedding = embedding_service.embed(query_text)

        # Search
        return self.search(query_embedding, session_id, n_results)

    def delete_session(self, session_id: str) -> None:
        """Delete all chunks for a session.

        Args:
            session_id: Session identifier
        """
        collection_name = self._get_collection_name(session_id)

        try:
            self.client.delete_collection(name=collection_name)
        except Exception:
            # Collection might not exist
            pass

    def count(self, session_id: str) -> int:
        """Get count of chunks in session.

        Args:
            session_id: Session identifier

        Returns:
            Number of chunks
        """
        try:
            collection = self._get_collection(session_id)
            return collection.count()
        except Exception:
            return 0

    def list_sessions(self) -> List[str]:
        """List all sessions with vector data.

        Returns:
            List of session IDs
        """
        try:
            collections = self.client.list_collections()
            sessions = []
            for collection in collections:
                name = collection.name if hasattr(collection, "name") else collection
                if name.startswith(self.collection_prefix + "_"):
                    session_id = name[len(self.collection_prefix) + 1 :]
                    sessions.append(session_id)
            return sessions
        except Exception:
            return []
