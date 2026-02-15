"""Test that the completeness analyzer flags frame-only drones and passes complete drones."""
import sys
sys.path.insert(0, 'Backend')
from services.claude_service import ClaudeService

# Create a minimal instance for testing (no API key needed for analyze_code_completeness)
class TestClaude:
    pass

cs = TestClaude()
cs.__class__ = ClaudeService
cs.analyze_code_completeness = ClaudeService.analyze_code_completeness.__get__(cs, ClaudeService)
cs._extract_user_feature_keywords = ClaudeService._extract_user_feature_keywords.__get__(cs, ClaudeService)

# BAD drone: frame-only (flat plate + arms + motor mount holes — no motors/props/canopy/legs)
bad_frame_only = '''
import cadquery as cq
# Central body plate
body = cq.Workplane("XY").box(120, 120, 4, centered=(True,True,False))
body = body.edges("|Z").fillet(10)
# Arms
arm_length = 150
arm_width = 20
arm_thickness = 4
for angle in [45, 135, 225, 315]:
    arm = cq.Workplane("XY").box(arm_length, arm_width, arm_thickness)
    import math
    dx = arm_length/2 * math.cos(math.radians(angle))
    dy = arm_length/2 * math.sin(math.radians(angle))
    body = body.union(arm.translate((dx, dy, 0)))
# Motor mount holes on arm tips
for angle in [45, 135, 225, 315]:
    dx = arm_length * math.cos(math.radians(angle))
    dy = arm_length * math.sin(math.radians(angle))
    hole = cq.Workplane("XY").cylinder(10, 12)
    body = body.cut(hole.translate((dx, dy, 0)))
# Battery bay cutout
battery = cq.Workplane("XY").box(60, 40, 8)
body = body.cut(battery.translate((0, 0, -2)))
# Camera mount hole
cam_hole = cq.Workplane("XY").cylinder(10, 8)
body = body.cut(cam_hole.translate((50, 0, -2)))
result = body
'''

# GOOD drone: complete assembly with motors, propellers, canopy, landing gear
good_complete_drone = '''
import cadquery as cq
import math
# Parameters
frame_size = 120
arm_length = 150
arm_width = 20
plate_thickness = 4
motor_height = 15
motor_r = 14
prop_r = 65
prop_thickness = 2
canopy_r = 45
leg_height = 40
leg_r = 4

# Central body plates (top + bottom)
body = cq.Workplane("XY").box(frame_size, frame_size, plate_thickness, centered=(True,True,False))
top_plate = cq.Workplane("XY").box(frame_size, frame_size, plate_thickness)
body = body.union(top_plate.translate((0, 0, 20)))
body = body.edges("|Z").fillet(8)

# Arms
for angle in [45, 135, 225, 315]:
    arm = cq.Workplane("XY").box(arm_length, arm_width, plate_thickness)
    dx = arm_length/2 * math.cos(math.radians(angle))
    dy = arm_length/2 * math.sin(math.radians(angle))
    body = body.union(arm.translate((dx, dy, 0)))

# Motors (cylindrical motor_body on arm tips)
for angle in [45, 135, 225, 315]:
    dx = arm_length * math.cos(math.radians(angle))
    dy = arm_length * math.sin(math.radians(angle))
    motor_body = cq.Workplane("XY").cylinder(motor_height, motor_r)
    body = body.union(motor_body.translate((dx, dy, plate_thickness + motor_height/2)))

# Propellers (thin discs on top of motors)
for angle in [45, 135, 225, 315]:
    dx = arm_length * math.cos(math.radians(angle))
    dy = arm_length * math.sin(math.radians(angle))
    propeller = cq.Workplane("XY").cylinder(prop_thickness, prop_r)
    body = body.union(propeller.translate((dx, dy, plate_thickness + motor_height + prop_thickness/2)))

# Canopy (half sphere dome over center)
canopy = cq.Workplane("XY").sphere(canopy_r)
canopy = canopy.cut(cq.Workplane("XY").box(999,999,999).translate((0,0,-499.5)))
body = body.union(canopy.translate((0, 0, 24)))

# Landing gear legs
for x, y in [(50, 50), (-50, 50), (50, -50), (-50, -50)]:
    landing_leg = cq.Workplane("XY").cylinder(leg_height, leg_r)
    body = body.union(landing_leg.translate((x, y, -leg_height/2)))

# Camera mount bracket
camera = cq.Workplane("XY").box(30, 30, 10)
body = body.union(camera.translate((50, 0, -10)))

result = body
'''

# PARTIAL drone: has motors and legs but missing propellers and canopy
partial_drone = '''
import cadquery as cq
import math
arm_length = 150
motor_height = 15
motor_r = 14
body = cq.Workplane("XY").box(120, 120, 4, centered=(True,True,False))
# Arms
for angle in [45, 135, 225, 315]:
    arm = cq.Workplane("XY").box(arm_length, 20, 4)
    dx = arm_length/2 * math.cos(math.radians(angle))
    dy = arm_length/2 * math.sin(math.radians(angle))
    body = body.union(arm.translate((dx, dy, 0)))
# Motors (cylinder bodies - NOT just holes)
for angle in [45, 135, 225, 315]:
    dx = arm_length * math.cos(math.radians(angle))
    dy = arm_length * math.sin(math.radians(angle))
    motor_body = cq.Workplane("XY").cylinder(motor_height, motor_r)
    body = body.union(motor_body.translate((dx, dy, 4 + motor_height/2)))
# Landing legs
for x, y in [(50, 50), (-50, 50), (50, -50), (-50, -50)]:
    landing_leg = cq.Workplane("XY").cylinder(40, 4)
    body = body.union(landing_leg.translate((x, y, -20)))
# Battery area
battery = cq.Workplane("XY").box(60, 40, 8)
body = body.cut(battery.translate((0, 0, -2)))
result = body
'''

