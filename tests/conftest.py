"""
BlendPilot — Test Configuration & Shared Fixtures

Provides a comprehensive bpy mock so core module tests can run
outside of Blender's Python environment.
"""

from __future__ import annotations

import sys
from types import ModuleType
from unittest.mock import MagicMock, PropertyMock

import pytest


class MockVector:
    """Minimal mathutils.Vector mock for tests."""

    def __init__(self, values=(0.0, 0.0, 0.0)):
        self._values = list(values)

    def __iter__(self):
        return iter(self._values)

    def __getitem__(self, index):
        return self._values[index]

    def __len__(self):
        return len(self._values)

    @property
    def x(self):
        return self._values[0]

    @property
    def y(self):
        return self._values[1]

    @property
    def z(self):
        return self._values[2]

    @property
    def length(self):
        return sum(v**2 for v in self._values) ** 0.5

    def dot(self, other):
        return sum(a * b for a, b in zip(self._values, other._values if hasattr(other, '_values') else other))

    def to_track_quat(self, *args):
        mock_quat = MagicMock()
        mock_quat.to_euler.return_value = (0.0, 0.0, 0.0)
        return mock_quat


class MockBlenderObject:
    """Mock of a Blender object for testing."""

    def __init__(self, name="Object", obj_type="MESH"):
        self.name = name
        self.type = obj_type
        self.location = MockVector((0.0, 0.0, 0.0))
        self.rotation_euler = MockVector((0.0, 0.0, 0.0))
        self.scale = MockVector((1.0, 1.0, 1.0))
        self.dimensions = MockVector((1.0, 1.0, 1.0))
        self.parent = None
        self.modifiers = MockModifierCollection()
        self.material_slots = []
        self.constraints = []
        self.data = MockMeshData()
        self._visible = True

    def visible_get(self):
        return self._visible

    def select_set(self, state):
        pass

    @property
    def users_collection(self):
        mock_col = MagicMock()
        mock_col.name = "Collection"
        return [mock_col]


class MockModifierCollection:
    """Mock of obj.modifiers."""

    def __init__(self):
        self._modifiers = {}

    def new(self, name, type):
        mod = MagicMock()
        mod.name = name
        mod.type = type
        mod.show_viewport = True
        mod.show_render = True
        self._modifiers[name] = mod
        return mod

    def get(self, name):
        return self._modifiers.get(name)

    def __iter__(self):
        return iter(self._modifiers.values())

    def __bool__(self):
        return bool(self._modifiers)

    def __len__(self):
        return len(self._modifiers)


class MockMeshData:
    """Mock of obj.data (mesh)."""

    def __init__(self):
        self.vertices = [MagicMock() for _ in range(8)]
        self.edges = [MagicMock() for _ in range(12)]
        self.polygons = [MagicMock() for _ in range(6)]
        self.uv_layers = []
        self.materials = MockMaterialList()


class MockMaterialList:
    """Mock of mesh.materials."""

    def __init__(self):
        self._materials = []

    def append(self, mat):
        self._materials.append(mat)

    def __iter__(self):
        return iter(self._materials)

    def __len__(self):
        return len(self._materials)


