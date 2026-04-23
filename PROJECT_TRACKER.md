# CRIS Project Tracker

## Project Goal

Build CRIS into a real-world FIR intelligence platform that can ingest the full FIR corpus, extract structured intelligence with confidence, perform semantic similarity and linkage analysis, generate hotspot and trend analytics, support analyst review, and produce results strong enough for research publication.

## Completed

- Streamlit dashboard foundation with dark UI
- FIR dataset scan and upload flow
- Batch processing over the FIR folder
- Incremental skip and force-reprocess workflow
- Supabase persistence baseline
- Supabase status visibility and batch history
- Digital PDF extraction with `PyMuPDF`
- OCR fallback path with `pypdfium2` and `pytesseract`
- Structured parser baseline with normalized fields
- Field-level confidence and document-level parser confidence
- Semantic similarity engine with embedding path and TF-IDF fallback
- Cluster preview, hotspot summaries, and relationship graph preview

## Current

- Real-world dataset processing from the FIR folder is active
- Parser is functional but still baseline for real FIR template diversity
- Semantic search is active, but may still use `tfidf-fallback` until the embedding environment is stabilized
- Dashboard is moving from preview-only analytics toward richer visual analysis

## Recommended Next Order

### 1. Embedding environment stabilization

Target:
- Make the app reliably use `sentence-transformers` instead of `tfidf-fallback`

Needed work:
- Use a stable Python version such as `3.11`
- Install `sentence-transformers`, `transformers`, and `torch` in the project environment
- Confirm the configured embedding model loads locally
- Re-run Streamlit from the same interpreter

Success condition:
- UI shows `sentence-transformers:<model-name>` instead of `tfidf-fallback`

### 2. Production OCR hardening

Target:
- Improve reliability on difficult scanned FIRs

Needed work:
- Add image preprocessing such as deskewing and denoising
- Integrate `PaddleOCR / PP-Structure`
- Persist page-level OCR metadata
- Route weak OCR pages into low-confidence review

Success condition:
- Better text recovery for noisy and scanned FIRs

### 3. FIR template-aware parser upgrade

Target:
- Improve precision and consistency for real FIR formats

Needed work:
- Expand template-aware field patterns
- Improve extraction for complainant, witness, occurrence place, report date, and evidence
- Add stronger location and police-station normalization
- Expand field-level validation and confidence logic

Success condition:
- Fewer malformed structured fields and fewer low-confidence records

### 4. True vector persistence in Supabase

Target:
- Move from in-memory semantic retrieval to full-corpus vector retrieval

Needed work:
- Persist embeddings into `pgvector`
- Add embedding version metadata
- Query similar FIRs from Supabase
- Support re-embedding when models change

Success condition:
- Similarity search works across the persisted FIR corpus

### 5. Advanced graph and hotspot intelligence

Target:
- Build stronger investigative linkage

Needed work:
- Expand entity-based graph logic
- Add signals for phone, device, account, address, vehicle, and time proximity
- Add graph confidence and better edge filtering
- Expand hotspot views by time and geography

Success condition:
- More useful inter-case linkage and more meaningful pattern detection

### 6. Analyst review workflow

Target:
- Create a human-in-the-loop correction loop

Needed work:
- Add review queue for low-confidence FIRs
- Add graph-link approval and rejection
- Allow manual correction of extracted fields
- Store corrections for future improvement

Success condition:
- Analysts can improve the system instead of only observing it

### 7. Evaluation and paper-preparation layer

Target:
- Make the system publication-ready

Needed work:
- OCR evaluation metrics
- field extraction metrics
- similarity ranking metrics
- clustering and graph validation metrics
- reproducible experiment tracking
- publication-quality figures and tables

Success condition:
- Results are defensible, reproducible, and paper-ready

## Deferred

- A manually validated benchmark subset is currently deferred by project choice
- The system should continue improving against the live FIR corpus first
- Formal benchmark creation can be added later for research validation and publication strength

## Immediate Implementation Priority

1. Stabilize the embedding environment
2. Persist embeddings into Supabase
3. Improve parser coverage for real FIR formats
4. Harden OCR with PaddleOCR
5. Add analyst review workflows

## Paper Milestones

- End-to-end OCR and parsing pipeline over the real FIR corpus
- Semantic retrieval over the persisted dataset
- Graph linkage and hotspot intelligence
- Evaluation tables and visualizations
- Error analysis and limitation section
- Reproducible environment and experiment descriptions
