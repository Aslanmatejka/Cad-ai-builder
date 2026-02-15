"""Quick test: verify anti-brick shape quality checks work"""
import sys
sys.path.insert(0, 'Backend')
from services.claude_service import ClaudeService
from services.parametric_cad_service import ParametricCADService

cs = ClaudeService()
pcs = ParametricCADService()

# Test 1: Phone case with ALL box cutouts (brick design)
print("=" * 60)
print("TEST 1: Phone case with all-box cutouts (should flag)")
print("=" * 60)
brick_code = """import cadquery as cq
body = cq.Workplane("XY").box(73, 10, 150, centered=(True, True, False))
usb = cq.Workplane("XY").box(12, 8, 6).translate((0, 0, 0))
body = body.cut(usb)
camera = cq.Workplane("XY").box(20, 6, 25).translate((0, 5, 120))
body = body.cut(camera)
speaker = cq.Workplane("XY").box(15, 6, 3).translate((10, 0, 0))
body = body.cut(speaker)
volume_button = cq.Workplane("XY").box(6, 6, 20).translate((-36, 0, 100))
body = body.cut(volume_button)
power_button = cq.Workplane("XY").box(6, 6, 12).translate((36, 0, 90))
body = body.cut(power_button)
result = body
"""
a = cs.analyze_code_completeness(brick_code, "iphone 16 case")
print(f"  Type: {a['product_type']}")
print(f"  Cuts: {a['cut_count']}, Round cutters: {a['round_cutter_count']}")
print(f"  Complete: {a['is_complete']}")
for f in a['missing_features']:
    print(f"  MISSING: {f}")

# Test 2: Phone case with proper rounded cutouts (good design)
print("\n" + "=" * 60)
print("TEST 2: Phone case with proper shapes (should pass shape check)")
print("=" * 60)
good_code = """import cadquery as cq
body = cq.Workplane("XY").box(73, 10, 150, centered=(True, True, False))
# USB-C port (rounded slot)
usb = cq.Workplane("XZ").slot2D(12, 4).extrude(6)
usb = usb.translate((0, 0, 0))
body = body.cut(usb)
# Camera cutout (rounded rect)
camera = cq.Workplane("XY").box(20, 6, 25).translate((0, 5, 120))
body = body.cut(camera)
# Speaker grille (cylinder holes)
for i in range(6):
    dot = cq.Workplane("XY").cylinder(6, 0.8).translate((-8 + i*3, 0, 0))
    body = body.cut(dot)
# Volume button (rounded slot) 
vol = cq.Workplane("YZ").slot2D(20, 3).extrude(6)
vol = vol.translate((-36, 0, 100))
body = body.cut(vol)
# Power button (cylinder)
pwr = cq.Workplane("YZ").cylinder(6, 4).translate((36, 0, 90))
body = body.cut(pwr)
try:
    body = body.edges('|Z').fillet(2.0)
except:
    pass
result = body
"""
a2 = cs.analyze_code_completeness(good_code, "iphone 16 case")
print(f"  Type: {a2['product_type']}")
print(f"  Cuts: {a2['cut_count']}, Round cutters: {a2['round_cutter_count']}")
print(f"  Complete: {a2['is_complete']}")
for f in a2['missing_features']:
    print(f"  MISSING: {f}")

# Test 3: Fillet clamping at 25%
print("\n" + "=" * 60)
print("TEST 3: Fillet clamping (should use 25% not 15%)")
print("=" * 60)
fillet_code = """import cadquery as cq
body_depth = 10.5
body = cq.Workplane("XY").box(73, 10.5, 150, centered=(True, True, False))
body = body.edges('|Z').fillet(5.0)
result = body
"""
clamped = pcs._clamp_fillet_radii(fillet_code)
for line in clamped.split('\n'):
    if '_auto_fillet_max' in line:
        print(f"  Guard line: {line.strip()}")
        # 25% of 10.5 = 2.625
        assert '2.62' in line or '2.63' in line, f"Expected ~2.625 but got: {line}"
        print("  PASS: 25% clamping applied correctly")
        break

# Test 4: Drinkware with box body (should flag - needs revolve+spline)
print("\n" + "=" * 60)
print("TEST 4: Mug with box body (should flag BODY SHAPE)")
print("=" * 60)
box_mug_code = """import cadquery as cq
body = cq.Workplane("XY").box(80, 80, 100, centered=(True, True, False))
cavity = cq.Workplane("XY").box(70, 70, 90).translate((0, 0, 10))
body = body.cut(cavity)
handle = cq.Workplane("XY").box(15, 30, 60).translate((45, 0, 30))
body = body.union(handle)
try:
    body = body.edges('|Z').fillet(3.0)
except:
    pass
result = body
"""
a4 = cs.analyze_code_completeness(box_mug_code, "coffee mug")
print(f"  Type: {a4['product_type']}")
print(f"  Revolve count: {a4.get('revolve_count', 0)}, Spline count: {a4.get('spline_count', 0)}")
print(f"  Main body is box: {a4.get('main_body_is_box', 'unknown')}")
print(f"  Complete: {a4['is_complete']}")
has_body_shape_flag = any("BODY SHAPE" in f for f in a4['missing_features'])
print(f"  Has BODY SHAPE flag: {has_body_shape_flag}")
for f in a4['missing_features']:
    if 'BODY SHAPE' in f or 'PROFILE' in f:
        print(f"  → {f}")
