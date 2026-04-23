from __future__ import annotations

from itertools import combinations

import networkx as nx
import pandas as pd

from src.cris.core.models import FIRStructuredRecord


def build_relationship_graph(records: list[FIRStructuredRecord]) -> nx.Graph:
    graph = nx.Graph()
    for record in records:
        graph.add_node(
            record.doc_id,
            crime_type=record.crime_type,
            police_station=record.police_station,
            parser_confidence=record.parser_confidence,
        )

    for left, right in combinations(records, 2):
        score, reasons = relationship_score(left, right)
        if score <= 0:
            continue
        graph.add_edge(left.doc_id, right.doc_id, weight=score, reasons=", ".join(reasons))
    return graph


def relationship_score(left: FIRStructuredRecord, right: FIRStructuredRecord) -> tuple[float, list[str]]:
    score = 0.0
    reasons: list[str] = []

    if left.crime_type and left.crime_type == right.crime_type:
        score += 0.35
        reasons.append("shared crime type")

    shared_locations = set(left.locations) & set(right.locations)
    if shared_locations:
        score += min(0.25, 0.08 * len(shared_locations))
        reasons.append("shared location")

    shared_people = set(left.accused_names + left.victim_names) & set(right.accused_names + right.victim_names)
    if shared_people:
        score += min(0.25, 0.1 * len(shared_people))
        reasons.append("shared entity")

    shared_sections = set(left.ipc_sections) & set(right.ipc_sections)
    if shared_sections:
        score += min(0.15, 0.05 * len(shared_sections))
        reasons.append("shared IPC sections")

    return round(score, 3), reasons


def graph_edges_frame(graph: nx.Graph) -> pd.DataFrame:
    rows = []
    for source, target, attrs in graph.edges(data=True):
        rows.append(
            {
                "source": source,
                "target": target,
                "weight": attrs.get("weight", 0),
                "reasons": attrs.get("reasons", ""),
            }
        )
    return pd.DataFrame(rows)


def graph_metrics(graph: nx.Graph) -> dict:
    if graph.number_of_nodes() == 0:
        return {"nodes": 0, "edges": 0, "density": 0.0, "components": 0}
    return {
        "nodes": graph.number_of_nodes(),
        "edges": graph.number_of_edges(),
        "density": round(nx.density(graph), 4),
        "components": nx.number_connected_components(graph),
    }
