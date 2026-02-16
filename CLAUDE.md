# CLAUDE.md

Guide for AI assistants working on the ticktick-cli codebase.

## Project Overview

**ticktick-cli** is a Python CLI tool for reading and managing TickTick tasks via the [TickTick Open API v1](https://developer.ticktick.com). It includes a "Claude cowork" integration — tasks tagged `claude` in TickTick are surfaced for AI-assisted completion.

## Repository Structure

```
ticktick/
├── __init__.py          # Empty package init
├── auth.py              # OAuth2 authorization code flow (token exchange, refresh, storage)
├── api.py               # TickTickClient — thin wrapper around the TickTick REST API
└── cli.py               # argparse-based CLI with command dispatch
pyproject.toml           # Package metadata, dependencies, entry point
requirements.txt         # Pinned dependency list
.env.example             # Template for OAuth credentials
```

## Architecture

- **auth.py** — Handles the full OAuth2 authorization code flow: opens the user's browser, runs a local HTTP server on port 8080 to capture the callback, exchanges the code for tokens, and persists them to `~/.ticktick_token.json` with `0o600` permissions. Includes CSRF protection via a `state` parameter and automatic token refresh.
- **api.py** — `TickTickClient` wraps the TickTick Open API. All HTTP calls go through `_request()`, which automatically refreshes tokens on 401 responses. Tasks are enriched with a `_project_name` field. When updating tasks, the entire task object is sent back to the API to avoid losing fields.
- **cli.py** — Entry point (`ticktick` command). Loads `.env` credentials, maps subcommands to handler functions via a dictionary dispatch pattern. Supports both human-readable and JSON output modes.

## Key Commands (CLI)

| Command              | Description                                  |
|----------------------|----------------------------------------------|
| `ticktick auth`     | Run OAuth2 flow, save tokens                 |
| `ticktick projects` | List all projects with IDs                   |
| `ticktick tasks`    | List tasks (filters: `--tag`, `--project`, `--all`, `--verbose`, `--json`) |
| `ticktick claude-tasks` | List open tasks tagged "claude"          |
| `ticktick append-description <project> <task> <text>` | Append to task description |
| `ticktick add-checklist <project> <task> <items...>` | Add checklist items |
| `ticktick complete-task <project> <task>` | Mark task complete |

## Development Setup

```bash
# 1. Copy and fill in OAuth credentials
cp .env.example .env

# 2. Install in editable mode
pip install -e .

# 3. Authorize (opens browser)
ticktick auth
```

**Required environment variables** (in `.env`):
- `TICKTICK_CLIENT_ID` — OAuth2 client ID from https://developer.ticktick.com/manage
- `TICKTICK_CLIENT_SECRET` — OAuth2 client secret
- `TICKTICK_REDIRECT_URI` — defaults to `http://localhost:8080/callback`

## Dependencies

- **Python >= 3.10** (uses `X | Y` union types, `list[T]` generics)
- **requests** — HTTP client for all API calls
- **python-dotenv** — Loads `.env` files for credentials
- **setuptools** — Build backend

## Code Conventions

- **No test suite exists** — there are no tests, test framework, or CI/CD pipelines configured.
- **No linter/formatter configured** — no black, ruff, flake8, or mypy settings. Code follows standard PEP 8 style informally.
- **Type hints** are used in function signatures (`str`, `dict`, `list[str]`, `Path`, `dict | None`) but there is no type checker enforced.
- **Docstrings** are present on public methods (brief one-liners) but not on every function.
- **Private helpers** are prefixed with `_` (e.g., `_request`, `_load_env`, `_format_task`).
- **Constants** are module-level `UPPER_SNAKE_CASE` (e.g., `BASE_URL`, `PRIORITY_LABELS`).
- **Error handling** — CLI functions catch `RuntimeError` and exit with messages. The API client raises `requests` exceptions via `raise_for_status()`.
- **Field preservation** — When updating tasks via the API, the full task object is always sent back to prevent field loss (see `append_task_content` and `add_checklist_items`).

## Important Design Decisions

1. **Token storage**: Tokens live at `~/.ticktick_token.json` with restrictive file permissions (`0o600`). Never commit this file.
2. **Auto-refresh on 401**: `TickTickClient._request()` transparently refreshes the access token when it expires, avoiding manual re-auth.
3. **Task enrichment**: `get_all_tasks()` adds `_project_name` to each task dict for display convenience. This is a client-side field, not from the API.
4. **Completed tasks hidden by default**: `cmd_tasks` and `cmd_claude_tasks` filter out completed tasks (`status != 0`) unless `--all` is passed.
5. **Checklist item IDs**: Generated as 24-character hex strings via `uuid.uuid4().hex[:24]` to match TickTick's format.

## Claude Cowork Workflow

When running the ticktick CLI inside Claude Code, follow this workflow to pick up and work on tasks:

1. **Fetch open tasks** — Run `ticktick claude-tasks --json` to list all open tasks tagged `claude`. Use the JSON output so you can parse task IDs, project IDs, titles, descriptions, and checklist items programmatically.

2. **Present tasks to the user** — Display the task list in a readable format and ask the user which task they want to work on. If there is only one task, confirm it with the user before proceeding.

3. **Research the selected task** — Read the task's title, description (`content` field), and any checklist items to understand the requirements. If the task references files, code, or concepts in the current repository, explore the codebase to build context. Ask the user clarifying questions if the task is ambiguous.

4. **Propose a plan** — Summarize what you found and outline the steps you would take to complete the task. Ask the user if they want to proceed.

5. **Execute the work** — Carry out the plan (write code, edit files, run commands, etc.). Use `ticktick append-description` to log progress notes back to the task if appropriate, and `ticktick add-checklist` to break the task into trackable sub-steps.

6. **Confirm completion** — When the work is done, present the results to the user and ask if they are satisfied. If so, run `ticktick complete-task <project_id> <task_id>` to mark the task as done in TickTick.

### Example session

```
> ticktick claude-tasks --json

Found 2 task(s) tagged 'claude':

  [open] Refactor auth module to support multiple providers  (tags: claude)  [Backend]
  [open] Write usage examples for README                      (tags: claude)  [Docs]

Which task would you like to work on?
```

After the user picks a task, research it, propose a plan, execute, and offer to mark it complete.

## Sensitive Files — Do Not Commit

- `.env` — Contains OAuth client credentials
- `.ticktick_token.json` — Contains access/refresh tokens
- These are already in `.gitignore`
