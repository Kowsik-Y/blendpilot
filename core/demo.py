"""
BlendPilot AI — Demo: Low-Poly Red Table

End-to-end demonstration of Phase 1 capabilities:
1. Create a tabletop (scaled cube)
2. Create four legs (scaled cubes)
3. Create and assign a red material
4. Add bevel modifiers
5. Set up camera and studio lighting
6. Render a preview image
7. Save the .blend file
8. Export as FBX

Run this script inside Blender's Python console or via command line:
    blender --python -m blendpilot.core.demo

Or call create_red_table() from Blender's scripting workspace.
"""

from __future__ import annotations

import logging
import os
import sys

logger = logging.getLogger("blendpilot.core.demo")


def create_red_table(
    output_dir: str = "./output/red_table",
    table_width: float = 1.2,
    table_depth: float = 0.8,
    table_height: float = 0.75,
    top_thickness: float = 0.05,
    leg_thickness: float = 0.06,
    render_preview: bool = True,
) -> dict:
    """Create a complete low-poly red table with four legs.

    This demonstrates the full Phase 1 pipeline:
    - Object creation
    - Transform manipulation
    - Modifier addition
    - Material creation & assignment
    - Camera & lighting setup
    - Rendering
    - Project save
    - FBX export

    Args:
        output_dir: Directory for output files.
        table_width: Table width in meters (X axis).
        table_depth: Table depth in meters (Y axis).
        table_height: Total table height in meters.
        top_thickness: Thickness of the tabletop.
        leg_thickness: Width/depth of each leg.
        render_preview: Whether to render a preview image.

    Returns:
        Dict with results from each step.
    """
    import bpy  # type: ignore[import-not-found]

    try:
        from core.materials import assign_material, create_material
        from core.modifiers import add_modifier
        from core.objects import create_primitive, delete_object
        from core.project import export_asset, save_project
        from core.rendering import (
            render_preview as do_render,
            setup_preview_camera,
            setup_studio_lighting,
        )
    except ImportError:
        from blendpilot.core.materials import assign_material, create_material
        from blendpilot.core.modifiers import add_modifier
        from blendpilot.core.objects import create_primitive, delete_object
        from blendpilot.core.project import export_asset, save_project
        from blendpilot.core.rendering import (
            render_preview as do_render,
            setup_preview_camera,
            setup_studio_lighting,
        )

    results: dict = {"steps": []}
    os.makedirs(output_dir, exist_ok=True)

    logger.info("=" * 60)
    logger.info("BlendPilot Demo: Creating Low-Poly Red Table")
    logger.info("=" * 60)

    # --- Step 0: Clean the scene ---
    logger.info("Step 0: Cleaning default scene...")
    # Delete default objects
    for obj_name in list(bpy.data.objects.keys()):
        try:
            delete_object(obj_name)
        except ValueError:
            pass  # Object may have already been removed
    results["steps"].append({"step": "clean_scene", "status": "done"})

    # --- Step 1: Create tabletop ---
    logger.info("Step 1: Creating tabletop...")
    top_z = table_height - (top_thickness / 2)
    result = create_primitive(
        primitive_type="cube",
        name="TableTop",
        dimensions=(table_width, table_depth, top_thickness),
        location=(0.0, 0.0, top_z),
    )
    results["steps"].append({"step": "create_tabletop", **result})

    # --- Step 2: Create four legs ---
    logger.info("Step 2: Creating table legs...")
    leg_height = table_height - top_thickness
    leg_z = leg_height / 2

    # Inset from edges
    inset_x = (table_width / 2) - (leg_thickness / 2) - 0.03
    inset_y = (table_depth / 2) - (leg_thickness / 2) - 0.03

    leg_positions = [
        ("LegFrontLeft",  (-inset_x, -inset_y, leg_z)),
        ("LegFrontRight", ( inset_x, -inset_y, leg_z)),
        ("LegBackLeft",   (-inset_x,  inset_y, leg_z)),
        ("LegBackRight",  ( inset_x,  inset_y, leg_z)),
    ]

    leg_names = []
    for leg_name, position in leg_positions:
        result = create_primitive(
            primitive_type="cube",
            name=leg_name,
            dimensions=(leg_thickness, leg_thickness, leg_height),
            location=position,
        )
        leg_names.append(result["object_name"])
        results["steps"].append({"step": f"create_{leg_name}", **result})

    # --- Step 3: Add bevel modifiers ---
    logger.info("Step 3: Adding bevel modifiers...")
    all_parts = ["TableTop"] + leg_names
    for part in all_parts:
        result = add_modifier(
            object_name=part,
            modifier_type="bevel",
            params={"width": 0.008, "segments": 2},
        )
        results["steps"].append({"step": f"bevel_{part}", **result})

    # --- Step 4: Create red material ---
    logger.info("Step 4: Creating red material...")
    result = create_material(
        name="RedTableMaterial",
        base_color=(0.8, 0.1, 0.1, 1.0),  # Rich red
        metallic=0.0,
        roughness=0.4,
    )
    results["steps"].append({"step": "create_material", **result})

    # --- Step 5: Assign material to all parts ---
    logger.info("Step 5: Assigning material...")
    for part in all_parts:
        result = assign_material(
            object_name=part,
            material_name="RedTableMaterial",
        )
        results["steps"].append({"step": f"assign_material_{part}", **result})

    # --- Step 6: Set up camera ---
    logger.info("Step 6: Setting up camera...")
    result = setup_preview_camera(
        target=(0.0, 0.0, table_height / 2),
        distance=3.0,
        elevation_angle=25.0,
        azimuth_angle=35.0,
    )
    results["steps"].append({"step": "setup_camera", **result})

    # --- Step 7: Set up studio lighting ---
    logger.info("Step 7: Setting up studio lighting...")
    result = setup_studio_lighting(
        target=(0.0, 0.0, table_height / 2),
    )
    results["steps"].append({"step": "setup_lighting", **result})

    # --- Step 8: Render preview ---
    if render_preview:
        logger.info("Step 8: Rendering preview...")
        preview_path = os.path.join(output_dir, "preview.png")
        result = do_render(
            output_path=preview_path,
            resolution_x=1920,
            resolution_y=1080,
            samples=64,
        )
        results["steps"].append({"step": "render_preview", **result})
    else:
        results["steps"].append({"step": "render_preview", "skipped": True})

    # --- Step 9: Save .blend file ---
    logger.info("Step 9: Saving .blend file...")
    blend_path = os.path.join(output_dir, "red_table.blend")
    result = save_project(blend_path)
    results["steps"].append({"step": "save_project", **result})

    # --- Step 10: Export FBX ---
    logger.info("Step 10: Exporting FBX...")
    fbx_path = os.path.join(output_dir, "red_table.fbx")
    result = export_asset(
        object_names=all_parts,
        export_format="FBX",
        output_path=fbx_path,
    )
    results["steps"].append({"step": "export_fbx", **result})

    # --- Summary ---
    logger.info("=" * 60)
    logger.info("Demo complete!")
    logger.info("  Objects created: %d (1 tabletop + 4 legs)", len(all_parts))
    logger.info("  Output directory: %s", os.path.abspath(output_dir))
    logger.info("=" * 60)

    results["summary"] = {
        "total_objects": len(all_parts),
        "object_names": all_parts,
        "output_dir": os.path.abspath(output_dir),
        "success": True,
    }

    return results


# Allow running as a Blender script
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(name)s — %(message)s")

    # Parse optional output dir from command args
    out_dir = "./output/red_table"
    if "--" in sys.argv:
        args = sys.argv[sys.argv.index("--") + 1:]
        if args:
            out_dir = args[0]

    result = create_red_table(output_dir=out_dir)

    # Print summary
    print("\n✅ Demo Results:")
    for step in result["steps"]:
        status = "✓" if step.get("success", step.get("skipped", False)) else "✗"
        print(f"  {status} {step['step']}")
