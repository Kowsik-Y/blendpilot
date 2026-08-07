"""
BlendPilot AI — LLM Prompt Templates

Complete prompt templates for all 10 AI agents.
Each module exports SYSTEM_PROMPT and USER_PROMPT constants.

Prompt Design Principles:
    1. Explicit constraints — every prompt states what the agent must NOT do
    2. Structured output — format instructions for Pydantic parsing
    3. Few-shot examples — complex agents include 1-2 examples
    4. Safety guards — security rules where applicable
    5. Scope limitation — each agent stays within its workflow
"""

from prompts.intent import INTENT_SYSTEM_PROMPT, INTENT_USER_PROMPT
from prompts.scene import SCENE_SYSTEM_PROMPT, SCENE_USER_PROMPT
from prompts.research import RESEARCH_SYSTEM_PROMPT, RESEARCH_USER_PROMPT
from prompts.planning import PLANNING_SYSTEM_PROMPT, PLANNING_USER_PROMPT
from prompts.modeling import MODELING_SYSTEM_PROMPT, MODELING_USER_PROMPT
from prompts.material import MATERIAL_SYSTEM_PROMPT, MATERIAL_USER_PROMPT
from prompts.geometry_qa import GEOMETRY_QA_SYSTEM_PROMPT, GEOMETRY_QA_USER_PROMPT
from prompts.visual_critic import VISUAL_CRITIC_SYSTEM_PROMPT, VISUAL_CRITIC_USER_PROMPT
from prompts.feedback import FEEDBACK_SYSTEM_PROMPT, FEEDBACK_USER_PROMPT
from prompts.export import EXPORT_SYSTEM_PROMPT, EXPORT_USER_PROMPT

__all__ = [
    "INTENT_SYSTEM_PROMPT", "INTENT_USER_PROMPT",
    "SCENE_SYSTEM_PROMPT", "SCENE_USER_PROMPT",
    "RESEARCH_SYSTEM_PROMPT", "RESEARCH_USER_PROMPT",
    "PLANNING_SYSTEM_PROMPT", "PLANNING_USER_PROMPT",
    "MODELING_SYSTEM_PROMPT", "MODELING_USER_PROMPT",
    "MATERIAL_SYSTEM_PROMPT", "MATERIAL_USER_PROMPT",
    "GEOMETRY_QA_SYSTEM_PROMPT", "GEOMETRY_QA_USER_PROMPT",
    "VISUAL_CRITIC_SYSTEM_PROMPT", "VISUAL_CRITIC_USER_PROMPT",
    "FEEDBACK_SYSTEM_PROMPT", "FEEDBACK_USER_PROMPT",
    "EXPORT_SYSTEM_PROMPT", "EXPORT_USER_PROMPT",
]
