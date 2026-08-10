import asyncio
import os
import json
from graph.graph import build_blendpilot_graph

async def run_vision_test():
    print(f"API KEY: {'Configured' if os.environ.get('GROQ_API_KEY') or os.environ.get('OPENAI_API_KEY') else 'Missing'}")
    
    graph = build_blendpilot_graph()
    config = {"configurable": {"thread_id": "test_vision_thread"}}
    state = {
        "user_request": "Create a red wooden table with four legs.",
        "project_id": "vision_test_run",
        "provider": "groq",  # We switched to Groq in the previous step
        "messages": [],
        "iterations": 0
    }
    
    print("Starting execution...")
    try:
        final_state = await graph.ainvoke(state, config)
        print("Execution completed.")
        
        print("\n--- VISION QA RESULT ---")
        vis_report = final_state.get("vision_report", {})
        print(json.dumps(vis_report, indent=2))
        
        print("\n--- PREVIEW IMAGE ---")
        preview_path = final_state.get("preview_image_path", "NOT SET")
        print(f"Path: {preview_path}")
        if os.path.exists(preview_path):
            print(f"Exists: Yes, Size: {os.path.getsize(preview_path)} bytes")
        else:
            print("Exists: No")
            
        print("\n--- DECISION AGENT ---")
        print(f"Current Agent state: {final_state.get('current_agent')}")
        
    except Exception as e:
        print(f"Execution failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_vision_test())
