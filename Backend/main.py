"""
Chat-to-CAD Platform - Phase 4
FastAPI Backend with Async Task Queue
"""

import sys as _sys
import os as _os

# Fix Windows console encoding for emoji characters (must run before any print)
_os.environ['PYTHONIOENCODING'] = 'utf-8'
try:
    _sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    _sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from typing import Optional, Dict, Any
import os
from pathlib import Path
import uuid
import time
import json
import asyncio

# Import services
from services import (
    claude_service, 
    cadquery_service, 
    parametric_cad_service, 
    database_service,
    s3_service, 
    S3_AVAILABLE,
    glb_service,
    GLB_AVAILABLE
)
from config import settings

print("\n" + "="*60)
print("🚀 BACKEND STARTING UP")
print("="*60)
print(f"Services loaded successfully:")
print(f"  - Claude Service: {claude_service is not None}")
print(f"  - CadQuery Service: {cadquery_service is not None}")
print(f"  - Parametric CAD Service: {parametric_cad_service is not None}")
print(f"  - S3 Available: {S3_AVAILABLE}")
print(f"  - GLB Available: {GLB_AVAILABLE}")

# Initialize MySQL database
DB_AVAILABLE = False
try:
    if settings.DB_HOST and settings.DB_NAME and settings.DB_PASSWORD:
        database_service.initialize(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
            pool_size=settings.DB_CONNECTION_LIMIT,
        )
        DB_AVAILABLE = True
        print(f"  - MySQL Database: ✅ Connected to {settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}")
    else:
        print(f"  - MySQL Database: ⚠️  Missing DB credentials in .env — storage disabled")
except Exception as db_err:
    print(f"  - MySQL Database: ❌ Connection failed: {db_err}")
    print(f"    Make sure MySQL is running and the database '{settings.DB_NAME}' exists.")

print("="*60 + "\n")

# Import Celery tasks (optional - only if Celery is installed)
try:
    from tasks import generate_cad_async, rebuild_async
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False
    print("⚠️  Celery not available - using synchronous processing")



# Initialize FastAPI app
app = FastAPI(
    title="Chat-to-CAD Platform",
    description="Natural Language to CAD Generation with Claude 3.5 Sonnet & CadQuery",
    version="2.0.0-phase4"
)

# CORS configuration for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    print(f"\n{'='*60}")
    print(f"📨 INCOMING REQUEST")
    print(f"{'='*60}")
    print(f"Method: {request.method}")
    print(f"URL: {request.url}")
    print(f"Client: {request.client}")
    print(f"{'='*60}\n")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"📤 RESPONSE")
    print(f"{'='*60}")
    print(f"Status: {response.status_code}")
    print(f"Process Time: {process_time:.3f}s")
    print(f"{'='*60}\n")
    
    return response

# Create exports directory structure
EXPORTS_DIR = settings.EXPORTS_DIR
CAD_DIR = settings.CAD_DIR

# Request/Response Models
class ChatRequest(BaseModel):
    message: str
    conversationHistory: Optional[list] = []
    currentDesign: Optional[Dict[str, Any]] = None

class BuildRequest(BaseModel):
    prompt: str
    previousDesign: Optional[Dict[str, Any]] = None
    projectId: Optional[str] = None

class ChatResponse(BaseModel):
    message: str
    updatedDesign: Optional[Dict[str, Any]] = None
    shouldBuild: bool = False
    buildResult: Optional[Dict[str, Any]] = None

class BuildResponse(BaseModel):
    buildId: str
    stlUrl: str
    stepUrl: str
    parametricScript: Optional[str] = None
    parameters: Optional[list] = None
    explanation: Optional[Dict[str, Any]] = None
    success: bool = True

class RebuildRequest(BaseModel):
    buildId: str
    parameters: Dict[str, float]

class AsyncBuildRequest(BaseModel):
    prompt: str
    useAsync: bool = False

