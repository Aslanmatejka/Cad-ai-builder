"""
CadQuery Geometry Generation Service
Converts design JSON into STEP/STL CAD files
"""

import cadquery as cq
from typing import Dict, Any, Tuple, Optional
from pathlib import Path
import uuid
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import settings

class CadQueryService:
    """CAD geometry generation using CadQuery"""
    
    def __init__(self):
        self.output_dir = settings.CAD_DIR
    
    async def generate_cad(
        self,
        design: Dict[str, Any],
        build_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generate STEP and STL files from design JSON
        
        Args:
            design: Design specification JSON
            build_id: Optional custom build ID (generates UUID if None)
            
        Returns:
            {
                "buildId": str,
                "stepFile": str,  // Relative path
                "stlFile": str,   // Relative path
                "parametricScript": str  // Python script for user editing
            }
        """
        
        if not build_id:
            build_id = str(uuid.uuid4())
        
        # Generate CadQuery result
        result = self._build_geometry(design)
        
        # Export files
        step_path = self.output_dir / f"{build_id}.step"
        stl_path = self.output_dir / f"{build_id}.stl"
        script_path = self.output_dir / f"{build_id}_parametric.py"
        
        # Export STEP (editable CAD)
        cq.exporters.export(result, str(step_path))
        
        # Export STL (3D printable)
        cq.exporters.export(result, str(stl_path))
        
        # Generate parametric Python script
        script_content = self._generate_parametric_script(design, result)
        script_path.write_text(script_content, encoding="utf-8")
        
        return {
            "buildId": build_id,
            "stepFile": f"/exports/cad/{build_id}.step",
            "stlFile": f"/exports/cad/{build_id}.stl",
            "parametricScript": f"/exports/cad/{build_id}_parametric.py"
        }
    
    def _build_geometry(self, design: Dict[str, Any]) -> cq.Workplane:
        """
        Build CadQuery geometry from design specification
        
        This is the core geometry generation logic
        """
        
        # Extract dimensions
        dims = design.get("dimensions", {})
        length = dims.get("length", 50)
        width = dims.get("width", 30)
        height = dims.get("height", 20)
        
        product_type = design.get("product_type", "box")
        wall_thickness = design.get("wall_thickness", 2.0)
        
        # Start with base shape
        if product_type in ["box", "enclosure"]:
            # Create hollow box
            result = (
                cq.Workplane("XY")
                .box(length, width, height)
                .faces(">Z")
                .shell(-wall_thickness)
            )
        elif product_type == "bracket":
            # Create L-bracket
            result = (
                cq.Workplane("XY")
                .box(length, width, wall_thickness)
                .faces(">Z")
                .workplane()
                .box(wall_thickness, width, height)
            )
        else:
            # Default: solid box
            result = cq.Workplane("XY").box(length, width, height)
        
        # Apply features
        features = design.get("features", [])
        for feature in features:
            result = self._apply_feature(result, feature)
        
        return result
    
    def _apply_feature(
        self,
        workplane: cq.Workplane,
        feature: Dict[str, Any]
    ) -> cq.Workplane:
        """Apply a single feature to the workplane"""
        
        feature_type = feature.get("type")
        params = feature.get("parameters", {})
        pos = feature.get("position", {})
        
        if feature_type == "mounting_hole":
            diameter = params.get("diameter", 3.2)
            depth = params.get("depth", None)  # None = through hole
            
            result = (
                workplane
                .faces(">Z")
                .workplane()
                .center(pos.get("x", 0), pos.get("y", 0))
                .circle(diameter / 2)
            )
            
            if depth:
                result = result.cutBlind(-depth)
            else:
                result = result.cutThruAll()
            
            return result
        
        elif feature_type == "fillet":
            radius = params.get("radius", 1.0)
            return workplane.edges().fillet(radius)
        
        elif feature_type == "chamfer":
            distance = params.get("distance", 0.5)
            return workplane.edges().chamfer(distance)
        
        # Add more feature types as needed
        return workplane
    
    def _generate_parametric_script(
        self,
        design: Dict[str, Any],
        result: cq.Workplane
    ) -> str:
        """
        Generate editable Python script for CadQuery
        Users can modify variables and re-run
        """
        
        dims = design.get("dimensions", {})
        
        script = f'''"""
Generated CadQuery Parametric Script
Edit the variables below and run to regenerate the model
"""

import cadquery as cq

# ============================================
# DESIGN PARAMETERS (Edit these values)
# ============================================

# Dimensions (mm)
length = {dims.get("length", 50)}
width = {dims.get("width", 30)}
height = {dims.get("height", 20)}
wall_thickness = {design.get("wall_thickness", 2.0)}

# Material
material = "{design.get("material", "PLA")}"

# ============================================
# GEOMETRY GENERATION (CadQuery code)
# ============================================

result = (
    cq.Workplane("XY")
    .box(length, width, height)
    .faces(">Z")
    .shell(-wall_thickness)
)

# Export
result.val().exportStep("output.step")
result.val().exportStl("output.stl")

print(f"Generated {{material}} part: {{length}}x{{width}}x{{height}}mm")
'''
        
        return script

# Singleton instance
cadquery_service = CadQueryService()
