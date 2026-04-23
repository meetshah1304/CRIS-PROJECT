import sys
from pathlib import Path

# Bootstrap: ensure project root is on sys.path
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import pandas as pd
import plotly.express as px
import streamlit as st

from src.cris.core.models import FIRStructuredRecord
from src.cris.services.similarity import (
    query_similar_cases_supabase,
    rank_similar_cases,
)
from src.cris.ui.dashboard_data import load_dashboard_bundle
from src.cris.ui.styles import inject_global_styles


st.set_page_config(page_title="CRIS | Analytics", layout="wide")
inject_global_styles()

st.title("Analytics, Similarity, and Relationship Mapping")
bundle = load_dashboard_bundle(limit=20)
docs = [FIRStructuredRecord(**doc) for doc in bundle["parsed_docs"]]
feature_df = pd.DataFrame(bundle["feature_rows"])
edge_df = pd.DataFrame(bundle["edge_rows"])
cluster_df = pd.DataFrame(bundle["cluster"])
embedding_method = bundle["embedding_method"]
hotspots = {key: pd.DataFrame(value) for key, value in bundle["hotspots"].items()}
similarity_matrix = pd.DataFrame.from_dict(bundle["similarity_matrix"], orient="index")
matrix_method = bundle["matrix_method"]
score_df = pd.DataFrame(bundle["score_distribution"])
score_method = bundle["score_method"]
entity_df = pd.DataFrame(bundle["entity_frequency"])
ipc_df = pd.DataFrame(bundle["ipc_frequency"])
confidence_df = pd.DataFrame(bundle["confidence"])
graph_stats = bundle["graph_stats"]

top_left, top_right = st.columns(2)

with top_left:
    st.subheader("Feature Store Preview")
    st.dataframe(feature_df, width='stretch', height=300)

with top_right:
    st.subheader("Cluster Preview")
    st.dataframe(cluster_df, width='stretch', height=300)
    st.caption(f"Clustering and semantic similarity currently use `{embedding_method}`.")

st.markdown("### Relationship Graph Edges")
st.dataframe(edge_df, width='stretch', height=320)
metric_cols = st.columns(4)
metric_cols[0].metric("Graph Nodes", graph_stats["nodes"])
metric_cols[1].metric("Graph Edges", graph_stats["edges"])
metric_cols[2].metric("Graph Density", graph_stats["density"])
metric_cols[3].metric("Connected Components", graph_stats["components"])

tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["Semantic Search", "Hotspots", "Similarity Matrix", "Confidence Views", "Entity and IPC Views"]
)

with tab1:
    if docs:
        selected_id = st.selectbox("Select FIR for semantic search", [doc.doc_id for doc in docs], index=0)
        selected_record = next(doc for doc in docs if doc.doc_id == selected_id)
        search_source = st.radio("Semantic search source", ["In-memory", "Supabase pgvector"], horizontal=True)
        if search_source == "Supabase pgvector":
            similar_df = pd.DataFrame(query_similar_cases_supabase(selected_record, top_k=8, match_threshold=0.2))
        else:
            similar_df = pd.DataFrame(rank_similar_cases(selected_id, docs, top_k=8))
        st.dataframe(similar_df, width='stretch', height=280)
    else:
        st.info("No parsed documents available for semantic search.")

with tab2:
    hotspot_choice = st.selectbox("Hotspot view", ["district", "station", "crime_type"], index=0)
    hotspot_df = hotspots[hotspot_choice]
    if not hotspot_df.empty:
        x_column = hotspot_df.columns[0]
        fig = px.bar(hotspot_df.head(12), x=x_column, y="count", color="count", template="plotly_white")
        st.plotly_chart(fig, width='stretch')
        st.dataframe(hotspot_df, width='stretch', height=260)
    else:
        st.info("No hotspot summary available yet.")

with tab3:
    st.caption(f"Semantic similarity matrix generated via `{matrix_method}`.")
    st.dataframe(similarity_matrix.round(3), width='stretch', height=320)
    if not score_df.empty:
        fig = px.histogram(
            score_df,
            x="score",
            nbins=20,
            title=f"Similarity Score Distribution ({score_method})",
            template="plotly_white",
        )
        st.plotly_chart(fig, width='stretch')

with tab4:
    if not confidence_df.empty:
        left_chart, right_chart = st.columns(2)
        with left_chart:
            fig = px.histogram(
                confidence_df,
                x="parser_confidence",
                nbins=14,
                color="crime_type",
                title="Parser Confidence by Crime Type",
                template="plotly_white",
            )
            st.plotly_chart(fig, width='stretch')
        with right_chart:
            fig = px.histogram(
                confidence_df,
                x="ocr_confidence",
                nbins=14,
                color="district",
                title="OCR Confidence by District",
                template="plotly_white",
            )
            st.plotly_chart(fig, width='stretch')
        st.dataframe(confidence_df, width='stretch', height=260)
    else:
        st.info("No confidence data available yet.")

with tab5:
    left_chart, right_chart = st.columns(2)
    with left_chart:
        if not entity_df.empty:
            fig = px.bar(
                entity_df,
                x="entity",
                y="count",
                color="count",
                title="Most Frequent Entities",
                template="plotly_white",
            )
            st.plotly_chart(fig, width='stretch')
            st.dataframe(entity_df, width='stretch', height=240)
        else:
            st.info("No repeated entities detected yet.")
    with right_chart:
        if not ipc_df.empty:
            fig = px.bar(
                ipc_df,
                x="ipc_section",
                y="count",
                color="count",
                title="Most Frequent IPC Sections",
                template="plotly_white",
            )
            st.plotly_chart(fig, width='stretch')
            st.dataframe(ipc_df, width='stretch', height=240)
        else:
            st.info("No IPC section frequency data available yet.")

st.markdown("### Linkage Logic")
st.write(
    [
        "Crime-type overlap creates category links.",
        "Location token overlap creates geographic links.",
        "Person/entity overlap creates investigation links.",
        "Embedding-based similarity supports semantic case matching even when wording differs.",
        "District and station hotspot summaries provide early trend visibility.",
    ]
)
