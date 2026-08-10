import os
import base64
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

load_dotenv(r"c:\Users\babyv\OneDrive\Desktop\blendpilot-1\.env")

# Try to use ChatGroq with a vision model
try:
    model = ChatGroq(model_name="llama-3.2-90b-vision-preview")
    
    # 1x1 transparent PNG
    b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII="
    
    msg = HumanMessage(content=[
        {"type": "text", "text": "What is this image?"},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
    ])
    
    res = model.invoke([msg])
    print("ChatGroq Success!")
    print(res.content)
except Exception as e:
    print(f"ChatGroq Error: {type(e).__name__} - {e}")

# Try direct Groq client
print("\n--- Direct Client ---")
try:
    import groq
    client = groq.Groq(api_key=os.environ.get("GROQ_API_KEY"))
    response = client.chat.completions.create(
        model="llama-3.2-90b-vision-preview",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What is this image?"},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}}
                ]
            }
        ]
    )
    print("Direct Client Success!")
    print(response.choices[0].message.content)
except Exception as e:
    print(f"Direct Client Error: {type(e).__name__} - {e}")
