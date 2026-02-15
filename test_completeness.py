"""
Test all product-type completeness checks in the analyzer.
Verifies that each new product type is correctly detected and
that missing features are properly flagged.
"""
import sys
sys.path.insert(0, 'Backend')

from services.claude_service import ClaudeService

svc = ClaudeService()

# ── Helpers ──────────────────────────────────────────────────────────
def check(prompt, expected_type, expected_missing_keywords, label=None):
    """
    Run analyzer with MINIMAL code (empty stub) and verify:
     - product_type matches expected_type
     - at least one missing_feature contains each keyword
    """
    # Minimal code that won't trigger any product feature keywords  
    stub_code = """
import cadquery as cq
result = cq.Workplane("XY").box(100, 100, 50)
"""
    analysis = svc.analyze_code_completeness(stub_code, prompt)
    name = label or f"{expected_type}({prompt[:30]}...)"
    
    errors = []
    if analysis["product_type"] != expected_type:
        errors.append(f"  type: got '{analysis['product_type']}', expected '{expected_type}'")
    
    missing_text = " ".join(analysis.get("missing_features", [])).lower()
    for kw in expected_missing_keywords:
        if kw.lower() not in missing_text:
            errors.append(f"  missing keyword '{kw}' not found in: {analysis['missing_features'][:3]}...")
    
    if errors:
        print(f"  ✗ {name}")
        for e in errors:
            print(f"    {e}")
        return False
    else:
        print(f"  ✓ {name}")
        return True


def check_complete(prompt, code, expected_type, label=None):
    """
    Run analyzer and verify it's COMPLETE (no missing features)
    when all required features are present in code.
    """
    analysis = svc.analyze_code_completeness(code, prompt)
    name = label or f"{expected_type}(complete)"
    
    errors = []
    if analysis["product_type"] != expected_type:
        errors.append(f"  type: got '{analysis['product_type']}', expected '{expected_type}'")

    # Allow generic checks (cut_count, fillet) to remain — only check product-specific
    product_specific_missing = [f for f in analysis.get("missing_features", [])
                                 if "cutout operations" not in f 
                                 and "edge fillets" not in f
                                 and "lines of code" not in f
                                 and "ALL cutouts are rectangular" not in f
                                 and "user requested" not in f]
    if product_specific_missing:
        errors.append(f"  unexpected product-specific missing: {product_specific_missing}")
    
    if errors:
        print(f"  ✗ {name}")
        for e in errors:
            print(f"    {e}")
        return False
    else:
        print(f"  ✓ {name}")
        return True


# ── Tests ─────────────────────────────────────────────────────────────
passed = 0
failed = 0

def t(result):
    global passed, failed
    if result:
        passed += 1
    else:
        failed += 1

print("=" * 60)
print("PRODUCT TYPE DETECTION TESTS")
print("=" * 60)

# Previously-existing types
t(check("build a phone case for iphone 16", "phone_case", ["usb", "camera", "speaker", "button"]))
t(check("design a house with a garden", "building", ["window", "door", "roof"]))
t(check("medieval castle model", "castle", ["tower", "gate", "crenel"]))
t(check("build a drone", "drone", ["motor", "propeller"]))
t(check("raspberry pi enclosure", "electronics_enclosure", ["vent", "port", "boss"]))
t(check("ps5 game controller", "game_controller", ["button", "thumbstick", "grip"]))
t(check("wooden desk with drawers", "furniture", ["feet"]))
t(check("ceramic coffee mug", "drinkware", ["handle", "rim"]))
t(check("storage container with lid", "container", ["handle", "feet"]))

print()
print("=" * 60)
print("NEW PRODUCT TYPE DETECTION TESTS")
print("=" * 60)

