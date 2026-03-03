"""
CAD Import Service
Imports STEP, STL, IGES, DXF, OBJ, 3MF files into CadQuery workplanes.
Enables NLP editing of uploaded CAD files.
"""

import cadquery as cq
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import uuid
import json
import math
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import settings

# Optional mesh libraries
try:
    import trimesh
    TRIMESH_AVAILABLE = True
except ImportError:
    trimesh = None
    TRIMESH_AVAILABLE = False

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False


# ── Supported formats ────────────────────────────────────────────────────
SUPPORTED_FORMATS = {
    # Native CadQuery / OCC importers (solid geometry — full NLP edit support)
    ".step": {"type": "solid", "label": "STEP (ISO 10303)", "editable": True},
    ".stp":  {"type": "solid", "label": "STEP (ISO 10303)", "editable": True},
    ".iges": {"type": "solid", "label": "IGES", "editable": True},
    ".igs":  {"type": "solid", "label": "IGES", "editable": True},
    ".brep": {"type": "solid", "label": "BRep (OpenCASCADE)", "editable": True},
    ".dxf":  {"type": "2d",    "label": "DXF (AutoCAD 2D)", "editable": True},

    # Mesh formats (via trimesh — view + convert, limited NLP edit)
    ".stl":  {"type": "mesh", "label": "STL (Stereolithography)", "editable": False},
    ".obj":  {"type": "mesh", "label": "OBJ (Wavefront)", "editable": False},
    ".3mf":  {"type": "mesh", "label": "3MF (3D Manufacturing)", "editable": False},
    ".ply":  {"type": "mesh", "label": "PLY (Polygon File)", "editable": False},
    ".off":  {"type": "mesh", "label": "OFF (Object File Format)", "editable": False},
    ".glb":  {"type": "mesh", "label": "GLB (glTF Binary)", "editable": False},
    ".gltf": {"type": "mesh", "label": "glTF (GL Transmission)", "editable": False},
}


