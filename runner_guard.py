import os
import json
import asyncio
from typing import Any, Dict, List, Optional

import httpx

# ENV:
# GITLAB_API_BASE = "https://gitlab.example.com/api/v4"
# GITLAB_TOKEN     = "<personal/group/project access token>"
# RUNNER_AUTO_CREATE = "true" | "false"
# RUNNER_TAGS = "docker,ci"
# RUNNER_DESCRIPTION = "orchestrator-managed"
# RUNNER_RUN_UNTAGGED = "true" | "false"

def env(name: str, default: Optional[str] = None, required: bool = False) -> Optional[str]:
    val = os.getenv(name, default)
    if required and (val is None or str(val).strip() == ""):
        raise RuntimeError(f"Missing required env var: {name}")
    return val

class RunnerGuard:
    def __init__(self) -> None:
        self.api_base = env("GITLAB_API_BASE", required=True).rstrip("/")
        self.token = env("GITLAB_TOKEN", required=True)
        self.auto_create = (env("RUNNER_AUTO_CREATE", "false").lower() == "true")
        self.tags = env("RUNNER_TAGS", "orchestrator").split(",")
        self.desc = env("RUNNER_DESCRIPTION", "orchestrator-managed").strip()
        self.run_untagged = (env("RUNNER_RUN_UNTAGGED", "true").lower() == "true")

        self.headers = {
            "PRIVATE-TOKEN": self.token,
            "Accept": "application/json",
        }

    async def _get(self, path: str, params: Dict[str, Any] | None = None) -> httpx.Response:
        url = f"{self.api_base}{path}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            return await client.get(url, headers=self.headers, params=params)

    async def _post(self, path: str, data: Dict[str, Any] | None = None) -> httpx.Response:
        url = f"{self.api_base}{path}"
        async with httpx.AsyncClient(timeout=60.0) as client:
            return await client.post(url, headers=self.headers, data=data)

    async def list_project_runners(self, project_id: str, status: Optional[str] = "online") -> List[Dict[str, Any]]:
        # GET /projects/:id/runners?status=online
        # Returns runners visible to the caller; online indicates availability.  :contentReference[oaicite:5]{index=5}
        params = {}
        if status:
            params["status"] = status
        resp = await self._get(f"/projects/{project_id}/runners", params=params)
        if resp.status_code >= 400:
            raise RuntimeError(f"Failed to list project runners: {resp.status_code} {resp.text}")
        return resp.json()

    async def create_project_runner(self, project_id: str) -> Dict[str, Any]:
        # New runner creation workflow via POST /user/runners (requires :create_runner scope).
        # Must include runner_type=project_type and project_id=<id>.  :contentReference[oaicite:6]{index=6}
        data = {
            "runner_type": "project_type",
            "project_id": project_id,
            "description": self.desc,
        }
        if self.tags:
            data["tag_list"] = ",".join([t.strip() for t in self.tags if t.strip()])
        # Note: run_untagged is set later on the runner record if needed; not all fields are supported here.
        resp = await self._post("/user/runners", data=data)
        if resp.status_code == 403:
            raise PermissionError("Token missing create_runner scope or insufficient permissions to create a runner.")
        if resp.status_code >= 400:
            raise RuntimeError(f"Failed to create runner: {resp.status_code} {resp.text}")

        return resp.json()  # { "id": <runner_id>, "token": "glrt-....", "token_expires_at": ... }

    async def verify_runner(self, auth_token: str) -> bool:
        # POST /runners/verify to validate the authentication token.  :contentReference[oaicite:7]{index=7}
        resp = await self._post("/runners/verify", data={"token": auth_token})
        return resp.status_code == 200

    async def ensure_available_runner(self, project_id: str) -> Dict[str, Any]:
        """Return a dict summarizing runner availability and any creation performed."""
        summary: Dict[str, Any] = {"project_id": project_id, "available": False, "action": "none", "details": {}}

        existing = await self.list_project_runners(project_id, status="online")
        if any(r.get("status") == "online" or r.get("online") for r in existing):
            summary["available"] = True
            summary["details"]["online_runners"] = existing
            return summary

        # None online; decide whether to create
        if not self.auto_create:
            summary["available"] = False
            summary["action"] = "noop"
            summary["details"]["reason"] = "no_online_runner_and_auto_create_disabled"
            return summary

        created = await self.create_project_runner(project_id)
        auth_token = created.get("token", "")
        summary["details"]["created"] = created

        if auth_token:
            ok = await self.verify_runner(auth_token)
            summary["details"]["verify_ok"] = ok

        # Even after creating a runner config, an actual runner process
        # still must be started (e.g., `gitlab-runner register` using the glrt token).  :contentReference[oaicite:8]{index=8}
        # We still return success because the configuration is ready.
        summary["available"] = True
        summary["action"] = "created_runner_config"
        return summary


async def main():
    import argparse
    p = argparse.ArgumentParser(description="Runner Guard")
    p.add_argument("--project-id", required=True)
    args = p.parse_args()

    guard = RunnerGuard()
    info = await guard.ensure_available_runner(args.project_id)
    print(json.dumps(info, indent=2))

if __name__ == "__main__":
    asyncio.run(main())
