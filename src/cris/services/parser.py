from __future__ import annotations

from datetime import datetime
import re

import json
import logging
from functools import lru_cache
from rapidfuzz import fuzz
from pathlib import Path

from src.cris.config import get_settings
from src.cris.core.models import FIRDocument, FIRStructuredRecord
from src.cris.services.ocr import extract_text


CRIME_KEYWORDS = {
    "fraud": ["420", "cheat", "fraud", "forgery"],
    "corruption": ["bribe", "corruption", "pc act"],
    "assault": ["assault", "hurt", "attack"],
    "theft": ["theft", "stolen", "robbery", "burglary"],
    "cybercrime": ["cyber", "otp", "phishing", "online transfer"],
}

def _parse_cache_dir() -> Path:
    settings = get_settings()
    cache = Path(settings.huggingface_cache_dir).parent / "parse-cache"
    cache.mkdir(parents=True, exist_ok=True)
    return cache

@lru_cache(maxsize=1)
def _get_ner_pipeline():
    try:
        from transformers import pipeline
        # Using a fast, highly accurate NER model
        return pipeline('ner', model='dslim/bert-base-NER', aggregation_strategy='simple')
    except Exception as e:
        logging.warning(f"Failed to load NER pipeline: {e}")
        return None

def _extract_entities_ner(text: str) -> dict:
    result = {"accused": set(), "victim": set(), "locations": set()}
    ner = _get_ner_pipeline()
    if not ner:
        return result
    try:
        entities = ner(text[:2000]) # Process up to 2000 chars to save time
        text_lower = text.lower()
        for ent in entities:
            word = ent["word"].strip()
            if len(word) < 3: continue
            
            if ent["entity_group"] == "LOC":
                result["locations"].add(word)
            elif ent["entity_group"] == "PER":
                # Check surrounding context to classify Accused vs Victim
                start = max(0, ent["start"] - 60)
                context = text_lower[start:ent["start"]]
                if "accused" in context or "suspect" in context or "arrest" in context:
                    result["accused"].add(word)
                else:
                    # Default to victim or witness if no accused keyword nearby
                    result["victim"].add(word)
    except Exception as e:
        logging.warning(f"NER extraction failed: {e}")
    
    return result

def parse_fir_document(document: FIRDocument) -> FIRStructuredRecord:
    cache_path = None
    if document.file_hash:
        cache_path = _parse_cache_dir() / f"{document.doc_id}_{document.file_hash[:16]}.json"
        if cache_path.exists():
            try:
                data = json.loads(cache_path.read_text(encoding="utf-8"))
                return FIRStructuredRecord(**data)
            except Exception:
                pass

    extraction = extract_text(document)
    raw_text = extraction.raw_text
    ocr_confidence = extraction.confidence or 0.0
    fir_number = _normalize_fir_number(
        _extract_first(r"\b(?:FIR|Case)\s*(?:No\.?|Number)?\s*[:\-]?\s*([A-Z0-9\/\-]+)", raw_text)
    )
    police_station = _normalize_title_case(
        _extract_first(
        r"(?:registered at|police station)\s+([A-Za-z ]+?)(?:\.|,|offence|incident)",
        raw_text,
        )
    )
    # Deep Learning NER Extraction
    ner_entities = _extract_entities_ner(raw_text)
    
    # Merge NER results with Legacy Regex results for maximum recall
    accused_names = _normalize_entity_list(_extract_entity_list(r"Accused\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", raw_text) + list(ner_entities["accused"]))
    victim_names = _normalize_entity_list(_extract_entity_list(r"Victim\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)", raw_text) + list(ner_entities["victim"]))
    locations = _normalize_location_candidates(_extract_location_candidates(raw_text) + list(ner_entities["locations"]))
    
    ipc_sections = _normalize_ipc_sections(re.findall(r"\b(?:IPC\s*)?(\d{3})\b", raw_text))
    crime_type = _infer_crime_type(raw_text, ipc_sections)
    district = _normalize_title_case(_extract_first(r"\b(Ahmedabad|Surat|Vadodara|Rajkot|Delhi|Mumbai|Pune)\b", raw_text))
    state = _normalize_title_case(_extract_first(r"\b(Gujarat|Maharashtra|Delhi)\b", raw_text))
    incident_date = _normalize_date(_extract_first(r"\b(\d{2}[\/\-]\d{2}[\/\-]\d{4})\b", raw_text))
    narrative_summary = _summarize_text(raw_text)
    evidence_items = _extract_evidence_items(raw_text)

    field_confidence = {
        "fir_number": _score_field(fir_number, base=0.93),
        "police_station": _score_field(police_station, base=0.82),
        "district": _score_field(district, base=0.86),
        "state": _score_field(state, base=0.88),
        "incident_date": _score_field(incident_date, base=0.9),
        "crime_type": _score_field(crime_type if crime_type != "other" else None, base=0.75),
        "ipc_sections": _score_collection(ipc_sections, base=0.88),
        "accused_names": _score_collection(accused_names, base=0.92 if ner_entities["accused"] else 0.76),
        "victim_names": _score_collection(victim_names, base=0.92 if ner_entities["victim"] else 0.76),
        "locations": _score_collection(locations, base=0.88 if ner_entities["locations"] else 0.72),
        "evidence_items": _score_collection(evidence_items, base=0.7),
    }

    parser_confidence = _compute_parser_confidence(field_confidence, ocr_confidence)

    payload = document.model_dump()
    payload.update(
        {
            "raw_text": raw_text,
            "ocr_confidence": extraction.confidence,
            "page_count": extraction.page_count,
            "extraction_method": extraction.extraction_method,
            "extraction_notes": extraction.extraction_notes,
            "fir_number": fir_number or document.doc_id,
            "police_station": police_station,
            "district": district,
            "state": state,
            "incident_date": incident_date,
            "report_date": None,
            "crime_type": crime_type,
            "ipc_sections": ipc_sections,
            "accused_names": accused_names,
            "victim_names": victim_names,
            "witness_names": [],
            "locations": locations,
            "evidence_items": evidence_items,
            "narrative_summary": narrative_summary,
            "field_confidence": field_confidence,
            "parser_confidence": parser_confidence,
        }
    )
    record = FIRStructuredRecord(**payload)
    if cache_path:
        try:
            cache_path.write_text(json.dumps(record.model_dump(mode="json")), encoding="utf-8")
        except Exception:
            pass
    return record