class CADImportService:
    """Import external CAD files, convert for visualization, enable NLP editing."""

    def __init__(self):
        self.output_dir = settings.CAD_DIR
        self.upload_dir = Path(settings.EXPORTS_DIR) / "uploads"
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    # ── Public API ────────────────────────────────────────────────────────

    async def import_file(
        self,
        file_bytes: bytes,
        original_filename: str,
        build_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Import an uploaded file → convert to STEP + STL → return metadata.

        Returns:
            {
                "buildId": str,
                "originalFilename": str,
                "format": str,
                "formatInfo": {...},
                "stlFile": str,
                "stepFile": str | None,
                "boundingBox": { width, depth, height },
                "geometryInfo": { faces, edges, vertices, volume, ... },
                "editable": bool,     # True if NLP editing is supported
                "importCode": str,    # CadQuery code to reproduce the import
                "success": True,
            }
        """
        if not build_id:
            build_id = str(uuid.uuid4())

        ext = Path(original_filename).suffix.lower()
        fmt_info = SUPPORTED_FORMATS.get(ext)
        if not fmt_info:
            supported = ", ".join(sorted(SUPPORTED_FORMATS.keys()))
            raise ValueError(
                f"Unsupported file format '{ext}'. Supported formats: {supported}"
            )

        # Save the raw upload
        upload_path = self.upload_dir / f"{build_id}{ext}"
        upload_path.write_bytes(file_bytes)

        step_path = self.output_dir / f"{build_id}.step"
        stl_path = self.output_dir / f"{build_id}.stl"

        geometry_info = {}
        bounding_box = {}
        import_code = ""

        if fmt_info["type"] == "solid":
            # ── Solid geometry import (STEP / IGES / BRep) ───────────
            workplane = self._import_solid(str(upload_path), ext)
            geometry_info = self._extract_geometry_info(workplane)
            bounding_box = self._extract_bounding_box(workplane)

            # Export STEP (copy or re-export)
            cq.exporters.export(workplane, str(step_path))
            # Export STL for 3D preview
            self._export_stl(workplane, stl_path)

            import_code = self._generate_import_code(build_id, ext, bounding_box)

        elif fmt_info["type"] == "2d":
            # ── 2D import (DXF) ──────────────────────────────────────
            workplane = cq.importers.importDXF(str(upload_path))
            # Extrude to make it 3D (default 10mm)
            solid = workplane.wires().toPending().extrude(10)
            geometry_info = self._extract_geometry_info(solid)
            bounding_box = self._extract_bounding_box(solid)
            cq.exporters.export(solid, str(step_path))
            self._export_stl(solid, stl_path)
            import_code = self._generate_import_code(build_id, ext, bounding_box)

        elif fmt_info["type"] == "mesh":
            # ── Mesh import (STL / OBJ / 3MF / etc.) ────────────────
            if not TRIMESH_AVAILABLE:
                raise RuntimeError(
                    "trimesh is required for mesh file import. "
                    "Install with: pip install trimesh"
                )
            mesh_result = self._import_mesh(str(upload_path), ext, stl_path, step_path)
            geometry_info = mesh_result["geometry_info"]
            bounding_box = mesh_result["bounding_box"]
            import_code = self._generate_mesh_import_code(build_id, bounding_box)
            # For mesh files, mark step as available only if conversion succeeded
            if not step_path.exists():
                step_path = None

        result = {
            "buildId": build_id,
            "originalFilename": original_filename,
            "format": ext,
            "formatInfo": fmt_info,
            "stlFile": f"/exports/cad/{build_id}.stl",
            "stepFile": f"/exports/cad/{build_id}.step" if step_path and Path(step_path).exists() else None,
            "boundingBox": bounding_box,
            "geometryInfo": geometry_info,
            "editable": fmt_info["editable"],
            "importCode": import_code,
            "success": True,
        }
        return result

    def get_supported_formats(self) -> Dict[str, Any]:
        """Return list of supported file formats with metadata."""
        return {
            "formats": SUPPORTED_FORMATS,
            "solidFormats": [k for k, v in SUPPORTED_FORMATS.items() if v["type"] == "solid"],
            "meshFormats": [k for k, v in SUPPORTED_FORMATS.items() if v["type"] == "mesh"],
            "2dFormats": [k for k, v in SUPPORTED_FORMATS.items() if v["type"] == "2d"],
        }

    # ── Private: Solid importers ──────────────────────────────────────────

    def _import_solid(self, filepath: str, ext: str) -> cq.Workplane:
        """Import a solid CAD file into a CadQuery Workplane."""
        if ext in (".step", ".stp"):
            return cq.importers.importStep(filepath)
        elif ext in (".iges", ".igs"):
            return self._import_iges(filepath)
        elif ext == ".brep":
            return cq.importers.importBrep(filepath)
        else:
            raise ValueError(f"No solid importer for {ext}")

    def _import_iges(self, filepath: str) -> cq.Workplane:
        """Import IGES via OCC kernel."""
        from OCP.IGESControl import IGESControl_Reader
        from OCP.IFSelect import IFSelect_RetDone

        reader = IGESControl_Reader()
        status = reader.ReadFile(filepath)
        if status != IFSelect_RetDone:
            raise RuntimeError(f"Failed to read IGES file (status={status})")
        reader.TransferRoots()
        shape = reader.OneShape()
        return cq.Workplane("XY").newObject([cq.Shape.cast(shape)])

    # ── Private: Mesh importers ───────────────────────────────────────────

    def _import_mesh(
        self, filepath: str, ext: str, stl_out: Path, step_out: Path
    ) -> Dict[str, Any]:
        """Import a mesh file, export as STL, attempt STEP conversion."""
        mesh = trimesh.load(filepath)

        # Handle Scene objects (multi-body meshes)
        if isinstance(mesh, trimesh.Scene):
            meshes = [g for g in mesh.geometry.values() if isinstance(g, trimesh.Trimesh)]
            if not meshes:
                raise ValueError("No valid geometry found in uploaded file")
            mesh = trimesh.util.concatenate(meshes)

        # Export STL (always works)
        mesh.export(str(stl_out), file_type="stl")

        # Extract geometry metadata
        bb = mesh.bounding_box.extents
        geometry_info = {
            "vertices": int(len(mesh.vertices)),
            "faces": int(len(mesh.faces)),
            "volume": round(float(mesh.volume), 2) if mesh.is_volume else None,
            "isWatertight": bool(mesh.is_watertight),
            "surfaceArea": round(float(mesh.area), 2),
        }
        bounding_box = {
            "width": round(float(bb[0]), 2),
            "depth": round(float(bb[1]), 2),
            "height": round(float(bb[2]), 2),
        }

        # Attempt mesh-to-solid conversion for STEP export
        try:
            self._mesh_to_step(mesh, step_out)
        except Exception as e:
            print(f"⚠️ Mesh→STEP conversion failed (view-only): {e}")
            # STL-only is still valid for visualization

        return {"geometry_info": geometry_info, "bounding_box": bounding_box}

    def _mesh_to_step(self, mesh, step_out: Path):
        """Best-effort: convert mesh to solid via OCC sewing."""
        from OCP.BRep import BRep_Builder
        from OCP.TopoDS import TopoDS_Shell, TopoDS_Solid
        from OCP.BRepBuilderAPI import BRepBuilderAPI_Sewing, BRepBuilderAPI_MakeSolid
        from OCP.gp import gp_Pnt
        from OCP.BRepBuilderAPI import BRepBuilderAPI_MakePolygon, BRepBuilderAPI_MakeFace

        sewing = BRepBuilderAPI_Sewing(1e-3)
        verts = mesh.vertices
        faces = mesh.faces

        for tri in faces:
            pts = [gp_Pnt(float(verts[i][0]), float(verts[i][1]), float(verts[i][2])) for i in tri]
            wire = BRepBuilderAPI_MakePolygon(pts[0], pts[1], pts[2], True).Wire()
            face = BRepBuilderAPI_MakeFace(wire, True).Face()
            sewing.Add(face)

        sewing.Perform()
        sewn = sewing.SewedShape()

        try:
            solid_maker = BRepBuilderAPI_MakeSolid()
            solid_maker.Add(cq.Shape.cast(sewn).wrapped)
            solid = solid_maker.Solid()
            wp = cq.Workplane("XY").newObject([cq.Shape.cast(solid)])
            cq.exporters.export(wp, str(step_out))
        except Exception:
            # Fallback: export the sewn shell as STEP (not solid, but still STEP)
            wp = cq.Workplane("XY").newObject([cq.Shape.cast(sewn)])
            cq.exporters.export(wp, str(step_out))

    # ── Private: Geometry analysis ────────────────────────────────────────

    def _extract_geometry_info(self, workplane: cq.Workplane) -> Dict[str, Any]:
        """Extract geometry metadata from a CadQuery Workplane."""
        try:
            solids = workplane.solids().vals()
            faces = workplane.faces().vals()
            edges = workplane.edges().vals()
            vertices = workplane.vertices().vals()

            total_volume = 0
            for solid in solids:
                try:
                    total_volume += solid.Volume()
                except:
                    pass

            return {
                "solids": len(solids),
                "faces": len(faces),
                "edges": len(edges),
                "vertices": len(vertices),
                "volume": round(total_volume, 2) if total_volume > 0 else None,
            }
        except Exception as e:
            return {"error": str(e)}

    def _extract_bounding_box(self, workplane: cq.Workplane) -> Dict[str, float]:
        """Extract bounding box dimensions."""
        try:
            bb = workplane.val().BoundingBox()
            return {
                "width": round(bb.xlen, 2),
                "depth": round(bb.ylen, 2),
                "height": round(bb.zlen, 2),
                "center": {
                    "x": round(bb.center.x, 2),
                    "y": round(bb.center.y, 2),
                    "z": round(bb.center.z, 2),
                },
            }
        except Exception as e:
            return {"error": str(e)}

    # ── Private: STL export ───────────────────────────────────────────────

    def _export_stl(self, workplane: cq.Workplane, stl_path: Path):
        """Export a workplane to STL with fallback tolerances."""
        try:
            cq.exporters.export(workplane, str(stl_path), exportType="STL",
                                tolerance=0.1, angularTolerance=0.1)
        except Exception:
            cq.exporters.export(workplane, str(stl_path))

    # ── Private: Code generation for NLP editing ─────────────────────────

    def _generate_import_code(
        self, build_id: str, ext: str, bounding_box: Dict
    ) -> str:
        """Generate CadQuery code that loads the uploaded file as a workplane."""
        w = bounding_box.get("width", "?")
        d = bounding_box.get("depth", "?")
        h = bounding_box.get("height", "?")
        return f"""import cadquery as cq

# ── Imported solid from uploaded {ext} file ──
# Bounding box: {w} x {d} x {h} mm
uploaded_path = r"exports/uploads/{build_id}{ext}"
result = cq.importers.importStep(uploaded_path)

# ═══════════════════════════════════════════════════════════════
# GEOMETRY GENERATION
# You can now modify 'result' using standard CadQuery operations:
#   result = result.faces(">Z").workplane().hole(10)       # drill a hole
#   result = result.edges("|Z").fillet(2)                  # fillet edges
#   result = result.faces("<Z").workplane().rect(20,20).cutBlind(-5)  # pocket
# ═══════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════
"""

    def _generate_mesh_import_code(
        self, build_id: str, bounding_box: Dict
    ) -> str:
        """Generate placeholder code for mesh imports (limited editability)."""
        w = bounding_box.get("width", "?")
        d = bounding_box.get("depth", "?")
        h = bounding_box.get("height", "?")
        return f"""import cadquery as cq

# ── Imported mesh (converted to solid approximation) ──
# Original bounding box: {w} x {d} x {h} mm
# NOTE: Mesh files have limited NLP edit support.
#       For full editing, upload a STEP or IGES file.

# Approximate the model as a box matching the bounding box
body_width = {w}
body_depth = {d}
body_height = {h}
result = cq.Workplane("XY").box(body_width, body_depth, body_height, centered=(True, True, False))

# ═══════════════════════════════════════════════════════════════
# GEOMETRY GENERATION
# ═══════════════════════════════════════════════════════════════

# ═══════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════
"""


# ── Singleton ─────────────────────────────────────────────────────────────
cad_import_service = CADImportService()
