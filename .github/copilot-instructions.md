# Product Builder AI Agent Guide

## Architecture

Chat-to-CAD platform: natural language → Claude AI → CadQuery Python code → STEP/STL files → Three.js 3D viewer.

- **Backend** (`Backend/`): FastAPI on port **3001**, started via `python Backend/start.py`. Config in `config.py` loads `.env` via `pydantic-settings`. Only `ANTHROPIC_API_KEY` is required; `AI_MODEL_NAME` defaults to `claude-opus-4-20250514`.
- **Frontend** (`client/`): React 18 + `@react-three/fiber` on port **3000** (`npm start`). API base URL in `client/src/api.js` defaults to `http://localhost:3001/api`. Some calls in `App.jsx` use hardcoded `http://localhost:3001` (scene endpoints).
- **Exports**: Generated files at `exports/cad/{buildId}.{stl,step}` and `{buildId}_parametric.py`.
- **Optional deps** degrade gracefully — MySQL (`pymysql`+`sqlalchemy`), S3 (`boto3`), Celery, GLB (`trimesh`) each activate only when their packages + credentials exist. See try/except pattern in `Backend/services/__init__.py`.
- **Product knowledge**: `product_library.py` (~2400 lines, 98+ product templates with real-world dimensions) + `product_visual_knowledge.py` (~1700 lines, per-category visual/build guides) feed into the system prompt.

## Core Data Flow

1. `POST /api/build/stream` → SSE events → `claude_service.generate_design_from_prompt()` → raw JSON `{parameters, code, explanation}`
2. `parametric_cad_service.generate_parametric_cad()` → `_validate_code_safety()` → 7-step preprocessing pipeline → `exec()` in sandboxed namespace → STEP + STL export
3. Frontend `MultiProductCanvas.jsx` loads STL via Three.js `STLLoader`; `ParameterPanel.jsx` renders sliders
4. Slider change → `POST /api/rebuild` → re-executes saved `_parametric.py` with new values (**no AI call**)
5. Modification flow: frontend sends `previousDesign` (with `code`) back to Claude → AI edits existing code rather than generating from scratch

## Startup (Windows)

```powershell
# Kill stale backends first
Get-Process -Name python -ErrorAction SilentlyContinue | Stop-Process -Force
# Terminal 1 — Backend (from project root, .venv activated)
cd Backend; python start.py          # uvicorn on :3001 with hot reload
# Terminal 2 — Frontend
cd client; npm start                 # CRA dev server on :3000
```

Health: `GET http://localhost:3001/` → JSON status. API docs at `/docs`. Encoding: `start.py` and `main.py` both set `PYTHONIOENCODING=utf-8` and reconfigure stdout/stderr before any import — **this must stay at the top of both files**.

## Critical Patterns — Do Not Break

### Code Safety Allowlist

`parametric_cad_service._validate_code_safety()` — AI-generated code runs in `exec()`. Only these imports pass: `cadquery`, `cq`, `math`, `copy`, `cq_warehouse`, `numpy`, `np`. Forbidden calls: `eval(`, `exec(`, `open(`, `__import__(`, `file(`. Import validation uses regex to check both `import X` and `from X.Y import` forms against the allowlist AND a separate `forbidden_modules` set (`os`, `sys`, `subprocess`, etc.).

**Triple-update rule**: add new libraries to ALL THREE places:

1. `allowed_imports` set in `_validate_code_safety()`
2. `namespace` dict in `_execute_cadquery_code()`
3. `namespace` dict in `rebuild_with_parameters()`

### Preprocessing Pipeline (order matters)

Before `exec()`, code passes through 7 transforms in `_execute_cadquery_code()` (and identically in `rebuild_with_parameters()`):

1. `_strip_centered_from_non_box()` — removes `centered=` from `.extrude()`, `.rect()`, `.circle()` (only `.box()` supports it)
2. `_ensure_box_grounding()` — adds `centered=(True,True,False)` to first main `.box()` so Z=0 is ground
3. `_fix_zero_dimensions()` — replaces `.extrude(0)` with `.extrude(0.1)`
4. `_fix_negative_z_positions()` — warns about features placed below Z=0
5. `_ensure_result_assignment()` — auto-adds `result = body` if AI forgets
6. `_clamp_fillet_radii()` — injects `min(r, _auto_fillet_max)` guards (15% of smallest dimension)
7. `_wrap_fillets_in_try_except()` — wraps unprotected `.fillet()`/`.chamfer()` assignments in try/except

### Parametric Script Markers (load-bearing)

Generated `_parametric.py` scripts use these exact comment markers parsed by `rebuild_with_parameters()`:

```
# ═══════════════════════════════════════════════════════════════
# GEOMETRY GENERATION
...
# ═══════════════════════════════════════════════════════════════
# EXPORT
```

