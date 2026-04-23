# CRIS Architecture Recommendation

## Core modules

- `app/`: Streamlit dashboard and workflow pages
- `src/cris/services/ingestion.py`: FIR upload and dataset discovery
- `src/cris/services/ocr.py`: OCR/text extraction adapter layer
- `src/cris/services/parser.py`: structured FIR parsing and confidence scoring
- `src/cris/services/feature_store.py`: normalized feature row generation
- `src/cris/services/similarity.py`: embeddings, ranking, and clustering adapters
- `src/cris/services/graph_engine.py`: inter-case graph linkage logic
- `src/cris/services/evaluation.py`: evaluation tracks and reporting hooks
- `src/cris/storage/supabase_client.py`: Supabase persistence
- `sql/supabase_schema.sql`: Postgres/pgvector schema

## OCR stack recommendation

- Primary digital PDF extractor: `PyMuPDF`
- PDF page rendering for OCR fallback: `pypdfium2`
- Baseline OCR fallback: `pytesseract`
- Production OCR/parsing target: `PaddleOCR` with `PP-Structure`

## Build order refinement

1. FIR-only upload flow
2. OCR and PDF text extraction hardening
3. Structured field parser
4. Gold-label design for evaluation
5. Feature extraction design review
6. Embedding generation
7. Cosine similarity search
8. Clustering and graph mapping
9. Training and evaluation

Adding gold labels slightly earlier makes precision and recall tuning much faster.
