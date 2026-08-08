import { NextRequest } from "next/server";

const BACKEND_URL = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ sessionId: string }> }
) {
  const { sessionId } = await params;
  const upstream = await fetch(`${BACKEND_URL}/api/workflow/${sessionId}/stream`, {
    headers: { Accept: "text/event-stream" },
    cache: "no-store",
  });

  if (!upstream.ok || !upstream.body) {
    return new Response(await upstream.text(), { status: upstream.status });
  }

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Cache-Control": "no-cache, no-transform",
      Connection: "keep-alive",
      "Content-Type": "text/event-stream",
    },
  });
}
