# Docwise: Gemini-Powered PDF Q&A App

**Docwise** is an intelligent web app for asking questions about any PDF—powered by Google’s Gemini language model. Upload a PDF, ask questions, and get precise answers based on the document’s content.

<img width="1869" height="884" alt="Screenshot 2025-07-30 153630" src="https://github.com/user-attachments/assets/8a6820ed-1a37-49bd-b751-9bbfa4ce673d" />


---

## ✅ Current Features

### 🧠 Gemini-Powered AI PDF Q&A
- Ask questions about the contents of any PDF.
- Receives answers using Google’s Gemini language model, tailored to your query.

### 📄 PDF Text Extraction
- Supports real-time extraction of text from uploaded PDFs using PyMuPDF (`fitz`).

### 🧩 Smart Text Chunking
- Automatically splits long documents into manageable chunks (default size: **500 words**) to optimize AI understanding.

### 🔍 Intelligent Chunk Selection
- Uses **TF-IDF vectorization** and **cosine similarity** to find the most relevant chunks for a given question.

### 💬 Sidebar Chat History
- View all previous questions and answers.
- Click on a previous question to revisit its answer.

### 🧹 Clear Chat Button
- Instantly clear chat history and reset the app session.

---

## 🚧 Current Limitations

To stay transparent and attract collaborators, here are some current app limitations:

- ❌ **Single PDF Support:** Only one PDF can be queried at a time.
- ❌ **Session-Based Storage:** Uploaded PDFs are not stored persistently.
- ❌ **No PDF Visualizer:** No visual display of the original PDF in the app.
- ❌ **No Model Fine-Tuning:** Lacks indexing or fine-tuning for large corpora.
- ❌ **Placeholder Model Name:** Gemini model name is a placeholder (`ai_model_name_here`) — requires actual model configuration.

---

## 🌱 Planned Features / Future Work

Help us grow! Here are some next steps and suggested features:

### 📦 Multiple PDF Support
- Allow users to upload multiple PDFs and ask questions across all of them.
- (Requires associating chunks with file names and updating `find_relevant_chunks()` accordingly.)

### 🗂️ PDF Selection Dropdown
- Let users choose which PDF to query.

### 🖼️ PDF Viewer
- Embed PDF viewer in the app (e.g., using [pdfjs](https://mozilla.github.io/pdf.js/) or [streamlit-pdf-viewer](https://github.com/streamlit/streamlit-pdf-viewer)) for enhanced context.

### 📌 Persistent Chat History
- Store chat history in a local database (e.g., SQLite) or file (e.g., JSON) to persist between sessions.

### 📁 Save/Export Q&A
- Export Q&A as `.txt` or `.csv` for later reference.

### 📈 Semantic Search
- Use embedding-based retrieval (e.g., [sentence-transformers](https://www.sbert.net/) or Gemini embeddings) for smarter chunk matching.

### 🌐 Gemini Pro / Gemini 1.5 API Integration
- Upgrade to more powerful Gemini models for longer context windows.

---

## 🛠️ Tech Stack

| Technology                | Purpose                             |
|---------------------------|-------------------------------------|
| **Streamlit**             | Web app frontend                    |
| **PyMuPDF (fitz)**        | Extracting text from PDFs           |
| **scikit-learn**          | TF-IDF vectorizer & cosine similarity |
| **Google Generative AI**  | Answering user questions            |
| **Python**                | Backend logic & NLP processing      |

---

## 🚀 Getting Started

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Keshav-spec/Docwise.git
   cd Docwise
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Streamlit app:**
   ```bash
   streamlit run app.py
   ```

4. **Upload your PDF and start asking questions!**

---

## 🤝 Contributing

- Found a bug, want to suggest a feature, or interested in collaborating? Feel free to open an issue or submit a pull request!
- See the [Planned Features](#planned-features--future-work) section for ideas.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

**Docwise** — “Ask your PDFs anything, get smarter answers!”
