#!/usr/bin/env python3
"""
complete-step.py - Complete the current step of a stepped workflow

Usage: python complete-step.py [name] [--step N]

Advances session state: increments current step, updates steps completed,
recalculates completion percentage, and marks workflow as completed when
all steps are done.

If no name provided, detects from active session.
If --step N provided, completes that specific step instead of current step.
"""

import argparse
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    print("Error: PyYAML required. Install with: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


def find_project_root() -> Path:
    """Find project root by looking for .pennyfarthing directory."""
    # Honor explicit PROJECT_ROOT override
    import os
    override = os.environ.get("PROJECT_ROOT")
    if override:
        return Path(override)

    current = Path.cwd()
    while current != current.parent:
        if (current / ".pennyfarthing").is_dir():
            return current
        current = current.parent
    print("Error: Could not find .pennyfarthing/ directory", file=sys.stderr)
    print("Are you in a Pennyfarthing-enabled project?", file=sys.stderr)
    sys.exit(1)


def parse_session_field(content: str, field: str) -> str:
    """Extract a field value from session markdown."""
    pattern = rf"^- \*\*{re.escape(field)}:\*\*\s*(.+)$"
    match = re.search(pattern, content, re.MULTILINE)
    return match.group(1).strip() if match else ""


def find_session_file(session_dir: Path, workflow_name: str | None) -> tuple[Path, str]:
    """Find session file and determine workflow name.

    Returns (session_path, workflow_name).
    """
    if workflow_name:
        session_file = session_dir / f"{workflow_name}-workflow-session.md"
        if not session_file.exists():
            print(f"Error: No session found for workflow '{workflow_name}'", file=sys.stderr)
            print(f"\nUse `/workflow start {workflow_name}` to begin.", file=sys.stderr)
            sys.exit(1)
        return session_file, workflow_name

    # Auto-detect from session directory
    sessions = list(session_dir.glob("*-workflow-session.md"))
    if not sessions:
        print("Error: No active workflow session found.", file=sys.stderr)
        print("\nUsage: complete-step.py [name] [--step N]", file=sys.stderr)
        sys.exit(1)

    session_file = sorted(sessions)[0]
    content = session_file.read_text()

    # Try to extract workflow name from content
    wf_match = re.search(r"^\*\*Workflow:\*\*\s*(.+)$", content, re.MULTILINE)
    if wf_match:
        name = wf_match.group(1).strip()
    else:
        # Derive from filename
        name = session_file.stem.replace("-workflow-session", "")

    return session_file, name


def find_workflow_file(workflows_dir: Path, workflow_name: str) -> Path:
    """Find workflow YAML definition."""
    flat = workflows_dir / f"{workflow_name}.yaml"
    if flat.exists():
        return flat

    nested = workflows_dir / workflow_name / "workflow.yaml"
    if nested.exists():
        return nested

    print(f"Error: Workflow definition '{workflow_name}' not found", file=sys.stderr)
    sys.exit(1)


def count_steps(steps_path: Path) -> int:
    """Count step files in a directory."""
    return len([
        f for f in steps_path.iterdir()
        if f.is_file() and re.match(r"step-\d+", f.name) and f.suffix == ".md"
    ])


def parse_steps_completed(value: str) -> list[int]:
    """Parse steps completed array from string like '[1, 2, 3]'."""
    if not value or value == "[]":
        return []
    # Extract numbers from the bracket notation
    return [int(n) for n in re.findall(r"\d+", value)]


def format_steps_completed(steps: list[int]) -> str:
    """Format steps list as bracket notation."""
    if not steps:
        return "[]"
    return "[" + ", ".join(str(s) for s in steps) + "]"


def find_next_step_file(steps_path: Path, step_number: int) -> Path | None:
    """Find step file for a given step number."""
    padded = f"{step_number:02d}"
    matches = sorted([
        f for f in steps_path.iterdir()
        if f.is_file()
        and (f.name.startswith(f"step-{padded}") or f.name.startswith(f"step-{step_number}-"))
        and f.suffix == ".md"
    ])
    return matches[0] if matches else None


def strip_frontmatter(content: str) -> str:
    """Remove YAML frontmatter from step file content."""
    if not content.startswith("---"):
        return content
    # Find the closing ---
    end = content.find("---", 3)
    if end == -1:
        return content
    return content[end + 3:].lstrip("\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Complete the current step of a stepped workflow"
    )
    parser.add_argument("name", nargs="?", default=None,
                        help="Workflow name (auto-detects from session if omitted)")
    parser.add_argument("--step", type=int, default=None, dest="step_override",
                        help="Complete a specific step number instead of current step")
    args = parser.parse_args()

    project_root = find_project_root()
    workflows_dir = project_root / ".pennyfarthing" / "workflows"
    session_dir = project_root / ".session"

    # Find session file
    session_file, workflow_name = find_session_file(session_dir, args.name)
    content = session_file.read_text()

    # Parse session state
    current_step_str = parse_session_field(content, "Current Step") or "1"
    current_step = int(current_step_str)
    mode = parse_session_field(content, "Mode") or "create"
    status = parse_session_field(content, "Status") or "in_progress"
    steps_completed_str = parse_session_field(content, "Steps Completed") or "[]"

    # Check if already completed
    if status == "completed":
        print(f"# Workflow Already Completed: {workflow_name}")
        print()
        print("This workflow has already been completed.")
        print()
        print("To start a new session, delete the session file:")
        print("```bash")
        print(f'rm "{session_file}"')
        print("```")
        print()
        print(f"Then run `/workflow start {workflow_name}`")
        return 0

    # Determine which step to complete
    completing_step = args.step_override if args.step_override is not None else current_step

    # Find workflow file and resolve steps path
    workflow_file = find_workflow_file(workflows_dir, workflow_name)
    workflow_dir = workflow_file.parent

    with open(workflow_file) as f:
        wf_data = yaml.safe_load(f)

    wf = wf_data.get("workflow", {})

    # Resolve steps path based on mode
    modes = wf.get("modes", {})
    mode_path = modes.get(mode)
    if mode_path and mode_path != "null":
        steps_path_str = mode_path
    else:
        steps_path_str = wf.get("steps", {}).get("path", ".")

    # Resolve relative path
    if steps_path_str.startswith("./"):
        steps_path = workflow_dir / steps_path_str[2:]
    elif not Path(steps_path_str).is_absolute():
        steps_path = project_root / steps_path_str
    else:
        steps_path = Path(steps_path_str)

    # Count total steps
    step_count = count_steps(steps_path)

    # Update Steps Completed array
    steps_completed = parse_steps_completed(steps_completed_str)
    if completing_step not in steps_completed:
        steps_completed.append(completing_step)
    new_steps_completed = format_steps_completed(steps_completed)

    # Calculate new current step
    next_step = completing_step + 1

    # Count completed and calculate percentage
    completed_count = len(steps_completed)
    completion_pct = (completed_count * 100 // step_count) if step_count > 0 else 0

    # Determine new status
    new_status = "completed" if completed_count >= step_count else "in_progress"

    # Update timestamp
    now = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Update session file content
    content = re.sub(
        r"^- \*\*Current Step:\*\*.*$",
        f"- **Current Step:** {next_step}",
        content, flags=re.MULTILINE
    )
    content = re.sub(
        r"^- \*\*Steps Completed:\*\*.*$",
        f"- **Steps Completed:** {new_steps_completed}",
        content, flags=re.MULTILINE
    )
    content = re.sub(
        r"^- \*\*Last Updated:\*\*.*$",
        f"- **Last Updated:** {now}",
        content, flags=re.MULTILINE
    )
    content = re.sub(
        r"^- \*\*Status:\*\*.*$",
        f"- **Status:** {new_status}",
        content, flags=re.MULTILINE
    )
    content = re.sub(
        r"^- Completion:.*$",
        f"- Completion: {completion_pct}%",
        content, flags=re.MULTILINE
    )

    # Write updated session file
    session_file.write_text(content)

    # Output result
    if new_status == "completed":
        print(f"# Workflow Complete: {workflow_name}")
        print()
        print(f"All {step_count} steps completed!")
        print()
        print(f"**Final Progress:** {completion_pct}%")
        print(f"**Steps Completed:** {new_steps_completed}")
        print()
        print(f"Session updated: {session_file}")
    else:
        print(f"# Step {completing_step} Complete")
        print()
        print(f"**Progress:** Step {next_step} of {step_count} ({completion_pct}% complete)")
        print(f"**Steps Completed:** {new_steps_completed}")
        print()
        print("---")
        print()
        print(f"## Step {next_step} of {step_count}")
        print()

        # Find and output next step file
        next_step_file = find_next_step_file(steps_path, next_step)
        if next_step_file:
            step_content = next_step_file.read_text()
            print(strip_frontmatter(step_content))

        print()
        print("---")
        print()
        print("**Controls:**")
        print("- `C` - Continue to next step")
        print("- `/workflow status` - Check progress")

    return 0


if __name__ == "__main__":
    sys.exit(main())
