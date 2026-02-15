"""Test all drone types are discoverable via keyword search."""
import sys
sys.path.insert(0, 'Backend')
from services.product_library import search_products, PRODUCTS

# Count drone entries
drone_entries = [p for p in PRODUCTS if p['category'] == 'Drones & RC']
print(f'Total drone entries: {len(drone_entries)}')
for e in drone_entries:
    print(f'  - {e["name"]} (keywords: {e["keywords"][:3]}...)')

# Test keyword matching for each type
test_prompts = [
    ('build a racing drone', 'Racing FPV'),
    ('make a DJI camera drone', 'Photography'),
    ('hexacopter heavy lift drone', 'Hexacopter'),
    ('octocopter cinema drone', 'Octocopter'),
    ('tricopter y frame', 'Tricopter'),
    ('fixed wing vtol survey drone', 'Fixed-Wing'),
    ('mini tiny whoop drone', 'Mini Indoor'),
    ('delivery cargo drone', 'Delivery'),
    ('underwater rov drone', 'Underwater'),
    ('agricultural spray drone', 'Agricultural'),
    ('build me a drone', 'Racing FPV'),  # default quadcopter
    ('fpv quadcopter', 'Racing FPV'),
]

errors = []
print('\nKeyword matching tests:')
for prompt, expected_substr in test_prompts:
    results = search_products(prompt)
    if results:
        name = results[0]["name"]
        if expected_substr in name:
            print(f'  ✓ "{prompt}" -> {name}')
        else:
            print(f'  ⚠ "{prompt}" -> {name} (expected "{expected_substr}" in name)')
            errors.append(f'{prompt} matched {name} instead of {expected_substr}')
    else:
        print(f'  ✗ "{prompt}" -> NO MATCH!')
        errors.append(f'{prompt} had no match')

# Test completeness analyzer with different drone types
from services.claude_service import ClaudeService
cs = ClaudeService.__new__(ClaudeService)

# Simulate analyzer: quad with missing motors
test_code_frame_only = """
import cadquery as cq
import math
arm_len = 100
body = cq.Workplane("XY").circle(40).extrude(3)
for angle in [45, 135, 225, 315]:
    arm = cq.Workplane("XY").box(arm_len, 15, 5)
    body = body.union(arm)
result = body
"""
result = cs.analyze_code_completeness(test_code_frame_only, "build a quadcopter drone")
missing = result.get('missing_features', [])
print(f'\nCompleteness: frame-only quad -> {len(missing)} missing features')
for m in missing:
    print(f'  - {m[:80]}...' if len(m) > 80 else f'  - {m}')

# Test hexacopter detection
result_hex = cs.analyze_code_completeness(test_code_frame_only, "hexacopter heavy lift drone")
missing_hex = result_hex.get('missing_features', [])
hex_has_6 = any('6' in m for m in missing_hex)
print(f'\nCompleteness: hexacopter -> {len(missing_hex)} issues, mentions "6": {hex_has_6}')
for m in missing_hex:
    print(f'  - {m[:80]}...' if len(m) > 80 else f'  - {m}')

# Test underwater ROV detection
rov_code = """
import cadquery as cq
frame = cq.Workplane("XY").box(350, 250, 180)
result = frame
"""
result_rov = cs.analyze_code_completeness(rov_code, "underwater rov drone")
missing_rov = result_rov.get('missing_features', [])
rov_has_thruster = any('thruster' in m.lower() for m in missing_rov)
print(f'\nCompleteness: ROV frame-only -> {len(missing_rov)} issues, mentions "thruster": {rov_has_thruster}')
for m in missing_rov:
    print(f'  - {m[:80]}...' if len(m) > 80 else f'  - {m}')

# Test delivery drone detection
result_del = cs.analyze_code_completeness(test_code_frame_only, "delivery cargo drone")
missing_del = result_del.get('missing_features', [])
del_has_cargo = any('cargo' in m.lower() for m in missing_del)
print(f'\nCompleteness: delivery frame-only -> {len(missing_del)} issues, mentions "cargo": {del_has_cargo}')

# Test agriculture drone detection
result_agri = cs.analyze_code_completeness(test_code_frame_only, "agricultural spray drone")
missing_agri = result_agri.get('missing_features', [])
agri_has_spray = any('spray' in m.lower() for m in missing_agri)
print(f'\nCompleteness: agri frame-only -> {len(missing_agri)} issues, mentions "spray": {agri_has_spray}')

if errors:
    print(f'\n❌ {len(errors)} error(s)')
    for e in errors:
        print(f'  • {e}')
else:
    print(f'\n✅ All {len(test_prompts)} keyword matches passed!')
