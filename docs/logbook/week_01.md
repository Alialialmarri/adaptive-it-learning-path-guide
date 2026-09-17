# Weekly Logbook - Week 1 (Project Initialization)

## Tasks Completed

### 1. Project Infrastructure Setup
- Defined and created the full-stack folder structure (Backend: FastAPI, Frontend: Angular 21, Docs: Academic Reports).
- Initialized the `README.md` with project setup instructions.

### 2. Database Design & Modeling
- Designed the relational database schema using SQLAlchemy.
- Implemented models for `User`, `Track`, `Module`, `UserProgress`, and `ChatMessage`.
- Established relationships for progress persistence and chat history.

### 3. RAG Pipeline Initialization
- Created a skeleton for the RAG ingestion pipeline using LangChain.
- Configured document loading for PDF and TXT formats.
- Set up chunking and vector store (ChromaDB) persistence logic.

### 4. Requirements Specification
- Identified and documented functional requirements for user management, track navigation, and AI-tutor chat.
- Outlined non-functional requirements covering performance, security, and academic compliance.

## Next Steps
- Implement basic user authentication (Signup/Login) in FastAPI.
- Set up the Angular 21 project skeleton.
- Start ingesting initial IT corpora into the vector store.
