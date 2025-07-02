"""
Epic‑Creator • planning.llm
---------------------------------
Generate a structured *Plan* object (Initiatives ▸ Epics ▸ Stories ▸ Tasks)
from a free‑form feature prompt and an optional Style Guide / Fields Guide.

Key differences vs. the previous version:
1.  Uses **ChatOpenAI.with_structured_output(Plan)** — the Plan JSON schema is
    sent as a function‑call tool outside the prompt, so **zero schema tokens**
    hit the context window.
2.  No explicit JsonOutputParser / OutputFixingParser boilerplate — parsing &
    validation are handled automatically by LangChain.
3.  Keeps the prompt concise and focused on high‑value context only.
"""
from __future__ import annotations

from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from epic_creator.planning.models import Plan

# ──────────────────────────────────────────────────────────────────────────────
# 1.  LLM wrapper
# ──────────────────────────────────────────────────────────────────────────────
class PlanningLLMService:
    """Plan generation helper — single public method:

    ```python
    create_plan(project_key: str, user_prompt: str,
                style_guide: str | None = None,
                fields_guide: str | None = None) -> Plan
    ```
    """

    SYSTEM_PROMPT = (
        "You are a senior agile project planner.\n"
        "Generate a product backlog *JSON* that conforms to the provided Plan\n"
        "schema (initiatives → epics → stories → tasks).\n"
        "Include **every** required field such as summary, description,\n"
        "priority, acceptance_criteria, parent_* links, etc.\n"
        "Return *only* JSON; no prose."
    )

    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        temperature: float = 0.2,
    ) -> None:
        # Base LLM
        base_llm = ChatOpenAI(model_name=model_name, temperature=temperature)
        # Wrap with structured‑output: ensures any .invoke() returns Plan
        self.structured_llm = base_llm.with_structured_output(Plan)

        # Prompt chain: template → structured LLM → Plan object
        self.chain = (
            ChatPromptTemplate.from_messages(
                [
                    ("system", self.SYSTEM_PROMPT),
                    ("user", "{full_prompt}"),
                ]
            )
            | self.structured_llm
        )

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #
    def create_plan(
        self,
        project_key: str,
        user_prompt: str,
        style_guide: Optional[str] = None,
        fields_guide: Optional[str] = None,
    ) -> Plan:
        """Generate and validate a **Plan** for the given feature request."""

        # — Build the user prompt context —
        full_prompt = (
            f"=== PROJECT KEY ===\n{project_key}\n\n"
            f"=== FEATURE PROMPT ===\n{user_prompt}\n\n"
            f"=== STYLE GUIDE ===\n{style_guide or 'No prior style guide available.'}\n\n"
            f"=== FIELDS GUIDE ===\n{fields_guide or 'No field constraints provided.'}"
        )
        print(full_prompt)
        # Invoke chain → returns validated Plan instance
        plan: Plan = self.chain.invoke({"full_prompt": full_prompt})
        return plan