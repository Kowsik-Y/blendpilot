"""
BlendPilot AI — Autonomous Agent Registry

Target pipeline agents (9):
1. IntentAgent      — Parse natural language into structured DesignSpec
2. PlanningAgent    — Generate atomic, step-by-step DesignPlan
3. GenerationAgent  — Execute mesh modeling + materials + lighting + render
4. GeometryQAAgent  — Deterministic geometry topology validation
5. VisualCriticAgent— Vision LLM aesthetic critique
6. DecisionAgent    — APPROVE or REPAIR routing decision
7. RepairAgent      — Targeted geometry and aesthetic repair operations
8. ExportAgent      — Multi-format asset packaging and reporting
"""

from agents.decision_agent import DecisionAgent
from agents.export_agent import ExportAgent
from agents.generation_agent import GenerationAgent
from agents.geometry_qa_agent import GeometryQAAgent
from agents.intent_agent import IntentAgent
from agents.planning_agent import PlanningAgent
from agents.repair_agent import RepairAgent
from agents.visual_critic_agent import VisualCriticAgent

__all__ = [
    "IntentAgent",
    "PlanningAgent",
    "GenerationAgent",
    "GeometryQAAgent",
    "VisualCriticAgent",
    "DecisionAgent",
    "RepairAgent",
    "ExportAgent",
]
