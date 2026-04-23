from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

from src.cris.config import get_settings
from src.cris.core.models import BatchProcessingResult, FIRStructuredRecord, PersistenceReport
from src.cris.services.feature_store import build_feature_rows
from src.cris.services.graph_engine import build_relationship_graph, graph_edges_frame
from src.cris.services.ingestion import scan_dataset
from src.cris.services.parser import parse_fir_document
from src.cris.services.similarity import attach_embeddings
from src.cris.storage.serializers import to_feature_row_db, to_fir_document_row, to_relationship_edge_db
from src.cris.storage.supabase_client import select_rows, upsert_rows


@dataclass
class BatchRunArtifacts:
    records: list[FIRStructuredRecord]
    results: list[BatchProcessingResult]
    feature_rows: list[dict]
    edge_rows: list[dict]
    summary: dict
    persistence: PersistenceReport


def process_dataset_batch(
    root: Path | None = None,
    limit: int | None = None,
    parser_confidence_threshold: float = 0.7,
    persist_to_supabase: bool = False,
    force_reprocess: bool = False,
) -> BatchRunArtifacts:
    settings = get_settings()
    docs = scan_dataset(root or Path(settings.data_dir), limit=limit)
    previous_index = load_processing_index()
    if persist_to_supabase:
        previous_index.update(load_supabase_processing_index())

    records: list[FIRStructuredRecord] = []
    results: list[BatchProcessingResult] = []

    for document in docs:
        previous = previous_index.get(document.doc_id)
        if not force_reprocess and _is_unchanged(document, previous):
            results.append(
                BatchProcessingResult(
                    doc_id=document.doc_id,
                    source_path=document.source_path,
                    file_hash=document.file_hash,
                    last_modified=document.last_modified,
                    processing_status="skipped",
                    parser_confidence=previous.get("parser_confidence") if previous else None,
                    ocr_confidence=previous.get("ocr_confidence") if previous else None,
                    extraction_method=previous.get("extraction_method") if previous else None,
                    reason="Skipped unchanged file based on hash and timestamp",
                )
            )
            continue

        try:
            record = parse_fir_document(document)
            status = "processed" if (record.parser_confidence or 0.0) >= parser_confidence_threshold else "low_confidence"
            record.processing_status = status
            records.append(record)
            results.append(
                BatchProcessingResult(
                    doc_id=record.doc_id,
                    source_path=record.source_path,
                    file_hash=record.file_hash,
                    last_modified=record.last_modified,
                    processing_status=status,
                    parser_confidence=record.parser_confidence,
                    ocr_confidence=record.ocr_confidence,
                    extraction_method=record.extraction_method,
                    reason=None if status == "processed" else "Parser confidence below threshold",
                )
            )
        except Exception as exc:
            results.append(
                BatchProcessingResult(
                    doc_id=document.doc_id,
                    source_path=document.source_path,
                    file_hash=document.file_hash,
                    last_modified=document.last_modified,
                    processing_status="failed",
                    parser_confidence=None,
                    ocr_confidence=document.ocr_confidence,
                    extraction_method=document.extraction_method,
                    reason=str(exc),
                )
            )

    update_processing_index(previous_index, results)
    records, _ = attach_embeddings(records)
    feature_rows = build_feature_rows(records)
    graph = build_relationship_graph(records)
    edge_rows = graph_edges_frame(graph).to_dict(orient="records")
    persistence = PersistenceReport(status="skipped", message="Persistence disabled for this batch run.")

    if persist_to_supabase and records:
        persistence = persist_batch_outputs(records, feature_rows, edge_rows)

    summary = summarize_batch_results(results)
    append_batch_history(
        {
            "run_at": datetime.now(timezone.utc).isoformat(),
            "persist_to_supabase": persist_to_supabase,
            "force_reprocess": force_reprocess,
            "limit": limit,
            "parser_confidence_threshold": parser_confidence_threshold,
            **summary,
            "persistence_status": persistence.status,
            "persistence_message": persistence.message,
        }
    )
    return BatchRunArtifacts(
        records=records,
        results=results,
        feature_rows=feature_rows,
        edge_rows=edge_rows,
        summary=summary,
        persistence=persistence,
    )


