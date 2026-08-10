"""
BlendPilot AI — Interactive Copilot Chat Router

Enables conversational 3D modeling assistance, real-time plan modifications,
and agent step reasoning using real LLMs (OpenAI, Anthropic, or local).
"""

from __future__ import annotations

import logging
from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel, Field

from services.llm import LLMService

logger = logging.getLogger("blendpilot.routers.copilot")
router = APIRouter(prefix="/api/copilot", tags=["copilot"])


class CopilotChatRequest(BaseModel):
    message: str = Field(..., description="User question or instruction to the Copilot")
    asset_spec: dict[str, Any] | None = Field(default=None, description="Current 3D asset specification")
    current_plan: list[dict[str, Any]] | None = Field(default=None, description="Current step-by-step modeling plan")
    api_key: str | None = Field(default=None, description="Optional LLM API Key")
    provider: str = Field(default="openai", description="LLM provider (openai, anthropic)")
    model: str = Field(default="gpt-4o", description="LLM model")


class CopilotChatResponse(BaseModel):
    reply: str
    suggested_actions: list[str] = Field(default_factory=list)
    proposed_plan: list[dict[str, Any]] | None = None
    provider_used: str = "heuristic"


COPILOT_SYSTEM_PROMPT = """You are BlendPilot AI Copilot, an expert 3D modeling copilot for Blender.
You assist 3D artists and technical directors in designing, planning, modifying, and refining 3D models.
You have access to 10 autonomous agents:
1. Intent Understanding
2. Scene Understanding
3. Technical Research
4. Step Planning
5. Autonomous Modeling
6. Materials & Lighting
7. Geometry Topology QA
8. Visual Critique
9. Human Review
10. Production Export

When asked to modify or plan an asset:
- Give concise, clear, expert 3D advice (proportions in meters, modifier stacks, edge flow, PBR parameters).
- Suggest 2-3 immediate actionable next steps.
"""


@router.post("/chat", response_model=CopilotChatResponse)
async def chat_with_copilot(req: CopilotChatRequest) -> CopilotChatResponse:
    """Chat with the AI 3D Copilot for real-time planning, reasoning, and asset adjustments."""
    llm_service = LLMService(
        provider=req.provider,
        model=req.model,
        api_key=req.api_key,
    )

    # If API key is available or auto-resolved from environment, execute live LLM reasoning
    if llm_service.config.api_key:
        try:
            context_str = f"User Query: {req.message}\n"
            if req.asset_spec:
                context_str += f"Current 3D Spec: {req.asset_spec}\n"
            if req.current_plan:
                context_str += f"Current Plan Steps ({len(req.current_plan)} steps): {req.current_plan}\n"

            llm_reply = await llm_service.generate(
                prompt=context_str,
                system_prompt=COPILOT_SYSTEM_PROMPT,
            )
            if llm_reply:
                return CopilotChatResponse(
                    reply=llm_reply,
                    suggested_actions=[
                        "🚀 Launch 10-Agent Pipeline",
                        "🛠️ Add 0.02m Bevel Modifier",
                        "🎨 Tune PBR Material Nodes",
                    ],
                    provider_used=llm_service.config.provider,
                )
        except Exception as e:
            logger.warning("Copilot LLM call failed (%s)", e)

    return CopilotChatResponse(
        reply=(
            "⚠️ **API Key Required**\n\n"
            "Please configure your LLM API Key (Groq, OpenAI, Anthropic) in `.env` or in the Studio Settings "
            "to enable live agent thinking and autonomous 3D pipeline execution."
        ),
        suggested_actions=["🔑 Configure LLM Key", "🚀 Launch 10-Agent Pipeline"],
        provider_used="none",
    )
