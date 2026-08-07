"""
BlendPilot AI — File & Directory Manager

Manages project directories, output files, checkpoints,
and asset report generation.

Phase: 3 (interface defined)
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger("blendpilot.services.file_manager")


class FileManager:
    """Manages BlendPilot project files and directories.

    Creates and organizes the output directory structure for each project:

    output/
        {project_id}/
            checkpoints/          # .blend checkpoints
            renders/              # Preview render images
            exports/              # FBX, GLB exports
            asset_report.json     # Final asset metadata

    Usage:
        fm = FileManager(base_output_dir="./output")
        project_dir = fm.create_project_directory("sci_fi_crate_001")
        checkpoint = fm.get_checkpoint_path("sci_fi_crate_001", "blockout")
        # → "./output/sci_fi_crate_001/checkpoints/blockout.blend"
    """

    def __init__(self, base_output_dir: str = "./output"):
        self.base_output_dir = Path(base_output_dir)

    def create_project_directory(self, project_id: str) -> Path:
        """Create the full output directory structure for a project.

        Args:
            project_id: Unique identifier for the project (used as folder name).

        Returns:
            Path to the project root directory.
        """
        project_dir = self.base_output_dir / project_id

        subdirs = ["checkpoints", "renders", "exports"]
        for subdir in subdirs:
            (project_dir / subdir).mkdir(parents=True, exist_ok=True)

        logger.info("Created project directory: %s", project_dir)
        return project_dir

    def get_project_dir(self, project_id: str) -> Path:
        """Get the path to a project's root directory."""
        return self.base_output_dir / project_id

    def get_checkpoint_path(self, project_id: str, checkpoint_name: str) -> str:
        """Get the full path for a checkpoint .blend file.

        Args:
            project_id: Project identifier.
            checkpoint_name: Checkpoint name (e.g., "blockout", "final").

        Returns:
            Absolute path string for the checkpoint file.
        """
        path = self.base_output_dir / project_id / "checkpoints" / f"{checkpoint_name}.blend"
        return str(path.resolve())

    def get_render_path(self, project_id: str, render_name: str) -> str:
        """Get the full path for a render output image.

        Args:
            project_id: Project identifier.
            render_name: Render name (e.g., "preview", "final_render").

        Returns:
            Absolute path string for the render file.
        """
        path = self.base_output_dir / project_id / "renders" / f"{render_name}.png"
        return str(path.resolve())

    def get_export_path(self, project_id: str, asset_name: str, fmt: str = "fbx") -> str:
        """Get the full path for an export file.

        Args:
            project_id: Project identifier.
            asset_name: Asset filename (without extension).
            fmt: Export format — "fbx", "glb", or "blend".

        Returns:
            Absolute path string for the export file.
        """
        path = self.base_output_dir / project_id / "exports" / f"{asset_name}.{fmt}"
        return str(path.resolve())

    def generate_asset_report(
        self,
        project_id: str,
        metadata: dict[str, Any],
    ) -> str:
        """Write an asset_report.json file for the project.

        The report includes:
        - Design specification
        - Validation results
        - Export paths
        - Creation timestamp
        - Agent run metadata

        Args:
            project_id: Project identifier.
            metadata: Dict containing all asset metadata.

        Returns:
            Path to the written report file.
        """
        report = {
            "project_id": project_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "blendpilot_version": "0.1.0",
            **metadata,
        }

        report_path = self.base_output_dir / project_id / "asset_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, default=str))

        logger.info("Asset report written: %s", report_path)
        return str(report_path.resolve())

    def list_projects(self) -> list[dict[str, Any]]:
        """List all project directories with basic metadata.

        Returns:
            List of dicts with project_id, path, and contents summary.
        """
        projects = []
        if not self.base_output_dir.exists():
            return projects

        for item in sorted(self.base_output_dir.iterdir()):
            if item.is_dir() and not item.name.startswith("."):
                project_info: dict[str, Any] = {
                    "project_id": item.name,
                    "path": str(item.resolve()),
                    "has_checkpoints": (item / "checkpoints").exists()
                                       and any((item / "checkpoints").iterdir()),
                    "has_renders": (item / "renders").exists()
                                   and any((item / "renders").iterdir()),
                    "has_exports": (item / "exports").exists()
                                   and any((item / "exports").iterdir()),
                    "has_report": (item / "asset_report.json").exists(),
                }
                projects.append(project_info)

        return projects

    def cleanup_project(self, project_id: str) -> bool:
        """Delete a project's output directory.

        Args:
            project_id: Project to delete.

        Returns:
            True if deleted, False if not found.
        """
        project_dir = self.base_output_dir / project_id
        if not project_dir.exists():
            logger.warning("Project directory not found: %s", project_dir)
            return False

        import shutil
        shutil.rmtree(project_dir)
        logger.info("Deleted project directory: %s", project_dir)
        return True
