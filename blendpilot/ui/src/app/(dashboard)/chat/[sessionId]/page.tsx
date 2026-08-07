import { auth } from "@/lib/auth";
import { db } from "@/lib/db";
import { ChatInterface } from "@/components/chat/chat-interface";
import { notFound, redirect } from "next/navigation";
import { type ChatMessage } from "@/types/chat";

export default async function ChatSessionPage({
  params,
}: {
  params: Promise<{ sessionId: string }>;
}) {
  const session = await auth();
  if (!session?.user?.id) {
    redirect("/login");
  }

  const { sessionId } = await params;

  const chatSession = await db.chatSession.findFirst({
    where: { id: sessionId, userId: session.user.id },
    include: {
      messages: {
        orderBy: { createdAt: "asc" },
      },
    },
  });

  if (!chatSession) {
    notFound();
  }

  const formattedMessages: ChatMessage[] = chatSession.messages.map((m) => ({
    id: m.id,
    sessionId: m.sessionId,
    role: m.role as "user" | "assistant" | "system",
    content: m.content,
    metadata: m.metadata ? JSON.parse(m.metadata) : undefined,
    tokenCount: m.tokenCount,
    createdAt: m.createdAt,
  }));

  return (
    <div className="h-full flex flex-col">
      <ChatInterface sessionId={sessionId} initialMessages={formattedMessages} />
    </div>
  );
}
