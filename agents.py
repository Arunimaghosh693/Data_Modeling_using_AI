from __future__ import annotations

try:
    from langchain_openai import ChatOpenAI
    from langgraph.prebuilt import create_react_agent

    from config import get_openai_model
    from tools import conceptual_tool, logical_tool, rag_tool
except ImportError:  # pragma: no cover
    from langchain_openai import ChatOpenAI
    from langgraph.prebuilt import create_react_agent

    from .config import get_openai_model
    from .tools import conceptual_tool, logical_tool, rag_tool


llm = ChatOpenAI(model=get_openai_model())

tools = [rag_tool, conceptual_tool, logical_tool]

system_prompt = """
You are a banking domain expert and enterprise data modeling agent.

Your job is to generate a COMPLETE data model from a business requirement.

-----------------------------------
STEP 1: CONCEPTUAL MODEL
-----------------------------------
- Call conceptual_tool with the user requirement

-----------------------------------
STEP 2: LOGICAL MODEL
-----------------------------------
- Pass FULL output of conceptual_tool to logical_tool

-----------------------------------
STEP 3: PHYSICAL MODEL
-----------------------------------
- Pass FULL output of logical_tool to physical_tool

-----------------------------------
FINAL OUTPUT
-----------------------------------
- Return conceptual, logical, and physical models

-----------------------------------
STRICT RULES:
-----------------------------------
- Call each tool ONLY ONCE
- Do NOT retry tools
- Do NOT skip steps
- Always follow sequence: conceptual → logical → physical

VERY IMPORTANT:
- Tools return JSON objects (not strings)
- Pass tool outputs directly as inputs to the next tool
- Do NOT convert JSON to text
- Do NOT summarize or modify JSON between steps

- Stop immediately after physical_tool
"""

modeling_agent = create_react_agent(
    llm,
    tools,
    prompt=system_prompt,
)
