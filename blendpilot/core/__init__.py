"""
BlendPilot AI — Core Blender Python Functions

This package contains direct Blender Python API (bpy/bmesh) wrappers
for all primitive operations needed by the BlendPilot agent.

These functions are designed to:
- Run inside Blender's Python environment
- Validate all inputs before executing
- Return structured results
- Provide meaningful error messages
- Be consumed by the Blender add-on operators in Phase 2+

Phase 1 — Blender Proof of Concept
"""

import logging

logger = logging.getLogger("blendpilot.core")
