import asyncio
from mcp_servers.blender.server import BlenderMCPServer
server = BlenderMCPServer()
print(server.list_tools()[0])
