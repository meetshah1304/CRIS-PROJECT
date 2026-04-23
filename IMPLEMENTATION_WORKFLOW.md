# CRIS Implementation Workflow Guide

## Project Goal

CRIS is an FIR intelligence platform for OCR, field extraction, semantic similarity retrieval, clustering, graph linkage, hotspot detection, and analyst review.

The success target is high precision, auditable confidence, and scalable full-dataset processing rather than claiming absolute 100% automation. The system should be trusted because every extraction, similarity match, and relationship link can be traced back to a source file, extraction method, confidence value, and review workflow.

## Current Project Status

The current repository already includes:

- A Streamlit UI shell with a dark dashboard theme
- Modular services for ingestion, OCR, parsing, features, similarity, graphing, evaluation, and Supabase access
- A Supabase schema scaffold with `pgvector` support
- Typed data models for `FIRDocument`, `FIRStructuredRecord`, and `FeatureRow`

The following areas are still baseline or placeholder and need to be completed for production use:

- OCR extraction still needs full production-grade hardening and page-level persistence
- Parser tuning against real FIR formats is still pending
- Embedding-based similarity search is not yet implemented
- Full-dataset batch processing and change tracking are not yet implemented
- Analyst review and correction workflows are not yet implemented

## Target Production Workflow

The intended CRIS pipeline should work as follows:

1. File upload or dataset scan discovers all FIR PDFs, JPGs, and JPEGs.
2. OCR and digital PDF text extraction recover raw document text.
3. Normalized raw text and extraction metadata are persisted.
4. Structured FIR parsing extracts deterministic and semantic fields.
5. Feature rows are generated for similarity, clustering, and graph linkage.
6. Embeddings are generated and stored for semantic retrieval.
7. Similarity retrieval returns related FIRs with scores and reasons.
8. Clustering and graph linkage identify related incidents, shared entities, and emerging patterns.
9. Hotspot and trend analytics aggregate results by station, district, time window, and crime type.
10. Analyst review and corrections improve low-confidence records and questionable links.
11. Evaluation runs measure OCR quality, parsing quality, ranking quality, clustering quality, and linkage quality.
12. Model and rule improvements are applied based on benchmark outcomes and analyst feedback.

## Phase-by-Phase Build Plan

### Phase 1: Environment and local run verification

Objective:
- Ensure the app, dependencies, configuration, and dataset paths are stable on the local machine.

Implementation tasks:
- Maintain a working `.env`
- Keep `streamlit run app\Home.py` working
- Confirm dataset scan succeeds on the FIR directory
- Confirm all pages load without runtime errors

Outputs and artifacts:
- Working local app startup
- Stable dependency set
- Verified dataset visibility

Completion criteria:
- The app starts successfully
- Dataset files are detected
- Dashboard pages render without import or parsing crashes

### Phase 2: Real OCR and full-dataset ingestion

Objective:
- Replace preview-only extraction with real text recovery and batch-ready file processing.

Implementation tasks:
- Use `PyMuPDF` as the primary digital PDF text extractor
- Use `pypdfium2` to render PDF pages when OCR fallback is required
- Use `pytesseract` initially for OCR fallback
- Add processing status tracking for all eligible files
- Prepare a batch processor that scans all FIR files instead of only preview subsets

Outputs and artifacts:
- Real extracted text
- OCR confidence values
- Extraction method tracking
- Batch ingestion status records

Completion criteria:
- Digital PDFs extract text directly when text is embedded
- Image files and scanned PDFs can be OCR processed
- Failed files are recorded without crashing the full batch

### Phase 3: Structured parser and normalization

Objective:
- Turn raw FIR text into reliable structured fields.

Implementation tasks:
- Separate deterministic fields from semantic fields
- Tune parser rules for FIR number, dates, station, district, state, and IPC sections
- Normalize dates, place names, and law section formatting
- Add field-level confidence scoring

Outputs and artifacts:
- Improved `FIRStructuredRecord`
- Normalized fields
- Field-level confidence values

Completion criteria:
- Required fields extract consistently on benchmark samples
- Invalid or malformed values are normalized or flagged
- Confidence scores are available per field or grouped field category

### Phase 4: Feature store and Supabase persistence

Objective:
- Persist all pipeline outputs in a form that supports analytics and reprocessing.

Implementation tasks:
- Persist document records, feature rows, and relationship edges to Supabase
- Extend storage for page-level OCR metadata and review workflows
- Track parser version, OCR version, and embedding version

