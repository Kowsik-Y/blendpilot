export type LLMProvider = "openai" | "anthropic" | "custom";

export interface LLMConfig {
  provider: LLMProvider;
  model: string;
  apiKey: string;
  baseUrl: string;
  temperature: number;
  maxTokens: number;
}

export interface LLMModel {
  id: string;
  name: string;
  provider: LLMProvider;
  contextWindow: number;
  supportsVision: boolean;
}

export const DEFAULT_MODELS: Record<LLMProvider, LLMModel[]> = {
  openai: [
    { id: "gpt-4o", name: "GPT-4o", provider: "openai", contextWindow: 128000, supportsVision: true },
    { id: "gpt-4o-mini", name: "GPT-4o Mini", provider: "openai", contextWindow: 128000, supportsVision: true },
    { id: "gpt-4-turbo", name: "GPT-4 Turbo", provider: "openai", contextWindow: 128000, supportsVision: true },
  ],
  anthropic: [
    { id: "claude-sonnet-4-20250514", name: "Claude Sonnet 4", provider: "anthropic", contextWindow: 200000, supportsVision: true },
    { id: "claude-3-5-haiku-20241022", name: "Claude 3.5 Haiku", provider: "anthropic", contextWindow: 200000, supportsVision: false },
  ],
  custom: [],
};

export const DEFAULT_BASE_URLS: Record<LLMProvider, string> = {
  openai: "https://api.openai.com/v1",
  anthropic: "https://api.anthropic.com",
  custom: "",
};
