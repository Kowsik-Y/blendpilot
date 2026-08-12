"""
BlendPilot AI — Material Creation & Assignment

Functions for creating Principled BSDF materials and assigning them
to Blender objects.

Runs inside Blender's Python environment.
"""

from __future__ import annotations

import logging
from typing import Any

import bpy  # type: ignore[import-not-found]

logger = logging.getLogger("blendpilot.core.materials")


def create_material(
    name: str,
    base_color: tuple[float, float, float, float] = (0.8, 0.8, 0.8, 1.0),
    metallic: float = 0.0,
    roughness: float = 0.5,
    emission_color: tuple[float, float, float, float] | None = None,
    emission_strength: float = 0.0,
) -> dict[str, Any]:
    """Create a Principled BSDF material.

    Args:
        name: Material name.
        base_color: RGBA base color (0.0–1.0 per channel).
        metallic: Metallic factor (0.0–1.0).
        roughness: Roughness factor (0.0–1.0).
        emission_color: Optional RGBA emission color.
        emission_strength: Emission strength (0.0+).

    Returns:
        Dict with 'success', 'material_name', and 'message'.

    Raises:
        ValueError: If parameters are out of range.
    """
    if not name or not name.strip():
        raise ValueError("Material name cannot be empty.")

    if len(base_color) != 4:
        raise ValueError("base_color must be a tuple of 4 floats (RGBA).")
    if any(c < 0.0 or c > 1.0 for c in base_color):
        raise ValueError("base_color values must be between 0.0 and 1.0.")

    if not 0.0 <= metallic <= 1.0:
        raise ValueError(f"Metallic must be between 0.0 and 1.0, got {metallic}.")
    if not 0.0 <= roughness <= 1.0:
        raise ValueError(f"Roughness must be between 0.0 and 1.0, got {roughness}.")
    if emission_strength < 0.0:
        raise ValueError(f"Emission strength must be >= 0.0, got {emission_strength}.")

    if emission_color is not None:
        if len(emission_color) != 4:
            raise ValueError("emission_color must be a tuple of 4 floats (RGBA).")
        if any(c < 0.0 or c > 1.0 for c in emission_color):
            raise ValueError("emission_color values must be between 0.0 and 1.0.")

    # Check if material already exists — reuse it
    mat = bpy.data.materials.get(name)
    if mat is not None:
        logger.info("Material '%s' already exists — updating properties.", name)
    else:
        mat = bpy.data.materials.new(name=name)
        logger.info("Created new material '%s'.", name)

    mat.use_nodes = True
    nodes = mat.node_tree.nodes

    # Find or create the Principled BSDF node
    principled = None
    for node in nodes:
        if node.type == "BSDF_PRINCIPLED":
            principled = node
            break

    if principled is None:
        # Clear existing nodes and create fresh
        nodes.clear()
        principled = nodes.new("ShaderNodeBsdfPrincipled")
        output = nodes.new("ShaderNodeOutputMaterial")
        mat.node_tree.links.new(principled.outputs["BSDF"], output.inputs["Surface"])

    # Set material properties
    mat.diffuse_color = base_color
    principled.inputs["Base Color"].default_value = base_color
    principled.inputs["Metallic"].default_value = metallic
    principled.inputs["Roughness"].default_value = roughness

    # Set emission if provided
    if emission_color is not None:
        principled.inputs["Emission Color"].default_value = emission_color
        principled.inputs["Emission Strength"].default_value = emission_strength
    elif emission_strength > 0.0:
        # Use base color as emission color if only strength is provided
        principled.inputs["Emission Color"].default_value = base_color
        principled.inputs["Emission Strength"].default_value = emission_strength

    logger.info(
        "Material '%s': base=%s, metallic=%.2f, roughness=%.2f",
        mat.name, base_color, metallic, roughness,
    )
    return {
        "success": True,
        "material_name": mat.name,
        "message": f"Material '{mat.name}' created/updated.",
    }


def assign_material(
    object_name: str,
    material_name: str,
) -> dict[str, Any]:
    """Assign an existing material to an object.

    If the object already has material slots, the material is added
    to the next available slot. If the material is already assigned,
    no duplicate slot is created.

    Args:
        object_name: Name of the target object.
        material_name: Name of the material to assign.

    Returns:
        Dict with 'success' and 'message'.

    Raises:
        ValueError: If object or material not found.
    """
    if not object_name or not object_name.strip():
        raise ValueError("Object name cannot be empty.")
    if not material_name or not material_name.strip():
        raise ValueError("Material name cannot be empty.")

    obj = bpy.data.objects.get(object_name)
    if obj is None:
        raise ValueError(f"Object '{object_name}' not found in scene.")

    mat = bpy.data.materials.get(material_name)
    if mat is None:
        raise ValueError(f"Material '{material_name}' not found.")

    if obj.type != "MESH":
        raise ValueError(
            f"Object '{object_name}' is type '{obj.type}', not MESH. "
            "Materials can only be assigned to mesh objects."
        )

    # Check if material is already assigned
    for slot in obj.material_slots:
        if slot.material and slot.material.name == material_name:
            logger.info("Material '%s' already assigned to '%s'.", material_name, object_name)
            return {
                "success": True,
                "message": f"Material '{material_name}' already assigned to '{object_name}'.",
            }

    # Assign the material
    obj.data.materials.append(mat)

    logger.info("Assigned material '%s' to '%s'.", material_name, object_name)
    return {
        "success": True,
        "message": f"Assigned material '{material_name}' to '{object_name}'.",
    }
