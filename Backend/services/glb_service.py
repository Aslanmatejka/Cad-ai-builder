"""
Phase 4: GLB Export Service
Converts STEP/STL files to GLB format for optimized Three.js rendering
"""

import subprocess
import trimesh
from pathlib import Path
from typing import Optional
import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import settings

class GLBService:
    """
    Converts CAD files to GLB format for web visualization
    Uses trimesh for STL->GLB and potentially FreeCAD for STEP->GLB
    """
    
    def __init__(self):
        self.output_dir = settings.CAD_DIR
    
    async def convert_stl_to_glb(
        self,
        build_id: str,
        optimize: bool = True
    ) -> str:
        """
        Convert STL to GLB using trimesh
        
        Args:
            build_id: Build identifier
            optimize: Apply mesh optimization (decimation, smoothing)
            
        Returns:
            Path to GLB file: "/exports/cad/{buildId}.glb"
        """
        
        stl_path = self.output_dir / f"{build_id}.stl"
        glb_path = self.output_dir / f"{build_id}.glb"
        
        if not stl_path.exists():
            raise FileNotFoundError(f"STL file not found: {stl_path}")
        
        try:
            # Load STL mesh
            mesh = trimesh.load(str(stl_path))
            
            if optimize:
                # Remove duplicate vertices
                mesh.merge_vertices()
                
                # Fix normals
                mesh.fix_normals()
                
                # Remove degenerate faces
                mesh.remove_degenerate_faces()
                
                # Optional: Simplify mesh if too large (>100k faces)
                if len(mesh.faces) > 100000:
                    target_faces = 50000
                    mesh = mesh.simplify_quadric_decimation(target_faces)
            
            # Export as GLB (binary glTF)
            mesh.export(str(glb_path), file_type='glb')
            
            return f"/exports/cad/{build_id}.glb"
            
        except Exception as e:
            raise RuntimeError(f"GLB conversion failed: {str(e)}")
    
    async def convert_step_to_glb(
        self,
        build_id: str,
        quality: str = "medium"
    ) -> str:
        """
        Convert STEP to GLB via intermediate STL
        
        Args:
            build_id: Build identifier
            quality: "low" | "medium" | "high" (tessellation quality)
            
        Returns:
            Path to GLB file
        """
        
        step_path = self.output_dir / f"{build_id}.step"
        glb_path = self.output_dir / f"{build_id}_from_step.glb"
        
        if not step_path.exists():
            raise FileNotFoundError(f"STEP file not found: {step_path}")
        
        try:
            # Import STEP using CadQuery (already has tessellation)
            import cadquery as cq
            from OCP.STEPControl import STEPControl_Reader
            from OCP.IFSelect import IFSelect_ReturnStatus
            
            # Read STEP file
            reader = STEPControl_Reader()
            status = reader.ReadFile(str(step_path))
            
            if status != IFSelect_ReturnStatus.IFSelect_RetDone:
                raise RuntimeError("Failed to read STEP file")
            
            reader.TransferRoots()
            shape = reader.OneShape()
            
            # Create workplane from shape
            result = cq.Workplane("XY").add(shape)
            
            # Export to STL with quality settings
            quality_settings = {
                "low": {"tolerance": 0.5, "angularTolerance": 0.3},
                "medium": {"tolerance": 0.1, "angularTolerance": 0.1},
                "high": {"tolerance": 0.01, "angularTolerance": 0.05}
            }
            
            settings_dict = quality_settings.get(quality, quality_settings["medium"])
            
            # Export to temporary STL
            temp_stl = self.output_dir / f"{build_id}_temp.stl"
            cq.exporters.export(result, str(temp_stl), **settings_dict)
            
            # Convert STL to GLB
            mesh = trimesh.load(str(temp_stl))
            mesh.export(str(glb_path), file_type='glb')
            
            # Clean up temporary STL
            temp_stl.unlink()
            
            return f"/exports/cad/{build_id}_from_step.glb"
            
        except Exception as e:
            raise RuntimeError(f"STEP to GLB conversion failed: {str(e)}")
    
    async def get_mesh_stats(self, build_id: str, file_type: str = "stl") -> dict:
        """
        Get statistics about the mesh
        
        Args:
            build_id: Build identifier
            file_type: "stl" | "glb"
            
        Returns:
            {
                "vertices": int,
                "faces": int,
                "watertight": bool,
                "volume": float,
                "bounds": {"min": [x,y,z], "max": [x,y,z]},
                "fileSize": int (bytes)
            }
        """
        
        file_path = self.output_dir / f"{build_id}.{file_type}"
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        try:
            mesh = trimesh.load(str(file_path))
            
            return {
                "vertices": len(mesh.vertices),
                "faces": len(mesh.faces),
                "watertight": mesh.is_watertight,
                "volume": float(mesh.volume),
                "bounds": {
                    "min": mesh.bounds[0].tolist(),
                    "max": mesh.bounds[1].tolist()
                },
                "fileSize": file_path.stat().st_size
            }
            
        except Exception as e:
            raise RuntimeError(f"Failed to analyze mesh: {str(e)}")

# Singleton instance
glb_service = GLBService()
