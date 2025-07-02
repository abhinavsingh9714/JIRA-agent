from epic_creator.planning.models import Plan
from epic_creator.services.jiraClient import JiraClient
from epic_creator.services.llm import PlanningLLMService
from epic_creator.planning.orchestrator import TicketOrchestrator

jira = JiraClient()
planner = PlanningLLMService(jira)
plan = planner.create_plan("JIRADEMO", "I want to create an app that generates marketing campaigns gifs from input image and text prompt")
print(plan)
# plan = Plan.model_validate(plan)
# # print(plan)
# orch = TicketOrchestrator(jira, "JIRADEMO")
# print(orch.create_plan(plan))