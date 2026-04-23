from __future__ import annotations

from pathlib import Path

import streamlit as st

from src.cris.config import get_settings
from src.cris.services.feature_store import build_feature_rows
from src.cris.services.graph_engine import build_relationship_graph, graph_edges_frame, graph_metrics
from src.cris.services.ingestion import scan_dataset
from src.cris.services.parser import parse_fir_document
from src.cris.services.similarity import (
    attach_embeddings,
    cluster_documents,
    confidence_frame,
    entity_frequency,
    generate_embeddings,
    hotspot_summary,
    ipc_frequency,
    semantic_similarity_matrix,
    similarity_score_distribution,
)


@st.cache_data(show_spinner="Loading CRIS dashboard data…", ttl=3600)
def load_dashboard_bundle(limit: int) -> dict:
    """
    Load and compute the full dashboard bundle.

    Performance notes:
    - Embeddings are computed ONCE via generate_embeddings() and disk-cached.
      All downstream operations (cluster, matrix, score dist, attach) reuse
      the same cached result — no redundant model calls.
    - ttl=3600 (1 hour) so the heavy compute only runs once per session restart.
    - Embedding cache persists across restarts so subsequent cold-starts are
      near-instant even after a server restart.
    """
    settings = get_settings()
    dataset = scan_dataset(Path(settings.data_dir), limit=max(limit * 6, limit))
    parsed_docs = [parse_fir_document(doc) for doc in dataset[:limit]]

    # --- Single embedding compute — all downstream reuses disk cache ---
    parsed_docs, embedding_method = attach_embeddings(parsed_docs)

    # All of the following call generate_embeddings() internally, but the
    # disk-cache means the model is NOT invoked again (hash hit → load .npy).
    feature_rows = build_feature_rows(parsed_docs)
    graph = build_relationship_graph(parsed_docs)
    edge_df = graph_edges_frame(graph)
    graph_stats = graph_metrics(graph)
    hotspots = hotspot_summary(parsed_docs)
    confidence_df = confidence_frame(parsed_docs)
    cluster_df = cluster_documents(parsed_docs)
    similarity_matrix, matrix_method = semantic_similarity_matrix(parsed_docs)
    score_df, score_method = similarity_score_distribution(parsed_docs)
    entity_df = entity_frequency(parsed_docs)
    ipc_df = ipc_frequency(parsed_docs)

    return {
        "dataset": [doc.model_dump(mode="json") for doc in dataset],
        "parsed_docs": [doc.model_dump(mode="json") for doc in parsed_docs],
        "feature_rows": feature_rows,
        "edge_rows": edge_df.to_dict(orient="records"),
        "graph_stats": graph_stats,
        "hotspots": {key: value.to_dict(orient="records") for key, value in hotspots.items()},
        "confidence": confidence_df.to_dict(orient="records"),
        "cluster": cluster_df.to_dict(orient="records"),
        "similarity_matrix": similarity_matrix.to_dict(orient="index"),
        "matrix_method": matrix_method,
        "score_distribution": score_df.to_dict(orient="records"),
        "score_method": score_method,
        "entity_frequency": entity_df.to_dict(orient="records"),
        "ipc_frequency": ipc_df.to_dict(orient="records"),
        "embedding_method": embedding_method,
    }
