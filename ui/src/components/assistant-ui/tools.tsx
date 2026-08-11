import { makeAssistantToolUI } from "@assistant-ui/react";
import { WebSearch } from "@/components/elements/web-search";
import { ResearchReport } from "@/components/elements/research-report";
import { ImageGeneration } from "@/components/elements/image-generation";

export const WebSearchToolUI = makeAssistantToolUI({
  toolName: "web_search",
  render: ({ args, status, result }) => {
    const isSearching = status.type === "running" || status.type === "requires-action";
    let searchResults: Array<{ title: string; domain: string; url?: string }> = [];
    
    if (result) {
      let parsed: any = result;
      if (typeof result === "string") {
        try {
          parsed = JSON.parse(result);
        } catch (e) {
          // Result is just a string (e.g. "Success"), not JSON
        }
      }
      
      if (parsed && typeof parsed === "object" && parsed.results && Array.isArray(parsed.results)) {
        searchResults = parsed.results.map((r: any) => ({
          title: r.title || "Unknown Title",
          domain: r.source_domain || (r.url ? new URL(r.url).hostname : "unknown"),
          url: r.url
        }));
      }
    }

    return (
      <WebSearch
        query={(args.query as string) || "Searching..."}
        results={searchResults}
        visibleResults={3}
        searching={isSearching}
        cycle={1}
      />
    );
  },
});

export const ResearchReportToolUI = makeAssistantToolUI({
  toolName: "research_report",
  render: ({ args, status }) => {
    return (
      <ResearchReport
        title={(args.topic as string) || "Researching..."}
        sections={[]}
        sourcesRead={0}
        className="w-full"
      />
    );
  },
});

export const ImageGenerationToolUI = makeAssistantToolUI({
  toolName: "image_generation",
  render: ({ args, status, result }) => {
    let images: Array<{ url: string; meta?: string }> = [];
    
    if (result) {
      let parsed: any = result;
      if (typeof result === "string") {
        try {
          parsed = JSON.parse(result);
        } catch (e) {
          // Result is just a string
        }
      }
      if (parsed && typeof parsed === "object" && parsed.images && Array.isArray(parsed.images)) {
        images = parsed.images;
      }
    }
    
    return (
      <ImageGeneration
        prompt={(args.prompt as string) || "Generating image..."}
        generating={status.type === "running"}
        className="w-full"
      />
    );
  },
});