**Never rename or reformat these markers** — the rebuild endpoint uses `str.find()` on these exact strings.

### Claude Response Contract

`claude_service._get_design_system_prompt()` (~3000 lines) instructs Claude to return raw JSON (no markdown fences):

```json
{
  "parameters": [
    { "name": "x", "default": 50.0, "min": 1, "max": 2000, "unit": "mm" }
  ],
  "code": "import cadquery as cq\nresult = ...",
  "explanation": { "design_intent": "...", "features_created": "..." }
}
```

Code **must** `import cadquery` and define `result` as `cq.Workplane`. Stray markdown is stripped by `_extract_json_from_response()`.

### Self-Healing Retries

`main.py` `/api/build/stream` catches CadQuery `RuntimeError`/`ValueError`, calls `claude_service.fix_code_with_error()` in an **infinite loop** — the builder never gives up. Error classification covers 16 categories: `GEOMETRY_FILLET_CHAMFER`, `GEOMETRY_SHELL`, `SKETCH_NOT_CLOSED`, `SELECTOR_FAILED`, `CURVE_TANGENT`, `REVOLVE_AXIS`, `MATH_ERROR`, `LOFT_FAILED`, `BOOLEAN_FAILED`, `WRONG_PARAMETER`, `SWEEP_FAILED`, `WORKPLANE_STACK`, `OCC_KERNEL_ERROR`, `ATTRIBUTE_ERROR`, `TYPE_ERROR`, `EMPTY_RESULT`, `NAME_ERROR`, `GENERAL`.

**Five graduated healing phases** escalate automatically:

| Phase        | Attempts | Strategy                                                         |
| ------------ | -------- | ---------------------------------------------------------------- |
| Targeted     | 1        | Fix only the crashing line, reduce radii 30%                     |
| Conservative | 2–3      | Reduce radii 60%, wrap in try/except, simplify splines           |
| Aggressive   | 4–5      | Strip all fillets/chamfers/shells, replace lofts with extrusions |
| Rewrite      | 6–7      | Rewrite the failing section using only safe primitives           |
| Nuclear      | 8+       | Rebuild entire model from scratch with boxes & cylinders only    |

### Streaming & Network Resilience

`claude_service` uses `client.messages.stream()` (not `.create()`) with retry on `httpx.ReadError` / `RemoteProtocolError` / `ConnectError` / `ConnectionError` / `OSError` (backoff 2s, 4s, up to 3 attempts). Complexity keywords in prompts auto-adjust `max_tokens` (up to 16384) and `temperature` (down to 0.25 for high complexity).

## Key Conventions

- Services are **singletons** instantiated at module level — `claude_service`, `parametric_cad_service`, etc.
- Backend routes are `async def` but CadQuery geometry is **synchronous** CPU-bound — no `await` on geometry ops.
- Frontend: components in `client/src/components/` have co-located `.css` files. `App.jsx` (~800 lines) is the central state manager with no Redux/context.
- CAD files served via `@app.get("/exports/cad/{filename}")` in `main.py`.
- Emoji logging: `📨` request, `📤` response, `❌` error, `🧠` AI, `🔧` fix, `💾` DB save.
- Errors logged to `exports/error_log.txt` with timestamps.
- `.env` lives at project root (loaded by `config.py` via `pydantic-settings`); a second copy exists at `Backend/.env`. Both need `ANTHROPIC_API_KEY`. `AI_MODEL_NAME` overrides the default model.

## Adding Features

- **New import for AI code**: triple-update — `_validate_code_safety()` allowlist + `_execute_cadquery_code()` namespace + `rebuild_with_parameters()` namespace.
- **New product category**: add to `CATEGORY_VISUAL_KNOWLEDGE` in `product_visual_knowledge.py` with required keys `visual_profile`, `build_strategy`, `recognition_features`, optionally `position_map`.
- **New product template**: add entry to `PRODUCTS` list in `product_library.py` with `keywords`, `name`, `category`, `dimensions`, `features`, `notes`.
- **New error recovery**: add keyword match + `error_category` + `targeted_fix` text to `claude_service.fix_code_with_error()`.
- **New system prompt rules**: edit `claude_service._get_design_system_prompt()` — it's ~3000 lines; search for relevant section headers.
- **New API endpoint**: add route in `main.py`; if it needs frontend, add API function in `client/src/api.js` and call from `App.jsx`.
- **New preprocessing step**: add method to `ParametricCADService`, call it in BOTH `_execute_cadquery_code()` AND `rebuild_with_parameters()` pipeline sections.

## Testing

Tests at project root (`test_phase*.py`). Run from project root with venv active: `python test_phase32.py`. Tests use `sys.path.insert(0, 'Backend')` to import services directly — no pytest framework. Tests validate service internals (product knowledge structure, preprocessing transforms), not HTTP endpoints.
