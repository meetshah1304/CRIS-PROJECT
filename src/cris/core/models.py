from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class OCRExtractionResult(BaseModel):
    raw_text: str = ""
    confidence: float | None = None
    page_count: int | None = None
    extraction_method: str | None = None
    extraction_notes: list[str] = Field(default_factory=list)


class FIRDocument(BaseModel):
    doc_id: str
    source_path: str
    file_name: str
    file_type: Literal["pdf", "image", "unknown"] = "unknown"
    file_hash: str | None = None
    last_modified: str | None = None
    processing_status: Literal["pending", "processed", "low_confidence", "failed"] = "pending"
    raw_text: str = ""
    ocr_confidence: float | None = None
    page_count: int | None = None
    extraction_method: str | None = None
    extraction_notes: list[str] = Field(default_factory=list)
    extracted_at: datetime = Field(default_factory=datetime.utcnow)


class FIRStructuredRecord(FIRDocument):
    fir_number: str | None = None
    police_station: str | None = None
    district: str | None = None
    state: str | None = None
    incident_date: str | None = None
    report_date: str | None = None
    crime_type: str | None = None
    ipc_sections: list[str] = Field(default_factory=list)
    accused_names: list[str] = Field(default_factory=list)
    victim_names: list[str] = Field(default_factory=list)
    witness_names: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    evidence_items: list[str] = Field(default_factory=list)
    narrative_summary: str = ""
    field_confidence: dict[str, float] = Field(default_factory=dict)
    embedding: list[float] = Field(default_factory=list)
    embedding_method: str | None = None
    parser_confidence: float = 0.0


class FeatureRow(BaseModel):
    doc_id: str
    crime_type: str
    police_station: str | None = None
    district: str | None = None
    incident_date: str | None = None
    entity_count: int = 0
    location_count: int = 0
    section_count: int = 0
    narrative_length: int = 0
    link_signature: str = ""


class BatchProcessingResult(BaseModel):
    doc_id: str
    source_path: str
    file_hash: str | None = None
    last_modified: str | None = None
    processing_status: Literal["processed", "low_confidence", "failed", "skipped"] = "failed"
    parser_confidence: float | None = None
    ocr_confidence: float | None = None
    extraction_method: str | None = None
    reason: str | None = None


class PersistenceReport(BaseModel):
    status: Literal["ok", "skipped", "partial", "error"] = "skipped"
    message: str = ""
    document_rows: int = 0
    feature_rows: int = 0
    edge_rows: int = 0


def infer_file_type(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return "pdf"
    if suffix in {".jpg", ".jpeg", ".png"}:
        return "image"
    return "unknown"
