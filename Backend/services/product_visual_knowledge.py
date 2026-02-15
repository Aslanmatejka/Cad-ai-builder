"""
Product Visual Knowledge — How Products Actually LOOK

Comprehensive visual/structural knowledge that teaches the AI what real products
look like, how they're shaped, what proportions make them recognizable, and how
to build them in CadQuery. This module augments the product library with deep
visual understanding.

Three types of knowledge per product/category:
  1. visual_profile  — What the product looks like from every angle. Shape language,
                        silhouette, cross-sections, surface character, proportions.
  2. build_strategy  — CadQuery-specific construction recipe. Step-by-step approach
                        to building this product in code.
  3. recognition_features — The 3-5 things that make this product instantly recognizable.
                           If these are wrong, the model looks "off". These are non-negotiable.
"""

from typing import Dict, Any, Optional

# ═══════════════════════════════════════════════════════════════════════════════
# CATEGORY-LEVEL VISUAL KNOWLEDGE
# ═══════════════════════════════════════════════════════════════════════════════
# Applies to ALL products in a category. Product-specific overrides below.

CATEGORY_VISUAL_KNOWLEDGE: Dict[str, Dict[str, str]] = {

    "Smartphones": {
        "visual_profile": (
            "OVERALL FORM: Thin rectangular slab with rounded corners — a 'bar' form factor. "
            "Think of a slim chocolate bar with softened edges. "
            "FRONT VIEW: Almost entirely screen — a dark glass rectangle with thin bezels (2-5mm). "
            "Camera cutout (notch/Dynamic Island/punch-hole) at top-center. "
            "SIDE VIEW: Extremely thin profile (~7-9mm), either perfectly flat edges (modern iPhones/Samsung) "
            "or gently curved edges (older models). Buttons appear as subtle bumps on left/right edges. "
            "BACK VIEW: Smooth flat surface with camera module in upper-left corner (island or individual rings). "
            "The camera module is the most visually prominent back feature. "
            "BOTTOM VIEW: USB-C (or Lightning) port centered, speaker grille holes on one or both sides. "
            "TOP VIEW: Clean — maybe just a tiny mic hole. "
            "PROPORTIONS: Length ≈ 2.1× width. Thickness ≈ 1/9 of width. "
            "Corner radius ≈ 7-12mm. The phone should look like it fits comfortably in one hand."
        ),
        "build_strategy": (
            "ORIENTATION: Phone STANDING UPRIGHT — tallest dimension is Z. "
            "  AXIS ASSIGNMENT: "
            "    X axis = phone width (~71mm)    — left-right "
            "    Y axis = phone depth (~8mm)     — front-back (screen on -Y, back on +Y) "
            "    Z axis = phone tall (~147mm)    — up-down (USB-C at Z=0, top at Z=tall) "
            "  .box(phone_width, phone_depth, phone_tall, centered=(True, True, False)) "
            "  Screen/front = -Y face ('<Y'),  Back = +Y face ('>Y'), "
            "  Top = +Z face ('>Z'),  Bottom = -Z face ('<Z'), "
            "  Left = -X face ('<X'),  Right = +X face ('>X'). "
            "STEPS: "
            "1. body = cq.Workplane('XY').box(phone_width, phone_depth, phone_tall, centered=(True,True,False)). "
            "2. Fillet all 4 long VERTICAL edges (|Z) with corner_radius for rounded-rect shape. "
            "3. SCREEN RECESS: Cut on FRONT face (<Y): "
            "   screen = cq.Workplane('XY').box(width - 2*bezel, depth*0.15, tall - 2*bezel) "
            "   screen = screen.translate((0, -depth/2, tall/2)) → cuts into front face. "
            "4. CAMERA ISLAND on BACK face (>Y): "
            "   Position: x ≈ -width/4 (upper-left), z ≈ tall*0.85 (upper area). "
            "5. CAMERA LENSES: Cut circles through the island. "
            "6. BUTTONS on sides — use SLOT2D for pill-shaped cutouts: "
            "   Volume on LEFT (<X): cq.Workplane('YZ').slot2D(btn_h, btn_d).extrude(wall*3).translate((-width/2, 0, tall*0.65)) "
            "   Power on RIGHT (>X): cq.Workplane('YZ').slot2D(btn_h, btn_d).extrude(wall*3).translate((+width/2, 0, tall*0.60)) "
            "7. USB-C on BOTTOM (<Z) at z=0 — use SLOT2D for rounded port: "
            "   usb = cq.Workplane('XZ').slot2D(usb_w, usb_h).extrude(wall*3).translate((0, 0, 0)) "
            "8. SPEAKER GRILLE on BOTTOM (<Z): array of tiny holes near USB-C, offset in X. "
            "9. Fillet/chamfer ALL remaining sharp edges. "
            "10. VERIFY: USB-C at Z=0 (bottom), camera at Z≈tall*0.85 (upper back), volume on -X side."
        ),
        "recognition_features": (
            "1. SCREEN DOMINANCE: The front face is 85-92% screen with thin uniform bezels. "
            "2. CAMERA MODULE: The specific camera layout (triangular triple, vertical dual, individual rings) "
            "   is THE signature identifier of each phone model. "
            "3. THIN PROFILE: Must look impossibly thin — thickness should be ≤ 1/9 of width. "
            "4. EDGE STYLE: Flat edges (modern) vs curved edges (pre-2020) dramatically changes the character. "
            "5. CORNER RADIUS: Uniform rounded corners — NOT sharp, NOT circular. A specific radius."
        ),
        "position_map": (
            "AXIS ASSIGNMENT: X=phone_width, Y=phone_depth, Z=phone_tall (tallest). "
            "FEATURE → FACE → AXIS → POSITION (Z=0 is bottom edge, Z=phone_tall is top edge): "
            "  USB-C port      → BOTTOM (<Z) → z=0, x=0, y=0 (centered on bottom edge) "
            "  Speaker grille   → BOTTOM (<Z) → z=0, x=±15mm, y=0 "
            "  Volume buttons   → LEFT (<X)   → x=-phone_width/2, y=0, z=phone_tall*0.65 "
            "  Power button     → RIGHT (>X)  → x=+phone_width/2, y=0, z=phone_tall*0.60 "
            "  Mute/Action btn  → LEFT (<X)   → x=-phone_width/2, y=0, z=phone_tall*0.80 "
            "  Camera island    → BACK (>Y)   → y=+phone_depth/2, x=-phone_width*0.25, z=phone_tall*0.85 "
            "  Screen recess    → FRONT (<Y)  → y=-phone_depth/2, centered on face "
            "  Mic hole (top)   → TOP (>Z)    → z=phone_tall, x=0, y=0 "
            "  SIM tray         → LEFT (<X)   → x=-phone_width/2, y=0, z=phone_tall*0.40"
        )
    },

    "Phone Cases": {
        "visual_profile": (
            "OVERALL FORM: An open-top shell that is the 'negative' of the phone it protects. "
            "The case is ~2mm larger than the phone in every dimension. "
            "FRONT VIEW: Open rectangle showing the screen — the case forms a frame around it with a slight lip. "
            "BACK VIEW: Smooth surface with a camera cutout hole that exactly matches the phone's camera island. "
            "SIDE VIEW: Shows the wall thickness (~1.5-2mm) and the protective lip rising above the screen surface. "
            "The sides have precise cutouts for buttons (or flexible membrane bumps over buttons). "
            "BOTTOM VIEW: Opening for USB-C/Lightning port and speaker grille access. "
            "FEEL: The case adds ~2mm to each dimension and ~3mm to thickness. Still fits in hand."
        ),
        "build_strategy": (
            "ORIENTATION: Case STANDING UPRIGHT — tallest dimension is Z. "
            "  AXIS ASSIGNMENT: "
            "    X axis = case width (~75mm)      — left-right "
            "    Y axis = case depth (~12mm)      — front-back (screen on -Y, back on +Y) "
            "    Z axis = case tall (~152mm)      — up-down (USB-C at Z=0, top at Z=tall) "
            "  .box(case_width, case_depth, case_tall, centered=(True, True, False)) "
            "  Screen/open side = FRONT (-Y face '<Y'),  Back = +Y face ('>Y'), "
            "  Top = +Z face ('>Z'),  Bottom = -Z face ('<Z'), "
            "  Left = -X face ('<X'),  Right = +X face ('>X'). "
            "STEPS: "
            "1. body = cq.Workplane('XY').box(case_width, case_depth, case_tall, centered=(True,True,False)). "
            "2. Fillet the 4 VERTICAL edges (|Z) for rounded corners. "
            "3. Shell from the FRONT face (<Y) — this is the screen-side opening. "
            "   body = body.faces('<Y').shell(-wall_thickness) "
            "4. CAMERA CUTOUT on BACK face (>Y) — use ROUNDED RECTANGLE: "
            "   cam_cut = cq.Workplane('XZ').rect(cam_w, cam_h).extrude(wall*3) "
            "   cam_cut = cam_cut.edges('|Y').fillet(min(4, min(cam_w,cam_h)*0.15)) "
            "   cam_cut = cam_cut.translate((cam_x, +case_depth/2, case_tall*0.85)) "
            "5. CAMERA LIP: 0.5mm raised ring around camera cutout on >Y face. "
            "6. BUTTON CUTOUTS on sides — use SLOT2D for rounded pill shapes: "
            "   Volume on LEFT (<X): slot2D(btn_len, btn_depth).extrude(wall*3).translate((-case_width/2, 0, case_tall*0.65)) "
            "   Power on RIGHT (>X): slot2D(btn_len, btn_depth).extrude(wall*3).translate((+case_width/2, 0, case_tall*0.60)) "
            "   Mute on LEFT (<X): cylinder(wall*3, mute_r).translate((-case_width/2, 0, case_tall*0.80)) "
            "7. USB-C CUTOUT on BOTTOM (<Z) — use SLOT2D for rounded slot: "
            "   usb_cut = cq.Workplane('XZ').slot2D(usb_w, usb_h).extrude(wall*3).translate((0, 0, 0)) "
            "8. SPEAKER CUTOUT on BOTTOM (<Z): array of CYLINDER holes offset from USB-C toward ±X. "
            "   for i in range(6): hole = cq.Workplane('XY').cylinder(wall*3, 0.8).translate((15+i*3, 0, 0)) "
            "9. Fillet all external edges for comfortable grip. "
            "CUTOUT SHAPE RULES: "
            "  - USB-C port → .slot2D() (rounded stadium/pill shape, NEVER .box()) "
            "  - Buttons → .slot2D() (rounded slots) "
            "  - Speaker grille → array of .cylinder() (round holes) "
            "  - Camera island → .rect() + .fillet() (rounded rectangle) "
            "  - Camera lenses → .cylinder() (perfect circles) "
            "  - Microphone → .cylinder() (tiny circle) "
            "  - A phone case should have ZERO .box() cutters."
        ),
        "recognition_features": (
            "1. OPEN FRONT: The screen side (-Y) is completely open — just a protective lip frame. "
            "2. CAMERA CUTOUT PRECISION: Must exactly match the phone model's camera layout on the BACK (+Y). "
            "3. BUTTON CUTOUTS: Each button gets its own precisely-placed opening on LEFT/RIGHT (±X) sides. "
            "4. PROTECTIVE LIP: Screen lip (1mm) and camera lip (0.5mm) — these are the functional purpose. "
            "5. SNUG FIT: The interior should look like a perfect mold of the phone's exterior."
        ),
        "position_map": (
            "AXIS ASSIGNMENT: X=case_width, Y=case_depth, Z=case_tall (tallest). "
            "FEATURE → FACE → AXIS → POSITION (Z=0 is bottom edge, Z=case_tall is top edge): "
            "  Camera cutout   → BACK (>Y)   → y=+case_depth/2, x=-case_width*0.2, z=case_tall*0.85 "
            "  Camera lip ring → BACK (>Y)   → around camera cutout, 0.5mm raised "
            "  Volume buttons  → LEFT (<X)   → x=-case_width/2, z=case_tall*0.65 "
            "  Power button    → RIGHT (>X)  → x=+case_width/2, z=case_tall*0.60 "
            "  Mute/Action btn → LEFT (<X)   → x=-case_width/2, z=case_tall*0.80 "
            "  USB-C cutout    → BOTTOM (<Z) → z=0, x=0 (centered on bottom edge) "
            "  Speaker holes   → BOTTOM (<Z) → z=0, x=±12mm from center "
            "  Screen opening  → FRONT (<Y)  → entire front face is open (shelled from <Y) "
            "  SIM tray slot   → LEFT (<X)   → x=-case_width/2, z=case_tall*0.40"
        )
    },

    "Tablets": {
        "visual_profile": (
            "OVERALL FORM: Large thin rectangular slab — like a scaled-up phone but proportionally thinner. "
            "Think of a thin cutting board with rounded edges. "
            "FRONT VIEW: Dominated by the screen with thin bezels. Larger bezel than phones (~5-8mm). "
            "SIDE VIEW: Very thin profile (~5-7mm). Flat edges on modern tablets. "
            "Buttons clustered on one short edge (top in portrait). "
            "BACK VIEW: Clean surface with small camera in one corner. Minimal camera bump. "
            "May have a magnetic connector strip (3 dots). "
            "PROPORTIONS: Roughly 4:3 aspect ratio (not as elongated as phones). "
            "The tablet should look like a portable digital canvas."
        ),
        "build_strategy": (
            "ORIENTATION: box(length, width, thickness) — tablet LYING FLAT (screen faces +Z). "
            "  Screen = +Z face ('>Z'), Back = -Z face ('<Z'), "
            "  Top edge = +Y face ('>Y'), Bottom edge = -Y face ('<Y'), "
            "  Left = -X face ('<X'), Right = +X face ('>X'). "
            "STEPS: "
            "1. body = cq.Workplane('XY').box(length, width, thickness) with corner fillets (~10-12mm). "
            "2. SCREEN RECESS on TOP (+Z): cut rounded rect on .faces('>Z') — 0.3mm deep. "
            "3. CAMERA on BACK (-Z): small circle boss on .faces('<Z') in one corner. "
            "4. USB-C on BOTTOM EDGE (<Y) — use SLOT2D for rounded port: "
            "   usb = cq.Workplane('XZ').slot2D(usb_w, usb_h).extrude(wall*3).translate((0, -width/2, 0)) "
            "5. BUTTONS on TOP EDGE (>Y) or RIGHT (+X) — use SLOT2D for pill shapes: "
            "   btn = cq.Workplane('XZ').slot2D(btn_w, btn_h).extrude(wall*3).translate((x, +width/2, 0)) "
            "6. SPEAKER GRILLES: arrays on short edges or corners. "
            "7. Fillet all edges — tablets feel softer/rounder than phones."
        ),
        "recognition_features": (
            "1. LARGE SCREEN: The screen area dominates — it's what makes it a tablet, not a phone. "
            "2. THINNESS: Must look paper-thin relative to its large face area. "
            "3. MINIMAL CAMERA: Unlike phones, tablets have tiny, unobtrusive cameras. "
            "4. LANDSCAPE ORIENTATION: Tablets are often shown and used in landscape. "
            "5. FLAT EDGES: Modern tablets have flat, squared-off edges."
        ),
        "position_map": (
            "FEATURE → FACE → AXIS → POSITION (tablet lying flat, Z=0 bottom, Z=thickness top): "
            "  Screen recess → TOP (>Z) → z=thickness, fills most of the face "
            "  Camera        → BOTTOM (<Z) → z=0, corner position "
            "  USB-C port    → BOTTOM EDGE (<Y) → y=-width/2, x=0 (centered) "
            "  Volume buttons → TOP EDGE (>Y) → y=+width/2, near right side "
            "  Power button  → TOP EDGE (>Y) → y=+width/2, near right side "
            "  Speakers      → SHORT EDGES (±X) → x=±length/2 "
            "  Smart connector → BOTTOM EDGE (<Y) → y=-width/2, centered"
        )
    },

    "Laptops": {
        "visual_profile": (
            "OVERALL FORM: Clamshell — two thin rectangular slabs hinged together along one long edge. "
            "CLOSED: Looks like a thin book or flat briefcase with rounded edges. "
            "OPEN (45-135°): Bottom half has keyboard + trackpad visible; top half is the screen. "
            "The hinge is visible from the back. "
            "BOTTOM HALF (base): Houses keyboard (centered, upper 60%), large trackpad (centered, lower area), "
            "and ports along left/right edges. Rubber feet on the bottom surface. "
            "TOP HALF (display): Screen with thin bezels. Camera notch or hole at top-center. "
            "SIDE VIEW: Wedge-shaped (thinner at front) or uniform thickness. "
            "Ports visible as rectangular cutouts along edges. "
            "PROPORTIONS: Width ≈ 1.4-1.6× depth. Closed thickness ≈ 12-17mm."
        ),
        "build_strategy": (
            "ORIENTATION: box(width, depth, thickness) — laptop CLOSED, lying flat on desk. "
            "  Top surface = +Z face ('>Z'), Bottom/feet = -Z face ('<Z'), "
            "  Front edge (opens here) = -Y face ('<Y'), "
            "  Back/hinge = +Y face ('>Y'), "
            "  Left = -X face ('<X'), Right = +X face ('>X'). "
            "STEPS: "
            "1. base = cq.Workplane('XY').box(width, depth, thickness) with corner fillets (~7-8mm). "
            "2. HINGE GROOVE on BACK edge (>Y): thin cut at y=+depth/2, z ≈ thickness*0.6. "
            "3. KEYBOARD RECESS on TOP (+Z): "
            "   key_recess = box(kb_w, kb_d, 0.5).translate((0, depth*0.1, +thickness/2)) "
            "   → centered, shifted toward back (hinge side). "
            "4. TRACKPAD RECESS on TOP (+Z): "
            "   tp_recess = box(tp_w, tp_d, 0.3).translate((0, -depth*0.2, +thickness/2)) "
            "   → centered, shifted toward front. "
            "5. PORT CUTOUTS on LEFT (<X) and RIGHT (>X) edges — match REAL port shapes: "
            "   USB-A on LEFT: box(wall*3, usb_w, usb_h).translate((-width/2, y, z)) — USB-A IS rectangular "
            "   USB-C on RIGHT: cq.Workplane('YZ').slot2D(usbc_w, usbc_h).extrude(wall*3).translate((+width/2, y, z)) — rounded "
            "   HDMI on LEFT: box(wall*3, hdmi_w, hdmi_h).translate((-width/2, y, z)) — HDMI IS rectangular "
            "6. RUBBER FEET on BOTTOM (<Z): 4 cylinders at corners, z=-thickness/2. "
            "7. For OPEN position: build two slabs, rotate display slab ~110° around back hinge."
        ),
        "recognition_features": (
            "1. CLAMSHELL FORM: Two halves hinged at BACK (+Y) — THE defining laptop shape. "
            "2. KEYBOARD LAYOUT: Full keyboard with distinct key grid visible on TOP (+Z), toward back. "
            "3. LARGE TRACKPAD: Prominent centered trackpad on TOP (+Z), below keyboard toward front. "
            "4. PORT VARIETY: Multiple port shapes on LEFT (<X) and RIGHT (>X) edges. "
            "5. THIN PROFILE: Modern laptops are notably thin — thickness should match specs closely."
        ),
        "position_map": (
            "FEATURE → FACE → AXIS → POSITION (laptop closed, lying flat, Z=0 bottom, Z=thickness top): "
            "  Keyboard    → TOP (>Z) → z=thickness, centered, shifted toward +Y (back) "
            "  Trackpad    → TOP (>Z) → z=thickness, centered, shifted toward -Y (front) "
            "  USB-A ports → LEFT (<X) → x=-width/2, various y positions, z=thickness*0.5 "
            "  USB-C ports → RIGHT (>X) → x=+width/2, various y positions, z=thickness*0.5 "
            "  HDMI        → LEFT (<X) → x=-width/2, y=center area "
            "  Headphone   → LEFT (<X) → x=-width/2, y toward front (-Y) "
            "  Rubber feet → BOTTOM (<Z) → z=0, 4 corners "
            "  Hinge       → BACK (>Y) → y=+depth/2, across the full width"
        )
    },

    "Audio": {
        "visual_profile": (
            "HEADPHONES — OVER-EAR: Two large oval ear cups connected by an arched headband. "
            "Side view: ear cups are thick ovals (~50mm deep). "
            "Front view: headband rises in a smooth arch above the cups. "
            "Arms connect headband to cups — may telescope for adjustment. "
            "EARBUDS: Small organic-shaped pieces designed to fit in the ear canal. "
            "Usually have a stem hanging down. The charging case is a small rounded box "
            "with a hinge — looks like a dental floss container or small jewelry box. "
            "PROPORTIONS (headphones): Headband arc width ≈ 185-200mm. "
            "Ear cups ≈ 80×65mm oval. Overall height when flat ≈ 200mm."
        ),
        "build_strategy": (
            "HEADPHONES: "
            "1. Ear cups: rounded box or lofted oval shape, ~80×65×50mm. "
            "2. Headband: sweep a small cross-section (10×5mm rect) along an arc path. "
            "3. Arms: boxes or cylinders connecting headband to ear cups. "
            "4. Add cushion rings: rounded annular shapes on ear cup faces. "
            "5. Details: buttons, ports, scroll wheels as small cylinder/box cuts. "
            "EARBUDS (case): "
            "1. Rounded box (45×60×22mm) with generous fillets. "
            "2. Shell from one face to create hollow interior. "
            "3. Add hinge detail on one long edge. "
            "4. Cut LED hole on front, port hole on bottom."
        ),
        "recognition_features": (
            "1. HEADBAND ARC: The smooth arch connecting two ear cups — THE headphone silhouette. "
            "2. EAR CUP SHAPE: Oval cushions that visually communicate 'audio device'. "
            "3. EARBUD STEMS: The short stems hanging from in-ear pieces are iconic (AirPods style). "
            "4. CASE HINGE LINE: The split line where the earbud case opens. "
            "5. MATERIAL CONTRAST: Mesh/fabric on cushions vs hard plastic/metal on cups."
        )
    },

    "Gaming": {
        "visual_profile": (
            "GAME CONTROLLERS: Ergonomic, organic shape designed to be held with two hands. "
            "FRONT VIEW: Symmetrical or near-symmetrical with two grips flaring downward like horns. "
            "Controls arranged on the face: D-pad (left), face buttons (right), analog sticks, "
            "center buttons, touchpad (PlayStation). "
            "TOP VIEW: Bumper buttons and triggers visible on the shoulder area. "
            "SIDE VIEW: The grips curve inward — the controller is thickest at the shoulders "
            "and tapers to rounded ends at the grips. "
            "GAME CONSOLES: Rectangular boxes, often with curved/angled surfaces. "
            "Disc drives, buttons, USB ports, ventilation patterns."
        ),
        "build_strategy": (
            "ORIENTATION: Controller built face-up — controls face +Z, held along X axis. "
            "  Face (buttons) = +Z face ('>Z'), Bottom = -Z face ('<Z'), "
            "  Front edge = -Y face ('<Y'), Back edge = +Y face ('>Y'), "
            "  Left grip = -X side ('<X'), Right grip = +X side ('>X'). "
            "CONTROLLER STEPS: "
            "1. Main body: rounded box for the central section. "
            "2. Grip extensions: two angled boxes below, extending toward ±X and -Z. "
            "3. D-PAD on TOP face (+Z), LEFT side: "
            "   cross-shaped cut at x ≈ -body_w*0.25, z = +height/2 "
            "4. FACE BUTTONS on TOP face (+Z), RIGHT side: "
            "   4 small cylinders in diamond at x ≈ +body_w*0.25, z = +height/2 "
            "5. ANALOG STICKS on TOP face (+Z): small cylinders with concave tops. "
            "   PS: symmetric (both at same Y). Xbox: asymmetric (left stick higher). "
            "6. BUMPERS/TRIGGERS on BACK edge (>Y): thin plates on upper-back edge. "
            "7. USB-C on FRONT or TOP edge — use SLOT2D for rounded port: "
            "   port_cut = cq.Workplane('XZ').slot2D(usb_w, usb_h).extrude(wall*3).translate((0, -depth/2, z_pos)) "
            "8. TOUCHPAD (PS) on TOP face (+Z): centered recessed rectangle. "
            "CONSOLE: Box with strategic ventilation cuts, drive slot, button recesses."
        ),
        "recognition_features": (
            "1. GRIP HORNS: The two downward-extending grips are THE controller shape signature. "
            "2. CONTROL LAYOUT: D-pad left, face buttons right, sticks in between — unmistakable. "
            "3. SHOULDER BUTTONS: Bumpers and triggers on the top/back edge (>Y). "
            "4. ANALOG STICKS: Thumbstick mushroom caps protruding from the top face (+Z). "
            "5. PS vs XBOX: Symmetric stick layout (PS) vs asymmetric (Xbox) — model-critical."
        ),
        "position_map": (
            "FEATURE → FACE → AXIS → POSITION (controller face-up, Z=0 bottom, Z=H top): "
            "  D-pad        → TOP (+Z) → z=body_height, x=-width*0.25 (left of center) "
            "  Face buttons → TOP (+Z) → z=body_height, x=+width*0.25 (right of center) "
            "  Left stick   → TOP (+Z) → z=body_height, left-center area "
            "  Right stick  → TOP (+Z) → z=body_height, right-center area "
            "  Touchpad     → TOP (+Z) → z=body_height, x=0 (dead center) "
            "  Bumpers      → BACK (>Y) → y=+depth/2, ±x (left and right shoulders) "
            "  Triggers     → BACK (>Y) → y=+depth/2, ±x, angled downward "
            "  USB-C port   → FRONT (<Y) or TOP → depending on controller model "
            "  Light bar    → FRONT (<Y) → y=-depth/2, around touchpad area "
            "  Speaker      → BOTTOM (<Z) or FRONT → z=0"
        )
    },

    "Wearables": {
        "visual_profile": (
            "SMARTWATCHES: Small rounded-rectangle or circular case worn on the wrist. "
            "FRONT VIEW: Screen dominates the face — rounded-rectangle with curved glass edges. "
            "SIDE VIEW: Shows the thickness (~10-14mm), the Digital Crown knob, and side button. "
            "The case transitions smoothly into band attachment lugs. "
            "BACK VIEW: Sensor array (circular glass/ceramic window) and band slots. "
            "PROPORTIONS: Face is roughly 42-49mm across, nearly square but slightly taller than wide. "
            "The device should look compact and wrist-appropriate — much smaller than a phone."
        ),
        "build_strategy": (
            "ORIENTATION: box(width, depth, height) — watch STANDING UPRIGHT, screen faces -Y. "
            "  Screen = FRONT (-Y face '<Y'), Back/sensors = +Y face ('>Y'), "
            "  Top (12 o'clock) = +Z face ('>Z'), Bottom (6 o'clock) = -Z face ('<Z'), "
            "  Right (crown side) = +X face ('>X'), Left (button side) = -X face ('<X'). "
            "STEPS: "
            "1. body = cq.Workplane('XY').box(width, depth, height) with large corner fillets. "
            "2. SCREEN RECESS on FRONT (<Y): "
            "   screen = box(scr_w, 0.5, scr_h).translate((0, -depth/2, 0)) "
            "3. DIGITAL CROWN on RIGHT (>X): "
            "   crown = cq.Workplane('XY').cylinder(3, crown_r) "
            "   crown = crown.rotate((0,0,0), (0,1,0), 90)  # align cylinder along X "
            "   crown = crown.translate((+width/2 + 1, 0, height*0.15))  # protrudes from right side "
            "4. SIDE BUTTON on RIGHT (>X): below the crown — use SLOT2D for pill shape. "
            "   btn = cq.Workplane('YZ').slot2D(btn_h, btn_w).extrude(3).translate((+width/2, 0, -height*0.1)) "
            "5. BAND LUGS on TOP (>Z) and BOTTOM (<Z): short extensions for strap. "
            "6. SENSOR on BACK (>Y): circular recess on .faces('>Y'). "
            "7. SPEAKER/MIC on LEFT (<X): thin slot."
        ),
        "recognition_features": (
            "1. ROUNDED RECTANGLE FACE: Not circular (unless it's a round watch) — distinctly a rounded rect. "
            "2. DIGITAL CROWN: The small knob on the RIGHT side (+X) — THE Apple Watch identifier. "
            "3. BAND INTEGRATION: How the case flows into the band attachment points at TOP and BOTTOM (±Z). "
            "4. COMPACT SIZE: Must look wrist-sized — visually much smaller than other devices. "
            "5. SCREEN CURVATURE: On modern models, the glass curves into the case edges."
        ),
        "position_map": (
            "FEATURE → FACE → AXIS → POSITION (Z=0 bottom, Z=H top): "
            "  Screen       → FRONT (<Y) → y=-depth/2, centered "
            "  Digital Crown → RIGHT (>X) → x=+width/2, z=height*0.6 (above center) "
            "  Side button  → RIGHT (>X) → x=+width/2, z=height*0.4 (below crown) "
            "  Sensor array → BACK (>Y) → y=+depth/2, centered "
            "  Band lug top → TOP (>Z) → z=body_height, centered "
            "  Band lug bot → BOTTOM (<Z) → z=0, centered "
            "  Speaker slot → LEFT (<X) → x=-width/2, z=height*0.5 (mid-height)"
        )
    },

    "Peripherals": {
        "visual_profile": (
            "KEYBOARDS: Low, wide rectangular platform with an array of keys on top. "
            "Keys are visible as a grid of small raised squares with gaps between them. "
            "Side view shows a slight rear-to-front taper (higher at back, lower at front). "
            "MICE: Organic sculpted shape fitting the hand. Smooth top surface with a "
            "scroll wheel visible between left and right click zones. Side buttons. "
            "Ergonomic mice are asymmetric with a thumb rest area. "
            "PROPORTIONS: Keyboard width ≈ 29cm (60%) to 44cm (full). "
            "Mouse ≈ 12cm long, 6-8cm wide, 3-5cm tall."
        ),
        "build_strategy": (
            "KEYBOARD: "
            "1. Base slab: box(width, depth, height_rear) with rounded corners. "
            "2. Taper the front: cut or loft so front is lower than rear. "
            "3. Cut key grid: array of small recesses (~14mm × 14mm, 1mm deep, 1mm gaps). "
            "4. Add keycaps: small raised rounded rectangles in each recess (0.5mm above surface). "
            "5. USB port on rear edge. "
            "MOUSE: "
            "1. Lofted shape from bottom outline to top peak. "
            "2. Scroll wheel: small cylinder recessed between the two button zones. "
            "3. Side buttons: small bumps or recessed panels on left side. "
            "4. Bottom: flat with sensor window hole and PTFE feet pads."
        ),
        "recognition_features": (
            "1. KEY GRID: The orderly array of keycaps is THE keyboard identifier. "
            "2. TAPER: Keyboards slope downward toward the front for typing comfort. "
            "3. SCROLL WHEEL: The wheel between mouse buttons is THE mouse identifier. "
            "4. ERGONOMIC CURVE: Mice have a smooth, hand-fitting contour on top. "
            "5. FUNCTIONAL SPLIT: Clear visual separation between left click, right click, and scroll."
        )
    },

    "Desk Accessories": {
        "visual_profile": (
            "STANDS/RISERS: Elevated platforms — minimal, architectural forms. "
            "Usually open underneath (for storage/airflow). Clean geometric shapes. "
            "ORGANIZERS: Multi-compartment containers with dividers creating sections "
            "of different heights and widths for various items. "
            "CABLE MANAGEMENT: Small devices with C-shaped channels or grooves. "
            "GENERAL CHARACTER: Desk accessories should look clean, minimal, functional. "
            "Sharp or soft edges depending on style. Visible organization."
        ),
        "build_strategy": (
            "STANDS: "
            "1. Top platform: flat box with rounded edges. "
            "2. Support structure: side panels, legs, or A-frame. "
            "3. Cut ventilation slots if needed. "
            "4. Add anti-slip pads on top and bottom surfaces. "
            "ORGANIZERS: "
            "1. Outer shell box. "
            "2. Shell to create walls. "
            "3. Add interior divider walls at specific positions. "
            "4. Create compartments of varying depths. "
            "5. Round all top edges for aesthetics."
        ),
        "recognition_features": (
            "1. UTILITY VISIBLE: The purpose should be obvious from the shape (slots, compartments, platforms). "
            "2. CLEAN GEOMETRY: Desk accessories are usually simple, intentional geometric forms. "
            "3. STABLE BASE: Wide footprint relative to height — things shouldn't look tippy. "
            "4. PROPORTIONAL TO DESK ITEMS: Sized appropriately for pens, phones, laptops, monitors."
        )
    },

    "Drinkware": {
        "visual_profile": (
            "MUGS: Cylindrical (or slightly tapered) vessel with a C-shaped handle on one side. "
            "Side view: gentle taper wider at top, handle visible as a curved loop. "
            "Top view: circular opening with the handle extending outward. "
            "TUMBLERS: Tall, narrow cylinders with lids. Modern ones have integrated handles. "
            "Side view: tall and narrow, slight taper (narrower at bottom). Lid is visually distinct. "
            "BOTTLES: Cylinder with a narrower neck section and a cap/lid. "
            "PROPORTIONS: Mugs are squat (height ≈ width). "
            "Tumblers are tall (height ≈ 3.5× diameter). "
            "Bottles are medium (height ≈ 3× diameter)."
        ),
        "build_strategy": (
            "MUGS: "
            "1. Revolution: create a 2D profile (outer wall line), revolve 360°. "
            "2. Shell from top to create hollow interior. "
            "3. Handle: sweep a circular cross-section along a C-shaped arc path on one side. "
            "4. Union handle to body. Fillet the joints. "
            "TUMBLERS: "
            "1. Revolution: outer profile with slight taper. "
            "2. Shell from top. Double-wall if insulated (two concentric shells). "
            "3. Lid: separate cylinder with drinking hole cut. "
            "4. Handle: box or shaped extrusion attached to one side. "
            "BOTTLES: "
            "1. Revolution: body cylinder → neck taper → mouth. "
            "2. Shell from top. "
            "3. Cap: threaded cylinder (simplified as smooth cylinder)."
        ),
        "recognition_features": (
            "1. HANDLE (mugs): The C-shaped handle IS the mug — without it, it's a cup. "
            "2. LID (tumblers): The distinctive lid with drinking hole makes it a travel tumbler. "
            "3. HOLLOW INTERIOR: Must look like it can hold liquid — visible interior cavity. "
            "4. CYLINDRICAL FORM: Drinkware is based on circular cross-sections (revolutions). "
            "5. LIP/RIM: The drinking edge should be rounded and smooth."
        )
    },

    "Tools": {
        "visual_profile": (
            "HAND TOOLS: Ergonomic handle + functional head/tip. "
            "The handle is the larger portion — designed to be gripped comfortably. "
            "SCREWDRIVERS: Long cylindrical handle with a metal shaft extending from one end. "
            "The handle has grip features (hex flats, ridges, rubber sections). "
            "WRENCHES: Flat profile tool — mostly 2D shape with a jaw mechanism at one end. "
            "Side view shows the flat cross-section. Top view shows the handle taper. "
            "PROPORTIONS: Tools should feel 'right' in size — handles ~100-130mm long, "
            "grips ~30-35mm diameter, shafts/heads proportional."
        ),
        "build_strategy": (
            "SCREWDRIVER: "
            "1. Handle: revolution profile — spline curve that bulges in the grip area. "
            "2. Cut hex flats: 6 flat faces on the widest section (intersect with hexagonal prism). "
            "3. Shaft: long cylinder extending from the narrow end. "
            "4. Tip: Phillips cross cut or flat blade at the shaft end. "
            "5. Hanging hole: through-hole at butt end. "
            "WRENCH: "
            "1. 2D profile sketch of the wrench shape (handle + head). "
            "2. Extrude to thickness. "
            "3. Add jaw details, adjustment wheel. "
            "4. Fillet edges for comfortable grip."
        ),
        "recognition_features": (
            "1. HANDLE-TO-HEAD TRANSITION: Clear visual distinction between grip and working end. "
            "2. ERGONOMIC GRIP: Handle should look comfortable — bulging center, tapered ends. "
            "3. METAL SHAFT: Thin, straight shaft extending from handle (screwdrivers). "
            "4. FUNCTIONAL HEAD: The working end must look purposeful (jaw, blade, bit)."
        )
    },

    "Enclosures": {
        "visual_profile": (
            "ELECTRONICS ENCLOSURES: Two-piece boxes (bottom + lid) designed to house circuit boards. "
            "The enclosure looks like a small rectangular container with precise cutouts on the sides "
            "for ports and connectors. Internal features (bosses, posts, ribs) are visible when the "
            "lid is removed. "
            "SIDE VIEW: Low profile box with port openings visible along edges. "
            "TOP VIEW: Lid with ventilation slots/holes and possibly a label recess. "
            "PROPORTIONS: Sized to fit the specific board + clearance. Low profile (height ≈ 20-30mm)."
        ),
        "build_strategy": (
            "ORIENTATION: box(length, width, height) — enclosure sitting on desk, lid faces +Z. "
            "  Top/lid = +Z face ('>Z'), Bottom/feet = -Z face ('<Z'), "
            "  Front (user-facing ports) = -Y face ('<Y'), Back (cables) = +Y face ('>Y'), "
            "  Left = -X face ('<X'), Right = +X face ('>X'). "
            "STEPS: "
            "1. body = cq.Workplane('XY').box(length, width, height) "
            "2. Shell from TOP (>Z) with wall_thickness — open top for lid. "
            "3. SCREW BOSSES at 4 corners: cylinders on <Z interior. "
            "4. PCB MOUNTING POSTS: short cylinders at board hole positions on interior <Z. "
            "5. PORT CUTOUTS — match each port's REAL shape: "
            "   USB-C on FRONT (<Y): slot2D(usb_w, usb_h).extrude(wall*3).translate((x, -width/2, z)) — ROUNDED "
            "   HDMI on FRONT (<Y): box(hdmi_w, wall*3, hdmi_h).translate((x, -width/2, z)) — HDMI is rectangular "
            "   Ethernet on BACK (>Y): box(eth_w, wall*3, eth_h).translate((x, +width/2, z)) — RJ45 is rectangular "
            "   Power on BACK (>Y): cylinder(wall*3, pwr_r).translate((x, +width/2, z)) — barrel jack is ROUND "
            "   SD card on LEFT (<X): box(wall*3, sd_w, sd_h).translate((-length/2, y, z)) — SD is rectangular "
            "   GPIO slot on RIGHT (>X) or TOP (>Z): positioned accordingly. "
            "6. VENTILATION on TOP (>Z): array of slots on lid. "
            "7. LABEL RECESS on TOP (>Z): shallow rounded rect, 0.5mm deep. "
            "8. RUBBER FEET on BOTTOM (<Z): 4 small cylinders at corners."
        ),
        "recognition_features": (
            "1. TWO-PIECE DESIGN: Visible split line between bottom shell and lid. "
            "2. PORT CUTOUTS: Precise rectangular openings on FRONT (<Y) and BACK (>Y) walls. "
            "3. CORNER SCREWS: Screw points at corners holding lid to base. "
            "4. VENTILATION: Slots or hole patterns on TOP (>Z) for airflow. "
            "5. COMPACT SIZE: Sized tightly around the board it houses."
        ),
        "position_map": (
            "FEATURE → FACE → AXIS → POSITION (Z=0 bottom, Z=H top): "
            "  USB ports   → FRONT (<Y) → y=-width/2, x varies, z=height*0.5 "
            "  HDMI        → FRONT (<Y) → y=-width/2, x offset, z=height*0.5 "
            "  Ethernet    → BACK (>Y)  → y=+width/2, x varies, z=height*0.5 "
            "  Power jack  → BACK (>Y)  → y=+width/2, x=edge, z=height*0.5 "
            "  SD card     → LEFT (<X)  → x=-length/2, y=0, z=height*0.5 "
            "  GPIO slot   → TOP (>Z)   → z=body_height, centered or offset "
            "  Vent slots  → TOP (>Z)   → z=body_height, array centered "
            "  Rubber feet → BOTTOM (<Z) → z=0, 4 corners "
            "  Screw holes → CORNERS    → at (±x_inset, ±y_inset) on >Z or <Z"
        )
    },

    "Mechanical": {
        "visual_profile": (
            "GEARS: Circular disc with teeth around the circumference. "
            "Central bore hole for the shaft. Hub may protrude on one side. "
            "Side view: flat disc with protruding tooth profiles. "
            "BEARINGS/HOUSINGS: Cylindrical pocket mounted on a flat base. "
            "The cylindrical housing sits proud above a flat mounting plate. "
            "PULLEYS: Grooved wheel — similar to gear but with smooth groove instead of teeth. "
            "Flanges on sides keep the belt centered."
        ),
        "build_strategy": (
            "GEAR: "
            "1. Outer cylinder at tip diameter. "
            "2. Use involute profile equations OR approximate teeth with polarArray of trapezoidal cuts. "
            "3. Central bore: through-hole cylinder. "
            "4. Keyway: rectangular cut in bore. "
            "5. Hub: taller cylinder extending from one face. "
            "BEARING HOUSING: "
            "1. Base plate: box with mounting holes. "
            "2. Cylindrical housing: cylinder centered on base. "
            "3. Bore: through-hole sized for bearing OD. "
            "4. Grease fitting: small hole on top."
        ),
        "recognition_features": (
            "1. TOOTH PROFILE: Regular, repeating teeth around circumference = gear. "
            "2. CENTRAL BORE: Shaft hole is fundamental — every rotating component has one. "
            "3. MOUNTING FEATURES: Bolt holes, keyways — these look functional and engineered. "
            "4. PRECISION LOOK: Mechanical components should look precise and machined."
        )
    },

    "Home": {
        "visual_profile": (
            "HOUSEHOLD ITEMS: Functional objects for daily life — plant pots, vases, hooks, bookends. "
            "These should look like things you'd see in a home — warm, practical, sometimes decorative. "
            "POTS/VASES: Revolution profiles — circular cross-sections. Pots taper wider at top. "
            "Vases have elegant S-curves. Both have a substantial base for stability. "
            "HOOKS/BRACKETS: Small wall-mounted pieces. Functional curve visible from the side. "
            "Backplate sits flush against wall. "
            "BOOKENDS: L-shaped — a flat base slides under books, a vertical face holds them."
        ),
        "build_strategy": (
            "POTS/VASES: "
            "1. Define 2D profile as a spline or line + arc chain. "
            "2. Revolve 360° around central axis. "
            "3. Shell from top to create hollow interior. "
            "4. Add rim detail at top edge (thickened lip). "
            "5. Cut drainage holes in bottom (pots). "
            "HOOKS: "
            "1. Backplate: flat box with screw holes. "
            "2. Hook arm: sweep a circular cross-section along a curved spline path. "
            "3. Union hook to backplate. "
            "BOOKENDS: "
            "1. L-shaped profile: two boxes joined at 90°. "
            "2. Add fillet at inner corner. "
            "3. Cut decorative patterns in upright face (optional)."
        ),
        "recognition_features": (
            "1. FUNCTIONAL FORM: Each item should immediately communicate its purpose. "
            "2. REVOLUTION SHAPES: Pots and vases are circular — use revolve, not box. "
            "3. WEIGHT DISTRIBUTION: Items that stand must have a wide, stable base. "
            "4. DRAINAGE (pots): Holes in the bottom are essential and expected."
        )
    },

    "Hardware": {
        "visual_profile": (
            "BRACKETS/HANDLES: Functional hardware — engineered, practical shapes. "
            "L-BRACKETS: Right-angle metal piece with mounting holes. The triangular "
            "gusset in the corner is the key structural feature. "
            "HANDLES: Arched bar between two mounting posts. The arc shape invites gripping. "
            "PROPORTIONS: Hardware should look strong relative to its size. Adequate material "
            "thickness, visible fastener holes, structural reinforcement."
        ),
        "build_strategy": (
            "BRACKETS: "
            "1. L-shaped extrusion from a 2D right-angle profile. "
            "2. Add gusset: triangular plate in the corner. "
            "3. Cut mounting holes: countersunk through-holes. "
            "4. Fillet the inner corner for strength. "
            "HANDLES: "
            "1. Arc path: define a semicircular or gentle arc between two mount points. "
            "2. Sweep a circular cross-section along the arc. "
            "3. Add mounting posts: cylinders at each end. "
            "4. Cut screw holes through posts."
        ),
        "recognition_features": (
            "1. FASTENER HOLES: Visible screw/bolt holes communicate 'hardware'. "
            "2. STRUCTURAL GUSSET: The triangular reinforcement in brackets. "
            "3. ARC SHAPE: Handles have a smooth arch — inviting to grip. "
            "4. MATERIAL THICKNESS: Should look strong enough for its purpose."
        )
    },

    "Storage": {
        "visual_profile": (
            "STORAGE HOLDERS: Containers designed to organize and protect small items. "
            "Precise compartments sized for specific objects (batteries, memory cards). "
            "Each slot is just slightly larger than its contents. "
            "Visible organization — you can see where each item goes. "
            "Usually has a lid mechanism (snap-fit, hinge, or slide)."
        ),
        "build_strategy": (
            "1. Outer box sized for the total layout of compartments. "
            "2. Shell to create walls. "
            "3. Add internal dividers creating individual cells. "
            "4. Size each cell precisely: item dimension + 0.3-0.5mm clearance. "
            "5. Add spring/clip features for retention. "
            "6. Lid: separate flat plate with snap-fit tabs or living hinge."
        ),
        "recognition_features": (
            "1. SIZED COMPARTMENTS: Each slot precisely fits its intended item. "
            "2. ORGANIZATION VISIBLE: The grid/layout of storage cells. "
            "3. LID MECHANISM: Snap, hinge, or slide closure. "
            "4. COMPACT FORM: Entire holder should be portable and pocket-friendly."
        )
    },

    "Mounts": {
        "visual_profile": (
            "MOUNTING DEVICES: Adjustable clamps, clips, or brackets that hold devices in position. "
            "Usually have an articulated joint (ball joint, hinge) for angle adjustment. "
            "A clamping mechanism grips the device; a mounting mechanism attaches to a surface. "
            "PHONE MOUNTS: Spring-loaded side clamps in a cradle shape. "
            "ACTION CAMERA MOUNTS: Finger-and-bolt system with standardized dimensions."
        ),
        "build_strategy": (
            "PHONE MOUNTS: "
            "1. Cradle body: open-top channel shape. "
            "2. Side clamps: two jaw pieces with spring mechanism. "
            "3. Ball joint: sphere + socket for angle adjustment. "
            "4. Mounting clip: spring-loaded U-shape for vent/surface attachment. "
            "GOPRO MOUNTS: "
            "1. Finger tabs: thin parallel plates with bolt hole. "
            "2. Standard spacing: 3mm thick, 3mm gap. "
            "3. Base plate: flat surface with adhesive or clip."
        ),
        "recognition_features": (
            "1. ADJUSTMENT JOINT: Ball joint or hinge — the mount must be positionable. "
            "2. CLAMPING MECHANISM: Visible spring-loaded or screw-driven grip. "
            "3. DUAL ATTACHMENT: One side holds device, other side attaches to surface. "
            "4. RUBBER PADS: Grip surfaces to prevent scratching and slipping."
        )
    },

    "3D Printing": {
        "visual_profile": (
            "SPOOL HOLDERS: Frame structures that support a round filament spool. "
            "The spool sits on a horizontal axle and must spin freely. "
            "A-frame or T-frame base provides stability. "
            "Functional, utilitarian look — practical, not decorative."
        ),
        "build_strategy": (
            "1. Base: A-frame or T-frame from box/cylinder primitives. "
            "2. Vertical supports: two uprights to hold the axle. "
            "3. Axle: horizontal cylinder at the right height for the spool center. "
            "4. Size for standard spool: 200mm OD, 55mm hub hole. "
            "5. Add filament guide hole or tube."
        ),
        "recognition_features": (
            "1. HORIZONTAL AXLE: The spinning rod/tube where the spool sits. "
            "2. STABLE FRAME: Wide base that won't tip under spool weight. "
            "3. SPOOL-SIZED: Proportioned for a standard 200mm spool."
        )
    },

    "Drones & RC": {
        "visual_profile": (
            "DRONE TYPE IDENTIFICATION — match the user's request to the correct drone form factor:\n"
            "\n"
            "RACING/FPV QUADCOPTER (250-class): Compact X-frame, 4 arms, 4 motors+propellers, "
            "low-profile canopy, lightweight. Top view: X-shape with prop discs at arm tips.\n"
            "\n"
            "PHOTOGRAPHY/CAMERA DRONE (DJI-style): Streamlined fuselage body (NOT flat plates), "
            "4 foldable arms, big propellers, 3-axis gimbal+camera hanging under front, retractable landing legs.\n"
            "\n"
            "HEXACOPTER: 6-arm star (60° spacing), 6 motors+propellers, large center body, "
            "tall landing gear with payload rails underneath for heavy cameras.\n"
            "\n"
            "OCTOCOPTER: 8-arm radial (45° spacing), 8 motors+propellers, heavy-duty center hub, "
            "very tall retractable landing gear, parachute tube on top. Industrial cinema platform.\n"
            "\n"
            "TRICOPTER: Y-shaped frame with only 3 arms/motors/propellers. Rear motor has a SERVO "
            "that tilts it for yaw control — this tail tilt mechanism is the key visual feature.\n"
            "\n"
            "FIXED-WING VTOL: Airplane body + wings + tail + 4 vertical lift motors on wing booms + "
            "1 pusher motor at rear. Streamlined fuselage (loft/spline, NOT a box). Used for mapping/survey.\n"
            "\n"
            "MINI/MICRO DRONE (Tiny Whoop): Very small (~65mm), integrated ducted frame with "
            "circular prop guards fused into body. No separate arms. Flat-bottom = landing surface.\n"
            "\n"
            "DELIVERY/CARGO DRONE: Large 6-8 arm frame with enclosed fuselage, CARGO BAY underneath "
            "with release hook, very tall landing gear for package clearance. Sensor windows all around.\n"
            "\n"
            "UNDERWATER ROV DRONE: NOT an air drone — open cage frame with enclosed thrusters "
            "(horizontal + vertical), camera dome, LED floodlights, buoyancy foam on top, tether port.\n"
            "\n"
            "AGRICULTURAL SPRAY DRONE: Large 6-8 arm heavy-lift with SPRAY TANK on top, "
            "SPRAY BOOM with nozzles underneath, extra-wide tall landing gear for crop clearance.\n"
            "\n"
            "UNIVERSAL RULE: Every drone (except underwater ROV) MUST have visible MOTORS (cylinders on "
            "arm tips) and PROPELLERS (thin discs on motors). Without these, it looks like a flat PCB."
        ),
        "build_strategy": (
            "DRONE BUILD STRATEGY — adapt to drone type:\n"
            "\n"
            "=== STANDARD QUADCOPTER / RACING FPV ===\n"
            "1. Center body: two circular plates stacked with spacer posts between. "
            "2. Arms: 4 thin boxes radiating at 90° from center. "
            "3. Motors: 4 cylinders on arm tips. 4. Propellers: 4 thin discs on motors. "
            "5. Canopy: dome/shell over center. 6. Landing gear: 4 legs or 2 skids. "
            "7. Camera mount under front.\n"
            "\n"
            "=== PHOTOGRAPHY/CAMERA DRONE (DJI-style) ===\n"
            "1. Fuselage: streamlined body using .loft() — NOT flat plates. "
            "2. Arms: 4 fold-style arms from body sides (box extrusions with motor pod bulges). "
            "3. Motors: 4 large cylinders on arm tips. 4. Props: 4 large thin discs (230mm). "
            "5. Gimbal: 3-axis bracket under front body (nested boxes + camera sphere). "
            "6. Landing gear: 2 retractable skid legs or 4 spring legs. "
            "7. GPS dome on top, sensor windows on front/bottom.\n"
            "\n"
            "=== HEXACOPTER ===\n"
            "1. Center hub: large reinforced circular plate stack (150mm Ø). "
            "2. Arms: 6 arms at 60° intervals (use loop with cos/sin for placement). "
            "3. Motors: 6 large cylinders on arm tips. 4. Props: 6 large discs (330mm). "
            "5. Canopy: large dome. 6. Tall landing gear: 2 skid rails (120mm+ clearance). "
            "7. Payload rails under center for gimbal mounting.\n"
            "\n"
            "=== OCTOCOPTER ===\n"
            "Same as hexacopter but 8 arms at 45° intervals, 8 motors, 8 props. "
            "Taller gear (150mm+), dual GPS, parachute tube. Very large scale.\n"
            "\n"
            "=== TRICOPTER ===\n"
            "1. Center body: elongated rectangle (longer than wide). "
            "2. Arms: 2 front arms at ±45° and 1 rear tail boom (Y-shape). "
            "3. Motors: 3 cylinders on arm tips. 4. Props: 3 discs. "
            "5. TAIL SERVO: box on rear arm that tilts the rear motor (key feature!). "
            "6. Asymmetric landing gear.\n"
            "\n"
            "=== FIXED-WING VTOL ===\n"
            "1. Fuselage: streamlined tube using .loft() (nose cone → body → tail cone). "
            "2. Wings: flat extrusions from mid-fuselage (use airfoil cross-section if possible). "
            "3. Tail: V-tail or conventional (vertical + horizontal stabilizers). "
            "4. VTOL booms: 2 tubes on each wing with motors on top. "
            "5. VTOL motors: 4 cylinders on boom tops. 6. VTOL props: 4 discs. "
            "7. Pusher motor + prop at tail. 8. Landing skids under fuselage.\n"
            "\n"
            "=== MINI/MICRO DRONE ===\n"
            "1. Integrated frame: single body with 4 circular duct rings (NOT separate arms). "
            "2. Motors: 4 tiny cylinders inside ducts. 3. Props: 4 small discs inside ducts. "
            "4. Small canopy clip over center. 5. No landing legs — flat bottom. "
            "6. Micro FPV camera pod on front.\n"
            "\n"
            "=== DELIVERY/CARGO DRONE ===\n"
            "1. Enclosed fuselage: streamlined box/loft body (electronics inside). "
            "2. Arms: 6-8 heavy-duty arms. 3. Motors + props: 6-8 sets. "
            "4. CARGO BAY: open compartment under body with hook/winch cylinder. "
            "5. Very tall landing gear (180mm+) for package clearance. "
            "6. Sensor windows, GPS domes, parachute tube.\n"
            "\n"
            "=== UNDERWATER ROV ===\n"
            "1. Open cage frame: rail/tube structure (NOT an enclosed body). "
            "2. Thrusters: 4-6 enclosed tubes (horizontal rear + vertical) with props inside. "
            "3. Camera dome: clear hemisphere on front. 4. LED floodlights flanking camera. "
            "5. Electronics tube: sealed cylinder in center of cage. "
            "6. Buoyancy foam: block on top of cage. 7. Tether port on rear.\n"
            "\n"
            "=== AGRICULTURAL SPRAY DRONE ===\n"
            "1. Heavy center body: reinforced plate stack. "
            "2. Arms: 6-8 thick arms. 3. Motors + props: 6-8 large sets. "
            "4. SPRAY TANK: large box/cylinder on top or center of body. "
            "5. SPRAY BOOM: horizontal bar under body with 4+ nozzle cylinders. "
            "6. Pump assembly. 7. Extra-wide tall landing gear (200mm+)."
        ),
        "recognition_features": (
            "1. ARM COUNT determines type: 3=tricopter, 4=quadcopter, 6=hexacopter, 8=octocopter.\n"
            "2. MOTORS + PROPELLERS: Every air drone MUST have visible motor cylinders and prop discs — "
            "   these are the defining visual feature. Without them it looks like a PCB.\n"
            "3. FIXED-WING: Has WINGS + TAIL + fuselage — looks like an airplane with extra vertical motors.\n"
            "4. UNDERWATER ROV: Open cage frame + enclosed thrusters + camera dome + foam — NOT an air drone.\n"
            "5. MINI DRONE: Integrated ducted frame (prop guards fused into body) — very compact.\n"
            "6. DJI-STYLE: Streamlined body (NOT flat plates) + gimbal camera hanging under front.\n"
            "7. CARGO DRONE: Has a CARGO BAY under body + very tall landing gear.\n"
            "8. SPRAY DRONE: Has a TANK on body + spray boom with nozzles underneath.\n"
            "9. TRICOPTER: Y-shape + tail SERVO tilt mechanism on rear arm.\n"
            "10. CANOPY/COVER over center electronics is required on all types except ROV.\n"
            "11. LANDING GEAR: Required on all types (except mini drones which use flat-bottom design)."
        )
    },

    "Automotive": {
        "visual_profile": (
            "CAR ACCESSORIES: Small, purpose-built devices for vehicle interiors. "
            "VENT MOUNTS: Small clips that grip AC vent slats + cradle for phone. "
            "CUP HOLDER INSERTS: Cylindrical adapters — simple revolution profiles. "
            "These should look like they belong in a car interior — compact, functional, "
            "with rubber/soft-touch surfaces for grip."
        ),
        "build_strategy": (
            "VENT MOUNT: "
            "1. Vent clip: U-shaped spring mechanism (two boxes forming a C-channel). "
            "2. Ball joint: sphere for angle adjustment. "
            "3. Phone cradle: three-sided open frame with spring arms. "
            "4. Rubber pads: recessed circles on grip surfaces. "
            "CUP HOLDER INSERT: "
            "1. Tapered cylinder (revolve a slightly angled line). "
            "2. Top lip/flange: wider ring at top that rests on cup holder rim. "
            "3. Shell from top to create hollow interior."
        ),
        "recognition_features": (
            "1. COMPACT SIZE: Must look car-interior-appropriate — small and unobtrusive. "
            "2. GRIP SURFACES: Rubber pads visible on contact areas. "
            "3. ADJUSTMENT MECHANISM: Ball joint or similar for positioning. "
            "4. TAPERED FIT: Cup adapters visually narrow from top to bottom."
        )
    },

    "Fitness": {
        "visual_profile": (
            "DUMBBELLS: Two weight heads connected by a central grip handle. "
            "Side view: barbell silhouette — thick ends, thin middle. "
            "End view: hexagonal (if hex dumbbell) — 6-sided weight head prevents rolling. "
            "The handle section has knurled texture (crosshatch grip pattern). "
            "PROPORTIONS: Handle length ≈ 120mm. Handle diameter ≈ 32mm (fits a fist). "
            "Weight heads ≈ 85mm diameter, proportional to the weight value."
        ),
        "build_strategy": (
            "1. Handle: cylinder (diameter ≈ 32mm, length ≈ 120mm). "
            "2. Weight heads: hexagonal prism extrusions on each end (or cylindrical for round style). "
            "3. Transition: filleted cone/taper connecting handle to weight heads. "
            "4. Knurl texture on handle: array of small diamond cuts (optional, adds realism). "
            "5. Chamfer all weight head edges."
        ),
        "recognition_features": (
            "1. DUMBBELL SILHOUETTE: Thick-thin-thick barbell shape is instantly recognizable. "
            "2. HEX HEADS: Hexagonal weight ends that prevent rolling. "
            "3. KNURLED HANDLE: Textured grip section in the center. "
            "4. SYMMETRY: Both ends must be identical — perfectly balanced."
        )
    },

    "Sculptures & Art": {
        "visual_profile": (
            "ARTISTIC OBJECTS: Decorative, display-oriented pieces prioritizing aesthetics. "
            "CHESS PIECES: Revolution-profile silhouettes — wide base, narrow stem, distinctive top. "
            "Each piece type has a unique crown (cross, coronet, mitre, horse, battlements, sphere). "
            "TROPHIES: Cup-on-pedestal form — flared bowl, decorative stem, tiered base. "
            "BUSTS: Head and shoulders on a plinth — simplified geometric approximation of human form. "
            "ABSTRACT: Flowing twisted forms created by lofting rotated cross-sections. "
            "MEDALS: Flat disc with raised rim and relief design. "
            "CHARACTER: Artistic pieces should look elegant, intentional, display-worthy."
        ),
        "build_strategy": (
            "CHESS PIECES: "
            "1. Base disc: short cylinder with molding profile. "
            "2. Stem: tapered cylinder (revolution of angled line). "
            "3. Body: wider section above stem (revolution profile). "
            "4. Crown: piece-specific top feature. "
            "5. Use .revolve() for most parts. "
            "TROPHIES: "
            "1. Base: stacked rectangular blocks with chamfers. "
            "2. Stem: thin cylinder or tapered shape. "
            "3. Cup: revolution of a U-profile → flared opening. "
            "4. Handles: sweep circles along C-shaped arc paths. "
            "BUSTS: "
            "1. Pedestal: cylinder or box. "
            "2. Shoulders: lofted trapezoid. "
            "3. Neck: cylinder. "
            "4. Head: ellipsoid (scaled sphere). "
            "ABSTRACT: "
            "1. Define 4-6 cross-sections at different heights. "
            "2. Rotate/scale each section. "
            "3. Loft all sections together."
        ),
        "recognition_features": (
            "1. SILHOUETTE IDENTITY: Each chess piece/sculpture is identified by its outline shape. "
            "2. PEDESTAL/BASE: Display pieces sit on proper bases — this says 'art object'. "
            "3. REVOLUTION PROFILES: Most sculptural forms use rotational symmetry. "
            "4. PROPORTIONAL ELEGANCE: Thin stems, flared tops, tiered bases — visual rhythm. "
            "5. SMOOTH SURFACES: Art pieces should have polished, fillet-rich surfaces."
        )
    },

    "Architecture": {
        "visual_profile": (
            "BUILDING MODELS: Simplified architectural representations capturing key structural elements. "
            "HOUSES: Box body + triangular roof prism. Windows as rectangular cutouts in walls. "
            "Door centered on front face. Chimney on roof. "
            "SKYSCRAPERS: Tall box with window grid on all faces. Setback (narrower) upper sections. "
            "CHURCHES: Cruciform (cross-shaped) plan with tower(s) and gabled roof. "
            "CASTLES: Curtain walls, corner towers, central keep, crenellated (battlement) tops. "
            "PAGODAS: Stacked tiers with upward-curving roofs, each tier smaller than below. "
            "CHARACTER: Architectural models should capture the ICONIC SILHOUETTE — "
            "even at small scale, you should recognize what building type it is."
        ),
        "build_strategy": (
            "ORIENTATION: box(width, depth, wall_height) — building standing up on ground plane. "
            "  Front (entrance) = -Y face ('<Y'), Back = +Y face ('>Y'), "
            "  Left = -X face ('<X'), Right = +X face ('>X'), "
            "  Roof/top = +Z face ('>Z'), Ground = -Z face ('<Z' or z=0). "
            "HOUSE STEPS: "
            "1. walls = cq.Workplane('XY').box(width, depth, wall_height) "
            "   walls = walls.translate((0, 0, wall_height/2))  # sit on ground at z=0 "
            "2. ROOF: triangular prism on top. "
            "   roof = cq.Workplane('XZ').moveTo(-width/2, wall_height).lineTo(0, wall_height + roof_h) "
            "   .lineTo(width/2, wall_height).close().extrude(depth)  # extrudes along Y "
            "   roof = roof.translate((0, -depth/2, 0)) "
            "3. WINDOWS on FRONT (<Y) — array of rectangular cutouts: "
            "   win = box(win_w, wall*3, win_h).translate((win_x, -depth/2, win_z)) "
            "   Repeat for BACK (>Y), LEFT (<X: box(wall*3, win_w, win_h)), RIGHT (>X). "
            "4. DOOR on FRONT (<Y): centered at ground level. "
            "   door = box(door_w, wall*3, door_h).translate((0, -depth/2, door_h/2)) "
            "5. CHIMNEY on ROOF: small box on one side of roof. "
            "   chimney = box(ch_w, ch_d, ch_h).translate((width*0.3, 0, wall_height + ch_h/2)) "
            "CASTLE STEPS: "
            "1. Curtain walls: rectangular shells. "
            "2. Corner towers: cylinders at (±width/2, ±depth/2), taller than walls. "
            "3. Gate: arch cut on FRONT wall (<Y): translate((0, -depth/2, arch_z)). "
            "4. Merlons: loop of small boxes along wall tops at z = wall_height."
        ),
        "recognition_features": (
            "1. ROOF SHAPE: Gabled (triangle), flat, dome, spire — defines the building type. "
            "2. WINDOW PATTERN: Regular grid of openings on ALL 4 wall faces (±X, ±Y). "
            "3. ENTRANCE: Door on FRONT face (<Y) — every building needs a visible entrance. "
            "4. VERTICAL PROPORTION: Buildings are taller than wide (except houses). "
            "5. ICONIC SILHOUETTE: The outline shape should identify the building type instantly."
        ),
        "position_map": (
            "FEATURE → FACE → AXIS → POSITION (building standing up, Z=0 is ground): "
            "  Front door    → FRONT (<Y) → y=-depth/2, x=0 (centered), z=0 (ground level, door rises from z=0 to z=door_h) "
            "  Front windows → FRONT (<Y) → y=-depth/2, x=±offset, z=floor_height (per floor) "
            "  Back windows  → BACK (>Y)  → y=+depth/2, x=±offset, z=floor_height "
            "  Side windows  → LEFT (<X)  → x=-width/2, y=±offset, z=floor_height "
            "  Side windows  → RIGHT (>X) → x=+width/2, y=±offset, z=floor_height "
            "  Chimney       → ROOF (>Z)  → on top of roof, offset from center "
            "  Steps         → FRONT (<Y) → y slightly < -depth/2, z=0 (ground level) "
            "  Roof          → TOP (>Z)   → starts at z=wall_height, peaks above "
            "  Foundation    → BOTTOM (<Z) → z=0, slightly wider than walls"
        )
    },

    "Landmarks": {
        "visual_profile": (
            "FAMOUS STRUCTURES: Simplified models of world-famous landmarks. "
            "These MUST capture the iconic silhouette — the shape everyone recognizes. "
            "STATUE OF LIBERTY: Robed figure on pedestal with raised torch arm and crown spikes. "
            "BIG BEN: Tall square tower with clock faces and pointed spire. "
            "TAJ MAHAL: Central dome on a building with 4 corner minarets on a platform. "
            "EIFFEL TOWER: 4 curved legs meeting at top, with observation platforms. "
            "CHARACTER: Simplification is OK, but the SILHOUETTE must be immediately recognizable."
        ),
        "build_strategy": (
            "LANDMARKS require 'silhouette-first' construction: "
            "1. Start with the most iconic element (dome, tower, figure shape). "
            "2. Build from bottom up — foundation/platform → body → distinctive top. "
            "3. Simplify details but NEVER simplify the outline shape. "
            "4. Use lofts for tapered forms, revolutions for domes, booleans for openings. "
            "5. Key proportions matter more than surface detail — get the ratios right."
        ),
        "recognition_features": (
            "1. ICONIC SILHOUETTE: The outline must match the real landmark — this is non-negotiable. "
            "2. KEY PROPORTIONS: Height-to-width ratios must match reality. "
            "3. SIGNATURE ELEMENT: Crown spikes (Liberty), clock faces (Big Ben), onion dome (Taj Mahal). "
            "4. SCALE INDICATORS: Arches, windows, stairs that communicate the massive scale."
        )
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# PRODUCT-SPECIFIC VISUAL OVERRIDES
# ═══════════════════════════════════════════════════════════════════════════════
# These override or supplement category-level knowledge for specific products
# that have unique visual characteristics.

PRODUCT_VISUAL_OVERRIDES: Dict[str, Dict[str, str]] = {

    # ── iPhones with FLAT edges (12 and later) ──
    "Apple iPhone 16 Pro Max": {
        "visual_profile": (
            "DISTINCTIVE: Premium 'jewelry slab' — titanium flat edges catch light. "
            "The camera island is a large rounded square in the upper-left back with 3 prominent "
            "lens circles in a triangular arrangement. The Dynamic Island is a small pill-shaped "
            "cutout at the top-center of the screen. The phone is notably tall and narrow. "
            "EDGE CHARACTER: Perfectly flat edges with very sharp transitions — like a precision-machined bar. "
            "The titanium finish has a subtle brushed texture. "
            "BACK: Almost entirely smooth except for the camera island — premium minimalism."
        ),
        "recognition_features": (
            "1. TITANIUM FLAT EDGES: Sharp, machined-look flat sides — not rounded. "
            "2. TRIANGULAR TRIPLE CAMERA: Three large circles in a triangle inside a rounded-rect island. "
            "3. DYNAMIC ISLAND: Pill-shaped cutout at top of screen (not a notch). "
            "4. ACTION BUTTON: Small button on upper-left replacing the old mute switch. "
            "5. USB-C: Port at bottom center (no more Lightning)."
        )
    },

    "Samsung Galaxy S24 Ultra": {
        "visual_profile": (
            "DISTINCTIVE: Nearly RECTANGULAR — the most squared-off phone on the market. "
            "Corner radius is only ~3mm, making it look angular and precise, like a titanium writing slate. "
            "The cameras are NOT in an island — each lens has its own individual raised ring on the back. "
            "The S Pen silo slot is visible at the bottom-left. "
            "EDGE CHARACTER: Flat titanium edges similar to iPhone but with MUCH sharper corners."
        ),
        "recognition_features": (
            "1. SQUARED CORNERS: Tiny 3mm radius — nearly rectangular, unlike any iPhone. "
            "2. INDIVIDUAL CAMERA RINGS: Each lens has its own separate circle — NO shared island. "
            "3. S PEN SLOT: Small rectangular slot at bottom-left for the stylus. "
            "4. FLAT TITANIUM EDGES: Similar to iPhone but sharper overall shape."
        )
    },

    "Google Pixel 9 Pro": {
        "visual_profile": (
            "DISTINCTIVE: The horizontal camera bar spanning the full width of the upper back — "
            "a raised strip like a speed bump running across the phone. This is the Pixel signature. "
            "The phone body is gently rounded at the back edges but flat at the sides. "
            "The camera bar is a pill-shaped island about 18mm tall, stretching nearly corner to corner."
        ),
        "recognition_features": (
            "1. FULL-WIDTH CAMERA BAR: Horizontal strip across the entire back width — UNIQUE to Pixel. "
            "2. POLISHED ALUMINUM FRAME: Shiny, reflective sides. "
            "3. SOFT CORNERS: Larger corner radius (~6.5mm) than Samsung but similar to iPhone. "
            "4. BAR CONTAINS CAMERAS + FLASH: Triple cameras inside the bar, not individual rings."
        )
    },

    # ── iPhones with ROUNDED edges (11 and earlier) ──
    "Apple iPhone 11": {
        "visual_profile": (
            "DISTINCTIVE: ROUNDED edges — the sides curve smoothly into front and back surfaces. "
            "This is the pre-flat-edge iPhone look — softer, more organic feel in hand. "
            "Square camera island on back with 2 lenses + flash. Wide notch on front face."
        ),
        "recognition_features": (
            "1. ROUNDED EDGES: Smooth curved sides, NOT flat — critical visual difference from 12+. "
            "2. SQUARE CAMERA ISLAND: Two-lens square bump, not triangular and not vertical. "
            "3. WIDE NOTCH: Broader notch than later models (not Dynamic Island). "
            "4. LIGHTNING PORT: Old-style connector, not USB-C."
        )
    },

    # ── Controllers ──
    "Sony DualSense Controller (PS5)": {
        "visual_profile": (
            "DISTINCTIVE: Two-tone black-and-white design with a futuristic, spaceship-like aesthetic. "
            "The body is split into a dark inner section (controls) and white outer shell (grips). "
            "The triggers are massive and deeply recessed. The touchpad is a prominent flat zone in center. "
            "A thin light bar wraps around the touchpad edges. "
            "PROPORTIONS: Wider and slightly bulkier than Xbox controller. Grips are more pronounced."
        ),
        "recognition_features": (
            "1. TWO-TONE SPLIT: White outer shell + black inner controls — the PS5 signature look. "
            "2. SYMMETRIC STICKS: Both analog sticks at same height — unlike Xbox. "
            "3. TOUCHPAD: Large flat rectangular surface dominating the center. "
            "4. LIGHT BAR: Thin RGB strip around the touchpad edge. "
            "5. MASSIVE TRIGGERS: L2/R2 are large, deeply recessed levers."
        )
    },

    "Xbox Wireless Controller": {
        "visual_profile": (
            "DISTINCTIVE: More traditional, compact controller design. Textured dot grip on front face "
            "and triggers. The asymmetric stick layout is THE Xbox signature — left stick is higher "
            "and more forward than right stick. "
            "PROPORTIONS: Slightly smaller and lighter-looking than DualSense. "
            "The bumpers have a more sculpted, wrap-around shape."
        ),
        "recognition_features": (
            "1. ASYMMETRIC STICKS: Left stick UP, right stick DOWN — the Xbox difference. "
            "2. TEXTURED GRIP: Small dot pattern on the face and triggers. "
            "3. XBOX BUTTON: Circular guide button with Xbox logo at top-center. "
            "4. D-PAD: Faceted disc shape (can be cross or circular depending on model). "
            "5. SINGLE-TONE: Usually one color, not two-tone like DualSense."
        )
    },

    # ── Headphones ──
    "Apple AirPods Max": {
        "visual_profile": (
            "DISTINCTIVE: Mesh canopy headband instead of padded foam — you can see through the headband. "
            "Stainless steel arms telescope for adjustment. The ear cups are large circular shapes "
            "with magnetic cushions. The Digital Crown (scroll wheel) on the right cup is a key identifier. "
            "Overall look: industrial, minimalist, premium metal."
        ),
        "recognition_features": (
            "1. MESH HEADBAND: See-through knit canopy, not a solid padded band. "
            "2. TELESCOPING METAL ARMS: Visible stainless steel slider mechanism. "
            "3. DIGITAL CROWN: Small scroll wheel on the right ear cup — borrowed from Apple Watch. "
            "4. CIRCULAR EAR CUPS: Perfectly round (not oval like most headphones). "
            "5. MAGNETIC CUSHIONS: Ear pads attach magnetically (visible seam line)."
        )
    },

    # ── Drinkware specifics ──
    "Insulated Travel Tumbler": {
        "visual_profile": (
            "DISTINCTIVE: Tall, narrow, cylindrical — like a chimney with a handle. "
            "The handle is a large loop attached vertically alongside the body (enough for 3-4 fingers). "
            "The lid is the most complex part — has a flip-top or sliding cover over the drinking hole, "
            "plus a straw slot. The bottom is wider with a rubber non-slip pad. "
            "Stanley/YETI look: rugged, outdoor-ready, substantial."
        ),
        "recognition_features": (
            "1. TALL NARROW FORM: Height is 3.5× the diameter — much taller than a mug. "
            "2. INTEGRATED HANDLE: Large enough for 3-4 fingers, attached alongside the body. "
            "3. COMPLEX LID: Flip-top mechanism with drinking hole and straw slot. "
            "4. RUBBER BASE PAD: Visible non-slip ring on the bottom. "
            "5. DOUBLE-WALL: If shown in cross-section, two concentric walls with air gap."
        )
    },

    # ── Keyboards/Mice ──
    "Logitech MX Master 3S": {
        "visual_profile": (
            "DISTINCTIVE: Highly ASYMMETRIC ergonomic shape — designed for right-hand use only. "
            "The left side has a pronounced thumb rest concavity. Two small thumb buttons above it. "
            "A small horizontal scroll wheel on the thumb side. "
            "The main scroll wheel is a machined steel cylinder with horizontal grooves (MagSpeed). "
            "The mouse is taller and more sculpted than most mice — almost like a small hill."
        ),
        "recognition_features": (
            "1. ASYMMETRIC BODY: Not symmetrical — right-hand ergonomic shape with thumb wing. "
            "2. TWO SCROLL WHEELS: Main (top) + horizontal thumb wheel (left side). "
            "3. THUMB REST: Concave depression on the left side for thumb comfort. "
            "4. MACHINED METAL WHEEL: The main scroll wheel looks metallic with horizontal lines. "
            "5. TALL PROFILE: Much taller than flat mice — substantial arch shape."
        )
    },

    "Apple Magic Mouse": {
        "visual_profile": (
            "DISTINCTIVE: Incredibly low-profile, almost like a slice of soap or a smooth river stone. "
            "The entire top surface is one continuous multi-touch surface — no visible buttons or wheel. "
            "Side view: wedge-shaped, rising from almost nothing at the front to ~21mm at the back. "
            "The base is flat and thin, with the charging port infamously on the BOTTOM."
        ),
        "recognition_features": (
            "1. NO VISIBLE BUTTONS: Completely smooth top surface — unique among mice. "
            "2. ULTRA-LOW PROFILE: Barely rises above the desk surface. "
            "3. CONTINUOUS CURVE: One seamless arc from front to back. "
            "4. PORT ON BOTTOM: Lightning/USB-C port on the underside (infamous design choice). "
            "5. MINIMALIST: White/silver, no visible mechanical features on top."
        )
    },

    # ── Architecture specifics ──
    "Medieval Castle Model": {
        "visual_profile": (
            "DISTINCTIVE: A fortified compound — outer walls enclosing a courtyard with a central keep. "
            "Cylindrical towers at each corner, taller than the walls, with conical or flat tops. "
            "Battlements (merlons and crenels) along every wall top and tower top — the distinctive "
            "rectangular tooth pattern. A gatehouse with an arched opening in the front wall. "
            "Arrow slits (narrow vertical cuts) scattered across walls and towers."
        ),
        "recognition_features": (
            "1. CRENELLATIONS: The rectangular tooth pattern along wall tops — THE castle identifier. "
            "2. CORNER TOWERS: Cylindrical towers rising above the walls at each corner. "
            "3. GATEHOUSE: Arched entrance in the front wall. "
            "4. CENTRAL KEEP: The tallest structure inside the walls. "
            "5. ARROW SLITS: Narrow vertical cuts in walls for defense."
        )
    },

    "Eiffel Tower Model (Simplified)": {
        "visual_profile": (
            "DISTINCTIVE: Four legs curving inward as they rise, meeting at a narrow top. "
            "Two horizontal platforms visible at 1/5 and 1/3 height. "
            "Lattice/ironwork texture on the legs (simplified as cutout windows). "
            "Arched openings between legs at the first platform level. "
            "Antenna/spire extending from the peak."
        ),
        "recognition_features": (
            "1. FOUR CURVED LEGS: Spreading wide at base, meeting at top — THE Eiffel shape. "
            "2. OBSERVATION PLATFORMS: Two visible horizontal levels breaking the leg curves. "
            "3. ARCH BETWEEN LEGS: Curved opening at the first platform level. "
            "4. EXTREME TAPER: Very wide at base, very narrow at top. "
            "5. ANTENNA SPIRE: Thin pointed top extension."
        )
    },

    "Taj Mahal Model (Simplified)": {
        "visual_profile": (
            "DISTINCTIVE: Large onion dome sitting atop a cube-like building on a raised platform, "
            "with 4 tall thin minarets at the platform corners. "
            "The onion dome BULGES outward beyond a hemisphere then narrows to a point — "
            "this is NOT a simple half-sphere, it's wider in the middle. "
            "Large pointed arch recesses (iwans) on each face of the main building."
        ),
        "recognition_features": (
            "1. ONION DOME: Bulging dome wider than a hemisphere — THE Taj Mahal shape. "
            "2. FOUR MINARETS: Tall thin towers at the corners of the platform. "
            "3. IWAN ARCHES: Large pointed arch recesses on each face. "
            "4. RAISED PLATFORM: The building sits on a substantial elevated terrace. "
            "5. SYMMETRY: Perfect symmetry on all 4 sides."
        )
    },

    # ── Sculptures ──
    "Chess Piece Set (Staunton Style)": {
        "visual_profile": (
            "DISTINCTIVE: Each piece has a unique silhouette but shares the same construction logic: "
            "wide circular base → narrow stem → wider body section → unique crown/top. "
            "KING: Tallest piece. Cross on top. Collar below the cross. "
            "QUEEN: Second tallest. Small coronet (crown with points) on top. "
            "BISHOP: Mitre (dome with diagonal slit) on top. "
            "KNIGHT: Horse head profile — the most complex piece. "
            "ROOK: Crenellated top (castle battlements on a cylinder). "
            "PAWN: Smallest. Simple ball on top."
        ),
        "recognition_features": (
            "1. BASE-STEM-BODY-CROWN: Every piece follows this structure — variation is only in the crown. "
            "2. KING'S CROSS: The cross finial is THE identifier for the king. "
            "3. QUEEN'S CORONET: Small crown with points — queen without it looks like a pawn. "
            "4. ROOK'S BATTLEMENTS: Rectangular teeth at top — castle fortress reference. "
            "5. KNIGHT'S HORSE HEAD: The only piece that's not rotationally symmetric."
        )
    },

    # ── Electronics ──
    "Raspberry Pi 4/5 Case": {
        "visual_profile": (
            "DISTINCTIVE: A small, tight-fitting box with precise port cutouts on two adjacent edges. "
            "One edge has a dense cluster of ports (2× USB-A stacked, Ethernet jack, all large). "
            "The adjacent edge has smaller ports (micro-HDMI × 2, USB-C power). "
            "Ventilation slots or a fan hole in the lid. GPIO header access slot."
        ),
        "recognition_features": (
            "1. DENSE PORT EDGE: One side is packed with large USB-A and Ethernet openings. "
            "2. SMALL FORM FACTOR: Only 85×56mm — smaller than a credit card in each direction. "
            "3. GPIO ACCESS: Long narrow slot in the lid for the 40-pin header. "
            "4. MOUNTING POSTS: 4 PCB standoffs at the Pi's specific hole pattern. "
            "5. SD CARD ACCESS: Slot on one short edge."
        )
    },

    # ── Nintendo Switch ──
    "Nintendo Switch Console": {
        "visual_profile": (
            "DISTINCTIVE: Central tablet with two colored controllers (Joy-Cons) attached to each side "
            "via rail grooves. The Joy-Cons make the device wider and add a colorful identity. "
            "A flip-out kickstand on the back lets it stand on a surface. "
            "The overall shape is a wide, thin rectangle — wider than a regular tablet due to the Joy-Cons. "
            "Top edge has vents, cartridge slot, and headphone jack."
        ),
        "recognition_features": (
            "1. JOY-CON RAILS: Side grooves where controllers slide on and off. "
            "2. CENTRAL SCREEN + SIDE CONTROLLERS: Three-piece appearance (controller-screen-controller). "
            "3. KICKSTAND: Flip-out stand on the back. "
            "4. GAME CARTRIDGE SLOT: Hidden under a cover on the top edge. "
            "5. COMPACT TABLET SIZE: ~239mm wide with Joy-Cons attached."
        )
    },

    # ── Apple Watch Ultra ──
    "Apple Watch Ultra 2": {
        "visual_profile": (
            "DISTINCTIVE: More rugged and squared-off than the standard Apple Watch. "
            "Raised edges guard the flat screen. An international orange action button on the left side "
            "is the key visual accent. The Digital Crown has a protective bumper. "
            "The case is noticeably thicker (14.4mm vs 9.7mm) and wider (49mm vs 46mm)."
        ),
        "recognition_features": (
            "1. ORANGE ACTION BUTTON: Bright orange button on left side — THE Ultra identifier. "
            "2. RAISED EDGE GUARD: Protective frame rising above the screen surface. "
            "3. CROWN GUARD: Bumper protecting the Digital Crown. "
            "4. RUGGED PROPORTIONS: Thicker and larger than standard Apple Watch. "
            "5. TITANIUM FINISH: Matte, brushed metal look."
        )
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# ADDITIONAL CATEGORY-LEVEL VISUAL KNOWLEDGE (Phase 3 Expansion)
# ═══════════════════════════════════════════════════════════════════════════════
# These cover product types users frequently request but previously had no
# visual guidance, resulting in generic box outputs.

CATEGORY_VISUAL_KNOWLEDGE_EXPANDED: Dict[str, Dict[str, str]] = {

    "Furniture": {
        "visual_profile": (
            "OVERALL FORM: Furniture pieces have functional proportions — a chair has a seat surface ~45cm "
            "high, a table top ~75cm high, shelves are 30-40cm deep. "
            "FRONT VIEW: Shows the main functional surface (seat, tabletop, shelf face) and legs/supports. "
            "SIDE VIEW: Reveals the depth/profile — chairs show backrest angle, tables show apron, "
            "shelves show depth and bracket shape. "
            "PROPORTIONS: Legs are typically 3-8% of the overall width in diameter/thickness. "
            "Tabletops overhang the base by 2-5cm on each side. "
            "MATERIAL CHARACTER: Wood = filleted edges with ~2mm radius. Metal = sharp chamfers. "
            "JOINERY: Real furniture has aprons (horizontal rails connecting legs below the top), "
            "stretchers (cross-braces between legs), and visible joint transitions."
        ),
        "build_strategy": (
            "ORIENTATION: Furniture STANDING UPRIGHT — tallest dimension is Z. "
            "STEPS: "
            "1. Start with the TOP surface (tabletop, seat) as a flat box or contoured shape at the target height. "
            "2. Add LEGS as cylinders or boxes descending from the underside of the top to Z=0. "
            "3. Add APRON rails — horizontal boxes connecting the tops of the legs just below the top surface. "
            "4. Add STRETCHERS — cross-braces between legs at ~30% of leg height. "
            "5. For chairs: add BACKREST as a flat box or contoured panel rising from the rear edge of the seat. "
            "6. For shelves: add VERTICAL SIDES as tall boxes, then insert SHELF PANELS at desired heights. "
            "7. Fillet ALL exposed edges. Add anti-slip feet (small cylinders at leg bottoms). "
            "8. For drawers: cut rectangular openings in the front face, add handle recesses or knob bosses."
        ),
        "recognition_features": (
            "1. FUNCTIONAL HEIGHT: Chairs ~45cm seat, tables ~75cm top, shelves variable. "
            "2. LEG PROPORTIONS: Legs that look structurally adequate (not too thin, not too thick). "
            "3. APRON/RAIL: Horizontal support member below the top surface connecting legs. "
            "4. EDGE TREATMENT: Rounded/chamfered edges on all user-touching surfaces. "
            "5. STABILITY: Wide enough base that the piece wouldn't tip over."
        )
    },

    "Kitchen & Cookware": {
        "visual_profile": (
            "OVERALL FORM: Kitchen items are either vessels (pots, bowls, cups — revolution profiles), "
            "flat surfaces (cutting boards, trays), or mechanical (grinders, presses, openers). "
            "Vessels: round cross-section, walls 1.5-3mm, handle attached to side. "
            "HANDLE: C-shape or D-shape handle on pots/pans, straight handle on skillets. "
            "Handles have a heat-break gap (air space between handle and hot body). "
            "LID: Slightly oversized disc with a central knob/handle, sits in a recessed rim. "
            "POUR SPOUT: Small triangular indent on rim for controlled pouring. "
            "BASE: Flat bottom with a slightly recessed foot ring (1-2mm step)."
        ),
        "build_strategy": (
            "ORIENTATION: UPRIGHT — height is Z. "
            "For ROUND VESSELS (pots, bowls, cups): "
            "1. Use revolve profile on XZ plane: draw outer profile from base up, then inner profile down. "
            "   profile = cq.Workplane('XZ').moveTo(0,0).lineTo(base_r,0).spline(...).lineTo(0,H).close().revolve(360) "
            "2. Hollow with shell or cut an inner revolution solid. "
            "3. Add handle: C-shape sweep or extruded profile on the side, with air gap from body. "
            "4. Add pour spout: small triangular cut at rim. "
            "5. Add foot ring: shallow annular cut on bottom. "
            "For FLAT ITEMS (cutting boards, trays): "
            "1. Use box or rounded-rectangle extrusion. "
            "2. Add juice groove (shallow rectangular channel inset from edges). "
            "3. Add handle cutout or grip indent at one end. "
            "4. Fillet all edges generously (food-safe = no sharp internal corners ≥ R2mm)."
        ),
        "recognition_features": (
            "1. ROUND PROFILE: Most cookware is circular — revolution geometry. "
            "2. HANDLE WITH GAP: Handle must have visible air space between it and the hot body. "
            "3. POUR SPOUT: Small spout on rim of pots/pans. "
            "4. FLAT BOTTOM: Stable base with foot ring or flat ground contact. "
            "5. RIM LIP: Slightly thickened or rolled rim at the top opening."
        )
    },

    "Jewelry & Accessories": {
        "visual_profile": (
            "OVERALL FORM: Small-scale items (10-80mm) with high detail density. "
            "Rings: torus or revolution profile, 2-4mm band width, inner diameter ~18mm. "
            "Pendants: flat or slightly domed disc/shape, 20-40mm, with bail loop at top. "
            "Bracelets: open or closed torus, 60-70mm inner diameter. "
            "Earrings: small lightweight shapes 10-30mm, with post or hook attachment. "
            "SURFACE: Smooth polished faces with sharp facet edges OR organic flowing curves. "
            "DETAIL SCALE: Features as small as 0.3-0.5mm (prong settings, engravings)."
        ),
        "build_strategy": (
            "ORIENTATION: Flat jewelry (pendants, brooches) lies flat — thickness is Z. "
            "Rings stand upright — finger-hole axis is Z. "
            "For RINGS: "
            "1. Create torus or revolution profile for the band. "
            "2. Add setting: raised platform or bezel cup on top of band. "
            "3. Add prongs: small cylinders or cones around the setting. "
            "4. Add engraving: text or pattern cut into inner or outer surface. "
            "For PENDANTS: "
            "1. Create base shape (disc, heart, star, cross) via extrude or loft. "
            "2. Add bail (loop for chain) at top: torus section or through-hole. "
            "3. Add surface detail: facets, texture, inset stones (cylinder cuts). "
            "4. Scale matters: keep dimensions in 15-40mm range."
        ),
        "recognition_features": (
            "1. SMALL SCALE: Jewelry dimensions are 10-80mm — not furniture-scale. "
            "2. BAIL/ATTACHMENT: Pendants have a loop or hole for chain/wire. "
            "3. SMOOTH SURFACES: Polished faces with intentional edge treatments. "
            "4. SYMMETRY: Most jewelry is symmetrical about at least one axis. "
            "5. WEARABILITY: Must have comfortable contact surfaces (no sharp edges on skin side)."
        )
    },

    "Toys & Games": {
        "visual_profile": (
            "OVERALL FORM: Toys have exaggerated proportions — larger heads, simpler geometry, "
            "bright colors implied by surface segmentation. "
            "Action figures: 100-150mm tall, 5-7 head-heights proportion. "
            "Building blocks: precise dimensional multiples (8mm grid for LEGO-compatible). "
            "Vehicles: simplified real-world shapes with reduced detail. "
            "Board game pieces: small (20-40mm), simple geometry, weighted base. "
            "SAFETY: All edges heavily filleted (R≥1mm), no small detachable parts, "
            "no sharp points, no thin fragile sections."
        ),
        "build_strategy": (
            "ORIENTATION: UPRIGHT — height is Z. "
            "For FIGURES/CHARACTERS: "
            "1. Build each body section as a simple primitive (sphere, cylinder, ellipsoid). "
            "2. Union all parts together with generous fillets at joints. "
            "3. Cut simple features (eyes = shallow cylinder cuts, mouth = arc groove). "
            "4. Add a weighted base (wider cylinder at feet). "
            "For BUILDING BLOCKS: "
            "1. Box with precise grid dimensions (e.g., 8mm multiples). "
            "2. Add studs on top: cylinders protruding from top face in grid pattern. "
            "3. Add tubes on bottom: hollow cylinders on underside for clutch mechanism. "
            "4. Fillet all edges 0.2-0.5mm (injection mold style). "
            "For VEHICLES: "
            "1. Main body as a lofted or box shape with rounded edges. "
            "2. Wheels: cylinders or toroid shapes at axle positions. "
            "3. Cabin/cockpit: cut or raised section. "
            "4. Simplified details: headlight circles, grille lines, window cuts."
        ),
        "recognition_features": (
            "1. CHILD-SAFE EDGES: ALL edges filleted ≥1mm — no exceptions. "
            "2. SIMPLIFIED GEOMETRY: Real-world shapes reduced to 3-5 key features. "
            "3. CHUNKY PROPORTIONS: Thicker walls, wider bases than real products. "
            "4. PLAY FEATURES: Moving parts, attachment points, stacking elements. "
            "5. WEIGHTED BASE: Bottom is heavier/wider for stability."
        )
    },

    "Lighting & Lamps": {
        "visual_profile": (
            "OVERALL FORM: Lamps consist of 3 zones: BASE (weighted, stable), "
            "BODY/STEM (structural, carries wiring), SHADE/DIFFUSER (shapes the light). "
            "Desk lamp: articulated arm + conical/cylindrical shade. "
            "Floor lamp: tall stem (1200-1800mm) + wide shade on top. "
            "Pendant lamp: hanging shade, no base on ground. "
            "Wall sconce: bracket mount + shade projecting from wall. "
            "SHADE SHAPES: Cone (empire shade), cylinder (drum shade), dome, lantern. "
            "CABLE: Entry hole in base or back, routed through hollow stem."
        ),
        "build_strategy": (
            "ORIENTATION: UPRIGHT — height is Z. "
            "1. BASE: Heavy weighted disc or box at Z=0. Add anti-slip rubber feet. "
            "   base = cq.Workplane('XY').cylinder(base_h, base_r) "
            "2. STEM: Cylinder or tube rising from base. Hollow for wiring. "
            "   stem = cq.Workplane('XY').circle(stem_r).circle(stem_r - wall).extrude(stem_h) "
            "3. SHADE: Loft or revolution for conical/dome shapes at top of stem. "
            "   For cone shade: loft from large circle at bottom to small circle at top. "
            "   For dome shade: half-sphere, hollowed. "
            "   For drum shade: cylinder, hollowed. "
            "4. SOCKET RECESS: Cylindrical hole in center of shade for bulb. "
            "5. SWITCH: Small cylinder or box on stem or cable. "
            "6. CABLE HOLE: Through-hole in base for cord exit."
        ),
        "recognition_features": (
            "1. THREE-ZONE STRUCTURE: Distinct base, body/stem, and shade sections. "
            "2. SHADE SHAPE: The shade defines the lamp's character — cone, drum, dome, or lantern. "
            "3. WEIGHTED BASE: Base is visually heavier/wider than the stem for stability. "
            "4. CABLE MANAGEMENT: Hole for cord exit, typically in base or back. "
            "5. BULB SOCKET: Visible or implied socket area inside the shade."
        )
    },

    "Pipes & Plumbing": {
        "visual_profile": (
            "OVERALL FORM: Cylindrical tubes with various end connections and fittings. "
            "Straight pipe: uniform cylinder. Elbow: 90° or 45° swept tube. "
            "Tee: T-shaped junction of three tubes. Cross: 4-way junction. "
            "Reducer: cone transitioning between two diameters. "
            "Valve: body with handle/wheel on top, pipe connections on sides. "
            "Flanges: flat disc with bolt circle at pipe ends. "
            "WALL THICKNESS: Standard schedule pipes have specific wall thicknesses "
            "(Schedule 40: ~3-5mm wall for 25-50mm nominal bore)."
        ),
        "build_strategy": (
            "For STRAIGHT PIPE: "
            "1. Outer cylinder - inner cylinder = hollow tube. "
            "For ELBOW: "
            "1. Draw circle profile. "
            "2. Sweep along 90° arc path on XZ plane. "
            "For TEE FITTING: "
            "1. Main horizontal pipe (cylinder - hollow). "
            "2. Branch pipe (cylinder - hollow) intersecting at 90°. "
            "3. Union and clean up the junction. "
            "For VALVE: "
            "1. Body: box or cylinder with pipe stubs on two sides. "
            "2. Bore: through-hole connecting the two pipe stubs. "
            "3. Handle: wheel (torus + spokes) or lever on top. "
            "4. Stem: cylinder connecting handle to bore."
        ),
        "recognition_features": (
            "1. CIRCULAR CROSS-SECTION: Pipes are always round in cross-section. "
            "2. HOLLOW: Pipes have consistent wall thickness throughout. "
            "3. END CONNECTIONS: Threaded ends, flanges, or socket joints. "
            "4. SMOOTH BENDS: Elbows are smooth curves, not sharp angles. "
            "5. JUNCTION BLENDING: Where branches meet, geometry blends smoothly."
        )
    },

    "Containers & Packaging": {
        "visual_profile": (
            "OVERALL FORM: Boxes, bins, cases with lids — designed to hold and protect contents. "
            "Shipping box: rectangular with flaps. Storage bin: tapered walls for nesting. "
            "Toolbox: hinged lid with handle on top. Pelican-style case: rugged with latches. "
            "WALLS: Slightly tapered (1-3°) for stackability and mold release. "
            "LID: Overlapping lip, gasket groove for seal, hinge on one side. "
            "HANDLE: Folding bail handle on top, or side grip recesses. "
            "INTERIOR: Dividers, foam channels, or compartment walls."
        ),
        "build_strategy": (
            "ORIENTATION: UPRIGHT — height is Z (opening at top). "
            "1. OUTER SHELL: box or lofted tapered shape. "
            "2. HOLLOW: shell or manual cavity cut. "
            "3. LID: separate box that overlaps the rim by 2-3mm. "
            "   Add tongue-and-groove or gasket groove for sealing. "
            "4. LATCHES: Raised clips on front face. "
            "5. HINGES: Cylindrical bosses on back edge for pin hinge. "
            "6. HANDLE: Bail handle = half-torus on top. Side grips = recessed cuts. "
            "7. STACKING: Add rim at top and matching recess at bottom. "
            "8. DIVIDERS: Internal walls at regular intervals. "
            "9. DRAIN HOLES: Small holes in bottom corners for outdoor containers."
        ),
        "recognition_features": (
            "1. OPENING MECHANISM: Lid, flap, or hinged cover at top. "
            "2. HANDLE/GRIP: Way to carry or hold the container. "
            "3. STACKING FEATURES: Rim + recess for nesting or stacking. "
            "4. TAPERED WALLS: Slight draft angle for nestability. "
            "5. REINFORCED CORNERS: Thicker material or ribs at stress points."
        )
    },

    "Musical Instruments": {
        "visual_profile": (
            "OVERALL FORM varies dramatically by instrument type: "
            "GUITAR: figure-8 body (waist), flat back, long neck with frets. ~1000mm total. "
            "DRUM: cylinder with tensioned head. VIOLIN: curvy body with f-holes. "
            "PIANO KEY: long rectangular lever. TRUMPET: coiled tubing with bell. "
            "COMMON: Sound holes/ports for acoustic instruments. Tuning pegs at headstock. "
            "Finger position markers. String anchor points. "
            "SURFACE: Smooth acoustic surfaces with minimal sharp edges."
        ),
        "build_strategy": (
            "GUITAR BODY: "
            "1. Use loft or spline extrusion for the figure-8 body shape. "
            "2. Hollow with shell for the resonance chamber. "
            "3. Add sound hole: circular cut on front face. "
            "4. Add bridge: raised rectangular pad near bottom. "
            "5. Add neck: long tapered box extending from upper bout. "
            "6. Add headstock: wider section at end of neck with tuning peg holes. "
            "DRUM: "
            "1. Cylinder for shell. "
            "2. Add rim (hoop) at top: torus or flattened cylinder slightly larger than shell. "
            "3. Add lug casings: small boxes or cylinders around the shell perimeter. "
            "4. Add tension rods: small cylinders from lugs to rim."
        ),
        "recognition_features": (
            "1. SOUND PRODUCTION FEATURE: Sound hole, bell, resonance chamber, or vibrating surface. "
            "2. PLAYING INTERFACE: Strings, keys, pads, mouthpiece — the part the musician touches. "
            "3. TUNING MECHANISM: Pegs, keys, or tension hardware for pitch adjustment. "
            "4. ACOUSTIC SHAPE: Body shape optimized for sound (curves, chambers, ports). "
            "5. PROPORTIONS: Instrument-specific ratios that make it recognizable."
        )
    },

    "Medical & Scientific": {
        "visual_profile": (
            "OVERALL FORM: Precision instruments with clean, clinical aesthetics. "
            "Lab equipment: beakers (cylinder + pour spout), flasks (sphere + narrow neck), "
            "test tubes (cylinder + hemispherical bottom), microscope (complex multi-stage). "
            "Medical devices: ergonomic grips, clear markings, sterile-friendly shapes. "
            "SURFACE: Ultra-smooth, no crevices where contaminants could accumulate. "
            "MARKINGS: Graduated measurement lines, unit labels. "
            "MATERIALS IMPLICATION: Stainless steel or glass — minimal fillets, precise edges."
        ),
        "build_strategy": (
            "For BEAKERS/FLASKS: "
            "1. Revolution profile for the main vessel shape. "
            "2. Pour spout: small triangular indent at rim. "
            "3. Graduated markings: array of shallow line cuts at measured intervals. "
            "4. Foot ring on bottom for stability. "
            "For SYRINGES: "
            "1. Main barrel: cylinder, slightly tapered. "
            "2. Plunger: cylinder with disc flange at back. "
            "3. Nozzle: cone at front end (Luer fitting). "
            "4. Finger flanges: flat wings at barrel end. "
            "For TEST TUBE RACKS: "
            "1. Base plate with array of holes sized for tubes. "
            "2. Support posts at corners. "
            "3. Label slots on front face."
        ),
        "recognition_features": (
            "1. PRECISION GEOMETRY: Clean, exact dimensions — no approximate shapes. "
            "2. GRADUATED MARKINGS: Measurement lines at regular intervals. "
            "3. CLINICAL AESTHETICS: Smooth, crevice-free surfaces. "
            "4. FUNCTIONAL ATTACHMENTS: Pour spouts, nozzles, connectors. "
            "5. STABILITY FEATURES: Wide base, foot ring, or rack stand."
        )
    },

    "Sports Equipment": {
        "visual_profile": (
            "OVERALL FORM: Ergonomic shapes designed for human interaction during physical activity. "
            "Dumbbells: two weighted discs connected by a grip bar. "
            "Rackets: oval head with string area + long handle. "
            "Helmets: dome shell with interior padding, visor/face opening. "
            "Balls: spheres with surface texture (dimples, panels, seams). "
            "Bats/clubs: tapered cylinder — thick barrel end, thin handle. "
            "GRIP: Contoured handle sections with texture for secure hold during exertion. "
            "PROTECTION: Helmets/guards have impact-absorbing shell + comfort padding cutouts."
        ),
        "build_strategy": (
            "For DUMBBELLS: "
            "1. Handle bar: cylinder at center height. "
            "2. Weight plates: cylinders or rounded discs at each end. "
            "3. Knurling on handle: grip texture pattern. "
            "4. Collar rings between handle and weights. "
            "For HELMETS: "
            "1. Outer shell: half-sphere or ellipsoid, cut flat at bottom. "
            "2. Face opening: large cut on front-lower area. "
            "3. Ventilation holes: array of oval cuts on top. "
            "4. Visor brim: thin protruding shelf above face opening. "
            "5. Chin strap attachment points: small cylinders on sides near bottom edge. "
            "For RACKETS: "
            "1. Head: elliptical frame (outer ellipse - inner ellipse, extruded). "
            "2. String area: grid of thin cuts inside the frame. "
            "3. Throat: tapered transition from head to shaft. "
            "4. Shaft: long cylinder or rounded rectangle. "
            "5. Handle: slightly wider section with grip texture."
        ),
        "recognition_features": (
            "1. ERGONOMIC GRIP: Handle shaped for human hand with texture. "
            "2. SPORT-SPECIFIC SHAPE: Shape immediately identifies the sport. "
            "3. IMPACT/PERFORMANCE ZONES: Distinct areas for hitting, catching, protecting. "
            "4. LIGHTWEIGHT FEATURES: Holes, cutouts, or thin sections for weight reduction. "
            "5. SAFETY ELEMENTS: Rounded edges, padding recesses, ventilation."
        )
    },
}

# Merge expanded categories into main dictionary
CATEGORY_VISUAL_KNOWLEDGE.update(CATEGORY_VISUAL_KNOWLEDGE_EXPANDED)


# ═══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ═══════════════════════════════════════════════════════════════════════════════

def get_visual_knowledge(product_name: str, category: str) -> Optional[Dict[str, str]]:
    """
    Get visual knowledge for a product — checks product-specific overrides first,
    then falls back to category-level knowledge.

    Returns a dict with keys: visual_profile, build_strategy, recognition_features
    Any of these may be overridden at the product level while others use category defaults.
    """
    result: Dict[str, str] = {}

    # Start with category defaults
    cat_knowledge = CATEGORY_VISUAL_KNOWLEDGE.get(category, {})
    if cat_knowledge:
        result.update(cat_knowledge)

    # Apply product-specific overrides (they win over category)
    prod_knowledge = PRODUCT_VISUAL_OVERRIDES.get(product_name, {})
    if prod_knowledge:
        result.update(prod_knowledge)

    return result if result else None


def format_visual_knowledge(product_name: str, category: str) -> str:
    """
    Format visual knowledge into a text block for injection into Claude's prompt.
    Returns empty string if no knowledge available.
    """
    knowledge = get_visual_knowledge(product_name, category)
    if not knowledge:
        return ""

    lines = [
        "",
        "  🎨 VISUAL & CONSTRUCTION KNOWLEDGE:",
        ""
    ]

    if "visual_profile" in knowledge:
        lines.append("  WHAT IT LOOKS LIKE (follow this visual guide):")
        # Wrap long text for readability
        profile = knowledge["visual_profile"]
        lines.append(f"    {profile}")
        lines.append("")

    if "build_strategy" in knowledge:
        lines.append("  HOW TO BUILD IT IN CADQUERY (follow this recipe):")
        strategy = knowledge["build_strategy"]
        lines.append(f"    {strategy}")
        lines.append("")

    if "position_map" in knowledge:
        lines.append("  📍 FEATURE POSITION MAP (use these EXACT axis references):")
        pos_map = knowledge["position_map"]
        lines.append(f"    {pos_map}")
        lines.append("")

    if "recognition_features" in knowledge:
        lines.append("  ⚠️ RECOGNITION FEATURES (these MUST be correct or the model is wrong):")
        features = knowledge["recognition_features"]
        lines.append(f"    {features}")
        lines.append("")

    return "\n".join(lines)
