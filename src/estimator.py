"""
Estimation engine.
Applies client context modifiers to baseline catalog estimates.
Produces adjusted hours with confidence scoring and rationale.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path

from .parser import ClientContext
from .matcher import TaskMatch


@dataclass
class EstimatedTask:
    task_id: str
    task_name: str
    category: str
    role: str
    phase: str
    baseline_hours: float
    adjusted_hours: float
    low_hours: float
    high_hours: float
    confidence: str
    rationale: str
    dependencies: list[str]
    match_type: str


def load_modifiers(catalog_path: str = "data/task_catalog.json") -> dict:
    """Load estimation modifiers from catalog."""
    path = Path(catalog_path)
    if not path.exists():
        path = Path(__file__).parent.parent / catalog_path
    with open(path) as f:
        data = json.load(f)
    return data.get("estimation_modifiers", {})


def estimate_tasks(
    matches: list[TaskMatch],
    context: ClientContext,
) -> list[EstimatedTask]:
    """
    Apply estimation modifiers based on client context.
    Returns adjusted estimates with confidence scoring.
    """
    modifiers = load_modifiers()
    results = []

    # Determine user count modifier
    uc = context.user_count
    if uc < 500:
        user_mod = modifiers.get("user_count", {}).get("under_500", 0.75)
        user_label = f"<500 users (×{user_mod})"
    elif uc <= 2000:
        user_mod = modifiers.get("user_count", {}).get("500_to_2000", 1.0)
        user_label = f"500-2000 users (×{user_mod})"
    elif uc <= 10000:
        user_mod = modifiers.get("user_count", {}).get("2000_to_10000", 1.4)
        user_label = f"2000-10000 users (×{user_mod})"
    else:
        user_mod = modifiers.get("user_count", {}).get("over_10000", 1.8)
        user_label = f"10000+ users (×{user_mod})"

    # Determine complexity modifier
    platform = context.current_platform.lower()
    if "multi" in platform or "hybrid" in platform:
        complexity_mod = modifiers.get("complexity", {}).get("multi_source_migration", 1.4)
        complexity_label = "multi-source migration"
    elif any(kw in platform for kw in ["365", "exchange", "gmail", "workspace"]):
        complexity_mod = modifiers.get("complexity", {}).get("single_source_migration", 1.0)
        complexity_label = "single-source migration"
    elif platform == "" or "new" in platform or "greenfield" in platform:
        complexity_mod = modifiers.get("complexity", {}).get("greenfield", 0.8)
        complexity_label = "greenfield"
    else:
        complexity_mod = 1.0
        complexity_label = "standard"

    # Federal overhead
    if context.is_federal:
        if any("high" in c.lower() for c in context.compliance_requirements):
            fed_mod = modifiers.get("federal_overhead", {}).get("fedramp_high", 1.4)
            fed_label = "FedRAMP High"
        elif any("il" in c.lower() for c in context.compliance_requirements):
            fed_mod = modifiers.get("federal_overhead", {}).get("il4_il5", 1.5)
            fed_label = "IL4/IL5"
        else:
            fed_mod = modifiers.get("federal_overhead", {}).get("fedramp_moderate", 1.25)
            fed_label = "FedRAMP Moderate"
    else:
        fed_mod = 1.0
        fed_label = "none"

    combined_modifier = user_mod * complexity_mod * fed_mod

    for match in matches:
        task = match.catalog_task
        baseline = task.estimated_hours
        adjusted = round(baseline * combined_modifier, 1)

        low_range = task.variance_range[0]
        high_range = task.variance_range[1]
        low_hours = round(adjusted * low_range, 1)
        high_hours = round(adjusted * high_range, 1)

        # Build rationale
        parts = [f"Baseline: {baseline}h"]
        if user_mod != 1.0:
            parts.append(f"User scale: {user_label}")
        if complexity_mod != 1.0:
            parts.append(f"Complexity: {complexity_label} (×{complexity_mod})")
        if fed_mod != 1.0:
            parts.append(f"Federal: {fed_label} (×{fed_mod})")
        parts.append(f"Range: {low_hours}h - {high_hours}h")

        results.append(EstimatedTask(
            task_id=task.id,
            task_name=task.name,
            category=task.category,
            role=task.role,
            phase=task.phase,
            baseline_hours=baseline,
            adjusted_hours=adjusted,
            low_hours=low_hours,
            high_hours=high_hours,
            confidence=match.confidence,
            rationale=" | ".join(parts),
            dependencies=task.dependencies,
            match_type=match.match_type,
        ))

    return results
