import { NextRequest, NextResponse } from "next/server";
import { promises as fs } from "fs";
import path from "path";

export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const filePath = searchParams.get("path");

  if (!filePath) {
    return new NextResponse("Missing path parameter", { status: 400 });
  }

  try {
    // Only allow serving files with common image extensions for security
    const ext = path.extname(filePath).toLowerCase();
    const allowedExts = [".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg"];
    
    if (!allowedExts.includes(ext)) {
      return new NextResponse("Invalid file type", { status: 403 });
    }

    const data = await fs.readFile(filePath);
    
    let contentType = "image/png";
    if (ext === ".jpg" || ext === ".jpeg") contentType = "image/jpeg";
    else if (ext === ".gif") contentType = "image/gif";
    else if (ext === ".webp") contentType = "image/webp";
    else if (ext === ".svg") contentType = "image/svg+xml";

    return new NextResponse(data, {
      headers: {
        "Content-Type": contentType,
        "Cache-Control": "public, max-age=31536000, immutable",
      },
    });
  } catch (error) {
    console.error(`Failed to serve local image at ${filePath}:`, error);
    return new NextResponse("File not found or unreadable", { status: 404 });
  }
}
