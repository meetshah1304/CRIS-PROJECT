# Methodology: Crime Report Intelligence System (CRIS)

## 1. Brief Gist
The Crime Report Intelligence System (CRIS) is a modular, AI-driven intelligence platform designed to ingest, process, and analyze First Information Reports (FIRs). Its primary objective is to transform unstructured FIR documents (both digital PDFs and scanned images) into structured, actionable intelligence. By leveraging advanced NLP, Optical Character Recognition (OCR), semantic similarity, clustering, and relationship mapping, CRIS enables law enforcement analysts to discover hidden patterns, identify crime hotspots, and link related cases with high precision and auditable confidence.

## 2. Project Scale
- **Dataset Size:** The system is engineered to handle large-scale, real-world data ingestion. During development, it has scaled from processing smaller samples to integrating open-source dataset, and is architected to support bulk ingestion of CBI FIR Dataset collected from the official website crime intelligence datasets, scaling upwards of millions of historical records.
- **Processing Volume:** Features a robust full-dataset batch processing pipeline capable of asynchronously scanning vast FIR directories, parsing documents, generating vector embeddings, and persisting them without memory bottlenecks.
- **Database Scale:** Utilizes a highly scalable Supabase (PostgreSQL) backend, specifically optimized with `pgvector` to enable high-speed bulk ingestion and low-latency semantic vector retrieval across the entire multi-gigabyte FIR corpus.

## 3. Technology Stack
The platform is constructed on a modern, modular Python data science and web stack:

### Core Frameworks & Application Layer
- **Python (3.11+):** The core programming language chosen for stability in AI workflows.
- **Streamlit (>=1.44):** Serves as the interactive dashboard and workflow UI, implementing a dark-themed, professional aesthetic for operational analysts.
- **Pandas (>=2.2) & NumPy (>=1.26):** For data manipulation, feature structuring, and numerical operations.
- **Pydantic (>=2.9):** Ensures rigorous data validation and strongly typed data models (e.g., `FIRDocument`, `FIRStructuredRecord`, `FeatureRow`).

### Database & Storage
- **Supabase (>=2.7):** The primary persistence layer.
- **PostgreSQL & pgvector:** Used to store structured features, metadata, relationship edges, and high-dimensional vector embeddings, making semantic search highly scalable.

### Graph & Visual Analytics
- **NetworkX (>=3.3):** Applied in the service layer to construct inter-case relationship graphs based on shared entities, locations, and crime signatures.
- **Plotly (>=5.24):** Generates interactive visual analytics, hotspot maps, statistical breakdowns, and distribution trends directly within the predictive dashboard.

## 4. Models Used and Their Purpose

### OCR & Text Extraction Pipeline
To recover raw text from diverse, often noisy and misaligned scanned FIRs, CRIS employs a tiered extraction strategy:
- **PyMuPDF (>=1.24):** 
  - **Purpose:** Acts as the primary, high-speed extractor for natively digital PDFs.
- **pypdfium2 (>=4.30):** 
  - **Purpose:** Used as a fallback rendering engine to convert scanned PDF pages into images when embedded text extraction yields nothing.
- **pytesseract (>=0.3.13):** 
  - **Purpose:** The baseline OCR engine used for rapid text recovery from images and rendered PDFs.
- **PaddleOCR (with PP-Structure):** 
  - **Purpose:** The target production-grade OCR engine. It is specifically integrated to handle difficult, heavily structured, table-heavy, and noisy real-world scanned FIR layouts.

### Natural Language Processing (NLP) & Feature Extraction
- **Regex & Layout-Aware Heuristics:** 
  - **Purpose:** The initial V1 parser designed to deterministically extract highly structured fields like FIR numbers, dates, police stations, districts, and IPC sections.
- **spaCy (Custom NER):** 
  - **Purpose:** Deployed to extract critical semantic entities such as accused individuals, victims, witnesses, specific occurrence locations, and evidence, normalizing them to improve downstream linkage.

### Embeddings & Semantic Similarity
- **`intfloat/multilingual-e5-large` (via `sentence-transformers`):** 
  - **Purpose:** The primary transformer model used to generate dense vector embeddings from the parsed FIR narrative. It was selected for its robust multilingual performance and high precision, allowing the system to grasp the deep semantic context of crime reports beyond simple keyword matching.
- **Cosine Similarity:** 
  - **Purpose:** Applied directly within the Supabase `pgvector` database to retrieve and rank similar historical FIRs accurately.

### Clustering & Pattern Detection
- **HDBSCAN:** 
  - **Purpose:** Applied on the normalized embeddings to organically group related incidents. Unlike KMeans, HDBSCAN does not require a pre-defined number of clusters and gracefully handles outliers/noise, making it exceptional for discovering emerging, unexpected crime syndicates and patterns.

## 5. Detailed Implementation Workflow
1. **Ingestion & OCR:** FIRs are ingested in batch mode. PyMuPDF attempts immediate digital extraction. If unsuccessful, the system falls back to pypdfium2 rendering and PaddleOCR/Tesseract. Page-level metadata, extraction methods, and confidence scores are meticulously logged.
2. **Parsing & Normalization:** The raw extracted text passes through the structured parser. Entities (dates, geographical places, IPC sections) are extracted using regex and spaCy NER. Crucially, confidence scores are assigned per field and per document to ensure auditable data quality.
3. **Feature Generation & Embedding:** Extracted attributes are compiled into a compact `FeatureRow`. The core narrative and entity lists are embedded using `multilingual-e5-large` and persisted safely to Supabase.
4. **Retrieval & Graph Mapping:** When analyzing an FIR, the system performs a cosine similarity search against the corpus. NetworkX builds an intelligence graph, drawing relationship edges between cases sharing accused entities, geographic hotspots, or distinct operational signatures.
5. **Human-in-the-Loop (Analyst Review):** A queue routes low-confidence extractions or uncertain cluster assignments to analysts. Analysts can correct fields, approve or reject graph links, and feed these corrections back to recalibrate parser rules and confidence thresholds.
6. **Evaluation & Validation:** Continuous measurement of OCR error rates (CER, WER), field extraction precision, and retrieval ranking metrics (Recall@K, MRR). This ensures the platform maintains the high-precision validation standards required for real-world deployment and academic publication.
