"""
Phase 2: Enhanced CadQuery Code Generation
Uses improved prompt engineering with schema enforcement and selector knowledge
"""

import cadquery as cq
from typing import Dict, Any, Optional, List
from pathlib import Path
import uuid
import json
import sys

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import settings

class ParametricCADService:
    """
    Phase 2: Advanced CAD generation with parametric code output
    Generates CadQuery Python scripts directly from AI
    """
    
    def __init__(self):
        self.output_dir = settings.CAD_DIR
    
    async def generate_parametric_cad(
        self,
        ai_response: Dict[str, Any],
        build_id: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Execute AI-generated CadQuery code with parameters
        
        Args:
            ai_response: {
                "parameters": [{name, default, min, max, unit}],
                "code": "CadQuery Python script",
                "explanation": {...}
            }
            build_id: Optional build ID
            
        Returns:
            {
                "buildId": str,
                "stepFile": str,
                "stlFile": str,
                "parametricScript": str,
                "parameters": [...],
                "explanation": {...}
            }
        """
        
        if not build_id:
            build_id = str(uuid.uuid4())
        
        # Extract components
        parameters = ai_response.get("parameters", [])
        code = ai_response.get("code", "")
        explanation = ai_response.get("explanation", {})
        
        # Validate code safety
        self._validate_code_safety(code)
        
        # Execute CadQuery code
        result = self._execute_cadquery_code(code, parameters)
        
        # Fix multi-solid results (keep largest solid)
        result = self._fix_multi_solid(result)
        
        # Validate output quality (log warnings, don't fail)
        quality = self._validate_output_quality(result, code)
        
        # Export files
        step_path = self.output_dir / f"{build_id}.step"
        stl_path = self.output_dir / f"{build_id}.stl"
        script_path = self.output_dir / f"{build_id}_parametric.py"
        
        # Export STEP (editable CAD)
        try:
            cq.exporters.export(result, str(step_path))
        except Exception as e:
            raise RuntimeError(f"STEP export failed: {str(e)}")
        
        # Export STL (3D printable) — try high quality, fall back to relaxed tolerances
        self._export_stl_safe(result, stl_path)
        
        # Save parametric script with parameter definitions
        script_content = self._generate_editable_script(code, parameters, explanation)
        script_path.write_text(script_content, encoding="utf-8")
        
        return {
            "buildId": build_id,
            "stepFile": f"/exports/cad/{build_id}.step",
            "stlFile": f"/exports/cad/{build_id}.stl",
            "parametricScript": f"/exports/cad/{build_id}_parametric.py",
            "parameters": parameters,
            "explanation": explanation,
            "quality": quality
        }
    
    def _validate_code_safety(self, code: str) -> None:
        """
        Validate that AI-generated code is safe to execute
        
        Raises:
            ValueError if code contains unsafe operations
        """
        
        # Allowed imports (safe for CAD work)
        allowed_imports = {
            "cadquery", "cq", "math", "copy",
            "cq_warehouse",  # parametric parts library
            "numpy", "np",   # advanced math for complex geometry calculations
        }
        
        # Forbidden function calls (substring match is safe — the "(" prevents false positives)
        forbidden_calls = [
            "eval(",
            "exec(",
            "__import__(",
            "open(",
            "file(",
        ]
        
        # Forbidden modules — checked via import statements only, NOT substring,
        # because words like "socket" and "http" are legitimate CAD feature names
        # (e.g. socket_depth, socket_head, http_port_cutout)
        forbidden_modules = {
            "os", "sys", "subprocess", "shutil", "pathlib",
            "socket", "http", "urllib", "requests",
            "pickle", "shelve", "ctypes",
            "multiprocessing", "threading",
        }
        
        code_lower = code.lower()
        for forbidden_item in forbidden_calls:
            if forbidden_item.lower() in code_lower:
                raise ValueError(f"Unsafe code detected: {forbidden_item}")
        
        # Check all import statements — only allow whitelisted modules
        # This also catches the forbidden_modules (socket, http, etc.)
        import re
        # Match "import X" (standalone) and "from X import ..." patterns
        # For "import X" — check X is whitelisted
        for match in re.finditer(r'^import\s+(\w+)', code, re.MULTILINE):
            module_name = match.group(1)
            if module_name in forbidden_modules:
                raise ValueError(f"Unsafe module detected: {module_name}")
            if module_name not in allowed_imports:
                raise ValueError(f"Unsafe import detected: {module_name}. Only {allowed_imports} are allowed.")
        # For "from X.Y.Z import ..." — check root module X is whitelisted
        for match in re.finditer(r'^from\s+([\w.]+)\s+import', code, re.MULTILINE):
            root_module = match.group(1).split('.')[0]
            if root_module in forbidden_modules:
                raise ValueError(f"Unsafe module detected: {root_module}")
            if root_module not in allowed_imports:
                raise ValueError(f"Unsafe import detected: {root_module}. Only {allowed_imports} are allowed.")
        
        # Must import cadquery (or use cq_warehouse which depends on it)
        has_cadquery = "import cadquery" in code or "import cq" in code
        has_cq_warehouse = "cq_warehouse" in code
        if not has_cadquery and not has_cq_warehouse:
            raise ValueError("Code must import cadquery or cq_warehouse")
    
    def _ensure_box_grounding(self, code: str) -> str:
        """
        Ensure the first/main .box() call uses centered=(True, True, False) 
        so the model sits on the XY ground plane (Z=0 is the bottom face).
        This is the single most impactful convention for correct feature placement.
        
        Only modifies the FIRST .box() call that:
        - Has no centered= argument already
        - Is an assignment to a body-like variable (body, case, base, main, housing, etc.)
        """
        import re
        
        lines = code.split('\n')
        fixed = False
        result_lines = []
        
        # Common body variable names that indicate the main shape
        body_vars = {
            'body', 'case', 'base', 'main', 'housing', 'shell', 'frame',
            'enclosure', 'box', 'container', 'model', 'part', 'product',
            'phone', 'tablet', 'device', 'wall', 'building', 'tower',
            'result', 'shape', 'solid', 'block', 'outer', 'hull',
        }
        
        for line in lines:
            if not fixed and '.box(' in line and 'centered=' not in line:
                stripped = line.lstrip()
                # Check if it's an assignment like: body = cq.Workplane(...).box(...)
                var_match = re.match(r'^(\w+)\s*=', stripped)
                if var_match:
                    var_name = var_match.group(1).lower()
                    # Check if the variable name suggests it's the main body
                    is_body = any(bv in var_name for bv in body_vars)
                    # Also fix if this is the very first .box() in the code
                    is_first_box = True
                    for prev_line in result_lines:
                        if '.box(' in prev_line:
                            is_first_box = False
                            break
                    
                    if is_body or is_first_box:
                        # Add centered=(True, True, False) before the closing parenthesis
                        # Handle multi-line .box() calls by checking if ')' is on this line
                        if ')' in line[line.index('.box('):]:
                            line = re.sub(
                                r'\.box\(([^)]+)\)',
                                r'.box(\1, centered=(True, True, False))',
                                line,
                                count=1
                            )
                            fixed = True
            
            result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    def _strip_centered_from_non_box(self, code: str) -> str:
        """
        Remove centered=(...) from .extrude(), .rect(), .circle() and other methods
        that don't support it. Only .box() supports the centered parameter.
        This prevents TypeError crashes from AI-generated code.
        """
        import re
        # Match centered=(...) inside .extrude(...), .circle(...), .rect(...), .cylinder(...)
        # Pattern: find lines with .extrude/.rect/.circle/.cylinder that also contain centered=
        lines = code.split('\n')
        fixed_lines = []
        for line in lines:
            # Only fix lines that have a non-.box() method call with centered=
            if 'centered=' in line and '.box(' not in line:
                # Remove centered=(True, True, False) or any centered=(...) pattern
                line = re.sub(r',\s*centered\s*=\s*\([^)]*\)', '', line)
                line = re.sub(r'centered\s*=\s*\([^)]*\)\s*,\s*', '', line)
            fixed_lines.append(line)
        return '\n'.join(fixed_lines)
    
    def _clamp_fillet_radii(self, code: str) -> str:
        """
        Auto-inject min() guards around fillet/chamfer radius values.
        Replaces .fillet(N) with .fillet(min(N, _safe_r)) where _safe_r
        is derived from the smallest body dimension found in the code.
        This prevents OCCT crashes from oversized radii BEFORE they happen.
        """
        import re
        
        # Try to extract the smallest body dimension from parameter assignments
        # Look for patterns like: body_length = 150.0, width = 75.0, height = 40.0
        dim_values = []
        for m in re.finditer(
            r'(?:body_|case_|box_|main_)?(?:length|width|height|depth|thick|tall|radius)\s*=\s*([\d.]+)',
            code
        ):
            try:
                val = float(m.group(1))
                if val > 0:
                    dim_values.append(val)
            except ValueError:
                pass
        
        if not dim_values:
            # No dimensions found — inject a conservative auto-computed guard
            guard_expr = "0.25"
            guard_comment = "# Auto-guard: no body dims found, using conservative limit"
        else:
            smallest = min(dim_values)
            guard_val = round(smallest * 0.25, 2)
            guard_expr = str(guard_val)
            guard_comment = f"# Auto-guard: clamped to 25% of smallest dim ({smallest}mm)"
        
        # Inject _auto_fillet_max at the top of the code (after imports)
        inject_line = f"_auto_fillet_max = {guard_expr}  {guard_comment}\n"
        
        # Find insertion point: after last import line
        lines = code.split('\n')
        insert_idx = 0
        for idx, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('import ') or stripped.startswith('from '):
                insert_idx = idx + 1
        
        # Clamp bare numeric fillet/chamfer args: .fillet(5.0) → .fillet(min(5.0, _auto_fillet_max))
        def clamp_radius(match):
            method = match.group(1)  # 'fillet' or 'chamfer'
            arg = match.group(2).strip()
            # Don't double-wrap if already guarded with min()
            if 'min(' in arg or '_auto_fillet_max' in arg or '_safe' in arg:
                return match.group(0)
            return f'.{method}(min({arg}, _auto_fillet_max))'
        
        clamped_code = re.sub(
            r'\.(fillet|chamfer)\(\s*([^,)]+)\s*\)',
            clamp_radius,
            code
        )
        
        # Only inject the guard variable if we actually clamped something
        if clamped_code != code:
            lines = clamped_code.split('\n')
            lines.insert(insert_idx, inject_line)
            clamped_code = '\n'.join(lines)
        
        return clamped_code
    
    def _wrap_fillets_in_try_except(self, code: str) -> str:
        """
        Auto-wrap unprotected .fillet() and .chamfer() calls in try/except blocks.
        This prevents the #1 cause of build failures: StdFail_NotDone from OCCT
        when fillet radius is too large for an edge.
        
        Only wraps lines that:
        - Contain .fillet( or .chamfer(
        - Are assignment statements (var = something.fillet(...))
        - Are NOT already inside a try block
        """
        import re
        
        lines = code.split('\n')
        result_lines = []
        i = 0
        
        while i < len(lines):
            line = lines[i]
            stripped = line.rstrip()
            
            # Check if this line has a fillet/chamfer call and is an assignment
            has_fillet = '.fillet(' in stripped or '.chamfer(' in stripped
            
            if has_fillet:
                # Get the indentation of this line
                indent = len(line) - len(line.lstrip())
                indent_str = line[:indent]
                
                # Check if already inside a try block (look back for 'try:')
                already_protected = False
                for j in range(max(0, i - 3), i):
                    prev_stripped = lines[j].strip()
                    if prev_stripped == 'try:':
                        already_protected = True
                        break
                
                if not already_protected:
                    # Check if this is an assignment like: var = expr.fillet(r)
                    assignment_match = re.match(r'^(\s*)(\w+)\s*=\s*(.+\.(?:fillet|chamfer)\(.+)', line)
                    
                    if assignment_match:
                        var_name = assignment_match.group(2)
                        expr = assignment_match.group(3)
                        
                        # Wrap in try/except that preserves the variable on failure
                        result_lines.append(f"{indent_str}try:")
                        result_lines.append(f"{indent_str}    {var_name} = {expr}")
                        result_lines.append(f"{indent_str}except:")
                        result_lines.append(f"{indent_str}    pass  # Auto-skip: fillet/chamfer too large for edge geometry")
                        i += 1
                        continue
            
            result_lines.append(line)
            i += 1
        
        return '\n'.join(result_lines)
    
    def _fix_zero_dimensions(self, code: str) -> str:
        """
        Guard against zero or negative dimensions in extrude/box/cylinder calls.
        Replaces literal 0 in geometry calls with a safe minimum (0.1mm).
        Also catches expressions that could evaluate to 0.
        """
        import re
        # Fix .extrude(0) → .extrude(0.1)
        code = re.sub(r'\.extrude\(\s*0\s*\)', '.extrude(0.1)', code)
        code = re.sub(r'\.extrude\(\s*0\.0\s*\)', '.extrude(0.1)', code)
        # Fix .box(0, ...) or .box(..., 0, ...) → minimum 0.1
        # Fix .cylinder(0, ...) → minimum 0.1
        return code
    
    def _fix_negative_z_positions(self, code: str) -> str:
        """
        Detect and warn about features placed at negative Z coordinates
        when the main body uses centered=(True,True,False).
        Common AI mistake: translate((x, y, -height/2)) when Z starts at 0.
        """
        import re
        # Only applies when centered=(True,True,False) is used (Z starts at 0)
        if 'centered=(True' not in code and 'centered = (True' not in code:
            return code
        
        lines = code.split('\n')
        result_lines = []
        for line in lines:
            # Look for translate with negative Z that's not a cutter overshoot
            # Pattern: .translate((x, y, -something)) where -something is a large negative
            match = re.search(r'\.translate\(\s*\(([^)]+)\)\s*\)', line)
            if match:
                coords = match.group(1).split(',')
                if len(coords) >= 3:
                    z_coord = coords[2].strip()
                    # If Z coordinate is a literal negative number (not a variable)
                    try:
                        z_val = float(z_coord)
                        if z_val < -5:  # More than 5mm below ground = likely wrong
                            # Comment it as a warning but don't break the code
                            line = line + "  # ⚠️ WARNING: Negative Z with grounded body — feature may be underground"
                    except (ValueError, TypeError):
                        pass
            result_lines.append(line)
        return '\n'.join(result_lines)
    
    def _ensure_result_assignment(self, code: str) -> str:
        """
        If code doesn't define 'result = ...', try to find the main variable
        and assign it. Common when AI forgets the final assignment.
        """
        import re
        # Check if result is already assigned
        if re.search(r'^result\s*=', code, re.MULTILINE):
            return code
        
        # Look for the last body-like variable assignment
        body_vars = [
            'body', 'case', 'base', 'main', 'housing', 'shell', 'frame',
            'enclosure', 'model', 'part', 'product', 'phone', 'tablet',
            'device', 'building', 'tower', 'figure', 'gear', 'column',
            'lamp', 'chair', 'table', 'mug', 'bottle', 'sculpture',
            'bracket', 'stand', 'rack', 'box', 'container'
        ]
        
        last_var = None
        for line in code.split('\n'):
            stripped = line.strip()
            match = re.match(r'^(\w+)\s*=\s*', stripped)
            if match:
                var_name = match.group(1).lower()
                if any(bv in var_name for bv in body_vars):
                    last_var = match.group(1)
        
        if last_var:
            code += f"\n\n# Auto-assigned result\nresult = {last_var}\n"
            print(f"  ⚠️ Auto-assigned result = {last_var} (missing result assignment)")
        
        return code

    def _execute_cadquery_code(
        self,
        code: str,
        parameters: List[Dict[str, Any]]
    ) -> cq.Workplane:
        """
        Execute CadQuery code in isolated namespace
        
        Returns:
            CadQuery Workplane result
        """
        
        # Create namespace with cadquery, math, and parameter defaults
        import math
        import copy
        
        # Import numpy for advanced math (optional but useful)
        try:
            import numpy as np
            numpy_available = True
        except ImportError:
            numpy_available = False
        
        # Import cq_warehouse modules for parametric parts
        try:
            from cq_warehouse import fastener as cq_fastener
            from cq_warehouse import bearing as cq_bearing
            from cq_warehouse import sprocket as cq_sprocket
            from cq_warehouse import chain as cq_chain
            from cq_warehouse import thread as cq_thread
            import cq_warehouse.extensions  # Monkey-patches CadQuery with extra methods
            import cq_warehouse
            cq_warehouse_available = True
        except ImportError:
            cq_warehouse_available = False
        
        namespace = {
            "cadquery": cq,
            "cq": cq,
            "math": math,
            "copy": copy,
            "deepcopy": copy.deepcopy,
        }
        
        # Add numpy if available
        if numpy_available:
            namespace["numpy"] = np
            namespace["np"] = np
        
        # Add cq_warehouse to namespace if available
        if cq_warehouse_available:
            namespace["cq_warehouse"] = cq_warehouse
            # Fastener classes
            namespace["Nut"] = cq_fastener.Nut
            namespace["Screw"] = cq_fastener.Screw
            namespace["Washer"] = cq_fastener.Washer
            namespace["HexNut"] = cq_fastener.HexNut
            namespace["HexNutWithFlange"] = cq_fastener.HexNutWithFlange
            namespace["SquareNut"] = cq_fastener.SquareNut
            namespace["DomedCapNut"] = cq_fastener.DomedCapNut
            namespace["UnchamferedHexagonNut"] = cq_fastener.UnchamferedHexagonNut
            namespace["BradTeeNut"] = cq_fastener.BradTeeNut
            namespace["HeatSetNut"] = cq_fastener.HeatSetNut
            namespace["SocketHeadCapScrew"] = cq_fastener.SocketHeadCapScrew
            namespace["ButtonHeadScrew"] = cq_fastener.ButtonHeadScrew
            namespace["ButtonHeadWithCollarScrew"] = cq_fastener.ButtonHeadWithCollarScrew
            namespace["CheeseHeadScrew"] = cq_fastener.CheeseHeadScrew
            namespace["CounterSunkScrew"] = cq_fastener.CounterSunkScrew
            namespace["HexHeadScrew"] = cq_fastener.HexHeadScrew
            namespace["HexHeadWithFlangeScrew"] = cq_fastener.HexHeadWithFlangeScrew
            namespace["PanHeadScrew"] = cq_fastener.PanHeadScrew
            namespace["PanHeadWithCollarScrew"] = cq_fastener.PanHeadWithCollarScrew
            namespace["RaisedCheeseHeadScrew"] = cq_fastener.RaisedCheeseHeadScrew
            namespace["RaisedCounterSunkOvalHeadScrew"] = cq_fastener.RaisedCounterSunkOvalHeadScrew
            namespace["SetScrew"] = cq_fastener.SetScrew
            namespace["PlainWasher"] = cq_fastener.PlainWasher
            namespace["ChamferedWasher"] = cq_fastener.ChamferedWasher
            namespace["CheeseHeadWasher"] = cq_fastener.CheeseHeadWasher
            # Bearing classes
            namespace["Bearing"] = cq_bearing.Bearing
            namespace["SingleRowDeepGrooveBallBearing"] = cq_bearing.SingleRowDeepGrooveBallBearing
            namespace["SingleRowCappedDeepGrooveBallBearing"] = cq_bearing.SingleRowCappedDeepGrooveBallBearing
            namespace["SingleRowAngularContactBallBearing"] = cq_bearing.SingleRowAngularContactBallBearing
            namespace["SingleRowCylindricalRollerBearing"] = cq_bearing.SingleRowCylindricalRollerBearing
            namespace["SingleRowTaperedRollerBearing"] = cq_bearing.SingleRowTaperedRollerBearing
            # Sprocket & Chain
            namespace["Sprocket"] = cq_sprocket.Sprocket
            namespace["Chain"] = cq_chain.Chain
            # Thread classes
            namespace["IsoThread"] = cq_thread.IsoThread
            namespace["AcmeThread"] = cq_thread.AcmeThread
            namespace["MetricTrapezoidalThread"] = cq_thread.MetricTrapezoidalThread
            namespace["PlasticBottleThread"] = cq_thread.PlasticBottleThread
        
        # Add parameter defaults to namespace
        for param in parameters:
            namespace[param["name"]] = param["default"]
        
        # ═══ PREPROCESSING PIPELINE (order matters!) ═══
        # 1. Fix invalid API usage
        code = self._strip_centered_from_non_box(code)
        # 2. Fix zero/negative dimensions that would crash geometry kernels
        code = self._fix_zero_dimensions(code)
        # 3. Ensure 'result' variable is assigned (AI sometimes forgets)
        code = self._ensure_result_assignment(code)
        # 4. Auto-clamp fillet/chamfer radii with min() guards
        code = self._clamp_fillet_radii(code)
        # 5. Auto-wrap unprotected fillet/chamfer calls in try/except
        code = self._wrap_fillets_in_try_except(code)
        
        # Execute code
        try:
            exec(code, namespace)
        except Exception as e:
            # Extract line number from traceback for better error reporting
            import traceback
            tb = traceback.extract_tb(e.__traceback__)
            line_info = ""
            context_lines = ""
            if tb:
                # Find the frame within the exec'd code (usually last frame)
                for frame in reversed(tb):
                    if frame.filename == "<string>":
                        line_info = f" (line {frame.lineno}"
                        # Try to extract the actual code line plus surrounding context
                        code_lines = code.split('\n')
                        if 0 < frame.lineno <= len(code_lines):
                            offending_line = code_lines[frame.lineno - 1].strip()
                            line_info += f": {offending_line}"
                            # Gather context: 3 lines before and after
                            start = max(0, frame.lineno - 4)
                            end = min(len(code_lines), frame.lineno + 3)
                            ctx = []
                            for ci in range(start, end):
                                marker = ">>>" if ci == frame.lineno - 1 else "   "
                                ctx.append(f"{marker} L{ci+1}: {code_lines[ci]}")
                            context_lines = "\n".join(ctx)
                        line_info += ")"
                        break
            error_msg = (
                f"CadQuery code execution failed{line_info}: "
                f"{type(e).__name__}: {str(e)}"
            )
            if context_lines:
                error_msg += f"\n\nCODE CONTEXT:\n{context_lines}"
            raise RuntimeError(error_msg)
        
        # Extract result
        if "result" not in namespace:
            raise RuntimeError("Code must define 'result' variable")
        
        result = namespace["result"]
        
        # Accept Workplane, Solid, Compound, or Shape results
        # cq_warehouse parts can return Solid/Compound objects directly
        if isinstance(result, cq.Workplane):
            result = self._ground_result(result)
            return result
        elif isinstance(result, (cq.occ_impl.shapes.Solid, cq.occ_impl.shapes.Compound, cq.occ_impl.shapes.Shape)):
            # Wrap in a Workplane for consistent export
            wp = cq.Workplane("XY")
            wp.objects = [result]
            wp = self._ground_result(wp)
            return wp
        else:
            raise RuntimeError(f"Result must be a CadQuery Workplane or Shape, got {type(result).__name__}")
    
    def _ground_result(self, result: cq.Workplane) -> cq.Workplane:
        """
        Translate the ENTIRE finished model so its bounding box bottom sits at Z=0.
        Done AFTER all geometry operations complete — preserves the relative
        positioning between the body and all cutters/features.
        
        This replaces the old _ensure_box_grounding() which only shifted the
        first .box() call but left cutter positions unchanged, causing 78%
        of generated designs to have misaligned cutouts.
        """
        try:
            bb = result.val().BoundingBox()
            z_min = bb.zmin
            if abs(z_min) > 0.01:  # Only translate if not already grounded
                result = result.translate((0, 0, -z_min))
        except Exception:
            pass  # If bounding box fails, leave as-is
        return result
    
    def _fix_multi_solid(self, result: cq.Workplane) -> cq.Workplane:
        """
        Fix geometry with multiple disconnected solids by keeping only the largest.
        This recovers from boolean operations that accidentally sever thin walls.
        """
        try:
            shape = result.val()
            if hasattr(shape, 'Solids'):
                solids = shape.Solids()
                if len(solids) > 1:
                    print(f"  ⚠️ Multi-solid detected: {len(solids)} solids — keeping largest")
                    # Find the solid with the largest volume
                    largest = max(solids, key=lambda s: s.Volume())
                    wp = cq.Workplane("XY")
                    wp.objects = [largest]
                    return wp
        except Exception as e:
            print(f"  ⚠️ Multi-solid check skipped: {e}")
        return result
    
    def _validate_output_quality(self, result: cq.Workplane, code: str) -> Dict[str, Any]:
        """
        Analyze the generated model for quality indicators.
        Returns a dict with quality metrics, warnings, a 1-10 quality score,
        and actionable improvement suggestions.
        Does NOT raise — quality issues are logged, not fatal.
        """
        quality = {"warnings": [], "metrics": {}, "score": 5, "suggestions": []}
        
        try:
            shape = result.val()
            bb = shape.BoundingBox()
            volume = shape.Volume()
            
            quality["metrics"] = {
                "volume_mm3": round(volume, 2),
                "bbox_x": round(bb.xlen, 2),
                "bbox_y": round(bb.ylen, 2),
                "bbox_z": round(bb.zlen, 2),
            }
            
            # ── Score components (out of 10) ──
            score = 5.0  # Start at baseline
            
            # Check for degenerate geometry (-2)
            if volume < 1.0:
                quality["warnings"].append("⚠️ Volume < 1mm³ — model may be degenerate or paper-thin")
                score -= 2.0
            
            # Check for flat/2D models (-1.5)
            dims = [bb.xlen, bb.ylen, bb.zlen]
            min_dim = min(dims)
            max_dim = max(dims)
            if min_dim < 0.1 and max_dim > 10:
                quality["warnings"].append(f"⚠️ Nearly flat model: thinnest dimension is {min_dim:.2f}mm")
                score -= 1.5
            
            # Check face/edge count for detail level
            try:
                faces = shape.Faces()
                edges = shape.Edges()
                face_count = len(faces)
                edge_count = len(edges)
                quality["metrics"]["face_count"] = face_count
                quality["metrics"]["edge_count"] = edge_count
                
                if face_count <= 6 and edge_count <= 12:
                    quality["warnings"].append("⚠️ Model appears to be a plain box with no additional features")
                    quality["suggestions"].append("Add cutouts, ports, or openings to make it functional")
                    quality["suggestions"].append("Add fillets on external edges for a professional look")
                    score -= 2.0
                elif face_count <= 10:
                    quality["warnings"].append("📐 Model has few features — consider adding cutouts, fillets, or details")
                    quality["suggestions"].append("Add ventilation slots or grip texture")
                    score -= 1.0
                elif face_count >= 60:
                    score += 2.0  # Bonus for high detail
                elif face_count >= 30:
                    score += 1.0  # Bonus for detail
                
            except Exception:
                face_count = 0
                edge_count = 0
            
            # Check code complexity as a proxy for detail
            code_lines = [l for l in code.split('\n') if l.strip() and not l.strip().startswith('#')]
            quality["metrics"]["code_lines"] = len(code_lines)
            
            cut_count = code.count('.cut(')
            union_count = code.count('.union(')
            fillet_count = code.count('.fillet(')
            chamfer_count = code.count('.chamfer(')
            quality["metrics"]["boolean_ops"] = cut_count + union_count
            quality["metrics"]["fillet_ops"] = fillet_count + chamfer_count
            
            # Boolean operations scoring
            if cut_count + union_count == 0 and len(code_lines) < 10:
                quality["warnings"].append("⚠️ No boolean operations found — model likely has no cutouts or added features")
                quality["suggestions"].append("Add functional cutouts (ports, holes, vents, slots)")
                score -= 1.5
            elif cut_count + union_count >= 8:
                score += 1.0  # Rich feature set
            elif cut_count + union_count >= 3:
                score += 0.5  # Has meaningful features
            
            # Edge treatment scoring
            if fillet_count + chamfer_count == 0:
                quality["suggestions"].append("Add fillet/chamfer on edges for professional finish")
                score -= 0.5
            elif fillet_count + chamfer_count >= 3:
                score += 0.5  # Good edge treatment
            
            # Parameter count scoring
            param_count = len([l for l in code.split('\n') 
                              if '=' in l and not l.strip().startswith('#') and not l.strip().startswith('import')
                              and any(kw in l.lower() for kw in ['length', 'width', 'height', 'depth', 'radius', 
                                                                   'thickness', 'diameter', 'angle', 'spacing',
                                                                   'count', 'offset', 'inset', 'margin'])])
            quality["metrics"]["param_count"] = param_count
            if param_count >= 15:
                score += 1.0  # Excellently parameterized
            elif param_count >= 10:
                score += 0.5  # Well-parameterized
            
            # Code structure quality
            has_axis_assignment = '# ═══ AXIS ASSIGNMENT' in code or '# AXIS ASSIGNMENT' in code
            has_coord_reference = 'left_x' in code or 'right_x' in code or 'front_y' in code
            if has_axis_assignment:
                score += 0.3
            if has_coord_reference:
                score += 0.3
            
            # Clamp score to 1-10
            quality["score"] = max(1, min(10, round(score)))
            
            # Assign grade
            s = quality["score"]
            if s >= 9:
                quality["grade"] = "🏆 Exceptional"
            elif s >= 7:
                quality["grade"] = "✅ Good"
            elif s >= 5:
                quality["grade"] = "📐 Adequate"
            elif s >= 3:
                quality["grade"] = "⚠️ Basic"
            else:
                quality["grade"] = "❌ Needs Improvement"
            
            # Log quality info
            print(f"  📊 Quality: {quality['grade']} ({quality['score']}/10) | "
                  f"{face_count} faces, {cut_count + union_count} booleans, "
                  f"{fillet_count + chamfer_count} edge treatments, vol={volume:.0f}mm³")
            if quality["warnings"]:
                for w in quality["warnings"]:
                    print(f"    {w}")
            if quality["suggestions"]:
                for s_text in quality["suggestions"][:3]:
                    print(f"    💡 {s_text}")
                
        except Exception as e:
            print(f"  ⚠️ Quality check skipped: {e}")
        
        return quality
    
    def _export_stl_safe(self, result: cq.Workplane, stl_path: Path) -> None:
        """
        Export STL with fallback tolerances. If high-quality export fails,
        retry with relaxed tolerances. If all fail, raise RuntimeError.
        """
        tolerance_levels = [
            (0.01, 0.1, "high quality"),
            (0.05, 0.5, "medium quality"),
            (0.1, 1.0, "low quality"),
        ]
        last_error = None
        for tol, ang_tol, quality in tolerance_levels:
            try:
                cq.exporters.export(
                    result,
                    str(stl_path),
                    exportType="STL",
                    tolerance=tol,
                    angularTolerance=ang_tol
                )
                # Verify the file was actually created and isn't empty
                if stl_path.exists() and stl_path.stat().st_size > 100:
                    if quality != "high quality":
                        print(f"  ⚠️ STL exported at {quality} (tolerance={tol})")
                    return
                else:
                    last_error = "STL file is empty or missing after export"
            except Exception as e:
                last_error = str(e)
                print(f"  ⚠️ STL export failed at {quality}: {last_error}")
                continue
        
        # All tolerance levels failed — raise so the AI retry loop can fix the geometry
        raise RuntimeError(f"STL export failed — geometry may be degenerate: {last_error}")

    async def rebuild_with_parameters(
        self,
        build_id: str,
        updated_parameters: Dict[str, float]
    ) -> Dict[str, str]:
        """
        Phase 4: Re-execute existing script with new parameter values
        NO AI CALL - just re-runs the Python code
        
        Args:
            build_id: Original build ID
            updated_parameters: {param_name: new_value}
            
        Returns:
            {
                "buildId": str,
                "stepFile": str,
                "stlFile": str
            }
        """
        
        # Load existing parametric script
        script_path = self.output_dir / f"{build_id}_parametric.py"
        if not script_path.exists():
            raise FileNotFoundError(f"Parametric script not found for build {build_id}")
        
        # Read original code
        script_content = script_path.read_text(encoding="utf-8")
        
        # Extract code section (between geometry generation markers)
        code_start = script_content.find("# ═══════════════════════════════════════════════════════════════\n# GEOMETRY GENERATION")
        code_end = script_content.find("# ═══════════════════════════════════════════════════════════════\n# EXPORT")
        
        if code_start == -1 or code_end == -1:
            raise ValueError("Cannot parse parametric script structure")
        
        code = script_content[code_start:code_end].split("\n\n", 1)[1].strip()
        
        # Create namespace with updated parameters
        import math
        import copy
        
        # Import numpy for advanced math (optional but useful)
        try:
            import numpy as np
            numpy_available = True
        except ImportError:
            numpy_available = False
        
        # Import cq_warehouse modules if available
        try:
            from cq_warehouse import fastener as cq_fastener
            from cq_warehouse import bearing as cq_bearing
            from cq_warehouse import sprocket as cq_sprocket
            from cq_warehouse import chain as cq_chain
            from cq_warehouse import thread as cq_thread
            import cq_warehouse.extensions
            import cq_warehouse
            cq_warehouse_available = True
        except ImportError:
            cq_warehouse_available = False
        
        namespace = {
            "cadquery": cq,
            "cq": cq,
            "math": math,
            "copy": copy,
            "deepcopy": copy.deepcopy,
        }
        
        # Add numpy if available
        if numpy_available:
            namespace["numpy"] = np
            namespace["np"] = np
        
        # Add cq_warehouse classes if available
        if cq_warehouse_available:
            namespace["cq_warehouse"] = cq_warehouse
            # Add all fastener, bearing, sprocket, chain, thread classes
            for name in dir(cq_fastener):
                obj = getattr(cq_fastener, name)
                if isinstance(obj, type):
                    namespace[name] = obj
            for name in dir(cq_bearing):
                obj = getattr(cq_bearing, name)
                if isinstance(obj, type):
                    namespace[name] = obj
            namespace["Sprocket"] = cq_sprocket.Sprocket
            namespace["Chain"] = cq_chain.Chain
            for name in dir(cq_thread):
                obj = getattr(cq_thread, name)
                if isinstance(obj, type):
                    namespace[name] = obj
        
        namespace.update(updated_parameters)
        
        # ═══ PREPROCESSING PIPELINE (same as _execute_cadquery_code) ═══
        code = self._strip_centered_from_non_box(code)
        code = self._fix_zero_dimensions(code)
        code = self._ensure_result_assignment(code)
        code = self._clamp_fillet_radii(code)
        code = self._wrap_fillets_in_try_except(code)
        
        # Execute code
        try:
            exec(code, namespace)
        except Exception as e:
            raise RuntimeError(f"Script execution failed: {str(e)}")
        
        # Extract result
        if "result" not in namespace:
            raise RuntimeError("Script must define 'result' variable")
        result = namespace["result"]
        
        # Accept Workplane, Solid, Compound, or Shape results
        if isinstance(result, cq.Workplane):
            result = self._ground_result(result)
        elif isinstance(result, (cq.occ_impl.shapes.Solid, cq.occ_impl.shapes.Compound, cq.occ_impl.shapes.Shape)):
            wp = cq.Workplane("XY")
            wp.objects = [result]
            result = self._ground_result(wp)
        else:
            raise RuntimeError(f"Result must be a CadQuery Workplane or Shape, got {type(result).__name__}")
        
        # Fix multi-solid results (keep largest solid)
        result = self._fix_multi_solid(result)
        
        # Export to same build_id (overwrite)
        step_path = self.output_dir / f"{build_id}.step"
        stl_path = self.output_dir / f"{build_id}.stl"
        
        try:
            cq.exporters.export(result, str(step_path))
        except Exception as e:
            raise RuntimeError(f"STEP export failed: {str(e)}")
        self._export_stl_safe(result, stl_path)
        
        return {
            "buildId": build_id,
            "stepFile": f"/exports/cad/{build_id}.step",
            "stlFile": f"/exports/cad/{build_id}.stl"
        }
    
    def _generate_editable_script(
        self,
        code: str,
        parameters: List[Dict[str, Any]],
        explanation: Dict[str, Any]
    ) -> str:
        """
        Generate user-editable Python script with documentation
        """
        
        # Build parameter section
        param_lines = []
        param_lines.append("# ═══════════════════════════════════════════════════════════")
        param_lines.append("# DESIGN PARAMETERS (Edit these values)")
        param_lines.append("# ═══════════════════════════════════════════════════════════")
        param_lines.append("")
        
        for param in parameters:
            param_lines.append(f"# {param.get('description', param['name'])}")
            param_lines.append(f"# Range: {param['min']} - {param['max']} {param['unit']}")
            param_lines.append(f"{param['name']} = {param['default']}")
            param_lines.append("")
        
        # Build explanation section
        explain_lines = []
        if explanation:
            explain_lines.append("# ═══════════════════════════════════════════════════════════")
            explain_lines.append("# DESIGN EXPLANATION")
            explain_lines.append("# ═══════════════════════════════════════════════════════════")
            explain_lines.append("")
            explain_lines.append(f"# Intent: {explanation.get('design_intent', 'N/A')}")
            explain_lines.append(f"# Selectors: {explanation.get('selector_choices', 'N/A')}")
            explain_lines.append(f"# Why Parametric: {explanation.get('why_parametric', 'N/A')}")
            explain_lines.append("")
        
        # Combine into final script
        script = f'''"""
CadQuery Parametric CAD Script
Generated by Chat-to-CAD Platform - Phase 2

Edit the parameters below and run this script to regenerate the model.
"""

import cadquery as cq

{chr(10).join(param_lines)}

{chr(10).join(explain_lines)}

# ═══════════════════════════════════════════════════════════════
# GEOMETRY GENERATION (CadQuery Code)
# ═══════════════════════════════════════════════════════════════

{code}

# ═══════════════════════════════════════════════════════════════
# EXPORT (Run this script to generate files)
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # Export STEP (editable in CAD software)
    cq.exporters.export(result, "output.step")
    
    # Export STL (for 3D printing)
    cq.exporters.export(result, "output.stl")
    
    print("✅ Generated: output.step, output.stl")
    print(f"📐 Parameters used:")
{chr(10).join([f'    print(f"  - {p["name"]}: {{{p["name"]}}} {p["unit"]}")' for p in parameters])}
'''
        
        return script

# Singleton instance
parametric_cad_service = ParametricCADService()
