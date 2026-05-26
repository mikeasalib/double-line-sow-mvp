"""
Task catalog matcher.
Maps parsed SOW deliverables to standard task catalog entries.
Handles direct matches, inferred matches, gaps, and scope exclusions.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .parser import Deliverable, ScopeExclusion


@dataclass
class CatalogTask:
    id: str
    category: str
    name: str
    description: str
    estimated_hours: float
    variance_range: list[float]
    role: str
    phase: str
    dependencies: list[str]
    federal_flag: bool
    tags: list[str]


@dataclass
class TaskMatch:
    catalog_task: CatalogTask
    matched_deliverable: Optional[Deliverable]
    match_type: str  # "direct", "inferred", "catalog_standard"
    confidence: str  # "high", "medium", "low"
    match_reason: str


@dataclass
class MatchResult:
    matched_tasks: list[TaskMatch] = field(default_factory=list)
    unmatched_deliverables: list[Deliverable] = field(default_factory=list)
    excluded_tasks: list[tuple[CatalogTask, str]] = field(default_factory=list)


def load_catalog(catalog_path: str = "data/task_catalog.json") -> list[CatalogTask]:
    """Load task catalog from JSON file."""
    path = Path(catalog_path)
    if not path.exists():
        # Try relative to project root
        path = Path(__file__).parent.parent / catalog_path

    with open(path, "r") as f:
        data = json.load(f)

    tasks = []
    for t in data["tasks"]:
        tasks.append(CatalogTask(
            id=t["id"],
            category=t["category"],
            name=t["name"],
            description=t["description"],
            estimated_hours=t["estimated_hours"],
            variance_range=t["variance_range"],
            role=t["role"],
            phase=t["phase"],
            dependencies=t["dependencies"],
            federal_flag=t["federal_flag"],
            tags=t["tags"],
        ))
    return tasks


def match_deliverables(
    deliverables: list[Deliverable],
    exclusions: list[ScopeExclusion],
    catalog: list[CatalogTask],
    is_federal: bool = False,
) -> MatchResult:
    """
    Match SOW deliverables against the task catalog.
    
    Logic:
    1. For each deliverable, find catalog tasks with overlapping keywords/tags.
    2. Score matches by keyword overlap count.
    3. Flag deliverables with no catalog match as gaps.
    4. Remove catalog tasks that match scope exclusions.
    5. Include federal tasks only when is_federal is True.
    """
    result = MatchResult()
    exclusion_keywords = set()
    for ex in exclusions:
        exclusion_keywords.update(kw.lower() for kw in ex.keywords)

    # Filter catalog: remove federal tasks for non-federal engagements
    active_catalog = [t for t in catalog if not t.federal_flag or is_federal]

    matched_task_ids = set()

    for deliverable in deliverables:
        d_keywords = set(kw.lower() for kw in deliverable.keywords)
        d_text = f"{deliverable.name} {deliverable.description}".lower()
        best_matches = []

        for task in active_catalog:
            t_keywords = set(kw.lower() for kw in task.tags)

            # Check if this task is excluded by scope
            if t_keywords & exclusion_keywords:
                if task.id not in [et[0].id for et in result.excluded_tasks]:
                    reason = f"Excluded: matches scope exclusion keywords {t_keywords & exclusion_keywords}"
                    result.excluded_tasks.append((task, reason))
                continue

            # Score: keyword overlap + text matching
            keyword_overlap = len(d_keywords & t_keywords)
            text_matches = sum(1 for tag in task.tags if tag.lower() in d_text)
            score = keyword_overlap * 2 + text_matches

            if score > 0:
                match_type = "direct" if keyword_overlap >= 2 else "inferred"
                confidence = "high" if score >= 4 else "medium" if score >= 2 else "low"
                best_matches.append((task, score, match_type, confidence))

        if best_matches:
            # Sort by score descending, take top matches
            best_matches.sort(key=lambda x: x[1], reverse=True)
            for task, score, match_type, confidence in best_matches[:3]:
                if task.id not in matched_task_ids:
                    result.matched_tasks.append(TaskMatch(
                        catalog_task=task,
                        matched_deliverable=deliverable,
                        match_type=match_type,
                        confidence=confidence,
                        match_reason=f"Score {score}: keyword overlap with deliverable '{deliverable.name}'",
                    ))
                    matched_task_ids.add(task.id)
        else:
            result.unmatched_deliverables.append(deliverable)

    # Add standard PM tasks that should always be included
    pm_always_include = {"PM-001", "PM-002", "PM-003", "PM-005"}
    for task in active_catalog:
        if task.id in pm_always_include and task.id not in matched_task_ids:
            result.matched_tasks.append(TaskMatch(
                catalog_task=task,
                matched_deliverable=None,
                match_type="catalog_standard",
                confidence="high",
                match_reason="Standard PM task included for all engagements",
            ))
            matched_task_ids.add(task.id)

    return result
