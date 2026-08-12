# System Architecture

BlendPilot's architecture revolves around a stateful graph powered by **LangGraph**, providing structured multi-agent coordination with built-in loops for self-correction.

## Multi-Agent LangGraph

The generation process follows a structured DAG (Directed Acyclic Graph) where specialized agents pass a validated `State` object down the pipeline.

```mermaid
graph TD
    User["User Prompt"] --> Agent1["1. Intent Understanding"]
    Agent1 --> Agent2["2. Scene Understanding"]
    Agent2 --> Agent3["3. Technical Research"]
    Agent3 --> Agent4["4. Step Planning"]
    Agent4 --> Agent5["5. Autonomous Modeling"]
    Agent5 --> Agent6["6. Materials & Lighting"]
    Agent6 --> Agent7["7. Geometry QA"]
    
    Agent7 -->|Pass| Agent8["8. Visual Critic"]
    Agent7 -->|Fail & Repairs < 3| Agent5
    
    Agent8 -->|Score >= 0.8| Agent9["9. Human Review"]
    Agent8 -->|Score < 0.8 & Revisions < 3| Agent5
    
    Agent9 -->|Approve| Agent10["10. Production Export"]
    Agent9 -->|Request Change| Agent4
    
    Agent10 --> ExportFiles[".blend / .fbx / .glb + Asset Report"]
```

## Core Components

1. **Agent Engine (`agents/` & `graph/`)**: Parses logic, manages states, and interfaces with the LLM backend.
2. **MCP Bridge (`mcp_servers/`)**: Converts intent-driven outputs from the agents into actionable tool calls using the Model Context Protocol.
3. **Blender Native Execution (`core/` & `blender_addon/`)**: Real-time `bpy` environment where the actual geometric modifications, shader creation, and rendering occur.
4. **Validation Engine (`evaluation/` & `agents/GeometryQAAgent`)**: Ensures outputs mathematically match requested dimensions and constraints.

## State Management

Each node in the LangGraph updates a strongly-typed Pydantic schema (`schemas/`), ensuring data reliability between jumps. If a node fails, the graph route conditionally branches back to a previous node (e.g., from `Geometry QA` back to `Modeling` if non-manifold geometry is detected).