# Health check endpoint
@app.get("/")
async def root():
    """Health check endpoint"""
    print("✅ Health check endpoint called")
    return {
        "status": "healthy",
        "service": "Chat-to-CAD Platform",
        "phase": "4",
        "engines": {
            "geometry": "CadQuery",
            "llm": "Claude 3.5 Sonnet",
            "framework": "FastAPI",
            "async_tasks": "Celery" if CELERY_AVAILABLE else "Synchronous"
        }
    }

@app.get("/api/health")
async def api_health():
    """API health check"""
    print("✅ API health check called")
    return {"status": "ok", "message": "Backend is running"}

# Chat endpoint (conversational mode)
@app.post("/api/chat", response_model=ChatResponse)
async def chat_with_engineer(request: ChatRequest):
    """
    Conversational interface for refining CAD designs
    Claude guides the user through design parameters
    """
    try:
        # TODO: Implement Claude conversation logic
        result = await claude_service.chat_about_design(
            message=request.message,
            conversation_history=request.conversationHistory,
            current_design=request.currentDesign
        )
        
        # If design is ready, trigger build
        build_result = None
        if result.get("shouldBuild") and result.get("updatedDesign"):
            cad_result = await cadquery_service.generate_cad(result["updatedDesign"])
            build_result = {
                "buildId": cad_result["buildId"],
                "stlUrl": cad_result["stlFile"],
                "stepUrl": cad_result["stepFile"],
                "parametricScript": cad_result.get("parametricScript")
            }
        
        return ChatResponse(
            message=result["message"],
            updatedDesign=result.get("updatedDesign"),
            shouldBuild=result.get("shouldBuild", False),
            buildResult=build_result
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Build endpoint (single-shot mode)
@app.post("/api/build", response_model=BuildResponse)
async def build_product(request: BuildRequest):
    """
    Single-shot CAD generation from natural language prompt
    Phase 2: Claude -> Parametric Code Schema -> CadQuery Execution -> STEP/STL
    """
    print(f"\n{'='*60}")
    print(f"🔨 BUILD REQUEST RECEIVED")
    print(f"{'='*60}")
    print(f"Prompt: {request.prompt}")
    print(f"Has previous design: {request.previousDesign is not None}")
    print(f"{'='*60}\n")
    
    last_error = None
    ai_response = None
    
    try:
        # Step 1: Claude generates parametric code schema
        print("📡 Step 1: Calling Claude AI for design generation...")
        ai_response = await claude_service.generate_design_from_prompt(
            prompt=request.prompt,
            previous_design=request.previousDesign
        )
        print(f"✅ Claude AI response received")
        print(f"Response keys: {list(ai_response.keys())}")
        
        # Step 2: Execute parametric CadQuery code (infinite self-healing)
        attempt = 0
        while True:
            attempt += 1
            try:
                print(f"\n🔧 Step 2 (attempt {attempt}): Generating CAD model with CadQuery...")
                cad_result = await parametric_cad_service.generate_parametric_cad(ai_response)
                print(f"✅ CAD generation complete (after {attempt} attempt{'s' if attempt > 1 else ''})")
                print(f"Build ID: {cad_result['buildId']}")
                print(f"Files generated: STL={cad_result.get('stlFile')}, STEP={cad_result.get('stepFile')}")
                
                return BuildResponse(
                    buildId=cad_result["buildId"],
                    stlUrl=cad_result["stlFile"],
                    stepUrl=cad_result["stepFile"],
                    parametricScript=cad_result.get("parametricScript"),
                    parameters=cad_result.get("parameters"),
                    explanation=cad_result.get("explanation"),
                    success=True
                )
            except (RuntimeError, ValueError) as cad_err:
                last_error = str(cad_err)
                print(f"\n⚠️ CadQuery attempt {attempt} failed: {last_error}")
                
                # Infinite self-healing — always retry with progressive strategy
                print(f"🔄 Self-healing (attempt {attempt})...")
                failed_code = ai_response.get("code", "")
                ai_response = await claude_service.fix_code_with_error(
                    failed_code=failed_code,
                    error_message=last_error,
                    original_prompt=request.prompt,
                    attempt=attempt,
                    max_retries=0  # 0 signals infinite mode
                )
                print(f"✅ Claude fix response received")
        
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f"\n{'='*60}")
        print(f"❌ ERROR in /api/build")
        print(f"{'='*60}")
        print(error_details)
        print(f"{'='*60}\n")
        
        # Log to file for debugging
        try:
            log_path = Path(EXPORTS_DIR) / "error_log.txt"
            with open(log_path, "a", encoding="utf-8") as f:
                import datetime
                f.write(f"\n{'='*60}\n")
                f.write(f"[{datetime.datetime.now()}] /api/build error\n")
                f.write(f"Prompt: {request.prompt}\n")
                f.write(f"Error: {str(e)}\n")
                f.write(error_details)
                f.write(f"{'='*60}\n")
        except:
            pass
        
        raise HTTPException(status_code=500, detail=str(e))

