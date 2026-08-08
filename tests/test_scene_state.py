"""
BlendPilot AI — Stage 3: Scene State Tests

Tests for Pydantic models in schemas/scene_state.py and the deterministic
scene inspector in core/scene_inspector.py.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock
import pytest

from schemas.scene_state import (
    Vec3,
    ObjectState,
    MaterialState,
    CameraState,
    LightState,
    ModifierState,
    SceneState,
)

# Remove top-level import of inspect_scene to avoid import errors during pytest collection.


def test_vec3_methods():
    v = Vec3(x=1.0, y=2.0, z=3.0)
    assert v.as_tuple() == (1.0, 2.0, 3.0)
    v2 = Vec3.from_tuple([4.0, 5.0, 6.0])
    assert v2.x == 4.0
    assert v2.y == 5.0
    assert v2.z == 6.0


def test_object_state_serialization():
    obj = ObjectState(
        name="TestCube",
        type="MESH",
        location=Vec3(x=1.0, y=2.0, z=3.0),
        status="active",
    )
    serialized = obj.model_dump_json()
    data = json.loads(serialized)
    assert data["name"] == "TestCube"
    assert data["location"]["x"] == 1.0
    assert len(data["id"]) == 12


def test_scene_state_serialization():
    state = SceneState(
        user_prompt="Create a low-poly crate",
        objects=[
            ObjectState(name="Crate", type="MESH"),
        ],
        materials=[
            MaterialState(name="DarkMetal", metallic=0.9),
        ],
    )
    serialized = state.model_dump_json()
    data = json.loads(serialized)
    assert data["user_prompt"] == "Create a low-poly crate"
    assert len(data["objects"]) == 1
    assert data["objects"][0]["name"] == "Crate"
    assert data["materials"][0]["name"] == "DarkMetal"
    assert data["materials"][0]["metallic"] == 0.9


def test_deterministic_inspection(mock_bpy):
    from core.scene_inspector import inspect_scene
    from tests.conftest import MockBlenderObject

    # Ensure there is exactly 1 default mock object (DefaultCube) in mock_bpy
    assert "DefaultCube" in mock_bpy._test_objects

    # Add a custom object to test parent hierarchy and materials
    child = MockBlenderObject("ChildCube", "MESH")
    child.parent = mock_bpy._test_objects["DefaultCube"]
    
    # Assign material to child object
    mat = mock_bpy.data.materials.new("RedMat")
    slot = MagicMock()
    slot.material = mat
    child.material_slots = [slot]

    # Add modifier
    child.modifiers.new("BevelModifier", "BEVEL")

    # Add a Light object
    light = MockBlenderObject("SunLight", "LIGHT")
    light_data = MagicMock()
    light_data.type = "SUN"
    light_data.energy = 100.0
    light.data = light_data
    
    # Active camera setup
    camera = MockBlenderObject("ActiveCamera", "CAMERA")
    
    # Register objects to test mock_bpy
    mock_bpy._test_register_object(child)
    mock_bpy._test_register_object(light)
    mock_bpy._test_register_object(camera)
    mock_bpy.context.scene.camera = camera
    
    # Set mock_bpy active lists
    mock_bpy.context.scene.objects = list(mock_bpy._test_objects.values())

    # Inspect the scene
    state = inspect_scene(user_prompt="Inspect scene test")

    # Assertions
    assert state.user_prompt == "Inspect scene test"
    assert state.status == "generated"
    assert len(state.objects) == 4  # DefaultCube, ChildCube, SunLight, ActiveCamera
    
    # Validate specific object properties
    child_state = next(o for o in state.objects if o.name == "ChildCube")
    assert child_state.parent == "DefaultCube"
    assert child_state.material == "RedMat"
    assert len(child_state.modifiers) == 1
    assert child_state.modifiers[0].name == "BevelModifier"

    # Validate active camera
    assert state.camera is not None
    assert state.camera.name == "ActiveCamera"

    # Validate lighting
    assert len(state.lighting) == 1
    assert state.lighting[0].name == "SunLight"
    assert state.lighting[0].energy == 100.0

    # Validate materials list
    assert any(m.name == "RedMat" for m in state.materials)
