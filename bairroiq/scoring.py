from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

import pandas as pd


_REQUIRED_COLUMNS = {
    "neighborhood",
    "latitude",
    "longitude",
    "formal_jobs_score",
    "robbery_index",
    "lighting_led",
    "trees_score",
    "mobility_score",
    "affordability_score",
}
_SCENARIO_DIMENSIONS = (
    ("trees", "Arborização", "trees_score"),
    ("safety", "Segurança", "safety_score"),
    ("mobility", "Mobilidade", "mobility_score"),
    ("budget", "Orçamento", "affordability_score"),
)


@dataclass(frozen=True)
class ScenarioInsight:
    leader_name: str
    leader_score: float
    dominant_priority: str | None
    dominant_weight: int
    recommended_name: str | None
    recommended_score: float | None


def score_neighborhoods(
    metrics: pd.DataFrame, weights: Mapping[str, int | float]
) -> pd.DataFrame:
    missing_columns = _REQUIRED_COLUMNS.difference(metrics.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"A tabela de bairros não contém as colunas: {missing}.")

    total_weight = sum(weights.values())
    if total_weight <= 0:
        raise ValueError("Escolha ao menos uma prioridade com peso maior que zero.")

    scored = metrics.copy()
    scored["safety_score"] = (100 - scored["robbery_index"] * 10).clip(0, 100)
    scored["priority_score"] = (
        scored["trees_score"] * weights["trees"]
        + scored["safety_score"] * weights["safety"]
        + scored["mobility_score"] * weights["mobility"]
        + scored["affordability_score"] * weights["budget"]
    ) / total_weight
    return scored.sort_values("priority_score", ascending=False).reset_index(drop=True)


def build_scenario_insight(
    scored_neighborhoods: pd.DataFrame,
    weights: Mapping[str, int | float],
    selected_names: list[str] | None = None,
) -> ScenarioInsight:
    compared = scored_neighborhoods
    if selected_names:
        selected = scored_neighborhoods[
            scored_neighborhoods["neighborhood"].isin(selected_names)
        ]
        if not selected.empty:
            compared = selected

    leader = compared.sort_values("priority_score", ascending=False).iloc[0]
    active_dimensions = [
        dimension
        for dimension in _SCENARIO_DIMENSIONS
        if weights.get(dimension[0], 0) > 0
    ]
    if not active_dimensions:
        return ScenarioInsight(
            leader_name=str(leader["neighborhood"]),
            leader_score=float(leader["priority_score"]),
            dominant_priority=None,
            dominant_weight=0,
            recommended_name=None,
            recommended_score=None,
        )

    dominant = max(active_dimensions, key=lambda dimension: weights[dimension[0]])
    lowest = compared.sort_values(dominant[2], ascending=True).iloc[0]
    return ScenarioInsight(
        leader_name=str(leader["neighborhood"]),
        leader_score=float(leader["priority_score"]),
        dominant_priority=dominant[1],
        dominant_weight=int(weights[dominant[0]]),
        recommended_name=str(lowest["neighborhood"]),
        recommended_score=float(lowest[dominant[2]]),
    )