Outputs and artifacts:
- Stored FIR document rows
- Stored feature rows
- Stored graph edge rows
- Reprocessing-safe metadata

Completion criteria:
- Supabase accepts parsed outputs
- Reprocessing unchanged files does not duplicate rows
- Storage supports future batch, review, and evaluation workflows

### Phase 5: Embeddings and semantic similarity

Objective:
- Replace baseline keyword similarity with semantic retrieval.

Implementation tasks:
- Generate embeddings using `intfloat/multilingual-e5-large`
- Store embeddings in `pgvector`
- Retrieve similar FIRs with cosine similarity
- Add result explanations using shared features when possible

Outputs and artifacts:
- Embedding vectors
- Semantic retrieval results
- Similarity result records with scores

Completion criteria:
- Embeddings are generated and stored
- Similar cases return with meaningful ranking
- Retrieval quality can be evaluated against labeled pairs

### Phase 6: Clustering, graph mapping, and hotspots

Objective:
- Build multi-case intelligence views from extracted records.

Implementation tasks:
- Use HDBSCAN on normalized embeddings for clustering
- Persist graph edges with reasons and confidence
- Add hotspot aggregation by district, station, and crime type
- Delay full geocoding until location normalization is stable

Outputs and artifacts:
- Cluster assignments
- Relationship graph edges
- Hotspot/trend views

Completion criteria:
- Clusters are explainable and inspectable
- Graph links capture shared entity, location, section, and crime-type signals
- Hotspot summaries are available for investigation review

### Phase 7: Evaluation suite and benchmark dataset

Objective:
- Measure whether the system is actually improving.

Implementation tasks:
- Create a gold-labeled FIR benchmark set before model tuning
- Compute OCR, extraction, retrieval, clustering, and graph metrics
- Add evaluation run history

Outputs and artifacts:
- Gold annotations
- Evaluation dashboards or reports
- Benchmark comparison outputs

Completion criteria:
- Metrics are reproducible
- Quality is visible per subsystem and per field
- Improvements can be compared across versions

### Phase 8: Analyst review and iterative improvement

Objective:
- Build feedback loops that improve real-world reliability.

Implementation tasks:
- Add review queues for low-confidence records
- Allow analysts to correct fields, approve or reject links, and validate similar cases
- Feed accepted corrections back into parser rules, confidence calibration, and training data

Outputs and artifacts:
- Review queue records
- Corrected structured outputs
- Feedback-driven improvement datasets

Completion criteria:
- Low-confidence outputs are reviewable
- Analyst decisions are persisted
- Feedback can be used for retraining and recalibration

## Recommended Models and Methods

### OCR

- Primary production choice: `PaddleOCR` with `PP-Structure`
- Primary digital PDF extraction inside the pipeline: `PyMuPDF`
- OCR rendering fallback for scanned PDFs: `pypdfium2`
- Baseline OCR fallback: `pytesseract`
- Optional research alternative: `docTR`

Recommended strategy:
- Use `PyMuPDF` first for digital PDFs
- If extracted text is empty or too weak, render pages and run OCR
- Use `pypdfium2` for rendering page images in fallback OCR paths
- Keep OCR metadata and extraction method for every document

### Field extraction

- V1: regex + layout-aware heuristics + validation rules
- V2: spaCy custom NER for accused, victim, witness, location, and evidence entities
- V3 if needed: LayoutLM / LayoutXLM-style token classification for heavily structured FIR layouts

### Embeddings

- Primary: `intfloat/multilingual-e5-large`
- Lower-cost fallback: `intfloat/multilingual-e5-base`

### Similarity search

- Supabase Postgres + `pgvector`
- Cosine similarity for retrieval

### Clustering

- Primary: HDBSCAN on normalized embeddings
- Baseline only: KMeans for early demos or debugging

### Graph mapping

- NetworkX in the service layer for graph construction
- Persist edges in Supabase for analytics and review

### Crime classification

- V1: rules from IPC sections and narrative keywords
- V2: fine-tuned transformer classifier after labeled data is available

### Confidence strategy

- Field-level confidence
- Document-level confidence
- Relationship-link confidence

### Geospatial and hotspot analysis

- Start with district and police-station aggregation
- Add geocoding only after location normalization is stable

## Data Architecture

### Core persisted entities

- `fir_documents`
- `fir_feature_rows`
- `fir_relationship_edges`

