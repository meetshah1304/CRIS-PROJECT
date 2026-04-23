# CRIS: Crime Report Intelligence System

CRIS is a modular Streamlit application for FIR ingestion, OCR extraction, structured field parsing, feature engineering, similarity search, clustering, and relationship mapping.

## What this scaffold includes

- FIR-only upload and batch ingestion shell
- OCR/text extraction abstraction for PDF/JPG/JPEG
- Structured FIR field extraction with confidence tracking
- Feature store records for similarity and pattern analysis
- Similarity search, clustering, and graph-based relationship mapping
- Supabase-ready schema and client wrapper
- Evaluation module for OCR, extraction, similarity, clustering, and linkage review
- Stylish Streamlit dashboard with workflow-oriented tabs

## Run locally

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
streamlit run app\Home.py
```