print("=" * 60)
print("TEST 1: Frame-only drone (should flag 4 missing components)")
print("=" * 60)
result1 = cs.analyze_code_completeness(bad_frame_only, "build me a drone quadcopter")
missing1 = result1.get('missing_features', [])
motor_missing = any('MISSING MOTORS' in m for m in missing1)
prop_missing = any('MISSING PROPELLERS' in m for m in missing1)
canopy_missing = any('MISSING CANOPY' in m for m in missing1)
landing_missing = any('MISSING LANDING GEAR' in m for m in missing1)
print(f"  is_complete: {result1['is_complete']}")
print(f"  product_type: {result1.get('product_type')}")
print(f"  MOTORS flagged: {motor_missing}")
print(f"  PROPELLERS flagged: {prop_missing}")
print(f"  CANOPY flagged: {canopy_missing}")
print(f"  LANDING GEAR flagged: {landing_missing}")
for m in missing1:
    if 'MISSING' in m:
        print(f"  → {m[:100]}")

print()
print("=" * 60)
print("TEST 2: Complete drone (should pass all drone checks)")
print("=" * 60)
result2 = cs.analyze_code_completeness(good_complete_drone, "build me a drone quadcopter")
missing2 = result2.get('missing_features', [])
drone_missing = [m for m in missing2 if 'MISSING' in m and any(w in m for w in ['MOTOR', 'PROPELLER', 'CANOPY', 'LANDING'])]
print(f"  is_complete: {result2['is_complete']}")
print(f"  product_type: {result2.get('product_type')}")
print(f"  Drone-specific missing: {len(drone_missing)}")
if drone_missing:
    for m in drone_missing:
        print(f"  → {m[:100]}")

print()
print("=" * 60)
print("TEST 3: Partial drone (has motors+legs, missing props+canopy)")
print("=" * 60)
result3 = cs.analyze_code_completeness(partial_drone, "build me a drone quadcopter")
missing3 = result3.get('missing_features', [])
motor_ok = not any('MISSING MOTORS' in m for m in missing3)
leg_ok = not any('MISSING LANDING GEAR' in m for m in missing3)
prop_flagged = any('MISSING PROPELLERS' in m for m in missing3)
canopy_flagged = any('MISSING CANOPY' in m for m in missing3)
print(f"  is_complete: {result3['is_complete']}")
print(f"  Motors NOT flagged (has motor_body): {motor_ok}")
print(f"  Landing NOT flagged (has landing_leg): {leg_ok}")
print(f"  Propellers flagged (missing): {prop_flagged}")
print(f"  Canopy flagged (missing): {canopy_flagged}")

print()
print("=" * 60)
print("ASSERTIONS")
print("=" * 60)
passed = 0
total = 10

def check(name, cond):
    global passed
    if cond:
        passed += 1
        print(f"  PASS: {name}")
    else:
        print(f"  FAIL: {name}")

check("BAD drone flagged as incomplete", not result1['is_complete'])
check("BAD drone has MISSING MOTORS", motor_missing)
check("BAD drone has MISSING PROPELLERS", prop_missing)
check("BAD drone has MISSING CANOPY", canopy_missing)
check("GOOD drone has NO drone-specific missing", len(drone_missing) == 0)
check("PARTIAL drone: motors NOT flagged", motor_ok)
check("PARTIAL drone: propellers ARE flagged", prop_flagged)
check("PARTIAL drone: canopy IS flagged", canopy_flagged)

# TEST 4: Verify enhancement body_note triggers for drone missing features
print()
print("=" * 60)
print("TEST 4: Enhancement body_note gate triggers for drones")
print("=" * 60)
# The has_body_issues gate must match drone-specific MISSING features
has_body_issues = any("BODY SHAPE:" in f or "PROFILE QUALITY:" in f or "SWEEP PATH:" in f 
                     or "BRICK-LIKE CUTOUTS:" in f
                     or "MISSING MOTORS:" in f or "MISSING PROPELLERS:" in f
                     or "MISSING CANOPY:" in f or "MISSING LANDING GEAR:" in f
                     for f in result1.get("missing_features", []))
print(f"  BAD drone has_body_issues: {has_body_issues}")
check("BAD drone triggers body_note gate", has_body_issues)

# Complete drone should NOT trigger body_note
has_body_issues_good = any("BODY SHAPE:" in f or "PROFILE QUALITY:" in f or "SWEEP PATH:" in f 
                          or "BRICK-LIKE CUTOUTS:" in f
                          or "MISSING MOTORS:" in f or "MISSING PROPELLERS:" in f
                          or "MISSING CANOPY:" in f or "MISSING LANDING GEAR:" in f
                          for f in result2.get("missing_features", []))
print(f"  GOOD drone has_body_issues: {has_body_issues_good}")
check("GOOD drone does NOT trigger body_note gate", not has_body_issues_good)

print()
print(f"=== {passed}/{total} tests passed ===")
if passed == total:
    print("ALL TESTS PASSED")
else:
    print(f"FAILED: {total - passed} tests")
    sys.exit(1)