### Planned future tables

- `ocr_pages`
- `review_queue`
- `evaluation_runs`
- `gold_annotations`

### Per-FIR stored data requirements

Every FIR should preserve:

- source file metadata
- extracted text
- OCR confidence
- parser confidence
- normalized structured fields
- feature representation
- embedding version
- linkage reasons

## Public Interfaces and System Contracts

### `FIRDocument`

Purpose:
- Raw source metadata and extraction state

Minimum contract:
- document identifier
- source path
- file name
- file type
- raw text
- OCR confidence
- page count
- extraction method
- extraction notes

### `FIRStructuredRecord`

Purpose:
- Normalized parsed FIR fields plus confidence

Minimum contract:
- all `FIRDocument` fields
- FIR number
- station and geography fields
- dates
- crime type
- section lists
- entity lists
- evidence fields
- parser confidence

### `FeatureRow`

Purpose:
- Compact search, clustering, and linkage features

Minimum contract:
- document identifier
- crime type
- location and station signals
- date signal
- entity counts
- section counts
- narrative size
- compact linkage signature

### OCR output contract

- raw text
- per-document confidence
- optional per-page metadata

### Similarity output contract

- query document id
- candidate document id
- score
- explanation source where available

### Graph edge contract

- source
- target
- weight
- reasons
- confidence

## Full-Dataset Processing Plan

The application must move from preview-only limits to full-dataset batch processing for all eligible FIR files.

Recommended batch workflow:

1. Scan the dataset
2. Identify new or changed files
3. Skip already-processed unchanged files
4. Process new and changed files
5. Mark failed files without breaking the batch
6. Retry low-confidence files after parser or OCR improvements

Required file tracking fields:

- file path
- file hash
- last modified timestamp
- processing status
- parser version
- OCR version
- embedding version

Recommended processing statuses:

- `pending`
- `processed`
- `low_confidence`
- `failed`

## Quality and Evaluation Plan

Required metrics:

- OCR: CER, WER, page confidence distributions
- Field extraction: precision, recall, F1 per field
- Similarity retrieval: Recall@K, MRR, NDCG@K
- Clustering: silhouette, cluster purity, and domain review
- Graph linkage: analyst acceptance and rejection rate

The project must create a gold-labeled FIR benchmark dataset before serious model tuning begins. Benchmark-first evaluation is the default policy for CRIS because otherwise parser and retrieval improvements cannot be measured reliably.

## Analyst-in-the-loop Plan

Manual review workflows should support:

- correcting extracted fields
- approving or rejecting graph links
- marking related and unrelated FIR pairs
- reviewing low-confidence records

All analyst corrections should be stored and reused for:

- parser rule tuning
- confidence calibration
- future NER or classifier training
- similarity relevance tuning

Recommended review policy:

- high confidence: auto-accept
- medium confidence: queue for analyst review
- low confidence: retry or manual correction

## Immediate Action Checklist

1. Implement real OCR in `src/cris/services/ocr.py`
2. Add batch processing for all FIR files
3. Persist outputs to Supabase
4. Build gold annotations
5. Improve parser rules and confidence
6. Add embeddings and semantic similarity
7. Upgrade clustering and graph logic
8. Add evaluation dashboard
9. Add review queue and correction workflows

## Implementation Acceptance Checks

### Local startup

- app runs with `.env` configured
- dataset scan succeeds
- pages load without import or runtime errors

### OCR phase

- digital PDF extraction works on sample FIRs
- image OCR fallback works on sample JPG and JPEG inputs
- failed OCR files are logged without crashing the batch

### Parser phase

- required fields extract on benchmark FIRs
- field-level confidence is generated
- invalid dates and sections are rejected or normalized

### Storage phase

- Supabase tables accept parsed rows and relationship edges
- reprocessing does not duplicate unchanged files

### Similarity and analytics phase

- embeddings are generated and stored
- related cases return via cosine search
- clusters and graph edges produce explainable outputs

### Evaluation phase

- benchmark metrics can be computed end-to-end
- low-confidence and failed-case rates are visible

## Assumptions

- This file is the main execution reference for the project
- The intended audience is the primary builder first, while still being implementer-friendly for others
- The current scaffold remains the starting architecture unless a later phase intentionally replaces a subsystem
- The project optimizes for realistic, auditable law-enforcement workflow quality rather than demo-only automation
- `.gsd/ROADMAP.md` is not relied on because it is not present in the workspace state
