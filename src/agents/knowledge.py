"""Knowledge Agent - Vector retrieval via ChromaDB and real-time web search."""
import json
import logging
import os
import re
from typing import List, Dict, Any, Optional

import chromadb
from src.config import settings

logger = logging.getLogger("multiagent.knowledge")


STOPWORDS = {
    # Artigos e preposições (PT)
    "de", "da", "do", "das", "dos", "o", "a", "os", "as", "um", "uma", "uns", "umas",
    "em", "na", "no", "nas", "nos", "por", "para", "com", "como", "e", "ou", "que",
    "se", "ao", "aos", "à", "às", "pelo", "pela", "pelos", "pelas", "num", "numa",
    # Pronomes e interrogativos (PT)
    "qual", "quais", "quem", "onde", "quando", "quanto", "quantos", "quanta", "quantas",
    "meu", "minha", "meus", "minhas", "seu", "sua", "seus", "suas", "nosso", "nossa",
    "este", "esta", "estes", "estas", "esse", "essa", "esses", "essas", "aquele", "aquela",
    "isso", "isto", "aquilo", "ele", "ela", "eles", "elas", "você", "voces", "vocês",
    # Verbos auxiliares e genéricos frequentes (PT)
    "é", "são", "era", "eram", "foi", "ser", "estar", "está", "estao", "estão",
    "ter", "tem", "temos", "têm", "tinha", "fazer", "faz", "faco", "faço", "fizer",
    "posso", "pode", "podem", "consigo", "consegue", "conseguem", "sobre", "entre", "sem",
    # Stopwords (EN)
    "the", "a", "an", "in", "on", "at", "for", "with", "to", "of", "and", "is", "are",
    "what", "how", "between", "from", "by", "this", "that", "it", "my", "your", "can",
    "do", "does", "did", "have", "has", "will", "would", "should"
}


