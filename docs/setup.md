# Setup & Installation

BlendPilot provides a flexible setup, allowing it to run entirely headless for automated pipelines or connected to a live GUI for interactive monitoring.

## 1. Prerequisites

- **Python:** 3.10 or higher.
- **Blender:** 4.0 or 5.2+ (Recommended).
- **API Keys:** Add your LLM keys (OpenAI/Anthropic) to a `.env` file.

## 2. Environment Setup

Clone the repository and set up the isolated Python virtual environment.

```bash
# Clone the repository
git clone https://github.com/Kowsik-Y/blendpilot.git
cd blendpilot

# Setup Python Virtual Environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Running the System

You have multiple ways to interact with BlendPilot:

### Web Interface
Provides a glassmorphic Three.js 3D viewport and node graph visualizer.
```bash
.venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```
Navigate to `http://localhost:8000`.

### CLI Application
For rapid testing and batch benchmarking.
```bash
# Single prompt execution
.venv/bin/python cli.py "Create a low-poly sci-fi supply crate for Unity. Dimensions: 1.0m x 0.7m x 0.6m."

# Interactive prompt session
.venv/bin/python cli.py -i
```

## 4. Live Blender Bridge Mode

To physically see BlendPilot manipulate geometry inside Blender:

1. Open Blender.
2. Open the Text Editor in Blender, load `scripts/start_blender_bridge.py`, and run it.
3. *Alternatively*, install the `blender_addon/` folder as a standard `.zip` addon in Blender Preferences.

The Python backend will automatically detect the local bridge on `localhost:8000` and stream commands directly to the active session.
