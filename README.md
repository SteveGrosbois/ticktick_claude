# ticktick-cli

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

## Claude Cowork Integration

### `claude` tag — task list for Claude

Tag any task in TickTick with `claude` and it will appear when running:

```bash
ticktick claude-tasks --json
```

This JSON output is designed to be consumed by Claude cowork to assist with or complete the tagged tasks.

### `claude-research` tag — automated research

Tag a task with `claude-research` and the CLI will:
1. Search the web for information related to the task title/description
2. Append a formatted summary of findings to the task description
3. Add actionable next steps as checklist items on the task

```bash
# Preview what would happen (no changes made)
ticktick claude-research-tasks --dry-run

# Run research and update tasks in TickTick
ticktick claude-research-tasks
```

Research uses DuckDuckGo (no API key required) to find relevant sources, then compiles numbered findings with links and generates follow-up checklist items.
