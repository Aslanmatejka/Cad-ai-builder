"""
Phase 4: Async Task Queue for CPU-Intensive CAD Operations
Uses Celery with Redis broker for background processing
"""

from celery import Celery
from typing import Dict, Any
import os
from pathlib import Path

# Initialize Celery
celery_app = Celery(
    'cad_tasks',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50
)

@celery_app.task(name='tasks.generate_cad_async', bind=True)
def generate_cad_async(self, prompt: str, build_id: str):
    """
    Async task for CAD generation
    Runs in Celery worker process
    
    Args:
        prompt: Natural language design prompt
        build_id: Unique build identifier
        
    Returns:
        {
            "buildId": str,
            "stepFile": str,
            "stlFile": str,
            "status": "success" | "failed",
            "error": str (optional)
        }
    """
    try:
        # Update task state
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Generating CadQuery code...', 'progress': 10}
        )
        
        # Import services (lazy import to avoid circular dependencies)
        from services.claude_service import claude_service
        from services.parametric_cad_service import parametric_cad_service
        
        # Step 1: Generate code with Claude
        import asyncio
        loop = asyncio.get_event_loop()
        ai_response = loop.run_until_complete(
            claude_service.generate_design_from_prompt(prompt)
        )
        
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Executing CadQuery geometry...', 'progress': 50}
        )
        
        # Step 2: Execute CadQuery code
        cad_result = loop.run_until_complete(
            parametric_cad_service.generate_parametric_cad(ai_response, build_id)
        )
        
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Exporting STEP/STL files...', 'progress': 90}
        )
        
        return {
            "buildId": cad_result["buildId"],
            "stepFile": cad_result["stepFile"],
            "stlFile": cad_result["stlFile"],
            "parametricScript": cad_result.get("parametricScript"),
            "parameters": cad_result.get("parameters"),
            "explanation": cad_result.get("explanation"),
            "status": "success"
        }
        
    except Exception as e:
        self.update_state(
            state='FAILURE',
            meta={'status': f'Failed: {str(e)}', 'progress': 0}
        )
        return {
            "buildId": build_id,
            "status": "failed",
            "error": str(e)
        }

@celery_app.task(name='tasks.rebuild_async', bind=True)
def rebuild_async(self, build_id: str, parameters: Dict[str, float]):
    """
    Async task for parameter-only rebuild
    No AI call - just re-executes Python script
    
    Args:
        build_id: Original build ID
        parameters: {param_name: new_value}
        
    Returns:
        {
            "buildId": str,
            "stepFile": str,
            "stlFile": str,
            "status": "success" | "failed"
        }
    """
    try:
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Re-executing CadQuery script...', 'progress': 30}
        )
        
        from services.parametric_cad_service import parametric_cad_service
        import asyncio
        
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(
            parametric_cad_service.rebuild_with_parameters(build_id, parameters)
        )
        
        self.update_state(
            state='PROCESSING',
            meta={'status': 'Exporting updated geometry...', 'progress': 80}
        )
        
        return {
            "buildId": result["buildId"],
            "stepFile": result["stepFile"],
            "stlFile": result["stlFile"],
            "status": "success"
        }
        
    except Exception as e:
        self.update_state(
            state='FAILURE',
            meta={'status': f'Rebuild failed: {str(e)}', 'progress': 0}
        )
        return {
            "buildId": build_id,
            "status": "failed",
            "error": str(e)
        }
