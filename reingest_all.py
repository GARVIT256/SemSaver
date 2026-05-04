import os
import sys
import glob
import logging

# Add backend directory to path
backend_path = os.path.join(os.getcwd(), "backend")
sys.path.append(backend_path)

import ingestion
import vector_store
from config import settings

# Configure logging to see progress
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("reingest")

def reingest():
    # 1. Wipe FAISS
    logger.info("Wiping FAISS index...")
    vector_store.reset()

    # 2. Find PDF files
    pdf_files = glob.glob("Chapter9/*.pdf")
    if not pdf_files:
        logger.error("No PDF files found in Chapter9/ directory.")
        return

    logger.info(f"Found {len(pdf_files)} PDF files for ingestion.")

    total_chunks = 0
    total_chars = 0
    
    # We'll monkeypatch or wrap the chunking to track lengths
    # Or just inspect the chunks after each ingest_file call
    
    for pdf in pdf_files:
        try:
            # We need to get the chunks to calculate lengths
            # ingest_file doesn't return the chunks, just a summary.
            # I'll slightly modify ingest_file or just do the steps here.
            
            # Since I want to report character length, I'll do a manual loop
            # similar to ingest_file but with extra tracking.
            
            from extraction import extract, clean
            import chunking
            
            logger.info(f"Processing {pdf}...")
            raw_pages = extract(pdf)
            pages = [{"text": clean(p["text"]), "page_number": p["page_number"]} for p in raw_pages if clean(p["text"])]
            chunks = chunking.chunk_pages(pages, os.path.basename(pdf))
            
            if not chunks:
                logger.warning(f"No chunks for {pdf}")
                continue
                
            # Add to vector store and graph
            vector_store.add_chunks(chunks)
            import graph_store
            try:
                graph_store.build_graph_from_chunks(chunks)
            except Exception as ge:
                logger.warning(f"Graph build failed for {pdf}: {ge}")
                
            # Track stats
            file_chunks = len(chunks)
            file_chars = sum(len(c["text"]) for c in chunks)
            total_chunks += file_chunks
            total_chars += file_chars
            
            avg_len = file_chars / file_chunks if file_chunks > 0 else 0
            logger.info(f"Completed {pdf}: {file_chunks} chunks, avg {avg_len:.1f} chars/chunk")
            
        except Exception as e:
            logger.error(f"Failed to process {pdf}: {e}")

    if total_chunks > 0:
        # Final save to ensure everything is committed to disk
        vector_store.save()
        
        overall_avg = total_chars / total_chunks
        logger.info("="*40)
        logger.info(f"RE-INGESTION COMPLETE")
        logger.info(f"Total Chunks: {total_chunks}")
        logger.info(f"Average Chunk Length: {overall_avg:.1f} characters")
        logger.info("="*40)
    else:
        logger.error("No chunks were ingested.")

if __name__ == "__main__":
    reingest()
