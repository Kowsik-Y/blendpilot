"""
BlendPilot AI — Blender MCP Server Pydantic Schemas

Validates inputs for all exposed MCP tools before execution.
"""

from pydantic import BaseModel, Field
from typing import Literal

# 1. Scene Tools
class GetSceneSummarySchema(BaseModel):
    include_mesh_stats: bool = Field(default=True, description="Whether to compute heavy vertex/poly stats")

class GetObjectDetailsSchema(BaseModel):
    name: str = Field(..., description="Object name")

class GetMeshStatisticsSchema(BaseModel):
    name: str = Field(..., description="Mesh object name")

# 2. Object Tools
class CreatePrimitiveSchema(BaseModel):
    primitive_type: Literal["cube", "cylinder", "uv_sphere", "ico_sphere", "plane", "cone", "torus"] = Field(...)
    name: str = Field(..., description="Unique object name")
    dimensions: list[float] | None = Field(default=None, description="[width, depth, height]")
    location: list[float] | None = Field(default=None, description="[x, y, z]")
    rotation: list[float] | None = Field(default=None, description="[rx, ry, rz] in radians")

class SetTransformSchema(BaseModel):
    name: str = Field(..., description="Target object name")
    location: list[float] | None = Field(default=None)
    rotation: list[float] | None = Field(default=None)
    scale: list[float] | None = Field(default=None)

class DuplicateObjectSchema(BaseModel):
    name: str = Field(..., description="Source object name")
    new_name: str | None = Field(default=None, description="Name for duplicate")
    offset: list[float] | None = Field(default=None)

class DeleteObjectSchema(BaseModel):
    name: str = Field(..., description="Object to delete")

# 3. Modeling Tools
class AddModifierSchema(BaseModel):
    object_name: str = Field(..., description="Target object name")
    modifier_type: Literal["BEVEL", "SUBSURF", "SOLIDIFY", "MIRROR", "BOOLEAN", "DECIMATE", "EDGE_SPLIT"] = Field(...)
    modifier_name: str | None = Field(default=None)
    properties: dict | None = Field(default=None, description="Modifier properties")

class ApplyModifierSchema(BaseModel):
    object_name: str = Field(...)
    modifier_name: str = Field(...)

class EditMeshSchema(BaseModel):
    object_name: str = Field(...)
    operation: str = Field(...)
    parameters: dict | None = Field(default=None)

# 4. Material Tools
class CreateMaterialSchema(BaseModel):
    name: str = Field(..., description="Material name")
    base_color: list[float] | None = Field(default=None, description="[R, G, B, A]")
    metallic: float | None = Field(default=None, ge=0.0, le=1.0)
    roughness: float | None = Field(default=None, ge=0.0, le=1.0)
    emission_color: list[float] | None = Field(default=None)
    emission_strength: float | None = Field(default=None, ge=0.0)

class AssignMaterialSchema(BaseModel):
    object_name: str = Field(...)
    material_name: str = Field(...)
    slot_index: int | None = Field(default=None, ge=0)

# 5. Validation Tools
class ValidateAssetSchema(BaseModel):
    object_name: str = Field(...)
    triangle_limit: int = Field(default=8000)
    target_engine: str = Field(default="Unity")

class CheckNonManifoldSchema(BaseModel):
    object_name: str = Field(...)

class CheckNormalsSchema(BaseModel):
    object_name: str = Field(...)

class CheckTriangleCountSchema(BaseModel):
    object_name: str = Field(...)
    max_triangles: int = Field(default=8000)

# 6. Rendering Tools
class SetupPreviewCameraSchema(BaseModel):
    target_object: str | None = Field(default=None)
    distance: float = Field(default=3.5)
    focal_length: float = Field(default=50.0)

class SetupStudioLightingSchema(BaseModel):
    key_energy: float = Field(default=1000.0)
    fill_energy: float = Field(default=400.0)
    rim_energy: float = Field(default=600.0)

class RenderPreviewSchema(BaseModel):
    output_path: str = Field(...)
    resolution_x: int = Field(default=1024)
    resolution_y: int = Field(default=1024)
    samples: int = Field(default=64)

# 7. Project Tools
class SaveCheckpointSchema(BaseModel):
    filepath: str = Field(...)
    checkpoint_name: str | None = Field(default=None)

class RestoreCheckpointSchema(BaseModel):
    filepath: str = Field(...)

class SaveProjectSchema(BaseModel):
    filepath: str = Field(...)

class ExportAssetSchema(BaseModel):
    object_names: list[str] = Field(...)
    output_path: str = Field(...)
    format: Literal["FBX", "GLB", "OBJ"] = Field(default="FBX")
    apply_modifiers: bool = Field(default=True)
