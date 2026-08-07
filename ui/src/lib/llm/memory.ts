/**
 * Conversation Memory Manager
 *
 * Handles persistent conversation storage and retrieval.
 * Integrates with context window manager for token budgeting.
 */

import { db } from "@/lib/db";
import { estimateTokens } from "@/lib/llm/context-window";

export async function saveMessage(
  sessionId: string,
  role: "user" | "assistant" | "system",
  content: string,
  metadata?: Record<string, unknown>
) {
  const tokenCount = estimateTokens(content);

  const message = await db.message.create({
    data: {
      sessionId,
      role,
      content,
      metadata: metadata ? JSON.stringify(metadata) : null,
      tokenCount,
    },
  });

  // Update session timestamp
  await db.chatSession.update({
    where: { id: sessionId },
    data: { updatedAt: new Date() },
  });

  return message;
}

export async function getSessionMessages(sessionId: string) {
  return db.message.findMany({
    where: { sessionId },
    orderBy: { createdAt: "asc" },
  });
}

export async function getSessionTokenCount(sessionId: string): Promise<number> {
  const result = await db.message.aggregate({
    where: { sessionId },
    _sum: { tokenCount: true },
  });
  return result._sum.tokenCount || 0;
}

export async function createSession(userId: string, title?: string) {
  return db.chatSession.create({
    data: {
      userId,
      title: title || "New Chat",
    },
  });
}

export async function getUserSessions(userId: string) {
  return db.chatSession.findMany({
    where: { userId },
    orderBy: { updatedAt: "desc" },
    include: {
      _count: { select: { messages: true } },
    },
  });
}

export async function deleteSession(sessionId: string, userId: string) {
  return db.chatSession.deleteMany({
    where: { id: sessionId, userId },
  });
}

export async function autoTitleSession(
  sessionId: string,
  firstMessage: string
) {
  // Generate title from first message (first 50 chars)
  const title =
    firstMessage.length > 50
      ? firstMessage.slice(0, 47) + "..."
      : firstMessage;

  await db.chatSession.update({
    where: { id: sessionId },
    data: { title },
  });
}