def summarize_batch_results(results: list[BatchProcessingResult]) -> dict:
    frame = pd.DataFrame([result.model_dump() for result in results])
    if frame.empty:
        return {"total": 0, "processed": 0, "low_confidence": 0, "failed": 0, "skipped": 0}

    counts = frame["processing_status"].value_counts().to_dict()
    return {
        "total": int(len(frame)),
        "processed": int(counts.get("processed", 0)),
        "low_confidence": int(counts.get("low_confidence", 0)),
        "failed": int(counts.get("failed", 0)),
        "skipped": int(counts.get("skipped", 0)),
    }


def load_processing_index() -> dict:
    settings = get_settings()
    state_path = Path(settings.processing_state_path)
    if not state_path.exists():
        return {}
    try:
        return json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def update_processing_index(previous_index: dict, results: list[BatchProcessingResult]) -> None:
    settings = get_settings()
    state_path = Path(settings.processing_state_path)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    for result in results:
        if result.processing_status == "skipped":
            continue
        previous_index[result.doc_id] = result.model_dump(mode="json")

    state_path.write_text(json.dumps(previous_index, indent=2), encoding="utf-8")


def load_batch_history(limit: int = 10) -> list[dict]:
    settings = get_settings()
    history_path = Path(settings.batch_history_path)
    if not history_path.exists():
        return []
    try:
        data = json.loads(history_path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return []
        return data[:limit]
    except (OSError, json.JSONDecodeError):
        return []


def append_batch_history(entry: dict) -> None:
    settings = get_settings()
    history_path = Path(settings.batch_history_path)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history = load_batch_history(limit=1000)
    history.insert(0, entry)
    history_path.write_text(json.dumps(history[:100], indent=2), encoding="utf-8")


def persist_batch_outputs(
    records: list[FIRStructuredRecord],
    feature_rows: list[dict],
    edge_rows: list[dict],
) -> PersistenceReport:
    document_response = upsert_rows("fir_documents", [to_fir_document_row(record) for record in records])
    feature_response = {"status": "skipped", "reason": "No feature rows to persist"}
    edge_response = {"status": "skipped", "reason": "No edge rows to persist"}

    if feature_rows:
        feature_response = upsert_rows("fir_feature_rows", [to_feature_row_db(row) for row in feature_rows])
    if edge_rows:
        edge_response = upsert_rows("fir_relationship_edges", [to_relationship_edge_db(row) for row in edge_rows])

    statuses = {document_response["status"], feature_response["status"], edge_response["status"]}
    if "error" in statuses:
        return PersistenceReport(
            status="error",
            message="One or more Supabase writes failed. Check the detailed response in the UI.",
            document_rows=len(records),
            feature_rows=len(feature_rows),
            edge_rows=len(edge_rows),
        )
    if statuses == {"ok"} or statuses == {"ok", "skipped"}:
        return PersistenceReport(
            status="ok",
            message="Batch outputs persisted successfully.",
            document_rows=len(records),
            feature_rows=len(feature_rows),
            edge_rows=len(edge_rows),
        )
    return PersistenceReport(
        status="partial",
        message="Persistence completed with mixed results.",
        document_rows=len(records),
        feature_rows=len(feature_rows),
        edge_rows=len(edge_rows),
    )


def load_supabase_processing_index() -> dict:
    response = select_rows(
        "fir_documents",
        columns="doc_id,file_hash,last_modified,processing_status,parser_confidence,ocr_confidence,extraction_method",
        limit=5000,
    )
    if response.get("status") != "ok":
        return {}
    return {row["doc_id"]: row for row in response.get("data", [])}


def _is_unchanged(document, previous: dict | None) -> bool:
    if not previous:
        return False
    if previous.get("processing_status") == "failed":
        return False
    return previous.get("file_hash") == document.file_hash and previous.get("last_modified") == document.last_modified
