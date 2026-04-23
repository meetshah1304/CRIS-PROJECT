import sys
from pathlib import Path

# Bootstrap: ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd
import streamlit as st

from src.cris.config import get_settings
from src.cris.services.batch_processing import load_batch_history, process_dataset_batch
from src.cris.services.ingestion import describe_uploads, scan_dataset
from src.cris.storage.supabase_client import get_supabase_status
from src.cris.ui.styles import inject_global_styles


st.set_page_config(page_title="CRIS | Ingestion", layout="wide")
inject_global_styles()
settings = get_settings()

st.title("FIR Ingestion and OCR")
st.caption("Upload-first workflow with OCR readiness and file diagnostics.")

uploaded = st.file_uploader(
    "Upload FIR files",
    type=["pdf", "jpg", "jpeg", "png"],
    accept_multiple_files=True,
)

left, right = st.columns([1.2, 0.8])

with left:
    st.subheader("Upload Summary")
    if uploaded:
        upload_df = pd.DataFrame(describe_uploads(uploaded))
        st.dataframe(upload_df, width='stretch')
    else:
        st.info("Upload FIR PDFs or images to validate the ingestion flow.")

with right:
    st.subheader("Dataset Scan")
    docs = scan_dataset(Path(settings.data_dir), limit=50)
    st.metric("Existing FIR files", len(docs))
    preview = pd.DataFrame([doc.model_dump() for doc in docs[:10]])
    st.dataframe(preview, width='stretch')

st.markdown("### Operational Status")
status_left, status_right = st.columns([1.0, 1.0])
supabase_status = get_supabase_status()

with status_left:
    st.subheader("Supabase Status")
    if supabase_status["status"] == "connected":
        st.success(supabase_status["message"])
    elif supabase_status["status"] == "not_configured":
        st.warning(supabase_status["message"])
    else:
        st.error(supabase_status["message"])
    st.write(supabase_status["tables"])

with status_right:
    st.subheader("Recent Batch Runs")
    history = load_batch_history(limit=8)
    if history:
        st.dataframe(pd.DataFrame(history), width='stretch', height=220)
    else:
        st.info("No batch history recorded yet.")

st.markdown("### Batch Processing")
controls = st.columns([0.8, 0.9, 1.0, 1.0, 1.1])
batch_limit = controls[0].number_input("Batch limit", min_value=1, max_value=5000, value=100, step=25)
confidence_threshold = controls[1].slider("Parser confidence threshold", min_value=0.4, max_value=0.95, value=0.7, step=0.05)
process_all = controls[2].checkbox("Ignore limit and scan all files", value=False)
persist_to_supabase = controls[3].checkbox("Persist results to Supabase", value=False)
force_reprocess = controls[4].checkbox("Force reprocess", value=False)

if st.button("Run Batch Processing", width='stretch'):
    artifacts = process_dataset_batch(
        root=Path(settings.data_dir),
        limit=None if process_all else int(batch_limit),
        parser_confidence_threshold=float(confidence_threshold),
        persist_to_supabase=persist_to_supabase,
        force_reprocess=force_reprocess,
    )
    summary = artifacts.summary

    metric_cols = st.columns(5)
    metric_cols[0].metric("Total Files", summary["total"])
    metric_cols[1].metric("Processed", summary["processed"])
    metric_cols[2].metric("Low Confidence", summary["low_confidence"])
    metric_cols[3].metric("Failed", summary["failed"])
    metric_cols[4].metric("Skipped", summary["skipped"])

    if artifacts.persistence.status == "ok":
        st.success(artifacts.persistence.message)
    elif artifacts.persistence.status == "error":
        st.error(artifacts.persistence.message)
    elif artifacts.persistence.status == "partial":
        st.warning(artifacts.persistence.message)
    else:
        st.info(artifacts.persistence.message)

    st.markdown("#### Batch Status")
    results_df = pd.DataFrame([result.model_dump() for result in artifacts.results])
    st.dataframe(results_df, width='stretch', height=320)

    st.markdown("#### Parsed Feature Preview")
    st.dataframe(pd.DataFrame(artifacts.feature_rows), width='stretch', height=260)

    st.markdown("#### Relationship Edge Preview")
    st.dataframe(pd.DataFrame(artifacts.edge_rows), width='stretch', height=260)

st.markdown("### OCR Hardening Checklist")
st.write(
    [
        "Use PyMuPDF first for digital PDF text extraction.",
        "Render scanned PDFs with pypdfium2 before OCR fallback.",
        "Deskew and denoise scanned pages before OCR.",
        "Use language-aware OCR where FIRs contain mixed English and local language text.",
        "Store raw OCR text, page-level confidence, and extracted blocks for auditability.",
        "Flag low-confidence pages for analyst review.",
    ]
)
