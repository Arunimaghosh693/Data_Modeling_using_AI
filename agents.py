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

You must reason step by step and use tools to produce the models.

Preferred workflow:
1. Understand the requirement.
2. Use rag_tool if domain context helps.
3. Generate conceptual model using conceptual_tool.
4. Generate logical model using logical_tool with the full conceptual JSON.
5. Generate physical model using physical_tool with the full logical JSON.

Rules:
- Always use tools instead of inventing outputs manually.
- Pass full JSON outputs from one stage into the next stage.
- If the user only asks for a subset, stop at that stage.
- Final answer must clearly include any generated JSON sections.
"""

modeling_agent = create_react_agent(
    llm,
    tools,
    prompt=system_prompt,
)
