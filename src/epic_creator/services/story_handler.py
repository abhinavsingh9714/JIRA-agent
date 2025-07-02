###############################################################################
# 5. Dynamic JIRA Story Creation Handler                                      #
###############################################################################
from typing import Dict, Any
from .jiraClient import JiraClient


class StoryCreationHandler:
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
        story_json: Dict[str, Any],
        allowed_map: Dict[str, Any],    # canonical key → {id, required, …}
        account_id: str,
        project_key: str,
        parent_epic_key: str,
    ) -> Dict[str, Any]:
        """
        Transform LLM Story JSON into a Jira-ready field dict.
        """
        canon = self._canon
        llm = {canon(k): v for k, v in story_json.items()}
        mapped: Dict[str, Any] = {}

        # 1️⃣ Copy LLM keys that Jira allows
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

        # 2️⃣ Set Epic Link / parent relation
        epic_link_key = canon("Epic Link")
        if epic_link_key in allowed_map:
            mapped[allowed_map[epic_link_key]["id"]] = parent_epic_key
        else:
            # modern cloud fallback where "parent" is used
            mapped["parent"] = {"key": parent_epic_key}

        # 3️⃣ Auto-fill Story Points if required & missing
        sp_key = canon("Story Points")
        if (
            sp_key in allowed_map
            and allowed_map[sp_key]["required"]
            and allowed_map[sp_key]["id"] not in mapped
        ):
            mapped[allowed_map[sp_key]["id"]] = llm.get("story_points", 1)

        # 4️⃣ Always-allowed system fields
        mapped["reporter"] = {"id": account_id}
        mapped["project"]  = {"key": project_key}
        # mapped["issuetype"] = "story"

        # 5️⃣ Validate required fields
        missing = [
            human for human, meta in allowed_map.items()
            if meta["required"] and meta["id"] not in mapped
        ]
        if missing and missing != ["issue_type"]:
            raise ValueError(f"Missing required fields: {missing}")

        return mapped

    # ----------------------------------------------------------- #
    # REST call                                                   #
    # ----------------------------------------------------------- #
    def create_story(
        self,
        project_key: str,
        story_payload: Dict[str, Any],
    ) -> str:
        data = {
            "fields": {
                **story_payload,
                "project":   {"key": project_key},
                "issuetype": {"name": "Story"},
            }
        }
        result = self.jira_client.post("/rest/api/3/issue", payload=data)
        return result.get("key")