"""
Dependency resolver.
Orders tasks by dependencies and identifies the critical path.
"""
from collections import defaultdict
from dataclasses import dataclass, field

from .estimator import EstimatedTask


PHASE_ORDER = {
    "Discovery": 0,
    "Planning": 1,
    "Build": 2,
    "Migration": 3,
    "Testing": 4,
    "Cutover": 5,
    "Hypercare": 6,
}


@dataclass
class ResolvedPlan:
    ordered_tasks: list[EstimatedTask] = field(default_factory=list)
    critical_path: list[str] = field(default_factory=list)
    total_hours: float = 0.0
    hours_by_phase: dict = field(default_factory=dict)
    hours_by_role: dict = field(default_factory=dict)
    dependency_warnings: list[str] = field(default_factory=list)


def resolve_dependencies(tasks: list[EstimatedTask]) -> ResolvedPlan:
    """
    Topological sort of tasks by dependencies.
    Identifies critical path (longest dependency chain by hours).
    """
    result = ResolvedPlan()
    task_map = {t.task_id: t for t in tasks}
    active_ids = set(task_map.keys())

    # Check for missing dependencies
    for task in tasks:
        for dep_id in task.dependencies:
            if dep_id not in active_ids:
                result.dependency_warnings.append(
                    f"Task {task.task_id} ({task.task_name}) depends on {dep_id} which is not in the plan"
                )

    # Topological sort (Kahn's algorithm)
    in_degree = defaultdict(int)
    adjacency = defaultdict(list)

    for task in tasks:
        if task.task_id not in in_degree:
            in_degree[task.task_id] = 0
        for dep_id in task.dependencies:
            if dep_id in active_ids:
                adjacency[dep_id].append(task.task_id)
                in_degree[task.task_id] += 1

    queue = []
    for tid in active_ids:
        if in_degree[tid] == 0:
            queue.append(tid)

    # Sort queue by phase order for deterministic output
    queue.sort(key=lambda tid: PHASE_ORDER.get(task_map[tid].phase, 99))

    ordered = []
    while queue:
        queue.sort(key=lambda tid: PHASE_ORDER.get(task_map[tid].phase, 99))
        current = queue.pop(0)
        ordered.append(task_map[current])

        for neighbor in adjacency[current]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # Detect cycles (tasks not in ordered list)
    if len(ordered) < len(tasks):
        missing = active_ids - {t.task_id for t in ordered}
        result.dependency_warnings.append(
            f"Circular dependency detected involving tasks: {missing}"
        )
        # Add remaining tasks at end
        for task in tasks:
            if task.task_id in missing:
                ordered.append(task)

    result.ordered_tasks = ordered

    # Calculate critical path (longest path by cumulative hours)
    earliest_finish = {}
    predecessor = {}
    
    for task in ordered:
        dep_finishes = [earliest_finish.get(d, 0) for d in task.dependencies if d in active_ids]
        start = max(dep_finishes) if dep_finishes else 0
        finish = start + task.adjusted_hours
        earliest_finish[task.task_id] = finish
        
        if dep_finishes:
            max_dep = max(task.dependencies, key=lambda d: earliest_finish.get(d, 0))
            predecessor[task.task_id] = max_dep
        else:
            predecessor[task.task_id] = None

    # Trace back from the task with the latest finish
    if earliest_finish:
        end_task = max(earliest_finish, key=earliest_finish.get)
        path = []
        current = end_task
        while current:
            path.append(current)
            current = predecessor.get(current)
        result.critical_path = list(reversed(path))

    # Summaries
    result.total_hours = sum(t.adjusted_hours for t in ordered)

    phase_hours = defaultdict(float)
    role_hours = defaultdict(float)
    for task in ordered:
        phase_hours[task.phase] += task.adjusted_hours
        role_hours[task.role] += task.adjusted_hours

    result.hours_by_phase = dict(phase_hours)
    result.hours_by_role = dict(role_hours)

    return result
