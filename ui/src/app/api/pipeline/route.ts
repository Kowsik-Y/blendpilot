import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { db } from "@/lib/db";

const BACKEND_URL = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";

export async function POST(req: NextRequest) {
  try {
    const session = await auth();
    const body = await req.json();

    // Fetch user settings for API key
    if (session?.user?.id) {
      const settings = await db.userSettings.findUnique({
        where: { userId: session.user.id },
      });
      if (settings) {
        body.overrides = {
          ...body.overrides,
          api_key: settings.llmApiKey,
          provider: settings.llmProvider,
        };
      }
    }

    const res = await fetch(`${BACKEND_URL}/api/workflow/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const data = await res.json();
    return NextResponse.json(data, { status: res.status });
  } catch (error: any) {
    return NextResponse.json(
      { success: false, error: error.message || "Failed to connect to Python backend" },
      { status: 500 }
    );
  }
}

