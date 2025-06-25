###############################################################################
# 3. Prompt Engineering & LLM Service                                         #
###############################################################################
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from pydantic import BaseModel, Field
from typing import List, Dict, Any


class EpicOutput(BaseModel):
    summary: str = Field(description="Epic summary/title")
    description: str = Field(description="Detailed epic description")
    priority: str = Field(description="Epic priority level, e.g. High/Medium/Low")
    labels: List[str] = Field(description="List of labels")


parser = JsonOutputParser(pydantic_object=EpicOutput)


class LLMService:
    """Generates structured Epic JSON using contextual prompt."""
    SYSTEM_PROMPT = (
        "You are a senior project manager creating well-structured JIRA Epics. "
        "Return *only* JSON that matches the schema."
    )

    def __init__(self, model_name: str = "gpt-4o-mini", temperature: float = 0.3):
        self.llm = ChatOpenAI(model_name=model_name, temperature=temperature)

        # Build a reusable chained runnable:  Prompt -> Model -> JSON-Parser
        self.chain = (
            ChatPromptTemplate.from_messages(
                [
                    ("system", self.SYSTEM_PROMPT),
                    # user content is injected later via input variable {prompt}
                    ("user", "{prompt}"),
                ]
            )
            | self.llm
            | parser            # automatically parses .content into EpicOutput
        )

    # --------------------------------------------------------------------- #
    # Prompt text helper                                                    #
    # --------------------------------------------------------------------- #
    def build_prompt(
        self,
        field_requirements: Dict[str, Any],
        project_info: Dict[str, str],
        examples: List[Dict[str, Any]],
        user_requirements: str,
    ) -> str:
        examples_fmt = "\n".join(f"- {e['fields']}" for e in examples) or "(none)"
        field_fmt = "\n".join(
            f"* {n} (required={m['required']})" for n, m in field_requirements.items()
        )
        return (
            f"Project: {project_info['name']}\n"
            f"Description: {project_info['description']}\n\n"
            f"Field requirements:\n{field_fmt}\n\n"
            f"Recent epic examples:\n{examples_fmt}\n\n"
            f"New epic requirement: {user_requirements}\n\n"
            f"Return a JSON object with keys in Field requirements"
        )

    # --------------------------------------------------------------------- #
    # Single entry-point the rest of your code calls                         #
    # --------------------------------------------------------------------- #
    def generate_epic(self, prompt: str) -> EpicOutput:
        return self.chain.invoke({"prompt": prompt})  # returns EpicOutput