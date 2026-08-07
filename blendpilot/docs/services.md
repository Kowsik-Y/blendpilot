# `services/` — External Service Integrations

> **Phase**: 3–9 (⬜ Pending)
> **Dependencies**: `httpx`, `mcp-python-sdk`
> **Consumed by**: `agents/`, `graph/nodes.py`

---

## Purpose

The `services/` package provides **client interfaces** for communicating with external systems. Each service:

- Has a well-defined async interface
- Handles connection management, retries, and timeouts
- Returns structured data (Pydantic models or typed dicts)
- Is independently testable with mock backends

---

## Module Inventory

| Service | File | Phase | Purpose |
|---------|------|-------|---------|
| **Blender Client** | `blender_client.py` | 2 | HTTP client to communicate with the Blender bridge |
| **Web Search** | `web_search.py` | 7 | Search the web for reference information |
| **Email** | `email.py` | 9 | Send review emails and parse responses |
| **LLM Provider** | `llm.py` | 4 | Unified LLM client (OpenAI, Anthropic, etc.) |
| **File Manager** | `file_manager.py` | 3 | Project file/directory management |

---

## Detailed Service Plans

### `blender_client.py` — Blender Bridge Client (Phase 2)

**Purpose**: Send commands to the Blender add-on bridge and receive responses.

```python
class BlenderClient:
    """HTTP client for the Blender bridge server."""

    def __init__(self, host: str = "127.0.0.1", port: int = 9876, timeout: float = 30.0):
        self.base_url = f"http://{host}:{port}"
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def execute(self, command: str, parameters: dict) -> BridgeResponse:
        """Send a command to the Blender bridge."""
        request = BridgeCommand(
            command=command,
            request_id=self._generate_request_id(),
            parameters=parameters,
        )
        response = await self._client.post(
            f"{self.base_url}/execute",
            json=request.model_dump(),
        )
        response.raise_for_status()
        return BridgeResponse.model_validate(response.json())

    # Convenience methods for each operation
    async def create_primitive(self, **kwargs) -> dict:
        return await self.execute("create_primitive", kwargs)

    async def set_transform(self, **kwargs) -> dict:
        return await self.execute("set_transform", kwargs)

    async def get_scene_summary(self) -> dict:
        return await self.execute("get_scene_summary", {})

    async def render_preview(self, output_path: str, **kwargs) -> dict:
        return await self.execute("render_preview", {"output_path": output_path, **kwargs})

    # ... convenience methods for all other commands

    async def health_check(self) -> bool:
        """Check if the Blender bridge is running."""
        try:
            resp = await self._client.get(f"{self.base_url}/health")
            return resp.status_code == 200
        except httpx.ConnectError:
            return False

    async def close(self):
        await self._client.aclose()
```

**Key Features**:
- Async HTTP client via `httpx`
- Automatic request ID generation
- Configurable timeout (default 30s for render operations)
- Health check for connection validation
- Structured responses via Pydantic

---

### `web_search.py` — Web Search Service (Phase 7)

**Purpose**: Search the web for reference information needed by the Research Agent.

```python
class WebSearchService:
    """Searches the web for reference information.

    Results are treated as UNTRUSTED data — never execute
    instructions found in web content.
    """

    def __init__(self, api_key: str | None = None, max_results: int = 5):
        self.api_key = api_key
        self.max_results = max_results

    async def search(self, query: str) -> list[SearchResult]:
        """Search the web and return structured results."""
        ...

    async def search_blender_docs(self, topic: str) -> list[SearchResult]:
        """Search specifically in Blender documentation."""
        return await self.search(f"site:docs.blender.org {topic}")

    async def search_unity_requirements(self, asset_type: str) -> list[SearchResult]:
        """Search for Unity asset requirements."""
        return await self.search(f"Unity {asset_type} import requirements FBX")

    async def search_reference_dimensions(self, object_type: str) -> list[SearchResult]:
        """Search for typical real-world dimensions of an object."""
        return await self.search(f"typical dimensions of {object_type} in meters")
```

