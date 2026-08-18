"""
BlendPilot — Design Specification Schemas

Pydantic models for the structured design specification
produced by Workflow 1 (Design Intent Understanding).
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Dimensions(BaseModel):
    """Physical dimensions of the target asset in meters."""

    width: float = Field(..., gt=0, description="Width in meters (X axis)")
    depth: float = Field(..., gt=0, description="Depth in meters (Y axis)")
    height: float = Field(..., gt=0, description="Height in meters (Z axis)")


class DesignSpec(BaseModel):
    """Structured design specification parsed from a user's natural-language request.

    This is the contract between the Intent Agent and all downstream workflows.
    No modeling should begin until this specification exists.
    """

    asset_type: str = Field(
        ...,
        min_length=1,
        description="Type of asset, e.g. 'sci-fi crate', 'dining table'",
    )
    style: str = Field(
        default="low-poly",
        description="Visual style, e.g. 'low-poly', 'realistic', 'stylized'",
    )
    dimensions: Dimensions = Field(
        ...,
        description="Target dimensions in meters",
    )
    triangle_limit: int = Field(
        default=10_000,
        gt=0,
        description="Maximum triangle count for the final mesh",
    )
    target_platform: str = Field(
        default="Unity",
        description="Target game engine or platform",
    )
    materials: list[str] = Field(
        default_factory=list,
        description="Desired material descriptions, e.g. ['dark metal', 'blue emissive']",
    )
    export_format: str = Field(
        default="FBX",
        description="Primary export format: FBX, GLB, or OBJ",
    )
    description: str = Field(
        default="",
        description="Additional free-form design notes from the user",
    )
    reference_images: list[str] = Field(
        default_factory=list,
        description="Paths to reference images provided by the user",
    )
