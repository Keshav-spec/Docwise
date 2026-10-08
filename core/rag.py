from typing import List, Dict, Any, Optional
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

_cached_working_model: Optional[str] = None

def get_candidate_models(api_key: str, preferred: Optional[str] = None) -> List[str]:
    """
    Returns an ordered list of candidate model names:
    1. Cached working model (if known)
    2. Preferred model from configuration
    3. Models discovered dynamically from the Gemini ModelService
    4. Standard fallback names
    """
    global _cached_working_model
    candidates: List[str] = []

    if _cached_working_model:
        candidates.append(_cached_working_model)

    if preferred and preferred.strip():
        pref = preferred.strip().replace("models/", "")
        if pref not in candidates:
            candidates.append(pref)

    # Discover models enabled for this specific API key via ListModels
    try:
        genai.configure(api_key=api_key.strip())
        for m in genai.list_models():
            methods = getattr(m, "supported_generation_methods", [])
            if "generateContent" in methods:
                clean_name = m.name.replace("models/", "")
                if clean_name not in candidates:
                    candidates.append(clean_name)
    except Exception:
        pass

    # Built-in fallback candidates in order of capability
    standard_fallbacks = [
        "gemini-3-flash-preview",
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-flash-latest",
        "gemini-1.5-flash",
        "gemini-1.5-pro-latest",
        "gemini-1.5-pro",
        "gemini-pro"
    ]
    for fb in standard_fallbacks:
        if fb not in candidates:
            candidates.append(fb)

    return candidates

def generate_with_fallback(
    api_key: str,
    prompt: str,
    preferred_model: Optional[str] = None,
    system_instruction: Optional[str] = None
) -> str:
    """
    Executes content generation with automatic model fallback if a 404 Not Found
    or unsupported model error is encountered.
    """
    global _cached_working_model
    candidates = get_candidate_models(api_key, preferred_model)
    last_error: Optional[Exception] = None

    genai.configure(api_key=api_key.strip())

    for model_name in candidates:
        try:
            try:
                if system_instruction:
                    model = genai.GenerativeModel(
                        model_name=model_name,
                        system_instruction=system_instruction
                    )
                else:
                    model = genai.GenerativeModel(model_name=model_name)
                response = model.generate_content(prompt)
            except Exception as e_inner:
                err_str = str(e_inner).lower()
                if "system_instruction" in err_str:
                    # Retry without system_instruction parameter for older model APIs
                    model = genai.GenerativeModel(model_name=model_name)
                    combined_prompt = f"{system_instruction}\n\n{prompt}" if system_instruction else prompt
                    response = model.generate_content(combined_prompt)
                else:
                    raise e_inner

            if response and response.text:
                _cached_working_model = model_name
                return response.text
        except Exception as e:
            last_error = e
            err_msg = str(e).lower()
            # If model is 404 or unsupported, continue trying next candidate
            if "404" in err_msg or "not found" in err_msg or "not supported" in err_msg:
                continue
            # If authentication or quota failure, do not retry other models pointlessly
            if "quota" in err_msg or "api_key" in err_msg or "permission" in err_msg or "invalid api key" in err_msg:
                raise e
            continue

    if last_error:
        raise last_error
    raise RuntimeError("No compatible Gemini model could be reached.")

def answer_question_with_citations(
    vector_store: VectorStore,
    question: str,
    api_key: str,
    model_name: str = DEFAULT_GENERATION_MODEL,
    top_k: int = DEFAULT_TOP_K
) -> Dict[str, Any]:
    """
    Performs semantic retrieval against the vector store and synthesizes an answer
    with explicit page citations using Gemini with automatic model fallback.
    """
    if not api_key or not api_key.strip():
        return {
            "answer": "Error: Gemini API key is required. Please set GEMINI_API_KEY in the environment.",
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
        answer_text = generate_with_fallback(
            api_key=api_key,
            prompt=prompt,
            preferred_model=model_name,
            system_instruction=SYSTEM_INSTRUCTION
        )

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
    Generates an executive summary and 3-4 starter questions for a newly uploaded document
    using automatic model fallback.
    """
    if not api_key or not api_key.strip() or not pages:
        return {
            "summary": "Document indexed successfully. Configure GEMINI_API_KEY to view automated summary and suggested questions.",
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
        raw_text = generate_with_fallback(
            api_key=api_key,
            prompt=prompt,
            preferred_model=model_name
        )

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
