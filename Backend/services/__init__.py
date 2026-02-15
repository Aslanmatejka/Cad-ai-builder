"""Services module initialization"""

from .claude_service import claude_service
from .cadquery_service import cadquery_service
from .parametric_cad_service import parametric_cad_service
from .product_library import search_products, lookup as product_lookup
from .database_service import database_service

# Phase 4: Optional S3 service (requires boto3)
try:
    from .s3_service import s3_service
    S3_AVAILABLE = True
except ImportError:
    s3_service = None
    S3_AVAILABLE = False

# Phase 4: Optional GLB service (requires trimesh)
try:
    from .glb_service import glb_service
    GLB_AVAILABLE = True
except ImportError:
    glb_service = None
    GLB_AVAILABLE = False

__all__ = [
    'claude_service', 
    'cadquery_service', 
    'parametric_cad_service', 
    'database_service',
    'search_products',
    'product_lookup',
    's3_service', 
    'S3_AVAILABLE',
    'glb_service',
    'GLB_AVAILABLE'
]