# Laptop
t(check("macbook pro laptop", "laptop", ["screen", "keyboard", "trackpad", "hinge", "port", "vent"], "laptop"))
# Tablet
t(check("ipad tablet device", "tablet", ["screen", "camera", "button", "port", "speaker"], "tablet"))
# Smartphone
t(check("design a smartphone like pixel phone", "smartphone", ["screen", "camera", "button", "port", "speaker"], "smartphone"))
# Headphones
t(check("over-ear headphones noise cancelling", "audio_headphones", ["earcup", "headband", "pad", "adjust"], "headphones_over_ear"))
# Earbuds
t(check("wireless earbuds like airpods", "audio_headphones", ["stem", "tip", "driver"], "earbuds"))
# Speaker
t(check("bluetooth speaker portable", "audio_speaker", ["driver", "grille", "port", "feet", "button"], "speaker"))
# Smartwatch
t(check("apple watch smartwatch", "wearable_watch", ["face", "band", "crown", "back"], "smartwatch"))
# Mouse 
t(check("ergonomic wireless mouse", "peripheral_mouse", ["button", "scroll", "sensor", "feet"], "mouse"))
# Keyboard
t(check("mechanical keyboard gaming", "peripheral_keyboard", ["key", "case", "feet", "port"], "keyboard"))
# Desk accessory
t(check("pen holder desk organizer", "desk_accessory", ["compartment", "feet"], "desk_accessory"))
# Tools
t(check("adjustable wrench hand tool", "tools", ["handle", "jaw", "texture", "hole"], "wrench"))
# Gear (mechanical)
t(check("spur gear 20 teeth", "mechanical", ["teeth", "bore"], "gear"))
# Clock (home decor)
t(check("wall clock for living room", "home_decor", ["clock face", "clock hands", "wall mounting"], "clock"))
# Mount
t(check("phone mount for car dashboard", "mount", ["grip", "mount", "adjust"], "mount"))
# Automotive
t(check("car bumper replacement automotive", "automotive", ["mount", "fillet", "rib"], "automotive"))
# Fitness
t(check("dumbbell weight training", "fitness", ["grip", "weight", "fillet"], "dumbbell"))
# Sculpture
t(check("marble sculpture bust", "sculpture", ["base", "surface detail", "smooth"], "sculpture"))
# Landmark
t(check("eiffel tower model", "landmark", ["base", "lines", "features"], "landmark"))
# Kitchen
t(check("cast iron frying pan cookware", "kitchen", ["handle", "fillet"], "kitchen_pan"))
# Toy
t(check("lego building brick toy", "toy", ["rounded", "stud", "tube"], "toy_brick"))
# Lamp
t(check("desk lamp modern design", "lamp", ["shade", "base", "socket", "arm", "switch"], "lamp"))
# Sports
t(check("skateboard complete deck", "sports", ["truck", "concave"], "skateboard"))
# Jewelry
t(check("diamond engagement ring", "jewelry", ["revolve", "setting"], "ring"))
# Guitar
t(check("acoustic guitar musical instrument", "instrument", ["body", "neck", "headstock", "tuning", "sound hole", "bridge"], "guitar"))
# Drum
t(check("snare drum percussion", "instrument", ["shell", "head", "rim", "lug"], "drum"))
# Wind instrument
t(check("trumpet brass instrument", "instrument", ["bell", "key", "mouthpiece"], "trumpet"))
# Medical
t(check("test tube rack lab equipment", "medical", ["hole", "base"], "test_tube_rack"))
# Pipe
t(check("brass pipe fitting elbow", "pipe", ["bore", "thread", "chamfer"], "pipe_fitting"))
# 3D printing
t(check("3d print filament spool holder", "3d_printing", ["hole", "fillet"], "3d_printing"))
# Hinge
t(check("metal hinge hardware", "hardware", ["pin", "leaves", "hole"], "hinge"))
# Basketball hoop
t(check("basketball hoop with backboard", "sports", ["rim", "backboard", "net"], "basketball_hoop"))
# Helmet
t(check("cycling helmet protective", "sports", ["shell", "visor", "vent"], "helmet"))

print()
print("=" * 60)
print("BODY SHAPE ENFORCEMENT TESTS")
print("=" * 60)

# Mouse with box body should get flagged
t(check("computer mouse wireless", "peripheral_mouse", ["body shape", "loft"], "mouse_body_shape"))
# Ring should require revolve
t(check("gold wedding ring", "jewelry", ["revolve"], "ring_revolve"))

print()
print("=" * 60)
print("COMPLETE PRODUCT TESTS (should pass with good code)")
print("=" * 60)

