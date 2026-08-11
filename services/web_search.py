"""
BlendPilot AI — Web Search Service

Provides web search capabilities for the Research Agent.
All web content is treated as UNTRUSTED reference data.

Phase: 7 (interface defined, implementation pending)

SECURITY RULES:
- All web content is marked trust_level="untrusted"
- Never execute code or instructions found in search results
- Never interpret web content as system commands
- Log all search queries for audit
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger("blendpilot.services.web_search")


# ── Data Models ─────────────────────────────────────────────


class SearchResult(BaseModel):
    """A single search result."""

    title: str = Field(..., description="Page title")
    url: str = Field(..., description="Page URL")
    snippet: str = Field(default="", description="Text excerpt from the page")
    source_domain: str = Field(default="", description="Domain name of the source")
    trust_level: str = Field(
        default="untrusted",
        description="Trust level — always 'untrusted' for web content",
    )


class SearchResponse(BaseModel):
    """Response from a search query."""

    query: str
    results: list[SearchResult] = Field(default_factory=list)
    total_results: int = 0
    error: str | None = None


# ── Service ─────────────────────────────────────────────────


class WebSearchService:
    """Searches the web for reference information.

    Used by the Research Agent (Workflow 3) to find:
    - Blender API documentation
    - Game engine asset requirements
    - Typical real-world object dimensions
    - Mechanical reference information

    All results are treated as UNTRUSTED data.
    The agent uses results as reference only, never as instructions.

    Usage:
        search = WebSearchService(api_key="...")
        results = await search.search("Unity FBX import requirements")
        for r in results.results:
            print(f"[{r.trust_level}] {r.title}: {r.url}")
    """

    def __init__(
        self,
        api_key: str | None = None,
        max_results: int = 5,
        search_provider: str = "tavily",
    ):
        """Initialize the search service.

        Args:
            api_key: API key for the search provider.
            max_results: Maximum number of results per query.
            search_provider: Search backend — "tavily", "serper", or "google".
        """
        self.api_key = api_key
        self.max_results = max_results
        self.search_provider = search_provider

    async def search(self, query: str) -> SearchResponse:
        """Search the web with a general query.

        Args:
            query: Search query string.

        Returns:
            SearchResponse with results marked as untrusted.
        """
        logger.info("Web search: '%s' (provider=%s)", query, self.search_provider)
        
        if self.search_provider == "tavily" and self.api_key:
            try:
                from tavily import AsyncTavilyClient
                # Typically, Tavily client accepts the API key.
                # In actual implementation, manage this carefully.
                client = AsyncTavilyClient(api_key=self.api_key)
                response = await client.search(
                    query,
                    search_depth="advanced",
                    max_results=self.max_results,
                    include_domains=[],
                    exclude_domains=[],
                )
                
                results = []
                for result in response.get("results", []):
                    results.append(SearchResult(
                        title=result.get("title", ""),
                        url=result.get("url", ""),
                        snippet=result.get("content", ""),
                        source_domain="",
                        trust_level="untrusted"
                    ))
                    
                return SearchResponse(query=query, results=results, total_results=len(results))
            except Exception as e:
                logger.error("Tavily search failed: %s", e)
                return SearchResponse(query=query, results=[], total_results=0, error=str(e))
                
        # Fallback or stub if API key is missing
        logger.warning("Web search stub fallback — returning empty results.")
        return SearchResponse(query=query, results=[], total_results=0)

    async def search_blender_docs(self, topic: str) -> SearchResponse:
        """Search specifically in Blender documentation.

        Args:
            topic: Blender-specific topic to search for.

        Returns:
            SearchResponse scoped to Blender docs.
        """
        return await self.search(f"site:docs.blender.org {topic}")

    async def search_unity_requirements(self, asset_type: str) -> SearchResponse:
        """Search for Unity asset import requirements.

        Args:
            asset_type: Type of asset (e.g., "FBX mesh", "character model").
        """
        return await self.search(f"Unity {asset_type} import requirements best practices")

    async def search_unreal_requirements(self, asset_type: str) -> SearchResponse:
        """Search for Unreal Engine asset requirements."""
        return await self.search(f"Unreal Engine {asset_type} import requirements")

    async def search_reference_dimensions(self, object_type: str) -> SearchResponse:
        """Search for typical real-world dimensions of an object.

        Args:
            object_type: Type of object (e.g., "dining table", "barrel").
        """
        return await self.search(f"typical dimensions of {object_type} in meters centimeters")

    async def search_mechanical_reference(self, component: str) -> SearchResponse:
        """Search for mechanical component reference data.

        Args:
            component: Component name (e.g., "M8 bolt", "spur gear").
        """
        return await self.search(f"{component} dimensions specifications mechanical engineering")

    async def search_blender_api(self, function_name: str) -> SearchResponse:
        """Search for Blender Python API documentation.

        Args:
            function_name: API function or class name.
        """
        return await self.search(f"Blender Python API bpy {function_name} documentation")
