from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field, validator


# ---------- Leaf level -----------------------------------------------------#
class Task(BaseModel):
    local_id: str = Field(..., description="Temporary ID, unique in the Plan")
    summary: str
    description: Optional[str] = ""
    priority: Optional[str] = "Medium"

    parent_story: Optional[str] = Field(
        None, description="local_id of the parent Story (resolved later)"
    )


# ---------- Story level ----------------------------------------------------#
class Story(BaseModel):
    local_id: str
    summary: str
    description: Optional[str] = ""
    story_points: Optional[int] = None
    priority: Optional[str] = "Medium"
    acceptance_criteria: List[str] = Field(default_factory=list)

    tasks: List[Task] = Field(default_factory=list)
    parent_epic: Optional[str] = None


# ---------- Epic level -----------------------------------------------------#
class Epic(BaseModel):
    local_id: str
    summary: str
    description: Optional[str] = ""
    priority: Optional[str] = "High"

    stories: List[Story] = Field(default_factory=list)
    parent_initiative: Optional[str] = None


# ---------- Initiative level ----------------------------------------------#
class Initiative(BaseModel):
    local_id: str
    summary: str
    description: Optional[str] = ""
    epics: List[Epic] = Field(default_factory=list)


# ---------- Plan root ------------------------------------------------------#
class Plan(BaseModel):
    project_key: str = Field(..., description="Target Jira project key (e.g. DEMO)")
    initiatives: List[Initiative]

    # ----- helpers ---------------------------------------------------------#
    @validator("project_key")
    def upper_case_project(cls, v: str) -> str:
        """Normalise project keys so users can type 'demo' or 'DeMo'."""
        return v.upper()

    def validate_self(self) -> None:
        """
        Extra guard you can call after human edits.
        Raises pydantic.ValidationError if something is off.
        """
        _ = self.dict()  # will raise if any field invalid

    def walk(self):
        """Yield items in top-down order (Initiative→Epic→Story→Task)."""
        for initiative in self.initiatives:
            yield initiative
            for epic in initiative.epics:
                yield epic
                for story in epic.stories:
                    yield story
                    for task in story.tasks:
                        yield task

'''
Why this shape?
| Requirement                                            | How it’s handled                                                                                                                                           |
| ------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Parent–child linking before Jira keys exist**        | Every node carries a `local_id`; child nodes store their parent’s `local_id`. `TicketOrchestrator` will resolve these to real keys after each create call. |
| **Round-trip safety** (LLM → human edits → validation) | Pydantic gives us strict type checking; `Plan.validate_self()` is a one-liner the UI can call after every change.                                          |
| **Extensibility** (e.g. add “component”, “fixVersion”) | Just add optional fields with defaults; no external code breaks.                                                                                           |
| **Iteration order needed for top-down creation**       | `Plan.walk()` yields items depth-first so the orchestrator doesn’t worry about nesting.                                                                    |


'''