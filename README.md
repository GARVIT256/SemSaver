# SemSaver
SemSaver is an AI-powered study assistant designed for B.Tech students to efficiently learn from their course materials.
The system ingests unstructured documents such as PDFs and PPTs, extracts key concepts using NLP techniques, and builds a dual-store knowledge system:
Vector Database (FAISS): Stores semantic embeddings for document retrieval
Graph Database (Neo4j): Stores relationships between concepts for reasoning
Using a hybrid retrieval mechanism, SemSaver enables:
Multi-hop reasoning (prerequisite chains)
Accurate, syllabus-aligned answers
Context-aware response generation
The final answers are generated using Gemini, ensuring responses remain grounded in the uploaded course content.