class ChromaDBKnowledgeRetriever:
    """Document retriever combining ChromaDB vector embeddings with lexical hybrid ranking."""

    COLLECTION_NAME = "getnet_kb"

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path or settings.KB_DATA_PATH
        self.raw_documents: List[Dict[str, Any]] = []
        self._init_chroma()
        self.documents = self.raw_documents

    def _load_documents_from_file(self) -> List[Dict[str, Any]]:
        candidate_paths = [
            self.data_path,
            os.path.join(os.getcwd(), "data", "getnet_kb.json"),
            os.path.join(os.path.dirname(__file__), "..", "..", "data", "getnet_kb.json"),
        ]

        for path in candidate_paths:
            if path and os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        docs = json.load(f)
                    logger.info(f"Loaded {len(docs)} documents from {path}")
                    return docs
                except Exception as e:
                    logger.error(f"Error reading knowledge base at {path}: {e}")

        logger.warning("Could not load knowledge base file from candidate paths. Using default documents.")
        return [
            {
                "id": "kb_fallback",
                "title": "Getnet Visão Geral",
                "category": "Geral",
                "url": "https://www.getnet.net",
                "content": "A Getnet é uma empresa do grupo PagoNxt (Santander) com soluções de maquininhas, Pix dinâmico, antecipação de recebíveis, crediário e link de pagamento."
            }
        ]

    def _init_chroma(self):
        self.raw_documents = self._load_documents_from_file()
        try:
            if getattr(settings, "CHROMA_PERSIST_DIR", ""):
                self.client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_DIR)
            else:
                self.client = chromadb.Client()
            self.collection = self.client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"}
            )

            if self.collection.count() == 0 and self.raw_documents:
                ids = [d["id"] for d in self.raw_documents]
                documents = [f"{d['title']}. Categoria: {d.get('category', '')}. {d['content']}" for d in self.raw_documents]
                metadatas = [
                    {
                        "id": d["id"],
                        "title": d["title"],
                        "category": d.get("category", ""),
                        "url": d.get("url", ""),
                        "content": d["content"]
                    }
                    for d in self.raw_documents
                ]
                self.collection.add(ids=ids, documents=documents, metadatas=metadatas)
                logger.info(f"ChromaDB initialized with {self.collection.count()} embedded documents in collection '{self.COLLECTION_NAME}'")
            else:
                logger.info(f"ChromaDB collection '{self.COLLECTION_NAME}' ready with {self.collection.count()} documents.")
            self.chroma_ready = True
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB collection: {e}. Falling back to lexical retriever.")
            self.chroma_ready = False

    def retrieve(self, query: str, top_k: int = 3, threshold: float = 0.20) -> List[Dict[str, Any]]:
        """Dense vector search combined with title and token overlap ranking, with similarity threshold."""
        if self.chroma_ready and self.raw_documents:
            try:
                results = self.collection.query(
                    query_texts=[query],
                    n_results=len(self.raw_documents)
                )

                if results and "ids" in results and results["ids"] and results["ids"][0]:
                    vec_ids = results["ids"][0]
                    distances = results["distances"][0] if "distances" in results and results["distances"] else [0.0] * len(vec_ids)

                    q_tokens = set(re.findall(r"\w+", query.lower()))
                    content_q_tokens = {w for w in q_tokens if w not in STOPWORDS and len(w) > 2}

                    scored = []
                    for doc_id, dist in zip(vec_ids, distances):
                        d_val = float(dist) if dist is not None else 0.0
                        cos_sim = max(0.0, 1.0 - d_val)
                        doc = next((d for d in self.raw_documents if d["id"] == doc_id), None)
                        if not doc:
                            continue

                        doc_tokens = set(re.findall(r"\w+", f"{doc.get('title', '')} {doc.get('content', '')}".lower()))
                        title_tokens = set(re.findall(r"\w+", doc.get("title", "").lower()))

                        lex_overlap = len(content_q_tokens.intersection(doc_tokens)) if content_q_tokens else len(q_tokens.intersection(doc_tokens))
                        title_overlap = len(content_q_tokens.intersection(title_tokens)) if content_q_tokens else len(q_tokens.intersection(title_tokens))

                        lexical_ratio = (lex_overlap / max(1, len(content_q_tokens))) if content_q_tokens else 0.0
                        title_ratio = (title_overlap / max(1, len(content_q_tokens))) if content_q_tokens else 0.0

                        hybrid_score = (cos_sim * 0.60) + (lexical_ratio * 0.25) + (title_ratio * 0.15)

                        scored.append({
                            "id": doc_id,
                            "title": doc.get("title", ""),
                            "category": doc.get("category", ""),
                            "url": doc.get("url", ""),
                            "content": doc.get("content", ""),
                            "distance": round(d_val, 4),
                            "similarity": round(cos_sim, 4),
                            "score": round(hybrid_score, 4),
                            "lex_overlap": lex_overlap,
                            "retrieval_mode": "vector"
                        })

                    scored.sort(key=lambda x: x["score"], reverse=True)
                    top_candidates = scored[:top_k]

                    if not top_candidates:
                        return []

                    top_cos_sim = top_candidates[0]["similarity"]
                    top_score = top_candidates[0]["score"]
                    top_lex_overlap = top_candidates[0]["lex_overlap"]

                    # 1. Purely mathematical semantic check:
                    # If query has substantive tokens but zero overlap with the corpus
                    # AND the vector cosine similarity is insignificant (< 0.55), the inquiry is out-of-domain.
                    if content_q_tokens and top_lex_overlap == 0 and top_cos_sim < 0.55:
                        logger.info(
                            f"RAG mathematically abstained for query '{query}': zero substantive term overlap and cosine similarity {top_cos_sim:.4f} < 0.55"
                        )
                        return []

                    # 2. General hybrid score threshold
                    if top_score < threshold:
                        logger.info(
                            f"RAG abstained for query '{query}': top score {top_score:.4f} below threshold {threshold:.2f}"
                        )
                        return []

                    return top_candidates
            except Exception as e:
                logger.error(f"Error executing hybrid ChromaDB query: {e}. Executing lexical fallback.")

        fallback_docs = self._lexical_fallback(query, top_k=top_k)
        if not fallback_docs or fallback_docs[0]["score"] < 1.0:
            return []
        return fallback_docs

    def _lexical_fallback(self, query: str, top_k: int = 2) -> List[Dict[str, Any]]:
        logger.warning(f"Falling back to lexical retrieval for query: '{query}'")
        q_tokens = set(re.findall(r"\w+", query.lower()))
        content_q_tokens = {w for w in q_tokens if w not in STOPWORDS and len(w) > 2}
        if not content_q_tokens:
            return []

        scored = []
        for doc in self.raw_documents:
            doc_words = set(re.findall(r"\w+", f"{doc.get('title', '')} {doc.get('content', '')}".lower()))
            title_words = set(re.findall(r"\w+", doc.get("title", "").lower()))
            overlap = len(content_q_tokens.intersection(doc_words))
            title_overlap = len(content_q_tokens.intersection(title_words))

            if overlap > 0:
                density = overlap / len(content_q_tokens)
                score = float(overlap) + (density * 2.0) + (title_overlap * 1.5)
                scored.append({
                    "id": doc.get("id"),
                    "title": doc.get("title"),
                    "category": doc.get("category"),
                    "url": doc.get("url"),
                    "content": doc.get("content"),
                    "score": round(score, 4),
                    "density": round(density, 4),
                    "retrieval_mode": "lexical_fallback"
                })
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]


_retriever_instance: Optional[ChromaDBKnowledgeRetriever] = None


def get_retriever() -> ChromaDBKnowledgeRetriever:
    """Dependency getter for knowledge retriever."""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = ChromaDBKnowledgeRetriever()
    return _retriever_instance
