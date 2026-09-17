import os
import shutil
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

TUTOR_PROMPT = PromptTemplate(
    template=(
        "You are a friendly, knowledgeable AI tutor helping a student with this course. "
        "Use the course material below as your primary source for explanations, terminology, "
        "and examples so you stay consistent with what the student has been taught.\n\n"
        "You are NOT limited to only repeating what's in the course material below. If the "
        "student asks for more practice, additional exercises, extra examples, or a harder "
        "version of a problem, create new ones yourself that fit the same topic and difficulty "
        "level, even if they are not explicitly listed in the material. Never refuse a request "
        "for more exercises just because the material only shows a couple of examples.\n\n"
        "Course material:\n{context}\n\n"
        "Student question: {question}\n"
        "Tutor answer:"
    ),
    input_variables=["context", "question"],
)

class RAGNotConfiguredError(RuntimeError):
    """Raised when the RAG service is used without a GOOGLE_API_KEY set."""


class RAGService:
    MODULE_SCOPE_RELEVANCE_THRESHOLD = 0.45

    def __init__(self, data_dir: str, persist_dir: str):
        self.data_dir = data_dir
        self.persist_dir = persist_dir
        self.has_api_key = bool(os.getenv("GOOGLE_API_KEY"))
        if not self.has_api_key:
            print("Warning: GOOGLE_API_KEY not found in environment variables. "
                  "RAG indexing and chat will be disabled until it is set.")

        # Lazily created so the app can start without a valid key. Google's
        # client constructors reach out for credentials immediately, which
        # crashes the whole process at import time if no key is present.
        self._embeddings = None
        self._llm = None
        self.vector_db = None

    @property
    def embeddings(self):
        if not self.has_api_key:
            raise RAGNotConfiguredError("GOOGLE_API_KEY is not set.")
        if self._embeddings is None:
            self._embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
        return self._embeddings

    @property
    def llm(self):
        if not self.has_api_key:
            raise RAGNotConfiguredError("GOOGLE_API_KEY is not set.")
        if self._llm is None:
            self._llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0.7)
        return self._llm

    def reset_vector_db(self):
        if os.path.isdir(self.persist_dir):
            shutil.rmtree(self.persist_dir, ignore_errors=True)
        self.vector_db = None

    def ingest_text(self, text_content: str, metadata: dict = None):
        """Ingest raw text content into the vector store."""
        doc = Document(page_content=text_content, metadata=metadata or {})
        
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100
        )
        chunks = text_splitter.split_documents([doc])

        if not self.vector_db:
            self.vector_db = Chroma(
                persist_directory=self.persist_dir,
                embedding_function=self.embeddings
            )
        self.vector_db.add_documents(chunks)
        return self.vector_db

    def get_retriever(self, module_id: int = None):
        """Return the retriever for the vector store, optionally scoped to a single module."""
        if not self.vector_db:
            self.vector_db = Chroma(
                persist_directory=self.persist_dir,
                embedding_function=self.embeddings
            )
        search_kwargs = {"k": 3}
        if module_id is not None:
            search_kwargs["filter"] = {"module_id": module_id}
        return self.vector_db.as_retriever(search_kwargs=search_kwargs)

    def query_rag(self, query: str, context: dict = None, module_id: int = None):
        """Query the RAG system and get an answer from the LLM.

        When module_id is given, retrieval is restricted to that module's content
        (FR-06 Module Scope Control). If nothing relevant is found in scope, the
        learner is guided back to the current topic instead of letting the LLM
        answer freely from outside the active module.
        """

        # If context is provided and query is vague, enhance the query
        enhanced_query = query
        if context:
            # Simple heuristic: if query is very short or generic like "explain more"
            if len(query.split()) < 5 or "explain" in query.lower() or "more" in query.lower():
                enhanced_query = f"Context: {context.type} '{context.title}'. User question: {query}"

        retriever = self.get_retriever(module_id)

        if module_id is not None:
            # Chroma's plain similarity search always returns its k nearest chunks
            # regardless of how irrelevant they are, so emptiness alone can't detect
            # an off-topic question. Score the best match instead and use a relevance
            # floor calibrated against real on-topic (~0.5-0.6) vs off-topic (~0.3-0.4)
            # queries against this project's content.
            scored_docs = self.vector_db.similarity_search_with_relevance_scores(
                enhanced_query, k=3, filter={"module_id": module_id}
            )
            best_score = max((score for _, score in scored_docs), default=0.0)
            if best_score < self.MODULE_SCOPE_RELEVANCE_THRESHOLD:
                topic = context.title if context else "this module"
                return {
                    "answer": (
                        f"That question looks like it's outside '{topic}'. Let's stay focused on "
                        "this module for now — ask me anything about what you're currently studying "
                        "and I'll be happy to help!"
                    ),
                    "source_documents": [],
                }

        qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True,
            chain_type_kwargs={"prompt": TUTOR_PROMPT},
        )

        result = qa_chain({"query": enhanced_query})
        return {
            "answer": result["result"],
            "source_documents": [doc.page_content for doc in result["source_documents"]]
        }
