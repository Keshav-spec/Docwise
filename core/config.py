import os
from dotenv import load_dotenv

load_dotenv()

DEFAULT_GENERATION_MODEL = "gemini-1.5-flash"
DEFAULT_EMBEDDING_MODEL = "models/text-embedding-004"
DEFAULT_CHUNK_SIZE = 800
DEFAULT_CHUNK_OVERLAP = 150
DEFAULT_TOP_K = 4

def get_api_key(explicit_key: str = None) -> str:
    """Resolve Gemini API key from explicit parameter, environment variable, or return empty string."""
    if explicit_key and explicit_key.strip():
        return explicit_key.strip()
    return os.getenv("GEMINI_API_KEY", "").strip()
