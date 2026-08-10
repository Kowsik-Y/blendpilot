import { auth } from "@/lib/auth";
import { db } from "@/lib/db";
import { decrypt } from "@/lib/encryption";
import { buildContextWindow, estimateTokens } from "@/lib/llm/context-window";
import { RAGService } from "@/lib/rag";
import { type LLMProvider } from "@/types/llm";
import { NextRequest, NextResponse } from "next/server";

const COPILOT_SYSTEM_PROMPT = `You are BlendPilot AI Copilot, an elite 3D Technical Director, autonomous agent coordinator, and Blender specialist.
You manage a 10-agent autonomous 3D modeling pipeline:
1. Intent Understanding (Dimensions, triangle quota, bounding boxes, topology taxonomy)
2. Scene Understanding (Mesh collision checks, origin calibration, object hierarchy)
3. Technical Research (Engine profiles for Unity/Unreal/glTF, non-manifold constraints)
4. Step Planning (Synthesizing atomic procedural modeling sequences)
5. Autonomous Modeling (bmesh primitives, insets, bevel modifiers, booleans)
6. Materials & Lighting (Principled BSDF shader networks, metallic/roughness, emissive accents)
7. Geometry Topology QA (Manifold verification, edge flow, vertex/face checks)
8. Visual Critique (Lighting distribution, silhouette balance, specular catch)
9. Human Review (Interactive approval & revision gate)
10. Production Export (.blend, .fbx, .glb bundles with clean metadata)

Your interaction style:
- Think deeply and provide expert, actionable 3D advice (proportions in meters, non-destructive modifier stacks, UV unwrapping, PBR material nodes).
- Deliver precise Python bpy / bmesh code snippets whenever appropriate.
- Answer user queries, greetings, and design thoughts naturally, intelligently, and contextually.
- At the end of your response, you may suggest 2 to 3 concise, highly relevant next actions prefixed with an emoji.
- Use crisp Markdown formatting (bold headers, bullet points, code blocks).`;

