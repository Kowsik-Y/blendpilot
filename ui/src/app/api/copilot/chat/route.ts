import { auth } from "@/lib/auth";
import { db } from "@/lib/db";
import { decrypt } from "@/lib/encryption";
import { buildContextWindow, estimateTokens } from "@/lib/llm/context-window";
import { RAGService } from "@/lib/rag";
import { type LLMProvider } from "@/types/llm";
import { NextRequest, NextResponse } from "next/server";

const COPILOT_SYSTEM_PROMPT = `You are BlendPilot AI Copilot, an elite 3D Technical Director and Blender specialist.
You coordinate a 10-agent autonomous 3D pipeline:
1. Intent Understanding (Dimensions, triangle quota, asset taxonomy)
2. Scene Understanding (Collision check, origin calibration)
3. Technical Research (Engine profiles, non-manifold checks)
4. Step Planning (Atomic modeling step sequences)
5. Autonomous Modeling (bmesh primitives, insets, bevel modifiers)
6. Materials & Lighting (Principled BSDF, roughness, metallic, emissive)
7. Geometry Topology QA (Manifold verification, edge flow)
8. Visual Critique (Lighting distribution, bevel reflection)
9. Human Review (Approval gate)
10. Production Export (.blend, .fbx, .glb bundles)

Your interaction style:
- Deliver deeply knowledgeable, practical 3D modeling advice (proportions in meters, non-destructive modifier stacks, UV unwrapping, PBR material nodes).
- Answer greetings naturally and conversationally — introduce yourself as BlendPilot Copilot and describe your capabilities.
- For 3D modeling questions, provide clean Python bpy/bmesh snippets and exact modifier settings.
- When users describe a 3D object to create, provide a clear specification with dimensions, materials, triangle budget, and topology strategy.
- Structure responses with crisp Markdown formatting (bold headers, bullet points, code blocks).
- Always suggest 2-3 actionable next steps at the end of your response.`;