# Test that a COMPLETE guitar code passes
guitar_code = """
import cadquery as cq
import math
# Guitar params
body_w = 350; body_d = 100; body_l = 450
neck_w = 50; neck_d = 25; neck_l = 500
# Body using loft between bouts
body = (cq.Workplane("XZ")
    .ellipse(body_w*0.35, body_d*0.4)
    .workplane(offset=body_l*0.4).ellipse(body_w*0.2, body_d*0.3)
    .workplane(offset=body_l*0.6).ellipse(body_w*0.5, body_d*0.45)
    .loft())
# Sound hole
body = body.faces(">Y").workplane().circle(40).cutBlind(-5)
soundhole = body  # alias for soundhole reference
# Neck / fretboard
neck = cq.Workplane("XZ").rect(neck_w, neck_d).extrude(neck_l)
neck = neck.translate((0, 0, body_l))
# Headstock with head scroll
headstock = cq.Workplane("XZ").rect(neck_w*1.5, neck_d*0.8).extrude(80)
headstock = headstock.translate((0, 0, body_l + neck_l))
head = headstock
# Tuning pegs/machine heads
for i in range(6):
    peg = cq.Workplane("XY").cylinder(15, 3)
    tuning = peg.translate((-neck_w*0.5 + i*neck_w/5, 0, body_l + neck_l + 40))
    headstock = headstock.union(tuning)
# Bridge on body face 
bridge = cq.Workplane("XZ").rect(80, 10).extrude(8)
bridge = bridge.translate((0, body_d*0.4, body_l*0.3))
saddle = bridge
# Assembly
result = body.union(neck).union(headstock).union(bridge)
result = result.edges().fillet(1)
"""
t(check_complete("acoustic guitar", guitar_code, "instrument", "guitar_complete"))

# Test that a complete smartwatch code passes
watch_code = """
import cadquery as cq
# Watch case using revolve
case_r = 22; case_h = 11
profile = (cq.Workplane("XZ").moveTo(0, 0)
    .lineTo(case_r, 0)
    .spline([(case_r*1.05, case_h*0.4), (case_r, case_h)])
    .lineTo(0, case_h).close()
    .revolve(360, (0,0,0), (0,1,0)))
# Display/face recess on front
face = case_r
display = case_r * 0.85
case_body = profile.faces(">Z").workplane().circle(display).cutBlind(-1.5)
# Band attachment lugs
lug_w = 10; lug_l = 8; lug_h = 4
lug1 = cq.Workplane("XY").box(lug_w, lug_l, lug_h)
band = lug1  # band attachment
case_body = case_body.union(lug1.translate((0, case_r + lug_l/2, case_h/2)))
case_body = case_body.union(lug1.translate((0, -case_r - lug_l/2, case_h/2)))
# Side crown button
crown_r = 2; crown_l = 5
digital_crown = cq.Workplane("YZ").cylinder(crown_l, crown_r)
case_body = case_body.union(digital_crown.translate((case_r + crown_l/2, 0, case_h*0.6)))
# Back sensor cover
back = cq.Workplane("XY").circle(case_r*0.6).extrude(1)
sensor = back
case_body = case_body.union(back.translate((0, 0, -1)))
result = case_body.edges().fillet(0.5)
"""
t(check_complete("apple watch smartwatch", watch_code, "wearable_watch", "watch_complete"))

# Test that complete lamp code passes
lamp_code = """
import cadquery as cq
# Base
base_r = 60; base_h = 15
base = cq.Workplane("XY").circle(base_r).extrude(base_h)
base = base.edges(">Z").fillet(5)
# Cable hole in base
cable_hole = cq.Workplane("XY").circle(4).extrude(base_h + 1)
base = base.cut(cable_hole.translate((base_r*0.7, 0, 0)))
# Stem
stem_r = 8; stem_h = 250
stem = cq.Workplane("XY").circle(stem_r).extrude(stem_h)
arm = stem  # arm reference
body = base.union(stem.translate((0, 0, base_h)))
# Switch recess on stem
switch = cq.Workplane("XY").box(10, 5, 15)
body = body.cut(switch.translate((stem_r, 0, base_h + 50)))
# Shade (truncated cone)
shade_bot_r = 80; shade_top_r = 40; shade_h = 100
shade = (cq.Workplane("XY")
    .circle(shade_bot_r).workplane(offset=shade_h).circle(shade_top_r).loft())
diffuser = shade
# Socket recess inside shade
socket_r = 15; socket_h = 30
socket = cq.Workplane("XY").circle(socket_r).extrude(socket_h)
bulb = socket  # bulb socket
lamp_shade = shade.cut(socket.translate((0, 0, shade_h - socket_h)))
body = body.union(lamp_shade.translate((0, 0, base_h + stem_h)))
result = body.edges().fillet(1)
"""
t(check_complete("modern desk lamp", lamp_code, "lamp", "lamp_complete"))


print()
print("=" * 60)
if failed == 0:
    print(f"ALL {passed} TESTS PASSED ✓")
else:
    print(f"RESULTS: {passed} passed, {failed} FAILED")
print("=" * 60)
