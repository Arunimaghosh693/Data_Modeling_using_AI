import base64
import json
import html
from datetime import datetime
from io import BytesIO
from pathlib import Path
import xml.etree.ElementTree as ET
import uuid
import zipfile

import requests
import streamlit as st

API = "http://127.0.0.1:8000"
LOGO_PATH = Path(__file__).with_name("kpmg-logo-png_seeklogo-290229.png")
EXAMPLE_IMAGE_PATH = Path(__file__).with_name("example.jpeg")
PROJECT_REPOSITORY_PATH = Path(__file__).with_name("project_repository")
PROJECT_STORE_FILE = PROJECT_REPOSITORY_PATH / "history.json"
LEGACY_PROJECT_STORE_FILE = PROJECT_REPOSITORY_PATH / "projects.json"
USE_CASE_REQUIREMENTS = {
    "usecase_1": "Design a full conceptual, logical, and physical data model for the loan credit risk domain.",
    "usecase_2": "Create a data model for customer, facility, loan, collateral, default, recovery, and provision reporting.",
}
LANDING_TOOL_CARDS = [
    {
        "phase": "Phase 1:",
        "title": "Conceptual",
        "description": "Business-level ER model with core entities and table-to-table relationships for review.",
    },
    {
        "phase": "Phase 2:",
        "title": "Logical",
        "description": "Low-level structure with tables, columns, primary keys, foreign keys, and relationships.",
    },
    {
        "phase": "Phase 3:",
        "title": "Physical",
        "description": "Developer-ready database design with datatypes, constraints, indexes, ER diagram, and DDL.",
    },
    {
        "phase": "Phase 4:",
        "title": "Upcoming",
        "description": "Reserved for Semantic Layer, Ontology, and Dimensional Modeling workflows.",
    },
]
TECH_USED = [
    "Python",
    "FastAPI",
    "Streamlit",
    "Gemini",
    "LangGraph",
    "LangChain",
    "FAISS",
    "Sentence Transformers",
    "Mermaid.js",
]
DATA_PRODUCTS = [
    "Conceptual",
    "Logical",
    "Physical",
    "Semantic Layer",
    "Ontology",
    "Dimensional Modeling",
]

