from __future__ import annotations
from typing import Dict

from .models import Plan
from ..services.epic_handler import EpicCreationHandler
from ..services.story_handler import StoryCreationHandler
from ..services.task_handler import TaskCreationHandler
from ..services.field_meta import FieldMetadataService
from ..services.jira_client import JiraClient


class TicketOrchestrator:
    def __init__(self, jira: JiraClient):
        self.jira = jira
        # self.project_key = project_key
        self.field_service = FieldMetadataService(jira)
        self.epic_handler  = EpicCreationHandler(jira)
        self.story_handler = StoryCreationHandler(jira)
        self.task_handler  = TaskCreationHandler(jira)

        # map local_id → real Jira key
        self._id_map: Dict[str, str] = {}

    # ------------------------------------------------------------------ #
    # Public API                                                         #
    # ------------------------------------------------------------------ #
    def create_plan(self, plan: Plan, account_id, project_key, progress_cb=None) -> Dict[str, str]:
        """
        Walk the Plan depth-first and create every ticket.

        Parameters
        ----------
        plan : Plan
            Validated plan object from PlanningLLMService.
        progress_cb : callable | None
            Optional callback (str msg, float pct) → Streamlit progress bar.

        Returns
        -------
        dict
            local_id → Jira key mapping.
        """
        items = list(plan.walk())
        total = len(items)
        done = 0
        epic_fields = self.field_service.get_allowed_field_map(project_key, 'epic')
        story_allowed = self.field_service.get_allowed_field_map(project_key, "story")
        task_allowed = self.field_service.get_allowed_field_map(project_key, "task")
        for item in items:
            # print(item.__class__.__name__)
            if item.__class__.__name__ == "Initiative":
                # Optionally map initiatives to a Portfolio Epic or a label only.
                self._id_map[item.local_id] = "INIT-PLACEHOLDER"
                continue

            if item.__class__.__name__ == "Epic":
                key = self._create_epic(item, account_id, project_key, epic_fields)
            elif item.__class__.__name__ == "Story":
                # print(item.parent_epic)
                parent_epic = self._id_map[item.parent_epic]
                key = self._create_story(item, parent_epic, account_id, project_key, story_allowed)
            else:  # Task
                parent_story = self._id_map[item.parent_story]
                key = self._create_task(item, parent_story, account_id, project_key, task_allowed)

            self._id_map[item.local_id] = key
            done += 1
            if progress_cb:
                progress_cb(f"Created {key}", done / total)

        return self._id_map

    # ------------------------------------------------------------------ #
    # Internals                                                          #
    # ------------------------------------------------------------------ #
    def _create_epic(self, epic, account_id, project_key, fields):
        # 1. Map friendly AI keys ➜ real Jira field IDs
        mapped_fields = self.epic_handler.map_fields(
            epic_json   = epic.dict(),
            allowed_map = fields,
            account_id  = account_id,
            project_key = project_key
        )
        # 2. Actually create the Epic
        print(f'Mapped Epic: {mapped_fields}')
        return self.epic_handler.create_epic(project_key, mapped_fields)


    def _create_story(self, story, epic_key: str, account_id, project_key, fields):
        mapped = self.story_handler.map_fields(
            story_json   = story.dict(),
            allowed_map  = fields,   # cache once per project
            account_id   = account_id,
            project_key  = project_key,
            parent_epic_key = epic_key,
        )
        print(f'Mapped Story: {mapped}')
        return self.story_handler.create_story(project_key, mapped)

    def _create_task(self, task, story_key: str, account_id, project_key, fields):
        mapped = self.task_handler.map_fields(
            task_json   = task.dict(),
            allowed_map = fields,
            account_id  = account_id,
            project_key = project_key,
            parent_story_key = story_key,
        )
        print(f'Mapped Task: {mapped}')
        return self.task_handler.create_task(project_key, mapped)
