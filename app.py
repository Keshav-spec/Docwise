<<<<<<< HEAD
import streamlit as st
import os
from dotenv import load_dotenv

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

load_dotenv()

# Streamlit Page Configuration
st.set_page_config(
    page_title="Docwise - Document Intelligence",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Professional styling without emojis
st.markdown("""
<style>
    .main-title {
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.2rem;
        color: #1e293b;
    }
    .sub-title {
        font-size: 0.95rem;
        color: #64748b;
        margin-bottom: 1.5rem;
    }
    .citation-box {
        background-color: #f8fafc;
        border-left: 3px solid #3b82f6;
        padding: 8px 12px;
        margin-top: 8px;
        margin-bottom: 8px;
        font-size: 0.85rem;
        border-radius: 0 4px 4px 0;
    }
    .citation-meta {
        font-weight: 600;
        color: #2563eb;
        margin-bottom: 2px;
    }
    .citation-snippet {
        color: #475569;
        font-style: italic;
    }
    .summary-box {
        background-color: #f1f5f9;
        border: 1px solid #cbd5e1;
        border-radius: 6px;
        padding: 12px;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Session State Initialization
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "vector_store" not in st.session_state:
    st.session_state.vector_store = VectorStore(embedding_model=DEFAULT_EMBEDDING_MODEL)

if "document_metadata" not in st.session_state:
    st.session_state.document_metadata = None

if "document_summary" not in st.session_state:
    st.session_state.document_summary = None

if "starter_questions" not in st.session_state:
    st.session_state.starter_questions = []

# Sidebar Controls
with st.sidebar:
    st.header("Configuration")
    
    env_key = get_api_key()
    api_key_input = st.text_input(
        "Google Gemini API Key",
        value=env_key,
        type="password",
        help="Enter your API key or configure GEMINI_API_KEY in your .env file."
    )
    api_key = api_key_input.strip() if api_key_input else env_key

    model_option = st.selectbox(
        "Generation Model",
        options=["gemini-1.5-flash", "gemini-1.5-pro"],
        index=0
    )

    top_k = st.slider("Top-K Retrieved Chunks", min_value=1, max_value=8, value=DEFAULT_TOP_K)

    st.markdown("---")
    st.header("Session Management")

    if st.button("Reset Session", use_container_width=True):
        st.session_state.chat_history = []
        st.session_state.vector_store.clear()
        st.session_state.document_metadata = None
        st.session_state.document_summary = None
        st.session_state.starter_questions = []
        st.rerun()

    if st.session_state.chat_history:
        st.markdown("---")
        st.subheader("Questions History")
        for idx, item in enumerate(st.session_state.chat_history):
            if st.button(f"Q: {item['question'][:30]}...", key=f"hist_{idx}"):
                st.session_state.active_review_idx = idx

# Main Content Interface
st.markdown('<div class="main-title">Docwise</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Dense vector retrieval and precision document analysis powered by Google Gemini.</div>', unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "Upload a PDF Document",
    type=["pdf"],
    key="pdf_uploader",
    help="Upload any PDF to extract text, compute embeddings, and query."
)

if uploaded_file is not None:
    # Process document if not already indexed
    current_doc = st.session_state.document_metadata
    if current_doc is None or current_doc.get("filename") != uploaded_file.name:
        with st.spinner("Processing document, extracting pages, and generating embeddings..."):
            file_bytes = uploaded_file.read()
            extraction_data = extract_text_from_pdf_stream(file_bytes, filename=uploaded_file.name)
            pages = extraction_data["pages"]

            if not pages or extraction_data["total_characters"] == 0:
                st.error("Could not extract readable text from the uploaded PDF. The file may be empty or image-only.")
            else:
                chunks = chunk_pages(
                    pages=pages,
                    doc_name=uploaded_file.name,
                    chunk_size=DEFAULT_CHUNK_SIZE,
                    chunk_overlap=DEFAULT_CHUNK_OVERLAP
                )

                st.session_state.vector_store.clear()
                st.session_state.vector_store.add_chunks(chunks, api_key=api_key)

                # Generate summary and starter questions
                summary_data = summarize_document(
                    pages=pages,
                    doc_name=uploaded_file.name,
                    api_key=api_key,
                    model_name=model_option
                )

                st.session_state.document_metadata = {
                    "filename": uploaded_file.name,
                    "total_pages": extraction_data["total_pages"],
                    "total_characters": extraction_data["total_characters"],
                    "chunk_count": len(chunks)
                }
                st.session_state.document_summary = summary_data["summary"]
                st.session_state.starter_questions = summary_data["starter_questions"]
                st.success(f"Indexed {len(chunks)} chunks across {extraction_data['total_pages']} pages successfully.")

    # Display Document Overview
    if st.session_state.document_metadata:
        meta = st.session_state.document_metadata
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("File", meta["filename"][:18] + ("..." if len(meta["filename"]) > 18 else ""))
        col2.metric("Total Pages", meta["total_pages"])
        col3.metric("Indexed Chunks", meta["chunk_count"])
        col4.metric("Mode", "Dense Vectors" if st.session_state.vector_store.use_dense else "Lexical Fallback")

        if st.session_state.document_summary:
            with st.expander("Document Executive Summary", expanded=False):
                st.write(st.session_state.document_summary)

        if st.session_state.starter_questions:
            st.markdown("**Suggested Questions:**")
            q_cols = st.columns(len(st.session_state.starter_questions))
            for i, q in enumerate(st.session_state.starter_questions):
                if q_cols[i].button(q, key=f"starter_{i}"):
                    st.session_state.prompt_input = q

    # Query Input
    preset_query = st.session_state.get("prompt_input", "")
    question = st.text_input(
        "Ask a question about your document:",
        value=preset_query,
        key="query_input_field"
    )

    if st.button("Submit Question", type="primary") and question:
        if not api_key:
            st.error("Please provide a Gemini API key in the sidebar configuration.")
        else:
            with st.spinner("Retrieving relevant passages and synthesizing answer..."):
                response_data = answer_question_with_citations(
                    vector_store=st.session_state.vector_store,
                    question=question,
                    api_key=api_key,
                    model_name=model_option,
                    top_k=top_k
                )

                st.session_state.chat_history.append({
                    "question": question,
                    "answer": response_data["answer"],
                    "citations": response_data["citations"],
                    "retrieval_method": response_data["retrieval_method"]
                })
                # Clear preset after use
                if "prompt_input" in st.session_state:
                    del st.session_state["prompt_input"]

# Display Conversation History
if st.session_state.chat_history:
    st.markdown("---")
    st.subheader("Conversation")

    for idx, item in enumerate(reversed(st.session_state.chat_history)):
        with st.container():
            st.markdown(f"**Question:** {item['question']}")
            st.markdown(f"**Answer:** {item['answer']}")

            if item.get("citations"):
                with st.expander(f"View Source Citations ({len(item['citations'])})"):
                    for c in item["citations"]:
                        st.markdown(f"""
                        <div class="citation-box">
                            <div class="citation-meta">Page {c['page_num']} | Document: {c['doc_name']} | Relevance: {c['score']}</div>
                            <div class="citation-snippet">"{c['snippet']}"</div>
                        </div>
                        """, unsafe_allow_html=True)
            st.markdown("---")

    # Export Chat Option
    export_content = ["# Docwise Conversation Export\n"]
    for i, itm in enumerate(st.session_state.chat_history, 1):
        export_content.append(f"### Q{i}: {itm['question']}\n\n**Answer:** {itm['answer']}\n")
    export_text = "\n".join(export_content)

    st.download_button(
        label="Download Conversation Log",
        data=export_text,
        file_name="docwise_conversation.md",
        mime="text/markdown"
    )
=======
import streamlit as st
import google.generativeai as genai
import fitz  
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# 🔑 Gemini API Key
genai.configure(api_key="Your_api_key_here")

# 📄 Extract text from uploaded PDF
def extract_text_from_pdf(pdf_file):
    doc = fitz.open(stream=pdf_file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

# 🧩 Break long text into chunks
def chunk_text(text, chunk_size=500):
    words = text.split()
    return [" ".join(words[i:i+chunk_size]) for i in range(0, len(words), chunk_size)]

# 🔍 Find most relevant chunks
def find_relevant_chunks(chunks, question, top_k=3):
    vectorizer = TfidfVectorizer().fit_transform(chunks + [question])
    vectors = vectorizer.toarray()
    similarity = cosine_similarity([vectors[-1]], vectors[:-1])
    top_indices = np.argsort(similarity[0])[::-1][:top_k]
    return [chunks[i] for i in top_indices]

# 🤖 Ask Gemini with context
def ask_gemini_about_pdf_chunks(chunks, question):
    model = genai.GenerativeModel('ai_model_name_here')  # Replace with your model name
    context = "\n\n".join(chunks)
    prompt = f"""You are given parts of a PDF. Based on this content, answer the user's question.

PDF Chunks:
{context}

Question:
{question}
"""
    response = model.generate_content(prompt)
    return response.text

if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []  # (question, answer)

if 'selected_question_index' not in st.session_state:
    st.session_state.selected_question_index = None

# -------- Sidebar Chat History --------
with st.sidebar:

    if st.button("🧹 Clear Chat"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.experimental_rerun()

    st.subheader("💬 Your Questions")
    for idx, (question, _) in enumerate(st.session_state.chat_history):
        if st.button(question, key=f"q_{idx}"):
            st.session_state.selected_question_index = idx

    if st.session_state.selected_question_index is not None:
        q, a = st.session_state.chat_history[st.session_state.selected_question_index]
        st.markdown("---")
        st.markdown(f"**👉 Selected Question:** `{q}``")
        st.markdown(f"**📄 Answer:** {a}")

# -------- Main Interface --------
st.title("📄 Docwise")

uploaded_file = st.file_uploader("Upload a PDF", type="pdf", key="pdf_uploader")

if uploaded_file is not None:
    pdf_text = extract_text_from_pdf(uploaded_file)
    chunks = chunk_text(pdf_text)

    question = st.text_input("Ask a question about your PDF:")
    if question:
        relevant_chunks = find_relevant_chunks(chunks, question)
        answer = ask_gemini_about_pdf_chunks(relevant_chunks, question)

        st.session_state.chat_history.append((question, answer))
        st.write("🧠 **Answer:**", answer)

>>>>>>> 592a5aad67f2d846ee19c58bf5eaaf4be95b53a6
