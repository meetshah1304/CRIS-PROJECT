from __future__ import annotations

from src.cris.core.models import FIRStructuredRecord, FeatureRow


def build_feature_rows(records: list[FIRStructuredRecord]) -> list[dict]:
    rows: list[dict] = []
    for item in records:
        row = FeatureRow(
            doc_id=item.doc_id,
            crime_type=item.crime_type or "other",
            police_station=item.police_station,
            district=item.district,
            incident_date=item.incident_date,
            entity_count=len(item.accused_names) + len(item.victim_names) + len(item.witness_names),
            location_count=len(item.locations),
            section_count=len(item.ipc_sections),
            narrative_length=len(item.raw_text.split()),
            link_signature="|".join(
                sorted(
                    set(
                        [item.crime_type or "other"]
                        + item.locations[:2]
                        + item.accused_names[:2]
                        + item.ipc_sections[:3]
                    )
                )
            ),
        )
        rows.append(row.model_dump())
    return rows
