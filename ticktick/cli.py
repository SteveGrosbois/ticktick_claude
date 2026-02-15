"""Command-line interface for TickTick."""

import argparse
import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from ticktick.api import TickTickClient, PRIORITY_LABELS
from ticktick.auth import authorize, DEFAULT_TOKEN_PATH


def _load_env():
    """Load .env from the current directory or project root."""
    # Try current dir, then script's parent dir
    for candidate in [Path.cwd() / ".env", Path(__file__).resolve().parent.parent / ".env"]:
        if candidate.exists():
            load_dotenv(candidate)
            return
    load_dotenv()  # fallback to default search


def _get_credentials() -> tuple[str, str, str]:
    client_id = os.environ.get("TICKTICK_CLIENT_ID", "")
    client_secret = os.environ.get("TICKTICK_CLIENT_SECRET", "")
    redirect_uri = os.environ.get("TICKTICK_REDIRECT_URI", "http://localhost:8080/callback")
    if not client_id or not client_secret:
        print("Error: TICKTICK_CLIENT_ID and TICKTICK_CLIENT_SECRET must be set.")
        print("Copy .env.example to .env and fill in your credentials.")
        print("Register an app at https://developer.ticktick.com/manage")
        sys.exit(1)
    return client_id, client_secret, redirect_uri


def _get_client() -> TickTickClient:
    client_id, client_secret, _ = _get_credentials()
    try:
        return TickTickClient(client_id=client_id, client_secret=client_secret)
    except RuntimeError as e:
        print(f"Error: {e}")
        sys.exit(1)


# ------------------------------------------------------------------
# Formatters
# ------------------------------------------------------------------

def _format_task(task: dict, verbose: bool = False) -> str:
    priority = PRIORITY_LABELS.get(task.get("priority", 0), "?")
    tags = ", ".join(task.get("tags", []))
    project = task.get("_project_name", "")
    status = "done" if task.get("status", 0) != 0 else "open"

    line = f"  [{status}] {task['title']}"
    if tags:
        line += f"  (tags: {tags})"
    if priority != "none":
        line += f"  [priority: {priority}]"
    if project:
        line += f"  [{project}]"

    if verbose:
        line += f"\n         id: {task.get('id', '?')}"
        line += f"\n    project: {task.get('projectId', '?')}"
        if task.get("content"):
            line += f"\n    content: {task['content']}"
        if task.get("dueDate"):
            line += f"\n        due: {task['dueDate']}"

    return line


# ------------------------------------------------------------------
# Commands
# ------------------------------------------------------------------

def cmd_auth(args):
    """Authorize with TickTick and save tokens."""
    client_id, client_secret, redirect_uri = _get_credentials()
    authorize(client_id, client_secret, redirect_uri)


def cmd_projects(args):
    """List all TickTick projects."""
    client = _get_client()
    projects = client.get_projects()
    if not projects:
        print("No projects found.")
        return
    for p in projects:
        print(f"  {p['name']}  (id: {p['id']})")


def cmd_tasks(args):
    """List tasks, optionally filtered by tag or project."""
    client = _get_client()

    if args.tag:
        tasks = client.get_tasks_by_tag(args.tag)
    elif args.project:
        data = client.get_project_data(args.project)
        tasks = data.get("tasks", [])
        # Look up project name
        projects = {p["id"]: p["name"] for p in client.get_projects()}
        for t in tasks:
            t["_project_name"] = projects.get(args.project, "")
    else:
        tasks = client.get_all_tasks()

    # Filter to open tasks unless --all is set
    if not args.all:
        tasks = [t for t in tasks if t.get("status", 0) == 0]

    if args.json:
        print(json.dumps(tasks, indent=2, default=str))
        return

    if not tasks:
        print("No tasks found.")
        return

    print(f"Found {len(tasks)} task(s):\n")
    for task in tasks:
        print(_format_task(task, verbose=args.verbose))


