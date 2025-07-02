###############################################################################
# 6. Dynamic JIRA Task / Sub-task Creation Handler                            #
###############################################################################
from typing import Dict, Any
from .jiraClient import JiraClient


class TaskCreationHandler:
    """
    Create a Sub-task under its parent Story.  Falls back to plain "Task"
    when the project has no Sub-task issue-type enabled.
    """

    def __init__(self, jira_client: JiraClient):
        self.jira_client = jira_client

    # ----------------------------------------------------------- #
    @staticmethod
    def _canon(name: str) -> str:
        return name.lower().replace(" ", "")

    def _as_adf(self, text: str) -> dict:
        return {
            "type": "doc",
            "version": 1,
            "content": [
                {"type": "paragraph",
                "content": [{"type": "text", "text": text}]}
            ],
        }
    # ----------------------------------------------------------- #
    # Field-mapping helper                                        #
    # ----------------------------------------------------------- #
    def map_fields(
        self,
        task_json: Dict[str, Any],
        allowed_map: Dict[str, Any],     # canonical key → {id, required, …}
        account_id: str,
        project_key: str,
        parent_story_key: str,
    ) -> Dict[str, Any]:
        """
        Transform LLM Task JSON into a Jira-ready field dict.
        """
        canon = self._canon
        llm = {canon(k): v for k, v in task_json.items()}
        mapped: Dict[str, Any] = {}

        # 1️⃣ Copy only Jira-allowed fields
        for human_key, meta in allowed_map.items():
            ck = canon(human_key)
            if ck in llm:
                if ck == "priority":
                    mapped[meta["id"]] = {"name": llm[ck]}
                else:
                    if ck == "description":
                        mapped[meta["id"]] = self._as_adf(llm[ck])
                    else:
                        mapped[meta["id"]] = llm[ck]

        # 2️⃣ Add parent link (always needed for Sub-tasks)
        mapped["parent"] = {"key": parent_story_key}

        # 3️⃣ Always-allowed system fields
        mapped["reporter"] = {"id": account_id}
        mapped["project"]  = {"key": project_key}
        # mapped["issuetype"] = {"name": "Task"}

        # 4️⃣ Validate required fields
        missing = [
            human for human, meta in allowed_map.items()
            if meta.get("required") and meta["id"] not in mapped
        ]
        if missing and missing != ["issue_type"]:
            raise ValueError(f"Missing required fields: {missing}")

        return mapped

    # ----------------------------------------------------------- #
    # REST call                                                   #
    # ----------------------------------------------------------- #
    def create_task(
        self,
        project_key: str,
        task_payload: Dict[str, Any],
        issue_type_name: str = "subtask",   # auto fallback handled upstream
    ) -> str:
        """
        issue_type_name can be "Sub-task" or "Task" depending on project config.
        """
        data = {
            "fields": {
                **task_payload,
                "project":   {"key": project_key},
                "issuetype": {"name": issue_type_name},
            }
        }
        result = self.jira_client.post("/rest/api/3/issue", payload=data)
        return result.get("key")