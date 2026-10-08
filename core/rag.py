from typing import List, Dict, Any, Optional
import google.generativeai as genai
from core.config import DEFAULT_GENERATION_MODEL, DEFAULT_TOP_K
from core.embeddings import VectorStore

SYSTEM_INSTRUCTION = (
    "You are Docwise, an AI document intelligence assistant. Provide comprehensive, "
    "accurate, and well-structured answers using the provided document excerpts. "
    "When referencing facts, explicitly cite the source page using [Page X]. "
    "If the document is a resume or CV, identify the candidate by name, extract their "
    "professional summary, work experience, technical skills, projects, and education. "
    "Do not extrapolate or fabricate facts not present in the excerpts."
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
            if "404" in err_msg or "not found" in err_msg or "not supported" in err_msg:
                continue
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
    Performs semantic retrieval with dynamic full-document context windowing,
    structured resume/document formatting, and explicit page citations.
    """
    if not api_key or not api_key.strip():
        return {
            "answer": "Error: Gemini API key is required. Please set GEMINI_API_KEY in the environment.",
            "citations": [],
            "retrieval_method": "none"
        }

    if not vector_store.chunks:
        return {
            "answer": "No indexed document chunks found. Please upload a PDF first.",
            "citations": [],
            "retrieval_method": "none"
        }

    q_lower = question.lower().strip()
    is_summary_query = any(k in q_lower for k in [
        "summar", "overview", "who is", "whose", "what is this",
        "about this", "resume", "cv", "profile", "background",
        "experience", "skills", "tell me about", "brief", "key points"
    ])

    total_chunks = len(vector_store.chunks)

    # Dynamic context window: if the document is short (<= 15 chunks, such as a resume)
    # or if the query is a document-level summary query, supply full context to Gemini
    if total_chunks <= 15 or is_summary_query:
        if total_chunks <= 15:
            selected_chunks = []
            for i, chunk in enumerate(vector_store.chunks):
                c_copy = dict(chunk)
                # Assign strong context score for complete document retrieval
                c_copy["score"] = round(0.95 - (i * 0.02), 2)
                c_copy["retrieval_method"] = "full_document_context"
                selected_chunks.append(c_copy)
        else:
            # For larger documents with a summary query, combine first chunks with top semantic matches
            top_matches = vector_store.query(question, api_key=api_key, top_k=max(top_k, 8))
            lead_chunks = vector_store.chunks[:2]
            combined_dict = {}
            for c in lead_chunks:
                c_dict = dict(c)
                c_dict["score"] = 0.90
                c_dict["retrieval_method"] = "lead_context"
                combined_dict[c_dict["chunk_id"]] = c_dict
            for c in top_matches:
                combined_dict[c["chunk_id"]] = c
            selected_chunks = list(combined_dict.values())
    else:
        selected_chunks = vector_store.query(question, api_key=api_key, top_k=top_k)

    formatted_context_parts = []
    citations = []

    for chunk in selected_chunks:
        page_num = chunk.get("page_num", 1)
        doc_name = chunk.get("doc_name", "Document")
        snippet = chunk.get("text", "")
        score = chunk.get("score", 0.85)

        formatted_context_parts.append(
            f"--- Source: {doc_name} | Page {page_num} ---\n{snippet}"
        )
        citations.append({
            "doc_name": doc_name,
            "page_num": page_num,
            "snippet": snippet[:220] + ("..." if len(snippet) > 220 else ""),
            "score": round(score, 2)
        })

    context_str = "\n\n".join(formatted_context_parts)

    prompt = f"""Analyze the provided document excerpts and provide an accurate, structured response.

Guidelines:
1. If this document is a resume or CV, structure your response clearly using the following sections:
   - Candidate Profile (Name, current title, and core background)
   - Professional Experience & Key Achievements
   - Technical & Domain Skills (Programming languages, frameworks, databases, cloud platforms)
   - Key Projects (Project title, technologies used, and outcomes)
   - Education & Certifications
2. If this is a general report or document, provide an executive summary followed by core findings and conclusions.
3. Reference page citations using [Page X] for every key fact.
4. Base your answer strictly on the provided text.

Document Excerpts:
{context_str}

User Question:
{question}"""

    try:
        answer_text = generate_with_fallback(
            api_key=api_key,
            prompt=prompt,
            preferred_model=model_name,
            system_instruction=SYSTEM_INSTRUCTION
        )

        return {
            "answer": answer_text,
            "citations": citations[:6],
            "retrieval_method": selected_chunks[0].get("retrieval_method", "unknown")
        }
    except Exception as e:
        return {
            "answer": f"API Error while generating answer: {str(e)}",
            "citations": citations[:6],
            "retrieval_method": selected_chunks[0].get("retrieval_method", "unknown")
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
    char_limit = 8000
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

    prompt = f"""Analyze the following document '{doc_name}':

{content_sample}

Task:
1. If this is a resume, provide a summary mentioning the candidate's name, specialization, experience, key projects, and education. If a general document, provide a comprehensive executive summary.
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
                "Who is this candidate and what is their background?",
                "What are the key technical skills and projects?",
                "Can you detail their work experience and education?"
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
