from typing import List, Dict, Any
import google.generativeai as genai
from core.config import DEFAULT_GENERATION_MODEL, DEFAULT_TOP_K
from core.embeddings import VectorStore

SYSTEM_INSTRUCTION = (
    "You are Docwise, an AI document assistant. Answer the user's question accurately "
    "and concisely using only the provided document excerpts. When referencing information, "
    "explicitly mention the page number using the format [Page X]. If the answer cannot be "
    "found in the excerpts, state clearly that the document does not contain that information. "
    "Do not extrapolate or fabricate facts."
)

def answer_question_with_citations(
    vector_store: VectorStore,
    question: str,
    api_key: str,
    model_name: str = DEFAULT_GENERATION_MODEL,
    top_k: int = DEFAULT_TOP_K
) -> Dict[str, Any]:
    """
    Performs semantic retrieval against the vector store and synthesizes an answer
    with explicit page citations using Gemini.
    """
    if not api_key or not api_key.strip():
        return {
            "answer": "Error: Gemini API key is required. Please provide a valid API key in settings or environment.",
            "citations": [],
            "retrieval_method": "none"
        }

    relevant_chunks = vector_store.query(question, api_key=api_key, top_k=top_k)
    if not relevant_chunks:
        return {
            "answer": "No indexed document chunks found. Please upload a PDF first.",
            "citations": [],
            "retrieval_method": "none"
        }

    formatted_context_parts = []
    citations = []

    for chunk in relevant_chunks:
        page_num = chunk.get("page_num", 1)
        doc_name = chunk.get("doc_name", "Document")
        snippet = chunk.get("text", "")
        score = chunk.get("score", 0.0)

        formatted_context_parts.append(
            f"--- Source: {doc_name} | Page {page_num} ---\n{snippet}"
        )
        citations.append({
            "doc_name": doc_name,
            "page_num": page_num,
            "snippet": snippet[:200] + ("..." if len(snippet) > 200 else ""),
            "score": round(score, 4)
        })

    context_str = "\n\n".join(formatted_context_parts)
    prompt = f"""Document Excerpts:
{context_str}

User Question:
{question}

Provide an accurate, well-structured answer with page citations [Page X]."""

    try:
        genai.configure(api_key=api_key.strip())
        model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=SYSTEM_INSTRUCTION
        )
        response = model.generate_content(prompt)
        answer_text = response.text if response and response.text else "No response generated."

        return {
            "answer": answer_text,
            "citations": citations,
            "retrieval_method": relevant_chunks[0].get("retrieval_method", "unknown")
        }
    except Exception as e:
        return {
            "answer": f"API Error while generating answer: {str(e)}",
            "citations": citations,
            "retrieval_method": relevant_chunks[0].get("retrieval_method", "unknown")
        }

def summarize_document(
    pages: List[Dict[str, Any]],
    doc_name: str,
    api_key: str,
    model_name: str = DEFAULT_GENERATION_MODEL
) -> Dict[str, Any]:
    """
    Generates an executive summary and 3-4 starter questions for a newly uploaded document.
    """
    if not api_key or not api_key.strip() or not pages:
        return {
            "summary": "Document indexed successfully. Provide an API key to view automated summary and suggested questions.",
            "starter_questions": [
                "What is the main topic of this document?",
                "What are the key conclusions or findings?",
                "Can you provide an overview of the contents?"
            ]
        }

    sample_text_parts = []
    char_limit = 6000
    current_chars = 0

    for page in pages:
        text = page.get("text", "")
        if current_chars + len(text) > char_limit:
            remaining = char_limit - current_chars
            if remaining > 100:
                sample_text_parts.append(text[:remaining])
            break
        sample_text_parts.append(text)
        current_chars += len(text)

    content_sample = "\n\n".join(sample_text_parts)

    prompt = f"""Analyze the following excerpt from document '{doc_name}':

{content_sample}

Task:
1. Provide a concise 2-3 paragraph executive summary of the document.
2. Provide 3 relevant, insightful questions that a user might ask about this document.

Format your output strictly as:
SUMMARY:
[Your summary here]

QUESTIONS:
- [Question 1]
- [Question 2]
- [Question 3]"""

    try:
        genai.configure(api_key=api_key.strip())
        model = genai.GenerativeModel(model_name=model_name)
        response = model.generate_content(prompt)
        raw_text = response.text or ""

        summary = "Document analyzed successfully."
        questions = []

        if "SUMMARY:" in raw_text and "QUESTIONS:" in raw_text:
            parts = raw_text.split("QUESTIONS:")
            summary = parts[0].replace("SUMMARY:", "").strip()
            q_lines = parts[1].strip().split("\n")
            for line in q_lines:
                clean_q = line.strip().lstrip("-*123456789. ")
                if clean_q and len(clean_q) > 5:
                    questions.append(clean_q)
        else:
            summary = raw_text.strip()

        if not questions:
            questions = [
                "What is the main objective of this document?",
                "What are the primary findings or details?",
                "Can you summarize the most important points?"
            ]

        return {
            "summary": summary,
            "starter_questions": questions[:4]
        }
    except Exception as e:
        return {
            "summary": f"Document indexed. (Summary could not be generated: {str(e)})",
            "starter_questions": [
                "What is the main topic of this document?",
                "What are the key conclusions?",
                "Can you summarize the document?"
            ]
        }
