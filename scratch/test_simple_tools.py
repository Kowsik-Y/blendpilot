"""
Test: Simple individual Blender tool calls through the real pipeline.
Verifies that field-name normalization in _execute_core_operation works correctly.
"""
import asyncio
import sys
sys.path.insert(0, r"c:\Users\babyv\OneDrive\Desktop\blendpilot-1")

from dotenv import load_dotenv
load_dotenv(r"c:\Users\babyv\OneDrive\Desktop\blendpilot-1\.env")

from agents.generation_agent import GenerationAgent
from schemas.plan_state import ModelingStep


async def run_test(label: str, op: str, target: str, params: dict) -> bool:
    """Run a single tool call and report result."""
    agent = GenerationAgent()
    step = ModelingStep(step_id=1, operation=op, target=target, parameters=params)
    try:
        result = await agent._execute_core_operation(step, "output/test/preview.png")
        success = result.get("success", False)
        msg = result.get("message", result.get("error", ""))
        status = "PASS" if success else "FAIL"
        print(f"[{status}] {label}")
        if not success:
            print(f"       Error: {msg}")
        return success
    except Exception as e:
        print(f"[FAIL] {label}")
        print(f"       Exception: {e}")
        return False


async def main():
    print("=" * 60)
    print("Simple Tool Call Tests")
    print("=" * 60)
    results = []

    # Test 1: create cube (with LLM-style 'type' field instead of 'primitive_type')
    results.append(await run_test(
        "create_primitive: cube (type->primitive_type fix)",
        "create_primitive", "test_cube",
        {"type": "cube", "name": "test_cube", "location": [0, 0, 0], "dimensions": [1, 1, 1]}
    ))

    # Test 2: create cylinder (correct primitive_type)
    results.append(await run_test(
        "create_primitive: cylinder (correct field name)",
        "create_primitive", "test_leg",
        {"primitive_type": "cylinder", "name": "test_leg", "location": [0.5, 0.5, 0.25], "dimensions": [0.1, 0.1, 0.5]}
    ))

    # Test 3: set_transform with LLM-style 'object_name' (should normalize to 'name')
    results.append(await run_test(
        "set_transform: using object_name->name fix",
        "set_transform", "test_cube",
        {"object_name": "test_cube", "location": [0, 0, 0.5]}
    ))

    # Test 4: create material
    results.append(await run_test(
        "create_material: red material",
        "create_material", "red_wood",
        {"name": "red_wood", "base_color": [0.9, 0.1, 0.1, 1.0], "roughness": 0.6, "metallic": 0.0}
    ))

    # Test 5: assign_material with 'material' instead of 'material_name'
    results.append(await run_test(
        "assign_material: material->material_name fix",
        "assign_material", "test_cube",
        {"object_name": "test_cube", "material": "red_wood"}
    ))

    print()
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} passed")
    print("=" * 60)
    return passed == total


if __name__ == "__main__":
    asyncio.run(main())
