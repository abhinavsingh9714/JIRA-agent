import json
import streamlit as st
from pathlib import Path

from ..services.jira_client    import JiraClient
from ..services.field_meta    import FieldMetadataService
from ..planning.models        import Plan
from ..planning.orchestrator  import TicketOrchestrator
from ..planning.planner             import AIPlanner
from ..planning.models import Initiative, Epic, Story, Task

def render_text(label, value, key):
    return st.text_input(label, value=value, key=key)

def render_textarea(label, value, key):
    return st.text_area(label, value=value, key=key, height=80)

def edit_task(t: Task, prefix: str):
    t.summary     = render_text("Task summary",     t.summary,     f"{prefix}.summary")
    t.description = render_textarea("Description", t.description, f"{prefix}.desc")
    t.priority    = render_text("Priority",        t.priority,    f"{prefix}.prio")

def edit_story(s: Story, prefix: str):
    s.summary     = render_text("Story summary",   s.summary,     f"{prefix}.summary")
    s.description = render_textarea("Description", s.description, f"{prefix}.desc")
    s.story_points= st.number_input("Story points", value=s.story_points or 0,
                                    key=f"{prefix}.sp", step=1)
    s.priority    = render_text("Priority",        s.priority,    f"{prefix}.prio")
    for i, t in enumerate(s.tasks):
        with st.expander(f"Task {t.local_id}"):
            edit_task(t, f"{prefix}.task{i}")

def edit_epic(e: Epic, prefix: str):
    e.summary     = render_text("Epic summary",    e.summary,     f"{prefix}.summary")
    e.description = render_textarea("Description", e.description, f"{prefix}.desc")
    e.priority    = render_text("Priority",        e.priority,    f"{prefix}.prio")
    for i, s in enumerate(e.stories):
        with st.expander(f"Story {s.local_id}"):
            edit_story(s, f"{prefix}.story{i}")

def edit_initiative(ini: Initiative, idx: int):
    prefix = f"ini{idx}"
    ini.summary     = render_text("Initiative summary", ini.summary, f"{prefix}.summary")
    ini.description = render_textarea("Description",    ini.description, f"{prefix}.desc")
    for i, e in enumerate(ini.epics):
        with st.expander(f"Epic {e.local_id}"):
            edit_epic(e, f"{prefix}.epic{i}")

# ───────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────
def connect_to_jira():
    base  = st.session_state.get("base_url")
    email = st.session_state.get("email")
    token = st.session_state.get("api_token")
    if not all([base, email, token]):
        st.error("Fill all credential fields.")
        return None
    try:
        jira = JiraClient(base_url=base, email=email, api_token=token)
        # lightweight ping: fetch own user
        _ = jira.get("/rest/api/3/myself")
        st.session_state.jira = jira
        st.session_state.connected = True
        st.success("🗸 Connected to Jira!")
        return jira
    except Exception as e:
        st.error(f"Connection failed → {e}")
        st.session_state.connected = False
        return None


def get_jira() -> JiraClient | None:
    return st.session_state.get("jira")


# ───────────────────────────────────────────────────────────
# Sidebar: step 1 – credentials
# ───────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Step 1 · Jira Credentials")
    st.text_input("Base URL",   key="base_url", placeholder="https://your-domain.atlassian.net")
    st.text_input("Email",      key="email")
    st.text_input("API Token",  key="api_token", type="password")

    if st.button("Connect"):
        connect_to_jira()


# ───────────────────────────────────────────────────────────
# Main column
# ───────────────────────────────────────────────────────────
st.title("AI-powered Jira Backlog Builder")

# ---------------------------------
# If not connected yet → show hint
# ---------------------------------
if not st.session_state.get("connected"):
    st.info("Enter your Jira credentials in the sidebar and click **Connect**.")
    st.stop()

# ---------------------------------
# Step 2 · Prompt + project key
# ---------------------------------
st.header("Step 2 · Generate Plan")

project_key = st.text_input("Target Project Key")
example_key = st.text_input("Example Project (for style-guide, optional)")
prompt      = st.text_area("Feature Prompt", height=200)

if st.button("Generate Plan"):
    if not (project_key and prompt):
        st.error("Project key and prompt are required.")
    else:
        try:
            planner = AIPlanner(project_key=project_key, example_project_key=example_key or None)
            st.info("Generating plan via LLM…")
            plan_obj: Plan = planner.plan(prompt)
            st.session_state.generated_plan = plan_obj
            st.session_state.plan_generated = True
            st.success("Plan generated")
        except Exception as e:
            st.error(f"Failed to generate plan: {e}")

# ---------------------------------
# Step 3 · Review & edit
# ---------------------------------
if st.session_state.get("plan_generated"):
    st.header("Step 3 · Review & Edit Plan")
    plan_obj: Plan = st.session_state.generated_plan # current plan

    # draw hierarchical forms
    for idx, ini in enumerate(plan_obj.initiatives):
        with st.expander(f"Initiative {ini.local_id}", expanded=False):
            edit_initiative(ini, idx)

    # save button
    if st.button("Save all edits"):
        try:
            plan_obj.validate_self()                 # pydantic guard
            st.session_state.generated_plan = plan_obj
            st.success("Plan validated & saved")
            st.session_state.plan_validated = True   # flag stays True
        except Exception as e:
            st.error(f"Validation error: {e}")

# ---------------------------------
# Step 4 · Push tickets
# ---------------------------------
if st.session_state.get("plan_validated"):
    st.header("Step 4 · Create Jira Tickets")
    if st.button("Push to Jira"):
        jira = get_jira()
        field_service = FieldMetadataService(jira)
        account_id    = field_service.get_user_id()
        orchestrator  = TicketOrchestrator(jira)
        epic_allowed  = field_service.get_allowed_field_map(project_key, "Epic")

        progress_bar  = st.progress(0)
        status_text   = st.empty()

        def progress(msg, pct):
            status_text.write(msg)
            progress_bar.progress(int(pct * 100))

        try:
            id_map = orchestrator.create_plan(
                st.session_state.generated_plan,
                account_id=account_id,
                project_key=project_key,
                progress_cb=progress,
            )
            progress_bar.progress(100)
            st.success("All tickets created!")
            st.json(id_map)
        except Exception as e:
            st.error(f"Ticket creation failed: {e}")