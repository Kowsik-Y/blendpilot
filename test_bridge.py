import httpx
import asyncio

async def main():
    try:
        async with httpx.AsyncClient() as client:
            r = await client.post('http://127.0.0.1:9876/execute', json={"command":"get_scene_summary", "parameters":{}}, timeout=10.0)
            print(r.status_code)
            print(r.text)
    except Exception as e:
        print(f"ERROR: {type(e)} - {str(e)}")

asyncio.run(main())
