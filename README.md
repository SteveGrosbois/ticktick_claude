# ticktick-claude

Command-line tool for reading and managing TickTick tasks via the [TickTick Open API](https://developer.ticktick.com). Designed for integration with Claude cowork — tag tasks with `claude` in TickTick to surface them for AI-assisted completion.

## Setup

### 1. Register a TickTick app

Go to <https://developer.ticktick.com/manage>, sign in, and create an app. Set the redirect URI to `http://localhost:8080/callback`. Note your **Client ID** and **Client Secret**.

### 2. Configure credentials

```bash
cp .env.example .env
# Edit .env with your Client ID and Client Secret
```

### 3. Install

```bash
pip install -e .
```

### 4. Authorize

```bash
ticktick auth
```

This opens your browser to authorize the app. Tokens are saved to `~/.ticktick_token.json`.

## Usage

```bash
# List all open tasks
ticktick tasks

# Create a simple task (goes to Inbox)
ticktick add-task "Buy milk"

# Create a task in a specific project with options
ticktick add-task "Fix login bug" --project Backend --priority high --due 2026-03-15 --tags urgent

# List tasks tagged "claude" (for Claude cowork)
ticktick claude-tasks

# List all projects
ticktick projects

# Filter by tag
ticktick tasks --tag work

# Filter by project ID
ticktick tasks --project <project-id>

# Include completed tasks
ticktick tasks --all

# Verbose output (IDs, content, due dates)
ticktick tasks --verbose

# JSON output (useful for piping to other tools)
ticktick tasks --json
ticktick claude-tasks --json
```

## Task Mutation Commands

These commands let you modify tasks directly from the CLI — useful as building blocks for Claude cowork or any automation.

```bash
# Append text to a task's description
ticktick append-description <project-id> <task-id> "Notes from research..."

# Add checklist items to a task
ticktick add-checklist <project-id> <task-id> "Step 1" "Step 2" "Step 3"

# Mark a task as completed
ticktick complete-task <project-id> <task-id>
```

Use `ticktick tasks --verbose` or `ticktick tasks --json` to find task and project IDs.

## Claude Cowork Integration

Tag any task in TickTick with `claude` and it will appear when running:

```bash
ticktick claude-tasks --json
```

This JSON output is designed to be consumed by Claude cowork to assist with or complete the tagged tasks. Claude can then use `append-description`, `add-checklist`, and `complete-task` to update tasks as it works on them.
