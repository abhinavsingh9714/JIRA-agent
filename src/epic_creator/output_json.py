# convert_plan_to_json.py
import json, pathlib
from epic_creator.planning.models import Plan, Initiative, Epic, Story, Task

plan_repr = pathlib.Path("/Users/abhinavsingh/projects/JIRA-agent/src/epic_creator/output.txt").read_text()

# Turn repr -> Plan instance
plan_obj = eval(f"Plan({plan_repr})",
                {"Plan": Plan, "Initiative": Initiative,
                 "Epic": Epic, "Story": Story, "Task": Task})

# Dump to compact JSON
pathlib.Path("plan.json").write_text(
    json.dumps(plan_obj.model_dump(), indent=2)
)
print("✅  Saved plan.json")