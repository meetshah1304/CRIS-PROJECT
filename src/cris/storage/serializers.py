from __future__ import annotations

from typing import Any

from src.cris.core.models import FIRStructuredRecord


def to_fir_document_row(record: FIRStructuredRecord) -> dict[str, Any]:
    row = {
        "doc_id": record.doc_id,
        "file_name": record.file_name,
        "source_path": record.source_path,
        "file_type": record.file_type,
        "file_hash": record.file_hash,
        "last_modified": record.last_modified,
        "processing_status": record.processing_status,
        "raw_text": record.raw_text,
        "ocr_confidence": record.ocr_confidence,
        "parser_confidence": record.parser_confidence,
        "page_count": record.page_count,
        "extraction_method": record.extraction_method,
        "extraction_notes": record.extraction_notes,
        "fir_number": record.fir_number,
        "police_station": record.police_station,
        "district": record.district,
        "state": record.state,
        "incident_date": record.incident_date,
        "report_date": record.report_date,
        "crime_type": record.crime_type,
        "ipc_sections": record.ipc_sections,
        "accused_names": record.accused_names,
        "victim_names": record.victim_names,
        "witness_names": record.witness_names,
        "locations": record.locations,
        "evidence_items": record.evidence_items,
        "narrative_summary": record.narrative_summary,
    }
    if record.embedding:
        row["embedding"] = _to_pgvector_literal(record.embedding)
    return row


def to_feature_row_db(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "doc_id": row.get("doc_id"),
        "crime_type": row.get("crime_type"),
        "police_station": row.get("police_station"),
        "district": row.get("district"),
        "incident_date": row.get("incident_date"),
        "entity_count": row.get("entity_count", 0),
        "location_count": row.get("location_count", 0),
        "section_count": row.get("section_count", 0),
        "narrative_length": row.get("narrative_length", 0),
        "link_signature": row.get("link_signature", ""),
    }


def to_relationship_edge_db(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "source_doc_id": row.get("source"),
        "target_doc_id": row.get("target"),
        "edge_weight": row.get("weight"),
        "reasons": row.get("reasons"),
    }


def _to_pgvector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{float(value):.8f}" for value in values) + "]"
