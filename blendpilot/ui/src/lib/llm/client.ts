/**
 * LLM Client — Proxies requests to user-configured LLM providers.
 * API keys are decrypted server-side and never sent to the browser.
 */

import { type LLMProvider } from "@/types/llm";

interface ChatCompletionMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

interface LLMClientConfig {
  provider: LLMProvider;
  model: string;
  apiKey: string;
  baseUrl: string;
  temperature: number;
  maxTokens: number;
}

export async function streamChatCompletion(
  config: LLMClientConfig,
  messages: ChatCompletionMessage[],
  onChunk: (chunk: string) => void,
  signal?: AbortSignal
): Promise<string> {
  if (config.provider === "anthropic") {
    return streamAnthropic(config, messages, onChunk, signal);
  }
  // OpenAI and OpenAI-compatible (custom, Ollama, OpenRouter)
  return streamOpenAI(config, messages, onChunk, signal);
}

async function streamOpenAI(
  config: LLMClientConfig,
  messages: ChatCompletionMessage[],
  onChunk: (chunk: string) => void,
  signal?: AbortSignal
): Promise<string> {
  const baseUrl = config.baseUrl || "https://api.openai.com/v1";

  const response = await fetch(`${baseUrl}/chat/completions`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${config.apiKey}`,
    },
    body: JSON.stringify({
      model: config.model,
      messages,
      temperature: config.temperature,
      max_tokens: config.maxTokens,
      stream: true,
    }),
    signal,
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`LLM API error (${response.status}): ${error}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let fullContent = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split("\n").filter((l) => l.startsWith("data: "));

    for (const line of lines) {
      const data = line.slice(6);
      if (data === "[DONE]") break;

      try {
        const parsed = JSON.parse(data);
        const delta = parsed.choices?.[0]?.delta?.content;
        if (delta) {
          fullContent += delta;
          onChunk(delta);
        }
      } catch {
        // Skip malformed chunks
      }
    }
  }

  return fullContent;
}

async function streamAnthropic(
  config: LLMClientConfig,
  messages: ChatCompletionMessage[],
  onChunk: (chunk: string) => void,
  signal?: AbortSignal
): Promise<string> {
  const baseUrl = config.baseUrl || "https://api.anthropic.com";

  // Separate system message from conversation
  const systemMsg = messages.find((m) => m.role === "system");
  const chatMsgs = messages.filter((m) => m.role !== "system");

  const response = await fetch(`${baseUrl}/v1/messages`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "x-api-key": config.apiKey,
      "anthropic-version": "2023-06-01",
    },
    body: JSON.stringify({
      model: config.model,
      system: systemMsg?.content || "",
      messages: chatMsgs.map((m) => ({
        role: m.role,
        content: m.content,
      })),
      max_tokens: config.maxTokens,
      temperature: config.temperature,
      stream: true,
    }),
    signal,
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`Anthropic API error (${response.status}): ${error}`);
  }

  const reader = response.body?.getReader();
  if (!reader) throw new Error("No response body");

  const decoder = new TextDecoder();
  let fullContent = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const chunk = decoder.decode(value);
    const lines = chunk.split("\n").filter((l) => l.startsWith("data: "));

    for (const line of lines) {
      const data = line.slice(6);
      try {
        const parsed = JSON.parse(data);
        if (parsed.type === "content_block_delta") {
          const delta = parsed.delta?.text;
          if (delta) {
            fullContent += delta;
            onChunk(delta);
          }
        }
      } catch {
        // Skip malformed chunks
      }
    }
  }

  return fullContent;
}

export async function testConnection(config: LLMClientConfig): Promise<boolean> {
  try {
    let fullResponse = "";
    await streamChatCompletion(
      { ...config, maxTokens: 10 },
      [{ role: "user", content: "Say hello in one word." }],
      (chunk) => { fullResponse += chunk; }
    );
    return fullResponse.length > 0;
  } catch {
    return false;
  }
}
