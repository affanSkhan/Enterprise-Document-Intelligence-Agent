# Enterprise Document Intelligence Agent

An agentic AI system for enterprise document intelligence. This MVP allows users to upload various documents (PDF, DOCX, PPTX, XLSX), search across them, chat with the content using Retrieval-Augmented Generation (RAG), and utilize specialized agents to generate reports, compare documents, extract BOMs, and draft presentations.

## Features
- **Document Ingestion:** Parses and chunks PDF, DOCX, PPTX, and XLSX files.
- **RAG Chat:** Conversational search with citations.
- **Specialized Agents:**
  - **Comparison Agent:** Compares two documents.
  - **Report Agent:** Drafts executive summaries.
  - **BOM Agent:** Extracts Bill of Materials as structured JSON.
  - **Presentation Agent:** Generates presentation deck outlines.
- **Modern UI:** Built with Next.js and Tailwind CSS featuring a glassmorphic dashboard.

## Architecture
- **Frontend:** Next.js (App Router), Tailwind CSS
- **Backend:** FastAPI (Python)
- **Vector Store:** ChromaDB
- **Database:** SQLite (Metadata)
- **AI Orchestration:** LangChain, Google Gemini API

## Setup Instructions

### 1. Prerequisites
- Python 3.10+
- Node.js 18+
- Docker & Docker Compose (optional)
- Gemini API Key

### 2. Backend Setup
```bash
cd backend
python -m venv venv
# Windows: .\venv\Scripts\activate | Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
```
Create a `.env` file in the `backend` directory:
```
GEMINI_API_KEY=your_gemini_api_key_here
```
Run the backend:
```bash
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

The app will be available at `http://localhost:3000`.

## Resume Bullet Points
- Architected and deployed an Enterprise Document Intelligence Agent utilizing LangChain and Google Gemini, enabling RAG-based semantic search and automated report generation across multi-modal enterprise documents (PDF, PPTX, XLSX, DOCX).
- Developed a highly modular multi-agent system (Comparison, BOM Extraction, Presentation drafting) that improved data retrieval times and standardized output formatting.
- Built a modern, responsive frontend dashboard using Next.js and Tailwind CSS to interact with a FastAPI-driven backend supported by ChromaDB vector storage.

## Future Improvements
- Implement authentication and Role-Based Access Control (RBAC).
- Replace SQLite with PostgreSQL for distributed production deployments.
- Integrate celery/Redis for truly asynchronous background document processing.
- Add real-time streaming for LLM responses in the frontend.
