/**
 * Context Window Manager
 *
 * Manages the token budget for LLM context windows:
 * 1. System prompt (always included)
 * 2. RAG context (if enabled)
 * 3. Conversation summary (compressed older messages)
 * 4. Recent messages (sliding window, newest first)
 * 5. Current user message
 */

interface ContextMessage {
  role: "system" | "user" | "assistant";
  content: string;
  tokenCount: number;
}

interface ContextWindowConfig {
  maxTokens: number;
  responseBuffer: number; // Reserve tokens for LLM response
  systemPrompt: string;
  ragContext?: string;
}

/**
 * Approximate token count for a string.
 * Uses the ~4 chars per token heuristic.
 * For production, use tiktoken or provider-specific tokenizer.
 */
export function estimateTokens(text: string): number {
  if (!text) return 0;
  return Math.ceil(text.length / 4);
}

/**
 * Build the context window from available messages,
 * fitting as many recent messages as possible within the budget.
 */
export function buildContextWindow(
  config: ContextWindowConfig,
  messages: ContextMessage[],
  conversationSummary?: string
): ContextMessage[] {
  const result: ContextMessage[] = [];
  let usedTokens = 0;
  const budget = config.maxTokens - config.responseBuffer;

  // 1. System prompt (always included)
  const systemTokens = estimateTokens(config.systemPrompt);
  result.push({
    role: "system",
    content: config.systemPrompt,
    tokenCount: systemTokens,
  });
  usedTokens += systemTokens;

  // 2. RAG context (if provided)
  if (config.ragContext) {
    const ragTokens = estimateTokens(config.ragContext);
    if (usedTokens + ragTokens < budget) {
      result.push({
        role: "system",
        content: `## Relevant Context\n\n${config.ragContext}`,
        tokenCount: ragTokens,
      });
      usedTokens += ragTokens;
    }
  }

  // 3. Conversation summary (if older messages were trimmed)
  if (conversationSummary) {
    const summaryTokens = estimateTokens(conversationSummary);
    if (usedTokens + summaryTokens < budget) {
      result.push({
        role: "system",
        content: `## Conversation Summary\n\n${conversationSummary}`,
        tokenCount: summaryTokens,
      });
      usedTokens += summaryTokens;
    }
  }

  // 4. Recent messages (newest first, then reverse for correct order)
  const remainingBudget = budget - usedTokens;
  const fittingMessages: ContextMessage[] = [];
  let messageTokens = 0;

  // Iterate from newest to oldest
  for (let i = messages.length - 1; i >= 0; i--) {
    const msg = messages[i];
    const msgTokens = msg.tokenCount || estimateTokens(msg.content);

    if (messageTokens + msgTokens > remainingBudget) {
      break; // No more room
    }

    fittingMessages.unshift(msg); // Add to front (maintain order)
    messageTokens += msgTokens;
  }

  result.push(...fittingMessages);

  return result;
}

/**
 * Determine if conversation history needs trimming.
 * Returns the number of messages that don't fit in the context window.
 */
export function getTrimmingInfo(
  config: ContextWindowConfig,
  messages: ContextMessage[]
): { needsTrimming: boolean; messagesToTrim: number; totalTokens: number } {
  let usedTokens =
    estimateTokens(config.systemPrompt) +
    estimateTokens(config.ragContext || "");
  const budget = config.maxTokens - config.responseBuffer;

  let totalTokens = usedTokens;
  let fittingCount = 0;

  for (let i = messages.length - 1; i >= 0; i--) {
    const msgTokens =
      messages[i].tokenCount || estimateTokens(messages[i].content);
    totalTokens += msgTokens;
    if (usedTokens + msgTokens <= budget) {
      usedTokens += msgTokens;
      fittingCount++;
    }
  }

  const messagesToTrim = messages.length - fittingCount;

  return {
    needsTrimming: messagesToTrim > 0,
    messagesToTrim,
    totalTokens,
  };
}
