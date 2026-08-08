"""
BlendPilot AI — Core LangChain Agent

Provides a tool-calling LangChain Agent that orchestrates Blender MCP tools.
It maintains conversational memory and streams Chain-of-Thought execution.
"""

from __future__ import annotations

import logging
from typing import Any, AsyncGenerator, Dict, List

from langchain.agents import create_agent
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, create_model

from mcp_servers.blender.server import BlenderMCPServer, MCPToolDefinition
from services.llm import LLMService

logger = logging.getLogger("blendpilot.core.agent")

class BlendPilotAgent:
    """Dynamic LangChain Agent that controls Blender via MCP tools."""

    def __init__(self, mcp_server: BlenderMCPServer | None = None, llm_service: LLMService | None = None):
        self.mcp_server = mcp_server or BlenderMCPServer()
        self.llm_service = llm_service or LLMService()
        self.tools = self._build_langchain_tools()
        self.memory = MemorySaver()
        self.agent_executor = self._build_agent_executor()

    def _build_langchain_tools(self) -> list[StructuredTool]:
        """Wrap Blender MCP tools as standard LangChain StructuredTools."""
        lc_tools = []
        for defn in self.mcp_server.list_tools():
            # Dynamically create a Pydantic model from the JSON schema
            fields = {}
            props = defn.parameters_schema.get("properties", {})
            required = defn.parameters_schema.get("required", [])
            
            for key, prop in props.items():
                ptype = Any
                if prop.get("type") == "string":
                    ptype = str
                elif prop.get("type") in ["integer", "number"]:
                    ptype = float
                elif prop.get("type") == "boolean":
                    ptype = bool
                elif prop.get("type") == "array":
                    ptype = list
                
                default = ... if key in required else None
                fields[key] = (ptype, default)

            SchemaModel = create_model(f"{defn.name}Schema", **fields)

            # Create closure for the async handler
            def make_coro(tool_name: str):
                async def _coro(**kwargs) -> dict[str, Any]:
                    logger.info("Agent invoking tool: %s with args: %s", tool_name, kwargs)
                    return await self.mcp_server.call_tool(tool_name, kwargs)
                return _coro

            tool = StructuredTool(
                name=defn.name,
                description=defn.description,
                args_schema=SchemaModel,
                func=None,
                coroutine=make_coro(defn.name),
            )
            lc_tools.append(tool)
        return lc_tools

    def _build_agent_executor(self):
        """Construct the core tool-calling agent executor."""
        model = self.llm_service.get_chat_model()

        system_prompt = (
             "You are BlendPilot, an autonomous expert 3D modeling AI. "
             "You have access to a suite of Blender MCP tools to create, modify, and render 3D scenes. "
             "When the user asks you to create or change something, make a plan and execute the necessary tools. "
             "Always explain what you are doing. If a tool fails, reason about the error and try again. "
             "Once you finish your tasks, inform the user."
        )

        return create_agent(
            model=model,
            tools=self.tools,
            system_prompt=system_prompt,
            checkpointer=self.memory,
        )

    async def astream_events(self, user_input: str, session_id: str = "default_thread") -> AsyncGenerator[Dict[str, Any], None]:
        """Stream the execution trace using astream_events."""
        async for event in self.agent_executor.astream_events(
            {"messages": [("user", user_input)]},
            config={"configurable": {"thread_id": session_id}},
            version="v2",
        ):
            yield event
