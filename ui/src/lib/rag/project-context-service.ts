/**
 * BlendPilot — Project Context Service
 *
 * Extracts and formats project specifications, QA reports, and iteration
 * history for retrieval into the LLM context window.
 */

import { db } from "@/lib/db";
import { type IngestDocumentPayload } from "./types";

export class ProjectContextService {
  /**
   * Fetch active project context documents for a user or specific project.
   */
  static async getProjectContextDocuments(
    userId: string,
    projectId?: string
  ): Promise<IngestDocumentPayload[]> {
    const docs: IngestDocumentPayload[] = [];

    const projects = await db.project.findMany({
      where: {
        userId,
        ...(projectId ? { id: projectId } : {}),
      },
      orderBy: { updatedAt: "desc" },
      take: 5,
    });

    for (const p of projects) {
      let specSummary = "";
      if (p.designSpec) {
        try {
          const parsed = JSON.parse(p.designSpec);
          specSummary = `
- Asset Type: ${parsed.asset_type || "Unknown"}
- Target Dimensions: ${JSON.stringify(parsed.dimensions || {})}
- Triangle Limit: ${parsed.triangle_limit || 10000}
- Style: ${parsed.style || "low-poly"}
- Export Format: ${parsed.export_format || "FBX"}
          `.trim();
        } catch {
          specSummary = p.designSpec;
        }
      }

      docs.push({
        source: `project_context/${p.id}`,
        category: "project_context",
        title: `Project Context: ${p.name}`,
        content: `
### Project Summary: ${p.name}
- Status: ${p.status}
- Output Directory: ${p.outputDir || "default"}
- Design Specifications:
${specSummary || "No explicit spec recorded."}
        `.trim(),
        metadata: {
          projectId: p.id,
          userId,
          status: p.status,
        },
      });
    }

    return docs;
  }
}
