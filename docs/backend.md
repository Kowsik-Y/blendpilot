# `backend/` & API Layer Architecture

> **Stack**: Next.js 14 API Routes (TypeScript) + Blender Add-on Python Bridge (HTTP)

---

## Purpose

The API layer is handled directly via **Next.js 14 App Router API Routes** (`ui/src/app/api/`) coupled with the **Blender Add-on HTTP Bridge** (`blender_addon/bridge.py`).

This architecture:
1. Eliminates redundant server hops by consolidating user authentication, conversation session memory, RAG vector retrieval, and LLM orchestration into Next.js.
2. Directly communicates with the local Blender bridge for 3D operations via typed HTTP requests.

---

## API Routes Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/auth/register` | Register new user with default settings |
| `GET`/`POST` | `/api/auth/[...nextauth]` | NextAuth session and credentials handler |
| `GET`/`POST` | `/api/chat` | List chat sessions / Create new chat session |
| `GET`/`DELETE`/`PATCH` | `/api/chat/[sessionId]` | Fetch session messages, delete, or rename |
| `POST` | `/api/chat/[sessionId]/messages` | Send message, trigger RAG + streaming LLM response |
| `POST`/`GET` | `/api/rag` | Query RAG knowledge store / fetch index stats |
| `POST` | `/api/rag/ingest` | Ingest custom documents into the vector store |
| `GET`/`POST` | `/api/settings` | Get masked settings / Update BYO API keys & host config |
| `GET`/`POST` | `/api/projects` | List user 3D design projects / Create project |
| `GET` | `/api/llm/models` | Get supported models for OpenAI, Anthropic, and custom |
