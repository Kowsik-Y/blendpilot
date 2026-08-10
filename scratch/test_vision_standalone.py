import asyncio
import os
import json
from dotenv import load_dotenv
load_dotenv(r"c:\Users\babyv\OneDrive\Desktop\blendpilot-1\.env")
from services.llm import LLMService

async def test_vision():
    # Use existing test image if possible, or dummy 1x1 png
    img_path = "preview.png"
    if not os.path.exists(img_path) or os.path.getsize(img_path) < 100:
        import base64
        # 2x2 black png
        b64 = "iVBORw0KGgoAAAANSUhEUgAAAAIAAAACCAYAAABytg0kAAAAFElEQVQIW2NkYGD4z8DAwMgAI0AMDA4FAvhq/KMAAAAASUVORK5CYII="
        with open(img_path, "wb") as f:
            f.write(base64.b64decode(b64))

    llm = LLMService(provider="groq")
    
    prompt = """
You are evaluating a rendered preview image.
Please provide your critique in the following JSON format ONLY:
{
    "object_presence": true,
    "required_component_presence": true,
    "color_match": true,
    "approximate_shape_match": true,
    "obvious_visual_errors": [],
    "confidence": 1.0,
    "overall_result": "PASS"
}
"""
    try:
        res = await llm.generate_vision(prompt, [img_path])
        print("Raw Output:")
        print(res)
        
        # Verify JSON
        parsed = json.loads(res)
        print("\nParsed JSON successfully:")
        print(json.dumps(parsed, indent=2))
        
    except Exception as e:
        print(f"Error: {type(e).__name__} - {e}")

if __name__ == "__main__":
    asyncio.run(test_vision())
