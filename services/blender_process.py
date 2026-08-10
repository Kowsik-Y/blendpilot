"""
BlendPilot AI — Blender Process Manager

Manages the lifecycle of a real Blender background process.
"""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import time
from typing import Optional
import httpx

from backend.config import settings

logger = logging.getLogger("blendpilot.services.blender_process")

class BlenderProcessManager:
    _instance: Optional["BlenderProcessManager"] = None
    
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.log_file = None
        self.is_running = False

    @classmethod
    def get_instance(cls) -> "BlenderProcessManager":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def start(self) -> None:
        """Start the Blender process if configured."""
        if not settings.require_real_blender:
            logger.info("Real Blender is not required (no executable configured).")
            return

        if self.is_running or self.process is not None:
            logger.info("Blender process is already running.")
            return

        exe_path = settings.blender_executable
        if not os.path.exists(exe_path) and not exe_path.lower().endswith("blender"):
            # Check if it's an absolute path that doesn't exist (allow just 'blender' in PATH)
            if os.path.isabs(exe_path):
                raise FileNotFoundError(f"Blender executable not found at: {exe_path}")

        runner_script = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backend", "blender_runner.py")
        
        cmd = [exe_path, "--background", "--python", runner_script]
        
        # Open log file
        log_dir = settings.output_dir
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, "blender.log")
        self.log_file = open(log_path, "w")
        
        logger.info(f"Starting Blender with command: {' '.join(cmd)}")
        try:
            self.process = subprocess.Popen(
                cmd,
                stdout=self.log_file,
                stderr=subprocess.STDOUT,
                text=True
            )
            self.is_running = True
            
            # Wait for it to become healthy
            healthy = await self._wait_for_health()
            if not healthy:
                self.stop()
                raise RuntimeError("Blender started but failed health check. See output/blender.log for details.")
            
            logger.info("Blender process started and bridge is healthy.")
        except Exception as e:
            logger.error(f"Failed to start Blender process: {e}")
            self.stop()
            raise

    async def _wait_for_health(self, timeout: float = 15.0) -> bool:
        """Wait for the Blender bridge health endpoint to return 200 OK."""
        url = f"http://{settings.blender_bridge_host}:{settings.blender_bridge_port}/health"
        start_time = time.time()
        
        async with httpx.AsyncClient() as client:
            while time.time() - start_time < timeout:
                if self.process and self.process.poll() is not None:
                    logger.error(f"Blender process exited prematurely with code {self.process.returncode}")
                    return False
                
                try:
                    res = await client.get(url, timeout=1.0)
                    if res.status_code == 200:
                        return True
                except httpx.RequestError:
                    pass # Keep polling
                
                await asyncio.sleep(0.5)
                
        return False

    def stop(self) -> None:
        """Stop the Blender process."""
        if self.process:
            logger.info("Stopping Blender process...")
            self.process.terminate()
            try:
                self.process.wait(timeout=5.0)
            except subprocess.TimeoutExpired:
                logger.warning("Blender process did not terminate gracefully. Killing it.")
                self.process.kill()
            self.process = None
        
        if self.log_file:
            self.log_file.close()
            self.log_file = None
            
        self.is_running = False

blender_manager = BlenderProcessManager.get_instance()
