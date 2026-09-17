# System Requirements - Adaptive IT Learning Path Guide

## 1. Functional Requirements (FR)

### 1.1 User Management
- **FR 1.1.1:** The system shall allow students to register and log in securely.
- **FR 1.1.2:** The system shall maintain user profiles, including progress across different IT tracks.

### 1.2 Track & Module Navigation
- **FR 1.2.1:** The system shall display a visual "track map" (Brilliant-style) for different IT domains (Programming, Cybersecurity, Data/ML).
- **FR 1.2.2:** Each track shall be broken down into sequential modules that students must complete to unlock the next.

### 1.3 AI Tutor Chat (RAG-Enabled)
- **FR 1.3.1:** The system shall provide a side-panel chat interface for real-time tutoring.
- **FR 1.3.2:** The AI tutor shall retrieve context from pre-indexed IT documents (RAG) to ground its responses.
- **FR 1.3.3:** The AI tutor shall cite its sources from the retrieved documents for every claim.
- **FR 1.3.4:** The AI tutor shall adhere to "Module Policies" (e.g., using the Socratic method instead of giving direct answers).

### 1.4 Progress Persistence
- **FR 1.4.1:** The system shall automatically save the user's progress within a module.
- **FR 1.4.2:** Users shall be able to resume their learning path from the last accessed module upon re-login.

## 2. Non-Functional Requirements (NFR)

### 2.1 Performance
- **NFR 2.1.1:** AI response time (including RAG retrieval) should not exceed 5 seconds on average.
- **NFR 2.1.2:** The system shall support concurrent users without significant performance degradation.

### 2.2 Security
- **NFR 2.2.1:** All user passwords shall be hashed (e.g., using bcrypt).
- **NFR 2.2.2:** API endpoints shall be protected by JWT (JSON Web Token) authentication.

### 2.3 Reliability & Accuracy
- **NFR 2.3.1:** The system must minimize hallucinations by strictly grounding AI responses in indexed documents.
- **NFR 2.3.2:** The vector store (ChromaDB) must be persisted reliably to prevent data loss.

### 2.4 Usability
- **NFR 2.4.1:** The UI must be responsive and follow modern design principles (Angular 21).
- **NFR 2.4.2:** The interface should clearly differentiate between lesson content and tutor chat.

### 2.5 Compliance
- **NFR 2.5.1:** All generated reports and documentation must adhere to IEEE/APA formatting standards as per Lusail University guidelines.
