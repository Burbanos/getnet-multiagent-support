"""Knowledge Agent - Vector retrieval via ChromaDB and real-time web search."""
import json
import logging
import os
import re
from typing import List, Dict, Any, Optional

import chromadb
from src.core.state import AgentState, AgentRole
from src.tools.web_search import web_search_tool
from src.core.llm import get_llm
from src.config import settings

logger = logging.getLogger("multiagent.knowledge")


STOPWORDS = {
    "de", "da", "do", "das", "dos", "o", "a", "os", "as", "um", "uma", "uns", "umas",
    "em", "na", "no", "nas", "nos", "por", "para", "com", "como", "e", "ou", "que",
    "se", "qual", "quais", "the", "a", "an", "in", "on", "at", "for", "with", "to",
    "of", "and", "is", "are", "what", "how", "between"
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
                            "lex_overlap": lex_overlap
                        })

                    scored.sort(key=lambda x: x["score"], reverse=True)
                    top_candidates = scored[:top_k]

                    # Filter by relevance threshold and domain coherence
                    if not top_candidates or top_candidates[0]["score"] < threshold:
                        logger.info(
                            f"RAG abstained for query '{query}': top score {top_candidates[0]['score'] if top_candidates else 0.0:.4f} "
                            f"below threshold {threshold:.2f}"
                        )
                        return []

                    # If query had content tokens but none overlapped and semantic similarity is weak (< 0.50), abstain
                    if content_q_tokens and top_candidates[0]["lex_overlap"] == 0 and top_candidates[0]["similarity"] < 0.50:
                        logger.info(f"RAG abstained for unrelated query '{query}': no term overlap and low similarity {top_candidates[0]['similarity']}")
                        return []

                    return top_candidates
            except Exception as e:
                logger.error(f"Error executing hybrid ChromaDB query: {e}. Executing lexical fallback.")

        fallback_docs = self._lexical_fallback(query, top_k=top_k)
        if not fallback_docs or fallback_docs[0]["score"] < 1.0:
            return []
        return fallback_docs

    def _lexical_fallback(self, query: str, top_k: int = 2) -> List[Dict[str, Any]]:
        query_words = set(re.findall(r"\w+", query.lower()))
        scored = []
        for doc in self.raw_documents:
            doc_words = set(re.findall(r"\w+", f"{doc.get('title', '')} {doc.get('content', '')}".lower()))
            overlap = len(query_words.intersection(doc_words))
            scored.append({
                "id": doc.get("id"),
                "title": doc.get("title"),
                "category": doc.get("category"),
                "url": doc.get("url"),
                "content": doc.get("content"),
                "score": float(overlap)
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


class KnowledgeAgent:
    """Answers queries via ChromaDB knowledge retrieval or external web search."""

    def __init__(self):
        self.retriever = get_retriever()
        self.llm = get_llm()

    async def execute(self, state: AgentState) -> AgentState:
        message = state.message
        intent = state.route.intent if state.route else "getnet_knowledge_retrieval"

        if intent == "external_web_search" or self._is_external_query(message):
            return await self._handle_web_search(state)
        else:
            return await self._handle_rag(state)

    def _is_external_query(self, message: str) -> bool:
        lower_msg = message.lower()
        external_keywords = [
            "weather", "tempo", "previsão", "porto alegre",
            "euro", "dollar", "dólar", "exchange rate", "cotação", "cotacao"
        ]
        return any(k in lower_msg for k in external_keywords)

    async def _handle_web_search(self, state: AgentState) -> AgentState:
        logger.info(f"Knowledge Agent executing Web Search for: '{state.message}'")
        search_result = web_search_tool(state.message, max_results=settings.WEB_SEARCH_MAX_RESULTS)
        state.tools_used.append("web_search_tool")
        state.tool_results.append(search_result)

        snippets = search_result.get("results", [])
        context_str = "\n".join([f"- [{s.get('title')}]: {s.get('snippet')} (Fonte: {s.get('url')})" for s in snippets])

        for s in snippets:
            if s.get("url"):
                state.sources.append(s.get("url"))

        system_prompt = (
            "Você é o Knowledge Agent do sistema de suporte da Getnet. "
            "Responda à pergunta do usuário de forma clara, prestativa e objetiva com base nos dados externos encontrados."
        )

        user_prompt = (
            f"Pergunta do usuário: {state.message}\n\n"
            f"Dados da pesquisa na Web:\n{context_str}\n\n"
            "Elabore uma resposta amigável e direta em português:"
        )

        response_text = await self.llm.generate_text(user_prompt, system_prompt=system_prompt)
        state.agent_response = response_text
        state.final_agent = AgentRole.KNOWLEDGE
        return state

    async def _handle_rag(self, state: AgentState) -> AgentState:
        logger.info(f"Knowledge Agent executing ChromaDB RAG retrieval for: '{state.message}'")
        docs = self.retriever.retrieve(state.message, top_k=2)
        state.context_docs = docs
        state.retrieved_docs = docs
        state.tools_used.append("knowledge_retriever")
        state.tools_used.append("chromadb_vector_search")

        for d in docs:
            if d.get("url"):
                state.sources.append(d.get("url"))

        # Focus context synthesis on the primary top-1 ranked document
        primary_doc = docs[0] if docs else {}
        context_str = f"### {primary_doc.get('title', 'Getnet')}\n{primary_doc.get('content', '')}"

        system_prompt = (
            "Você é o Knowledge Agent especialista em produtos e soluções da Getnet. "
            "Seu papel é responder às dúvidas com base exclusivamente nas informações oficiais da Getnet. "
            "Seja claro, didático e profissional."
        )

        user_prompt = (
            f"Pergunta do usuário: {state.message}\n\n"
            f"Base de Conhecimento Oficial Getnet:\n{context_str}\n\n"
            "Instruções:\n"
            "- Responda a dúvida com precisão e clareza com base no artigo principal.\n"
            "- Destaque os benefícios e opções disponíveis para o lojista.\n"
            "- Responda em português com boa formatação."
        )

        response_text = await self.llm.generate_text(user_prompt, system_prompt=system_prompt)
        state.agent_response = response_text
        state.final_agent = AgentRole.KNOWLEDGE
        return state
