import { auth } from "@/lib/auth";
import { db } from "@/lib/db";
import { decrypt } from "@/lib/encryption";
import { streamChatCompletion } from "@/lib/llm/client";
import { buildContextWindow } from "@/lib/llm/context-window";
import { autoTitleSession, getSessionMessages, saveMessage } from "@/lib/llm/memory";
import { RAGService } from "@/lib/rag";
import { type LLMProvider } from "@/types/llm";
import { NextRequest, NextResponse } from "next/server";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { sessionId } = await params;
  const messages = await getSessionMessages(sessionId);
  return NextResponse.json(messages);
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { sessionId } = await params;
  const { content, attachments } = await req.json();

  if (!content || typeof content !== "string") {
    return NextResponse.json({ error: "Message content is required." }, { status: 400 });
  }

  // 1. Save user message to database
  const userMsg = await saveMessage(sessionId, "user", content, {
    attachments: attachments || [],
  });

  // Check if session needs auto-titling (if first message)
  const existingMsgs = await getSessionMessages(sessionId);
  if (existingMsgs.length <= 1) {
    await autoTitleSession(sessionId, content);
  }

  // 2. Fetch user settings for LLM and RAG
  const settings = await db.userSettings.findUnique({
    where: { userId: session.user.id },
  });

  const provider = (settings?.llmProvider || "openai") as LLMProvider;
  const model = settings?.llmModel || "gpt-4o";
  const apiKey = settings?.llmApiKey ? decrypt(settings.llmApiKey) : "";
  const baseUrl = settings?.llmBaseUrl || "";
  const maxTokens = settings?.llmMaxTokens || 4096;
  const temperature = settings?.llmTemperature || 0.0;
  const ragEnabled = settings?.ragEnabled ?? true;
  const ragTopK = settings?.ragTopK || 4;
  const contextWindowSize = settings?.contextWindowSize || 128000;

  if (!apiKey && provider !== "custom") {
    // If no API key configured, return informative response
    const helpMsg =
      "⚠️ **LLM API Key Not Configured**\n\nPlease go to **Settings** and provide your API key (OpenAI, Anthropic, or custom endpoint) to start generating 3D assets.";
    const assistantMsg = await saveMessage(sessionId, "assistant", helpMsg);
    return NextResponse.json({ message: assistantMsg });
  }

  // 3. Perform RAG Retrieval if enabled
  let ragContextFormatted = "";
  let ragSources: Array<{ title: string; source: string; score: number }> = [];

  if (ragEnabled) {
    try {
      const rag = new RAGService({ apiKey, baseUrl });
      await rag.syncProjectContext(session.user.id);
      const retrieved = await rag.retrieveContext(content, {
        topK: ragTopK,
        maxTokens: 2000,
      });
      ragContextFormatted = retrieved.formattedContext;
      ragSources = retrieved.sources;
    } catch (e) {
      console.warn("RAG retrieval skipped due to error:", e);
    }
  }

  // 4. Build Context Window (System prompt + RAG + History budget)
  const systemPrompt = `
You are BlendPilot AI, an expert agentic 3D modeling copilot for Blender.
You assist users in designing, reviewing, modifying, and validating low-poly and game-ready 3D assets.

Guidelines:
- When the user asks for a 3D asset, break down the intent (dimensions in meters, style, triangle limit, materials, and hierarchy).
- Present structured design steps and refer to available Blender operations.
- Cite relevant Blender parameters and PBR material values when appropriate.
- Be concise, professional, and helpful.
`.trim();

  const formattedHistory = existingMsgs.map((m) => ({
    role: m.role as "user" | "assistant" | "system",
    content: m.content,
    tokenCount: m.tokenCount,
  }));

  const contextMessages = buildContextWindow(
    {
      maxTokens: contextWindowSize,
      responseBuffer: maxTokens,
      systemPrompt,
      ragContext: ragContextFormatted || undefined,
    },
    formattedHistory
  );

  // 5. Setup Streaming response using TransformStream / SSE
  const encoder = new TextEncoder();
  const stream = new TransformStream();
  const writer = stream.writable.getWriter();

  // Run streaming in background
  (async () => {
    let completeResponse = "";
    try {
      // Send RAG sources metadata chunk first if present
      if (ragSources.length > 0) {
        const metaEvent = `data: ${JSON.stringify({ type: "rag_sources", sources: ragSources })}\n\n`;
        await writer.write(encoder.encode(metaEvent));
      }

      await streamChatCompletion(
        {
          provider,
          model,
          apiKey,
          baseUrl,
          temperature,
          maxTokens,
        },
        contextMessages,
        async (chunk) => {
          completeResponse += chunk;
          const sseEvent = `data: ${JSON.stringify({ type: "chunk", content: chunk })}\n\n`;
          await writer.write(encoder.encode(sseEvent));
        }
      );

      // Save complete assistant message to DB
      await saveMessage(sessionId, "assistant", completeResponse, {
        ragSources,
        model,
        provider,
      });

      const doneEvent = `data: ${JSON.stringify({ type: "done", messageId: userMsg.id })}\n\n`;
      await writer.write(encoder.encode(doneEvent));
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : "Generation failed";
      const errEvent = `data: ${JSON.stringify({ type: "error", error: errMsg })}\n\n`;
      await writer.write(encoder.encode(errEvent));
    } finally {
      await writer.close();
    }
  })();

  return new Response(stream.readable, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
    },
  });
}
