import os
from typing import List, Optional
from fastapi import FastAPI, UploadFile, File, HTTPException
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

class QueryRequest(BaseModel):
    question: str
    top_k: Optional[int] = DEFAULT_TOP_K

@app.get("/api/status")
def get_status():
    server_key = get_api_key()
    return {
        "status": "online",
        "has_api_key": bool(server_key),
        "model": DEFAULT_GENERATION_MODEL,
        "indexed_documents_count": len(uploaded_documents),
        "indexed_chunks_count": len(vector_store.chunks),
        "use_dense_embeddings": vector_store.use_dense
    }

@app.post("/api/upload")
async def upload_pdf(file: UploadFile = File(...)):
    global uploaded_documents, vector_store
    server_key = get_api_key()

    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    try:
        extraction_result = extract_text_from_pdf_stream(content, filename=file.filename)
        pages = extraction_result["pages"]

        if not pages or extraction_result["total_characters"] == 0:
            raise HTTPException(status_code=400, detail="Could not extract readable text. The document may be scanned or empty.")

        chunks = chunk_pages(
            pages=pages,
            doc_name=file.filename,
            chunk_size=DEFAULT_CHUNK_SIZE,
            chunk_overlap=DEFAULT_CHUNK_OVERLAP
        )

        vector_store.add_chunks(chunks, api_key=server_key)

        doc_summary_data = summarize_document(
            pages=pages,
            doc_name=file.filename,
            api_key=server_key,
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
    global chat_history, vector_store
    server_key = get_api_key()

    if not server_key:
        raise HTTPException(
            status_code=500,
            detail="Server configuration error: GEMINI_API_KEY environment variable is not configured."
        )

    if not vector_store.chunks:
        raise HTTPException(status_code=400, detail="No documents indexed. Please upload a PDF first.")

    result = answer_question_with_citations(
        vector_store=vector_store,
        question=req.question,
        api_key=server_key,
        model_name=DEFAULT_GENERATION_MODEL,
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
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
