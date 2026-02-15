"""Test that the completeness analyzer flags brick-like phone cases."""
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

# BAD phone case design (all box cutters, like 98d3f4c4)
bad_code = '''
import cadquery as cq
body = cq.Workplane("XY").box(73.6, 10.5, 149.6, centered=(True,True,False))
body = body.edges("|Z").fillet(6)
body = body.faces("<Y").shell(-1.5)
# USB-C port - box (BAD)
usb = cq.Workplane("XY").box(12, 5, 4)
body = body.cut(usb.translate((0, 0, 0)))
# Camera cutout - box (BAD)
cam = cq.Workplane("XY").box(30, 5, 35)
body = body.cut(cam.translate((10, 5, 120)))
# Speaker grille - boxes (BAD)
for i in range(4):
    speaker = cq.Workplane("XY").box(2, 5, 1.5)
    body = body.cut(speaker.translate((-6+i*3, 0, 0)))
# Volume button - box (BAD)
vol = cq.Workplane("XY").box(5, 15, 3)
body = body.cut(vol.translate((-37, 0, 95)))
# Power button - box (BAD)
pwr = cq.Workplane("XY").box(5, 10, 3)
body = body.cut(pwr.translate((37, 0, 90)))
result = body
'''

# GOOD phone case design (slot2D + cylinder cutters)
good_code = '''
import cadquery as cq
body = cq.Workplane("XY").box(73.6, 10.5, 149.6, centered=(True,True,False))
body = body.edges("|Z").fillet(6)
body = body.faces("<Y").shell(-1.5)
# USB-C port - slot2D (GOOD)
usb = cq.Workplane("XZ").slot2D(12, 4).extrude(5)
body = body.cut(usb.translate((0, 0, -1)))
# Camera cutout - rect + fillet (GOOD)
cam = cq.Workplane("XZ").rect(30, 35).extrude(5)
body = body.cut(cam.translate((10, 3, 120)))
# Speaker grille - cylinders (GOOD)
for i in range(6):
    speaker = cq.Workplane("XY").cylinder(5, 0.8)
    body = body.cut(speaker.translate((-4+i*2, 0, 0)))
# Volume button - slot2D (GOOD)
vol = cq.Workplane("YZ").slot2D(15, 3).extrude(5)
body = body.cut(vol.translate((-37, 0, 95)))
# Power button - slot2D (GOOD)
pwr = cq.Workplane("YZ").slot2D(10, 3).extrude(5)
body = body.cut(pwr.translate((37, 0, 90)))
# Microphone - cylinder (GOOD)
mic = cq.Workplane("XY").cylinder(5, 0.5)
body = body.cut(mic.translate((15, 0, 0)))
result = body
'''

prompt = 'Make me an iPhone 16 Pro case'

print('=== BAD phone case (all box cutters) ===')
bad_result = cs.analyze_code_completeness(bad_code, prompt)
print(f'  is_complete: {bad_result["is_complete"]}')
print(f'  box_cutter_count: {bad_result["box_cutter_count"]}')
print(f'  round_cutter_count: {bad_result["round_cutter_count"]}')
print(f'  missing_features:')
for f in bad_result['missing_features']:
    print(f'    - {f}')

print()
print('=== GOOD phone case (slot2D + cylinder cutters) ===')
good_result = cs.analyze_code_completeness(good_code, prompt)
print(f'  is_complete: {good_result["is_complete"]}')
print(f'  box_cutter_count: {good_result["box_cutter_count"]}')
print(f'  round_cutter_count: {good_result["round_cutter_count"]}')
print(f'  missing_features:')
for f in good_result['missing_features']:
    print(f'    - {f}')
if not good_result['missing_features']:
    print('    (none - PASS)')

# Test assertions
print()
print('=== ASSERTIONS ===')
tests_passed = 0
tests_total = 0

# BAD case should be flagged
tests_total += 1
assert not bad_result['is_complete'], "BAD case should NOT be complete"
tests_passed += 1
print(f'  PASS: BAD case flagged as incomplete')

tests_total += 1
brick_flagged = any('BRICK-LIKE CUTOUTS' in f for f in bad_result['missing_features'])
assert brick_flagged, "BAD case should have BRICK-LIKE CUTOUTS warning"
tests_passed += 1
print(f'  PASS: BAD case has BRICK-LIKE CUTOUTS warning')

tests_total += 1
assert bad_result['box_cutter_count'] > 0, "BAD case should have box cutters"
tests_passed += 1
print(f'  PASS: BAD case box_cutter_count={bad_result["box_cutter_count"]}')

# GOOD case should pass (or at least not have brick warning)
tests_total += 1
brick_flagged_good = any('BRICK-LIKE CUTOUTS' in f for f in good_result['missing_features'])
assert not brick_flagged_good, "GOOD case should NOT have BRICK-LIKE CUTOUTS warning"
tests_passed += 1
print(f'  PASS: GOOD case has no BRICK-LIKE CUTOUTS warning')

tests_total += 1
assert good_result['round_cutter_count'] > good_result['box_cutter_count'], \
    "GOOD case should have more round cutters than box cutters"
tests_passed += 1
print(f'  PASS: GOOD case round_cutter_count={good_result["round_cutter_count"]} > box_cutter_count={good_result["box_cutter_count"]}')

print(f'\n=== {tests_passed}/{tests_total} tests passed ===')
