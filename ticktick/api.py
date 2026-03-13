"""TickTick Open API client."""

import uuid
from pathlib import Path

import requests

from ticktick.auth import load_token, save_token, refresh_access_token, DEFAULT_TOKEN_PATH

BASE_URL = "https://api.ticktick.com/open/v1"

PRIORITY_LABELS = {0: "none", 1: "low", 3: "medium", 5: "high"}


class TickTickClient:
    """Thin wrapper around the TickTick Open API v1."""

    def __init__(self, client_id: str = None, client_secret: str = None,
                 token_path: Path = DEFAULT_TOKEN_PATH):
        self.client_id = client_id
        self.client_secret = client_secret
        self.token_path = token_path
        self._token_data = load_token(token_path)
        if not self._token_data:
            raise RuntimeError(
                "No saved token found. Run `ticktick auth` first."
            )

    @property
    def _access_token(self) -> str:
        return self._token_data["access_token"]

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self._access_token}"}

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = f"{BASE_URL}{path}"
        resp = requests.request(method, url, headers=self._headers(), **kwargs)

        # Attempt token refresh on 401
        if resp.status_code == 401 and self.client_id and self.client_secret:
            refresh_token = self._token_data.get("refresh_token")
            if refresh_token:
                self._token_data = refresh_access_token(
                    self.client_id, self.client_secret, refresh_token
                )
                save_token(self._token_data, self.token_path)
                resp = requests.request(
                    method, url, headers=self._headers(), **kwargs
                )

        resp.raise_for_status()
        return resp

    # ------------------------------------------------------------------
    # Projects
    # ------------------------------------------------------------------

    def get_projects(self) -> list[dict]:
        return self._request("GET", "/project").json()

    def get_project_data(self, project_id: str) -> dict:
        return self._request("GET", f"/project/{project_id}/data").json()

    # ------------------------------------------------------------------
    # Tasks
    # ------------------------------------------------------------------

    def get_all_tasks(self) -> list[dict]:
        """Fetch every task across all projects."""
        projects = self.get_projects()
        tasks = []
        for project in projects:
            data = self.get_project_data(project["id"])
            project_tasks = data.get("tasks", [])
            # Attach project name for convenience
            for task in project_tasks:
                task["_project_name"] = project.get("name", "Unknown")
            tasks.extend(project_tasks)
        return tasks

    def get_tasks_by_tag(self, tag: str) -> list[dict]:
        """Fetch all tasks that have a specific tag."""
        all_tasks = self.get_all_tasks()
        return [
            t for t in all_tasks
            if tag.lower() in [tg.lower() for tg in t.get("tags", [])]
        ]

    def get_task(self, project_id: str, task_id: str) -> dict:
        """Get a single task via its project data."""
        data = self.get_project_data(project_id)
        for task in data.get("tasks", []):
            if task["id"] == task_id:
                return task
        raise ValueError(f"Task {task_id} not found in project {project_id}")

    def complete_task(self, project_id: str, task_id: str) -> None:
        self._request("POST", f"/project/{project_id}/task/{task_id}/complete")

    def create_task(self, title: str, project_id: str = None,
                    tags: list[str] = None, **kwargs) -> dict:
        body = {"title": title}
        if project_id:
            body["projectId"] = project_id
        if tags:
            body["tags"] = tags
        body.update(kwargs)
        return self._request("POST", "/task", json=body).json()

    def update_task(self, task_id: str, **fields) -> dict:
        return self._request("POST", f"/task/{task_id}", json=fields).json()

    def append_task_content(self, project_id: str, task_id: str,
                            text: str) -> dict:
        """Append text to the visible description field.

        TickTick displays different fields depending on task type:
        - CHECKLIST tasks show the 'desc' field
        - TEXT tasks show the 'content' field
        """
        task = self.get_task(project_id, task_id)
        field = "desc" if task.get("kind") == "CHECKLIST" else "content"
        existing = task.get(field) or ""
        task[field] = (existing + "\n\n" + text).lstrip("\n")
        # Send the entire task object to preserve all fields
        return self.update_task(task_id, **task)

    def append_content_and_add_checklist(self, project_id: str, task_id: str,
                                          text: str, titles: list[str]) -> dict:
        """Append text to description and add checklist items in a single API call.

        Use this instead of calling append_task_content and add_checklist_items
        separately, as sequential calls can trigger a stale-read race condition
        where the second GET returns data that doesn't yet reflect the first write.
        """
        task = self.get_task(project_id, task_id)

        # Append description
        field = "desc" if task.get("kind") == "CHECKLIST" else "content"
        existing = task.get(field) or ""
        task[field] = (existing + "\n\n" + text).lstrip("\n")

        # Add checklist items
        existing_items = task.get("items") or []
        max_sort = max((item.get("sortOrder", 0) for item in existing_items), default=0)
        for i, title in enumerate(titles):
            existing_items.append({
                "id": uuid.uuid4().hex[:24],
                "title": title,
                "status": 0,
                "sortOrder": max_sort + i + 1,
            })
        task["items"] = existing_items

        return self.update_task(task_id, **task)

    def add_checklist_items(self, project_id: str, task_id: str,
                            titles: list[str]) -> dict:
        """Add checklist (sub-task) items to a task."""
        task = self.get_task(project_id, task_id)
        existing_items = task.get("items") or []

        # Determine the next sortOrder
        max_sort = max((item.get("sortOrder", 0) for item in existing_items), default=0)

        for i, title in enumerate(titles):
            existing_items.append({
                "id": uuid.uuid4().hex[:24],
                "title": title,
                "status": 0,  # 0 = open
                "sortOrder": max_sort + i + 1,
            })

        task["items"] = existing_items
        # Send the entire task object to preserve all fields
        return self.update_task(task_id, **task)

    def delete_task(self, project_id: str, task_id: str) -> None:
        self._request("DELETE", f"/task/{project_id}/{task_id}")
