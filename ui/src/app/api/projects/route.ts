import { auth } from "@/lib/auth";
import { db } from "@/lib/db";
import { NextRequest, NextResponse } from "next/server";

export async function GET() {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const projects = await db.project.findMany({
    where: { userId: session.user.id },
    orderBy: { updatedAt: "desc" },
    include: {
      sessions: {
        select: { id: true, title: true },
      },
    },
  });

  return NextResponse.json(projects);
}

export async function POST(req: NextRequest) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { name, designSpec, outputDir } = await req.json();

  if (!name) {
    return NextResponse.json({ error: "Project name is required" }, { status: 400 });
  }

  const project = await db.project.create({
    data: {
      userId: session.user.id,
      name,
      designSpec: designSpec ? JSON.stringify(designSpec) : null,
      outputDir,
      status: "active",
    },
  });

  return NextResponse.json(project);
}
