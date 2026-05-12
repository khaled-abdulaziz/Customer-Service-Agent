# ==============================================================
# vector_store.py — Qdrant + LlamaIndex RAG
# ==============================================================

import os
from pathlib import Path

from dotenv import load_dotenv

# LlamaIndex core
from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    Settings,
    SimpleDirectoryReader,
)

from llama_index.core.node_parser import SentenceSplitter

# Embeddings + LLM
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI as LlamaOpenAI

# Qdrant
from llama_index.vector_stores.qdrant import QdrantVectorStore

from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
)

load_dotenv()

# ==============================================================
# Constants from .env
# ==============================================================

OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-4o"
)

EMBEDDING_MODEL = os.getenv(
    "OPENAI_EMBEDDING_MODEL",
    "text-embedding-3-small"
)

QDRANT_HOST = os.getenv(
    "QDRANT_HOST",
    "localhost"
)

QDRANT_PORT = int(
    os.getenv("QDRANT_PORT", 6333)
)

QDRANT_API_KEY = os.getenv(
    "QDRANT_API_KEY"
)

COLLECTION_NAME = os.getenv(
    "QDRANT_COLLECTION",
    "customer_service_docs"
)


EMBEDDING_DIMENSION = 1536

# ==============================================================
# Configure LlamaIndex models
# ==============================================================

def _configure_models():
    """
    Configure LlamaIndex global models.
    """

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise ValueError(
            "❌ OPENAI_API_KEY is missing."
        )

    Settings.llm = LlamaOpenAI(
        model=OPENAI_MODEL,
        api_key=api_key,
        temperature=0.1,
    )

    Settings.embed_model = OpenAIEmbedding(
        model=EMBEDDING_MODEL,
        api_key=api_key,
    )

# ==============================================================
# Qdrant Client Singleton
# ==============================================================

_qdrant_client = None

def get_qdrant_client() -> QdrantClient:
    """
    Returns singleton Qdrant client.
    """

    global _qdrant_client

    if _qdrant_client is None:

        if QDRANT_API_KEY:

            
            _qdrant_client = QdrantClient(
                url=f"https://{QDRANT_HOST}",
                api_key=QDRANT_API_KEY,
            )

            print(
                f"☁️ Qdrant Cloud → {QDRANT_HOST}"
            )

        else:

            
            _qdrant_client = QdrantClient(
                host=QDRANT_HOST,
                port=QDRANT_PORT,
            )

            print(
                f"🐳 Qdrant Local → "
                f"{QDRANT_HOST}:{QDRANT_PORT}"
            )

    return _qdrant_client

# ==============================================================
# Collection Manager
# ==============================================================

def _ensure_collection_exists(
    client: QdrantClient
):
    """
    Create collection if missing.
    """

    existing = [
        c.name
        for c in client.get_collections().collections
    ]

    if COLLECTION_NAME not in existing:

        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(
                size=EMBEDDING_DIMENSION,
                distance=Distance.COSINE,
            )
        )

        print(
            f"✅ Created collection: "
            f"{COLLECTION_NAME}"
        )

    else:

        print(
            f"📦 Collection exists: "
            f"{COLLECTION_NAME}"
        )

# ==============================================================
# Collection Has Documents
# ==============================================================

def collection_has_documents() -> bool:
    """
    Returns True if collection has vectors.
    """

    try:

        client = get_qdrant_client()

        info = client.get_collection(
            COLLECTION_NAME
        )

        count = info.points_count or 0

        print(
            f"📊 Qdrant points count: {count}"
        )

        return count > 0

    except Exception as e:

        print(
            f"❌ Failed checking collection: {e}"
        )

        return False

# ==============================================================
# Load Documents
# ==============================================================

def _load_documents(data_path: str):
    """
    Load FAQ documents.
    """

    path = Path(data_path)

    if not path.exists():

        raise FileNotFoundError(
            f"❌ Folder not found: {data_path}"
        )

    files = list(path.glob("*"))

    print(
        f"📂 Files detected in FAQ folder: "
        f"{len(files)}"
    )

    for file in files:
        print(f"   - {file.name}")

    loader = SimpleDirectoryReader(
        input_dir=str(path),
        recursive=True,
        required_exts=[
            ".pdf",
            ".txt",
            ".docx",
        ]
    )

    documents = loader.load_data()

    if not documents:

        raise ValueError(
            f"⚠️ No readable documents found "
            f"in: {data_path}"
        )

    print(
        f"📄 Loaded {len(documents)} documents."
    )

    return documents

# ==============================================================
# Upload Documents
# ==============================================================

def upload_documents(
    data_path: str = "data/faqs",
    force: bool = False,
):
    """
    Upload FAQ docs into Qdrant.
    """

    _configure_models()

    client = get_qdrant_client()

    _ensure_collection_exists(client)

    # Skip if already indexed
    if collection_has_documents() and not force:

        print(
            "✅ Documents already indexed."
        )

        return

    documents = _load_documents(data_path)

    splitter = SentenceSplitter(
        chunk_size=512,
        chunk_overlap=64,
    )

    vector_store = QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
    )

    storage_context = (
        StorageContext.from_defaults(
            vector_store=vector_store
        )
    )

    print("🚀 Uploading vectors to Qdrant...")

    VectorStoreIndex.from_documents(
        documents,
        transformations=[splitter],
        storage_context=storage_context,
        show_progress=True,
    )

    print(
        f"✅ Successfully indexed "
        f"{len(documents)} documents."
    )

# ==============================================================
# Query Engine
# ==============================================================

def get_query_engine(
    top_k: int = 4
):
    """
    Returns query engine.

    Automatically uploads documents
    if collection is empty.
    """

    _configure_models()

    client = get_qdrant_client()

    _ensure_collection_exists(client)

    # ----------------------------------------------------------
    # AUTO INDEX IF EMPTY
    # ----------------------------------------------------------

    if not collection_has_documents():

        print(
            "📥 Collection empty."
        )

        print(
            "🚀 Auto-uploading FAQ documents..."
        )

        upload_documents(
            data_path="data/faqs",
            force=True,
        )

        print(
            "✅ FAQ upload complete."
        )

    # ----------------------------------------------------------
    # LOAD VECTOR STORE
    # ----------------------------------------------------------

    vector_store = QdrantVectorStore(
        client=client,
        collection_name=COLLECTION_NAME,
    )

    storage_context = (
        StorageContext.from_defaults(
            vector_store=vector_store
        )
    )

    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        storage_context=storage_context,
    )

    print(
        f"🔎 Query engine ready "
        f"(top_k={top_k})"
    )

    return index.as_query_engine(
        similarity_top_k=top_k,
        response_mode="tree_summarize",
    )