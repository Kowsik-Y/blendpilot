import { auth } from "@/lib/auth";
import { db } from "@/lib/db";
import { decrypt, encrypt, maskApiKey } from "@/lib/encryption";
import { testConnection } from "@/lib/llm/client";
import { type LLMProvider } from "@/types/llm";
import { NextRequest, NextResponse } from "next/server";

export async function GET(req: NextRequest) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  let settings = await db.userSettings.findUnique({
    where: { userId: session.user.id },
  });

  if (!settings) {
    settings = await db.userSettings.create({
      data: {
        userId: session.user.id,
        llmProvider: "openai",
        llmModel: "gpt-4o",
      },
    });
  }

  const rawKey = settings.llmApiKey ? decrypt(settings.llmApiKey) : "";
  const rawTavilyKey = settings.tavilyApiKey ? decrypt(settings.tavilyApiKey) : "";

  return NextResponse.json({
    llmProvider: settings.llmProvider,
    llmModel: settings.llmModel,
    llmApiKeyMasked: maskApiKey(rawKey),
    hasApiKey: rawKey.length > 0,
    llmBaseUrl: settings.llmBaseUrl,
    llmTemperature: settings.llmTemperature,
    llmMaxTokens: settings.llmMaxTokens,
    contextWindowSize: settings.contextWindowSize,
    ragEnabled: settings.ragEnabled,
    ragTopK: settings.ragTopK,
    blenderHost: settings.blenderHost,
    blenderPort: settings.blenderPort,
    tavilyApiKeyMasked: maskApiKey(rawTavilyKey),
    hasTavilyApiKey: rawTavilyKey.length > 0,
  });
}

export async function POST(req: NextRequest) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  try {
    const body = await req.json();
    const {
      llmProvider,
      llmModel,
      llmApiKey,
      llmBaseUrl,
      llmTemperature,
      llmMaxTokens,
      contextWindowSize,
      ragEnabled,
      ragTopK,
      blenderHost,
      blenderPort,
      tavilyApiKey,
      shouldTestConnection,
    } = body;

    const existingSettings = await db.userSettings.findUnique({
      where: { userId: session.user.id },
    });

    let encryptedKey = existingSettings?.llmApiKey || "";
    // Only re-encrypt if a new unmasked key was sent
    if (llmApiKey && !llmApiKey.includes("••••")) {
      encryptedKey = encrypt(llmApiKey.trim());
    }

    let encryptedTavilyKey = existingSettings?.tavilyApiKey || "";
    if (tavilyApiKey && !tavilyApiKey.includes("••••")) {
      encryptedTavilyKey = encrypt(tavilyApiKey.trim());
    }

    if (shouldTestConnection) {
      const activeKey = llmApiKey && !llmApiKey.includes("••••")
        ? llmApiKey.trim()
        : encryptedKey ? decrypt(encryptedKey) : "";

      const ok = await testConnection({
        provider: (llmProvider || "openai") as LLMProvider,
        model: llmModel || "gpt-4o",
        apiKey: activeKey,
        baseUrl: llmBaseUrl || "",
        temperature: 0,
        maxTokens: 10,
      });

      if (!ok) {
        return NextResponse.json(
          { error: "Failed to connect to LLM provider with current settings." },
          { status: 400 }
        );
      }
    }

    const updated = await db.userSettings.upsert({
      where: { userId: session.user.id },
      create: {
        userId: session.user.id,
        llmProvider: llmProvider || "openai",
        llmModel: llmModel || "gpt-4o",
        llmApiKey: encryptedKey,
        llmBaseUrl: llmBaseUrl || "",
        llmTemperature: llmTemperature !== undefined ? Number(llmTemperature) : 0.0,
        llmMaxTokens: llmMaxTokens ? Number(llmMaxTokens) : 4096,
        contextWindowSize: contextWindowSize ? Number(contextWindowSize) : 128000,
        ragEnabled: ragEnabled !== undefined ? Boolean(ragEnabled) : true,
        ragTopK: ragTopK ? Number(ragTopK) : 4,
        blenderHost: blenderHost || "127.0.0.1",
        blenderPort: blenderPort ? Number(blenderPort) : 9876,
        tavilyApiKey: encryptedTavilyKey,
      },
      update: {
        ...(llmProvider !== undefined && { llmProvider }),
        ...(llmModel !== undefined && { llmModel }),
        ...(llmApiKey && !llmApiKey.includes("••••") && { llmApiKey: encryptedKey }),
        ...(llmBaseUrl !== undefined && { llmBaseUrl }),
        ...(llmTemperature !== undefined && { llmTemperature: Number(llmTemperature) }),
        ...(llmMaxTokens !== undefined && { llmMaxTokens: Number(llmMaxTokens) }),
        ...(contextWindowSize !== undefined && { contextWindowSize: Number(contextWindowSize) }),
        ...(ragEnabled !== undefined && { ragEnabled: Boolean(ragEnabled) }),
        ...(ragTopK !== undefined && { ragTopK: Number(ragTopK) }),
        ...(blenderHost !== undefined && { blenderHost }),
        ...(blenderPort !== undefined && { blenderPort: Number(blenderPort) }),
        ...(tavilyApiKey && !tavilyApiKey.includes("••••") && { tavilyApiKey: encryptedTavilyKey }),
      },
    });

    const rawKey = updated.llmApiKey ? decrypt(updated.llmApiKey) : "";
    const rawTavilyKey = updated.tavilyApiKey ? decrypt(updated.tavilyApiKey) : "";

    return NextResponse.json({
      success: true,
      hasApiKey: rawKey.length > 0,
      llmApiKeyMasked: maskApiKey(rawKey),
      hasTavilyApiKey: rawTavilyKey.length > 0,
      tavilyApiKeyMasked: maskApiKey(rawTavilyKey),
    });
  } catch (error: unknown) {
    const msg = error instanceof Error ? error.message : "Settings update error";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
