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
from pydantic import BaseModel, create_model, Field

from mcp_servers.blender.server import BlenderMCPServer, MCPToolDefinition
from services.llm import LLMService

logger = logging.getLogger("blendpilot.core.agent")

class BlendPilotAgent:
    """Dynamic LangChain Agent that controls Blender via MCP tools."""

    def __init__(self, mcp_server: BlenderMCPServer | None = None, llm_service: LLMService | None = None, tavily_api_key: str | None = None):
        self.mcp_server = mcp_server or BlenderMCPServer()
        self.llm_service = llm_service or LLMService()
        self.tavily_api_key = tavily_api_key
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
            
        if self.tavily_api_key:
            from services.web_search import WebSearchService
            
            class WebSearchSchema(BaseModel):
                query: str = Field(..., description="The search query to look up on the web.")
                
            async def _web_search(query: str) -> dict[str, Any]:
                logger.info("Agent invoking web_search: %s", query)
                searcher = WebSearchService(api_key=self.tavily_api_key)
                res = await searcher.search(query)
                return res.model_dump()
                
            web_search_tool = StructuredTool(
                name="web_search",
                description="Search the web for 3D reference data, requirements, and documentation.",
                args_schema=WebSearchSchema,
                func=None,
                coroutine=_web_search,
            )
            lc_tools.append(web_search_tool)
            
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
        try:
            summary = await self.mcp_server.call_tool("get_scene_summary", {"include_mesh_stats": False})
            if isinstance(summary, dict) and not summary.get("error"):
                safe_summary = {k: v for k, v in summary.items() if k not in ["success", "error"]}
                user_input += (
                    f"\n\n[System Note: Current Blender scene state: {safe_summary}. "
                    "CRITICAL RULES: "
                    "1. Do not hallucinate objects not listed here. "
                    "2. ALWAYS check the 'dimensions' and 'location' of existing objects in this summary before creating new objects (e.g. if making a cup for a table, scale the cup down drastically so it physically fits on the table). "
                    "3. If a tool fails more than twice, STOP retrying and ask the user for help to avoid infinite loops. "
                    "4. SPATIAL REASONING: Blender's Z-axis is UP and primitive origins are at their center. When placing supports (like legs under a table) or resting objects (like a cup on a table), explicitly calculate the Z-location using the objects' Z-dimensions so they don't intersect or poke through the wrong side. "
                    "5. COMPLETENESS: Execute the FULL user request in a single turn without stopping halfway to ask for permission. If asked to 'create a table', do not just create the tabletop and stop; create the tabletop AND all 4 legs in one continuous execution before finishing.]"
                )
        except Exception as e:
            logger.warning("Failed to auto-inject scene summary: %s", e)

        async for event in self.agent_executor.astream_events(
            {"messages": [("user", user_input)]},
            config={"configurable": {"thread_id": session_id}, "recursion_limit": 150},
            version="v2",
        ):
            yield event
