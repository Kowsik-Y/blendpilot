import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";

const BACKEND_URL = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";

export async function GET(req: NextRequest) {
  try {
    const session = await auth();
    if (!session?.user?.id) {
      return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
    }

    const url = new URL(req.url);
    const projectId = url.searchParams.get("projectId");
    const backendUrl = projectId 
      ? `${BACKEND_URL}/api/workflow/scene?project_id=${projectId}` 
      : `${BACKEND_URL}/api/workflow/scene`;

    const res = await fetch(backendUrl, {
      method: "GET",
      headers: { "Content-Type": "application/json" },
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error: unknown) {
    const message = error instanceof Error ? error.message : "Failed to connect to Python backend";
    return NextResponse.json(
      { success: false, error: message },
      { status: 500 }
    );
  }
}
