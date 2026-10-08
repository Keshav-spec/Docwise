# Docwise: Intelligent Document Analysis & Retrieval System

Docwise is an advanced document question-answering and retrieval system powered by Google Gemini (`gemini-3-flash-preview`) and dense vector embeddings (`models/text-embedding-004`). Upload any PDF document to extract text, compute semantic embeddings, generate automated executive summaries, and ask questions with verified page citations.

Live Deployment: [https://docwise-web.onrender.com/](https://docwise-web.onrender.com/)

<img width="1514" height="849" alt="image" src="https://github.com/user-attachments/assets/bd678849-9d3b-4f02-8d50-2746b8942146" />

---

## Architectural Overview

Docwise utilizes a modern Retrieval-Augmented Generation (RAG) pipeline:

1. **Document Ingestion**: Extracts text page-by-page using PyMuPDF (`fitz`), preserving page structure and character offsets.
2. **Context-Aware Chunking**: Employs sentence-boundary and recursive window chunking with configurable overlap (default 800 characters, 150-character overlap) to prevent context loss across boundaries.
3. **Semantic Dense Embeddings**: Utilizes Google Gemini dense embedding model (`models/text-embedding-004`) to generate normalized vector representations. Features automatic fallback to TF-IDF cosine similarity when operating in offline mode.
4. **Source Attribution & Citations**: Answers are synthesized using Gemini (`gemini-3-flash-preview`) with system prompts that mandate explicit page citations (`[Page X]`) and relevant excerpt cards.
5. **Secure Server-Side Configuration**: The Google Gemini API key is managed exclusively on the server through environment variables (`GEMINI_API_KEY`), never exposing or requesting API keys from web users.
6. **Dual Interface**:
   - **FastAPI Web Application**: A dedicated, full-stack web dashboard built with HTML5, vanilla CSS, and JavaScript featuring drag-and-drop ingestion, document summaries, suggestion chips, and conversation export.
   - **Streamlit Application**: An interactive prototype interface for rapid testing and data exploration.

---

## Key Features

- **Built-in Server Credentials**: Web users do not need to enter API keys; the application securely utilizes the server environment configuration.
- **Dense Vector Search**: Semantic retrieval powered by Google Gemini embeddings captures contextual meaning beyond literal keyword matching.
- **Source Citation Tracking**: Every response references verified page numbers and text snippets from the original document.
- **Automated Document Intelligence**: Generates executive summaries and suggested starter questions upon document upload.
- **Export Capabilities**: Export entire question-and-answer transcripts directly to Markdown or JSON.
- **High-Performance Model**: Standardized on Google's `gemini-3-flash-preview` model for fast, accurate reasoning.
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
├── Dockerfile              # Container deployment file
├── Procfile                # Process file for cloud web services
├── render.yaml             # Render deployment configuration
├── .env.example            # Environment variables configuration template
└── README.md               # Project documentation
```

---

## Configuration & Environment Variables

Docwise reads configuration from environment variables or a `.env` file:

| Variable | Description | Default Value |
| :--- | :--- | :--- |
| `GEMINI_API_KEY` | Google Gemini API key (required on server) | None |
| `GEMINI_MODEL` | Google Gemini model name for generation | `gemini-3-flash-preview` |
| `PORT` | Web server listening port | `8000` |

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

```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
GEMINI_MODEL=gemini-3-flash-preview
```

---

## Running Locally

### Option A: Modern Web Dashboard (FastAPI)

Launch the FastAPI web server:

```bash
python server.py
```

Or using uvicorn:

```bash
uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

Open your browser and navigate to: `http://127.0.0.1:8000`

### Option B: Streamlit Interface

Run the Streamlit app:

```bash
streamlit run app.py
```

Open your browser and navigate to: `http://localhost:8501`

---

## Deployment on Render

1. In the [Render Dashboard](https://dashboard.render.com/), select your web service.
2. Under **Environment Variables**, ensure the following variables are defined:
   - `GEMINI_API_KEY`: Your Google Gemini API Key
   - `GEMINI_MODEL`: `gemini-3-flash-preview`
3. With continuous deployment enabled, pushing commits to the repository automatically triggers a build and redeployment.

---

## Technical Specifications

| Component | Specification |
| :--- | :--- |
| Generation Model | Google Gemini (`gemini-3-flash-preview`) |
| Embedding Model | Google Gemini Dense Embeddings (`models/text-embedding-004`) |
| Chunk Size | 800 characters (sentence boundary aligned) |
| Chunk Overlap | 150 characters |
| Retrieval Metric | Cosine similarity on normalized dense vectors |
| Supported File Types | PDF (`.pdf`) |

---

## License

Distributed under the MIT License. See `LICENSE` for more information.
