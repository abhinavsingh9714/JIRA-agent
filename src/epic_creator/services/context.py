###############################################################################
# 2. Feature Context Retrieval Service                                        #
###############################################################################
from typing import Any, Dict, List
from ..jiraClient import JiraClient

class FeatureContextService:
    """Fetches organisational context (project summary, recent epics)."""

    def __init__(self, jira_client: JiraClient):
        self.jira_client = jira_client

    def get_project_overview(self, project_key: str) -> Dict[str, str]:
        proj = self.jira_client.get(f"/rest/api/2/project/{project_key}")
        return {
            "name": proj.get("name"),
            "description": proj.get("description", ""),
            "lead": proj.get("lead", {}).get("displayName", "")
        }

    def get_recent_epics(self, project_key: str, limit: int = 3) -> List[Dict[str, Any]]:
        jql = f"project = \"{project_key}\" AND issuetype = Epic ORDER BY created DESC"
        search = self.jira_client.get("/rest/api/2/search", jql=jql, maxResults=limit, fields="summary,description,labels")
        return search.get("issues", [])