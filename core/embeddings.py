from typing import List, Dict, Any, Optional
import numpy as np
import google.generativeai as genai
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from core.config import DEFAULT_EMBEDDING_MODEL, DEFAULT_TOP_K

class VectorStore:
    """
    Semantic vector index supporting Google Gemini dense embeddings (models/text-embedding-004)
    with graceful fallback to TF-IDF vectorization when API access is unconfigured.
    """

    def __init__(self, embedding_model: str = DEFAULT_EMBEDDING_MODEL):
        self.embedding_model = embedding_model
        self.chunks: List[Dict[str, Any]] = []
        self.dense_embeddings: Optional[np.ndarray] = None
        self.use_dense: bool = False
        self.tfidf_vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix = None

    def add_chunks(self, chunks: List[Dict[str, Any]], api_key: str = None) -> None:
        """
        Embeds chunks using Gemini embeddings when an API key is available,
        otherwise fits a TF-IDF lexical index.
        """
        if not chunks:
            return

        self.chunks.extend(chunks)
        all_texts = [c["text"] for c in self.chunks]

        if api_key and api_key.strip():
            try:
                genai.configure(api_key=api_key.strip())
                embeddings_list = []
                batch_size = 50
                for i in range(0, len(all_texts), batch_size):
                    batch = all_texts[i:i + batch_size]
                    result = genai.embed_content(
                        model=self.embedding_model,
                        content=batch,
                        task_type="retrieval_document"
                    )
                    embeddings_list.extend(result["embedding"])

                embeddings_array = np.array(embeddings_list, dtype=np.float32)
                # Normalize vectors for fast cosine similarity via dot product
                norms = np.linalg.norm(embeddings_array, axis=1, keepdims=True)
                norms[norms == 0] = 1e-10
                self.dense_embeddings = embeddings_array / norms
                self.use_dense = True
                return
            except Exception as e:
                # Fall back to TF-IDF if embedding call encounters network or quota issues
                self.use_dense = False

        # Fallback to TF-IDF vectorizer
        self.tfidf_vectorizer = TfidfVectorizer().fit(all_texts)
        self.tfidf_matrix = self.tfidf_vectorizer.transform(all_texts)
        self.use_dense = False

    def query(self, query_text: str, api_key: str = None, top_k: int = DEFAULT_TOP_K) -> List[Dict[str, Any]]:
        """
        Retrieves top_k most relevant chunks using semantic dense vector similarity
        or TF-IDF lexical similarity.
        """
        if not self.chunks:
            return []

        k = min(top_k, len(self.chunks))

        if self.use_dense and self.dense_embeddings is not None and api_key and api_key.strip():
            try:
                genai.configure(api_key=api_key.strip())
                query_result = genai.embed_content(
                    model=self.embedding_model,
                    content=query_text,
                    task_type="retrieval_query"
                )
                q_vec = np.array(query_result["embedding"], dtype=np.float32)
                norm = np.linalg.norm(q_vec)
                if norm > 0:
                    q_vec = q_vec / norm

                similarities = np.dot(self.dense_embeddings, q_vec)
                top_indices = np.argsort(similarities)[::-1][:k]

                results = []
                for idx in top_indices:
                    chunk = dict(self.chunks[idx])
                    chunk["score"] = float(similarities[idx])
                    chunk["retrieval_method"] = "dense_embedding"
                    results.append(chunk)
                return results
            except Exception:
                # If dense retrieval fails at runtime, continue to TF-IDF fallback
                pass

        # TF-IDF fallback retrieval
        if self.tfidf_vectorizer is None or self.tfidf_matrix is None:
            all_texts = [c["text"] for c in self.chunks]
            self.tfidf_vectorizer = TfidfVectorizer().fit(all_texts)
            self.tfidf_matrix = self.tfidf_vectorizer.transform(all_texts)

        q_vec = self.tfidf_vectorizer.transform([query_text])
        similarities = cosine_similarity(q_vec, self.tfidf_matrix)[0]
        top_indices = np.argsort(similarities)[::-1][:k]

        results = []
        for idx in top_indices:
            chunk = dict(self.chunks[idx])
            chunk["score"] = float(similarities[idx])
            chunk["retrieval_method"] = "tfidf_fallback"
            results.append(chunk)
        return results

    def clear(self) -> None:
        """Resets the vector index."""
        self.chunks = []
        self.dense_embeddings = None
        self.use_dense = False
        self.tfidf_vectorizer = None
        self.tfidf_matrix = None
