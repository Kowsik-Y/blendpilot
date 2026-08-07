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

    # If real API key is provided, execute real LLM reasoning
    if llm_service.config.api_key:
        try:
            context_str = f"User Query: {req.message}\n"
            if req.asset_spec:
                context_str += f"Current Spec: {req.asset_spec}\n"
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
                        "🚀 Apply Changes & Rerun Pipeline",
                        "📐 Inspect Bevel & Modifier Stack",
                        "🎨 Tune PBR Material Nodes",
                    ],
                    provider_used=req.provider,
                )
        except Exception as e:
            logger.warning("Copilot LLM call failed (%s), falling back to heuristic assistant", e)

    # Heuristic Copilot responses for instant interactive feedback without requiring API key
    msg_lower = req.message.lower()
    spec = req.asset_spec or {"asset_type": "crate", "dimensions": {"width": 1.0, "depth": 0.7, "height": 0.6}}
    asset_name = spec.get("asset_type", "model")

    if "bevel" in msg_lower or "edge" in msg_lower or "smooth" in msg_lower:
        reply = (
            f"🛠️ **Bevel & Edge Flow Adjustment for {asset_name.title()}**\n\n"
            f"I recommend adding a 2-segment non-destructive `BEVEL` modifier with width `0.02m` and angle limit `30°`. "
            f"This prevents harsh razor edges and catches specular highlights realistically."
        )
        actions = ["Apply 0.02m Bevel Modifier", "Enable Smooth Shading", "Run Topology QA"]

    elif "dimension" in msg_lower or "size" in msg_lower or "wider" in msg_lower or "taller" in msg_lower:
        reply = (
            f"📐 **Dimension Optimization**\n\n"
            f"Current dimensions: `{spec.get('dimensions', {})}`.\n"
            f"For Unity/Unreal scale conformity (1 unit = 1 meter), the proportions have been calibrated for standard character interaction bounds."
        )
        actions = ["Scale Width +20%", "Scale Height +15%", "Reset to Default 1x1x1"]

    elif "plan" in msg_lower or "steps" in msg_lower:
        reply = (
            f"📋 **Step-by-Step 10-Agent Plan for {asset_name.title()}**:\n\n"
            f"1. **Intent Parser**: Validate boundary dimensions & triangle quota (< 8,000 tris).\n"
            f"2. **Base Primitive**: Spawn bounding primitive with centered pivot at ground `Z=0`.\n"
            f"3. **Boolean & Modifiers**: Carve inset details and apply non-destructive Bevel.\n"
            f"4. **PBR Shader Tree**: Assign Principled BSDF with metallic and roughness nodes.\n"
            f"5. **Topology QA**: Verify manifold geometry, 0 non-manifold edges, 0 loose vertices."
        )
        actions = ["Execute 10-Step Pipeline", "Customize Material Nodes", "Export Multi-format"]

    elif "material" in msg_lower or "color" in msg_lower or "texture" in msg_lower:
        reply = (
            f"🎨 **PBR Material Configuration**\n\n"
            f"Configured with PBR Principled BSDF shader:\n"
            f"- Base Color: Dark Gunmetal `#1e293b`\n"
            f"- Metallic: `0.85`, Roughness: `0.35`\n"
            f"- Emissive Strip: Cyan `#06b6d4` with strength `1.5` for sci-fi accentuation."
        )
        actions = ["Switch to Warm Orange Glow", "Increase Roughness to 0.7", "Add Weathered Scratches"]

    else:
        reply = (
            f"🤖 **BlendPilot Copilot Ready**\n\n"
            f"I am analyzing your **{asset_name.title()}** 3D model. You can instruct me to adjust dimensions, "
            f"tweak modifier stacks, change PBR material finishes, or generate an atomic step-by-step modeling plan."
        )
        actions = ["Generate Detailed Modeling Plan", "Add Bevel Modifier", "Run Quality Check"]

    return CopilotChatResponse(
        reply=reply,
        suggested_actions=actions,
        provider_used="heuristic_assistant",
    )
