"""
BlendPilot — Checkpoint Manager

Manages state persistence for long-running workflows with:
- 30-second checkpoint intervals
- SHA256 hash verification for integrity
- Automatic cleanup (keeps most recent 10 checkpoints)
- Resume support under 5 seconds
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("blendpilot.services.checkpoint")

DEFAULT_CHECKPOINT_DIR = "/tmp/blendpilot/checkpoints"
DEFAULT_MAX_CHECKPOINTS = 10
DEFAULT_CHECKPOINT_INTERVAL = 30  # seconds


@dataclass
class Checkpoint:
    """Represents a workflow checkpoint."""
    session_id: str
    sequence: int
    created_at: datetime
    workflow_state: Dict[str, Any]
    blender_state: Optional[Dict[str, Any]]
    hash: str  # SHA256 of workflow_state
    path: str

    def verify(self) -> bool:
        """Verify checkpoint integrity using SHA256 hash."""
        with open(self.path, 'r') as f:
            data = json.load(f)
        computed_hash = hashlib.sha256(
            json.dumps(data.get("workflow_state", {}), sort_keys=True).encode()
        ).hexdigest()
        return computed_hash == self.hash

    def to_dict(self) -> Dict[str, Any]:
        """Convert checkpoint to dictionary."""
        return {
            "session_id": self.session_id,
            "sequence": self.sequence,
            "created_at": self.created_at.isoformat(),
            "workflow_state": self.workflow_state,
            "blender_state": self.blender_state,
            "hash": self.hash,
            "path": self.path,
        }


class CheckpointManager:
    """
    Manages workflow checkpoints with persistence and integrity verification.

    Features:
    - Checkpoints every 30 seconds by default
    - SHA256 hash verification for integrity
    - Automatic cleanup (keeps most recent 10 checkpoints)
    - Fast resume from checkpoint (<5 seconds)
    """

    def __init__(
        self,
        storage_path: str = DEFAULT_CHECKPOINT_DIR,
        max_checkpoints: int = DEFAULT_MAX_CHECKPOINTS,
        checkpoint_interval: int = DEFAULT_CHECKPOINT_INTERVAL,
    ):
        self.storage_path = Path(storage_path)
        self.max_checkpoints = max_checkpoints
        self.checkpoint_interval = checkpoint_interval

        # Create storage directory if it doesn't exist
        self.storage_path.mkdir(parents=True, exist_ok=True)

        self._last_checkpoint_time: Dict[str, float] = {}
        self._sequence_counter: Dict[str, int] = {}

    async def should_checkpoint(self, session_id: str) -> bool:
        """Check if a checkpoint should be created for this session."""
        last_time = self._last_checkpoint_time.get(session_id, 0)
        return (time.monotonic() - last_time) >= self.checkpoint_interval

    async def create_checkpoint(
        self,
        session_id: str,
        workflow_state: Dict[str, Any],
        blender_state: Optional[Dict[str, Any]] = None,
    ) -> Checkpoint:
        """Create a new checkpoint for the session."""
        # Update sequence counter
        self._sequence_counter[session_id] = self._sequence_counter.get(
            session_id, 0) + 1
        sequence = self._sequence_counter[session_id]

        # Compute hash for integrity verification
        state_to_hash = json.dumps(workflow_state, sort_keys=True).encode()
        hash_value = hashlib.sha256(state_to_hash).hexdigest()

        # Create checkpoint data
        checkpoint_data = {
            "session_id": session_id,
            "sequence": sequence,
            "created_at": datetime.utcnow().isoformat(),
            "workflow_state": workflow_state,
            "blender_state": blender_state,
            "hash": hash_value,
        }

        # Save to file
        checkpoint_filename = f"checkpoint_{session_id}_{sequence}.json"
        checkpoint_path = self.storage_path / checkpoint_filename

        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint_data, f, indent=2)

        # Update last checkpoint time
        self._last_checkpoint_time[session_id] = time.monotonic()

        # Cleanup old checkpoints
        await self._cleanup_old_checkpoints(session_id)

        logger.info(
            "Created checkpoint %d for session %s at %s",
            sequence, session_id, checkpoint_path
        )

        return Checkpoint(
            session_id=session_id,
            sequence=sequence,
            created_at=datetime.utcnow(),
            workflow_state=workflow_state,
            blender_state=blender_state,
            hash=hash_value,
            path=str(checkpoint_path),
        )

    async def resume_from_checkpoint(
        self,
        checkpoint: Checkpoint,
    ) -> Dict[str, Any]:
        """Resume workflow state from a checkpoint."""
        start_time = time.monotonic()

        # Verify integrity
        if not checkpoint.verify():
            raise ValueError(
                f"Checkpoint integrity check failed: {checkpoint.path}")

        # Load state
        with open(checkpoint.path, 'r') as f:
            data = json.load(f)

        elapsed = time.monotonic() - start_time

        if elapsed > 5.0:
            logger.warning(
                "Checkpoint resume took %.2f seconds (expected <5s)",
                elapsed,
            )

        logger.info(
            "Resumed from checkpoint %d for session %s in %.2fs",
            checkpoint.sequence,
            checkpoint.session_id,
            elapsed,
        )

        return data.get("workflow_state", {})

    async def _cleanup_old_checkpoints(self, session_id: str) -> None:
        """Remove old checkpoints, keeping only the most recent N."""
        checkpoint_files = list(
            self.storage_path.glob(f"checkpoint_{session_id}_*.json")
        )

        if len(checkpoint_files) <= self.max_checkpoints:
            return

        # Sort by modification time (newest first)
        checkpoint_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        # Remove old checkpoints
        for old_file in checkpoint_files[self.max_checkpoints:]:
            try:
                old_file.unlink()
                logger.info("Removed old checkpoint: %s", old_file)
            except Exception as e:
                logger.warning(
                    "Failed to remove checkpoint %s: %s", old_file, e)

    async def get_latest_checkpoint(
        self,
        session_id: str,
    ) -> Optional[Checkpoint]:
        """Get the most recent checkpoint for a session."""
        checkpoint_files = list(
            self.storage_path.glob(f"checkpoint_{session_id}_*.json")
        )

        if not checkpoint_files:
            return None

        # Get newest file
        newest_file = max(checkpoint_files, key=lambda p: p.stat().st_mtime)

        # Load checkpoint metadata
        with open(newest_file, 'r') as f:
            data = json.load(f)

        return Checkpoint(
            session_id=data["session_id"],
            sequence=data["sequence"],
            created_at=datetime.fromisoformat(data["created_at"]),
            workflow_state=data["workflow_state"],
            blender_state=data.get("blender_state"),
            hash=data["hash"],
            path=str(newest_file),
        )

    async def cleanup_all_checkpoints(self) -> int:
        """Remove all checkpoints and return count deleted."""
        deleted = 0
        for checkpoint_file in self.storage_path.glob("checkpoint_*.json"):
            try:
                checkpoint_file.unlink()
                deleted += 1
            except Exception as e:
                logger.warning("Failed to delete %s: %s", checkpoint_file, e)

        logger.info("Deleted %d checkpoints", deleted)
        return deleted

    def get_checkpoint_dir(self) -> Path:
        """Return the checkpoint storage directory."""
        return self.storage_path
