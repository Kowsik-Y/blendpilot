import { DEFAULT_BASE_URLS, DEFAULT_MODELS, type LLMProvider } from "@/types/llm";
import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  const provider = (req.nextUrl.searchParams.get("provider") || "openai") as LLMProvider;
  const models = DEFAULT_MODELS[provider] || [];
  const defaultBaseUrl = DEFAULT_BASE_URLS[provider] || "";

  return NextResponse.json({
    provider,
    models,
    defaultBaseUrl,
  });
}
