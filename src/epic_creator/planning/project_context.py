"""
epic_creator.planning.project_context
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Light-weight metadata snapshot of *all* Epics + Stories in a Jira project.
The payload is intentionally small (only a few core fields) so we can feed
it to ProjectStyleAnalyzer and, ultimately, to PlanningLLMService.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Tuple

from epic_creator.services.jiraClient import JiraClient


__all__ = ["ProjectSnapshotService"]


class ProjectSnapshotService:
    """
    Pulls issue metadata via `/rest/api/3/search` with JQL pagination.

    Parameters
    ----------
    jira_client : JiraClient
        Already-authenticated wrapper (token + retries).
    page_size : int, default 100
        Jira Cloud caps `maxResults` at 100.  Keep as constant.
    """

    def __init__(self, jira_client: JiraClient, page_size: int = 100) -> None:
        self.jira = jira_client
        self.page_size = min(page_size, 100)

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #
    def fetch_issue_metadata(
        self,
        project_key: str,
        issuetypes: Sequence[str] = ("Epic", "Story"),
        max_issues: Optional[int] = None,
        extra_fields: Optional[Sequence[str]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Return *all* matching issues’ key + summary + description (+ labels).

        Parameters
        ----------
        project_key : str
            Jira project key (e.g. ``"DEMO"``).
        issuetypes : Sequence[str], default ``("Epic", "Story")``
            Filter for Epic, Story or any other mix you need.
        max_issues : int or None
            Hard cap.  ``None`` → fetch everything available.
        extra_fields : Sequence[str] or None
            Additional Jira field names to include (e.g. ``["components"]``).

        Notes
        -----
        • We *don’t* pull comments, worklogs, changelogs – only summary data.  
        • If the project has *thousands* of tickets, expect a few requests but
          an overall payload < 500 KB – fine for in-memory use.
        """
        jql_issuetype = ", ".join(f'"{t}"' for t in issuetypes)
        jql = f"project = {project_key} AND issuetype IN ({jql_issuetype}) ORDER BY created ASC"

        fields: Tuple[str, ...] = (
            "summary",
            "issuetype",
            "description",
            "labels",
        )
        if extra_fields:
            fields += tuple(extra_fields)

        collected: List[Dict[str, Any]] = []
        start_at = 0
        keep_fetching = True

        while keep_fetching:
            params = {
                "jql": jql,
                "fields": list(fields),
                "maxResults": self.page_size,
                "startAt": start_at,
            }
            page = self.jira.get("/rest/api/3/search", **params)
            issues = page.get("issues", [])
            collected.extend(self._to_light_dict(i) for i in issues)

            start_at += self.page_size
            keep_fetching = (
                page.get("total", 0) > start_at
                and (max_issues is None or len(collected) < max_issues)
            )

        # Apply final max-issues cap, if any
        if max_issues is not None:
            collected = collected[:max_issues]

        return collected

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    @staticmethod
    def _to_light_dict(issue: Dict[str, Any]) -> Dict[str, Any]:
        """Minimal normalisation."""
        f = issue.get("fields", {})
        return {
            "key": issue.get("key"),
            "summary": f.get("summary", ""),
            "description": f.get("description", "") or "",
            "issuetype": f.get("issuetype", {}).get("name", ""),
            "labels": f.get("labels", []),
        }