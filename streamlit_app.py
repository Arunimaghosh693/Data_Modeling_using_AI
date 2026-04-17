import streamlit as st
import requests
import json

API = "http://127.0.0.1:8000"

# ---------------------------------------------------
# Page Config
# ---------------------------------------------------
st.set_page_config(
    page_title="AI Data Modeling Workflow",
    layout="wide"
)

st.title("AI Data Modeling Workflow")
st.caption("Conceptual → Review → Logical → Review → Physical")

# ---------------------------------------------------
# Session State Initialization
# ---------------------------------------------------
defaults = {
    "conceptual": None,
    "logical": None,
    "physical": None,
    "conceptual_url": None,
    "logical_url": None,
    "physical_url": None,
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# ---------------------------------------------------
# Helpers
# ---------------------------------------------------
def api_post(endpoint, payload):
    try:
        res = requests.post(
            f"{API}{endpoint}",
            json=payload,
            timeout=300
        )
        return res
    except requests.exceptions.ConnectionError:
        st.error("FastAPI backend not running.")
        st.info("Run: uvicorn api:app --reload")
        st.stop()
    except Exception as e:
        st.error(str(e))
        st.stop()


def show_json(data, title):
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


def show_diagram(title, url):
    st.markdown(f"### {title}")

    if url:
        st.link_button(f"Open {title}", url)
        st.components.v1.iframe(
            url,
            height=500,
            scrolling=True
        )
    else:
        st.info("Diagram not available.")


# ---------------------------------------------------
# Step 1: Requirement Input
# ---------------------------------------------------
requirement = st.text_area(
    "Enter Business Requirement",
    height=180,
    placeholder="Example: Build a banking data model with customer, account, loan, transaction and repayment entities."
)

col1, col2 = st.columns([1, 5])

with col1:
    generate = st.button("Generate Conceptual")

# ---------------------------------------------------
# Generate Conceptual
# ---------------------------------------------------
if generate:

    if not requirement.strip():
        st.warning("Please enter requirement.")
        st.stop()

    with st.spinner("Generating Conceptual Model..."):
        res = api_post(
            "/generate-conceptual",
            {"requirement": requirement}
        )

    if res.status_code != 200:
        st.error(res.text)
        st.stop()

    data = res.json()

    st.session_state.conceptual = data.get("conceptual_output")
    st.session_state.conceptual_url = data.get("conceptual_view_url")

    st.success("Conceptual Model Generated")

# ---------------------------------------------------
# Conceptual Section
# ---------------------------------------------------
if st.session_state.conceptual:

    st.divider()
    st.header("Step 2: Review Conceptual Model")

    tab1, tab2 = st.tabs(["JSON", "Diagram"])

    with tab1:
        show_json(
            st.session_state.conceptual,
            "Conceptual Model"
        )

    with tab2:
        show_diagram(
            "Conceptual Diagram",
            st.session_state.conceptual_url
        )

    # -------------------------------
    # Add Changes
    # -------------------------------
    st.subheader("Add Changes")

    change_request = st.text_input(
        "Example: Connect Customer to Account one to many"
    )

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Apply Conceptual Changes"):

            with st.spinner("Updating Conceptual Model..."):
                res = api_post(
                    "/update-conceptual",
                    {
                        "existing_model": st.session_state.conceptual,
                        "change_request": change_request
                    }
                )

            if res.status_code == 200:
                data = res.json()

                st.session_state.conceptual = data.get("conceptual_output")
                st.session_state.conceptual_url = data.get("conceptual_view_url")

                st.success("Conceptual Model Updated")
                st.rerun()

            else:
                st.error(res.text)

    with col2:
        if st.button("Approve Conceptual"):

            with st.spinner("Generating Logical Model..."):
                res = api_post(
                    "/generate-logical",
                    {
                        "conceptual_model": st.session_state.conceptual
                    }
                )

            if res.status_code == 200:
                data = res.json()

                st.session_state.logical = data.get("logical_output")
                st.session_state.logical_url = data.get("logical_view_url")

                st.success("Logical Model Generated")
                st.rerun()

            else:
                st.error(res.text)

# ---------------------------------------------------
# Logical Section
# ---------------------------------------------------
if st.session_state.logical:

    st.divider()
    st.header("Step 3: Review Logical Model")

    tab3, tab4 = st.tabs(["JSON", "Diagram"])

    with tab3:
        show_json(
            st.session_state.logical,
            "Logical Model"
        )

    with tab4:
        show_diagram(
            "Logical Diagram",
            st.session_state.logical_url
        )

    if st.button("Approve Logical"):

        with st.spinner("Generating Physical Model..."):
            res = api_post(
                "/generate-physical",
                {
                    "logical_model": st.session_state.logical
                }
            )

        if res.status_code == 200:
            data = res.json()

            st.session_state.physical = data.get("physical_output")
            st.session_state.physical_url = data.get("physical_view_url")

            st.success("Physical Model Generated")
            st.rerun()

        else:
            st.error(res.text)

# ---------------------------------------------------
# Physical Section
# ---------------------------------------------------
if st.session_state.physical:

    st.divider()
    st.header("Step 4: Physical Model")

    tab5, tab6 = st.tabs(["JSON", "Diagram"])

    with tab5:
        show_json(
            st.session_state.physical,
            "Physical Model"
        )

        ddl = None

        if isinstance(st.session_state.physical, dict):
            ddl = st.session_state.physical.get("ddl")

        if ddl:
            st.subheader("DDL Scripts")

            if isinstance(ddl, list):
                for stmt in ddl:
                    st.code(stmt, language="sql")
            else:
                st.code(str(ddl), language="sql")

    with tab6:
        show_diagram(
            "Physical Diagram",
            st.session_state.physical_url
        )