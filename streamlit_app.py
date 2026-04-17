import json

import requests
import streamlit as st

API = "http://127.0.0.1:8000"

st.set_page_config(page_title="AI Data Modeling Workflow", layout="wide")

st.title("AI Data Modeling Workflow")
st.caption("Conceptual -> Review -> Approve -> Logical + Physical")

DEFAULTS = {
    "artifact_id": None,
    "conceptual_status": None,
    "conceptual": None,
    "logical": None,
    "physical": None,
    "conceptual_url": None,
    "logical_url": None,
    "physical_url": None,
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


def show_diagram(title: str, url: str | None) -> None:
    st.markdown(f"### {title}")

    if not url:
        st.info("Diagram not available.")
        return

    st.link_button(f"Open {title}", url)
    st.components.v1.iframe(url, height=500, scrolling=True)


def _store_orchestrate_response(data: dict) -> None:
    st.session_state.artifact_id = data.get("conceptual_artifact_id", st.session_state.artifact_id)
    st.session_state.conceptual_status = data.get("conceptual_status")
    st.session_state.conceptual = data.get("conceptual_output")
    st.session_state.logical = data.get("logical_output")
    st.session_state.physical = data.get("physical_output")
    st.session_state.conceptual_url = data.get("conceptual_view_url")
    st.session_state.logical_url = data.get("logical_view_url")
    st.session_state.physical_url = data.get("physical_view_url")


requirement = st.text_area(
    "Enter Business Requirement",
    height=180,
    placeholder="Example: Build a banking data model with customer, account, loan, transaction and repayment entities.",
)

if st.button("Generate Conceptual"):
    if not requirement.strip():
        st.warning("Please enter requirement.")
        st.stop()

    with st.spinner("Generating conceptual draft..."):
        response = api_post({"requirement": requirement})

    if response.status_code != 200:
        st.error(response.text)
        st.stop()

    _store_orchestrate_response(response.json())
    st.success("Conceptual draft generated.")
    st.rerun()


if st.session_state.conceptual:
    st.divider()
    st.header("Step 2: Review Conceptual Model")
    if st.session_state.artifact_id:
        st.caption(f"Artifact ID: {st.session_state.artifact_id}")

    tab1, tab2 = st.tabs(["JSON", "Diagram"])

    with tab1:
        show_json(st.session_state.conceptual, "Conceptual Model")

    with tab2:
        show_diagram("Conceptual Diagram", st.session_state.conceptual_url)

    if st.session_state.conceptual_status != "approved":
        st.subheader("Add Changes")
        change_request = st.text_input(
            "Example: Connect Customer to Account one to many",
            key="conceptual_change_request",
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Apply Conceptual Changes"):
                if not change_request.strip():
                    st.warning("Please describe the change.")
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

                _store_orchestrate_response(response.json())
                st.success("Conceptual draft updated.")
                st.rerun()

        with col2:
            if st.button("Approve Conceptual"):
                with st.spinner("Generating logical and physical models..."):
                    response = api_post(
                        {
                            "artifact_id": st.session_state.artifact_id,
                            "requirement": "approve",
                        }
                    )

                if response.status_code != 200:
                    st.error(response.text)
                    st.stop()

                _store_orchestrate_response(response.json())
                st.success("Conceptual draft approved.")
                st.rerun()


if st.session_state.logical:
    st.divider()
    st.header("Step 3: Logical Model")

    tab3, tab4 = st.tabs(["JSON", "Diagram"])

    with tab3:
        show_json(st.session_state.logical, "Logical Model")

    with tab4:
        show_diagram("Logical Diagram", st.session_state.logical_url)


if st.session_state.physical:
    st.divider()
    st.header("Step 4: Physical Model")

    tab5, tab6 = st.tabs(["JSON", "Diagram"])

    with tab5:
        show_json(st.session_state.physical, "Physical Model")

        ddl = None
        if isinstance(st.session_state.physical, dict):
            ddl = st.session_state.physical.get("ddl")

        if ddl:
            st.subheader("DDL Scripts")
            if isinstance(ddl, list):
                st.code("\n".join(ddl), language="sql")
            else:
                st.code(str(ddl), language="sql")

    with tab6:
        show_diagram("Physical Diagram", st.session_state.physical_url)
