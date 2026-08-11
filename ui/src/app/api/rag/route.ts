import { auth } from "@/lib/auth";
import { decrypt } from "@/lib/encryption";
import { RAGService } from "@/lib/rag";
import { db } from "@/lib/db";
import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const session = await auth();
    const body = await req.json();
    const { query, topK, maxTokens, category } = body;

    if (!query) {
      return NextResponse.json({ error: "Missing query string." }, { status: 400 });
    }

    // Retrieve user settings to use user's configured LLM embeddings if present
    let apiKey: string | undefined;
    let baseUrl: string | undefined;

    if (session?.user?.id) {
      const settings = await db.userSettings.findUnique({
        where: { userId: session.user.id },
      });
      if (settings?.llmApiKey) {
        apiKey = decrypt(settings.llmApiKey);
        baseUrl = settings.llmBaseUrl || undefined;
      }
    }

    const rag = new RAGService({ apiKey, baseUrl });

    // Sync project context if user is authenticated
    if (session?.user?.id) {
      await rag.syncProjectContext(session.user.id);
    }

    const context = await rag.retrieveContext(query, {
      topK: topK || 4,
      maxTokens: maxTokens || 1500,
      category,
    });

    return NextResponse.json(context);
  } catch (error: unknown) {
    const msg = error instanceof Error ? error.message : "RAG query error";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}

export async function GET(req: NextRequest) {
  try {
    const rag = new RAGService();
    await rag.initializeBaseline();
    return NextResponse.json(rag.getStats());
  } catch (error: unknown) {
    const msg = error instanceof Error ? error.message : "Failed to get RAG stats";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
