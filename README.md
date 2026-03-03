# 🧱 CAD AI Builder — Chat-to-CAD Platform

> **Describe any physical product in plain English → AI generates production-quality 3D geometry → download STL/STEP instantly.**

A full-stack, AI-powered parametric CAD generation platform. Type "iPhone 15 Pro case with camera cutout and USB-C port", and within seconds a fully-parametric, 3D-printable model appears in your browser — adjustable with sliders, exportable in STEP and STL, and editable with further natural language commands. Upload your own CAD files (STEP, IGES, STL, OBJ, 3MF, DXF…) and continue editing them with language.

---

## Table of Contents

1. [Features](#features)
2. [Architecture Overview](#architecture-overview)
3. [Tech Stack](#tech-stack)
4. [Project Structure](#project-structure)
5. [Prerequisites](#prerequisites)
6. [Installation & Setup](#installation--setup)
7. [Running the App](#running-the-app)
8. [Environment Variables](#environment-variables)
9. [API Reference](#api-reference)
10. [CAD File Upload & NLP Editing](#cad-file-upload--nlp-editing)
11. [How the AI Pipeline Works](#how-the-ai-pipeline-works)
12. [Self-Healing Engine](#self-healing-engine)
13. [Parametric System](#parametric-system)
14. [Product Library](#product-library)
15. [Optional Services](#optional-services)
16. [Frontend Architecture](#frontend-architecture)
17. [State Management](#state-management)
18. [Testing](#testing)
19. [Roadmap](#roadmap)
20. [Contributing](#contributing)
21. [License](#license)

---

## Features

### Core

| Feature | Description |
|---|---|
| 🗣️ **Natural Language → 3D Model** | Describe any product; Claude AI writes CadQuery Python that builds real solid geometry |
| 🔁 **Iterative NLP Editing** | Send follow-up messages to modify existing designs ("add ventilation slots", "make it 10mm taller") |
| 📁 **CAD File Upload** | Upload STEP, IGES, STL, OBJ, 3MF, DXF, BRep, PLY, GLB and edit them with language |
| 🎛️ **Live Parameter Sliders** | Every dimension is a named parameter; sliders rebuild the model in seconds (no AI call) |
| 💾 **Dual Export** | Download STL for 3D printing, STEP for CAD editing in FreeCAD/Fusion 360/SolidWorks |
| 🐍 **Parametric Python Script** | Each build also exports a standalone `.py` CadQuery script you can run and modify locally |

### AI & Generation

| Feature | Description |
|---|---|
| 🧠 **Claude Sonnet / Opus** | Uses `claude-opus-4-20250514` by default; configurable via env var |
| 🔥 **High-complexity mode** | 98+ product templates with real-world dimensions; 3 detail tiers (standard / detailed / professional) |
| 🧪 **Completeness analysis** | After generation, AI self-critiques its code and re-enhances if features are missing |
| 🛡️ **Infinite self-healing loop** | CadQuery errors trigger automatic fix retries with 5 graduated strategies (targeted → nuclear) |
| ⚡ **Prompt caching** | Identical prompts return instantly from an in-memory SHA-256 cache (no Al call) |
| 📡 **SSE streaming** | 6-step progress events streamed live to the UI as the model is built |

### UI/UX

| Feature | Description |
|---|---|
| ↔️ **Independent panels** | Chat and 3D preview are fully decoupled — collapse/expand either, drag resize handle |
| 📱 **Mobile tab layout** | On screens < 968 px, chat and preview switch via tabs |
| ↩️ **Undo / Redo** | 20-step history with Ctrl+Z / Ctrl+Shift+Z |
| 📊 **Build progress bar** | Animated progress bar with elapsed-time counter during generation |
| 🔽 **Smart auto-scroll** | Chat only auto-scrolls if you're already at the bottom; "↓ New messages" button otherwise |
| 🌐 **3D WebGL viewer** | Three.js/React Three Fiber with orbit controls, lighting, and auto-fit |
| 🎨 **Empty-state & loading animations** | Placeholder canvas with floating icon and 3D rotating cube during build |

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser (React 18)                       │
│  ┌──────────────┐  drag-resize  ┌────────────────────────────┐  │
│  │  Chat Panel  │◄─────────────►│      3D Preview Panel      │  │
│  │              │               │  ┌──────────────────────┐  │  │
│  │  • Messages  │               │  │  Three.js WebGL      │  │  │
│  │  • Steps log │               │  │  (STL via STLLoader) │  │  │
│  │  • Healing   │               │  └──────────────────────┘  │  │
│  │    history   │               │  ┌──────────┐ ┌─────────┐  │  │
│  │  • FileUpload│               │  │ Params   │ │ Export  │  │  │
│  │  • PromptBox │               │  │ Sliders  │ │ Panel   │  │  │
│  └──────────────┘               │  └──────────┘ └─────────┘  │  │
└─────────────────────────────────────────────────────────────────┘
              │  SSE stream / REST  │  REST  │
              ▼                    ▼        ▼
┌──────────────────────────────────────────────────────────────┐
│                  FastAPI  (port 3001)                        │
│                                                              │
│  POST /api/build/stream ──► claude_service                   │
│      │  (SSE 6-step)         generate_design_from_prompt()   │
│      │                          │                            │
│      │                          ▼                            │
│      │                    parametric_cad_service             │
│      │                    _execute_cadquery_code()           │
│      │                    7-transform pipeline               │
│      │                    exec() sandbox                     │
│      │                          │                            │
│      │                    CadQuery (OCC kernel)              │
│      │                    → .step  .stl  _parametric.py      │
│      │                                                       │
│  POST /api/rebuild ───────► rebuild_with_parameters()        │
│  POST /api/upload  ───────► cad_import_service               │
│  POST /api/upload/edit ───► claude_service + cad_exec        │
│  POST /api/scene/* ───────► in-memory scene store            │
│  GET  /exports/cad/* ─────► FileResponse                     │
└──────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

### Backend

| Layer | Tech |
|---|---|
| Web framework | FastAPI 0.128+ |
| ASGI server | Uvicorn |
| CAD geometry | CadQuery 2.4+ (OpenCASCADE Technology / OCC) |
| Parametric parts | `cq_warehouse` (fasteners, bearings, gears) |
| AI / LLM | Anthropic Claude (`claude-opus-4-20250514`) via `anthropic` SDK |
| Mesh import | trimesh (STL/OBJ/3MF/PLY/GLB) |
| IGES import | OCP `IGESControl_Reader` |
| Async | Python `asyncio`, `httpx` for streaming |
| Config | `pydantic-settings` + `.env` |
| Database (optional) | MySQL via `SQLAlchemy` + `pymysql` |
| Async tasks (optional) | Celery + Redis |
| S3 sharing (optional) | `boto3` |

### Frontend

| Layer | Tech |
|---|---|
| UI framework | React 18.2 |
| State management | `useReducer` + React Context (`AppContext`) |
| 3D rendering | `@react-three/fiber` 8.15 · `@react-three/drei` 9.92 · `three` 0.159 |
| SSE streaming | Native `fetch` + `ReadableStream` |
| File upload | `XMLHttpRequest` (for upload progress) |
| Build tooling | Create React App 5 (Webpack 5) |

---

## Project Structure

```
Cad-ai-builder/
├── Backend/
│   ├── main.py                    # FastAPI app, all routes, in-memory stores
│   ├── start.py                   # Startup script (sets UTF-8 encoding)
│   ├── config.py                  # pydantic-settings config
│   ├── tasks.py                   # Celery task definitions (optional)
│   ├── validator.py               # Extra param validation helpers
│   ├── requirements.txt           # Core Python dependencies
│   ├── requirements-phase4.txt    # Optional deps (Celery, boto3, trimesh)
│   └── services/
│       ├── __init__.py            # Service singletons & availability flags
│       ├── claude_service.py      # AI design generation, self-healing, system prompts (~5100 lines)
│       ├── parametric_cad_service.py  # Code safety, 7-transform pipeline, exec sandbox (~1050 lines)
│       ├── cad_import_service.py  # CAD file upload & format conversion
│       ├── cadquery_service.py    # Legacy CadQuery geometry service
│       ├── database_service.py    # MySQL projects/builds/messages ORM
│       ├── glb_service.py         # STL→GLB conversion (trimesh)
│       ├── s3_service.py          # S3 upload/download sharing
│       ├── product_library.py     # 98+ product templates with real-world dimensions (~2400 lines)
│       └── product_visual_knowledge.py  # Per-category visual & build guides (~1700 lines)
│
├── client/
│   ├── package.json
│   └── src/
│       ├── index.js               # React entry (wraps with AppProvider)
│       ├── App.jsx                # Layout shell: panels, header, progress bar, mobile tabs
│       ├── App.css                # Full layout CSS (~900 lines)
│       ├── api.js                 # All API calls (build, rebuild, upload, projects)
│       ├── context/
│       │   └── AppContext.jsx     # useReducer state (25 actions, undo/redo history)
│       ├── hooks/
│       │   └── useBuild.js        # Build logic: SSE streaming, scene management, NLP edit
│       └── components/
│           ├── MultiProductCanvas.jsx  # Three.js STL viewer (orbit, lighting, multi-model)
│           ├── ParameterPanel.jsx      # Slider UI for parametric dimensions
│           ├── ExportPanel.jsx         # STL/STEP/Script download + S3 share
│           ├── PromptInput.jsx         # Textarea with upload-mode badge
│           ├── FileUpload.jsx          # Drag-and-drop CAD file upload zone
│           └── ProjectBrowser.jsx      # MySQL-backed saved projects browser
│
├── exports/
│   ├── cad/                       # Generated .step .stl _parametric.py files
│   └── uploads/                   # Uploaded CAD source files
│
├── .env                           # API keys (never commit)
├── .env.example                   # Template for new devs
└── .gitignore
```

---

## Prerequisites

| Requirement | Minimum version | Notes |
|---|---|---|
| Python | 3.10+ | 3.12 recommended |
| Node.js | 18+ | 22 recommended |
| npm | 8+ | |
| Anthropic API key | — | [console.anthropic.com](https://console.anthropic.com) |
| MySQL | 8.0+ | **Optional** — app runs without it |
| Redis | 7+ | **Optional** — only needed for Celery async tasks |

> **Windows users**: CadQuery's OCC kernel is available as pre-built wheels. No FreeCAD or system OpenCASCADE installation required.

---

## Installation & Setup

### 1. Clone the repository

```bash
git clone https://github.com/Aslanmatejka/Cad-ai-builder.git
cd Cad-ai-builder
```

### 2. Create and activate a Python virtual environment

```bash
# Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1

# macOS / Linux
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Python dependencies

```bash
pip install -r Backend/requirements.txt
```

For optional features (GLB export, S3 sharing, Celery):

```bash
pip install -r Backend/requirements-phase4.txt
```

### 4. Set up environment variables

```bash
cp .env.example .env
```

Edit `.env` and add your Anthropic API key (the only required value):

```ini
ANTHROPIC_API_KEY=sk-ant-api03-...
```

See [Environment Variables](#environment-variables) for all options.

### 5. Install frontend dependencies

```bash
cd client
npm install
cd ..
```

---

## Running the App

Open **two terminals** from the project root:

**Terminal 1 — Backend**

```powershell
# Windows (PowerShell), from project root with venv active
cd Backend
python start.py
```

The backend starts on **http://localhost:3001** with hot-reload enabled.  
Health check: `GET http://localhost:3001/` → `{"status": "healthy"}`  
OpenAPI docs: **http://localhost:3001/docs**

**Terminal 2 — Frontend**

```powershell
cd client
npm start
```

The React dev server starts on **http://localhost:3000** and opens automatically.

> **Windows note**: If you see process already running errors, kill stale processes first:
> ```powershell
> Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force
> Get-Process -Name node   -ErrorAction SilentlyContinue | Stop-Process -Force
> ```

---

## Environment Variables

Place these in the `.env` file at the project root. A copy at `Backend/.env` also works.

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ | — | Anthropic API key for Claude |
| `AI_MODEL_NAME` | ❌ | `claude-opus-4-20250514` | Claude model to use |
| `AI_MAX_TOKENS` | ❌ | `16384` | Max tokens per AI response |
| `AI_TEMPERATURE` | ❌ | `0.3` | AI temperature (0.0–1.0) |
| `PORT` | ❌ | `3001` | Backend server port |
| `HOST` | ❌ | `0.0.0.0` | Backend bind host |
| `DEBUG` | ❌ | `false` | Enable debug mode |
| `DB_HOST` | ❌ | `localhost` | MySQL host |
| `DB_PORT` | ❌ | `3306` | MySQL port |
| `DB_USER` | ❌ | `root` | MySQL user |
| `DB_PASSWORD` | ❌ | — | MySQL password (leave blank to disable DB) |
| `DB_NAME` | ❌ | `product_builder` | MySQL database name |
| `AWS_ACCESS_KEY_ID` | ❌ | — | AWS key for S3 model sharing |
| `AWS_SECRET_ACCESS_KEY` | ❌ | — | AWS secret for S3 model sharing |
| `AWS_S3_BUCKET` | ❌ | — | S3 bucket name |
| `REDIS_URL` | ❌ | `redis://localhost:6379` | Redis URL for Celery |

**Minimal `.env` for local development:**

```ini
ANTHROPIC_API_KEY=sk-ant-api03-your-key-here
```

---

## API Reference

### Build Endpoints

#### `POST /api/build/stream`
Stream a new CAD build via Server-Sent Events (SSE).

**Request body:**
```json
{
  "prompt": "iPhone 15 Pro case with camera cutout and USB-C port",
  "previousDesign": null,
  "projectId": null
}
```

For modifications, pass `previousDesign` with the previous build's `code`, `parameters`, and `explanation`.

**SSE Event stream** (each line is `data: {...}\n\n`):

| Step | Event |
|---|---|
| 1 | Product library search |
| 2 | Claude AI design generation |
| 3 | Completeness check & enhancement |
| 4 | CadQuery geometry execution (+ self-healing events) |
| 5 | STEP / STL file export |
| 6 | Complete — includes full result |

**Final event payload:**
```json
{
  "step": 6,
  "status": "complete",
  "result": {
    "buildId": "uuid",
    "stlUrl": "/exports/cad/{buildId}.stl",
    "stepUrl": "/exports/cad/{buildId}.step",
    "parametricScript": "/exports/cad/{buildId}_parametric.py",
    "parameters": [{"name": "width", "default": 75, "min": 10, "max": 200, "unit": "mm"}],
    "explanation": {"design_intent": "...", "features_created": "..."},
    "design": {"code": "import cadquery...", "parameters": [...]}
  }
}
```

---

#### `POST /api/rebuild`
Rebuild a model with updated parameter values — **no AI call**, executes saved `_parametric.py` script.

**Request body:**
```json
{
  "buildId": "uuid",
  "parameters": {"width": 80, "height": 150}
}
```

---

#### `POST /api/build` (non-streaming)
Synchronous build — waits for full result before returning. Useful for scripting. Same request body as `/api/build/stream`.

---

### File Upload Endpoints

#### `GET /api/upload/formats`
Returns all supported upload formats with editability flags.

```json
{
  "solidFormats": [".step", ".stp", ".iges", ".igs", ".brep"],
  "meshFormats": [".stl", ".obj", ".3mf", ".ply", ".off", ".glb", ".gltf"],
  "2dFormats": [".dxf"]
}
```

---

#### `POST /api/upload`
Upload a CAD file (`multipart/form-data`, field name `file`, max 100 MB).

**Response:**
```json
{
  "buildId": "uuid",
  "originalFilename": "bracket.step",
  "format": ".step",
  "stlFile": "/exports/cad/{buildId}.stl",
  "stepFile": "/exports/cad/{buildId}.step",
  "boundingBox": {"width": 50.0, "depth": 30.0, "height": 20.0},
  "geometryInfo": {"solids": 1, "faces": 24, "edges": 48, "vertices": 32, "volume": 12500.0},
  "editable": true,
  "importCode": "import cadquery as cq\n...",
  "success": true
}
```

---

#### `POST /api/upload/edit`
Apply a natural language edit to an uploaded CAD file.

**Request body:**
```json
{
  "buildId": "uuid",
  "prompt": "Add four M3 mounting holes in the corners",
  "importCode": "import cadquery as cq\nresult = cq.importers.importStep(...)\n...",
  "previousDesign": null
}
```

Returns the same shape as the `/api/build/stream` final result.

---

### Scene Management Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/scene/create` | Create a new multi-product scene |
| `GET` | `/api/scene/{id}` | Get scene + all products |
| `POST` | `/api/scene/{id}/add-product` | Add a product to a scene |
| `PUT` | `/api/scene/product/{instanceId}/transform` | Update position/rotation/scale |
| `POST` | `/api/scene/product/{instanceId}/duplicate` | Duplicate with offset |
| `DELETE` | `/api/scene/product/{instanceId}` | Remove from scene |
| `POST` | `/api/scene/{id}/assemble` | Group products into assembly |
| `DELETE` | `/api/scene/assembly/{id}` | Disassemble group |

---

### Project & History Endpoints (MySQL required)

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/projects` | List all saved projects |
| `POST` | `/api/projects` | Create project |
| `GET` | `/api/projects/{id}` | Get project with builds + chat messages |
| `PUT` | `/api/projects/{id}` | Rename / update project |
| `DELETE` | `/api/projects/{id}` | Delete project and all data |
| `POST` | `/api/messages` | Save a chat message to a project |
| `GET` | `/api/history` | Recent builds across all projects |

---

### Utility Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/` | Health check |
| `GET` | `/api/health` | Detailed service status |
| `GET` | `/exports/cad/{filename}` | Serve generated CAD/STL/STEP files |
| `GET` | `/exports/uploads/{filename}` | Serve uploaded source files |
| `GET` | `/api/cache/check?prompt=...` | Check if a prompt has a cached result |
| `POST` | `/api/convert/glb` | Convert STL to GLB (trimesh, optional) |
| `GET` | `/api/mesh/stats/{buildId}` | Mesh vertex/face statistics |
| `POST` | `/api/s3/upload` | Upload model to S3 for sharing |
| `GET` | `/api/s3/download/{key}` | Download shared model from S3 |

---

## CAD File Upload & NLP Editing

One of the platform's most powerful features: upload any supported CAD file and immediately start editing it with natural language.

### Supported Formats

| Format | Extension | Type | NLP Editing |
|---|---|---|---|
| STEP | `.step`, `.stp` | Solid B-Rep | ✅ Full support |
| IGES | `.iges`, `.igs` | Solid B-Rep | ✅ Full support |
| BRep | `.brep` | OpenCASCADE native | ✅ Full support |
| DXF | `.dxf` | 2D sketch | ✅ Auto-extruded to 3D |
| STL | `.stl` | Mesh | ⚠️ View & export only |
| OBJ | `.obj` | Mesh | ⚠️ View & export only |
| 3MF | `.3mf` | Mesh | ⚠️ View & export only |
| PLY | `.ply` | Mesh | ⚠️ View & export only |
| GLB/glTF | `.glb`, `.gltf` | Mesh | ⚠️ View & export only |

> **Tip:** For full NLP editing of mesh files, convert them to STEP first using FreeCAD, Fusion 360, or any STEP exporter, then re-upload.

### Editing Flow

1. Drag-and-drop a STEP/IGES file onto the **Upload CAD file** zone in the chat panel
2. The model appears in the 3D viewer with geometry metadata (bounding box, face/edge count, volume)
3. A "**NLP editable**" badge appears in the prompt bar
4. Type your edit: `"add four M3 mounting holes 5mm from each corner"`
5. Claude reads the imported geometry code as the starting point and produces modified CadQuery code
6. The new model replaces the old one in the viewer
7. Chain further edits — each iteration uses the latest code as the base

---

## How the AI Pipeline Works

### Build Pipeline (6 steps)

```
User prompt
    │
    ├─ 1. Product Library Search
    │      Searches 98+ product templates for real-world reference dimensions
    │      (e.g., "iPhone 15 Pro" → exact port positions, camera island size)
    │
    ├─ 2. Claude AI Design Generation
    │      System prompt (~3000 lines) instructs Claude to return raw JSON:
    │      { parameters: [...], code: "import cadquery...", explanation: {...} }
    │      Adapts max_tokens (up to 16384) and temperature by complexity
    │
    ├─ 3. Completeness Check & Enhancement
    │      analyze_code_completeness() checks for missing features
    │      If incomplete → enhance_incomplete_design() sends back to AI for targeted fixes
    │
    ├─ 4. CadQuery Execution (with self-healing)
    │      7-transform preprocessing pipeline (see below)
    │      exec() in sandboxed namespace
    │      On error → infinite self-healing loop (5 escalating phases)
    │
    ├─ 5. File Export
    │      CadQuery → .step (editable) + .stl (printable) + _parametric.py (script)
    │
    └─ 6. Return result to frontend via SSE
```

### 7-Step Code Preprocessing Pipeline

Before `exec()`, every AI-generated code snippet goes through these transforms **in order**:

| # | Transform | What it does |
|---|---|---|
| 1 | `_strip_centered_from_non_box()` | Removes `centered=` from `.extrude()`, `.rect()`, `.circle()` — only `.box()` supports it |
| 2 | `_ensure_box_grounding()` | Adds `centered=(True,True,False)` to the first main `.box()` so Z=0 is ground |
| 3 | `_fix_zero_dimensions()` | Replaces `.extrude(0)` with `.extrude(0.1)` to prevent zero-height geometry errors |
| 4 | `_fix_negative_z_positions()` | Warns and clamps features placed below Z=0 |
| 5 | `_ensure_result_assignment()` | Auto-adds `result = body` if the AI forgot to assign the final workplane |
| 6 | `_clamp_fillet_radii()` | Injects `min(r, _auto_fillet_max)` guards — 15% of the smallest dimension |
| 7 | `_wrap_fillets_in_try_except()` | Wraps unprotected `.fillet()` / `.chamfer()` calls in try/except blocks |

---

## Self-Healing Engine

When CadQuery raises a `RuntimeError` or `ValueError`, the system **never gives up**. It classifies the error into one of 18 categories and retries with progressively more aggressive fixes:

### Error Categories

`GEOMETRY_FILLET_CHAMFER` · `GEOMETRY_SHELL` · `SKETCH_NOT_CLOSED` · `SELECTOR_FAILED` · `CURVE_TANGENT` · `REVOLVE_AXIS` · `MATH_ERROR` · `LOFT_FAILED` · `BOOLEAN_FAILED` · `WRONG_PARAMETER` · `SWEEP_FAILED` · `WORKPLANE_STACK` · `OCC_KERNEL_ERROR` · `ATTRIBUTE_ERROR` · `TYPE_ERROR` · `EMPTY_RESULT` · `NAME_ERROR` · `GENERAL`

### Healing Phases

| Phase | Attempts | Strategy |
|---|---|---|
| **Targeted** | 1 | Fix only the crashing line; reduce fillet radii 30% |
| **Conservative** | 2–3 | Reduce radii 60%; wrap in try/except; simplify splines |
| **Aggressive** | 4–5 | Strip all fillets, chamfers, shells; replace lofts with extrusions |
| **Rewrite** | 6–7 | Rewrite the failing section using only safe primitives |
| **Nuclear** | 8+ | Rebuild the entire model from scratch with boxes & cylinders only |

The self-healing loop also emits live SSE events to the frontend showing which phase and attempt is in progress.

---

## Parametric System

Every generated model is parametric. The system:

1. **Defines parameters** as named variables at the top of the generated script (e.g., `body_width = 75.0`)
2. **Saves a `_parametric.py` script** with section markers used for rebuilding:
   ```python
   # ═══════════════════════════════════════ GEOMETRY GENERATION
   ...
   # ═══════════════════════════════════════ EXPORT
   ```
3. **Rebuilds on slider change** via `POST /api/rebuild` — loads the saved script, replaces parameter values, re-executes the GEOMETRY section only, re-exports STL/STEP

This means parameter changes respond in 1–3 seconds with no AI usage.

### Parameter Schema

```json
{
  "name": "wall_thickness",
  "default": 2.5,
  "min": 0.5,
  "max": 10.0,
  "unit": "mm"
}
```

---

## Product Library

`product_library.py` contains **98+ product templates** with real-world reference dimensions. When a user prompt matches a product, its reference data is injected directly into the Claude context, ensuring accurate measurements.

### Example Entry

```python
{
  "keywords": ["iphone 15 pro", "iphone15", "iphone 15"],
  "name": "iPhone 15 Pro",
  "category": "phone_case",
  "dimensions": {"length": 159.9, "width": 76.7, "height": 8.25},
  "features": ["Dynamic Island", "USB-C port", "Action Button", "triple camera"],
  "notes": "Titanium frame. Camera island 37×30mm at top-left."
}
```

`product_visual_knowledge.py` adds per-category **visual build guides** with:
- `visual_profile` — what the product looks like and key proportions
- `build_strategy` — mandatory CadQuery approach (e.g., "use `.revolve()` + `.spline()` for mugs")
- `recognition_features` — features that distinguish this category
- `position_map` — where specific features are located

---

## Optional Services

All optional services degrade gracefully — the app works fully without them.

### MySQL Database

When `DB_PASSWORD` is set, the app stores:
- **Projects** — named workspaces
- **Builds** — each AI generation with code, parameters, file paths
- **Chat messages** — full conversation history per project

Without MySQL, the app runs in-memory only (data is lost on server restart).

**Setup:**
```sql
CREATE DATABASE product_builder CHARACTER SET utf8mb4;
CREATE USER 'cad_user'@'localhost' IDENTIFIED BY 'yourpassword';
GRANT ALL ON product_builder.* TO 'cad_user'@'localhost';
```

### S3 Model Sharing

With AWS credentials set, use `POST /api/s3/upload` to generate a shareable URL for any model, and `GET /api/s3/download/{key}` to restore a shared model.

### GLB Export (Three.js optimized)

With `trimesh` installed, `POST /api/convert/glb` converts STL to GLB format — smaller file size and faster loading in the 3D viewer.

### Celery Async Tasks

With Celery + Redis running, use `POST /api/build/async` to queue builds and poll `GET /api/task/{taskId}` for results. Useful for server deployments with multiple concurrent users.

---

## Frontend Architecture

### Panels & Layout

The UI is a 3-column CSS grid: `chat | resize-handle | preview`. The columns are computed by `getGridColumns()` based on state:

- **Normal**: `${chatWidth}% 8px ${100-chatWidth}%` — user can drag the resize handle
- **Chat collapsed**: `48px 0px 1fr` — chat shows a vertical expand button
- **Preview collapsed**: `1fr 0px 48px` — preview shows a vertical expand button
- **Mobile** (`< 968px`): `1fr` with tab bar switching between panels

### Component Tree

```
App.jsx  (layout shell)
├── header
│   ├── undo/redo buttons
│   └── projects button + quick export links
├── BuildProgressBar  (inline)
├── MobileTabBar  (inline, < 968px only)
├── main  (CSS grid)
│   ├── ChatPanel
│   │   ├── WelcomeScreen / message list
│   │   │   ├── UserMessage
│   │   │   └── AssistantMessage
│   │   │       ├── BuildingStatus (live steps + healing log)
│   │   │       ├── DesignSummary (explanation sections + downloads)
│   │   │       └── ErrorMessage (retry button)
│   │   ├── PromptInput  (upload badge when file active)
│   │   └── FileUpload  (drag-and-drop zone)
│   ├── ResizeHandle
│   └── PreviewPanel
│       ├── PreviewHeader (collapse btn + params toggle)
│       ├── MultiProductCanvas (Three.js)
│       ├── ParameterPanel (sliders)
│       └── ExportPanel (download + S3 share)
└── ProjectBrowser  (modal overlay)
```

---

## State Management

`AppContext.jsx` provides a single `useReducer` store wrapping the entire app.

### State Shape

```typescript
{
  // Build
  status: 'idle' | 'building' | 'success' | 'error',
  result: BuildResult | null,
  messages: Message[],
  currentDesign: { code, parameters, explanation } | null,
  currentBuildId: string | null,
  currentProjectId: string | null,

  // Scene
  currentScene: Scene | null,
  sceneProducts: Product[],

  // Upload
  uploadedFile: UploadedFile | null,

  // Layout
  chatWidth: number,           // percent (20–80)
  isDragging: boolean,
  chatCollapsed: boolean,
  previewCollapsed: boolean,
  activeTab: 'chat' | 'preview',

  // UI flags
  showProjectBrowser: boolean,
  showParameterPanel: boolean,

  // Progress
  buildProgress: number,        // 0–100
  buildStartTime: number | null,

  // Undo/Redo
  history: Snapshot[],          // max 20
  historyIndex: number,
}
```

### Key Actions

| Action | Effect |
|---|---|
| `BUILD_START` | Sets status=building, resets progress |
| `BUILD_PROGRESS` | Updates progress bar value |
| `BUILD_COMPLETE` | Saves result, pushes history snapshot |
| `UPDATE_BUILD_STEP` | Updates SSE step in current assistant message |
| `TOGGLE_CHAT_COLLAPSED` | Collapses/expands chat panel |
| `TOGGLE_PREVIEW_COLLAPSED` | Collapses/expands preview panel |
| `SET_UPLOADED_FILE` | Stores upload metadata for NLP edit mode |
| `UNDO` / `REDO` | Restores previous/next history snapshot |
| `REPLACE_LAST_PRODUCT` | Updates 3D viewer after rebuild |
| `RESET_WORKSPACE` | Clears everything for a new project |

---

## Testing

Test files are at the project root. They use `sys.path.insert(0, 'Backend')` to import services directly (no pytest required — just run with Python).

```bash
# Test parametric CAD generation
python test_phase32.py

# Test code completeness analysis
python test_completeness.py

# Test drone type detection
python test_drone_types.py

# Test phone case analysis
python test_phone_case_analyzer.py

# Test shape quality metrics
python test_shape_quality.py

# Test cq_warehouse integration
python test_cq_warehouse.py
```

---

## Roadmap

- [ ] **Multi-model assembly** — place multiple generated parts relative to each other and export as assembly STEP
- [ ] **Real-time collaboration** — share a session link; multiple users edit the same design
- [ ] **Version history** — git-like branching for design iterations
- [ ] **STL mesh editing** — use mesh sculpting to NLP-edit mesh files (not just solids)
- [ ] **Material & finish metadata** — annotate models with material, colour, surface finish for ordering
- [ ] **Direct 3D printer slicing** — integrate Slic3r/PrusaSlicer API to preview G-code and print time
- [ ] **BOM generation** — extract fasteners, bearings, and standard parts from `cq_warehouse` usage
- [ ] **Dimensions & annotations** — overlay dimension lines and callouts on the 3D model
- [ ] **Drawing export** — generate 2D engineering drawings (DXF/PDF) from the STEP model

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Follow the [copilot-instructions.md](.github/copilot-instructions.md) for code conventions
4. When adding new imports for AI-generated code, apply the **triple-update rule**:
   - Add to `allowed_imports` in `_validate_code_safety()`
   - Add to `namespace` in `_execute_cadquery_code()`
   - Add to `namespace` in `rebuild_with_parameters()`
5. Add tests in `test_*.py` at the project root
6. Submit a pull request with a clear description of what changed

---

## License

MIT © 2026 Aslanmatejka
