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

