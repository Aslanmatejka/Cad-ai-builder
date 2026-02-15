"""
Design Validator - Ensures CAD design JSON meets requirements
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, validator, Field

class Dimensions(BaseModel):
    """3D dimensions for the part"""
    length: float = Field(gt=0, le=2000, description="X-axis dimension in mm")
    width: float = Field(gt=0, le=2000, description="Y-axis dimension in mm")
    height: float = Field(gt=0, le=2000, description="Z-axis dimension in mm")

class Position(BaseModel):
    """3D position coordinates"""
    x: float
    y: float
    z: Optional[float] = 0

class Feature(BaseModel):
    """Design feature (hole, fillet, etc.)"""
    type: str = Field(
        description="Feature type: mounting_hole, cutout, boss, fillet, chamfer"
    )
    position: Optional[Position] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('type')
    def validate_feature_type(cls, v):
        valid_types = {
            'mounting_hole', 'cutout', 'boss', 'fillet', 
            'chamfer', 'pocket', 'extrusion'
        }
        if v not in valid_types:
            raise ValueError(f"Feature type must be one of {valid_types}")
        return v

class DesignSpec(BaseModel):
    """Complete CAD design specification"""
    
    product_type: str = Field(
        default="box",
        description="Type: box, enclosure, bracket, plate, custom"
    )
    units: str = Field(default="mm", description="Unit system (mm or inches)")
    dimensions: Dimensions
    features: List[Feature] = Field(default_factory=list)
    wall_thickness: Optional[float] = Field(
        None,
        ge=1.5,
        description="Wall thickness for hollow parts (≥1.5mm)"
    )
    material: str = Field(
        default="PLA",
        description="Material: PLA, ABS, PETG, Aluminum, Steel"
    )
    
    @validator('wall_thickness')
    def validate_wall_thickness(cls, v, values):
        if v is not None and v < 1.5:
            raise ValueError("Wall thickness must be ≥ 1.5mm for structural integrity")
        return v
    
    @validator('units')
    def validate_units(cls, v):
        if v not in ['mm', 'inches']:
            raise ValueError("Units must be 'mm' or 'inches'")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "product_type": "box",
                "units": "mm",
                "dimensions": {
                    "length": 50,
                    "width": 30,
                    "height": 20
                },
                "wall_thickness": 2.0,
                "features": [
                    {
                        "type": "mounting_hole",
                        "position": {"x": 10, "y": 10, "z": 0},
                        "parameters": {"diameter": 3.2, "depth": None}
                    }
                ],
                "material": "PLA"
            }
        }

def validate_design(design_json: Dict[str, Any]) -> DesignSpec:
    """
    Validate design JSON against schema
    
    Raises:
        ValidationError if design is invalid
    
    Returns:
        Validated DesignSpec object
    """
    return DesignSpec(**design_json)
