import asyncio
import logging
from graph.graph import run_pipeline
from services.blender_process import blender_manager

logging.basicConfig(level=logging.INFO)

async def main():
    try:
        await blender_manager.start()
    except Exception as e:
        print(f"FAILED TO START BLENDER: {e}")
        return

    result = await run_pipeline("Create a red wooden table with four legs")
    print("FINISHED")
    print(result.get("status"))
    
    blender_manager.stop()

if __name__ == "__main__":
    asyncio.run(main())