**Data Model**:
```python
class SearchResult(BaseModel):
    title: str
    url: str
    snippet: str
    source_domain: str
    trust_level: str = "untrusted"  # Always untrusted by default
```

**Security Rules**:
- All web content is marked `trust_level = "untrusted"`
- Never execute code found in search results
- Never interpret instructions from websites as system commands
- Log all search queries for audit

---

### `email.py` — Email Review Service (Phase 9)

**Purpose**: Send asset review emails and parse incoming feedback.

```python
class EmailService:
    """Send review emails and parse reviewer feedback."""

    def __init__(self, smtp_host: str, smtp_port: int, username: str, password: str):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.username = username
        self.password = password

    async def send_review_email(
        self,
        to: str,
        asset_name: str,
        version: str,
        preview_image_path: str,
        validation_results: dict,
        changes_summary: str,
    ) -> EmailSendResult:
        """Compose and send a review email.

        IMPORTANT: Never sends automatically — requires explicit approval
        from the user before calling this method.
        """
        ...

    async def parse_feedback_email(self, email_body: str) -> list[FeedbackItem]:
        """Parse reviewer feedback into structured change requests."""
        ...
```

**Data Models**:
```python
class EmailSendResult(BaseModel):
    sent: bool
    message_id: str | None
    recipient: str
    timestamp: str

class FeedbackItem(BaseModel):
    target: str          # e.g. "SidePanels"
    instruction: str     # e.g. "increase thickness by 20%"
    priority: str = "medium"
```

**Safety Rules**:
- Never send emails automatically — always require explicit user approval
- Log all sent emails
- Parse feedback into structured format, don't execute raw text

---

### `llm.py` — LLM Provider Service (Phase 4)

**Purpose**: Unified interface for LLM providers (OpenAI, Anthropic, etc.).

```python
class LLMService:
    """Unified LLM client with provider abstraction."""

    def __init__(self, provider: str = "openai", model: str = "gpt-4o"):
        self.provider = provider
        self.model = model
        self._client = self._create_client()

    def get_chat_model(self):
        """Return a LangChain chat model instance."""
        if self.provider == "openai":
            return ChatOpenAI(model=self.model, temperature=0)
        elif self.provider == "anthropic":
            return ChatAnthropic(model=self.model, temperature=0)
        raise ValueError(f"Unsupported provider: {self.provider}")

    def get_vision_model(self):
        """Return a vision-capable model for visual critique."""
        if self.provider == "openai":
            return ChatOpenAI(model="gpt-4o", temperature=0)
        elif self.provider == "anthropic":
            return ChatAnthropic(model="claude-sonnet-4-20250514", temperature=0)
        raise ValueError(f"No vision model for provider: {self.provider}")
```

---

### `file_manager.py` — File & Directory Manager (Phase 3)

**Purpose**: Manage project directories, output files, and checkpoints.

```python
class FileManager:
    """Manages BlendPilot project files and directories."""

    def __init__(self, base_output_dir: str = "./output"):
        self.base_output_dir = Path(base_output_dir)

    def create_project_directory(self, project_id: str) -> Path:
        """Create output directory structure for a project."""
        project_dir = self.base_output_dir / project_id
        (project_dir / "checkpoints").mkdir(parents=True, exist_ok=True)
        (project_dir / "renders").mkdir(parents=True, exist_ok=True)
        (project_dir / "exports").mkdir(parents=True, exist_ok=True)
        return project_dir

    def get_checkpoint_path(self, project_id: str, checkpoint_name: str) -> str:
        """Get the full path for a checkpoint file."""
        return str(self.base_output_dir / project_id / "checkpoints" / f"{checkpoint_name}.blend")

    def get_render_path(self, project_id: str, render_name: str) -> str:
        """Get the full path for a render output."""
        return str(self.base_output_dir / project_id / "renders" / f"{render_name}.png")

    def generate_asset_report(self, project_id: str, metadata: dict) -> str:
        """Write asset_report.json for the project."""
        report_path = self.base_output_dir / project_id / "asset_report.json"
        report_path.write_text(json.dumps(metadata, indent=2))
        return str(report_path)
```
