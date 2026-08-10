import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import fs from "fs";
import path from "path";

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { id } = await params;

  try {
    // Look in the backend's data/projects folder
    const dataDir = path.join(process.cwd(), "..", "data", "projects");
    if (!fs.existsSync(dataDir)) {
      return NextResponse.json({ checkpoints: [] });
    }

    const files = fs.readdirSync(dataDir);
    
    const checkpoints = files
      .filter(f => f.endsWith(".blend") && f !== `${id}.blend` && !f.match(/^[a-z0-9]{25}\.blend$/))
      .map(f => ({
        name: f.replace(".blend", ""),
        path: `data/projects/${f}`,
        time: fs.statSync(path.join(dataDir, f)).mtime.toISOString(),
      }))
      .sort((a, b) => new Date(b.time).getTime() - new Date(a.time).getTime());

    return NextResponse.json({ checkpoints });
  } catch (error) {
    console.error(error);
    return NextResponse.json({ error: "Failed to list checkpoints" }, { status: 500 });
  }
}
