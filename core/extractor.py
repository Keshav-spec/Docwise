from typing import Dict, List, Any
import fitz

def extract_text_from_pdf_stream(pdf_bytes: bytes, filename: str = "document.pdf") -> Dict[str, Any]:
    """
    Extracts text page-by-page from PDF bytes while preserving page numbers and metadata.
    Returns document statistics and a list of page objects.
    """
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages: List[Dict[str, Any]] = []
    total_characters = 0

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        raw_text = page.get_text() or ""
        cleaned_text = " ".join(raw_text.split())
        
        char_count = len(cleaned_text)
        total_characters += char_count

        pages.append({
            "page_num": page_idx + 1,
            "text": cleaned_text,
            "raw_text": raw_text,
            "char_count": char_count
        })

    doc.close()

    return {
        "filename": filename,
        "total_pages": len(pages),
        "total_characters": total_characters,
        "pages": pages
    }
