###############################################################################
# 4. Dynamic JIRA Epic Creation Handler                                       #
###############################################################################
from typing import List, Dict, Any
from ..jiraClient import JiraClient
from .field_meta import FieldMetadataService

class EpicCreationHandler:
    def __init__(self, jira_client: JiraClient, field_service: FieldMetadataService):
        self.jira_client = jira_client
        self.field_service = field_service

    # ----------------------------------------------------------- #
    # canonical form = lower-case, no spaces (cheap + collision-free)
    # ----------------------------------------------------------- #
    @staticmethod
    def _canonical(name: str) -> str:
        return name.lower().replace(" ", "")

    def map_fields(
        self,
        epic_json: Dict[str, Any],
        field_requirements: Dict[str, Any],
        account_id
    ) -> Dict[str, Any]:
        """
        Translate LLM keys → Jira field IDs, case-insensitively.
        Raises ValueError if any required field is missing.
        """
        # Build a quick look-up from canonical LLM key → original key/value
        llm_lookup = {
            self._canonical(k): (k, v) for k, v in epic_json.items()
        }

        mapped: Dict[str, Any] = {}

        for human_name, meta in field_requirements.items():
            canon = self._canonical(human_name)

            # If LLM supplied a value (regardless of case/spacing)
            if canon in llm_lookup:
                _, val = llm_lookup[canon]
                mapped[meta["id"]] = val

            # If required but missing → error
            elif meta["required"] and canon not in {
                "summary", "description", "project", "worktype", "reporter"
            }:
                raise ValueError(
                    f"Required field '{human_name}' missing from AI output"
                )

        # Always set core fields from whatever key-form the LLM used
        for base in ("summary", "description"):
            canon = self._canonical(base)
            if canon not in llm_lookup:
                raise ValueError(f"'{base}' missing from AI output")
            _, val = llm_lookup[canon]
            mapped[base] = val

        # Optional helpers
        if "labels" in epic_json or "Labels" in epic_json:
            mapped["labels"] = epic_json.get("labels") or epic_json.get("Labels")
        if "priority" in epic_json or "Priority" in epic_json:
            pri = epic_json.get("priority") or epic_json.get("Priority")
            mapped["priority"] = {"name": pri}
        mapped["reporter"] = {"id": account_id}
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