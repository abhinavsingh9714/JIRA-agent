from typing import List, Dict, Any
from .jira_client import JiraClient

class EpicCreationHandler:
    def __init__(self, jira_client: JiraClient):#, field_service: FieldMetadataService):
        self.jira_client = jira_client

    # ----------------------------------------------------------- #
    # canonical form = lower-case, no spaces (cheap + collision-free)
    # ----------------------------------------------------------- #
    @staticmethod
    def _canonical(name: str) -> str:
        return name.lower().replace(" ", "")

    def map_fields(
        self,
        epic_json: Dict[str, Any],
        allowed_map: Dict[str, Any],   # <-- canonical-key map
        account_id: str,
        project_key: str
    ) -> Dict[str, Any]:

        # print(epic_json)
        canon = self._canonical
        llm_lookup = {canon(k): v for k, v in epic_json.items()}
        mapped: Dict[str, Any] = {}

        for human_key, meta in allowed_map.items():
            canon_key = canon(human_key)
            if canon_key in llm_lookup:
                if canon_key == "priority":
                    mapped[meta["id"]] = {"name": llm_lookup[canon_key]}
                else:
                    mapped[meta["id"]] = llm_lookup[canon_key]

        for human_key, meta in allowed_map.items():
            if meta["required"] and meta["id"] not in mapped:
                canon_key = canon(human_key)
                if canon_key == "epic_name" and "summary" in llm_lookup:
                    mapped[meta["id"]] = llm_lookup["summary"][:255]

        mapped["reporter"] = {"id": account_id}
        mapped["project"]  = {"key": project_key}

        missing = [
            human for human, meta in allowed_map.items()
            if meta["required"] and meta["id"] not in mapped
        ]
        if missing:
            raise ValueError(f"Missing required fields: {missing}")
        
        return mapped


    def create_epic(self, project_key: str, epic_payload: Dict[str, Any]) -> str:
        data = {
            "fields": {
                **epic_payload,
                "project": {"key": project_key},
                "issuetype": {"name": "Epic"}
            }
        }
        result = self.jira_client.post("/rest/api/2/issue", payload=data)
        return result.get("key")