assert has_body_shape_flag, "Mug with box body should be flagged for BODY SHAPE issue"
print("  PASS: Box-mug correctly flagged")

# Test 5: Mug with revolve+spline body (should NOT flag body shape)
print("\n" + "=" * 60)
print("TEST 5: Mug with revolve+spline body (should pass body check)")
print("=" * 60)
good_mug_code = """import cadquery as cq
import math
profile = (cq.Workplane("XZ")
    .moveTo(0, 0)
    .lineTo(35, 0)
    .spline([(36, 5), (38, 50), (40, 85)])
    .tangentArcPoint((38, 95))
    .lineTo(0, 95)
    .close()
    .revolve(360, (0,0,0), (0,1,0)))
inner = (cq.Workplane("XZ")
    .moveTo(0, 5)
    .lineTo(32, 5)
    .spline([(33, 10), (35, 50), (37, 85)])
    .tangentArcPoint((35, 93))
    .lineTo(0, 93)
    .close()
    .revolve(360, (0,0,0), (0,1,0)))
body = profile.cut(inner)
handle_path = (cq.Workplane("XY")
    .moveTo(40, 75)
    .threePointArc((55, 50), (40, 25)))
handle = cq.Workplane("YZ").circle(5).sweep(handle_path)
body = body.union(handle)
try:
    body = body.edges().fillet(0.5)
except:
    pass
result = body
"""
a5 = cs.analyze_code_completeness(good_mug_code, "coffee mug")
print(f"  Type: {a5['product_type']}")
print(f"  Revolve: {a5.get('revolve_count', 0)}, Spline: {a5.get('spline_count', 0)}, Sweep: {a5.get('sweep_count', 0)}")
print(f"  Advanced techniques: {a5.get('advanced_technique_count', 0)}")
has_body_shape_flag_5 = any("BODY SHAPE" in f for f in a5['missing_features'])
has_profile_flag_5 = any("PROFILE" in f for f in a5['missing_features'])
print(f"  Has BODY SHAPE flag: {has_body_shape_flag_5}")
print(f"  Has PROFILE QUALITY flag: {has_profile_flag_5}")
assert not has_body_shape_flag_5, "Good mug with revolve+spline should NOT be flagged for body shape"
assert not has_profile_flag_5, "Good mug with spline profile should NOT be flagged for profile quality"
print("  PASS: Revolve+spline mug passes body quality check")

# Test 6: Travel mug with revolve but all-lineTo profile (should flag profile quality)
print("\n" + "=" * 60)
print("TEST 6: Revolve mug with all-lineTo (should flag PROFILE QUALITY)")
print("=" * 60)
lineto_mug_code = """import cadquery as cq
import math
profile = (cq.Workplane("XZ")
    .moveTo(0, 0)
    .lineTo(30, 0)
    .lineTo(30, 2)
    .lineTo(28, 4)
    .lineTo(35, 80)
    .lineTo(35, 90)
    .lineTo(33, 92)
    .lineTo(0, 92)
    .close()
    .revolve(360, (0,0,0), (0,1,0)))
inner = (cq.Workplane("XZ")
    .moveTo(0, 3)
    .lineTo(27, 3)
    .lineTo(32, 87)
    .lineTo(0, 87)
    .close()
    .revolve(360, (0,0,0), (0,1,0)))
body = profile.cut(inner)
handle_path = (cq.Workplane("XZ")
    .moveTo(35, 25)
    .lineTo(50, 35)
    .lineTo(50, 65)
    .lineTo(35, 75))
handle = cq.Workplane("XY").circle(5).sweep(handle_path)
body = body.union(handle)
try:
    body = body.fillet(0.5)
except:
    pass
result = body
"""
a6 = cs.analyze_code_completeness(lineto_mug_code, "coffee mug")
print(f"  Type: {a6['product_type']}")
print(f"  Revolve: {a6.get('revolve_count', 0)}, Spline: {a6.get('spline_count', 0)}")
print(f"  LineTo count: {a6.get('lineto_count', 'N/A')}")
has_profile_flag = any("PROFILE QUALITY" in f for f in a6['missing_features'])
has_sweep_flag = any("SWEEP PATH" in f for f in a6['missing_features'])
print(f"  Has PROFILE QUALITY flag: {has_profile_flag}")
print(f"  Has SWEEP PATH flag: {has_sweep_flag}")
for f in a6['missing_features']:
    if 'PROFILE' in f or 'SWEEP' in f:
        print(f"  → {f}")
assert has_profile_flag, "All-lineTo mug should be flagged for profile quality"
assert has_sweep_flag, "Straight-line sweep handle should be flagged"
print("  PASS: LineTo-only profile correctly flagged")

print("\n" + "=" * 60)
print("ALL TESTS PASSED")
print("=" * 60)
