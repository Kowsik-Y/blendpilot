import { NextRequest } from "next/server";

const BACKEND_URL = process.env.BACKEND_API_URL || "http://127.0.0.1:8000";

export const dynamic = "force-dynamic";

export async function GET(
  _req: NextRequest,
  { params }: { params: Promise<{ assetName: string }> }
) {
  const { assetName } = await params;
  const upstream = await fetch(`${BACKEND_URL}/api/export/${assetName}/download`, {
    cache: "no-store",
  });

  if (!upstream.ok || !upstream.body) {
    return new Response(await upstream.text(), { status: upstream.status });
  }

  return new Response(upstream.body, {
    status: upstream.status,
    headers: {
      "Content-Disposition": upstream.headers.get("Content-Disposition") || `attachment; filename=${assetName}_bundle.zip`,
      "Content-Type": upstream.headers.get("Content-Type") || "application/zip",
    },
  });
}
