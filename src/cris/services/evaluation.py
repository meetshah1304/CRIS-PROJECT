from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EvaluationPlan:
    track: str
    metric: str
    target: str
    notes: str


def recommended_evaluation_tracks() -> list[EvaluationPlan]:
    return [
        EvaluationPlan("OCR accuracy", "CER, WER, page confidence", "Maximize readable text recovery", "Measure by page and by document"),
        EvaluationPlan("Field extraction", "Precision, recall, F1", "Reliable structured FIR parsing", "Evaluate per label such as FIR number, station, sections, accused, location"),
        EvaluationPlan("Similarity ranking", "MRR, Recall@K, NDCG@K", "Relevant case retrieval", "Use analyst-labeled related FIR pairs"),
        EvaluationPlan("Cluster coherence", "Silhouette, purity, topic consistency", "Meaningful case groupings", "Review clusters by investigators"),
        EvaluationPlan("Pattern linkage", "Analyst validation rate", "Trustworthy graph edges", "Domain review is essential for final acceptance"),
    ]
