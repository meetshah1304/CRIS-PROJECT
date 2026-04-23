from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from functools import lru_cache
from itertools import combinations
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN, KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from sklearn.metrics.pairwise import cosine_similarity

from src.cris.config import get_settings
from src.cris.core.models import FIRStructuredRecord
from src.cris.storage.supabase_client import rpc

# Suppress HuggingFace symlink warning on Windows (symlinks need Developer Mode)
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

try:
    from sentence_transformers import SentenceTransformer
except ImportError:  # pragma: no cover
    SentenceTransformer = None

# Matches multilingual-e5-small native dim (384). Resize only if using a different model.
TARGET_EMBEDDING_DIM = 384


# ---------------------------------------------------------------------------
# Embedding cache — persists to disk so re-runs skip model encoding entirely
# ---------------------------------------------------------------------------

def _embedding_cache_dir() -> Path:
    settings = get_settings()
    cache = Path(settings.huggingface_cache_dir).parent / "embed-cache"
    cache.mkdir(parents=True, exist_ok=True)
    return cache


def _cache_key(texts: list[str], model_name: str) -> str:
    payload = json.dumps({"model": model_name, "texts": texts}, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _load_cached_embeddings(texts: list[str], model_name: str) -> np.ndarray | None:
    key = _cache_key(texts, model_name)
    path = _embedding_cache_dir() / f"{key}.npy"
    if path.exists():
        try:
            return np.load(str(path))
        except Exception:
            path.unlink(missing_ok=True)
    return None


def _save_cached_embeddings(texts: list[str], model_name: str, embeddings: np.ndarray) -> None:
    key = _cache_key(texts, model_name)
    path = _embedding_cache_dir() / f"{key}.npy"
    try:
        np.save(str(path), embeddings)
    except Exception:
        pass


# ---------------------------------------------------------------------------
# Model loading — cached in process memory for the session lifetime
# ---------------------------------------------------------------------------

@lru_cache(maxsize=2)
def _load_embedding_model(model_name: str):
    if SentenceTransformer is None:
        return None
    settings = get_settings()
    cache_dir = Path(settings.huggingface_cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    os.environ["HF_HOME"] = str(cache_dir.resolve())
    os.environ["HUGGINGFACE_HUB_CACHE"] = str(cache_dir.resolve())
    return SentenceTransformer(model_name, cache_folder=str(cache_dir))


def _documents_to_text(records: list[FIRStructuredRecord]) -> list[str]:
    return [
        " ".join(
            [
                f"crime_type: {record.crime_type or ''}",
                f"police_station: {record.police_station or ''}",
                f"district: {record.district or ''}",
                f"state: {record.state or ''}",
                f"incident_date: {record.incident_date or ''}",
                f"ipc_sections: {' '.join(record.ipc_sections)}",
                f"locations: {' '.join(record.locations)}",
                f"accused: {' '.join(record.accused_names)}",
                f"victims: {' '.join(record.victim_names)}",
                f"evidence: {' '.join(record.evidence_items)}",
                record.raw_text,
            ]
        ).strip()
        for record in records
    ]


def generate_embeddings(records: list[FIRStructuredRecord]) -> tuple[np.ndarray, str]:
    """
    Generate embeddings for a list of records.

    Results are cached to disk keyed by model + text content so subsequent
    calls with the same documents (across Streamlit re-runs or restarts) are
    essentially free.
    """
    if not records:
        return np.empty((0, 0)), "none"

    texts = _documents_to_text(records)
    settings = get_settings()

    # --- Try sentence-transformer model (with disk cache) ---
    try:
        model = _load_embedding_model(settings.embedding_model)
        if model is not None:
            cached = _load_cached_embeddings(texts, settings.embedding_model)
            if cached is not None:
                return _resize_embeddings(cached), f"sentence-transformers:{settings.embedding_model} (cached)"

            embeddings = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True,
                                      show_progress_bar=False, batch_size=32)
            _save_cached_embeddings(texts, settings.embedding_model, embeddings)
            return _resize_embeddings(embeddings), f"sentence-transformers:{settings.embedding_model}"
    except Exception:
        pass

    # --- Fallback: try the fallback model ---
    try:
        fallback_model = _load_embedding_model(settings.fallback_embedding_model)
        if fallback_model is not None:
            cached = _load_cached_embeddings(texts, settings.fallback_embedding_model)
            if cached is not None:
                return _resize_embeddings(cached), f"sentence-transformers:{settings.fallback_embedding_model} (cached)"

            embeddings = fallback_model.encode(texts, normalize_embeddings=True, convert_to_numpy=True,
                                               show_progress_bar=False, batch_size=32)
            _save_cached_embeddings(texts, settings.fallback_embedding_model, embeddings)
            return _resize_embeddings(embeddings), f"sentence-transformers:{settings.fallback_embedding_model}"
    except Exception:
        pass

    # --- TF-IDF fallback (no model needed, always fast) ---
    tfidf = TfidfVectorizer(stop_words="english", max_features=2048)
    fallback = tfidf.fit_transform(texts).toarray()
    if fallback.size:
        fallback = normalize(fallback)
    return _resize_embeddings(fallback), "tfidf-fallback"


def rank_similar_cases(target_doc_id: str, records: list[FIRStructuredRecord], top_k: int = 5) -> list[dict]:
    if not records:
        return []

    embeddings, embedding_method = generate_embeddings(records)
    sims = cosine_similarity(embeddings, embeddings)
    index_map = {record.doc_id: idx for idx, record in enumerate(records)}
    target_idx = index_map[target_doc_id]

    ranked = []
    for idx, score in enumerate(sims[target_idx]):
        if idx == target_idx:
            continue
        explanation = _similarity_explanation(records[target_idx], records[idx])
        ranked.append(
            {
                "query_doc_id": target_doc_id,
                "candidate_doc_id": records[idx].doc_id,
                "crime_type": records[idx].crime_type,
                "score": round(float(score), 4),
                "embedding_method": embedding_method,
                "explanation": explanation,
            }
        )
    ranked.sort(key=lambda item: item["score"], reverse=True)
    return ranked[:top_k]


def cluster_documents(records: list[FIRStructuredRecord], n_clusters: int = 4) -> pd.DataFrame:
    if not records:
        return pd.DataFrame(columns=["doc_id", "cluster", "crime_type", "embedding_method"])
    if len(records) < n_clusters:
        n_clusters = max(1, len(records))

    embeddings, embedding_method = generate_embeddings(records)
    if len(records) == 1:
        labels = np.array([0])
    else:
        labels = _cluster_embeddings(embeddings, n_clusters=n_clusters)

    return pd.DataFrame(
        {
            "doc_id": [record.doc_id for record in records],
            "cluster": labels,
            "crime_type": [record.crime_type for record in records],
            "embedding_method": [embedding_method for _ in records],
        }
    )


def cluster_coherence(records: list[FIRStructuredRecord]) -> dict:
    cluster_df = cluster_documents(records)
    sizes = Counter(cluster_df["cluster"].tolist())
    return {"cluster_count": len(sizes), "cluster_sizes": dict(sizes)}


def hotspot_summary(records: list[FIRStructuredRecord]) -> dict[str, pd.DataFrame]:
    if not records:
        empty = pd.DataFrame()
        return {"district": empty, "station": empty, "crime_type": empty}

    frame = pd.DataFrame(
        [
            {
                "doc_id": record.doc_id,
                "district": record.district or "Unknown",
                "police_station": record.police_station or "Unknown",
                "crime_type": record.crime_type or "Unknown",
                "incident_date": record.incident_date,
            }
            for record in records
        ]
    )
    return {
        "district": frame.groupby("district", dropna=False).size().reset_index(name="count").sort_values("count", ascending=False),
        "station": frame.groupby("police_station", dropna=False).size().reset_index(name="count").sort_values("count", ascending=False),
        "crime_type": frame.groupby("crime_type", dropna=False).size().reset_index(name="count").sort_values("count", ascending=False),
    }


def semantic_similarity_matrix(records: list[FIRStructuredRecord]) -> tuple[pd.DataFrame, str]:
    if not records:
        return pd.DataFrame(), "none"
    embeddings, embedding_method = generate_embeddings(records)
    sims = cosine_similarity(embeddings, embeddings)
    frame = pd.DataFrame(sims, index=[r.doc_id for r in records], columns=[r.doc_id for r in records])
    return frame, embedding_method


def attach_embeddings(records: list[FIRStructuredRecord]) -> tuple[list[FIRStructuredRecord], str]:
    if not records:
        return records, "none"
    embeddings, embedding_method = generate_embeddings(records)
    for idx, record in enumerate(records):
        record.embedding = embeddings[idx].tolist()
        record.embedding_method = embedding_method
    return records, embedding_method


def query_similar_cases_supabase(record: FIRStructuredRecord, top_k: int = 10, match_threshold: float = 0.25) -> list[dict]:
    if not record.embedding:
        return []
    response = rpc(
        "match_fir_documents",
        {
            "query_embedding": _to_pgvector_literal(record.embedding),
            "match_threshold": match_threshold,
            "match_count": top_k,
        },
    )
    if response.get("status") != "ok":
        return []
    return response.get("data", [])


def similarity_score_distribution(records: list[FIRStructuredRecord]) -> tuple[pd.DataFrame, str]:
    if len(records) < 2:
        return pd.DataFrame(columns=["left_doc_id", "right_doc_id", "score"]), "none"
    embeddings, embedding_method = generate_embeddings(records)
    sims = cosine_similarity(embeddings, embeddings)
    rows = []
    for left_idx, right_idx in combinations(range(len(records)), 2):
        rows.append(
            {
                "left_doc_id": records[left_idx].doc_id,
                "right_doc_id": records[right_idx].doc_id,
                "score": round(float(sims[left_idx][right_idx]), 4),
            }
        )
    return pd.DataFrame(rows), embedding_method


def entity_frequency(records: list[FIRStructuredRecord], top_k: int = 15) -> pd.DataFrame:
    counter: Counter = Counter()
    for record in records:
        counter.update(record.accused_names)
        counter.update(record.victim_names)
    rows = [{"entity": name, "count": count} for name, count in counter.most_common(top_k)]
    return pd.DataFrame(rows)


def ipc_frequency(records: list[FIRStructuredRecord], top_k: int = 15) -> pd.DataFrame:
    counter: Counter = Counter()
    for record in records:
        counter.update(record.ipc_sections)
    rows = [{"ipc_section": name, "count": count} for name, count in counter.most_common(top_k)]
    return pd.DataFrame(rows)


def confidence_frame(records: list[FIRStructuredRecord]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "doc_id": record.doc_id,
                "ocr_confidence": record.ocr_confidence,
                "parser_confidence": record.parser_confidence,
                "crime_type": record.crime_type,
                "district": record.district,
            }
            for record in records
        ]
    )


