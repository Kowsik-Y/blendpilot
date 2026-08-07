"""
BlendPilot AI — External Service Clients

This package provides async client interfaces for communicating
with external systems used by BlendPilot agents.

Services:
    - BlenderClient: HTTP client for the Blender bridge (Phase 2)
    - LLMService: Unified LLM provider abstraction (Phase 4)
    - WebSearchService: Web search for reference data (Phase 7)
    - EmailService: Email review workflow (Phase 9)
    - FileManager: Project file/directory management (Phase 3)
"""

from services.blender_client import BlenderClient
from services.file_manager import FileManager

__all__ = [
    "BlenderClient",
    "FileManager",
]
