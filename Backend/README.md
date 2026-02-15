# Chat-to-CAD Platform - Phase 1 Setup

## Backend Installation & Startup

```bash
# Navigate to Backend directory
cd Backend

# Install dependencies in virtual environment
pip install -r requirements.txt

# Start FastAPI server
python main.py
```

Server runs on: http://localhost:3001

## API Endpoints

### Health Check

```
GET /
```

### Single-Shot Build

```
POST /api/build
{
  "prompt": "Create a 50x30x20mm box with 2mm walls"
}
```

### Conversational Chat

```
POST /api/chat
{
  "message": "I need an enclosure for Raspberry Pi",
  "conversationHistory": [],
  "currentDesign": null
}
```

### File Download

```
GET /exports/cad/{buildId}.stl
GET /exports/cad/{buildId}.step
GET /exports/cad/{buildId}_parametric.py
```

## Environment Setup

Copy `.env.example` to `.env` and add your Anthropic API key:

```env
ANTHROPIC_API_KEY=your_key_here
AI_MODEL_NAME=claude-3-5-sonnet-20241022
PORT=3001
CAD_ENGINE=cadquery
```

## Phase 1 Architecture

```
User Prompt
    ↓
Claude 3.5 Sonnet (LLM Architect)
    ↓
Design JSON Schema
    ↓
CadQuery (Geometry Engine)
    ↓
STEP/STL Files → React 3D Viewer
```

## Testing

```bash
# Test health endpoint
curl http://localhost:3001/

# Test build endpoint
curl -X POST http://localhost:3001/api/build \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a box 50x30x20mm with 2mm walls"}'
```

## Next Steps for Frontend Integration

The React client in `../client/` is already configured to connect to this backend via the proxy at `localhost:3001`. The existing frontend components will work with these new endpoints.
