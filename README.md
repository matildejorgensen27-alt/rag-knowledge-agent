# RAG Knowledge Base Agent

An AI agent that answers questions by searching a vector database instead 
of relying on a hardcoded system prompt. No hallucination — Claude only 
answers from real document content.

## How It Works

1. Loads a document and splits it into overlapping chunks
2. Stores chunks in a ChromaDB vector database
3. When a question arrives, finds the most relevant chunks
4. Passes those chunks to Claude as context
5. Claude answers using only that specific information

## Architecture
Question → Embedding → Vector Search → Relevant Chunks → Claude → Answer

## Tech Stack
- Claude API (Anthropic)
- ChromaDB — local vector database
- Python
- python-dotenv

## Key Concepts Demonstrated
- Retrieval Augmented Generation (RAG)
- Text embeddings and vector search
- Document chunking with overlap
- Hallucination prevention
- Semantic similarity search

## How to Run
1. Clone the repository
2. Install: `pip install anthropic chromadb python-dotenv`
3. Create `.env` with `ANTHROPIC_API_KEY=your_key`
4. Add your document as `restaurant_knowledge.txt`
5. Run: `python rag_agent.py`

