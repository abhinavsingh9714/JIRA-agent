###############################################################################
# 5. Orchestrator / Facade                                                    #
###############################################################################
from epic_creator.jiraClient import JiraClient
from epic_creator.services.field_meta    import FieldMetadataService
from epic_creator.services.context       import FeatureContextService
from epic_creator.services.llm           import LLMService
from epic_creator.services.epic_handler  import EpicCreationHandler

def create_epic_from_prompt(project_key: str, manager_prompt: str) -> str:
    """End‑to‑end utility: returns new epic key (e.g., PROJ‑123)."""
    jira = JiraClient()
    
    # 1. Metadata
    field_service = FieldMetadataService(jira)
    account_id = field_service.get_user_id()
    # print(account_id)
    fields = field_service.get_epic_fields(project_key)
    # llm_fields = {k: v for k, v in fields.items()
    #               if k not in {"Project", "Work type", "Reporter"}}
    # print(fields)

    # 2. Context
    context_service = FeatureContextService(jira)
    project_info = context_service.get_project_overview(project_key)
    recent_epics = context_service.get_recent_epics(project_key)
    # print(project_info)
    # print(recent_epics)

    # 3. LLM
    llm_service   = LLMService()
    prompt_text   = llm_service.build_prompt(
        fields, project_info, recent_epics, manager_prompt
    )
    # print(prompt_text)
    epic_obj      = llm_service.generate_epic(prompt_text)
    # print(epic_obj)

    # 4. Map + create
    handler = EpicCreationHandler(jira, field_service)
    mapped_fields = handler.map_fields(epic_obj, fields, account_id)
    print(mapped_fields)
    # epic_key = handler.create_epic(project_key, mapped_fields)
    # return epic_key
    return mapped_fields

if __name__ == "__main__":
    # Example usage
    project_key = "JIRADEMO"
    manager_prompt = "Build a UI-based tool for users to upload an image and text, and instantly generate temporally consistent video results."
    create_epic_from_prompt(project_key, manager_prompt)
    # print(f"Created epic: {epic_key}")