def _extract_first(pattern: str, text: str) -> str | None:
    match = re.search(pattern, text, flags=re.IGNORECASE)
    if not match:
        return None
    return match.group(1).strip()


def _extract_entity_list(pattern: str, text: str) -> list[str]:
    return sorted(set(re.findall(pattern, text)))


def _extract_location_candidates(text: str) -> list[str]:
    candidates = re.findall(r"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})\b", text)
    filtered = [value for value in candidates if fuzz.ratio(value.lower(), "sample police station") < 92]
    return filtered[:5]


def _extract_evidence_items(text: str) -> list[str]:
    known = []
    for token in ["mobile", "weapon", "cash", "documents", "vehicle", "bank statement", "device"]:
        if token in text.lower():
            known.append(token)
    return known


def _infer_crime_type(text: str, ipc_sections: list[str]) -> str:
    text_lower = text.lower()
    if "420" in ipc_sections or "406" in ipc_sections:
        return "fraud"
    for crime_type, keywords in CRIME_KEYWORDS.items():
        if any(keyword in text_lower for keyword in keywords):
            return crime_type
    return "other"


def _summarize_text(text: str) -> str:
    return text[:220] + ("..." if len(text) > 220 else "")


def _normalize_title_case(value: str | None) -> str | None:
    if not value:
        return None
    normalized = " ".join(value.split()).strip(" .,-")
    return normalized.title() if normalized else None


def _normalize_entity_list(values: list[str]) -> list[str]:
    normalized = [_normalize_title_case(value) for value in values]
    return sorted(set(value for value in normalized if value))


def _normalize_location_candidates(values: list[str]) -> list[str]:
    blacklist = {"Fir", "Case", "Victim", "Accused", "Incident", "Offence"}
    cleaned = []
    for value in values:
        normalized = _normalize_title_case(value)
        if not normalized or normalized in blacklist:
            continue
        cleaned.append(normalized)
    return sorted(set(cleaned))[:5]


def _normalize_ipc_sections(values: list[str]) -> list[str]:
    cleaned = sorted(set(value for value in values if len(value) == 3 and value.isdigit()))
    return cleaned


def _normalize_fir_number(value: str | None) -> str | None:
    if not value:
        return None
    normalized = re.sub(r"[^A-Za-z0-9/\-]", "", value).upper()
    return normalized or None


def _normalize_date(value: str | None) -> str | None:
    if not value:
        return None
    for pattern in ("%d/%m/%Y", "%d-%m-%Y"):
        try:
            parsed = datetime.strptime(value, pattern)
            return parsed.date().isoformat()
        except ValueError:
            continue
    return None


def _score_field(value: str | None, base: float) -> float:
    return round(base if value else 0.0, 3)


def _score_collection(values: list[str], base: float) -> float:
    if not values:
        return 0.0
    bonus = min(0.08, 0.02 * max(0, len(values) - 1))
    return round(min(base + bonus, 0.98), 3)


def _compute_parser_confidence(field_confidence: dict[str, float], ocr_confidence: float) -> float:
    populated_scores = [score for score in field_confidence.values() if score > 0]
    if not populated_scores:
        return round(min(0.2 + (ocr_confidence * 0.4), 0.98), 3)
    avg_score = sum(populated_scores) / len(populated_scores)
    return round(min((avg_score * 0.75) + (ocr_confidence * 0.25), 0.98), 3)
