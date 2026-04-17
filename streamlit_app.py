import json

import requests
import streamlit as st

API = "http://127.0.0.1:8000"

st.set_page_config(page_title="AI Data Modeling Workflow", layout="wide")

st.title("AI Data Modeling Workflow")
st.caption("Requirement -> Conceptual review -> Update conceptual -> Approve -> Logical and Physical")

DEFAULTS = {
    "artifact_id": None,
    "conceptual_status": None,
    "conceptual": None,
    "logical": None,
    "physical": None,
    "conceptual_url": None,
    "logical_url": None,
    "physical_url": None,
    "agent_final_answer": "",
}


for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def api_post(payload: dict) -> requests.Response:
    try:
        return requests.post(
            f"{API}/orchestrate",
            json=payload,
            timeout=300,
        )
    except requests.exceptions.ConnectionError:
        st.error("FastAPI backend not running.")
        st.info("Run: uvicorn api:app --reload")
        st.stop()
    except Exception as exc:  # pragma: no cover - UI-only safeguard
        st.error(str(exc))
        st.stop()


def show_json(data, title: str) -> None:
    st.subheader(title)

    if not data:
        st.info("No data available.")
        return

    if isinstance(data, (dict, list)):
        st.json(data)
        return

    if isinstance(data, str):
        try:
            st.json(json.loads(data))
        except Exception:
            st.code(data)
        return

    st.write(data)


def show_diagram_button(title: str, url: str | None) -> None:
    st.subheader(title)
    if not url:
        st.info("Diagram is not available.")
        return
    st.link_button(f"View {title}", url, use_container_width=False)


def store_orchestrate_response(data: dict) -> None:
    if data.get("conceptual_artifact_id"):
        st.session_state.artifact_id = data["conceptual_artifact_id"]

    st.session_state.conceptual_status = data.get("conceptual_status")
    st.session_state.conceptual = data.get("conceptual_output")
    st.session_state.logical = data.get("logical_output")
    st.session_state.physical = data.get("physical_output")
    st.session_state.conceptual_url = data.get("conceptual_view_url")
    st.session_state.logical_url = data.get("logical_view_url")
    st.session_state.physical_url = data.get("physical_view_url")
    st.session_state.agent_final_answer = data.get("agent_final_answer", "")


st.header("Enter Business Requirement")
requirement = st.text_area(
    "Requirement",
    height=220,
    placeholder="Example: Design a full conceptual, logical, and physical data model for the loan credit risk domain.",
    disabled=st.session_state.artifact_id is not None,
    label_visibility="collapsed",
)

generate_disabled = st.session_state.artifact_id is not None
if st.button("Generate Conceptual Draft", disabled=generate_disabled):
    if not requirement.strip():
        st.warning("Please enter requirement.")
        st.stop()

    with st.spinner("Generating conceptual draft..."):
        response = api_post({"requirement": requirement})

    if response.status_code != 200:
        st.error(response.text)
        st.stop()

    store_orchestrate_response(response.json())
    st.success("Conceptual draft generated.")
    st.rerun()

if st.session_state.artifact_id:
    st.caption(f"artifact_id: {st.session_state.artifact_id}")
    st.caption("This artifact_id stays the same for the full workflow until the page is refreshed.")

if st.session_state.agent_final_answer:
    st.info(st.session_state.agent_final_answer)


if st.session_state.conceptual:
    st.divider()
    st.header("Conceptual Review")
    conceptual_json_tab, conceptual_diagram_tab = st.tabs(["Conceptual JSON", "Conceptual Diagram"])

    with conceptual_json_tab:
        show_json(st.session_state.conceptual, "Conceptual JSON")

    with conceptual_diagram_tab:
        show_diagram_button("Conceptual Diagram", st.session_state.conceptual_url)

    if st.session_state.conceptual_status != "approved":
        st.divider()
        st.header("Update Conceptual")
        change_request = st.text_area(
            "Conceptual update request",
            key="conceptual_change_request",
            height=120,
            placeholder="Example: Create a direct connection between Loan and Customer_KYC, and add a new entity Customer_CIBIL connected to Customer_KYC.",
        )

        update_col, approve_col = st.columns(2)

        with update_col:
            if st.button("Apply Conceptual Update", use_container_width=True):
                if not st.session_state.artifact_id:
                    st.error("No conceptual artifact found. Generate the conceptual draft first.")
                    st.stop()
                if not change_request.strip():
                    st.warning("Please describe the conceptual update.")
                    st.stop()

                with st.spinner("Updating conceptual draft..."):
                    response = api_post(
                        {
                            "artifact_id": st.session_state.artifact_id,
                            "requirement": change_request,
                        }
                    )

                if response.status_code != 200:
                    st.error(response.text)
                    st.stop()

                store_orchestrate_response(response.json())
                st.success("Conceptual draft updated.")
                st.rerun()

        with approve_col:
            if st.button("Approve Conceptual", use_container_width=True):
                if not st.session_state.artifact_id:
                    st.error("No conceptual artifact found. Generate the conceptual draft first.")
                    st.stop()

                with st.spinner("Generating logical and physical outputs..."):
                    response = api_post(
                        {
                            "artifact_id": st.session_state.artifact_id,
                            "requirement": "approve",
                        }
                    )

                if response.status_code != 200:
                    st.error(response.text)
                    st.stop()

                store_orchestrate_response(response.json())
                st.success("Conceptual draft approved.")
                st.rerun()


if st.session_state.logical:
    st.divider()
    st.header("Logical Review")
    logical_json_tab, logical_diagram_tab = st.tabs(["Logical JSON", "Logical Diagram"])

    with logical_json_tab:
        show_json(st.session_state.logical, "Logical JSON")

    with logical_diagram_tab:
        show_diagram_button("Logical Diagram", st.session_state.logical_url)


if st.session_state.physical:
    st.divider()
    st.header("Physical Review")
    physical_json_tab, physical_diagram_tab = st.tabs(["Physical JSON", "Physical Diagram"])

    with physical_json_tab:
        show_json(st.session_state.physical, "Physical JSON")

        ddl = None
        if isinstance(st.session_state.physical, dict):
            ddl = st.session_state.physical.get("ddl")

        if ddl:
            st.subheader("DDL")
            if isinstance(ddl, list):
                st.code("\n".join(ddl), language="sql")
            else:
                st.code(str(ddl), language="sql")

    with physical_diagram_tab:
        show_diagram_button("Physical Diagram", st.session_state.physical_url)
