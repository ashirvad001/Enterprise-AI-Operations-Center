from fastapi import APIRouter, status, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
import os
import io

from ..services.vector_store import VectorStoreManager

router = APIRouter()
vector_store = VectorStoreManager()

# --- Pydantic Schemas ---
class KnowledgeBaseCreate(BaseModel):
    name: str
    description: Optional[str] = None

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5

# --- Endpoints ---
@router.post("/knowledge-bases", status_code=status.HTTP_201_CREATED)
async def create_kb(request: KnowledgeBaseCreate):
    kb_id = str(uuid.uuid4())
    return {
        "data": {
            "id": kb_id,
            "name": request.name,
            "description": request.description,
            "created_at": "2026-06-13T00:00:00Z"
        }
    }

@router.post("/knowledge-bases/{kb_id}/documents", status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    kb_id: str, 
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Accepts a file, uploads the raw bytes to MinIO, and triggers background chunking/embedding.
    """
    doc_id = str(uuid.uuid4())
    file_bytes = await file.read()
    
    # In reality, upload file_bytes to MinIO bucket 'eaioc-rag-docs'
    s3_path = f"s3://eaioc-rag-docs/{kb_id}/{doc_id}_{file.filename}"
    
    # Extract text (mocking PyPDF2 or raw read)
    try:
        text_content = file_bytes.decode('utf-8')
    except:
        text_content = "Mock extracted text from binary file."

    # Process chunks and embeddings in background
    background_tasks.add_task(vector_store.ingest_document, text_content, doc_id)

    return {
        "data": {
            "document_id": doc_id,
            "filename": file.filename,
            "s3_path": s3_path,
            "status": "processing"
        }
    }

@router.post("/search", status_code=status.HTTP_200_OK)
async def semantic_search(request: SearchRequest):
    """
    Performs a vector similarity search across all authorized knowledge bases.
    """
    # Hardcoded kb_id for mock
    results = await vector_store.search(kb_id="all", query=request.query, top_k=request.top_k)
    
    return {
        "data": results
    }
