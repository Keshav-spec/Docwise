# Docwise: Intelligent Document Analysis & Retrieval System

Docwise is an advanced document question-answering and retrieval system powered by Google Gemini generative models and dense vector embeddings. Upload any PDF document to extract text, compute semantic embeddings, generate automated executive summaries, and ask questions with verified page citations.

---

## Architectural Overview

Docwise utilizes a modern Retrieval-Augmented Generation (RAG) pipeline:

1. **Document Ingestion**: Extracts text page-by-page using PyMuPDF (`fitz`), preserving page structure and character offsets.
2. **Context-Aware Chunking**: Employs sentence-boundary and recursive window chunking with configurable overlap (default 800 characters, 150-character overlap) to prevent context loss across boundaries.
3. **Semantic Dense Embeddings**: Utilizes Google Gemini dense embedding model (`models/text-embedding-004`) to generate normalized vector representations. Features automatic fallback to TF-IDF cosine similarity when operating in offline or test mode.
4. **Source Attribution & Citations**: Answers are synthesized using Gemini 1.5 with system prompts that mandate explicit page citations (`[Page X]`) and relevant excerpt cards.
5. **Dual Interface**:
   - **FastAPI Web Application**: A dedicated, full-stack web dashboard built with HTML5, vanilla CSS, and JavaScript featuring drag-and-drop ingestion, document summaries, suggestion chips, and conversation export.
   - **Streamlit Application**: An interactive prototype interface for rapid testing and data exploration.

---

## Key Features

- **Dense Vector Search**: Semantic retrieval powered by Google Gemini embeddings captures contextual meaning beyond literal keyword matching.
- **Source Citation Tracking**: Every response references verified page numbers and text snippets from the original document.
- **Automated Document Intelligence**: Generates executive summaries and suggested starter questions upon document upload.
- **Export Capabilities**: Export entire question-and-answer transcripts directly to Markdown or JSON.
- **Configurable Models**: Seamlessly switch between `gemini-1.5-flash` for high throughput and `gemini-1.5-pro` for complex analytical queries.
- **Clean Aesthetic**: Modern, professional interface designed without decorative emojis for an enterprise-grade experience.

---

## Project Structure

```text
Docwise-main/
├── core/
│   ├── __init__.py         # Core package initialization
│   ├── config.py           # Configuration defaults and environment loader
│   ├── extractor.py        # PyMuPDF page-aware text extraction
│   ├── chunker.py          # Sentence-aware chunker with sliding overlap
│   ├── embeddings.py       # Gemini dense vector store and similarity index
│   └── rag.py              # Retrieval synthesis and document summarization
├── web/
│   ├── index.html          # Web dashboard markup
│   ├── style.css           # Modern CSS with custom properties and glassmorphism
│   └── app.js              # Frontend controller and asynchronous API client
├── server.py               # FastAPI backend server
├── app.py                  # Streamlit application
├── requirements.txt        # Python dependency manifest
├── .env.example            # Environment variables configuration template
└── README.md               # Project documentation
```

---

## Installation & Setup

### Prerequisites

- Python 3.9 or higher
- A Google Gemini API key from [Google AI Studio](https://aistudio.google.com/)

### 1. Clone the Repository

```bash
git clone https://github.com/Keshav-spec/Docwise.git
cd Docwise
```

### 2. Set Up a Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Edit `.env` and add your Gemini API key:

```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

---

## Running the Application

### Option A: Modern Web Dashboard (FastAPI)

Launch the FastAPI web server:

```bash
python server.py
```

Or using uvicorn:

```bash
uvicorn server:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser and navigate to:
`http://127.0.0.1:8000`

### Option B: Streamlit Interface

Run the Streamlit app:

```bash
streamlit run app.py
```

Open your browser and navigate to the local Streamlit URL displayed in the terminal (typically `http://localhost:8501`).

---

## API Endpoints Reference

The FastAPI backend exposes the following REST endpoints:

- `GET /api/status`: Returns server health, key configuration status, and indexed chunk count.
- `POST /api/config`: Updates active API key or generation model settings.
- `POST /api/upload`: Uploads a PDF, extracts text, computes embeddings, and returns document summary and suggested questions.
- `POST /api/query`: Queries indexed documents using semantic similarity and returns the generated answer with page citations.
- `GET /api/history`: Returns the conversation history for the current session.
- `POST /api/clear`: Resets active document indices and chat history.
- `GET /api/export`: Exports conversation transcripts in Markdown or JSON format.

---

## Technical Specifications

| Component | Specification |
| :--- | :--- |
| Default Generation Model | Google Gemini 1.5 Flash (`gemini-1.5-flash`) |
| High-Precision Model | Google Gemini 1.5 Pro (`gemini-1.5-pro`) |
| Embedding Model | Google Gemini Dense Embeddings (`models/text-embedding-004`) |
| Chunk Size | 800 characters (sentence boundary aligned) |
| Chunk Overlap | 150 characters |
| Retrieval Metric | Cosine similarity on normalized dense vectors |
| Supported File Types | PDF (`.pdf`) |

---

## License

Distributed under the MIT License. See `LICENSE` for more information.