export async function POST(req: NextRequest) {
  try {
    const session = await auth();
    const body = await req.json().catch(() => ({}));
    const { message, asset_spec, current_plan, conversation_history = [], api_key: inlineApiKey, provider: inlineProvider, model: inlineModel } = body;

    if (!message || typeof message !== "string") {
      return NextResponse.json({ error: "Message is required." }, { status: 400 });
    }

    // 1. Fetch User Settings from Database
    let apiKey = inlineApiKey || "";
    let provider: LLMProvider = (inlineProvider as LLMProvider) || "openai";
    let model = inlineModel || "gpt-4o";
    let baseUrl = "";
    let temperature = 0.7;
    let maxTokens = 4096;
    let ragEnabled = true;

    if (session?.user?.id && !apiKey) {
      const settings = await db.userSettings.findUnique({
        where: { userId: session.user.id },
      });
      if (settings) {
        provider = (settings.llmProvider || provider) as LLMProvider;
        model = settings.llmModel || model;
        if (settings.llmApiKey) {
          apiKey = decrypt(settings.llmApiKey);
        }
        baseUrl = settings.llmBaseUrl || "";
        temperature = settings.llmTemperature || 0.7;
        maxTokens = settings.llmMaxTokens || 4096;
        ragEnabled = settings.ragEnabled ?? true;
      }
    }

    // 2. Perform RAG Retrieval if enabled
    let ragContext = "";
    let ragSources: Array<{ title: string; source: string; score: number }> = [];

    if (ragEnabled) {
      try {
        const rag = new RAGService({ apiKey, baseUrl });
        if (session?.user?.id) {
          await rag.syncProjectContext(session.user.id);
        }
        const retrieved = await rag.retrieveContext(message, {
          topK: 3,
          maxTokens: 1500,
        });
        ragContext = retrieved.formattedContext;
        ragSources = retrieved.sources;
      } catch (e) {
        console.warn("Copilot RAG retrieval warning:", e);
      }
    }

    // 3. Build Rich Context Window with Scene State & Memory
    let enrichedSystemPrompt = COPILOT_SYSTEM_PROMPT;
    if (asset_spec) {
      enrichedSystemPrompt += `\n\n## Active 3D Scene State:\n- Asset Type: ${asset_spec.asset_type || "crate"}\n- Dimensions: Width ${asset_spec.dimensions?.width || 1.0}m, Depth ${asset_spec.dimensions?.depth || 0.7}m, Height ${asset_spec.dimensions?.height || 0.6}m\n- Budget: ${asset_spec.budget?.target_triangles || 8000} triangles`;
    }
    if (current_plan && current_plan.length > 0) {
      enrichedSystemPrompt += `\n- Current Step Plan: ${JSON.stringify(current_plan)}`;
    }

    // Format conversation history for context window
    const rawMessages = [
      ...conversation_history.map((m: any) => ({
        role: m.role === "user" ? ("user" as const) : ("assistant" as const),
        content: m.content,
        tokenCount: estimateTokens(m.content),
      })),
      {
        role: "user" as const,
        content: message,
        tokenCount: estimateTokens(message),
      },
    ];

    const contextMessages = buildContextWindow(
      {
        maxTokens: 8192,
        responseBuffer: 2048,
        systemPrompt: enrichedSystemPrompt,
        ragContext,
      },
      rawMessages
    );

    // 4. If API Key is present, call Real LLM Provider (OpenAI, Anthropic Claude, Gemini, Custom)
    if (apiKey && apiKey.trim().length > 5) {
      try {
        let reply = "";

        if (provider === "anthropic") {
          const anthropicEndpoint = baseUrl || "https://api.anthropic.com/v1/messages";
          const systemMsg = contextMessages.find((m) => m.role === "system")?.content || "";
          const userAssistantMsgs = contextMessages
            .filter((m) => m.role !== "system")
            .map((m) => ({ role: m.role, content: m.content }));

          const res = await fetch(anthropicEndpoint, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              "x-api-key": apiKey,
              "anthropic-version": "2023-06-01",
            },
            body: JSON.stringify({
              model: model || "claude-3-5-sonnet-20241022",
              system: systemMsg,
              messages: userAssistantMsgs,
              max_tokens: maxTokens,
              temperature,
            }),
          });

          if (res.ok) {
            const data = await res.json();
            reply = data.content?.[0]?.text || "";
          }
        } else {
          // OpenAI & OpenAI-compatible
          const openaiEndpoint = (baseUrl || "https://api.openai.com/v1") + "/chat/completions";
          const res = await fetch(openaiEndpoint, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${apiKey}`,
            },
            body: JSON.stringify({
              model: model || "gpt-4o",
              messages: contextMessages.map((m) => ({ role: m.role, content: m.content })),
              max_tokens: maxTokens,
              temperature,
            }),
          });

          if (res.ok) {
            const data = await res.json();
            reply = data.choices?.[0]?.message?.content || "";
          }
        }

        if (reply) {
          return NextResponse.json({
            reply,
            ragSources,
            suggested_actions: extractSuggestedActions(message, reply),
            provider_used: provider,
            is_live_llm: true,
          });
        }
      } catch (err) {
        console.error("LLM Provider Call Error:", err);
      }
    }

    // 5. If no API key is provided, return a clear prompt to configure it
    return NextResponse.json({
      reply: `⚠️ **API Key Required**\n\nPlease configure your LLM API Key to enable real-time AI chat and agent execution.\n\n**How to connect:**\n1. Click the **🔑 Configure LLM Key** button below\n2. Or go to **⚙️ Settings** to link your OpenAI (\`gpt-4o\`) or Anthropic (\`claude-3-5-sonnet\`) key\n\nOnce connected, I'll use real LLM reasoning to:\n- Generate creative 3D modeling plans\n- Provide expert Blender advice with code snippets\n- Power all 10 autonomous agents with real AI intelligence`,
      suggested_actions: ["🔑 Configure LLM Key"],
      ragSources: [],
      provider_used: "none",
      is_live_llm: false,
    });
  } catch (error: any) {
    console.error("Copilot API Exception:", error);
    return NextResponse.json(
      { error: error.message || "Failed to process Copilot request" },
      { status: 500 }
    );
  }
}

function extractSuggestedActions(userMsg: string, reply: string): string[] {
  const lower = (userMsg + " " + reply).toLowerCase();
  const actions: string[] = [];

  if (lower.includes("bevel") || lower.includes("edge") || lower.includes("chamfer")) {
    actions.push("🛠️ Add 0.02m Bevel Modifier");
  }
  if (lower.includes("dimension") || lower.includes("scale") || lower.includes("size")) {
    actions.push("📐 Adjust Dimensions");
  }
  if (lower.includes("material") || lower.includes("shader") || lower.includes("color") || lower.includes("pbr")) {
    actions.push("🎨 Tune PBR Shader Nodes");
  }
  if (lower.includes("plan") || lower.includes("step") || lower.includes("workflow")) {
    actions.push("📋 Generate Step-by-Step Plan");
  }
  if (lower.includes("create") || lower.includes("build") || lower.includes("make") || lower.includes("generate")) {
    actions.push("🚀 Launch 10-Agent Pipeline");
  }
  if (lower.includes("export") || lower.includes("download") || lower.includes("fbx") || lower.includes("glb")) {
    actions.push("📦 Export Production Bundle");
  }
  if (lower.includes("topology") || lower.includes("manifold") || lower.includes("quality")) {
    actions.push("🔍 Run Topology QA");
  }
  if (actions.length === 0) {
    actions.push("🚀 Launch 10-Agent Pipeline", "📋 Generate Modeling Plan", "🛠️ Add 0.02m Bevel Modifier");
  }
  return actions.slice(0, 3);
}
