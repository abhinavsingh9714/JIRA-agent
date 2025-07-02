# """
# Streamlit UI for ai-epic-creator
# --------------------------------
# Run with:
#     streamlit run streamlit_epic.py
# Requires:
#     pip install streamlit python-dotenv
# """

# import json
# import streamlit as st
# from dotenv import load_dotenv

# #  make sure .env is loaded so JiraClient picks up the tokens
# load_dotenv()

# # ---- import the orchestrator from your package ----
# from epic_creator.orchestrator import create_epic_from_prompt


# # ──────────────────────────────────────────────────────────
# # Sidebar – project key & prompt
# # ──────────────────────────────────────────────────────────
# st.sidebar.title("AI Epic Creator")

# project_key = st.sidebar.text_input("Jira Project Key", "JIRADEMO")
# prompt_text = st.sidebar.text_area(
#     "Manager Prompt",
#     "Build a UI-based tool for users to upload an image and text, "
#     "and instantly generate temporally consistent video results.",
#     height=160,
# )

# generate = st.sidebar.button("Generate Epic JSON 🚀")

# # ──────────────────────────────────────────────────────────
# # Main panel
# # ──────────────────────────────────────────────────────────
# st.title("🦾 AI-Assisted Epic JSON")

# if generate:
#     with st.status("Talking to OpenAI …", expanded=False):
#         try:
#             epic_json = create_epic_from_prompt(project_key, prompt_text)
#             # pretty-print the dict (it’s already mapped to Jira field-ids)
#             st.code(json.dumps(epic_json, indent=2), language="json")
#         except Exception as e:
#             st.error(f"❌ Generation failed: {e}")

# else:
#     st.info("Fill in the sidebar and hit *Generate* to see the result.")

"""
streamlit_epic.py
———————————————————————————————————
Streamlit UI for ai-epic-creator
"""

from __future__ import annotations

import datetime, json
from pathlib import Path
from typing import Dict, Any

import streamlit as st
from dotenv import load_dotenv, find_dotenv

# 1️⃣  Load .env so JiraClient gets credentials
load_dotenv(find_dotenv())

# 2️⃣  Import your package
from epic_creator.services.jiraClient          import JiraClient
from epic_creator.services.field_meta import FieldMetadataService
from epic_creator.services.context    import FeatureContextService
from epic_creator.services.llm        import LLMService
from epic_creator.services.epic_handler import EpicCreationHandler


# ─────────────────────────────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────────────────────────────
def canon(name: str) -> str:
    return name.lower().replace(" ", "")


def generate_draft(project_key: str, manager_prompt: str) -> tuple[dict, dict]:
    """Return (draft_json, field_meta) but DOES NOT push to Jira"""
    jira = st.session_state["jira"]

    fm     = FieldMetadataService(jira)
    meta   = fm.get_epic_fields(project_key)

    ctx    = FeatureContextService(jira)
    proj   = ctx.get_project_overview(project_key)
    recent = ctx.get_recent_epics(project_key)

    llm    = LLMService()
    prompt = llm.build_prompt(meta, proj, recent, manager_prompt)
    draft  = llm.generate_epic(prompt)          # dict

    return draft, meta


# ─────────────────────────────────────────────────────────────────────
# Streamlit UI
# ─────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="AI Epic Creator", page_icon="🦾", layout="wide")
st.title("🦾 AI-Assisted Epic Creator")

with st.sidebar:
    st.header("Jira Project & Prompt")
    project_key = st.text_input("Project Key", "JIRADEMO")
    manager_prompt = st.text_area("Manager Prompt", height=150, key="prompt")
    generate_btn = st.button("Generate Draft")

# Session-state setup
if "jira" not in st.session_state:
    st.session_state["jira"] = JiraClient()      # creds via .env

if generate_btn:
    try:
        draft, meta = generate_draft(project_key, manager_prompt)
        st.session_state["draft"] = draft
        st.session_state["meta"]  = meta
        st.success("Draft generated – edit below ⬇️")
    except Exception as e:
        st.error(f"Generation failed: {e}")

# ───────────────────────── form appears after draft is in session ───
if "draft" in st.session_state:
    draft: Dict[str, Any] = st.session_state["draft"]
    meta : Dict[str, Any] = st.session_state["meta"]

    st.subheader("📝 Review & Edit Draft")

    with st.form("edit_form", clear_on_submit=False):
        widgets: Dict[str, Any] = {}

        # existing fields
        for fid, value in draft.items():
            h_name = next((n for n, m in meta.items() if m["id"] == fid), fid)
            schema = meta.get(h_name, {}).get("schema", {})
            allowed = meta.get(h_name, {}).get("allowed")

            if schema.get("type") == "date":
                val = datetime.date.fromisoformat(value) if value else datetime.date.today()
                widgets[fid] = st.date_input(h_name, val)
            elif isinstance(value, list):
                widgets[fid] = st.text_input(h_name, ",".join(value))
            elif allowed:
                opts = [opt.get("value") or opt.get("name") for opt in allowed]
                widgets[fid] = st.selectbox(h_name, opts, index=opts.index(value) if value in opts else 0)
            else:
                widgets[fid] = st.text_area(h_name, value, height=80)

        # any required fields missing? add empty inputs
        for n, m in meta.items():
            if m["required"] and m["id"] not in draft and n not in {"Project", "Reporter", "Work type"}:
                widgets[m["id"]] = st.text_input(f"{n} (required)", "")

        submit_btn = st.form_submit_button("Create Epic in Jira 🏁")

    # ───── when user clicks submit ──────────────────────────────────
    if submit_btn:
        edited = {}
        for fid, w_val in widgets.items():
            if isinstance(w_val, datetime.date):
                edited[fid] = w_val.isoformat()
            elif isinstance(w_val, str) and fid == "labels":
                edited[fid] = [s.strip() for s in w_val.split(",") if s.strip()]
            else:
                edited[fid] = w_val

        jira      = st.session_state["jira"]
        fm        = FieldMetadataService(jira)
        handler   = EpicCreationHandler(jira, fm)
        accountId = fm.get_user_id()

        try:
            mapped  = handler.map_fields(edited, meta, accountId)
            key     = handler.create_epic(project_key, mapped)
            url     = f"{jira.base_url}/browse/{key}"
            st.success(f"✅ Epic {key} created!")
            st.markdown(f"[Open in Jira]({url})")
            st.balloons()
            del st.session_state["draft"]     # clear after success
        except Exception as e:
            st.error(f"Push failed: {e}")