def cmd_claude_tasks(args):
    """List tasks tagged with 'claude' — designed for Claude cowork."""
    client = _get_client()
    tasks = client.get_tasks_by_tag("claude")

    # Only open tasks
    tasks = [t for t in tasks if t.get("status", 0) == 0]

    if args.json:
        print(json.dumps(tasks, indent=2, default=str))
        return

    if not tasks:
        print("No open tasks tagged 'claude' found.")
        return

    print(f"Found {len(tasks)} task(s) tagged 'claude':\n")
    for task in tasks:
        print(_format_task(task, verbose=args.verbose))


def cmd_append_description(args):
    """Append text to a task's description."""
    client = _get_client()
    result = client.append_task_content(args.project_id, args.task_id, args.text)
    print(f"Updated task: {result.get('title', args.task_id)}")
    if result.get("content"):
        print(f"Description now:\n  {result['content']}")


def cmd_add_checklist(args):
    """Add checklist items to a task."""
    client = _get_client()
    result = client.add_checklist_items(args.project_id, args.task_id, args.items)
    items = result.get("items", [])
    print(f"Updated task: {result.get('title', args.task_id)}")
    print(f"Checklist ({len(items)} item(s)):")
    for item in items:
        status = "x" if item.get("status", 0) != 0 else " "
        print(f"  [{status}] {item['title']}")


def cmd_complete_task(args):
    """Mark a task as completed."""
    client = _get_client()

    # Fetch the task first to show its title in confirmation
    task = client.get_task(args.project_id, args.task_id)
    title = task.get("title", args.task_id)

    client.complete_task(args.project_id, args.task_id)
    print(f"Completed task: {title}")


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():
    _load_env()

    parser = argparse.ArgumentParser(
        prog="ticktick",
        description="CLI for reading and managing TickTick tasks.",
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # auth
    subparsers.add_parser("auth", help="Authorize with TickTick (opens browser)")

    # projects
    subparsers.add_parser("projects", help="List all projects")

    # tasks
    tasks_parser = subparsers.add_parser("tasks", help="List tasks")
    tasks_parser.add_argument("--tag", "-t", help="Filter by tag name")
    tasks_parser.add_argument("--project", "-p", help="Filter by project ID")
    tasks_parser.add_argument("--all", "-a", action="store_true",
                              help="Include completed tasks")
    tasks_parser.add_argument("--verbose", "-v", action="store_true",
                              help="Show task details (IDs, content, due date)")
    tasks_parser.add_argument("--json", action="store_true",
                              help="Output as JSON")

    # claude-tasks (shortcut for --tag claude)
    claude_parser = subparsers.add_parser(
        "claude-tasks",
        help="List open tasks tagged 'claude' (for Claude cowork)",
    )
    claude_parser.add_argument("--verbose", "-v", action="store_true",
                               help="Show task details")
    claude_parser.add_argument("--json", action="store_true",
                               help="Output as JSON")

    # append-description
    append_parser = subparsers.add_parser(
        "append-description",
        help="Append text to a task's description",
    )
    append_parser.add_argument("project_id", help="Project ID")
    append_parser.add_argument("task_id", help="Task ID")
    append_parser.add_argument("text", help="Text to append to the description")

    # add-checklist
    checklist_parser = subparsers.add_parser(
        "add-checklist",
        help="Add checklist items to a task",
    )
    checklist_parser.add_argument("project_id", help="Project ID")
    checklist_parser.add_argument("task_id", help="Task ID")
    checklist_parser.add_argument("items", nargs="+", help="Checklist item titles")

    # complete-task
    complete_parser = subparsers.add_parser(
        "complete-task",
        help="Mark a task as completed",
    )
    complete_parser.add_argument("project_id", help="Project ID")
    complete_parser.add_argument("task_id", help="Task ID")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    commands = {
        "auth": cmd_auth,
        "projects": cmd_projects,
        "tasks": cmd_tasks,
        "claude-tasks": cmd_claude_tasks,
        "append-description": cmd_append_description,
        "add-checklist": cmd_add_checklist,
        "complete-task": cmd_complete_task,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
