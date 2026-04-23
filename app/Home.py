import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap: ensure the project root (parent of 'app/') is on sys.path so
# that 'from src.cris...' imports resolve correctly regardless of cwd.
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

from src.cris.core.models import FIRStructuredRecord
from src.cris.services.similarity import query_similar_cases_supabase, rank_similar_cases
from src.cris.ui.dashboard_data import load_dashboard_bundle
from src.cris.ui.styles import inject_global_styles


st.set_page_config(
    page_title="CRIS Dashboard",
    page_icon="CRIS",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_global_styles()

st.title("CRIS: Crime Report Intelligence System")
st.caption(
    "FIR parsing, structured intelligence extraction, similarity search, "
    "pattern mapping, and relationship analysis in one modular dashboard."
)

bundle = load_dashboard_bundle(limit=12)
dataset = bundle["dataset"]
parsed_docs = [FIRStructuredRecord(**doc) for doc in bundle["parsed_docs"]]
feature_df = pd.DataFrame(bundle["feature_rows"])
edge_df = pd.DataFrame(bundle["edge_rows"])
embedding_method = bundle["embedding_method"]
confidence_df = pd.DataFrame(bundle["confidence"])
hotspots = {key: pd.DataFrame(value) for key, value in bundle["hotspots"].items()}
graph_stats = bundle["graph_stats"]

top_cols = st.columns(4)
top_cols[0].metric("Dataset Files Scanned", len(dataset))
top_cols[1].metric("Parsed Preview Cases", len(parsed_docs))
top_cols[2].metric("Graph Links", len(edge_df))
top_cols[3].metric("Distinct Crime Labels", feature_df["crime_type"].nunique() if not feature_df.empty else 0)

left, right = st.columns([1.15, 0.85])

with left:
    st.markdown("### Intelligence Overview")
    if not feature_df.empty:
        crime_counts = (
            feature_df["crime_type"]
            .fillna("Unknown")
            .value_counts()
            .reset_index(name="count")
            .rename(columns={"index": "crime_type"})
        )
        fig = px.bar(
            crime_counts.head(10),
            x="crime_type",
            y="count",
            color="count",
            title="Crime Type Distribution",
            template="plotly_white",
        )
        st.plotly_chart(fig, width='stretch')
    else:
        st.info("No parsed features available yet.")

with right:
    st.markdown("### Pipeline Readiness")
    st.progress(0.78, text="Architecture scaffold readiness")
    st.write(
        {
            "OCR Layer": "Baseline ready, production engine recommended",
            "Structured Parser": "Field-level confidence and normalization enabled",
            "Feature Store": "Ready for Supabase persistence",
            "Similarity Engine": f"Embedding search active via {embedding_method}",
            "Graph Mapping": "Relationship graph and hotspot views active",
            "Evaluation Suite": "Scaffolded",
        }
    )
    st.markdown("### Graph Snapshot")
    st.write(graph_stats)

tab1, tab2, tab3, tab4 = st.tabs(
    ["FIR Parsing", "Similarity Search", "Relationship Mapping", "Recommended Stack"]
)

with tab1:
    st.subheader("Parsed FIR Preview")
    parsed_df = pd.DataFrame([doc.model_dump() for doc in parsed_docs])
    st.dataframe(parsed_df, width='stretch', height=320)
    confidence_preview = pd.DataFrame(
        [
            {
                "doc_id": doc.doc_id,
                "parser_confidence": doc.parser_confidence,
                **doc.field_confidence,
            }
            for doc in parsed_docs[:10]
        ]
    )
    st.markdown("#### Field-Level Confidence Preview")
    st.dataframe(confidence_preview, width='stretch', height=240)

with tab2:
    st.subheader("Similarity Search Demo")
    if parsed_docs:
        selected_id = st.selectbox(
            "Select FIR Case",
            options=[doc.doc_id for doc in parsed_docs],
            index=0,
        )
        selected_record = next(doc for doc in parsed_docs if doc.doc_id == selected_id)
        source_choice = st.radio("Search source", ["In-memory", "Supabase pgvector"], horizontal=True)
        if source_choice == "Supabase pgvector":
            ranked = query_similar_cases_supabase(selected_record, top_k=5, match_threshold=0.2)
        else:
            ranked = rank_similar_cases(selected_id, parsed_docs, top_k=5)
        st.dataframe(pd.DataFrame(ranked), width='stretch')
    else:
        st.warning("Add documents to see similarity ranking.")

with tab3:
    st.subheader("Relationship Links")
    st.dataframe(edge_df, width='stretch', height=320)
    st.caption(
        "Links are formed when FIRs share crime type, place overlap, accused/victim entities, or similar narrative features."
    )
    chart_left, chart_right = st.columns(2)
    with chart_left:
        if not hotspots["district"].empty:
            fig = px.bar(
                hotspots["district"].head(8),
                x="district",
                y="count",
                color="count",
                title="District Hotspots",
                template="plotly_white",
            )
            st.plotly_chart(fig, width='stretch')
    with chart_right:
        if not confidence_df.empty:
            fig = px.histogram(
                confidence_df,
                x="parser_confidence",
                nbins=12,
                title="Parser Confidence Distribution",
                template="plotly_white",
            )
            st.plotly_chart(fig, width='stretch')

with tab4:
    st.subheader("Best Practical Stack for CRIS")
    st.markdown(
        """
        - OCR: `PaddleOCR / PP-Structure` for production, `PyMuPDF + pypdfium2 + Tesseract` as the current fallback stack.
        - Field extraction: template-aware parser + NER + validation rules.
        - Embeddings: `multilingual-e5-large` for multilingual FIR semantic similarity.
        - Similarity retrieval: `Supabase pgvector` with cosine distance.
        - Clustering: `HDBSCAN` for incident groups and emerging hotspots.
        - Relationship engine: graph edges from shared entities, IPC sections, crime type, time, and geography.
        - Evaluation: OCR CER/WER, extraction precision/recall, NDCG/MRR for similarity, silhouette/coherence for clusters, and domain-reviewed graph validation.
        """
    )

with st.sidebar:
    st.markdown("## CRIS Workflow")
    st.write(
        [
            "1. Upload FIR PDFs/images",
            "2. OCR and layout extraction",
            "3. Structured field parsing",
            "4. Feature generation",
            "5. Similarity + clustering",
            "6. Relationship graph + hotspot review",
            "7. Evaluation and analyst feedback",
        ]
    )
    st.markdown("## Storage")
    st.code("Supabase + Postgres + pgvector", language="text")
