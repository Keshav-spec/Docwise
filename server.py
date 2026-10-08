import os
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from core.config import (
    DEFAULT_GENERATION_MODEL,
    DEFAULT_EMBEDDING_MODEL,
    DEFAULT_CHUNK_SIZE,
    DEFAULT_CHUNK_OVERLAP,
    DEFAULT_TOP_K,
    get_api_key
)
from core.extractor import extract_text_from_pdf_stream
from core.chunker import chunk_pages
from core.embeddings import VectorStore
from core.rag import answer_question_with_citations, summarize_document

app = FastAPI(title="Docwise API", version="2.0.0")

# In-memory document and vector store session
vector_store = VectorStore(embedding_model=DEFAULT_EMBEDDING_MODEL)
uploaded_documents = []
chat_history = []
runtime_api_key = get_api_key()

class QueryRequest(BaseModel):
    question: str
    api_key: Optional[str] = None
    model_name: Optional[str] = DEFAULT_GENERATION_MODEL
    top_k: Optional[int] = DEFAULT_TOP_K

class ConfigRequest(BaseModel):
    api_key: str
    model_name: Optional[str] = DEFAULT_GENERATION_MODEL

@app.get("/api/status")
def get_status():
    global runtime_api_key
    has_key = bool(runtime_api_key and runtime_api_key.strip())
    return {
        "status": "online",
        "has_api_key": has_key,
        "default_model": DEFAULT_GENERATION_MODEL,
        "indexed_documents_count": len(uploaded_documents),
        "indexed_chunks_count": len(vector_store.chunks),
        "use_dense_embeddings": vector_store.use_dense
    }

@app.post("/api/config")
def update_config(config: ConfigRequest):
    global runtime_api_key
    if config.api_key:
        runtime_api_key = config.api_key.strip()
    return {"message": "Configuration updated successfully", "has_api_key": bool(runtime_api_key)}

@app.post("/api/upload")
async def upload_pdf(
    file: UploadFile = File(...),
    api_key: Optional[str] = Form(None)
):
    global runtime_api_key, uploaded_documents, vector_store
    active_key = api_key.strip() if api_key and api_key.strip() else runtime_api_key

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        extraction_result = extract_text_from_pdf_stream(content, filename=file.filename)
        pages = extraction_result["pages"]

        if not pages or extraction_result["total_characters"] == 0:
            raise HTTPException(status_code=400, detail="Could not extract text. The document may be scanned or empty.")

        chunks = chunk_pages(
            pages=pages,
            doc_name=file.filename,
            chunk_size=DEFAULT_CHUNK_SIZE,
            chunk_overlap=DEFAULT_CHUNK_OVERLAP
        )

        vector_store.add_chunks(chunks, api_key=active_key)

        doc_summary_data = summarize_document(
            pages=pages,
            doc_name=file.filename,
            api_key=active_key,
            model_name=DEFAULT_GENERATION_MODEL
        )

        doc_meta = {
            "filename": file.filename,
            "total_pages": extraction_result["total_pages"],
            "total_characters": extraction_result["total_characters"],
            "chunk_count": len(chunks),
            "summary": doc_summary_data["summary"],
            "starter_questions": doc_summary_data["starter_questions"]
        }
        uploaded_documents.append(doc_meta)

        return {
            "message": "File processed and indexed successfully",
            "document": doc_meta,
            "total_indexed_chunks": len(vector_store.chunks),
            "dense_embeddings_active": vector_store.use_dense
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.post("/api/query")
def query_document(req: QueryRequest):
    global runtime_api_key, chat_history, vector_store
    active_key = req.api_key.strip() if req.api_key and req.api_key.strip() else runtime_api_key

    if not active_key:
        raise HTTPException(status_code=400, detail="Gemini API key is not configured. Please enter your API key.")

    if not vector_store.chunks:
        raise HTTPException(status_code=400, detail="No documents indexed. Please upload a PDF first.")

    result = answer_question_with_citations(
        vector_store=vector_store,
        question=req.question,
        api_key=active_key,
        model_name=req.model_name or DEFAULT_GENERATION_MODEL,
        top_k=req.top_k or DEFAULT_TOP_K
    )

    chat_entry = {
        "question": req.question,
        "answer": result["answer"],
        "citations": result["citations"],
        "retrieval_method": result["retrieval_method"]
    }
    chat_history.append(chat_entry)

    return chat_entry

@app.get("/api/history")
def get_history():
    return {"history": chat_history}

@app.post("/api/clear")
def clear_session():
    global uploaded_documents, chat_history, vector_store
    vector_store.clear()
    uploaded_documents = []
    chat_history = []
    return {"message": "Session reset successfully"}

@app.get("/api/export")
def export_history(format: str = "markdown"):
    if format == "json":
        return JSONResponse(content={"chat_history": chat_history, "documents": uploaded_documents})

    lines = ["# Docwise Conversation Export", ""]
    if uploaded_documents:
        lines.append("## Indexed Documents")
        for doc in uploaded_documents:
            lines.append(f"- {doc['filename']} ({doc['total_pages']} pages, {doc['chunk_count']} chunks)")
        lines.append("")

    lines.append("## Q&A Log")
    for idx, item in enumerate(chat_history, 1):
        lines.append(f"### Question {idx}: {item['question']}")
        lines.append("")
        lines.append(f"**Answer:** {item['answer']}")
        lines.append("")
        if item.get("citations"):
            lines.append("**Sources & Citations:**")
            for c in item["citations"]:
                lines.append(f"- Page {c['page_num']} ({c['doc_name']}): \"{c['snippet']}\"")
        lines.append("")
        lines.append("---")
        lines.append("")

    return {"content": "\n".join(lines)}

# Mount static frontend
web_dir = os.path.join(os.path.dirname(__file__), "web")
if os.path.exists(web_dir):
    app.mount("/static", StaticFiles(directory=web_dir), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(web_dir, "index.html"))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
