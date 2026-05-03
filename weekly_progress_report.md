# SemSaver: Weekly Progress Report
## AI-Powered Syllabus Assistant
**Date:** May 1, 2026  
**Status:** In Progress (Retrieval Optimization Phase)  

---

### 1. Title
**SemSaver: Engineering a Hybrid RAG Architecture for Academic Knowledge Retrieval**

### 2. Objective of this Week
The primary objective of this week was to stabilize the hybrid retrieval pipeline and evaluate its effectiveness against baseline LLM performance. We focused on integrating Graph-based reasoning (Neo4j) with Vector-based semantic search (FAISS) to address "multi-hop" syllabus queries that general-purpose models often hallucinate or answer shallowly.

### 3. Work Completed
*   **Pipeline Integration:** Successfully connected the end-to-end pipeline:
    *   **Extraction:** PyMuPDF and `python-pptx` for robust text recovery from slide decks and PDFs.
    *   **Indexing:** Keyword extraction using KeyBERT (KeyphraseVectorizers) to populate Neo4j concept nodes.
    *   **Storage:** Multi-modal storage using FAISS for high-dimensional Jina embeddings and Neo4j for structural concept mapping.
*   **Retrieval Logic:** Implemented intent detection to trigger graph traversal when queries imply prerequisite relationships (e.g., "What should I know before...").

### 4. System Improvements
*   **Reduced LLM Dependency:** By improving the precision of retrieved context chunks, we reduced the need for the LLM to "reason from scratch," allowing it to function primarily as a synthesizer of grounded facts.
*   **Improved Retrieval Pipeline:** Switched to local Jina/SentenceTransformers for embeddings, providing better domain-specific alignment for technical academic content.
*   **Hybrid Graph + Vector Reasoning:** Introduced a dual-path retrieval strategy. Vector search handles "What is X?" while Graph traversal handles "How does X relate to Y?".
*   **Better Context Grounding:** Refined chunking strategies to preserve header context, ensuring that small text fragments retain their parent topic metadata during retrieval.

### 5. Evaluation Summary
We conducted a benchmarking exercise comparing SemSaver against a Baseline LLM (Groq/Gemini without RAG).

| Metric | Baseline LLM | SemSaver (Hybrid) |
| :--- | :--- | :--- |
| **Syllabus Alignment** | General knowledge; lacks specific curriculum context | High; strictly grounded in uploaded documents |
| **Grounded Answers** | Moderate; prone to "hallucinating" external facts | High; cites specific excerpts from the syllabus |
| **Multi-hop Reasoning** | Weak; often misses prerequisite links | Strong; traverses Neo4j paths for structural logic |

**Qualitative Observations:**
*   **Wins:** SemSaver significantly outperformed the baseline on "What to learn first" type queries by correctly identifying the structural hierarchy of the course.
*   **Ties:** On very broad definitions (e.g., "What is a variable?"), both systems performed similarly, though SemSaver was more concise.
*   **Losses:** Baseline occasionally provided more "tutorial-like" explanations for coding syntax which were absent in the specific syllabus chunks.

### 6. Sample System Logs
Below are representative logs illustrating the internal reasoning of the SemSaver pipeline:

```text
[2026-05-01 14:10:22] [INFO] Query received: "What is polymorphism?"
[2026-05-01 14:10:22] [INFO] Keywords extracted: ["polymorphism", "inheritance", "object-oriented"]
[2026-05-01 14:10:23] [INFO] FAISS: Retrieved top-5 chunks (avg similarity: 0.88)
[2026-05-01 14:10:23] [INFO] Neo4j: Prerequisite path found: [Classes] → [Inheritance] → [Polymorphism]
[2026-05-01 14:10:24] [INFO] Context constructed (tokens: 412). Injecting prerequisite chain.
[2026-05-01 14:10:26] [INFO] Gemini response generated.
[2026-05-01 14:10:26] [INFO] Confidence score: 0.85
```

```text
[2026-05-01 14:12:05] [INFO] Query received: "How to implement a List?"
[2026-05-01 14:12:05] [INFO] FAISS: Retrieved 3 chunks regarding 'ArrayList' and 'Collection Interface'
[2026-05-01 14:12:06] [INFO] Neo4j: No prerequisite intent detected. Skipping graph traversal.
[2026-05-01 14:12:08] [INFO] Gemini response generated.
[2026-05-01 14:12:08] [INFO] Confidence score: 0.79
```

### 7. Observations & Insights
*   **Structural Context:** Traditional RAG (Vector-only) often retrieves the "definition" of a topic but fails to explain its place in a learning journey. The addition of Neo4j allows SemSaver to act as a "tutor" that understands the curriculum roadmap.
*   **Extraction Noise:** We observed that PPTX files often contain sparse text; our keyword-heavy indexing strategy helps bridge the gap between "slide bullets" and "dense queries."

### 8. Fine-Tuning Exploration
This week, we explored the possibility of fine-tuning the embedding model using **Contrastive Learning with Hard Negatives**.

*   **The Concept:** The objective was to refine the embedding space by training on triples: `(Query + Correct Chunk + Hard Negative Chunk)`. A "Hard Negative" is a chunk that is semantically similar to the query but factually incorrect or irrelevant to the specific syllabus context.
*   **The Goal:** To "pull" the relevant academic content closer to the user's query in the vector space while "pushing" away distracting or generic information.

**Status Update:**
> [!IMPORTANT]
> **Fine-tuning was NOT implemented in the current production build.**  
> While the theoretical foundation is strong, we decided to defer implementation due to:
> 1. **Limited Dataset Size:** We currently lack the volume of high-quality query-answer pairs required to avoid overfitting.
> 2. **Compute Constraints:** The project priority shifted toward optimizing retrieval latency and graph-vector fusion.
> **Current Focus:** We are achieving significant performance gains through retrieval-side engineering (Hybrid Search) rather than model weights.

### 9. Limitations
*   **Cold Start:** Neo4j requires manual or semi-automated concept mapping for new subjects, which can be time-consuming.
*   **Dependency on Extraction:** If the PDF is poorly formatted (e.g., scanned images without OCR), retrieval quality drops significantly.

### 10. Next Steps
*   **Automated Graph Building:** Implement LLM-based relation extraction to automatically populate Neo4j from PDF text.
*   **Enhanced Scoring:** Refine the `semsaver_confidence` metric by factoring in both vector similarity and graph distance.
*   **UI/UX:** Integrate the prerequisite "roadmap" visualization into the frontend.

### 11. Conclusion
SemSaver has evolved from a standard RAG chatbot into a specialized academic tool. By prioritizing **structural grounding** over raw LLM power, we have created a system that doesn't just answer questions, but understands the *sequence* of learning. The results confirm that for educational use-cases, the relationship between concepts is as important as the concepts themselves.

---
*End of Report*