# ── Streaming build endpoint (SSE) ──────────────────────────────────────
@app.post("/api/build/stream")
async def build_product_stream(request: BuildRequest):
    """
    SSE streaming build endpoint — sends step-by-step progress events.
    Each event is a JSON line: { step, message, status, ... }
    Final event includes the full build result or error.
    """
    async def event_generator():
        def sse(data: dict) -> str:
            return f"data: {json.dumps(data)}\n\n"

        last_error = None
        ai_response = None
        attempt = 0
        is_modification = request.previousDesign is not None and bool(request.previousDesign)
        has_previous_code = is_modification and bool(request.previousDesign.get("code", ""))

        print(f"\n{'='*60}")
        print(f"🔨 STREAM BUILD REQUEST")
        print(f"{'='*60}")
        print(f"Prompt: {request.prompt[:100]}..." if len(request.prompt) > 100 else f"Prompt: {request.prompt}")
        print(f"Is modification: {is_modification}")
        print(f"Has previous code: {has_previous_code}")
        if has_previous_code:
            code_preview = request.previousDesign['code'][:150].replace('\n', ' ')
            print(f"Previous code preview: {code_preview}...")
        print(f"{'='*60}\n")

        try:
            # Step 1: Searching product library
            yield sse({"step": 1, "message": "Searching product library for real-world dimensions and reference specs...", "status": "active", "detail": "Checking our database of 98+ product templates for matching measurements."})
            await asyncio.sleep(0.05)  # allow flush

            # Detect complexity for adaptive behavior
            complexity = claude_service._detect_complexity(request.prompt)
            complexity_labels = {"high": "Professional", "medium": "Detailed", "standard": "Standard"}
            complexity_label = complexity_labels.get(complexity, "Standard")

            # Step 2: Analyzing prompt with AI
            yield sse({"step": 1, "message": f"Product library checked — {complexity_label} complexity detected", "status": "done"})
            if is_modification:
                step2_msg = "Modifying your design — reading previous code and applying your changes..."
                step2_detail = "Claude is editing the existing CadQuery code to add/change only what you asked for."
            else:
                step2_msg = "Designing your product with Claude AI..."
                step2_detail = "Claude is analyzing your description, selecting dimensions, and writing parametric CadQuery code."
            yield sse({"step": 2, "message": step2_msg, "status": "active", "detail": step2_detail})

            ai_response = await claude_service.generate_design_from_prompt(
                prompt=request.prompt,
                previous_design=request.previousDesign
            )

            yield sse({"step": 2, "message": "AI design complete", "status": "done"})

            # Step 3: Completeness check + design review
            code = ai_response.get("code", "")
            param_count = len(ai_response.get("parameters", []))
            code_lines = code.count("\n") + 1
            explanation = ai_response.get("explanation", {})
            design_intent = explanation.get("design_intent", "")
            
            if code and not is_modification:
                yield sse({"step": 3, "message": "Checking design completeness...", "status": "active", "detail": "Analyzing generated code for missing features, cutouts, and detail level."})
                analysis = claude_service.analyze_code_completeness(code, request.prompt)
                
                print(f"\n📊 Completeness Analysis:")
                print(f"   Product type: {analysis['product_type']}")
                print(f"   Features: {analysis['total_features']} (cut={analysis['cut_count']}, union={analysis['union_count']})")
                print(f"   Treatments: fillet={analysis['fillet_count']}, round_cutters={analysis.get('round_cutter_count', 0)}")
                print(f"   Advanced: spline={analysis.get('spline_count', 0)}, loft={analysis.get('loft_count', 0)}, revolve={analysis.get('revolve_count', 0)}, sweep={analysis.get('sweep_count', 0)}")
                print(f"   Body: {'box-based' if analysis.get('main_body_is_box', True) else 'advanced shape'}")
                print(f"   Code lines: {analysis['code_lines']}")
                print(f"   Complete: {'✅' if analysis['is_complete'] else '❌'}")
                
                if not analysis["is_complete"]:
                    missing_summary = ", ".join(analysis["missing_features"][:4])
                    yield sse({"step": 3, "message": f"Found {len(analysis['missing_features'])} missing features — enhancing design...", "status": "active", "detail": f"Missing: {missing_summary}. Sending back to AI for targeted enhancement."})
                    
                    for mf in analysis["missing_features"]:
                        print(f"     • {mf}")
                    
                    ai_response = await claude_service.enhance_incomplete_design(ai_response, request.prompt, analysis)
                    
                    # Re-check after enhancement and update metrics
                    enhanced_code = ai_response.get("code", "")
                    if enhanced_code:
                        re_analysis = claude_service.analyze_code_completeness(enhanced_code, request.prompt)
                        code_lines = enhanced_code.count("\n") + 1
                        param_count = len(ai_response.get("parameters", []))
                        print(f"\n📊 Post-enhancement: features={re_analysis['total_features']}, complete={'✅' if re_analysis['is_complete'] else '⚠️'}")
                    
                    yield sse({"step": 3, "message": f"Design enhanced — {param_count} params, {code_lines} lines", "status": "done"})
                else:
                    step3_detail = f"Created {param_count} adjustable parameters across {code_lines} lines of CadQuery code."
                    if design_intent:
                        step3_detail += f" {design_intent}"
                    yield sse({"step": 3, "message": f"Design complete — {analysis['total_features']} features, {param_count} params", "status": "done", "detail": step3_detail})
            else:
                step3_detail = f"Created {param_count} adjustable parameters across {code_lines} lines of CadQuery code."
                if design_intent:
                    step3_detail += f" {design_intent}"
                yield sse({"step": 3, "message": f"Design validated — {param_count} parameters, {code_lines} lines", "status": "done", "detail": step3_detail})

            # Step 4: Executing CadQuery (infinite self-healing)
            attempt = 0
            while True:
                attempt += 1

                # Determine the healing phase name
                if attempt == 1:
                    phase_name = None  # first try, no healing yet
                elif attempt == 2:
                    phase_name = "Targeted fix"
                elif attempt <= 4:
                    phase_name = "Conservative fix"
                elif attempt <= 6:
                    phase_name = "Aggressive simplification"
                elif attempt <= 8:
                    phase_name = "Section rewrite"
                else:
                    phase_name = "Full rebuild"

                if attempt == 1:
                    yield sse({"step": 4, "message": "Building 3D geometry with CadQuery engine...", "status": "active", "detail": "Executing the Python code to construct solid 3D geometry with boolean operations, fillets, and cutouts."})
                else:
                    yield sse({"step": 4, "message": f"🔧 Self-healing ({phase_name}) — attempt {attempt-1}...", "status": "active", "detail": f"AI is applying {phase_name.lower()} strategy to fix the geometry error.", "healing": {"attempt": attempt - 1, "phase": phase_name}})

                try:
                    cad_result = await parametric_cad_service.generate_parametric_cad(ai_response)

                    if attempt == 1:
                        yield sse({"step": 4, "message": "3D model built successfully", "status": "done"})
                    else:
                        yield sse({"step": 4, "message": f"✅ 3D model built after {attempt - 1} self-healing fix{'es' if attempt > 2 else ''}", "status": "done", "healing": {"attempt": attempt - 1, "phase": phase_name, "resolved": True}})

                    # Emit quality warnings if any
                    quality_info = cad_result.get("quality", {})
                    quality_warnings = quality_info.get("warnings", [])
                    quality_metrics = quality_info.get("metrics", {})
                    if quality_warnings:
                        warnings_text = " | ".join(quality_warnings)
                        yield sse({"step": 4.5, "message": f"Quality notes: {warnings_text}", "status": "info", "detail": json.dumps(quality_metrics)})

                    # Step 5: Exporting files
                    yield sse({"step": 5, "message": "Exporting STL and STEP files...", "status": "active", "detail": "Generating STL (for 3D printing) and STEP (for CAD editing) from the solid model."})
                    await asyncio.sleep(0.05)
                    yield sse({"step": 5, "message": "Files exported — ready to download", "status": "done"})

                    # Final result — include full design for modification flow
                    # Save to database if available
                    saved_project_id = request.projectId
                    if DB_AVAILABLE:
                        try:
                            # Auto-create project if none specified
                            if not saved_project_id:
                                # Use first ~50 chars of prompt as project name
                                project_name = request.prompt[:50].strip()
                                if len(request.prompt) > 50:
                                    project_name += "..."
                                proj = database_service.create_project(name=project_name)
                                saved_project_id = proj["id"]

                            database_service.save_build(
                                project_id=saved_project_id,
                                build_id=cad_result["buildId"],
                                prompt=request.prompt,
                                code=ai_response.get("code"),
                                parameters=ai_response.get("parameters"),
                                explanation=ai_response.get("explanation"),
                                stl_path=cad_result.get("stlFile"),
                                step_path=cad_result.get("stepFile"),
                                script_path=cad_result.get("parametricScript"),
                                is_modification=is_modification,
                            )
                            print(f"💾 Build saved to MySQL (project={saved_project_id})")
                        except Exception as db_save_err:
                            print(f"⚠️ Failed to save build to DB: {db_save_err}")

                    yield sse({
                        "step": 6,
                        "message": "Build complete!",
                        "status": "complete",
                        "result": {
                            "buildId": cad_result["buildId"],
                            "stlUrl": cad_result["stlFile"],
                            "stepUrl": cad_result["stepFile"],
                            "parametricScript": cad_result.get("parametricScript"),
                            "parameters": cad_result.get("parameters"),
                            "explanation": cad_result.get("explanation"),
                            "design": {
                                "parameters": ai_response.get("parameters", []),
                                "code": ai_response.get("code", ""),
                                "explanation": ai_response.get("explanation", {})
                            },
                            "projectId": saved_project_id,
                            "healingAttempts": attempt - 1 if attempt > 1 else 0,
                            "success": True
                        }
                    })
                    return  # done

                except (RuntimeError, ValueError) as cad_err:
                    last_error = str(cad_err)
                    short_error = last_error[:150] + "..." if len(last_error) > 150 else last_error
                    # Use step 4 for errors too — keeps the list clean
                    yield sse({"step": 4, "message": f"⚠️ Error: {short_error}", "status": "error", "detail": last_error[:500], "healing": {"attempt": attempt, "errorType": type(cad_err).__name__}})

                    # Infinite self-healing — always retry, never give up
                    failed_code = ai_response.get("code", "")
                    ai_response = await claude_service.fix_code_with_error(
                        failed_code=failed_code,
                        error_message=last_error,
                        original_prompt=request.prompt,
                        attempt=attempt,
                        max_retries=0  # 0 signals infinite mode
                    )

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"\n{'='*60}\n❌ ERROR in /api/build/stream\n{'='*60}")
            print(error_details)

            try:
                log_path = Path(EXPORTS_DIR) / "error_log.txt"
                with open(log_path, "a", encoding="utf-8") as f:
                    import datetime
                    f.write(f"\n{'='*60}\n[{datetime.datetime.now()}] /api/build/stream error\n")
                    f.write(f"Prompt: {request.prompt}\nError: {str(e)}\n{error_details}\n{'='*60}\n")
            except:
                pass

            yield sse({"step": -1, "message": str(e), "status": "fatal"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )

@app.post("/api/rebuild")
async def rebuild_with_parameters(request: RebuildRequest):
    """
    Phase 4: Re-execute existing parametric script with new parameter values
    NO AI CALL - just re-runs Python code with updated parameters
    """
    try:
        result = await parametric_cad_service.rebuild_with_parameters(
            build_id=request.buildId,
            updated_parameters=request.parameters
        )
        
        return {
            "success": True,
            "buildId": result["buildId"],
            "stlUrl": result["stlFile"],
            "stepUrl": result["stepFile"],
            "message": "Model regenerated with updated parameters"
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/build/async")
async def build_product_async(request: AsyncBuildRequest):
    """
    Phase 4: Async CAD generation for CPU-intensive operations
    Returns task_id for status polling
    """
    if not CELERY_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="Celery not configured. Install redis and celery to use async mode."
        )
    
    try:
        build_id = str(uuid.uuid4())
        
        # Submit task to Celery worker
        task = generate_cad_async.delay(request.prompt, build_id)
        
        return {
            "success": True,
            "taskId": task.id,
            "buildId": build_id,
            "status": "queued",
            "message": "CAD generation task queued. Poll /api/task/{taskId} for status."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/task/{task_id}")
async def get_task_status(task_id: str):
    """
    Phase 4: Get async task status and result
    """
    if not CELERY_AVAILABLE:
        raise HTTPException(status_code=501, detail="Celery not configured")
    
    from celery.result import AsyncResult
    
    task = AsyncResult(task_id, app=generate_cad_async.app)
    
    if task.state == 'PENDING':
        response = {
            "state": task.state,
            "status": "Task is waiting in queue...",
            "progress": 0
        }
    elif task.state == 'PROCESSING':
        response = {
            "state": task.state,
            "status": task.info.get('status', ''),
            "progress": task.info.get('progress', 0)
        }
    elif task.state == 'SUCCESS':
        response = {
            "state": task.state,
            "status": "Completed",
            "progress": 100,
            "result": task.info
        }
    elif task.state == 'FAILURE':
        response = {
            "state": task.state,
            "status": str(task.info),
            "progress": 0,
            "error": str(task.info)
        }
    else:
        response = {
            "state": task.state,
            "status": str(task.info)
        }
    
    return response

@app.post("/api/s3/upload")
async def upload_to_s3(request: Dict[str, str]):
    """
    Phase 4: Upload build to S3 for sharing and caching
    """
    if not S3_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="S3 not configured. Set AWS credentials in .env"
        )
    
    try:
        build_id = request.get("buildId")
        if not build_id:
            raise HTTPException(status_code=400, detail="buildId required")
        
        result = await s3_service.upload_build(build_id, settings.CAD_DIR)
        
        return {
            "success": True,
            "buildId": build_id,
            "shareUrl": result["shareUrl"],
            "s3Key": result["s3Key"],
            "expiresAt": result["expiresAt"],
            "files": result["uploadedFiles"]
        }
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Build files not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/s3/download/{s3_key:path}")
async def download_from_s3(s3_key: str):
    """
    Phase 4: Download shared build from S3
    """
    if not S3_AVAILABLE:
        raise HTTPException(status_code=501, detail="S3 not configured")
    
    try:
        result = await s3_service.download_build(s3_key, settings.CAD_DIR)
        
        return {
            "success": True,
            "buildId": result["buildId"],
            "stlUrl": result.get("stlFile"),
            "stepUrl": result.get("stepFile"),
            "scriptUrl": result.get("scriptFile")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/s3/check/{build_id}")
async def check_s3_cache(build_id: str):
    """
    Phase 4: Check if build exists in S3 cache
    """
    if not S3_AVAILABLE:
        return {"cached": False, "message": "S3 not configured"}
    
    try:
        exists = await s3_service.check_build_exists(build_id)
        metadata = None
        
        if exists:
            metadata = await s3_service.get_build_metadata(build_id)
        
        return {
            "cached": exists,
            "buildId": build_id,
            "metadata": metadata
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/convert/glb")
async def convert_to_glb(request: Dict[str, str]):
    """
    Phase 4: Convert STL/STEP to GLB format for optimized web rendering
    """
    if not GLB_AVAILABLE:
        raise HTTPException(
            status_code=501,
            detail="GLB conversion not available. Install trimesh: pip install trimesh"
        )
    
    try:
        build_id = request.get("buildId")
        source_format = request.get("sourceFormat", "stl")  # "stl" or "step"
        optimize = request.get("optimize", True)
        
        if not build_id:
            raise HTTPException(status_code=400, detail="buildId required")
        
        if source_format == "stl":
            glb_url = await glb_service.convert_stl_to_glb(build_id, optimize=optimize)
        elif source_format == "step":
            quality = request.get("quality", "medium")
            glb_url = await glb_service.convert_step_to_glb(build_id, quality=quality)
        else:
            raise HTTPException(status_code=400, detail="sourceFormat must be 'stl' or 'step'")
        
        # Get mesh stats
        stats = await glb_service.get_mesh_stats(build_id, "glb")
        
        return {
            "success": True,
            "buildId": build_id,
            "glbUrl": glb_url,
            "stats": stats
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/mesh/stats/{build_id}")
async def get_mesh_stats(build_id: str, file_type: str = "stl"):
    """
    Phase 4: Get mesh statistics (vertices, faces, volume, etc.)
    """
    if not GLB_AVAILABLE:
        raise HTTPException(status_code=501, detail="Mesh analysis not available")
    
    try:
        stats = await glb_service.get_mesh_stats(build_id, file_type)
        return {
            "success": True,
            "buildId": build_id,
            "fileType": file_type,
            "stats": stats
        }
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Scene management endpoints (for frontend compatibility)
@app.post("/api/scene/create")
async def create_scene():
    """Create a new scene for managing multiple products"""
    scene_id = str(uuid.uuid4())
    scene_data = {
        "sceneId": scene_id,
        "name": "Default Scene",
        "products": []
    }
    return {
        "success": True,
        "scene": scene_data
    }

@app.get("/api/scene/{scene_id}")
async def get_scene(scene_id: str):
    """Get scene details"""
    return {
        "success": True,
        "sceneId": scene_id,
        "name": "Default Scene",
        "products": []
    }

@app.post("/api/scene/{scene_id}/add-product")
async def add_product_to_scene(scene_id: str, product: dict):
    """Add a product to the scene"""
    # Generate a unique instanceId if not provided
    if "instanceId" not in product or not product["instanceId"]:
        product["instanceId"] = str(uuid.uuid4())
    return {
        "success": True,
        "sceneId": scene_id,
        "product": product
    }

@app.put("/api/scene/product/{instance_id}/transform")
async def update_product_transform(instance_id: str, transform: dict):
    """Update a product's position/rotation/scale in the scene"""
    return {
        "success": True,
        "instanceId": instance_id,
        "position": transform.get("position", {"x": 0, "y": 0, "z": 0}),
        "rotation": transform.get("rotation", {"x": 0, "y": 0, "z": 0}),
        "scale": transform.get("scale", {"x": 1, "y": 1, "z": 1})
    }

@app.post("/api/scene/product/{instance_id}/duplicate")
async def duplicate_product(instance_id: str, options: dict = None):
    """Duplicate a product in the scene with an offset"""
    if options is None:
        options = {}
    offset = options.get("offset", {"x": 50, "y": 0, "z": 0})
    new_instance_id = str(uuid.uuid4())
    return {
        "success": True,
        "duplicate": {
            "instanceId": new_instance_id,
            "originalId": instance_id,
            "position": offset
        }
    }

@app.delete("/api/scene/product/{instance_id}")
async def delete_product_from_scene(instance_id: str):
    """Remove a product from the scene"""
    return {
        "success": True,
        "deleted": instance_id
    }

@app.post("/api/scene/{scene_id}/assemble")
async def assemble_products(scene_id: str, assembly: dict):
    """Group products into an assembly"""
    assembly_id = str(uuid.uuid4())
    return {
        "success": True,
        "assembly": {
            "assemblyId": assembly_id,
            "name": assembly.get("name", "Assembly"),
            "parentInstanceId": assembly.get("parentInstanceId"),
            "childInstanceIds": assembly.get("childInstanceIds", []),
            "sceneId": scene_id
        }
    }

@app.delete("/api/scene/assembly/{assembly_id}")
async def disassemble_products(assembly_id: str):
    """Break an assembly back into individual products"""
    return {
        "success": True,
        "disassembled": assembly_id
    }



# ── Project & History Endpoints (MySQL) ─────────────────────────────────

class ProjectCreateRequest(BaseModel):
    name: str = "Untitled Project"
    description: Optional[str] = None

class ProjectUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class SaveMessageRequest(BaseModel):
    projectId: str
    role: str
    content: str
    buildResult: Optional[Dict[str, Any]] = None
    status: Optional[str] = None

@app.get("/api/projects")
async def list_projects():
    """List all saved projects"""
    if not DB_AVAILABLE:
        return {"success": True, "projects": []}
    try:
        projects = database_service.list_projects()
        return {"success": True, "projects": projects}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/projects")
async def create_project(request: ProjectCreateRequest):
    """Create a new project"""
    if not DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        project = database_service.create_project(name=request.name, description=request.description)
        return {"success": True, "project": project}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/projects/{project_id}")
async def get_project(project_id: str):
    """Get project with all builds and chat messages"""
    if not DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        project = database_service.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"success": True, "project": project}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/projects/{project_id}")
async def update_project(project_id: str, request: ProjectUpdateRequest):
    """Update project name or description"""
    if not DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        project = database_service.update_project(project_id, name=request.name, description=request.description)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"success": True, "project": project}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project and all its builds/messages"""
    if not DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        deleted = database_service.delete_project(project_id)
        if not deleted:
            raise HTTPException(status_code=404, detail="Project not found")
        return {"success": True, "message": "Project deleted"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/messages")
async def save_message(request: SaveMessageRequest):
    """Save a chat message to a project"""
    if not DB_AVAILABLE:
        raise HTTPException(status_code=503, detail="Database not available")
    try:
        msg = database_service.save_chat_message(
            project_id=request.projectId,
            role=request.role,
            content=request.content,
            build_result=request.buildResult,
            status=request.status,
        )
        return {"success": True, "message": msg}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/history")
async def get_build_history():
    """Get recent builds across all projects"""
    if not DB_AVAILABLE:
        return {"success": True, "builds": []}
    try:
        builds = database_service.get_all_builds(limit=50)
        return {"success": True, "builds": builds}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# File serving endpoint
@app.get("/exports/cad/{filename}")
async def serve_cad_file(filename: str):
    """Serve generated CAD files (STL, STEP)"""
    file_path = CAD_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=3001,
        reload=True,
        log_level="info"
    )
