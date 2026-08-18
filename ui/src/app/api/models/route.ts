import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { db } from "@/lib/db";
import { decrypt } from "@/lib/encryption";
import { DEFAULT_MODELS, type LLMProvider } from "@/types/llm";

export async function GET(req: NextRequest) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const settings = await db.userSettings.findUnique({
    where: { userId: session.user.id },
  });

  if (!settings) {
    return NextResponse.json({ models: DEFAULT_MODELS.openai.map((m) => ({ id: m.id, name: m.name })) });
  }

  const provider = (settings.llmProvider || "openai") as LLMProvider;
  const baseUrl = settings.llmBaseUrl || (provider === "openai" ? "https://api.openai.com/v1" : "");
  const apiKey = settings.llmApiKey ? decrypt(settings.llmApiKey) : "";

  return fetchModelsFromProvider(provider, baseUrl, apiKey);
}

export async function POST(req: NextRequest) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await req.json();
  const provider = (body.provider || "openai") as LLMProvider;
  let apiKey = body.apiKey || "";
  const baseUrl = body.baseUrl || (provider === "openai" ? "https://api.openai.com/v1" : "");

  // If the key is masked, retrieve the real key from the database
  if (!apiKey || apiKey.includes("••••")) {
    const settings = await db.userSettings.findUnique({
      where: { userId: session.user.id },
    });
    if (settings?.llmApiKey) {
      apiKey = decrypt(settings.llmApiKey);
    }
  }

  return fetchModelsFromProvider(provider, baseUrl, apiKey);
}

async function fetchModelsFromProvider(provider: LLMProvider, baseUrl: string, apiKey: string) {
  if (!apiKey && provider !== "ollama" && provider !== "custom") {
    return NextResponse.json({ models: DEFAULT_MODELS[provider].map((m) => ({ id: m.id, name: m.name })) });
  }

  if (provider === "anthropic") {
    try {
      const res = await fetch("https://api.anthropic.com/v1/models", {
        headers: {
          "x-api-key": apiKey,
          "anthropic-version": "2023-06-01",
          "anthropic-beta": "models-2024-10-22",
        },
      });
      if (res.ok) {
        const data = await res.json();
        return NextResponse.json({
          models: data.data.map((m: any) => ({ id: m.id, name: m.display_name || m.id })),
        });
      }
    } catch (e) {
      console.error("Failed to fetch Anthropic models", e);
    }
    // Fallback to defaults
    return NextResponse.json({ models: DEFAULT_MODELS.anthropic.map((m) => ({ id: m.id, name: m.name })) });
  }

  if (baseUrl) {
    try {
      const headers: Record<string, string> = {};
      if (apiKey) {
        headers["Authorization"] = `Bearer ${apiKey}`;
      }
      
      const res = await fetch(`${baseUrl}/models`, {
        headers,
      });
      if (res.ok) {
        const data = await res.json();
        if (data.data && Array.isArray(data.data)) {
          // OpenRouter returns id and name. OpenAI returns id.
          return NextResponse.json({
            models: data.data.map((m: any) => ({ id: m.id, name: m.name || m.id })),
          });
        }
      }
    } catch (e) {
      console.error("Failed to fetch OpenAI/Custom models", e);
    }
  }

  // Fallback to defaults
  return NextResponse.json({ models: DEFAULT_MODELS[provider].map((m) => ({ id: m.id, name: m.name })) });
}
