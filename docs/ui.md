# `ui/` — Next.js 14 + shadcn/ui Frontend & API Architecture

> **Stack**: Next.js 14 (App Router), TypeScript, Tailwind CSS, shadcn/ui, NextAuth.js v5, Prisma ORM, SQLite/PostgreSQL
> **Features**: Multi-Agent Chat Interface, BYO LLM Keys (AES-256 encrypted), Context-Window Sliding Memory, RAG Knowledge Retrieval for Blender Docs & Project Context.

---

## 1. Overview

The UI layer is a unified Next.js 14 application that serves both the frontend interactive dashboard and the server-side API routes for:
- 🔐 **Authentication & Sessions**: NextAuth.js v5 with credentials and JWT sessions.
- 💬 **Conversational 3D Modeling**: Streaming chat interface with real-time agent execution pipeline cards.
- 📚 **Separate RAG Service Layer**: Ingests and retrieves Blender 3D documentation, modifier guidelines, PBR rules, and project specifications.
- 🔑 **BYO LLM Credentials**: Encrypted storage for user-provided API keys (OpenAI, Anthropic, Ollama, OpenRouter, and custom endpoints).
- 🔌 **Blender Bridge Client**: Communicates with the local Blender Add-on bridge server (port 9876).

---

## 2. Directory Structure

```
ui/
├── prisma/
│   ├── schema.prisma              # Database schema (User, UserSettings, ChatSession, Message, Project)
│   └── dev.db                     # SQLite development database
│
├── src/
│   ├── app/
│   │   ├── layout.tsx             # Root layout (SessionProvider, ThemeProvider, Toaster)
│   │   ├── page.tsx               # Landing & redirect hero page
│   │   ├── globals.css            # Dark mode tokens & glassmorphism styles
│   │   │
│   │   ├── (auth)/
│   │   │   ├── login/page.tsx     # Login page with credentials form
│   │   │   └── register/page.tsx  # Registration page with default settings setup
│   │   │
│   │   ├── (dashboard)/
│   │   │   ├── layout.tsx         # Authenticated layout with sidebar & header
│   │   │   ├── chat/
│   │   │   │   ├── page.tsx       # Auto-redirect / chat index
│   │   │   │   └── [sessionId]/   # Active chat workspace
│   │   │   ├── projects/
│   │   │   │   └── page.tsx       # 3D design projects management
│   │   │   └── settings/
│   │   │       └── page.tsx       # LLM API keys, RAG config, Blender host/port
│   │   │
│   │   └── api/
│   │       ├── auth/[...nextauth]/route.ts  # NextAuth handlers
│   │       ├── auth/register/route.ts       # User registration
│   │       ├── chat/route.ts                # List & create chat sessions
│   │       ├── chat/[sessionId]/route.ts    # Get, update, delete session
│   │       ├── chat/[sessionId]/messages/route.ts # Streaming SSE + RAG prompt injection
│   │       ├── rag/route.ts                 # RAG query & knowledge store statistics
│   │       ├── rag/ingest/route.ts          # Ingest custom documents into vector store
│   │       ├── settings/route.ts            # CRUD user settings & test connection
│   │       ├── projects/route.ts            # 3D design project management
│   │       └── llm/models/route.ts          # Available provider models metadata
│   │
│   ├── components/
│   │   ├── chat/
│   │   │   ├── chat-interface.tsx      # SSE stream listener & message state
│   │   │   ├── message-bubble.tsx      # Markdown bubble + RAG citation pills
│   │   │   ├── message-input.tsx       # Auto-resizing textarea with quick templates
│   │   │   └── agent-progress.tsx      # Multi-agent execution stage cards
│   │   ├── layout/
│   │   │   ├── app-sidebar.tsx         # Sidebar with chat history & navigation
│   │   │   ├── header.tsx              # Top bar with user profile & bridge status
│   │   │   └── theme-toggle.tsx        # Dark/light mode switcher
│   │   └── ui/                         # shadcn/ui primitives
│   │
│   ├── lib/
│   │   ├── auth.ts                     # NextAuth v5 configuration
│   │   ├── db.ts                       # Prisma client singleton
│   │   ├── encryption.ts               # AES-256-GCM API key encryption
│   │   ├── llm/
│   │   │   ├── client.ts               # Streaming LLM client (OpenAI, Anthropic, Custom)
│   │   │   ├── context-window.ts       # Sliding context window & token budgeting
│   │   │   └── memory.ts               # Conversation persistence & auto-titling
│   │   └── rag/
│   │       ├── types.ts                # RAG type definitions
│   │       ├── embeddings.ts           # OpenAI + local fallback vectorizer
│   │       ├── vector-store.ts         # Cosine similarity vector store singleton
│   │       ├── blender-docs-service.ts # Blender docs loader & markdown chunker
│   │       ├── project-context-service.ts # User project spec extractor
│   │       └── rag-service.ts          # Unified RAG coordinator
│   │
│   └── types/
│       ├── chat.ts
│       └── llm.ts
```

---

## 3. RAG Service Architecture

The RAG pipeline runs as a standalone service layer under `ui/src/lib/rag/`:

```
┌─────────────────────────────────────────────────────────────┐
│                       RAG Service Layer                     │
│                                                             │
│  1. BlenderDocsService       2. ProjectContextService       │
│     • Primitives & bmesh       • Active project design specs│
│     • PBR Materials & nodes    • QA results & triangle limits│
│     • Low-poly QA standards    • User modification history  │
│                   │                         │               │
│                   ▼                         ▼               │
│          ┌──────────────────────────────────────┐           │
│          │ EmbeddingsService (OpenAI / Fallback)│           │
│          └──────────────────────────────────────┘           │
│                             │                               │
│                             ▼                               │
│          ┌──────────────────────────────────────┐           │
│          │ VectorStore (Cosine Similarity Top-K)│           │
│          └──────────────────────────────────────┘           │
│                             │                               │
│                             ▼                               │
│          ┌──────────────────────────────────────┐           │
│          │ Formatted RAG Context Block          │           │
│          │ (Injected into LLM Context Window)   │           │
│          └──────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────┘
```

---

## 4. Running the UI

```bash
cd ui

# Install dependencies (already completed)
npm install

# Push database schema
npx prisma db push

# Start Next.js development server
npm run dev
```

Visit **`http://localhost:3000`** in your browser.