st.set_page_config(page_title="OmniModel.AI - AI Data Fabric Application", layout="wide")

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
            max-width: calc(100vw - 28rem);
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
            font-size: 30px !important;
            font-weight: 700 !important;
            line-height: 1.05 !important;
            letter-spacing: -0.02em !important;
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
                max-width: calc(100vw - 6rem);
                font-size: 20px !important;
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
            <h1 class="app-fixed-header-title">OmniModel.AI - AI Data Fabric Application</h1>
        </div>
        """,
        unsafe_allow_html=True,
    )


render_app_logo()

st.markdown(
    """
    <style>
    div.block-container {
        font-size: 15px;
    }
    div.block-container h1 {
        font-size: 34px !important;
        line-height: 1.15 !important;
        letter-spacing: -0.02em !important;
    }
    div.block-container h2 {
        font-size: 30px !important;
        line-height: 1.16 !important;
        letter-spacing: -0.02em !important;
    }
    div.block-container h3 {
        font-size: 20px !important;
        line-height: 1.2 !important;
    }
    div.block-container label,
    div.block-container input,
    div.block-container textarea,
    div.block-container button,
    div.block-container p {
        font-size: 15px;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        font-size: 22px !important;
        line-height: 1.2 !important;
    }
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] button,
    section[data-testid="stSidebar"] span {
        font-size: 15px !important;
    }
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
        font-size: 13px;
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
    .workflow-step.completed.current {
        background: rgba(35, 182, 120, 0.16);
        border-color: rgba(35, 182, 120, 0.34);
        color: rgba(188, 255, 220, 0.98);
        box-shadow: 0 0 0 0.2rem rgba(35, 182, 120, 0.12);
    }
    .workflow-step-index {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 1.2rem;
        height: 1.2rem;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.14);
        font-size: 11px;
        font-weight: 800;
        color: inherit;
        flex: 0 0 auto;
    }
    .workflow-arrow {
        color: rgba(250, 250, 250, 0.34);
        font-size: 15px;
        font-weight: 700;
    }
    .landing-hero {
        max-width: 86rem;
        padding: 1rem 0 0.75rem;
    }
    .landing-hero h2 {
        margin: 0;
        color: rgba(250, 250, 250, 0.98);
        font-size: clamp(2.3rem, 4vw, 4.4rem);
        line-height: 1.02;
        letter-spacing: -0.04em;
    }
    .landing-hero p {
        max-width: 58rem;
        margin: 1rem 0 0;
        color: rgba(250, 250, 250, 0.62);
        font-size: 1.02rem;
        line-height: 1.6;
    }
    .landing-cta-panel {
        margin: 1.35rem 0 1.5rem;
        padding: 1rem;
        border-radius: 1.35rem;
        background: rgba(255, 255, 255, 0.04);
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 20px 56px rgba(0, 0, 0, 0.2);
    }
    .landing-section-title {
        margin: 0.4rem 0 0.85rem;
        color: rgba(250, 250, 250, 0.92);
        font-size: 1.05rem;
        font-weight: 800;
        letter-spacing: 0.02em;
    }
    .landing-card {
        min-height: 13rem;
        padding: 1.25rem;
        border-radius: 1.25rem;
        background:
            radial-gradient(circle at 10% 0%, rgba(43, 108, 255, 0.24), transparent 32%),
            rgba(255, 255, 255, 0.045);
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 20px 56px rgba(0, 0, 0, 0.24);
    }
    .landing-card h3 {
        margin: 0;
        color: rgba(250, 250, 250, 0.96);
        font-size: 1.25rem;
        line-height: 1.2;
    }
    .landing-card p {
        margin: 0.75rem 0 0;
        color: rgba(250, 250, 250, 0.58);
        font-size: 0.92rem;
        line-height: 1.45;
    }
    .landing-card-count {
        display: block;
        margin-top: 1.2rem;
        text-align: center;
        color: rgba(188, 255, 220, 0.98);
        font-size: 3rem;
        font-weight: 800;
        line-height: 1;
        letter-spacing: -0.04em;
    }
    .landing-card-note {
        display: block;
        margin-top: 0.55rem;
        text-align: center;
        color: rgba(250, 250, 250, 0.58);
        font-size: 0.9rem;
        line-height: 1.35;
    }
    .landing-tool-card {
        height: 15.5rem;
        padding: 1.1rem;
        border-radius: 1.25rem;
        display: flex;
        flex-direction: column;
        justify-content: flex-start;
        background:
            linear-gradient(140deg, rgba(18, 30, 52, 0.94), rgba(18, 22, 30, 0.78)),
            radial-gradient(circle at 90% 10%, rgba(255, 75, 82, 0.18), transparent 30%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 20px 56px rgba(0, 0, 0, 0.24);
    }
    .landing-tool-card h3 {
        margin: 0.2rem 0 0;
        color: rgba(250, 250, 250, 0.96);
        font-size: 1.2rem;
        line-height: 1.15;
    }
    .landing-tool-phase {
        display: block;
        color: rgba(188, 255, 220, 0.94);
        font-size: 0.88rem;
        font-weight: 800;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    .landing-tool-card p {
        margin: 1.05rem 0 0;
        color: rgba(250, 250, 250, 0.62);
        font-size: 0.86rem;
        line-height: 1.5;
    }
    .landing-tool-card.is-upcoming {
        background:
            linear-gradient(140deg, rgba(33, 34, 40, 0.86), rgba(17, 20, 27, 0.78)),
            radial-gradient(circle at 90% 10%, rgba(255, 255, 255, 0.08), transparent 30%);
        border-style: dashed;
    }
    .landing-example-section {
        margin-top: 2.8rem;
    }
    .landing-example-frame {
        padding: 0.8rem;
        border-radius: 1.35rem;
        background:
            radial-gradient(circle at 8% 0%, rgba(43, 108, 255, 0.14), transparent 30%),
            rgba(255, 255, 255, 0.035);
        border: 1px solid rgba(255, 255, 255, 0.09);
        box-shadow: 0 20px 56px rgba(0, 0, 0, 0.2);
        max-width: 54rem;
        margin: 0 auto;
    }
    .landing-example-frame img {
        display: block;
        width: 100%;
        max-height: 18rem;
        object-fit: contain;
        border-radius: 1rem;
        background: rgba(0, 0, 0, 0.18);
    }
    .tech-stack-section {
        margin-top: 3rem;
        padding: 1rem 1.2rem;
        border-radius: 1.35rem;
        background:
            radial-gradient(circle at 10% 0%, rgba(255, 75, 82, 0.12), transparent 30%),
            rgba(255, 255, 255, 0.035);
        border: 1px solid rgba(255, 255, 255, 0.09);
        box-shadow: 0 20px 56px rgba(0, 0, 0, 0.18);
    }
    .tech-stack-list {
        display: flex;
        flex-wrap: wrap;
        gap: 0.45rem;
        align-items: center;
    }
    .tech-stack-label {
        color: rgba(250, 250, 250, 0.92);
        font-size: 0.95rem;
        font-weight: 800;
        margin-right: 0.25rem;
    }
    .tech-stack-pill {
        display: inline-flex;
        align-items: center;
        padding: 0.35rem 0.55rem;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.07);
        color: rgba(250, 250, 250, 0.68);
        font-size: 0.78rem;
        line-height: 1;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .project-picker {
        margin-top: 1.25rem;
        padding: 1.1rem;
        border-radius: 1.1rem;
        background: rgba(255, 255, 255, 0.045);
        border: 1px solid rgba(255, 255, 255, 0.1);
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
        width: 4.4rem !important;
        min-width: 4.4rem !important;
        max-width: 4.4rem !important;
        height: 3.2rem;
        min-height: 3.2rem !important;
        max-height: 3.2rem !important;
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
        width: 4.4rem !important;
        min-width: 4.4rem !important;
        max-width: 4.4rem !important;
        height: 3.2rem !important;
        min-height: 3.2rem !important;
        max-height: 3.2rem !important;
        padding: 0 !important;
        border-radius: 999px !important;
        border: 0 !important;
        background: transparent !important;
        overflow: hidden;
    }
    [data-testid="stFileUploader"] > div,
    [data-testid="stFileUploader"] section > div,
    [data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"],
    [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] {
        width: 4.4rem !important;
        min-width: 4.4rem !important;
        max-width: 4.4rem !important;
        height: 3.2rem !important;
        min-height: 3.2rem !important;
        max-height: 3.2rem !important;
        overflow: hidden !important;
        border: 0 !important;
        background: transparent !important;
        box-shadow: none !important;
    }
    [data-testid="stFileUploader"] section > div:first-child,
    [data-testid="stFileUploader"] small,
    [data-testid="stFileUploader"] span,
    [data-testid="stFileUploader"] p,
    [data-testid="stFileUploader"] svg,
    [data-testid="stFileUploader"] [data-testid="stFileUploaderFile"] * {
        visibility: hidden !important;
        opacity: 0 !important;
        color: transparent !important;
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
        font-size: 16px !important;
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
        font-size: 15px !important;
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
        or st.session_state.get("conceptual_approved", False)
        or st.session_state.get("conceptual_status") == "approved"
        or st.session_state.get("logical") is not None
        or st.session_state.get("physical") is not None
    )
    logical_ready = st.session_state.get("logical") is not None
    physical_ready = st.session_state.get("physical") is not None
    logical_and_physical_ready = (
        st.session_state.get("conceptual_approved", False)
        or st.session_state.get("conceptual_status") == "approved"
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


if "app_page" not in st.session_state:
    st.session_state.app_page = "landing"
if "show_project_picker" not in st.session_state:
    st.session_state.show_project_picker = False

if st.session_state.app_page == "main":
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
    "conceptual_approved": False,
    "agent_final_answer": "",
    "brd_upload_reset": 0,
}


for key, value in DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = value

if "current_project_id" not in st.session_state:
    st.session_state.current_project_id = None
if "current_project_name" not in st.session_state:
    st.session_state.current_project_name = None
if "current_project_from_history" not in st.session_state:
    st.session_state.current_project_from_history = False
if "project_name_input" not in st.session_state:
    st.session_state.project_name_input = ""


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


def current_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_project_repository() -> None:
    PROJECT_REPOSITORY_PATH.mkdir(parents=True, exist_ok=True)


def project_file_path(project_id: str) -> Path:
    return PROJECT_REPOSITORY_PATH / f"{project_id}.json"


def read_store_file(store_file: Path) -> dict:
    if not store_file.exists():
        return {}

    try:
        store = json.loads(store_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}

    return store if isinstance(store, dict) else {}


#editd by mani
def normalize_project_for_history(project: dict) -> bool:
    changed = False
    timestamp = current_timestamp()

    if not project.get("project_id"):
        project["project_id"] = uuid.uuid4().hex
        changed = True

    if not project.get("project_name"):
        project["project_name"] = project.get("name") or f"Project {timestamp}"
        changed = True

    if not project.get("created_at"):
        project["created_at"] = project.get("updated_at") or timestamp
        changed = True

    if not project.get("updated_at"):
        project["updated_at"] = project.get("created_at") or timestamp
        changed = True

    if not isinstance(project.get("chat_history"), list):
        project["chat_history"] = []
        changed = True

    if not isinstance(project.get("state"), dict):
        project["state"] = {}
        changed = True

    state = project["state"]
    for state_key in (
        "artifact_id",
        "conceptual_url",
        "logical_url",
        "physical_url",
    ):
        if state.get(state_key) is not None:
            state[state_key] = None
            changed = True

    if not isinstance(project.get("diagram_json"), dict):
        project["diagram_json"] = diagram_json_from_state(project.get("state", {}))
        changed = True
    elif not project.get("diagram_json"):
        project["diagram_json"] = diagram_json_from_state(project.get("state", {}))
        changed = True

    for layer_data in (project.get("diagram_json") or {}).values():
        if isinstance(layer_data, dict) and layer_data.get("diagram_url") is not None:
            layer_data["diagram_url"] = None
            changed = True

    return changed


def read_project_store() -> dict:
    ensure_project_repository()
    projects = []
    known_project_ids = set()
    migrated_project = False

    for store_file in (PROJECT_STORE_FILE, LEGACY_PROJECT_STORE_FILE):
        store = read_store_file(store_file)
        store_projects = store.get("projects") if isinstance(store, dict) else None
        if not isinstance(store_projects, list):
            continue

        for project in store_projects:
            if not isinstance(project, dict):
                continue

            project_id = project.get("project_id")
            if not project_id:
                normalize_project_for_history(project)
                project_id = project.get("project_id")

            if project_id in known_project_ids:
                continue

            projects.append(project)
            known_project_ids.add(project_id)
            if store_file == LEGACY_PROJECT_STORE_FILE:
                migrated_project = True

    if not PROJECT_STORE_FILE.exists() and not projects:
        migrated_project = True

    for project_path in PROJECT_REPOSITORY_PATH.glob("*.json"):
        if project_path.name in {
            PROJECT_STORE_FILE.name,
            LEGACY_PROJECT_STORE_FILE.name,
        }:
            continue

        try:
            project = json.loads(project_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        project_id = project.get("project_id") if isinstance(project, dict) else None
        if project_id and project_id not in known_project_ids:
            projects.append(project)
            known_project_ids.add(project_id)
            migrated_project = True

    for project in projects:
        if not isinstance(project, dict):
            continue
        if normalize_project_for_history(project):
            migrated_project = True

    store = {
        "version": 2,
        "updated_at": current_timestamp(),
        "projects": projects,
    }
    if migrated_project or not PROJECT_STORE_FILE.exists():
        write_project_store(store)

    return store


def write_project_store(store: dict) -> None:
    ensure_project_repository()
    store["updated_at"] = current_timestamp()
    PROJECT_STORE_FILE.write_text(
        json.dumps(store, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def read_project(project_id: str) -> dict | None:
    store = read_project_store()
    for project in store.get("projects", []):
        if project.get("project_id") == project_id:
            return project

    project_path = project_file_path(project_id)
    if not project_path.exists():
        return None

    try:
        project = json.loads(project_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None

    if project.get("project_id"):
        normalize_project_for_history(project)
        store.setdefault("projects", []).append(project)
        write_project_store(store)

    return project


def write_project(project: dict) -> None:
    normalize_project_for_history(project)
    store = read_project_store()
    projects = store.setdefault("projects", [])
    project_written = False

    for index, existing_project in enumerate(projects):
        if existing_project.get("project_id") == project["project_id"]:
            projects[index] = project
            project_written = True
            break

    if not project_written:
        projects.append(project)

    write_project_store(store)


def list_saved_projects() -> list[dict]:
    store = read_project_store()
    projects = [
        project
        for project in store.get("projects", [])
        if isinstance(project, dict)
        and project.get("project_id")
        and project_has_saved_content(project)
    ]

    return sorted(projects, key=lambda item: item.get("updated_at", ""), reverse=True)


def project_has_saved_content(project: dict) -> bool:
    if project.get("chat_history"):
        return True

    state = project.get("state", {})
    if isinstance(state, dict) and any(
        state.get(key) is not None
        for key in (
            "conceptual",
            "logical",
            "physical",
        )
    ):
        return True

    diagram_json = project.get("diagram_json", {})
    if isinstance(diagram_json, dict):
        return any(
            isinstance(layer_data, dict)
            and layer_data.get("model_json") is not None
            for layer_data in diagram_json.values()
        )

    return False


def create_project(project_name: str | None = None) -> dict:
    timestamp = current_timestamp()
    project_id = uuid.uuid4().hex
    name = project_name.strip() if project_name and project_name.strip() else f"Project {timestamp}"
    project = {
        "project_id": project_id,
        "project_name": name,
        "created_at": timestamp,
        "updated_at": timestamp,
        "chat_history": [],
        "state": {},
        "diagram_json": {},
    }
    write_project(project)
    return project


def export_workflow_state() -> dict:
    state = {key: st.session_state.get(key) for key in DEFAULTS}
    state["artifact_id"] = None
    state["conceptual_url"] = None
    state["logical_url"] = None
    state["physical_url"] = None
    state["requirement_input"] = st.session_state.get("requirement_input", "")
    state["supportive_requirement_input"] = st.session_state.get("supportive_requirement_input", "")
    state["conceptual_change_request"] = st.session_state.get("conceptual_change_request", "")
    return state


def export_diagram_json() -> dict:
    return {
        "conceptual": {
            "model_json": st.session_state.get("conceptual"),
            "diagram_url": None,
            "diagram_version": st.session_state.get("conceptual_diagram_version", 0),
        },
        "logical": {
            "model_json": st.session_state.get("logical"),
            "diagram_url": None,
            "diagram_version": st.session_state.get("logical_diagram_version", 0),
        },
        "physical": {
            "model_json": st.session_state.get("physical"),
            "diagram_url": None,
            "diagram_version": st.session_state.get("physical_diagram_version", 0),
        },
    }


def diagram_json_from_state(state: dict) -> dict:
    if not isinstance(state, dict):
        state = {}

    return {
        "conceptual": {
            "model_json": state.get("conceptual"),
            "diagram_url": None,
            "diagram_version": state.get("conceptual_diagram_version", 0),
        },
        "logical": {
            "model_json": state.get("logical"),
            "diagram_url": None,
            "diagram_version": state.get("logical_diagram_version", 0),
        },
        "physical": {
            "model_json": state.get("physical"),
            "diagram_url": None,
            "diagram_version": state.get("physical_diagram_version", 0),
        },
    }


def workflow_state_from_diagram_json(diagram_json: dict) -> dict:
    if not isinstance(diagram_json, dict):
        return {}

    conceptual = diagram_json.get("conceptual", {})
    logical = diagram_json.get("logical", {})
    physical = diagram_json.get("physical", {})

    return {
        "artifact_id": None,
        "conceptual": conceptual.get("model_json"),
        "logical": logical.get("model_json"),
        "physical": physical.get("model_json"),
        "conceptual_url": None,
        "logical_url": None,
        "physical_url": None,
        "conceptual_diagram_version": conceptual.get("diagram_version", 0),
        "logical_diagram_version": logical.get("diagram_version", 0),
        "physical_diagram_version": physical.get("diagram_version", 0),
    }


def load_workflow_state(state: dict) -> None:
    reset_workflow_state()

    for key, value in state.items():
        if key in DEFAULTS or key in {
            "requirement_input",
            "supportive_requirement_input",
            "conceptual_change_request",
        }:
            st.session_state[key] = value

    st.session_state.artifact_id = None


def save_current_project(
    action_label: str,
    user_message: str = "",
    assistant_message: str = "",
) -> None:
    project_id = st.session_state.get("current_project_id")
    if not project_id:
        return

    project = read_project(project_id)
    if project is None:
        project = {
            "project_id": project_id,
            "project_name": st.session_state.get("current_project_name") or "Untitled Project",
            "created_at": current_timestamp(),
            "updated_at": current_timestamp(),
            "chat_history": [],
            "state": {},
        }

    timestamp = current_timestamp()
    if user_message:
        project.setdefault("chat_history", []).append(
            {
                "timestamp": timestamp,
                "role": "user",
                "action": action_label,
                "message": user_message,
            }
        )
    if assistant_message:
        project.setdefault("chat_history", []).append(
            {
                "timestamp": timestamp,
                "role": "assistant",
                "action": action_label,
                "message": assistant_message,
            }
        )

    project["project_name"] = st.session_state.get("current_project_name") or project.get("project_name")
    project["updated_at"] = timestamp
    project["state"] = export_workflow_state()
    project["diagram_json"] = export_diagram_json()
    write_project(project)


#editd by mani
def update_current_project_name(project_name: str) -> None:
    clean_project_name = project_name.strip()
    project_id = st.session_state.get("current_project_id")

    if not clean_project_name or not project_id:
        return
    if clean_project_name == st.session_state.get("current_project_name"):
        return

    project = read_project(project_id)
    if project is None:
        return

    project["project_name"] = clean_project_name
    project["updated_at"] = current_timestamp()
    st.session_state.current_project_name = clean_project_name
    write_project(project)


def open_project(project: dict) -> None:
    st.session_state.current_project_id = project["project_id"]
    st.session_state.current_project_name = project.get("project_name", "Untitled Project")
    diagram_state = workflow_state_from_diagram_json(project.get("diagram_json", {}))
    state = {
        **(project.get("state") or {}),
        **{key: value for key, value in diagram_state.items() if value is not None},
        "artifact_id": None,
        "conceptual_url": None,
        "logical_url": None,
        "physical_url": None,
    }
    load_workflow_state(state)
    st.session_state.current_project_id = project["project_id"]
    st.session_state.current_project_name = project.get("project_name", "Untitled Project")
    st.session_state.current_project_from_history = True
    st.session_state.project_name_input = st.session_state.current_project_name
    st.session_state.app_page = "main"
    st.session_state.show_project_picker = False


def start_new_project(project_name: str = "") -> None:
    reset_workflow_state()
    project = create_project(project_name)
    st.session_state.current_project_id = project["project_id"]
    st.session_state.current_project_name = project["project_name"]
    st.session_state.current_project_from_history = False
    st.session_state.project_name_input = project_name.strip()
    st.session_state.app_page = "main"
    st.session_state.show_project_picker = False


def render_project_picker(projects: list[dict]) -> None:
    st.markdown("<div class='project-picker'>", unsafe_allow_html=True)
    st.subheader("Previous Projects")

    if not projects:
        st.info("No saved projects found yet. Create a new project first.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    project_options = {
        f"{project.get('project_name', 'Untitled Project')} | Updated {project.get('updated_at', 'unknown')}": project
        for project in projects
    }
    selected_label = st.selectbox(
        "Select project",
        list(project_options.keys()),
        label_visibility="collapsed",
    )

    open_col, cancel_col = st.columns([1, 1])
    with open_col:
        if st.button("Open Selected Project", use_container_width=True):
            open_project(project_options[selected_label])
            st.rerun()

    with cancel_col:
        if st.button("Cancel", use_container_width=True):
            st.session_state.show_project_picker = False
            st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def render_landing_page() -> None:
    saved_projects = list_saved_projects()

    usecase_1_col, usecase_2_col, old_repo_col, docs_col = st.columns([1, 1, 1.45, 0.8])

    with usecase_1_col:
        if st.button("Core Banking", use_container_width=True):
            start_new_project()
            st.rerun()

    with usecase_2_col:
        if st.button("Loan", use_container_width=True):
            start_new_project()
            st.rerun()

    with old_repo_col:
        if saved_projects:
            project_options = {
                f"{project.get('project_name', 'Untitled Project')} | {project.get('updated_at', 'unknown')}": project
                for project in saved_projects
            }
            selected_project_label = st.selectbox(
                "Old repo",
                ["Select old repo"] + list(project_options.keys()),
                label_visibility="collapsed",
            )
            if selected_project_label != "Select old repo":
                open_project(project_options[selected_project_label])
                st.rerun()
        else:
            st.button("Old Repo (0)", disabled=True, use_container_width=True)

    with docs_col:
        if st.button("Docs", use_container_width=True):
            st.session_state.landing_notice = "Docs placeholder: add your project documentation link here."
            st.rerun()

    if st.session_state.get("landing_notice"):
        st.info(st.session_state.landing_notice)

    st.markdown("<div class='landing-section-title'>Data Modeling Flow</div>", unsafe_allow_html=True)
    card_columns = st.columns(4)
    for index, card in enumerate(LANDING_TOOL_CARDS):
        with card_columns[index]:
            upcoming_class = " is-upcoming" if card["title"] == "Upcoming" else ""
            st.markdown(
                f"""
                <div class="landing-tool-card{upcoming_class}">
                    <span class="landing-tool-phase">{html.escape(card["phase"])}</span>
                    <h3>{html.escape(card["title"])}</h3>
                    <p>{html.escape(card["description"])}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

    if EXAMPLE_IMAGE_PATH.exists():
        encoded_example = base64.b64encode(EXAMPLE_IMAGE_PATH.read_bytes()).decode("utf-8")
        st.markdown(
            f"""
            <section class="landing-example-section">
                <div class="landing-example-frame">
                    <img src="data:image/jpeg;base64,{encoded_example}" alt="Example workflow preview" />
                </div>
            </section>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.info("example.jpeg is not available in the project root.")

    tech_used_pills = "".join(
        f"<span class='tech-stack-pill'>{html.escape(tech)}</span>"
        for tech in TECH_USED
    )

    st.markdown(
        f"""
        <section class="tech-stack-section">
            <div class="tech-stack-list">
                <span class="tech-stack-label">Tech Stack:</span>
                {tech_used_pills}
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )


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


#editd by mani
def build_conceptual_continuation_payload(requirement: str) -> dict:
    return {
        "artifact_id": st.session_state.artifact_id,
        "requirement": requirement,
    }


def diagram_layer_from_title(title: str) -> str:
    return title.split(" ", 1)[0].lower()


#editd by mani
def get_saved_mermaid(layer: str) -> str | None:
    model_json = st.session_state.get(layer)

    if not isinstance(model_json, dict):
        return None

    mermaid_text = model_json.get("er_diagram_mermaid")
    if isinstance(mermaid_text, str) and mermaid_text.strip():
        return mermaid_text

    return None


#editd by mani
def build_saved_mermaid_html(title: str, payload: dict, mermaid_text: str) -> str:
    payload_json = json.dumps(payload, indent=2)
    safe_mermaid_text = html.escape(mermaid_text)
    mermaid_js = json.dumps(mermaid_text)
    payload_js = json.dumps(payload_json)
    json_filename = f"{diagram_layer_from_title(title)}_model.json"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <script type="module">
    import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs';
    mermaid.initialize({{ startOnLoad: true, theme: 'default' }});
  </script>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 0; background: #f7f7fb; color: #1f2937; }}
    .wrap {{ max-width: 1180px; margin: 0 auto; background: #ffffff; border-radius: 12px; padding: 24px; box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08); }}
    h1 {{ margin-top: 0; }}
    .toolbar {{ display: flex; gap: 12px; margin-bottom: 20px; flex-wrap: wrap; }}
    button {{ border: 0; border-radius: 8px; padding: 10px 14px; background: #0f766e; color: #ffffff; cursor: pointer; font-size: 14px; }}
    pre {{ background: #111827; color: #e5e7eb; padding: 16px; border-radius: 10px; overflow-x: auto; white-space: pre-wrap; }}
    .section {{ margin-top: 24px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>{html.escape(title)}</h1>
    <div class="toolbar">
      <button onclick="downloadMermaid()">Download .mmd</button>
      <button onclick="downloadJson()">Download JSON</button>
    </div>
    <div class="mermaid">
{safe_mermaid_text}
    </div>
    <div class="section"><h2>Mermaid Source</h2><pre id="source"></pre></div>
  </div>
  <script>
    const mermaidText = {mermaid_js};
    const modelJson = {payload_js};
    document.getElementById("source").textContent = mermaidText;
    function downloadMermaid() {{
      const blob = new Blob([mermaidText], {{ type: "text/plain;charset=utf-8" }});
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "er_diagram.mmd";
      link.click();
      URL.revokeObjectURL(url);
    }}
    function downloadJson() {{
      const blob = new Blob([modelJson], {{ type: "application/json;charset=utf-8" }});
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = {json.dumps(json_filename)};
      link.click();
      URL.revokeObjectURL(url);
    }}
  </script>
</body>
</html>"""


def show_diagram(title: str, url: str | None, height: int = 760) -> None:
    st.subheader(title)
    layer = diagram_layer_from_title(title)
    saved_mermaid = get_saved_mermaid(layer)

    if saved_mermaid:
        model_json = st.session_state.get(layer, {})
        st.components.v1.html(
            build_saved_mermaid_html(title, model_json, saved_mermaid),
            height=height,
            scrolling=True,
        )
        return

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

    conceptual_output = data.get("conceptual_output", st.session_state.get("conceptual"))
    logical_output = data.get("logical_output", st.session_state.get("logical"))
    physical_output = data.get("physical_output", st.session_state.get("physical"))

    st.session_state.conceptual_status = data.get(
        "conceptual_status",
        st.session_state.get("conceptual_status"),
    )
    st.session_state.conceptual = conceptual_output
    st.session_state.logical = logical_output
    st.session_state.physical = physical_output
    st.session_state.conceptual_url = data.get("conceptual_view_url", st.session_state.get("conceptual_url"))
    st.session_state.logical_url = data.get("logical_view_url", st.session_state.get("logical_url"))
    st.session_state.physical_url = data.get("physical_view_url", st.session_state.get("physical_url"))
    st.session_state.agent_final_answer = data.get(
        "agent_final_answer",
        st.session_state.get("agent_final_answer", ""),
    )

    if conceptual_output and st.session_state.conceptual_url:
        st.session_state.conceptual_diagram_version += 1
    if logical_output and st.session_state.logical_url:
        st.session_state.logical_diagram_version += 1
    if physical_output and st.session_state.physical_url:
        st.session_state.physical_diagram_version += 1
    if (
        st.session_state.conceptual_status == "approved"
        or logical_output is not None
        or physical_output is not None
    ):
        st.session_state.conceptual_approved = True


if st.session_state.app_page == "landing":
    render_landing_page()
    st.stop()

if st.session_state.app_page == "main" and not st.session_state.current_project_id:
    start_new_project()

with st.sidebar:
    if st.button("Back to Landing", use_container_width=True):
        st.session_state.app_page = "landing"
        st.rerun()

    st.caption("Current Project")
    st.info(st.session_state.current_project_name or "Untitled Project")

    st.header("Data Products")
    selected_product = st.radio(
        "Data Products",
        DATA_PRODUCTS,
        label_visibility="collapsed",
    )

    st.divider()
    if st.button("Start New Workflow", use_container_width=True):
        start_new_project()
        st.rerun()

    project = read_project(st.session_state.current_project_id) if st.session_state.current_project_id else None
    if project:
        with st.expander("Project History"):
            diagram_json = project.get("diagram_json", {})
            saved_layers = [
                layer_name.title()
                for layer_name, layer_data in diagram_json.items()
                if isinstance(layer_data, dict)
                and layer_data.get("model_json") is not None
            ]
            if saved_layers:
                st.caption(f"Saved JSON/Diagrams: {', '.join(saved_layers)}")

            st.download_button(
                "Download Project JSON",
                data=json.dumps(project, indent=2, ensure_ascii=False),
                file_name=f"{project.get('project_name', 'project').replace(' ', '_')}.json",
                mime="application/json",
                use_container_width=True,
            )

            if not project.get("chat_history"):
                st.caption("No chat history saved yet.")

            for item in project.get("chat_history", [])[-8:]:
                role = item.get("role", "user").title()
                action = item.get("action", "")
                message = item.get("message", "")
                st.caption(f"{role} | {action} | {item.get('timestamp', '')}")
                st.write(message[:350] + ("..." if len(message) > 350 else ""))

if selected_product == "Conceptual":
    st.header("Enter Business Requirement")

    if st.session_state.get("current_project_from_history"):
        st.caption(f"Project: {st.session_state.current_project_name or 'Untitled Project'}")
    else:
        project_name_value = st.text_input(
            "Project Name",
            key="project_name_input",
            placeholder="Enter project name",
        )
        update_current_project_name(project_name_value)

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
    # st.markdown(
    #     "<div class='chat-input-helper'>Use + to attach a BRD .docx. Attachment text and prompt are combined as the requirement.</div>",
    #     unsafe_allow_html=True,
    # )

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

        response_data = response.json()
        store_orchestrate_response(response_data)
        save_current_project(
            action_label="Generate Conceptual Draft",
            user_message=requirement,
            assistant_message=response_data.get("agent_final_answer", "Conceptual draft generated."),
        )
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
                        payload=build_conceptual_continuation_payload(change_request),
                        action_label="Updating conceptual draft",
                    )

                    if response.status_code != 200:
                        st.error(response.text)
                        st.stop()

                    response_data = response.json()
                    store_orchestrate_response(response_data)
                    st.session_state.conceptual_updated = True
                    save_current_project(
                        action_label="Update Conceptual Draft",
                        user_message=change_request,
                        assistant_message=response_data.get("agent_final_answer", "Conceptual draft updated."),
                    )
                    st.success("Conceptual draft updated.")
                    st.rerun()

            with approve_col:
                if st.button("Approve Conceptual", use_container_width=True):
                    if not st.session_state.artifact_id:
                        st.error("No conceptual artifact found. Generate the conceptual draft first.")
                        st.stop()

                    response = api_post(
                        payload=build_conceptual_continuation_payload("approve"),
                        action_label="Approving conceptual draft",
                    )

                    if response.status_code != 200:
                        st.error(response.text)
                        st.stop()

                    response_data = response.json()
                    store_orchestrate_response(response_data)
                    st.session_state.conceptual_updated = True
                    st.session_state.conceptual_approved = True
                    st.session_state.conceptual_status = "approved"
                    save_current_project(
                        action_label="Approve Conceptual Draft",
                        user_message="approve",
                        assistant_message=response_data.get(
                            "agent_final_answer",
                            "Conceptual draft approved. Logical and physical outputs generated.",
                        ),
                    )
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
