import os
import shutil
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from pydantic import BaseModel

from app.models.schemas import DocumentItem, RAGQueryRequest, RAGQueryResponse
from app.services.rag_service import rag_service
from app.core.database import db_manager

router = APIRouter(prefix="/api/rag", tags=["Knowledge Base & RAG"])

UPLOAD_DIR = "./data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("/documents", response_model=List[DocumentItem])
async def list_documents():
    docs = await db_manager.get_all("documents")
    return docs

@router.post("/upload", response_model=DocumentItem, status_code=status.HTTP_201_CREATED)
async def upload_document(file: UploadFile = File(...)):
    filename = file.filename
    ext = os.path.splitext(filename)[1].lower()

    if ext not in [".pdf", ".txt"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file format. Please upload a PDF (.pdf) or Plain Text (.txt) file."
        )

    file_path = os.path.join(UPLOAD_DIR, filename)
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size_kb = round(os.path.getsize(file_path) / 1024.0, 2)

        # Ingest into vector store
        if ext == ".pdf":
            chunk_count = rag_service.extract_and_ingest_pdf(file_path, filename)
        else:
            chunk_count = rag_service.extract_and_ingest_txt(file_path, filename)

        doc_record = {
            "filename": filename,
            "file_type": ext.replace(".", ""),
            "chunk_count": chunk_count,
            "file_size_kb": file_size_kb
        }

        doc_id = await db_manager.insert("documents", doc_record)
        return await db_manager.get_by_id("documents", doc_id) or {**doc_record, "_id": doc_id}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process document: {str(e)}"
        )

@router.post("/query", response_model=RAGQueryResponse)
async def query_knowledge_base(req: RAGQueryRequest):
    results = rag_service.query(req.query, top_k=req.top_k)
    return RAGQueryResponse(query=req.query, results=results)

@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    doc = await db_manager.get_by_id("documents", doc_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    
    file_path = os.path.join(UPLOAD_DIR, doc.get("filename", ""))
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass

    await db_manager.delete("documents", doc_id)
    return {"message": "Document removed from knowledge base", "id": doc_id}