def create_mock_bpy():
    """Create a comprehensive bpy mock module."""
    bpy = MagicMock(spec=[])

    # --- bpy.data ---
    objects_dict = {}
    materials_dict = {}

    bpy.data = MagicMock()
    bpy.data.objects = MagicMock()
    bpy.data.objects.get = lambda name: objects_dict.get(name)
    bpy.data.objects.keys = lambda: list(objects_dict.keys())
    bpy.data.objects.__getitem__ = lambda _, name: objects_dict[name]
    bpy.data.objects.__contains__ = lambda _, name: name in objects_dict

    bpy.data.materials = MagicMock()
    bpy.data.materials.get = lambda name: materials_dict.get(name)
    bpy.data.materials.__getitem__ = lambda _, name: materials_dict[name]

    def new_material(name):
        mat = MagicMock()
        mat.name = name
        mat.use_nodes = False
        mat.node_tree = MagicMock()
        mat.node_tree.nodes = MockNodeCollection()
        materials_dict[name] = mat
        return mat

    bpy.data.materials.new = new_material

    bpy.data.cameras = MagicMock()
    bpy.data.cameras.new = lambda name: MagicMock(name=name)

    bpy.data.lights = MagicMock()
    bpy.data.lights.new = lambda name, type: MagicMock(name=name, type=type)

    bpy.data.collections = []
    bpy.data.filepath = ""

    # --- bpy.context ---
    active_obj = MockBlenderObject("DefaultCube")
    objects_dict["DefaultCube"] = active_obj

    bpy.context = MagicMock()
    bpy.context.active_object = active_obj
    bpy.context.view_layer.objects.active = active_obj

    scene = MagicMock()
    scene.objects = list(objects_dict.values())
    scene.camera = None
    scene.frame_current = 1
    scene.render.engine = "BLENDER_EEVEE"
    scene.collection.objects.link = MagicMock()
    bpy.context.scene = scene

    # --- bpy.ops ---
    bpy.ops = MagicMock()
    bpy.ops.object.select_all = MagicMock()
    bpy.ops.object.delete = MagicMock()
    bpy.ops.object.duplicate = MagicMock()
    bpy.ops.object.modifier_apply = MagicMock()
    bpy.ops.render.render = MagicMock()
    bpy.ops.wm.save_as_mainfile = MagicMock()
    bpy.ops.wm.open_mainfile = MagicMock()
    bpy.ops.export_scene.fbx = MagicMock()
    bpy.ops.export_scene.gltf = MagicMock()

    # Primitive creation operators
    for prim in ["cube", "uv_sphere", "cylinder", "plane", "cone", "torus", "ico_sphere"]:
        op = getattr(bpy.ops.mesh, f"primitive_{prim}_add")
        op.return_value = {"FINISHED"}

    # Helper to register a new object in the mock
    def _register_object(obj):
        objects_dict[obj.name] = obj
        bpy.context.active_object = obj
        bpy.context.view_layer.objects.active = obj
        scene.objects = list(objects_dict.values())

    def _remove_object(name):
        if name in objects_dict:
            del objects_dict[name]
            scene.objects = list(objects_dict.values())

    bpy._test_register_object = _register_object
    bpy._test_remove_object = _remove_object
    bpy._test_objects = objects_dict
    bpy._test_materials = materials_dict

    return bpy


class MockNodeCollection:
    """Mock of node_tree.nodes."""

    def __init__(self):
        self._nodes = []

    def new(self, node_type):
        node = MagicMock()
        node.type = node_type.replace("ShaderNode", "").upper()
        if "PRINCIPLED" in node_type.upper() or "BSDF" in node_type.upper():
            node.type = "BSDF_PRINCIPLED"
        inputs = {}
        for input_name in [
            "Base Color", "Metallic", "Roughness",
            "Emission Color", "Emission Strength",
            "Surface", "BSDF",
        ]:
            mock_input = MagicMock()
            mock_input.default_value = (
                0.8, 0.8, 0.8, 1.0) if "Color" in input_name else 0.0
            inputs[input_name] = mock_input
        node.inputs = inputs
        node.outputs = inputs  # simplified
        self._nodes.append(node)
        return node

    def clear(self):
        self._nodes.clear()

    def __iter__(self):
        return iter(self._nodes)


@pytest.fixture(autouse=True)
def mock_bpy():
    """Automatically inject a mock bpy module for all tests.

    This fixture ensures that `import bpy` works outside Blender
    and provides a controllable mock environment.
    """
    mock = create_mock_bpy()

    # Also mock mathutils and bmesh
    mathutils_mock = ModuleType("mathutils")
    mathutils_mock.Vector = MockVector  # type: ignore[attr-defined]

    bmesh_mock = MagicMock()

    # Install mocks
    sys.modules["bpy"] = mock
    sys.modules["mathutils"] = mathutils_mock
    sys.modules["bmesh"] = bmesh_mock

    yield mock

    # Cleanup
    sys.modules.pop("bpy", None)
    sys.modules.pop("mathutils", None)
    sys.modules.pop("bmesh", None)
