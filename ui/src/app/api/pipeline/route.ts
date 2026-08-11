import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { db } from "@/lib/db";
import { decrypt } from "@/lib/encryption";

const BACKEND_URL = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";

export async function POST(req: NextRequest) {
  try {
    const session = await auth();
    const body = await req.json();

    // Fetch user settings for API key
    if (session?.user?.id) {
      const settings = await db.userSettings.findUnique({
        where: { userId: session.user.id },
      });
      if (settings) {
        body.overrides = {
          ...body.overrides,
          api_key: settings.llmApiKey ? decrypt(settings.llmApiKey) : "",
          provider: settings.llmProvider,
          model: settings.llmModel,
          base_url: settings.llmBaseUrl || null,
          temperature: settings.llmTemperature,
          max_tokens: settings.llmMaxTokens,
          context_window_size: settings.contextWindowSize,
          rag_enabled: settings.ragEnabled,
          rag_top_k: settings.ragTopK,
          tavily_api_key: settings.tavilyApiKey ? decrypt(settings.tavilyApiKey) : "",
        };
      }
    }

    const res = await fetch(`${BACKEND_URL}/api/workflow/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Failed to connect to Python backend";
    return NextResponse.json(
      { success: false, error: message },
      { status: 500 }
    );
  }
}
