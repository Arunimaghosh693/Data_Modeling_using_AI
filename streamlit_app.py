import base64
import html
from io import BytesIO
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

import requests
import streamlit as st

API = "http://127.0.0.1:8000"
LOGO_PATH = Path(__file__).with_name("kpmg-logo-png_seeklogo-290229.png")
DATA_PRODUCTS = [
    "Conceptual",
    "Logical",
    "Physical",
    "Semantic Layer",
    "Ontology",
    "Dimensional Modeling",
]

st.set_page_config(page_title="AI Data Modeling Workflow", layout="wide")

def render_app_logo() -> None:
    if not LOGO_PATH.exists():
        return

    encoded_logo = base64.b64encode(LOGO_PATH.read_bytes()).decode("utf-8")
    st.markdown(
        f"""
        <style>
        .app-fixed-header-bg {{
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            height: 5.75rem;
            background: rgb(14, 17, 23);
            z-index: 999988;
            pointer-events: none;
        }}
        .app-fixed-header {{
            position: fixed;
            top: 0.95rem;
            left: 3.6rem;
            right: 1.25rem;
            z-index: 999990;
            display: flex;
            align-items: center;
            gap: 0.9rem;
            pointer-events: none;
            transition: left 180ms ease;
        }}
        .app-fixed-header img {{
            height: 46px;
            width: auto;
            display: block;
        }}
        .app-fixed-header-title {{
            margin: 0;
            color: rgba(250, 250, 250, 0.98);
            font-size: 2rem;
            font-weight: 700;
            line-height: 1;
            letter-spacing: -0.02em;
        }}
        div.block-container {{
            padding-top: 6.6rem;
        }}
        body:has(section[data-testid="stSidebar"][aria-expanded="true"]) .app-fixed-header {{
            left: 21rem;
        }}
        body:has(section[data-testid="stSidebar"][aria-expanded="false"]) .app-fixed-header {{
            left: 3.6rem;
        }}
        @media (max-width: 768px) {{
            .app-fixed-header-bg {{
                height: 5.9rem;
            }}
            .app-fixed-header {{
                top: 1rem;
                left: 4.2rem;
                right: 0.75rem;
            }}
            .app-fixed-header-title {{
                font-size: 1.35rem;
            }}
            body:has(section[data-testid="stSidebar"][aria-expanded="true"]) .app-fixed-header {{
                left: 4.2rem;
            }}
            div.block-container {{
                padding-top: 6.8rem;
            }}
        }}
        </style>
        <div class="app-fixed-header-bg"></div>
        <div class="app-fixed-header">
            <img src="data:image/png;base64,{encoded_logo}" alt="KPMG logo" />
            <h1 class="app-fixed-header-title">AI Data Modeling Workflow</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )


render_app_logo()

st.markdown(
    """
    <style>
    .workflow-stepper {
        display: flex;
        flex-wrap: nowrap;
        align-items: center;
        gap: 0.55rem;
        overflow-x: auto;
        white-space: nowrap;
        scrollbar-width: none;
    }
    .workflow-stepper::-webkit-scrollbar {
        display: none;
    }
    .workflow-stepper-shell {
        display: block;
        padding: 0.2rem 0;
    }
    .workflow-step {
        display: inline-flex;
        align-items: center;
        gap: 0.55rem;
        min-height: 2.25rem;
        padding: 0.4rem 0.8rem;
        border-radius: 999px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        background: rgba(255, 255, 255, 0.04);
        color: rgba(250, 250, 250, 0.68);
        font-size: 0.84rem;
        font-weight: 600;
        transition: all 180ms ease;
    }
    .workflow-step.completed {
        background: rgba(35, 182, 120, 0.16);
        border-color: rgba(35, 182, 120, 0.34);
        color: rgba(188, 255, 220, 0.98);
    }
    .workflow-step.current {
        background: rgba(43, 108, 255, 0.18);
        border-color: rgba(43, 108, 255, 0.4);
        color: rgba(229, 239, 255, 0.98);
        box-shadow: 0 0 0 0.2rem rgba(43, 108, 255, 0.14);
    }
    .workflow-step-index {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 1.2rem;
        height: 1.2rem;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.14);
        font-size: 0.68rem;
        font-weight: 800;
        color: inherit;
        flex: 0 0 auto;
    }
    .workflow-arrow {
        color: rgba(250, 250, 250, 0.34);
        font-size: 0.95rem;
        font-weight: 700;
    }
    .chat-input-shell {
        margin-top: 1rem;
    }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) {
        max-width: 82rem;
        min-height: 4.25rem;
        display: grid !important;
        grid-template-columns: 5.4rem minmax(0, 1fr) 5.4rem;
        align-items: center !important;
        gap: 0.75rem;
        padding: 0.55rem 0.85rem;
        border-radius: 999px;
        background: rgb(43, 43, 43);
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 22px 54px rgba(0, 0, 0, 0.24);
    }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) [data-testid="column"] {
        display: flex;
        align-items: center;
    }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) > div {
        width: auto !important;
        min-width: 0 !important;
        max-width: none !important;
        flex: unset !important;
    }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) > div:has([data-testid="stFileUploader"]) {
        justify-self: start;
    }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) > div:has([data-testid="stTextArea"]) {
        justify-self: stretch;
        padding-left: 0.3rem !important;
        padding-right: 0.3rem !important;
    }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) > div:has(.stButton) {
        justify-self: center;
    }
    .chat-input-shell [data-testid="column"] {
        padding-left: 0;
        padding-right: 0;
    }
    .chat-input-shell [data-testid="column"]:first-child {
        flex: unset !important;
        width: auto !important;
        min-width: 0 !important;
        padding-left: 0;
        padding-right: 0;
        justify-content: flex-start;
    }
    .chat-input-shell [data-testid="column"]:last-child {
        flex: unset !important;
        width: auto !important;
        min-width: 0 !important;
        padding-left: 0;
        padding-right: 0;
        justify-content: flex-end;
    }
    [data-testid="stFileUploader"] label,
    .chat-input-shell [data-testid="stTextArea"] label {
        display: none;
    }
    [data-testid="stFileUploader"] {
        width: 4.4rem;
        height: 3.2rem;
        overflow: hidden;
        border-radius: 999px;
        margin: 0;
        position: relative;
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.16);
    }
    [data-testid="stFileUploader"]:before {
        content: "+";
        position: absolute;
        inset: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        color: rgba(250, 250, 250, 0.92);
        font-size: 2.15rem;
        font-weight: 300;
        line-height: 1;
        pointer-events: none;
        z-index: 2;
    }
    [data-testid="stFileUploader"] section {
        width: 4.4rem;
        height: 3.2rem;
        min-height: 3.2rem;
        padding: 0 !important;
        border-radius: 999px !important;
        border: 0 !important;
        background: transparent !important;
        overflow: hidden;
    }
    [data-testid="stFileUploader"] section > div:first-child,
    [data-testid="stFileUploader"] small,
    [data-testid="stFileUploader"] span,
    [data-testid="stFileUploader"] p {
        display: none;
    }
    [data-testid="stFileUploader"] button {
        width: 4.4rem;
        height: 3.2rem;
        padding: 0;
        border: 0;
        background: transparent;
        color: transparent;
        opacity: 0;
    }
    [data-testid="stFileUploader"]:hover {
        background: rgba(255, 255, 255, 0.14);
        transform: translateY(-1px);
        box-shadow: 0 10px 28px rgba(0, 0, 0, 0.28);
    }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) [data-testid="stTextArea"] {
        width: 100%;
    }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) [data-testid="stTextArea"] textarea {
        height: auto !important;
        min-height: 3.2rem !important;
        max-height: 12rem;
        field-sizing: content;
        resize: none;
        border: 0 !important;
        outline: 0 !important;
        background: transparent !important;
        background-color: transparent !important;
        color: rgba(250, 250, 250, 0.95);
        padding: 0.72rem 0.85rem;
        font-size: 1.18rem;
        line-height: 1.45;
        box-shadow: none !important;
        overflow-y: auto;
    }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) [data-testid="stTextArea"] > div,
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) [data-testid="stTextArea"] > div > div,
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) [data-testid="stTextArea"] [data-baseweb="base-input"],
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) [data-testid="stTextArea"] [data-baseweb="textarea"],
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) [data-testid="stTextArea"] [data-baseweb="textarea"] > div {
        background: transparent !important;
        background-color: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
    }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) [data-testid="stTextArea"] * {
        background-color: transparent !important;
    }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) [data-testid="stTextArea"] [data-baseweb="textarea"]:focus-within {
        background: transparent !important;
        background-color: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
    }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) [data-testid="stTextArea"] textarea:focus {
        border: 0 !important;
        box-shadow: none !important;
        background: transparent !important;
    }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) [data-testid="InputInstructions"] {
        display: none !important;
    }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) .stButton > button {
        position: relative;
        width: 4.4rem;
        min-width: 4.4rem;
        min-height: 3.2rem;
        border-radius: 999px;
        border: 1px solid rgba(255, 255, 255, 0.16);
        background: rgba(255, 255, 255, 0.08);
        color: rgba(250, 250, 250, 0.95);
        padding: 0 0.75rem;
        font-size: 0.95rem;
        font-weight: 700;
        line-height: 1;
    }
    div[data-testid="stHorizontalBlock"]:has([data-testid="stFileUploader"]):has([data-testid="stTextArea"]) .stButton > button:hover {
        background: rgba(255, 255, 255, 0.14);
        transform: translateY(-1px);
        box-shadow: 0 10px 28px rgba(0, 0, 0, 0.28);
    }
    .chat-input-helper {
        margin-top: 0.45rem;
        color: rgba(250, 250, 250, 0.5);
        font-size: 0.86rem;
    }
    .attachment-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.55rem;
        max-width: 42rem;
        margin-top: 0.75rem;
        margin-bottom: 0.35rem;
        padding: 0.45rem 0.7rem 0.45rem 0.85rem;
        border-radius: 999px;
        border: 1px solid rgba(255, 255, 255, 0.12);
        background: rgba(255, 255, 255, 0.06);
        color: rgba(250, 250, 250, 0.9);
        font-size: 0.9rem;
        font-weight: 600;
    }
    .attachment-chip-type {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 2.8rem;
        padding: 0.16rem 0.4rem;
        border-radius: 999px;
        background: rgba(43, 108, 255, 0.22);
        color: rgba(229, 239, 255, 0.98);
        font-size: 0.68rem;
        font-weight: 800;
        letter-spacing: 0.04em;
    }
    .attachment-chip-name {
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    div[data-testid="stHorizontalBlock"]:has(.attachment-chip) {
        max-width: 82rem;
        align-items: center;
        gap: 0.35rem;
        margin-top: 0.55rem;
        margin-bottom: -0.35rem;
    }
    div[data-testid="stHorizontalBlock"]:has(.attachment-chip) [data-testid="column"] {
        display: flex;
        align-items: center;
    }
    div[data-testid="stHorizontalBlock"]:has(.attachment-chip) .stButton > button {
        width: 2.1rem;
        min-width: 2.1rem;
        min-height: 2.1rem;
        padding: 0;
        border-radius: 999px;
        font-size: 0.8rem;
        font-weight: 800;
        color: rgba(250, 250, 250, 0.82);
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255, 255, 255, 0.12);
    }
    div[data-testid="stHorizontalBlock"]:has(.attachment-chip) .stButton > button:hover {
        color: white;
        background: rgba(255, 85, 105, 0.18);
        border-color: rgba(255, 85, 105, 0.32);
    }
    @media (max-width: 768px) {
        .app-corner-logo {
            float: none;
            margin-right: 0;
            margin-bottom: 0.65rem;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)

def render_workflow_stepper() -> None:
    requirement_ready = (
        bool(st.session_state.get("requirement_input", "").strip())
        or bool(st.session_state.get("supportive_requirement_input", "").strip())
        or bool(st.session_state.get("artifact_id"))
    )
    conceptual_ready = st.session_state.get("conceptual") is not None
    update_or_approve_ready = (
        st.session_state.get("conceptual_updated", False)
        or st.session_state.get("conceptual_status") == "approved"
        or st.session_state.get("logical") is not None
        or st.session_state.get("physical") is not None
    )
    logical_ready = st.session_state.get("logical") is not None
    physical_ready = st.session_state.get("physical") is not None
    logical_and_physical_ready = (
        st.session_state.get("conceptual_status") == "approved"
        or logical_ready
        or physical_ready
    )

    step_completion = [
        ("Requirement", requirement_ready),
        ("Conceptual draft", conceptual_ready),
        ("Update/Approve", update_or_approve_ready),
        ("Logical & Physical", logical_and_physical_ready),
    ]

    if not requirement_ready:
        current_step = "Requirement"
    elif not conceptual_ready:
        current_step = "Conceptual draft"
    elif not logical_and_physical_ready:
        current_step = "Update/Approve"
    else:
        current_step = "Logical & Physical"

    html_parts = ["<div class='workflow-stepper-shell'><div class='workflow-stepper'>"]

    for index, (label, is_complete) in enumerate(step_completion, start=1):
        classes = ["workflow-step"]
        if is_complete:
            classes.append("completed")
        if label == current_step:
            classes.append("current")

        html_parts.append(
            f"<div class='{' '.join(classes)}'>"
            f"<span class='workflow-step-index'>{index}</span>"
            f"<span>{label}</span>"
            f"</div>"
        )
        if index < len(step_completion):
            html_parts.append("<span class='workflow-arrow'>&rarr;</span>")

    html_parts.append("</div></div><div style='clear: both;'></div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)


render_workflow_stepper()

DEFAULTS = {
    "artifact_id": None,
    "conceptual_status": None,
    "conceptual": None,
    "logical": None,
    "physical": None,
    "conceptual_url": None,
    "logical_url": None,
    "physical_url": None,
    "conceptual_diagram_version": 0,
    "logical_diagram_version": 0,
    "physical_diagram_version": 0,
    "conceptual_updated": False,
    "agent_final_answer": "",
    "brd_upload_reset": 0,
}


for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value


def reset_workflow_state() -> None:
    upload_reset = st.session_state.get("brd_upload_reset", 0) + 1
    for key, value in DEFAULTS.items():
        st.session_state[key] = value
    st.session_state.brd_upload_reset = upload_reset
    st.session_state.pop("requirement_input", None)
    st.session_state.pop("supportive_requirement_input", None)
    st.session_state.pop("conceptual_change_request", None)
    for key in list(st.session_state.keys()):
        if key.startswith("brd_upload_") and key != "brd_upload_reset":
            st.session_state.pop(key, None)


def extract_docx_text(uploaded_file) -> str:
    try:
        with zipfile.ZipFile(BytesIO(uploaded_file.getvalue())) as docx_zip:
            document_xml = docx_zip.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile) as exc:
        raise ValueError("Please upload a valid .docx Word document.") from exc

    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

    try:
        root = ET.fromstring(document_xml)
    except ET.ParseError as exc:
        raise ValueError("Could not read text from the uploaded Word document.") from exc

    paragraphs = []
    for paragraph in root.findall(".//w:p", namespace):
        text_parts = [node.text for node in paragraph.findall(".//w:t", namespace) if node.text]
        paragraph_text = "".join(text_parts).strip()
        if paragraph_text:
            paragraphs.append(paragraph_text)

    return "\n".join(paragraphs).strip()


def build_requirement_text(brd_text: str, supportive_text: str) -> str:
    sections = []
    if brd_text.strip():
        sections.append(f"BRD Document Content:\n{brd_text.strip()}")
    if supportive_text.strip():
        sections.append(f"Additional User Context:\n{supportive_text.strip()}")
    return "\n\n".join(sections).strip()


def api_post(payload: dict, action_label: str) -> requests.Response:
    try:
        with st.spinner(f"{action_label}..."):
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


def show_diagram(title: str, url: str | None, height: int = 760) -> None:
    st.subheader(title)

    if not url:
        st.info("Diagram is not available yet.")
        return

    if title == "Conceptual Diagram":
        version = st.session_state.conceptual_diagram_version
    elif title == "Logical Diagram":
        version = st.session_state.logical_diagram_version
    else:
        version = st.session_state.physical_diagram_version

    separator = "&" if "?" in url else "?"
    cache_busted_url = f"{url}{separator}v={version}"

    st.link_button(f"Open {title} in new tab", cache_busted_url, use_container_width=True)
    st.components.v1.iframe(cache_busted_url, height=height, scrolling=True)


def store_orchestrate_response(data: dict) -> None:
    if data.get("conceptual_artifact_id"):
        st.session_state.artifact_id = data["conceptual_artifact_id"]

    conceptual_output = data.get("conceptual_output")
    logical_output = data.get("logical_output")
    physical_output = data.get("physical_output")

    st.session_state.conceptual_status = data.get("conceptual_status")
    st.session_state.conceptual = conceptual_output
    st.session_state.logical = logical_output
    st.session_state.physical = physical_output
    st.session_state.conceptual_url = data.get("conceptual_view_url")
    st.session_state.logical_url = data.get("logical_view_url")
    st.session_state.physical_url = data.get("physical_view_url")
    st.session_state.agent_final_answer = data.get("agent_final_answer", "")

    if conceptual_output and st.session_state.conceptual_url:
        st.session_state.conceptual_diagram_version += 1
    if logical_output and st.session_state.logical_url:
        st.session_state.logical_diagram_version += 1
    if physical_output and st.session_state.physical_url:
        st.session_state.physical_diagram_version += 1


with st.sidebar:
    st.header("Data Products")
    selected_product = st.radio(
        "Data Products",
        DATA_PRODUCTS,
        label_visibility="collapsed",
    )

    st.divider()
    if st.button("Start New Workflow", use_container_width=True):
        reset_workflow_state()
        st.rerun()

if selected_product == "Conceptual":
    st.header("Enter Business Requirement")
    upload_key = f"brd_upload_{st.session_state.brd_upload_reset}"
    attached_brd = st.session_state.get(upload_key)

    if attached_brd is not None:
        attached_name = html.escape(getattr(attached_brd, "name", "Attached BRD document"))
        chip_col, remove_col = st.columns([7.8, 0.45])

        with chip_col:
            st.markdown(
                f"""
                <div class="attachment-chip">
                    <span class="attachment-chip-type">DOCX</span>
                    <span class="attachment-chip-name">{attached_name}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with remove_col:
            if st.button("x", key="remove_brd_attachment", help="Remove attachment"):
                st.session_state.pop(upload_key, None)
                st.session_state.brd_upload_reset += 1
                st.rerun()

    st.markdown("<div class='chat-input-shell'>", unsafe_allow_html=True)
    attach_col, text_col, action_col = st.columns([0.62, 6.4, 0.72])

    with attach_col:
        uploaded_brd = st.file_uploader(
            "Attach BRD .docx",
            type=["docx"],
            key=upload_key,
            disabled=st.session_state.artifact_id is not None,
            label_visibility="collapsed",
        )

    with text_col:
        supportive_text = st.text_area(
            "Supportive Text / Additional Requirement",
            key="supportive_requirement_input",
            placeholder="Enter/Upload your BRD document  draft.",
            height=68,
            disabled=st.session_state.artifact_id is not None,
            label_visibility="collapsed",
        )

    generate_disabled = st.session_state.artifact_id is not None
    with action_col:
        generate_clicked = st.button("Run", disabled=generate_disabled, use_container_width=True)

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='chat-input-helper'>Use + to attach a BRD .docx. Attachment text and prompt are combined as the requirement.</div>",
        unsafe_allow_html=True,
    )

    if generate_clicked:
        brd_text = ""
        if uploaded_brd is not None:
            try:
                brd_text = extract_docx_text(uploaded_brd)
            except ValueError as exc:
                st.error(str(exc))
                st.stop()

        requirement = build_requirement_text(brd_text, supportive_text)

        if not requirement:
            st.warning("Please upload a BRD document or enter supportive text.")
            st.stop()

        reset_workflow_state()
        st.session_state.requirement_input = requirement
        response = api_post(
            payload={"requirement": requirement},
            action_label="Generating conceptual draft",
        )

        if response.status_code != 200:
            st.error(response.text)
            st.stop()

        store_orchestrate_response(response.json())
        st.success("Conceptual draft generated.")
        st.rerun()

    st.divider()
    st.header("Conceptual")

    if not st.session_state.conceptual:
        st.info("Generate the conceptual draft first.")
    else:
        st.subheader("Update Conceptual")
        if st.session_state.conceptual_status == "approved":
            st.success("Conceptual draft is already approved.")
        else:
            change_request = st.text_area(
                "Conceptual update request",
                key="conceptual_change_request",
                height=180,
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

                    response = api_post(
                        payload={
                            "artifact_id": st.session_state.artifact_id,
                            "requirement": change_request,
                        },
                        action_label="Updating conceptual draft",
                    )

                    if response.status_code != 200:
                        st.error(response.text)
                        st.stop()

                    store_orchestrate_response(response.json())
                    st.session_state.conceptual_updated = True
                    st.success("Conceptual draft updated.")
                    st.rerun()

            with approve_col:
                if st.button("Approve Conceptual", use_container_width=True):
                    if not st.session_state.artifact_id:
                        st.error("No conceptual artifact found. Generate the conceptual draft first.")
                        st.stop()

                    response = api_post(
                        payload={
                            "artifact_id": st.session_state.artifact_id,
                            "requirement": "approve",
                        },
                        action_label="Approving conceptual draft",
                    )

                    if response.status_code != 200:
                        st.error(response.text)
                        st.stop()

                    store_orchestrate_response(response.json())
                    st.session_state.conceptual_updated = True
                    st.success("Conceptual draft approved.")
                    st.rerun()

        st.divider()
        show_diagram("Conceptual Diagram", st.session_state.conceptual_url, height=900)


elif selected_product == "Logical":
    st.divider()
    st.header("Logical")

    if not st.session_state.logical:
        if st.session_state.conceptual:
            st.info("Approve the conceptual draft to generate the logical output.")
        else:
            st.info("Generate and approve the conceptual draft first.")
    else:
        show_diagram("Logical Diagram", st.session_state.logical_url, height=900)
        st.divider()
        st.success("Logical model generated successfully.")
        if st.session_state.logical_url:
            st.caption("Use the diagram to inspect tables, columns, and PK/FK structure.")


elif selected_product == "Physical":
    st.divider()
    st.header("Physical")

    if not st.session_state.physical:
        if st.session_state.conceptual:
            st.info("Approve the conceptual draft to generate the physical output.")
        else:
            st.info("Generate and approve the conceptual draft first.")
    else:
        show_diagram("Physical Diagram", st.session_state.physical_url, height=900)
        st.divider()
        st.subheader("DDL")
        ddl = None
        if isinstance(st.session_state.physical, dict):
            ddl = st.session_state.physical.get("ddl")

        if ddl:
            if isinstance(ddl, list):
                st.code("\n".join(ddl), language="sql")
            else:
                st.code(str(ddl), language="sql")
        else:
            st.info("DDL is not available yet.")


elif selected_product == "Semantic Layer":
    st.divider()
    st.header("Semantic Layer")
    st.info("Semantic Layer will be added later.")


elif selected_product == "Ontology":
    st.divider()
    st.header("Ontology")
    st.info("Ontology workflow is not added yet.")


elif selected_product == "Dimensional Modeling":
    st.divider()
    st.header("Dimensional Modeling")
    st.info("Dimensional Modeling workflow is not added yet.")
