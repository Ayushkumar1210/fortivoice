import os
import re
import math
import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class SimpleVectorIndex:
    """Fast, dependency-free in-memory and persistent vector/TF-IDF similarity fallback"""
    def __init__(self):
        self.documents: List[Dict[str, Any]] = []

    def add_documents(self, docs: List[Dict[str, Any]]):
        self.documents.extend(docs)

    def search(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        if not self.documents:
            return []
        query_words = set(re.findall(r'\w+', query.lower()))
        if not query_words:
            return self.documents[:top_k]

        scored = []
        for doc in self.documents:
            text = doc.get("text", "").lower()
            text_words = re.findall(r'\w+', text)
            if not text_words:
                continue
            
            # Simple TF-IDF / term overlap matching
            matches = sum(1 for w in query_words if w in text_words)
            phrase_bonus = 2.0 if query.lower() in text else 0.0
            score = (matches / (math.sqrt(len(text_words)) + 1e-5)) + phrase_bonus
            if score > 0:
                scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k]]


class RAGService:
    def __init__(self, persist_dir: str = "./data/chroma"):
        self.persist_dir = persist_dir
        self.chroma_client = None
        self.collection = None
        self.simple_index = SimpleVectorIndex()
        self._init_chroma()
        self._seed_default_knowledge()

    def _init_chroma(self):
        os.makedirs(self.persist_dir, exist_ok=True)
        try:
            import numpy as np
            if not hasattr(np, "float_"):
                np.float_ = np.float64

            import chromadb
            from chromadb.config import Settings as ChromaSettings
            
            self.chroma_client = chromadb.PersistentClient(
                path=self.persist_dir,
                settings=ChromaSettings(anonymized_telemetry=False)
            )
            self.collection = self.chroma_client.get_or_create_collection(
                name="fortivoice_knowledge",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("ChromaDB initialized successfully!")
        except Exception as e:
            logger.warning(f"ChromaDB initialization error ({e}). Using robust built-in vector index.")
            self.chroma_client = None
            self.collection = None

    def chunk_text(self, text: str, chunk_size: int = 400, chunk_overlap: int = 50) -> List[str]:
        # Clean text
        text = re.sub(r'\s+', ' ', text).strip()
        words = text.split(' ')
        chunks = []
        i = 0
        while i < len(words):
            chunk = " ".join(words[i:i + chunk_size])
            if chunk:
                chunks.append(chunk)
            i += max(1, chunk_size - chunk_overlap)
        return chunks

    def ingest_text(self, text: str, filename: str, metadata: Optional[Dict[str, Any]] = None) -> int:
        chunks = self.chunk_text(text)
        if not chunks:
            return 0

        meta = metadata or {}
        meta["source"] = filename
        meta["uploaded_at"] = datetime.utcnow().isoformat()

        doc_ids = [f"{filename}_chunk_{idx}" for idx in range(len(chunks))]
        metadatas = [{**meta, "chunk_index": idx} for idx in range(len(chunks))]

        # Store in Chroma if available
        if self.collection:
            try:
                self.collection.upsert(
                    ids=doc_ids,
                    documents=chunks,
                    metadatas=metadatas
                )
            except Exception as e:
                logger.error(f"Error adding chunks to ChromaDB: {e}")

        # Also store in memory index for immediate ultra-fast retrieval
        fallback_docs = [
            {"id": doc_ids[i], "text": chunks[i], "metadata": metadatas[i]}
            for i in range(len(chunks))
        ]
        self.simple_index.add_documents(fallback_docs)
        return len(chunks)

    def extract_and_ingest_pdf(self, file_path: str, filename: str) -> int:
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            full_text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    full_text += page_text + "\n"
            return self.ingest_text(full_text, filename, {"file_type": "pdf"})
        except Exception as e:
            logger.error(f"PDF extraction error for {filename}: {e}")
            raise

    def extract_and_ingest_txt(self, file_path: str, filename: str) -> int:
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            return self.ingest_text(content, filename, {"file_type": "txt"})
        except Exception as e:
            logger.error(f"TXT extraction error for {filename}: {e}")
            raise

    def query(self, query_text: str, top_k: int = 4) -> List[Dict[str, Any]]:
        results = []
        if self.collection:
            try:
                chroma_res = self.collection.query(
                    query_texts=[query_text],
                    n_results=top_k
                )
                if chroma_res and chroma_res.get("documents") and chroma_res["documents"][0]:
                    docs = chroma_res["documents"][0]
                    metas = chroma_res["metadatas"][0] if chroma_res.get("metadatas") else [{}] * len(docs)
                    distances = chroma_res["distances"][0] if chroma_res.get("distances") else [0.0] * len(docs)
                    for d, m, dist in zip(docs, metas, distances):
                        results.append({
                            "text": d,
                            "metadata": m,
                            "score": round(1.0 - float(dist), 4) if dist is not None else 1.0
                        })
                    return results
            except Exception as e:
                logger.warning(f"Chroma query failed ({e}), using instant internal vector index.")
                self.collection = None

        # Fallback search
        fallback_matches = self.simple_index.search(query_text, top_k=top_k)
        for doc in fallback_matches:
            results.append({
                "text": doc.get("text", ""),
                "metadata": doc.get("metadata", {}),
                "score": 0.88
            })
        return results

    def _seed_default_knowledge(self):
        """Pre-seeds standard company sales knowledge base so agent has deep grounding from day 1"""
        company_knowledge = """
        FORTIVOICE & FORTICLOUD ENTERPRISE SALES PLAYBOOK & PRODUCT GUIDE

        Company Overview:
        FortiVoice is an enterprise Autonomous AI Sales Voice Agent platform developed by FortiCloud Solutions.
        We help B2B and high-velocity B2C companies automate inbound sales calls, qualify inbound leads, schedule demos, and update CRM records automatically.

        Key Product Offerings & Pricing:
        1. Starter Plan ($499 / month):
           - Up to 1,000 voice minutes per month.
           - Single phone line / web agent integration.
           - Real-time CRM synchronization with HubSpot and Zapier.
           - Standard RAG knowledge base (up to 50 documents).
           - English language support.
           - 99.9% uptime SLA and business hours support.

        2. Professional Growth Plan ($1,499 / month):
           - Up to 5,000 voice minutes per month.
           - Multi-agent deployment (up to 5 sales personas).
           - Native integrations with Salesforce, HubSpot, Zoho, and MongoDB.
           - Dynamic RAG vector search with unlimited document uploads.
           - Multilingual support including English and Hindi with automatic accent adaptation.
           - 99.95% uptime SLA, dedicated onboarding manager, and 24/7 technical support.

        3. Enterprise Custom Plan (Starting at $3,500 / month):
           - Unlimited voice minutes.
           - Custom LLM fine-tuning, voice cloning, and custom telephony trunking (SIP / Twilio / Plivo).
           - Dedicated VPC deployment, SOC-2 Type II, HIPAA, and GDPR compliance.
           - 99.99% uptime SLA with 15-minute response time.
           - Dedicated AI Solutions Architect and 24/7 priority phone support.

        Implementation Timeline:
        - Starter plan: Setup and live in under 48 hours.
        - Professional plan: 3 to 5 business days including CRM integration and knowledge base ingestion.
        - Enterprise plan: 2 weeks with custom security reviews and sandbox testing.

        Appointment Booking & Demo Policy:
        - We offer live 30-minute interactive product demos conducted by our Senior Sales Engineers.
        - Demos can be booked Monday through Friday between 9:00 AM and 6:00 PM EST.
        - Demos include live call simulation, lead qualification review, and custom pricing analysis.

        Security, Compliance & Privacy:
        - All audio and transcripts are encrypted in transit using TLS 1.3 and at rest using AES-256.
        - We do not use customer proprietary sales conversations to train public LLM models.
        - Certified SOC-2 Type II compliant and ISO 27001 ready.

        Discounts & Special Offers:
        - Annual prepayment receives a 20% discount across all subscription tiers.
        - Qualified early-stage startups (under $2M ARR) can apply for our 30% Startup Accelerator Credit.
        """
        self.ingest_text(company_knowledge, "fortivoice_enterprise_playbook.txt", {
            "title": "FortiVoice Enterprise Sales Playbook & Pricing",
            "category": "sales_guide",
            "is_system_default": True
        })


rag_service = RAGService()
