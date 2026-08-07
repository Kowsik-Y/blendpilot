/**
 * BlendPilot AI — Blender Documentation Knowledge Service
 *
 * Provides domain-specific knowledge chunks for Blender modeling,
 * Python bpy API, modifiers, materials, and low-poly guidelines.
 */

import { type IngestDocumentPayload } from "./types";

export interface TextChunk {
  title: string;
  content: string;
  tokenCount: number;
}

export class BlenderDocsService {
  /**
   * Split a markdown document into semantic chunks based on headings (#, ##, ###).
   */
  static splitMarkdownIntoChunks(markdown: string, defaultTitle: string = "Section"): TextChunk[] {
    const lines = markdown.split("\n");
    const chunks: TextChunk[] = [];

    let currentTitle = defaultTitle;
    let currentLines: string[] = [];

    const flushChunk = () => {
      const content = currentLines.join("\n").trim();
      if (content.length > 20) {
        chunks.push({
          title: currentTitle,
          content,
          tokenCount: Math.ceil(content.length / 4),
        });
      }
      currentLines = [];
    };

    for (const line of lines) {
      if (line.startsWith("#")) {
        flushChunk();
        currentTitle = line.replace(/^#+\s*/, "").trim();
      } else {
        currentLines.push(line);
      }
    }
    flushChunk();

    return chunks;
  }

  /**
   * Built-in knowledge base containing core Blender 3D modeling, PBR, and MCP tool instructions.
   */
  static getBaselineBlenderDocuments(): IngestDocumentPayload[] {
    return [
      {
        source: "blender_docs/primitives.md",
        category: "blender_docs",
        title: "Blender Mesh Primitives Reference",
        content: `
### Mesh Primitives in BlendPilot
- Cube: create_primitive("cube", name, dimensions=[w, d, h], location=[x, y, z])
- Cylinder: create_primitive("cylinder", name, dimensions=[radius*2, radius*2, depth])
- Sphere / UV Sphere: create_primitive("sphere", name, dimensions=[d, d, d])
- IcoSphere: create_primitive("ico_sphere", name, dimensions=[d, d, d])
- Plane: create_primitive("plane", name, dimensions=[w, d, 0])
- Torus: create_primitive("torus", name, dimensions=[major_radius*2, major_radius*2, minor_radius*2])

Rules:
1. Always name primitives descriptively (e.g. "TableTop", "FrontLeftLeg").
2. Dimensions are in meters (width, depth, height).
3. Compute precise Z height so assets rest at z=0 (ground plane).
        `.trim(),
      },
      {
        source: "blender_docs/modifiers.md",
        category: "blender_docs",
        title: "Blender Modifiers Best Practices",
        content: `
### Modifier Types & Usage
1. Bevel: Adds chamfered edges for realism. Typical low-poly width: 0.01m to 0.03m, segments: 1 or 2.
2. Mirror: Duplicates mesh across X/Y/Z axes with clipping enabled. Useful for symmetrical props (tables, chairs, vehicles).
3. Solidify: Gives thickness to single-surface meshes (e.g. sheet metal, hollow crates).
4. Subdivision: Smooths surface. Use sparingly in low-poly pipelines to keep triangle budgets.
5. Boolean: Union, difference, or intersect operations. Must be checked for non-manifold geometry after applying.
6. Decimate: Reduces polygon count to meet triangle budgets.
        `.trim(),
      },
      {
        source: "blender_docs/materials_pbr.md",
        category: "blender_docs",
        title: "Principled BSDF PBR Material Translation",
        content: `
### PBR Material Parameters
- Wood: Base Color (0.4, 0.25, 0.13, 1.0), Metallic: 0.0, Roughness: 0.7
- Dark Metal / Steel: Base Color (0.2, 0.2, 0.22, 1.0), Metallic: 0.9, Roughness: 0.35
- Gold: Base Color (1.0, 0.77, 0.34, 1.0), Metallic: 1.0, Roughness: 0.2
- Red Paint: Base Color (0.85, 0.1, 0.1, 1.0), Metallic: 0.0, Roughness: 0.4
- Emissive Strips: Base Color (0.0, 0.6, 1.0, 1.0), Emission Color: (0.0, 0.8, 1.0, 1.0), Strength: 5.0 to 10.0
- Glass / Transparent: Base Color (0.95, 0.95, 0.95, 1.0), Metallic: 0.0, Roughness: 0.05
        `.trim(),
      },
      {
        source: "blender_docs/qa_standards.md",
        category: "blender_docs",
        title: "Geometry QA & Engine Compatibility Guidelines",
        content: `
### Quality Assurance Rules for Game Engines (Unity, Unreal, Godot, Web)
1. Triangle Budget: Low-poly props must remain within requested limits (e.g., 2,000 - 10,000 tris).
2. Normals: All face normals must point outward with no inverted winding order.
3. Manifold Geometry: Meshes must be watertight without interior intersecting faces or non-manifold edges.
4. Applied Transforms: Scale must be (1.0, 1.0, 1.0) and rotation applied before FBX/GLB export.
5. Pivot Point: Origin should be located at the base center (z=0) for easy placement in game engines.
        `.trim(),
      },
    ];
  }
}
