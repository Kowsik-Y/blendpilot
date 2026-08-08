"""
BlendPilot AI — Interactive Copilot Chat Router

LLM-powered conversational 3D modeling assistant using LangChain.
Supports real-time plan modifications, agent step reasoning, and
multi-turn conversation memory with RAG context.
"""

from __future__ import annotations

import json
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
    conversation_history: list[dict[str, str]] | None = Field(default=None, description="Multi-turn conversation history")
    api_key: str | None = Field(default=None, description="Optional LLM API Key")
    provider: str = Field(default="openai", description="LLM provider (openai, anthropic)")
    model: str = Field(default="gpt-4o", description="LLM model")


class CopilotChatResponse(BaseModel):
    reply: str
    suggested_actions: list[str] = Field(default_factory=list)
    proposed_plan: list[dict[str, Any]] | None = None
    provider_used: str = "heuristic"
    is_live_llm: bool = False


COPILOT_SYSTEM_PROMPT = """You are BlendPilot AI Copilot, an elite 3D Technical Director and Blender specialist.
You coordinate a 10-agent autonomous 3D pipeline:
1. Intent Understanding (Dimensions, triangle quota, asset taxonomy)
2. Scene Understanding (Collision check, origin calibration)
3. Technical Research (Engine profiles, non-manifold checks)
4. Step Planning (Atomic modeling step sequences)
5. Autonomous Modeling (bmesh primitives, insets, bevel modifiers)
6. Materials & Lighting (Principled BSDF, roughness, metallic, emissive)
7. Geometry Topology QA (Manifold verification, edge flow)
8. Visual Critique (Lighting distribution, bevel reflection)
9. Human Review (Approval gate)
10. Production Export (.blend, .fbx, .glb bundles)

Your interaction style:
- Deliver deeply knowledgeable, practical 3D modeling advice (proportions in meters, non-destructive modifier stacks, UV unwrapping, PBR material nodes).
- Answer greetings naturally and conversationally.
- For 3D modeling questions, provide clean Python bpy/bmesh snippets and exact modifier settings.
- When users describe a 3D object to create, provide a clear specification with dimensions, materials, triangle budget, and topology strategy.
- Structure responses with crisp Markdown formatting (bold headers, bullet points, code blocks).
- Suggest 2-3 actionable next steps at the end of your response.
"""


@router.post("/chat", response_model=CopilotChatResponse)
async def chat_with_copilot(req: CopilotChatRequest) -> CopilotChatResponse:
    """Chat with the AI 3D Copilot using real LLM reasoning via LangChain."""
    llm_service = LLMService(
        provider=req.provider,
        model=req.model,
        api_key=req.api_key,
    )

    # Build enriched context from scene state
    context_parts = [f"User Query: {req.message}"]
    if req.asset_spec:
        asset_type = req.asset_spec.get("asset_type", "model")
        dims = req.asset_spec.get("dimensions", {})
        context_parts.append(
            f"Active 3D Scene: {asset_type} "
            f"({dims.get('width', 1.0)}m × {dims.get('depth', 0.7)}m × {dims.get('height', 0.6)}m)"
        )
    if req.current_plan:
        context_parts.append(f"Current Plan: {len(req.current_plan)} modeling steps queued")

    context_str = "\n".join(context_parts)

    # If real API key is provided, use LangChain for real LLM reasoning
    if llm_service.config.api_key:
        try:
            reply = await _llm_chat(llm_service, context_str, req.conversation_history or [])
            if reply:
                return CopilotChatResponse(
                    reply=reply,
                    suggested_actions=_extract_suggested_actions(req.message, reply),
                    provider_used=req.provider,
                    is_live_llm=True,
                )
        except Exception as e:
            logger.warning("Copilot LLM call failed (%s), falling back to heuristic assistant", e)

    # No API key — return a helpful prompt
    return CopilotChatResponse(
        reply=(
            "⚠️ **API Key Required**\n\n"
            "To enable real-time AI chat and 3D agent execution, please configure your LLM API Key.\n\n"
            "Click **🔑 Configure LLM Key** or go to **⚙️ Settings** to link your OpenAI or Anthropic key."
        ),
        suggested_actions=["🔑 Configure LLM Key"],
        provider_used="none",
        is_live_llm=False,
    )


async def _llm_chat(
    llm_service: LLMService,
    context_str: str,
    conversation_history: list[dict[str, str]],
) -> str:
    """Execute real LLM chat with multi-turn conversation memory via LangChain."""
    from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

    messages = [SystemMessage(content=COPILOT_SYSTEM_PROMPT)]

    # Add conversation history for multi-turn memory
    for msg in conversation_history[-8:]:  # Keep last 8 turns for context window
        role = msg.get("role", "user")
        content = msg.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role in ("assistant", "copilot"):
            messages.append(AIMessage(content=content))

    # Add current user message with enriched context
    messages.append(HumanMessage(content=context_str))

    chat_model = llm_service.get_chat_model()
    response = await chat_model.ainvoke(messages)
    return str(response.content) if response.content else ""


def _extract_suggested_actions(user_msg: str, reply: str) -> list[str]:
    """Contextually extract suggested action chips from the conversation."""
    lower = (user_msg + " " + reply).lower()
    actions: list[str] = []

    # Detect modeling-related actions
    if any(kw in lower for kw in ["bevel", "edge", "chamfer", "smooth"]):
        actions.append("🛠️ Add 0.02m Bevel Modifier")
    if any(kw in lower for kw in ["dimension", "scale", "size", "resize", "wider", "taller"]):
        actions.append("📐 Adjust Dimensions")
    if any(kw in lower for kw in ["material", "shader", "color", "texture", "pbr", "metallic", "roughness"]):
        actions.append("🎨 Tune PBR Shader Nodes")
    if any(kw in lower for kw in ["plan", "step", "workflow", "pipeline"]):
        actions.append("📋 Generate Step-by-Step Plan")
    if any(kw in lower for kw in ["create", "make", "build", "generate", "design", "model"]):
        actions.append("🚀 Launch 10-Agent Pipeline")
    if any(kw in lower for kw in ["export", "download", "fbx", "glb", "blend"]):
        actions.append("📦 Export Production Bundle")
    if any(kw in lower for kw in ["topology", "manifold", "quality", "check", "validate"]):
        actions.append("🔍 Run Topology QA")

    if not actions:
        actions = ["🚀 Launch 10-Agent Pipeline", "📋 Generate Modeling Plan", "🛠️ Add 0.02m Bevel Modifier"]

    return actions[:3]