export async function POST(req: NextRequest) {
  try {
    const session = await auth();
    const body = await req.json().catch(() => ({}));
    const {
      message,
      asset_spec,
      current_plan,
      conversation_history = [],
      api_key: inlineApiKey,
      provider: inlineProvider,
      model: inlineModel,
    } = body;

    if (!message || typeof message !== "string") {
      return NextResponse.json({ error: "Message is required." }, { status: 400 });
    }

    // 1. Resolve LLM Configuration strictly from user input (Request Payload -> User Settings in DB)
    let apiKey = inlineApiKey || "";
    let provider: LLMProvider = (inlineProvider as LLMProvider) || "groq";
    let model = inlineModel || "";
    let baseUrl = "";
    let temperature = 0.7;
    let maxTokens = 4096;
    let ragEnabled = true;

    // Check DB User Settings if not sent inline
    if (session?.user?.id && (!apiKey || apiKey.trim().length < 5)) {
      try {
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
          temperature = settings.llmTemperature ?? 0.7;
          maxTokens = settings.llmMaxTokens || 4096;
          ragEnabled = settings.ragEnabled ?? true;
        }
      } catch (dbErr) {
        console.warn("[Copilot API] DB settings lookup warning:", dbErr);
      }
    }

    // Set model defaults by provider if empty
    if (!model) {
      if (provider === "groq") model = "llama-3.3-70b-versatile";
      else if (provider === "anthropic") model = "claude-3-5-sonnet-20241022";
      else if (provider === "custom") model = "gemini-1.5-flash";
      else model = "gpt-4o";
    }

    // 2. If no valid API key has been configured by the user in the UI, prompt the user to configure it
    if (!apiKey || apiKey.includes("your_") || apiKey.trim().length < 5) {
      return NextResponse.json({
        reply: `🔑 **API Key Required**\n\nPlease configure your LLM API Key directly in the application to enable live AI reasoning and agent execution.\n\n* Click the **🔑 Configure API Key** button above to link your **Groq**, **OpenAI**, **Anthropic**, or **Gemini** key.`,
        suggested_actions: ["🔑 Configure LLM Key"],
        ragSources: [],
        provider_used: "none",
        is_live_llm: false,
      });
    }

    // 2. Perform RAG Retrieval if enabled
    let ragContext = "";
    let ragSources: Array<{ title: string; source: string; score: number }> = [];

    if (ragEnabled && apiKey && apiKey.trim().length > 5) {
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
        console.warn("[Copilot API] RAG retrieval warning:", e);
      }
    }

    // 3. Build Enriched Context Window with Active 3D Scene State & Conversation Memory
    let enrichedSystemPrompt = COPILOT_SYSTEM_PROMPT;
    if (asset_spec) {
      enrichedSystemPrompt += `\n\n## Active 3D Scene State:\n- Asset Type: ${asset_spec.asset_type || "3D Asset"}\n- Dimensions: Width ${asset_spec.dimensions?.width ?? 1.0}m, Depth ${asset_spec.dimensions?.depth ?? 1.0}m, Height ${asset_spec.dimensions?.height ?? 1.0}m\n- Budget: ${asset_spec.budget?.target_triangles ?? 8000} triangles\n- Target Engine: ${asset_spec.target_platform || "Unity/Unreal"}`;
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

    // 4. Live LLM Provider Execution
    if (apiKey && apiKey.trim().length > 5 && !apiKey.includes("your_")) {
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
          } else {
            const errText = await res.text();
            console.error("[Copilot API] Anthropic error:", errText);
          }
        } else {
          // Groq, OpenAI & OpenAI-compatible providers
          const defaultBase = provider === "groq" ? "https://api.groq.com/openai/v1" : "https://api.openai.com/v1";
          const endpoint = (baseUrl || defaultBase) + "/chat/completions";

          const res = await fetch(endpoint, {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Authorization: `Bearer ${apiKey}`,
            },
            body: JSON.stringify({
              model: model || (provider === "groq" ? "llama-3.3-70b-versatile" : "gpt-4o"),
              messages: contextMessages.map((m) => ({ role: m.role, content: m.content })),
              max_tokens: maxTokens,
              temperature,
            }),
          });

          if (res.ok) {
            const data = await res.json();
            reply = data.choices?.[0]?.message?.content || "";
          } else {
            const errText = await res.text();
            console.error(`[Copilot API] ${provider.toUpperCase()} error:`, errText);
          }
        }

        if (reply) {
          const suggested_actions = extractSuggestedActions(message, reply);
          return NextResponse.json({
            reply,
            ragSources,
            suggested_actions,
            provider_used: provider,
            model_used: model,
            is_live_llm: true,
          });
        }
      } catch (err: any) {
        console.error("[Copilot API] Live LLM Exception:", err);
      }
    }

    // 5. If no valid API key is configured anywhere, provide a clear, helpful message
    return NextResponse.json({
      reply: `⚠️ **LLM Connection Required**\n\nTo enable live AI agent reasoning and autonomous Blender generation, please configure your API key:\n\n* **Groq** (Recommended for ultra-fast reasoning: \`GROQ_API_KEY\`)\n* **OpenAI** (\`gpt-4o\` / \`gpt-4o-mini\`)\n* **Anthropic** (\`claude-3-5-sonnet\`)\n* **Local / Custom** (Ollama, LM Studio)\n\nClick the **⚙️ Settings / Key icon** at the top right to link your API key.`,
      suggested_actions: ["🔑 Configure LLM Key", "🚀 Launch 10-Agent Pipeline"],
      ragSources: [],
      provider_used: "none",
      is_live_llm: false,
    });
  } catch (error: any) {
    console.error("[Copilot API] Route Exception:", error);
    return NextResponse.json(
      { error: error.message || "Failed to process Copilot request" },
      { status: 500 }
    );
  }
}

/**
 * Dynamically extract actionable chips from the user message and LLM reply.
 */
function extractSuggestedActions(userMsg: string, reply: string): string[] {
  const combined = (userMsg + " " + reply).toLowerCase();
  const actions: string[] = [];

  // Check for dynamic intent patterns
  if (combined.includes("launch") || combined.includes("create") || combined.includes("generate") || combined.includes("build") || combined.includes("pipeline")) {
    actions.push("🚀 Launch 10-Agent Pipeline");
  }
  if (combined.includes("bevel") || combined.includes("chamfer") || combined.includes("modifier")) {
    actions.push("🛠️ Add 0.02m Bevel Modifier");
  }
  if (combined.includes("shader") || combined.includes("material") || combined.includes("bsdf") || combined.includes("color")) {
    actions.push("🎨 Tune PBR Shader Nodes");
  }
  if (combined.includes("dimension") || combined.includes("scale") || combined.includes("size") || combined.includes("width")) {
    actions.push("📐 Adjust Proportions & Scale");
  }
  if (combined.includes("topology") || combined.includes("manifold") || combined.includes("qa") || combined.includes("check")) {
    actions.push("🔍 Run Topology QA Check");
  }
  if (combined.includes("plan") || combined.includes("step") || combined.includes("sequence")) {
    actions.push("📋 Generate Step-by-Step Plan");
  }

  // Ensure default helpful actions if none matched
  if (actions.length === 0) {
    actions.push("🚀 Launch 10-Agent Pipeline", "📋 Generate Modeling Plan", "🛠️ Add 0.02m Bevel Modifier");
  }

  return Array.from(new Set(actions)).slice(0, 3);
}
