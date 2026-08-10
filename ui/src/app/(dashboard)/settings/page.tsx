"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";
import {
  Key,
  Layers,
  Sparkles,
  CheckCircle2,
  Database,
  Cpu,
  RefreshCw,
  Box,
} from "lucide-react";
import { DEFAULT_MODELS, type LLMProvider } from "@/types/llm";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

export default function SettingsPage() {
  const [provider, setProvider] = useState<LLMProvider>("openai");
  const [model, setModel] = useState("gpt-4o");
  const [apiKey, setApiKey] = useState("");
  const [maskedKey, setMaskedKey] = useState("");
  const [tavilyApiKey, setTavilyApiKey] = useState("");
  const [maskedTavilyKey, setMaskedTavilyKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [temperature, setTemperature] = useState(0.0);
  const [maxTokens, setMaxTokens] = useState(4096);
  const [contextWindowSize, setContextWindowSize] = useState(128000);
  const [ragEnabled, setRagEnabled] = useState(true);
  const [ragTopK, setRagTopK] = useState(4);
  const [blenderHost, setBlenderHost] = useState("127.0.0.1");
  const [blenderPort, setBlenderPort] = useState(9876);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [ragStats, setRagStats] = useState<{ totalChunks: number; categoryCounts: Record<string, number> } | null>(null);

  // Load existing settings
  const loadSettings = async () => {
    try {
      const res = await fetch("/api/settings");
      if (res.ok) {
        const data = await res.json();
        setProvider((data.llmProvider as LLMProvider) || "openai");
        setModel(data.llmModel || "gpt-4o");
        setMaskedKey(data.llmApiKeyMasked || "");
        setBaseUrl(data.llmBaseUrl || "");
        setTemperature(data.llmTemperature ?? 0.0);
        setMaxTokens(data.llmMaxTokens ?? 4096);
        setContextWindowSize(data.contextWindowSize ?? 128000);
        setRagEnabled(data.ragEnabled ?? true);
        setRagTopK(data.ragTopK ?? 4);
        setMaskedTavilyKey(data.tavilyApiKeyMasked || "");
        setBlenderHost(data.blenderHost || "127.0.0.1");
        setBlenderPort(data.blenderPort ?? 9876);
      }
    } catch {
      toast.error("Failed to load user settings");
    } finally {
      setLoading(false);
    }
  };

  const loadRagStats = async () => {
    try {
      const res = await fetch("/api/rag");
      if (res.ok) {
        const data = await res.json();
        setRagStats(data);
      }
    } catch {
      // Ignore
    }
  };

  useEffect(() => {
    void Promise.resolve().then(async () => {
      await loadSettings();
      await loadRagStats();
    });
  }, []);

  const handleSave = async (shouldTest = false) => {
    if (shouldTest) setTesting(true);
    else setSaving(true);

    try {
      const res = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          llmProvider: provider,
          llmModel: model,
          llmApiKey: apiKey || undefined,
          llmBaseUrl: baseUrl,
          llmTemperature: temperature,
          llmMaxTokens: maxTokens,
          contextWindowSize,
          ragEnabled,
          ragTopK,
          tavilyApiKey: tavilyApiKey || undefined,
          blenderHost,
          blenderPort,
          shouldTestConnection: shouldTest,
        }),
      });

      const data = await res.json();
      if (!res.ok) {
        toast.error(data.error || "Save failed");
        return;
      }

      if (data.llmApiKeyMasked) {
        setMaskedKey(data.llmApiKeyMasked);
        setApiKey("");
      }
      
      if (data.tavilyApiKeyMasked) {
        setMaskedTavilyKey(data.tavilyApiKeyMasked);
        setTavilyApiKey("");
      }

      if (shouldTest) {
        toast.success("✅ Connection test succeeded! Settings saved.");
      } else {
        toast.success("Settings saved successfully.");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Save failed";
      toast.error(msg);
    } finally {
      setSaving(false);
      setTesting(false);
    }
  };

  const handleReindexRag = async () => {
    try {
      toast.info("Re-indexing baseline Blender knowledge base...");
      const res = await fetch("/api/rag");
      if (res.ok) {
        const data = await res.json();
        setRagStats(data);
        toast.success(`RAG indexed ${data.totalChunks} knowledge chunks!`);
      }
    } catch {
      toast.error("Failed to re-index RAG");
    }
  };

  if (loading) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        Loading settings...
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6 bg-background text-foreground">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">System Settings</h1>
          <p className="text-sm text-muted-foreground">
            Configure your LLM provider credentials, RAG context window, and Blender bridge.
          </p>
        </div>
        <Badge variant="outline" className="bg-muted border-border text-foreground">
          AES-256 Encrypted
        </Badge>
      </div>

      <Tabs defaultValue="llm" className="space-y-4">
        <TabsList className="h-fit!">
          <TabsTrigger value="llm" className="gap-2 py-2 px-3">
            <Key className="w-4 h-4" />
            <span>LLM & BYO API Keys</span>
          </TabsTrigger>
          <TabsTrigger value="rag" className="gap-2 py-2 px-3">
            <Database className="w-4 h-4" />
            <span>RAG & Memory</span>
          </TabsTrigger>
          <TabsTrigger value="bridge" className="gap-2 py-2 px-3">
            <Box className="w-4 h-4" />
            <span>Blender Bridge</span>
          </TabsTrigger>
        </TabsList>

        {/* LLM Configuration Tab */}
        <TabsContent value="llm" className="space-y-4">
          <Card className="border-border bg-card text-card-foreground">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-primary" />
                LLM Provider & Authentication
              </CardTitle>
              <CardDescription className="text-muted-foreground">
                Supply your API key. Keys are encrypted at rest with AES-256-GCM and never exposed to the client.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Provider</Label>
                  <Select
                    value={provider}
                    onValueChange={(value) => {
                      const p = value as LLMProvider;
                      setProvider(p);
                      if (DEFAULT_MODELS[p]?.[0]) {
                        setModel(DEFAULT_MODELS[p][0].id);
                      }
                    }}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select provider" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="openai">OpenAI (GPT-4o, GPT-4o Mini)</SelectItem>
                      <SelectItem value="anthropic">Anthropic (Claude Sonnet 4, Claude 3.5)</SelectItem>
                      <SelectItem value="custom">Custom / Ollama / OpenRouter / vLLM</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Model Name</Label>
                  {provider === "custom" ? (
                    <Input
                      placeholder="e.g. llama3.3:70b, mistral-large"
                      value={model}
                      onChange={(e) => setModel(e.target.value)}
                      className="bg-background border-input"
                    />
                  ) : (
                    <div className="space-y-2">
                      <Select
                        value={DEFAULT_MODELS[provider]?.some(m => m.id === model) ? model : "custom-input"}
                        onValueChange={(value) => {
                          if (value && value !== "custom-input") {
                            setModel(value);
                          } else {
                            setModel("");
                          }
                        }}
                      >
                        <SelectTrigger className="w-full">
                          <SelectValue placeholder="Select model" />
                        </SelectTrigger>
                        <SelectContent>
                          {DEFAULT_MODELS[provider]?.map((m) => (
                            <SelectItem key={m.id} value={m.id}>
                              {m.name} ({m.contextWindow.toLocaleString()} tokens)
                            </SelectItem>
                          ))}
                          <SelectItem value="custom-input">Custom Model...</SelectItem>
                        </SelectContent>
                      </Select>
                      
                      {!DEFAULT_MODELS[provider]?.some(m => m.id === model) && (
                        <Input
                          placeholder={`Enter custom ${provider} model name`}
                          value={model}
                          onChange={(e) => setModel(e.target.value)}
                          className="bg-background border-input"
                        />
                      )}
                    </div>
                  )}
                </div>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <Label>API Key</Label>
                  {maskedKey && (
                    <span className="text-xs text-foreground flex items-center gap-1 font-mono">
                      <CheckCircle2 className="w-3.5 h-3.5 text-primary" />
                      Configured: {maskedKey}
                    </span>
                  )}
                </div>
                <Input
                  type="password"
                  placeholder={maskedKey ? "Leave blank to keep existing key" : "sk-..."}
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  className="bg-background border-input font-mono"
                />
              </div>

              <div className="space-y-2">
                <Label>Custom Base URL (Optional)</Label>
                <Input
                  placeholder="https://api.openai.com/v1 or http://localhost:11434/v1"
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                  className="bg-background border-input"
                />
                <p className="text-[11px] text-muted-foreground">
                  For Ollama use <code className="text-foreground">http://localhost:11434/v1</code>, for OpenRouter use <code className="text-foreground">https://openrouter.ai/api/v1</code>.
                </p>
              </div>


            </CardContent>
            <CardFooter className="flex justify-between border-t border-border pt-4">
              <Button
                variant="outline"
                onClick={() => handleSave(true)}
                disabled={saving || testing}
                className="border-border text-foreground"
              >
                {testing ? "Testing..." : "Test Connection"}
              </Button>
              <Button
                onClick={() => handleSave(false)}
                disabled={saving || testing}
                className="bg-primary text-primary-foreground hover:bg-primary/90"
              >
                {saving ? "Saving..." : "Save Settings"}
              </Button>
            </CardFooter>
          </Card>
        </TabsContent>

        {/* RAG & Memory Tab */}
        <TabsContent value="rag" className="space-y-4">
          <Card className="border-border bg-card text-card-foreground">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Layers className="w-5 h-5 text-primary" />
                RAG Retrieval & Context Window Memory
              </CardTitle>
              <CardDescription className="text-muted-foreground">
                Retrieval-Augmented Generation injects relevant Blender Python API documentation, material specs, and project history into agent prompts.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="p-3.5 rounded-xl bg-muted border border-border flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-foreground">Enable RAG Retrieval</p>
                  <p className="text-xs text-muted-foreground">
                    Automatically augment prompts with Blender 3D knowledge & project context
                  </p>
                </div>
                <input
                  type="checkbox"
                  checked={ragEnabled}
                  onChange={(e) => setRagEnabled(e.target.checked)}
                  className="w-5 h-5 accent-primary rounded cursor-pointer"
                />
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Context Window Size (Tokens)</Label>
                  <Input
                    type="number"
                    value={contextWindowSize}
                    onChange={(e) => setContextWindowSize(parseInt(e.target.value) || 128000)}
                    className="bg-background border-input font-mono"
                  />
                  <p className="text-[11px] text-muted-foreground">
                    Sliding window trims old messages to stay under budget.
                  </p>
                </div>

                <div className="space-y-2">
                  <Label>RAG Top-K Chunks</Label>
                  <Input
                    type="number"
                    min="1"
                    max="10"
                    value={ragTopK}
                    onChange={(e) => setRagTopK(parseInt(e.target.value) || 4)}
                    className="bg-background border-input font-mono"
                  />
                  <p className="text-[11px] text-muted-foreground">
                    Number of similar knowledge chunks to retrieve per prompt.
                  </p>
                </div>
              </div>

              {/* Tavily API Key */}
              <div className="space-y-2 pt-4 border-t border-border">
                <div className="flex items-center justify-between">
                  <Label>Tavily Search API Key</Label>
                  {maskedTavilyKey && (
                    <span className="text-xs text-foreground flex items-center gap-1 font-mono">
                      <CheckCircle2 className="w-3.5 h-3.5 text-primary" />
                      Configured: {maskedTavilyKey}
                    </span>
                  )}
                </div>
                <Input
                  type="password"
                  placeholder={maskedTavilyKey ? "Leave blank to keep existing key" : "tvly-..."}
                  value={tavilyApiKey}
                  onChange={(e) => setTavilyApiKey(e.target.value)}
                  className="bg-background border-input font-mono"
                />
                <p className="text-[11px] text-muted-foreground">
                  Required for ResearchAgent dynamic web search.
                </p>
              </div>

              {/* RAG Knowledge Store Status */}
              <div className="pt-3 border-t border-border">
                <div className="flex items-center justify-between mb-2">
                  <Label className="flex items-center gap-1.5">
                    <Cpu className="w-4 h-4 text-primary" />
                    Knowledge Vector Store Status
                  </Label>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleReindexRag}
                    className="h-7 text-xs text-muted-foreground hover:text-foreground"
                  >
                    <RefreshCw className="w-3.5 h-3.5 mr-1" />
                    Re-index Baseline
                  </Button>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  <div className="p-3 rounded-lg bg-muted border border-border text-center">
                    <p className="text-xs text-muted-foreground">Total Chunks</p>
                    <p className="text-lg font-bold text-foreground">{ragStats?.totalChunks || 4}</p>
                  </div>
                  <div className="p-3 rounded-lg bg-muted border border-border text-center">
                    <p className="text-xs text-muted-foreground">Blender Docs</p>
                    <p className="text-lg font-bold text-foreground">{ragStats?.categoryCounts?.blender_docs || 4}</p>
                  </div>
                  <div className="p-3 rounded-lg bg-muted border border-border text-center">
                    <p className="text-xs text-muted-foreground">Project Context</p>
                    <p className="text-lg font-bold text-foreground">{ragStats?.categoryCounts?.project_context || 0}</p>
                  </div>
                  <div className="p-3 rounded-lg bg-muted border border-border text-center">
                    <p className="text-xs text-muted-foreground">Embeddings</p>
                    <p className="text-xs font-semibold text-foreground mt-1">Active</p>
                  </div>
                </div>
              </div>
            </CardContent>
            <CardFooter className="flex justify-end border-t border-border pt-4">
              <Button
                onClick={() => handleSave(false)}
                disabled={saving}
                className="bg-primary text-primary-foreground hover:bg-primary/90"
              >
                {saving ? "Saving..." : "Save RAG Settings"}
              </Button>
            </CardFooter>
          </Card>
        </TabsContent>

        {/* Blender Bridge Tab */}
        <TabsContent value="bridge" className="space-y-4">
          <Card className="border-border bg-card text-card-foreground">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Box className="w-5 h-5 text-primary" />
                Blender Bridge Connection
              </CardTitle>
              <CardDescription className="text-muted-foreground">
                Connects to the local BlendPilot Blender Add-on HTTP Bridge running on port 9876.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Bridge Host</Label>
                  <Input
                    value={blenderHost}
                    onChange={(e) => setBlenderHost(e.target.value)}
                    className="bg-background border-input font-mono"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Bridge Port</Label>
                  <Input
                    type="number"
                    value={blenderPort}
                    onChange={(e) => setBlenderPort(parseInt(e.target.value) || 9876)}
                    className="bg-background border-input font-mono"
                  />
                </div>
              </div>

              <div className="p-3.5 rounded-xl bg-muted border border-border text-xs text-muted-foreground space-y-1">
                <p className="font-semibold text-foreground">How to start Blender Bridge:</p>
                <p>1. Open Blender 4.x</p>
                <p>2. Install and enable the <code className="text-primary">blendpilot</code> addon</p>
                <p>3. In the 3D View Sidebar (N-panel), click <strong className="text-foreground">&quot;Start Bridge Server&quot;</strong></p>
              </div>
            </CardContent>
            <CardFooter className="flex justify-end border-t border-border pt-4">
              <Button
                onClick={() => handleSave(false)}
                disabled={saving}
                className="bg-primary text-primary-foreground hover:bg-primary/90"
              >
                {saving ? "Saving..." : "Save Bridge Settings"}
              </Button>
            </CardFooter>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
