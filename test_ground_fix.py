"""
Test that the _ground_result() fix works correctly.
Compares NEW pipeline (post-exec grounding) vs OLD pipeline (pre-exec box grounding).
"""
import sys
sys.path.insert(0, 'Backend')
from services.parametric_cad_service import parametric_cad_service as pcs

# Minimal params to satisfy the interface
params = [{'name': 'test', 'default': 1, 'min': 0, 'max': 2, 'unit': 'mm'}]

# ═══════════════════════════════════════════════════════
# TEST 1: Desk organizer WITHOUT centered=(True,True,False)
# This is the 78% case where AI omits centered.
# OLD: _ensure_box_grounding shifted only the body → cutters misaligned
# NEW: _ground_result translates ENTIRE model after exec → cutters preserved
# ═══════════════════════════════════════════════════════
code_no_centered = """
import cadquery as cq

organizer_width = 250.0
organizer_depth = 150.0
organizer_height = 120.0
wall_thickness = 3.0

inner_width = organizer_width - 2 * wall_thickness
inner_depth = organizer_depth - 2 * wall_thickness

# Body centered at origin (Z from -60 to 60)
outer_body = cq.Workplane("XY").box(organizer_width, organizer_depth, organizer_height)

# Hollow out — cavity centered too, shifted up by wall_thickness
main_cavity = cq.Workplane("XY").box(inner_width, inner_depth, organizer_height - wall_thickness)
main_cavity = main_cavity.translate((0, 0, wall_thickness))
body = outer_body.cut(main_cavity)

# Pen holes from top of body
for i in range(5):
    pen_x = -80 + i * 20
    pen_hole = cq.Workplane("XY").circle(6).extrude(81)
    pen_hole = pen_hole.translate((pen_x, 0, organizer_height/2 - 80))
    body = body.cut(pen_hole)

# Phone slot through side wall
phone_slot = cq.Workplane("XY").box(60, 15, organizer_height * 0.8)
phone_slot = phone_slot.translate((60, inner_depth/2 - 20, 0))
body = body.cut(phone_slot)

result = body
"""

result1 = pcs._execute_cadquery_code(code_no_centered, params)
bb1 = result1.val().BoundingBox()
vol1 = result1.val().Volume()
solid_vol = 250 * 150 * 120

print("=== TEST 1: Desk organizer (no centered) ===")
print(f"  Z range: {bb1.zmin:.2f} to {bb1.zmax:.2f} (height: {bb1.zlen:.1f}mm)")
print(f"  Grounded at Z=0: {abs(bb1.zmin) < 0.02}")
print(f"  Volume ratio: {vol1/solid_vol:.3f} (hollow < 0.3)")
assert abs(bb1.zmin) < 0.02, f"NOT grounded! Z_min = {bb1.zmin}"
assert vol1 / solid_vol < 0.5, f"NOT hollow! ratio = {vol1/solid_vol:.3f}"
print("  ✅ PASS — grounded AND hollow")

# ═══════════════════════════════════════════════════════
# TEST 2: Simulate OLD pipeline bug (centered only on first box)
# ═══════════════════════════════════════════════════════
code_old_bug = code_no_centered.replace(
    'cq.Workplane("XY").box(organizer_width, organizer_depth, organizer_height)',
    'cq.Workplane("XY").box(organizer_width, organizer_depth, organizer_height, centered=(True, True, False))',
    1  # Only first occurrence (simulates old _ensure_box_grounding)
)

result_old = pcs._execute_cadquery_code(code_old_bug, params)
vol_old = result_old.val().Volume()

print("\n=== TEST 2: Simulated OLD bug (only body shifted) ===")
print(f"  Volume ratio: {vol_old/solid_vol:.3f}")
vol_increase = (vol_old - vol1) / vol1 * 100
print(f"  Volume increase over correct: {vol_increase:.1f}%")
if vol_old > vol1 * 1.3:
    print("  ⚠️  CONFIRMED: Old pipeline produced 30%+ more solid material (brick-like!)")
else:
    print("  ℹ️  Difference minimal for this design")

# ═══════════════════════════════════════════════════════
# TEST 3: Revolve body (non-box) also gets grounded
# ═══════════════════════════════════════════════════════
code_revolve = """
import cadquery as cq

body = (cq.Workplane("XZ")
    .moveTo(30, 0)
    .lineTo(35, 0)
    .lineTo(35, 100)
    .lineTo(30, 100)
    .close()
    .revolve(360))

# Cut hole through side
hole = cq.Workplane("XY").circle(5).extrude(40)
hole = hole.translate((0, 0, 50))
body = body.cut(hole)
result = body
"""

result3 = pcs._execute_cadquery_code(code_revolve, params)
bb3 = result3.val().BoundingBox()
print("\n=== TEST 3: Revolve body ===")
print(f"  Z range: {bb3.zmin:.2f} to {bb3.zmax:.2f}")
assert abs(bb3.zmin) < 0.02, f"NOT grounded! Z_min = {bb3.zmin}"
print("  ✅ PASS — revolve grounded at Z=0")

# ═══════════════════════════════════════════════════════
# TEST 4: Code WITH centered=(True,True,False) still works
# ═══════════════════════════════════════════════════════
code_with_centered = """
import cadquery as cq

body = cq.Workplane("XY").box(100, 80, 60, centered=(True, True, False))
cavity = cq.Workplane("XY").box(94, 74, 57, centered=(True, True, False))
cavity = cavity.translate((0, 0, 3))
body = body.cut(cavity)

# Port cutout on side
port = cq.Workplane("XZ").rect(15, 10).extrude(10)
port = port.translate((0, -40, 10))
body = body.cut(port)

result = body
"""

result4 = pcs._execute_cadquery_code(code_with_centered, params)
bb4 = result4.val().BoundingBox()
vol4 = result4.val().Volume()
solid4 = 100 * 80 * 60

print("\n=== TEST 4: Code with centered (AI-written) ===")
print(f"  Z range: {bb4.zmin:.2f} to {bb4.zmax:.2f}")
print(f"  Volume ratio: {vol4/solid4:.3f}")
assert abs(bb4.zmin) < 0.02, f"NOT grounded! Z_min = {bb4.zmin}"
assert vol4 / solid4 < 0.5, f"NOT hollow! ratio = {vol4/solid4:.3f}"
print("  ✅ PASS — grounded AND hollow")

# ═══════════════════════════════════════════════════════
# TEST 5: Pre-existing tests still pass
# ═══════════════════════════════════════════════════════
print("\n=== TEST 5: Preprocessing still works ===")

# Test _strip_centered_from_non_box
test_code = 'shape = cq.Workplane("XY").rect(10, 5).extrude(3, centered=(True, True, False))'
fixed = pcs._strip_centered_from_non_box(test_code)
assert "centered=" not in fixed, "centered= not stripped from extrude!"
print("  ✅ _strip_centered_from_non_box works")

# Test _fix_zero_dimensions
test_code = 'x.extrude(0)'
fixed = pcs._fix_zero_dimensions(test_code)
assert "extrude(0.1)" in fixed, "Zero dim not fixed!"
print("  ✅ _fix_zero_dimensions works")

# Test _ensure_result_assignment
test_code = 'body = cq.Workplane("XY").box(10, 10, 10)'
fixed = pcs._ensure_result_assignment(test_code)
assert "result = body" in fixed, "result not assigned!"
print("  ✅ _ensure_result_assignment works")

print("\n" + "="*50)
print("ALL TESTS PASSED ✅")
print("="*50)
