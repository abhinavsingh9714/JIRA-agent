###############################################################################
# 1. Field Metadata Retrieval Service                                         #
###############################################################################
from typing import Any, Dict, List
from ..jiraClient import JiraClient
class FieldMetadataService:
    def __init__(self, jira_client: JiraClient):
        self.jira_client = jira_client

    def _index_by_id(self, fields: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        return {f["id"]: f for f in fields}

    def _process_field_metadata(self, all_fields: List[Dict[str, Any]], project_fields: List[Dict[str, Any]] | Dict[str, Any]) -> Dict[str, Any]:
        """Return mapping field_name → {id, required, allowedValues?} for EPIC creation."""
        id_index = self._index_by_id(all_fields)
        epic_fields: Dict[str, Any] = {}
        # ``project_fields`` structure: list[{'id':issuetypeId,'fields':{fieldId:{required,..}}}] ; keep first (EPIC) entry
        for issuetype in project_fields:
            # print(issuetype)
            if issuetype.get("name", "").lower() == "epic":
                for fid, meta in issuetype["fields"].items():
                    full = id_index.get(fid, {})
                    epic_fields[full.get("name", fid)] = {
                        "id": fid,
                        "required": meta.get("required", False),
                        "schema": full.get("schema", {}),
                        "allowed": meta.get("allowedValues", full.get("allowedValues"))
                    }
                break
        return epic_fields

    def _process_field_metadata1(
        self,
        all_fields: List[Dict[str, Any]],
        project_fields: List[Dict[str, Any]] | Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Build `{field_display_name: {id, required, schema, allowed}}`
        for the Epic issue-type, coping with both v2 and v3 Jira payloads.
        """
        # Fast lookup id  → system metadata (names, schema, …)
        id_index = {f["id"]: f for f in all_fields}

        # Normalise project_fields to a list
        if isinstance(project_fields, dict):
            project_fields = [project_fields]

        epic_fields: Dict[str, Any] = {}

        for issuetype in project_fields:
            # v2 payloads carry "name"; v3 single-ID payloads don’t.
            if issuetype.get("name", "").lower() not in ("", "epic"):
                continue                                  # skip Stories, Bugs, …

            raw_fields = issuetype.get("fields")
            if raw_fields is None:                       # safety-net
                continue

            # ── ① v2: dict  {fieldId: meta} ───────────────────────────────────
            if isinstance(raw_fields, dict):
                field_items = raw_fields.items()

            # ── ② v3: list [ {..., "fieldId":"summary", …}, … ] ──────────────
            else:  # list/tuple
                field_items = ((f["fieldId"], f) for f in raw_fields)

            for fid, meta in field_items:
                # Fallbacks: prefer data from /field, else from meta blob
                full = id_index.get(fid, {})
                display_name = meta.get("name") or full.get("name") or fid

                epic_fields[display_name] = {
                    "id": fid,
                    "required": meta.get("required", False),
                    "schema":  meta.get("schema", full.get("schema", {})),
                    "allowed": meta.get("allowedValues",
                                        full.get("allowedValues")),
                }

            # if this entry was explicitly "Epic", no need to keep scanning
            if issuetype.get("name", "").lower() == "epic":
                break

        return epic_fields

    def get_epic_fields(self, project_key: str) -> Dict[str, Any]:
        # discover Epic issueTypeId
        types = self.jira_client.get(
            f"/rest/api/3/issue/createmeta/{project_key}/issuetypes"
        )["issueTypes"]
        epic_id = next(t["id"] for t in types if t["name"].lower() == "epic")

        # fetch field metadata for that ID (fields included by default)
        epic_meta = self.jira_client.get(
            f"/rest/api/3/issue/createmeta/{project_key}/issuetypes/{epic_id}"
        )
        
        # global field catalogue for nice names / schemas
        all_fields = self.jira_client.get("/rest/api/3/field")

        return self._process_field_metadata1(all_fields, [epic_meta])
    
    def get_user_id(self):
        # discover Epic issueTypeId
        accountId = self.jira_client.get(
            f"/rest/api/3/myself"
        )["accountId"]

        return accountId
