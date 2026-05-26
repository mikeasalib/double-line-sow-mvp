"""
Output exporters.
Generates JIRA CSV, Markdown timeline, and JSON outputs.
"""
import csv
import json
import io
from pathlib import Path

from .estimator import EstimatedTask
from .dependency import ResolvedPlan
from .parser import ClientContext


def export_jira_csv(plan: ResolvedPlan, output_path: str = "output/jira_import.csv") -> str:
    """
    Generate JIRA-importable CSV.
    Columns mapped to the standard workflow:
    Backlog → To Do (set estimate) → In Progress → To Review → Customer Approval
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "Summary", "Description", "Issue Type", "Priority",
        "Story Points", "Original Estimate", "Component",
        "Labels", "Sprint Phase", "Assignee Role",
        "Dependencies", "Confidence", "Estimation Rationale",
    ]

    rows = []
    for task in plan.ordered_tasks:
        # Convert hours to story points (rough: 1 point ≈ 4 hours)
        story_points = max(1, round(task.adjusted_hours / 4))

        # Format estimate as JIRA time format (e.g., "16h")
        original_estimate = f"{task.adjusted_hours}h"

        rows.append({
            "Summary": task.task_name,
            "Description": f"[{task.task_id}] {task.category}\n\nMatch type: {task.match_type}\nConfidence: {task.confidence}\n\n{task.rationale}",
            "Issue Type": "Task",
            "Priority": "High" if task.confidence == "high" else "Medium" if task.confidence == "medium" else "Low",
            "Story Points": story_points,
            "Original Estimate": original_estimate,
            "Component": task.category,
            "Labels": f"{task.phase},{task.match_type}",
            "Sprint Phase": task.phase,
            "Assignee Role": task.role,
            "Dependencies": ", ".join(task.dependencies) if task.dependencies else "",
            "Confidence": task.confidence,
            "Estimation Rationale": task.rationale,
        })

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    return output_path


def export_markdown(
    plan: ResolvedPlan,
    context: ClientContext,
    output_path: str = "output/project_timeline.md",
) -> str:
    """Generate a Markdown project timeline with phases and critical path."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    lines = []
    lines.append(f"# Project Plan: {context.organization_name or 'Engagement'}")
    lines.append("")
    lines.append(f"**Users:** {context.user_count} | **Timeline:** {context.timeline_weeks} weeks | **Platform:** {context.current_platform} → {', '.join(context.target_services)}")
    if context.is_federal:
        lines.append(f"**Compliance:** {', '.join(context.compliance_requirements)}")
    lines.append("")

    # Summary
    lines.append("## Summary")
    lines.append("")
    lines.append(f"| Metric | Value |")
    lines.append(f"|--------|-------|")
    lines.append(f"| Total Estimated Hours | **{plan.total_hours:.0f}h** |")
    for phase, hours in sorted(plan.hours_by_phase.items(), key=lambda x: {"Discovery": 0, "Planning": 1, "Build": 2, "Migration": 3, "Testing": 4, "Cutover": 5, "Hypercare": 6}.get(x[0], 99)):
        lines.append(f"| {phase} | {hours:.0f}h |")
    lines.append("")

    lines.append("### Hours by Role")
    lines.append("")
    for role, hours in sorted(plan.hours_by_role.items(), key=lambda x: -x[1]):
        lines.append(f"- **{role}:** {hours:.0f}h")
    lines.append("")

    # Critical path
    if plan.critical_path:
        lines.append("## Critical Path")
        lines.append("")
        for tid in plan.critical_path:
            task = next((t for t in plan.ordered_tasks if t.task_id == tid), None)
            if task:
                lines.append(f"→ **{task.task_name}** ({task.adjusted_hours}h, {task.phase})")
        lines.append("")

    # Tasks by phase
    lines.append("## Task Breakdown by Phase")
    lines.append("")

    current_phase = None
    for task in plan.ordered_tasks:
        if task.phase != current_phase:
            current_phase = task.phase
            lines.append(f"### {current_phase}")
            lines.append("")

        confidence_icon = "🟢" if task.confidence == "high" else "🟡" if task.confidence == "medium" else "🔴"
        critical = " ⚡" if task.task_id in plan.critical_path else ""
        deps = f" (depends on: {', '.join(task.dependencies)})" if task.dependencies else ""

        lines.append(f"- {confidence_icon} **{task.task_name}** [{task.task_id}]{critical}")
        lines.append(f"  - Role: {task.role} | Hours: {task.adjusted_hours}h (range: {task.low_hours}-{task.high_hours}h)")
        lines.append(f"  - {task.rationale}{deps}")
        lines.append("")

    # Warnings
    if plan.dependency_warnings:
        lines.append("## Warnings")
        lines.append("")
        for w in plan.dependency_warnings:
            lines.append(f"⚠️ {w}")
        lines.append("")

    content = "\n".join(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return output_path


def export_json(
    plan: ResolvedPlan,
    context: ClientContext,
    output_path: str = "output/plan.json",
) -> str:
    """Export the full plan as structured JSON."""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    data = {
        "client": {
            "name": context.organization_name,
            "user_count": context.user_count,
            "current_platform": context.current_platform,
            "target_services": context.target_services,
            "is_federal": context.is_federal,
            "timeline_weeks": context.timeline_weeks,
        },
        "summary": {
            "total_hours": plan.total_hours,
            "hours_by_phase": plan.hours_by_phase,
            "hours_by_role": plan.hours_by_role,
            "task_count": len(plan.ordered_tasks),
            "critical_path": plan.critical_path,
        },
        "tasks": [
            {
                "id": t.task_id,
                "name": t.task_name,
                "category": t.category,
                "role": t.role,
                "phase": t.phase,
                "baseline_hours": t.baseline_hours,
                "adjusted_hours": t.adjusted_hours,
                "range": [t.low_hours, t.high_hours],
                "confidence": t.confidence,
                "rationale": t.rationale,
                "dependencies": t.dependencies,
                "match_type": t.match_type,
            }
            for t in plan.ordered_tasks
        ],
        "warnings": plan.dependency_warnings,
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return output_path
