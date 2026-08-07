import { auth } from "@/lib/auth";
import { createSession, getUserSessions } from "@/lib/llm/memory";
import { NextRequest, NextResponse } from "next/server";

export async function GET() {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const sessions = await getUserSessions(session.user.id);
  return NextResponse.json(sessions);
}

export async function POST(req: NextRequest) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await req.json().catch(() => ({}));
  const newSession = await createSession(session.user.id, body.title);

  return NextResponse.json(newSession);
}