def _cluster_embeddings(embeddings: np.ndarray, n_clusters: int) -> np.ndarray:
    if embeddings.size == 0:
        return np.array([])
    if len(embeddings) < 3:
        return KMeans(n_clusters=max(1, min(n_clusters, len(embeddings))), n_init=10, random_state=42).fit_predict(embeddings)

    labels = DBSCAN(eps=0.35, min_samples=2, metric="cosine").fit_predict(embeddings)
    unique_non_noise = {label for label in labels if label != -1}
    if unique_non_noise:
        return labels
    return KMeans(n_clusters=max(1, min(n_clusters, len(embeddings))), n_init=10, random_state=42).fit_predict(embeddings)


def _similarity_explanation(left: FIRStructuredRecord, right: FIRStructuredRecord) -> str:
    reasons: list[str] = []
    if left.crime_type and left.crime_type == right.crime_type:
        reasons.append("same crime type")
    if set(left.locations) & set(right.locations):
        reasons.append("shared location")
    if set(left.ipc_sections) & set(right.ipc_sections):
        reasons.append("shared IPC sections")
    if set(left.accused_names + left.victim_names) & set(right.accused_names + right.victim_names):
        reasons.append("shared entity")
    if not reasons:
        reasons.append("narrative embedding similarity")
    return ", ".join(reasons)


def _resize_embeddings(embeddings: np.ndarray) -> np.ndarray:
    if embeddings.size == 0:
        return embeddings
    current_dim = embeddings.shape[1]
    if current_dim == TARGET_EMBEDDING_DIM:
        return embeddings
    if current_dim > TARGET_EMBEDDING_DIM:
        return embeddings[:, :TARGET_EMBEDDING_DIM]

    padding = np.zeros((embeddings.shape[0], TARGET_EMBEDDING_DIM - current_dim), dtype=embeddings.dtype)
    return np.hstack([embeddings, padding])


def _to_pgvector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{float(value):.8f}" for value in values) + "]"
