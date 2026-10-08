from typing import List, Dict, Any
from core.config import DEFAULT_CHUNK_SIZE, DEFAULT_CHUNK_OVERLAP

def chunk_pages(
    pages: List[Dict[str, Any]],
    doc_name: str = "document.pdf",
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
) -> List[Dict[str, Any]]:
    """
    Splits page texts into contextual chunks with sliding-window overlap while associating
    each chunk with its exact page number and source document name.
    """
    chunks: List[Dict[str, Any]] = []
    chunk_counter = 0

    step_size = max(chunk_size - chunk_overlap, 100)

    for page in pages:
        page_num = page["page_num"]
        text = page["text"].strip()

        if not text:
            continue

        if len(text) <= chunk_size:
            chunk_counter += 1
            chunks.append({
                "chunk_id": chunk_counter,
                "doc_name": doc_name,
                "page_num": page_num,
                "text": text,
                "char_length": len(text)
            })
            continue

        start = 0
        text_len = len(text)
        while start < text_len:
            end = min(start + chunk_size, text_len)
            
            # If not at the end of the text, try to break at a sentence boundary or word boundary
            if end < text_len:
                boundary = text.rfind(". ", start + step_size, end)
                if boundary != -1:
                    end = boundary + 1
                else:
                    space_boundary = text.rfind(" ", start + step_size, end)
                    if space_boundary != -1:
                        end = space_boundary

            chunk_text = text[start:end].strip()
            if chunk_text:
                chunk_counter += 1
                chunks.append({
                    "chunk_id": chunk_counter,
                    "doc_name": doc_name,
                    "page_num": page_num,
                    "text": chunk_text,
                    "char_length": len(chunk_text)
                })

            if end >= text_len:
                break

            start = start + step_size

    return chunks
