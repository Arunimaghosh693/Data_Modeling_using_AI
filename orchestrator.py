from __future__ import annotations
import logging
logger = logging.getLogger(__name__)

import json
from dataclasses import dataclass
from typing import Any, Dict

try:
    from agents import modeling_agent
    from tools import extract_json_from_tool_output
except ImportError:  # pragma: no cover
    from .agents import modeling_agent
    from .tools import extract_json_from_tool_output



@dataclass
class DataModelingOrchestrator:
    name: str = "data_modeling_orchestrator"

    def run(self, user_query: str) -> Dict[str, Any]:
        result = modeling_agent.invoke(
            {"messages": [("user", user_query)]}
        )
         
        logger.info("Agent finished execution")


        conceptual_output = None
        logical_output = None
        physical_output = None
        final_text = ""

        for message in result.get("messages", []):
            name = getattr(message, "name", "") or ""
            content = getattr(message, "content", "")
            if isinstance(content, list):
                text_parts = []
                for part in content:
                    if isinstance(part, dict) and part.get("type") == "text":
                        text_parts.append(part.get("text", ""))
                content = "\n".join(text_parts)
            if not isinstance(content, str):
                content = str(content)

            if name == "conceptual_tool" and conceptual_output is None:
                conceptual_output = extract_json_from_tool_output(content)
            elif name == "logical_tool" and logical_output is None:
                logical_output = extract_json_from_tool_output(content)
            elif name == "physical_tool" and physical_output is None:
                physical_output = extract_json_from_tool_output(content)

            if content:
                final_text = content

        return {
            "requirement": user_query,
            "conceptual_output": conceptual_output,
            "logical_output": logical_output,
            "physical_output": physical_output,
            "agent_final_answer": final_text,
        }
