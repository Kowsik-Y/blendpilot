import { auth } from "@/lib/auth";
import { decrypt } from "@/lib/encryption";
import { RAGService, type IngestDocumentPayload } from "@/lib/rag";
import { db } from "@/lib/db";
import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  try {
    const session = await auth();
    const body = await req.json();
    const { documents } = body as { documents: IngestDocumentPayload[] };

    if (!documents || !Array.isArray(documents) || documents.length === 0) {
      return NextResponse.json(
        { error: "Must provide a non-empty 'documents' array." },
        { status: 400 }
      );
    }

    let apiKey: string | undefined;
    let baseUrl: string | undefined;

    if (session?.user?.id) {
      const settings = await db.userSettings.findUnique({
        where: { userId: session.user.id },
      });
      if (settings?.llmApiKey) {
        apiKey = decrypt(settings.llmApiKey);
        baseUrl = settings.llmBaseUrl || undefined;
      }
    }

    const rag = new RAGService({ apiKey, baseUrl });
    const count = await rag.ingestDocuments(documents);

    return NextResponse.json({
      success: true,
      ingestedChunks: count,
      stats: rag.getStats(),
    });
  } catch (error: unknown) {
    const msg = error instanceof Error ? error.message : "Ingestion failed";
    return NextResponse.json({ error: msg }, { status: 500 });
  }
}
