# Backend API

The BlendPilot backend is built using **FastAPI** to provide high-performance, asynchronous endpoints for managing the multi-agent graph.

## Core Endpoints

### `POST /api/v1/generate`
The primary entry point for starting a generation job.
- **Payload**: `{"prompt": "string", "target_engine": "unity"}`
- **Response**: Returns a `job_id` for tracking.

### `GET /api/v1/status/{job_id}`
Returns the current active state of the LangGraph.
- **Response**: Yields the current executing agent, logs, and partial state schemas.

### `GET /api/v1/stream/{job_id}` (SSE)
Server-Sent Events endpoint used by the frontend Web UI to stream agent thinking, intermediate renders, and topology validation scores in real-time.

### `POST /api/v1/feedback/{job_id}`
Allows the human-in-the-loop to approve or reject the generation.
- **Payload**: `{"status": "APPROVE" | "REQUEST_CHANGE", "comment": "Make it rounder"}`

## Project Structure (`backend/`)

- `main.py`: FastAPI application initialization and routing.
- `api/`: Route definitions for jobs, feedback, and streaming.
- `core/`: Config and dependency injection.
- `services/`: Interfaces with the LangGraph execution engine.

## WebSockets vs SSE

While the initial Blender Bridge uses HTTP/Sockets, the frontend web UI consumes updates via **Server-Sent Events (SSE)**. This allows for lightweight, unidirectional streaming of agent tokens and progress updates without the overhead of full WebSockets, making it perfectly suited for displaying LLM generation progress.
