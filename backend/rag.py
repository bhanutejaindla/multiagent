import os
from dotenv import load_dotenv
from langchain_postgres import PGVector
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

load_dotenv()

# Initialize Embeddings
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Database Connection
# Using the service name 'postgres' if running in docker, or localhost if running locally
# The docker-compose maps 5432:5432, so localhost works for local python
DB_CONNECTION = os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:postgrespassword@localhost:5432/multiagent_db")

# Initialize Vector Store
vector_store = PGVector(
    embeddings=embeddings,
    collection_name="research_docs",
    connection=DB_CONNECTION,
    use_jsonb=True,
)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
)

def add_document(text: str, source: str, job_id: str | None = None):
    """
    Splits text into chunks and adds to vector store with metadata.
    """
    print(f"[RAG] Adding document from {source} (Job ID: {job_id})...")
    
    metadata = {"source": source}
    if job_id:
        metadata["job_id"] = str(job_id)
        
    docs = [Document(page_content=text, metadata=metadata)]
    splits = text_splitter.split_documents(docs)
    
    if splits:
        vector_store.add_documents(splits)
        print(f"[RAG] Added {len(splits)} chunks.")
        return len(splits)
    return 0

def query_documents(query: str, n_results: int = 5, job_id: str | None = None):
    """
    Retrieves relevant context from vector store, optionally filtered by job_id.
    Falls back to searching all documents if job-specific search returns no results.
    """
    print(f"[RAG] Querying: {query} (Filter Job ID: {job_id})")
    
    results = []
    
    # First, try searching with job_id filter if provided
    if job_id:
        filter_dict = {"job_id": str(job_id)}
        try:
            results = vector_store.similarity_search(query, k=n_results, filter=filter_dict)
            print(f"[RAG] Found {len(results)} documents with job_id={job_id}")
        except Exception as e:
            print(f"[RAG] Error filtering by job_id: {e}")
            results = []
    
    # Fallback: If no results with job_id filter, search all documents
    if not results:
        print(f"[RAG] No documents found for job_id={job_id}, searching all documents...")
        try:
            results = vector_store.similarity_search(query, k=n_results)
            print(f"[RAG] Found {len(results)} documents from all sources")
        except Exception as e:
            print(f"[RAG] Error in similarity search: {e}")
            results = []
    
    if not results:
        print(f"[RAG] No documents found at all for query: {query}")
        return ""
    
    context = "\n\n".join([
        f"Source: {doc.metadata.get('source', 'Unknown')}\n"
        f"Job ID: {doc.metadata.get('job_id', 'N/A')}\n"
        f"Content: {doc.page_content}" 
        for doc in results
    ])
        
    return context
