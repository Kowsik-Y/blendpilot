"""
BlendPilot AI — Intent Agent Schemas
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field, field_validator, model_validator

SUPPORTED_CATEGORIES = {
    "table", "chair", "mug", "lamp", "stool", "bottle", "desk", "bookshelf", "bed", "box"
}


class IntentDimensions(BaseModel):
    """Extracted physical dimensions if explicitly provided."""
    width: float | None = None
    depth: float | None = None
    height: float | None = None


class IntentSpec(BaseModel):
    """Structured design intent extracted by the Intent Understanding Agent."""
    object_type: str = Field(..., description="Parsed category of the object")
    asset_type: str = Field(default="", description="Alias for object_type for backward compatibility")
    style: str = Field(default="low-poly", description="Visual style of the object")
    color: str | None = Field(default=None, description="Color name or hex code")
    material: str | None = Field(default=None, description="Primary material composition")
    required_components: list[str] = Field(default_factory=list, description="Extracted sub-parts or components")
    count: int = Field(default=1, description="Number of instances requested")
    dimensions: IntentDimensions | None = Field(default=None, description="Physical dimensions if explicitly provided")
    additional_constraints: list[str] = Field(default_factory=list, description="Other constraints or design rules")
    is_supported: bool = Field(default=True, description="Whether the object type is in the supported list")
    reference_images: list[str] = Field(default_factory=list, description="Reference image URLs or base64 strings")

    @model_validator(mode="before")
    @classmethod
    def populate_asset_and_object_types(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "object_type" not in data and "asset_type" in data:
                data["object_type"] = data["asset_type"]
            elif "asset_type" not in data and "object_type" in data:
                data["asset_type"] = data["object_type"]
        return data

    @field_validator("object_type")
    @classmethod
    def validate_object_type(cls, v: str) -> str:
        cleaned = v.strip().lower()
        # Clean plurals or common variants (simple heuristic)
        if cleaned.endswith("s") and cleaned[:-1] in SUPPORTED_CATEGORIES:
            cleaned = cleaned[:-1]
        return cleaned
