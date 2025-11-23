import os
from dotenv import load_dotenv

load_dotenv()

# Mock RAG for demo
def add_document(text: str, source: str):
    print(f"[Mock RAG] Adding document from {source}")
    return 1

def query_documents(query: str, n_results: int = 5):
    print(f"[Mock RAG] Querying: {query}")
    return "[Mock Context] Telangana is a state in India. The current CM is Revanth Reddy."

