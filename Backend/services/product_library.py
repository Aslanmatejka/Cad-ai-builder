"""
Product Library — Real-World Product Dimensions & Design Specifications

A searchable knowledge base of actual product measurements, features, and
construction guidance. Matched against user prompts so the AI can generate
accurate CAD models of real products.
"""

from typing import Dict, List, Any, Optional
import re
from services.product_visual_knowledge import format_visual_knowledge

# ═══════════════════════════════════════════════════════════════════════════════
# PRODUCT DATABASE
# ═══════════════════════════════════════════════════════════════════════════════
# Each entry has:
#   keywords    — terms that trigger this entry (matched against user prompt)
#   name        — display name
#   category    — grouping
#   dimensions  — real-world measurements in mm
#   features    — list of design features to include
#   notes       — construction guidance for the AI
# ═══════════════════════════════════════════════════════════════════════════════

PRODUCTS: List[Dict[str, Any]] = [

    # ─────────────────────────────────────────────────────────────────────────
    #  SMARTPHONES & CASES
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["iphone 16 pro max", "iphone 16pro max"],
        "name": "Apple iPhone 16 Pro Max",
        "category": "Smartphones",
        "dimensions": {
            "length": 163.0, "width": 77.6, "thickness": 8.25,
            "corner_radius": 9.0, "screen_radius": 3.5,
            "weight_grams": 227
        },
        "features": [
            "Titanium frame with flat edges",
            "Camera island: 3 lenses in triangular layout, island ~37×37mm, top-left of back",
            "Dynamic Island: pill-shaped cutout ~36×12mm centered at top of front face",
            "Action button on upper-left side: 9×3mm",
            "Volume buttons on left side: two separate 12×3mm buttons",
            "Side button (power) on right side: 18×3mm",
            "USB-C port bottom-center: 8.5×3mm opening",
            "Speaker grille: left of USB-C, ~15×2mm with micro-holes",
            "Microphone: right of USB-C, ~2×2mm",
            "SIM tray on left side below volume buttons"
        ],
        "notes": "Flat-edge design (no rounded sides like older models). Camera island has rounded-rect shape with 3 large lens circles (~15mm diameter each) and one smaller sensor."
    },
    {
        "keywords": ["iphone 16 pro"],
        "name": "Apple iPhone 16 Pro",
        "category": "Smartphones",
        "dimensions": {
            "length": 149.6, "width": 71.5, "thickness": 8.25,
            "corner_radius": 9.0
        },
        "features": [
            "Same design language as 16 Pro Max but smaller",
            "Titanium frame with flat edges",
            "Triple camera in triangular layout, island ~35×35mm",
            "Dynamic Island top-center",
            "Action button upper-left, volume buttons left, side button right",
            "USB-C port bottom-center with speaker grille"
        ],
        "notes": "Identical design to Pro Max, just scaled down."
    },
    {
        "keywords": ["iphone 16"],
        "name": "Apple iPhone 16",
        "category": "Smartphones",
        "dimensions": {
            "length": 147.6, "width": 71.6, "thickness": 7.80,
            "corner_radius": 9.0
        },
        "features": [
            "Aluminum frame with flat edges",
            "Dual camera: vertical arrangement on back, island ~30×55mm",
            "Dynamic Island top-center",
            "Action button upper-left, volume buttons left, side button right",
            "USB-C port bottom-center"
        ],
        "notes": "Dual camera in vertical pill shape, not triangular like Pro models."
    },
    {
        "keywords": ["iphone 15 pro max"],
        "name": "Apple iPhone 15 Pro Max",
        "category": "Smartphones",
        "dimensions": {
            "length": 159.9, "width": 76.7, "thickness": 8.25,
            "corner_radius": 8.5
        },
        "features": [
            "Titanium frame, flat edges, rounded internal corners",
            "Triple camera island ~36×36mm, top-left",
            "Dynamic Island ~36×12mm",
            "Action button replaces mute switch",
            "USB-C port bottom"
        ],
        "notes": "First iPhone with titanium. Action button replaced the mute toggle."
    },
    {
        "keywords": ["iphone 15 pro"],
        "name": "Apple iPhone 15 Pro",
        "category": "Smartphones",
        "dimensions": {
            "length": 146.6, "width": 70.6, "thickness": 8.25,
            "corner_radius": 8.5
        },
        "features": [
            "Titanium frame, flat edges",
            "Triple camera island ~35×35mm",
            "Dynamic Island, Action button, USB-C"
        ],
        "notes": "Same design as 15 Pro Max, smaller form factor."
    },
    {
        "keywords": ["iphone 15"],
        "name": "Apple iPhone 15",
        "category": "Smartphones",
        "dimensions": {
            "length": 147.6, "width": 71.6, "thickness": 7.80,
            "corner_radius": 8.5
        },
        "features": [
            "Aluminum frame, rounded edges with contoured feel",
            "Dual camera vertical layout on back",
            "Dynamic Island, USB-C port"
        ],
        "notes": "First standard iPhone with Dynamic Island and USB-C."
    },
    {
        "keywords": ["iphone 14 pro max"],
        "name": "Apple iPhone 14 Pro Max",
        "category": "Smartphones",
        "dimensions": {
            "length": 160.7, "width": 77.6, "thickness": 7.85,
            "corner_radius": 8.5
        },
        "features": [
            "Stainless steel frame, flat edges",
            "Triple camera island ~36×36mm",
            "Dynamic Island (first model to have it)",
            "Lightning port bottom-center",
            "Mute toggle switch upper-left side"
        ],
        "notes": "Last Lightning Pro model. Mute toggle instead of action button."
    },
    {
        "keywords": ["iphone 14"],
        "name": "Apple iPhone 14",
        "category": "Smartphones",
        "dimensions": {
            "length": 146.7, "width": 71.5, "thickness": 7.80,
            "corner_radius": 8.0
        },
        "features": [
            "Aluminum frame, flat edges",
            "Dual camera diagonal layout",
            "Notch (not Dynamic Island)",
            "Lightning port"
        ],
        "notes": "Standard notch, not Dynamic Island. Lightning, not USB-C."
    },
    {
        "keywords": ["iphone 13"],
        "name": "Apple iPhone 13",
        "category": "Smartphones",
        "dimensions": {
            "length": 146.7, "width": 71.5, "thickness": 7.65,
            "corner_radius": 7.5
        },
        "features": [
            "Aluminum frame, flat edges",
            "Dual camera diagonal layout on back",
            "Smaller notch than iPhone 12",
            "Lightning port bottom-center"
        ],
        "notes": "Diagonal dual-camera arrangement. Smaller notch than predecessor."
    },
    {
        "keywords": ["iphone 12"],
        "name": "Apple iPhone 12",
        "category": "Smartphones",
        "dimensions": {
            "length": 146.7, "width": 71.5, "thickness": 7.40,
            "corner_radius": 7.5
        },
        "features": [
            "Aluminum frame, flat edges (reintroduced from iPhone 5 era)",
            "Dual camera vertical layout on back",
            "Wide notch on front",
            "Lightning port bottom-center"
        ],
        "notes": "First flat-edge iPhone since the 5S. Vertical dual camera."
    },
    {
        "keywords": ["iphone 11 pro max"],
        "name": "Apple iPhone 11 Pro Max",
        "category": "Smartphones",
        "dimensions": {
            "length": 158.0, "width": 77.8, "thickness": 8.10,
            "corner_radius": 8.0
        },
        "features": [
            "Stainless steel frame, ROUNDED edges",
            "Triple camera in square island ~36×36mm, top-left",
            "Wide notch on front",
            "Lightning port bottom-center",
            "Mute toggle, volume buttons left, side button right"
        ],
        "notes": "Rounded edge design (not flat). Square camera bump with 3 lenses in triangle + flash."
    },
    {
        "keywords": ["iphone 11 pro"],
        "name": "Apple iPhone 11 Pro",
        "category": "Smartphones",
        "dimensions": {
            "length": 144.0, "width": 71.4, "thickness": 8.10,
            "corner_radius": 8.0
        },
        "features": [
            "Stainless steel frame, rounded edges",
            "Triple camera square island, top-left",
            "Wide notch, Lightning port"
        ],
        "notes": "Same design as 11 Pro Max, smaller body."
    },
    {
        "keywords": ["iphone 11"],
        "name": "Apple iPhone 11",
        "category": "Smartphones",
        "dimensions": {
            "length": 150.9, "width": 75.7, "thickness": 8.30,
            "corner_radius": 8.0
        },
        "features": [
            "Aluminum frame, rounded edges",
            "Dual camera in square island with 2 lenses, top-left",
            "Wide notch on front",
            "Lightning port bottom-center",
            "Mute toggle, volume buttons left side"
        ],
        "notes": "Rounded edges, NOT flat. Dual camera in square island (2 lenses + flash)."
    },
    {
        "keywords": ["iphone se", "iphone se 3", "iphone se 2022"],
        "name": "Apple iPhone SE (3rd gen)",
        "category": "Smartphones",
        "dimensions": {
            "length": 138.4, "width": 67.3, "thickness": 7.3,
            "corner_radius": 7.0
        },
        "features": [
            "Aluminum frame, rounded edges (iPhone 8 body)",
            "Single camera on back, top-left",
            "Home button with Touch ID on front",
            "Lightning port, 3.5mm-like speaker grille"
        ],
        "notes": "Classic iPhone design with home button. Single rear camera."
    },
    {
        "keywords": ["samsung galaxy s24 ultra", "galaxy s24 ultra", "s24 ultra"],
        "name": "Samsung Galaxy S24 Ultra",
        "category": "Smartphones",
        "dimensions": {
            "length": 162.3, "width": 79.0, "thickness": 8.6,
            "corner_radius": 3.0
        },
        "features": [
            "Titanium frame with FLAT edges and sharp corners (nearly rectangular)",
            "Quad camera array: vertical row on upper-left back, NOT in a single island",
            "Individual circular lens rings: 2 large (~15mm), 2 smaller (~10mm), plus flash",
            "S Pen silo: bottom-left, ~5×3mm slot",
            "USB-C port bottom-center",
            "Volume + power buttons on right side",
            "Centered front punch-hole camera ~4mm diameter"
        ],
        "notes": "Very squared-off corners (small radius ~3mm). No camera island — each lens has its own raised ring. Includes S Pen slot."
    },
    {
        "keywords": ["samsung galaxy s24", "galaxy s24", "s24"],
        "name": "Samsung Galaxy S24",
        "category": "Smartphones",
        "dimensions": {
            "length": 147.0, "width": 70.6, "thickness": 7.6,
            "corner_radius": 4.0
        },
        "features": [
            "Aluminum frame, flat edges",
            "Triple camera: vertical row upper-left, individual lens rings",
            "USB-C bottom, front punch-hole camera center"
        ],
        "notes": "Flat edge design with individual camera lens rings (no island)."
    },
    {
        "keywords": ["samsung galaxy s23 ultra", "galaxy s23 ultra", "s23 ultra"],
        "name": "Samsung Galaxy S23 Ultra",
        "category": "Smartphones",
        "dimensions": {
            "length": 163.4, "width": 78.1, "thickness": 8.9,
            "corner_radius": 3.5
        },
        "features": [
            "Armor aluminum frame, flat edges, squared corners",
            "Quad camera individual lens rings on back",
            "S Pen silo bottom-left",
            "USB-C port, front punch-hole"
        ],
        "notes": "Very similar to S24 Ultra but slightly thicker with more rounded lens rings."
    },
    {
        "keywords": ["google pixel 9 pro", "pixel 9 pro"],
        "name": "Google Pixel 9 Pro",
        "category": "Smartphones",
        "dimensions": {
            "length": 152.8, "width": 72.0, "thickness": 8.5,
            "corner_radius": 6.5
        },
        "features": [
            "Polished aluminum frame, flat sides, rounded back edges",
            "Camera bar: horizontal pill-shaped island spanning full width of upper back ~68×18mm",
            "Triple cameras inside the bar with flash",
            "USB-C bottom, front punch-hole camera"
        ],
        "notes": "Signature Pixel camera bar — a raised horizontal strip across the full back width near the top."
    },
    {
        "keywords": ["google pixel 9", "pixel 9"],
        "name": "Google Pixel 9",
        "category": "Smartphones",
        "dimensions": {
            "length": 152.8, "width": 72.0, "thickness": 8.5,
            "corner_radius": 6.5
        },
        "features": [
            "Aluminum frame, flat sides",
            "Camera bar: horizontal raised island with dual cameras",
            "USB-C bottom, front punch-hole"
        ],
        "notes": "Same body as Pixel 9 Pro but dual camera in the bar."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  PHONE CASES
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["iphone 16 pro max case", "case for iphone 16 pro max"],
        "name": "iPhone 16 Pro Max Case",
        "category": "Phone Cases",
        "dimensions": {
            "length": 165.0, "width": 79.6, "height": 11.0,
            "wall_thickness": 1.5, "corner_radius": 10.0,
            "lip_height": 1.0
        },
        "features": [
            "Shell body ~1.5mm wall, open top (screen side)",
            "Camera island cutout: rounded rectangle ~39×39mm, top-left of back",
            "Raised lip around screen edge: ~1mm above phone surface",
            "Raised lip around camera cutout: ~0.5mm",
            "Side button cutouts: action button (9×3.5mm), volume x2, power button",
            "Bottom cutout: USB-C opening ~12×5mm centered, speaker holes",
            "Mute/action button cutout on upper-left",
            "Interior ribbing or microfiber-texture pattern (optional)"
        ],
        "notes": "Case must be ~2mm larger than phone in each dimension. Open top for screen. Camera cutout must be precisely positioned. Button areas can be cutouts or flexible membrane sections."
    },
    {
        "keywords": ["iphone 15 pro max case", "case for iphone 15 pro max"],
        "name": "iPhone 15 Pro Max Case",
        "category": "Phone Cases",
        "dimensions": {
            "length": 162.0, "width": 78.7, "height": 11.0,
            "wall_thickness": 1.5, "corner_radius": 9.5
        },
        "features": [
            "Shell with open top, ~1.5mm wall",
            "Camera island cutout ~38×38mm rounded-rect",
            "Screen lip ~1mm, camera lip ~0.5mm",
            "Action button cutout, volume cutouts, side button cutout",
            "USB-C + speaker cutout on bottom"
        ],
        "notes": "Similar to 16 Pro Max case but very slightly smaller."
    },
    {
        "keywords": ["iphone 11 case", "case for iphone 11", "iphone 11 phone case"],
        "name": "iPhone 11 Case",
        "category": "Phone Cases",
        "dimensions": {
            "length": 153.0, "width": 77.7, "height": 11.0,
            "wall_thickness": 1.5, "corner_radius": 9.0
        },
        "features": [
            "Shell with open top, rounded back edges to match phone",
            "Square camera island cutout ~28×28mm with rounded corners, top-left",
            "Dual camera lenses visible through cutout",
            "Raised screen lip ~1mm",
            "Mute toggle cutout (slot, not button) upper-left side",
            "Volume button cutouts (2 circles or pills) left side",
            "Side button (power) cutout right side",
            "Lightning port + speaker cutout bottom-center"
        ],
        "notes": "iPhone 11 has ROUNDED edges so the case follows that curve. Lightning port, NOT USB-C. Mute TOGGLE (physical switch), not action button."
    },
    {
        "keywords": ["samsung s24 ultra case", "galaxy s24 ultra case", "case for s24 ultra"],
        "name": "Samsung Galaxy S24 Ultra Case",
        "category": "Phone Cases",
        "dimensions": {
            "length": 164.5, "width": 81.0, "height": 11.0,
            "wall_thickness": 1.5, "corner_radius": 4.0
        },
        "features": [
            "Very squared-off corners (small radius) to match phone",
            "Individual camera lens cutouts — 4 circular holes, NOT one big island",
            "S Pen access: slot or cutout at bottom-left",
            "Screen lip ~1mm, open top",
            "Volume + power button cutouts on right side",
            "USB-C + speaker cutout bottom"
        ],
        "notes": "Nearly rectangular — the S24 Ultra is very squared off. Individual lens holes, not a unified camera island."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  TABLETS
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["ipad pro 13", "ipad pro 12.9", "ipad pro m4"],
        "name": "Apple iPad Pro 13-inch (M4)",
        "category": "Tablets",
        "dimensions": {
            "length": 281.6, "width": 215.5, "thickness": 5.1,
            "corner_radius": 12.0
        },
        "features": [
            "Ultra-thin aluminum unibody",
            "Single rear camera + LiDAR scanner top-left corner",
            "Landscape Face ID in top bezel",
            "USB-C / Thunderbolt port on short edge",
            "Magnetic Smart Connector on back (3 dots)",
            "Quad speaker grilles, one in each corner",
            "Volume buttons on the short edge (top in portrait)",
            "Apple Pencil magnetic attachment along one long edge"
        ],
        "notes": "Thinnest Apple product. Camera bump is minimal. Flat edges all around."
    },
    {
        "keywords": ["ipad air", "ipad air m2", "ipad air 13"],
        "name": "Apple iPad Air 13-inch (M2)",
        "category": "Tablets",
        "dimensions": {
            "length": 281.6, "width": 214.9, "thickness": 6.1,
            "corner_radius": 11.0
        },
        "features": [
            "Aluminum unibody, flat edges",
            "Single rear camera top-left, no LiDAR",
            "Touch ID in power button (top edge)",
            "USB-C port on short edge",
            "Smart Connector on back"
        ],
        "notes": "Similar to iPad Pro but slightly thicker. Touch ID in button, not Face ID."
    },
    {
        "keywords": ["ipad", "ipad 10", "ipad 10th gen"],
        "name": "Apple iPad (10th gen)",
        "category": "Tablets",
        "dimensions": {
            "length": 248.6, "width": 179.5, "thickness": 7.0,
            "corner_radius": 10.0
        },
        "features": [
            "Aluminum body, flat edges",
            "Single rear camera with landscape orientation",
            "Touch ID in power button",
            "USB-C port",
            "Landscape front camera centered on long edge"
        ],
        "notes": "Colorful, flat-edge redesign. USB-C, no Lightning."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  LAPTOPS
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["macbook pro 16", "macbook 16"],
        "name": "Apple MacBook Pro 16-inch (M3/M4)",
        "category": "Laptops",
        "dimensions": {
            "length": 355.7, "width": 248.1, "thickness_closed": 16.8,
            "corner_radius": 8.0, "screen_bezel": 5.0
        },
        "features": [
            "Aluminum unibody, flat bottom with 4 rubber feet",
            "Full keyboard with function row + Touch ID key (top-right)",
            "Large trackpad below keyboard: ~160×100mm",
            "Notch in top screen bezel for camera",
            "MagSafe port (left), 2 Thunderbolt (left), HDMI (right), SD card slot (right), headphone jack (right)",
            "Speaker grilles flanking keyboard",
            "Hinge visible from rear"
        ],
        "notes": "When closed: slab with rounded edges. The keyboard area and port layout are distinctive. Bottom has regulatory text area."
    },
    {
        "keywords": ["macbook pro 14", "macbook 14"],
        "name": "Apple MacBook Pro 14-inch",
        "category": "Laptops",
        "dimensions": {
            "length": 312.6, "width": 221.2, "thickness_closed": 15.5,
            "corner_radius": 7.0
        },
        "features": [
            "Same design as 16-inch but smaller",
            "Same port layout: MagSafe, Thunderbolt, HDMI, SD, headphone",
            "Screen notch for camera",
            "Full keyboard with Touch ID"
        ],
        "notes": "Scaled-down 16-inch design. Same port selection."
    },
    {
        "keywords": ["macbook air 15", "macbook air"],
        "name": "Apple MacBook Air 15-inch (M3/M4)",
        "category": "Laptops",
        "dimensions": {
            "length": 340.4, "width": 237.6, "thickness_closed": 11.5,
            "corner_radius": 7.0
        },
        "features": [
            "Ultra-thin aluminum unibody, uniform thickness (no wedge)",
            "MagSafe (left), 2 Thunderbolt (left), headphone jack (right)",
            "No HDMI, no SD card slot",
            "Full keyboard with function row + Touch ID",
            "Large trackpad",
            "No fan — completely silent"
        ],
        "notes": "Noticeably thinner than Pro. No active cooling so no visible vents. Flat profile, not wedge-shaped."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  AUDIO
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["airpods pro", "airpods pro 2"],
        "name": "Apple AirPods Pro (2nd gen)",
        "category": "Audio",
        "dimensions": {
            "earbud_length": 30.9, "earbud_width": 21.8, "earbud_height": 24.0,
            "stem_length": 14.0, "stem_width": 5.5,
            "case_length": 45.2, "case_width": 60.6, "case_height": 21.7
        },
        "features": [
            "In-ear design with silicone tip",
            "Short stem below earbud body",
            "Force sensor on stem for controls",
            "Speaker mesh on outer face",
            "Charging case: rounded rectangle with hinge on long edge, speaker slot, lanyard loop, Lightning/USB-C on bottom"
        ],
        "notes": "The case is the easier CAD target. Rounded-rect body, hinge at top, LED on front, port on bottom."
    },
    {
        "keywords": ["airpods", "airpods 3", "airpods 4"],
        "name": "Apple AirPods (4th gen / AirPods 3)",
        "category": "Audio",
        "dimensions": {
            "earbud_length": 30.2, "earbud_width": 18.3, "earbud_height": 18.3,
            "stem_length": 16.0, "stem_width": 5.0,
            "case_length": 46.4, "case_width": 50.4, "case_height": 21.4
        },
        "features": [
            "Open-ear (no silicone tip), contoured to fit ear",
            "Longer stem than AirPods Pro",
            "Optical sensors on inner face",
            "Case: rounded, wider than tall, USB-C on bottom"
        ],
        "notes": "Open-ear design — no removable silicone tip unlike Pro."
    },
    {
        "keywords": ["airpods max"],
        "name": "Apple AirPods Max",
        "category": "Audio",
        "dimensions": {
            "headband_width": 185.0, "headband_height": 65.0,
            "ear_cup_height": 82.0, "ear_cup_width": 67.0, "ear_cup_depth": 50.0
        },
        "features": [
            "Over-ear headphones with mesh headband (not padded)",
            "Circular ear cups with full-size cushions",
            "Digital Crown on right ear cup (scroll wheel ~12mm)",
            "Noise control button on right ear cup",
            "Telescoping stainless steel arms connecting headband to cups",
            "Lightning/USB-C port on bottom of right ear cup"
        ],
        "notes": "Distinctive mesh canopy headband. Metal construction. Ear cups rotate for flat fold."
    },
    {
        "keywords": ["sony wh-1000xm5", "sony xm5", "xm5 headphones"],
        "name": "Sony WH-1000XM5",
        "category": "Audio",
        "dimensions": {
            "headband_width": 195.0, "headband_height": 55.0,
            "ear_cup_height": 82.0, "ear_cup_width": 60.0, "ear_cup_depth": 45.0
        },
        "features": [
            "Over-ear headphones with padded headband",
            "Oval ear cups, smooth plastic exterior",
            "Touch panel on right ear cup",
            "Custom button + power slider on left ear cup bottom",
            "USB-C charging port on left ear cup bottom",
            "3.5mm audio jack on left ear cup",
            "Swivel hinge at headband junction (folds flat, not in)"
        ],
        "notes": "Smooth, minimal design. No visible screws. One-piece headband-to-cup arm (no telescoping)."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  GAMING
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["ps5 controller", "dualsense", "playstation controller"],
        "name": "Sony DualSense Controller (PS5)",
        "category": "Gaming",
        "dimensions": {
            "width": 160.0, "height": 66.0, "depth": 106.0,
            "grip_diameter": 38.0
        },
        "features": [
            "Two-tone design: matte + gloss sections",
            "Dual analog sticks: offset symmetric, ~14mm cap diameter, ~10mm travel",
            "D-pad (left): 4-directional cross shape ~28mm",
            "Face buttons (right): triangle/circle/cross/square ~10mm each in diamond pattern",
            "Touchpad (center): ~44×23mm clickable surface",
            "PS button below touchpad: ~8mm circle",
            "Create + Options buttons flanking touchpad: ~6×3mm each",
            "L1/R1 bumpers on top: ~35×8mm curved",
            "L2/R2 triggers below bumpers: ~35×15mm with adaptive resistance",
            "USB-C port bottom-center",
            "Speaker grille below touchpad",
            "Built-in microphone",
            "Light bar around touchpad (thin ~2mm strip)"
        ],
        "notes": "Ergonomic split body with flared grips. Two-tone aesthetic. The triggers have significant depth."
    },
    {
        "keywords": ["xbox controller", "xbox series controller", "xbox wireless controller"],
        "name": "Xbox Wireless Controller",
        "category": "Gaming",
        "dimensions": {
            "width": 153.0, "height": 62.0, "depth": 101.0,
            "grip_diameter": 36.0
        },
        "features": [
            "Asymmetric analog stick layout: left stick higher than right",
            "Left stick: offset upper-left",
            "D-pad (left, below stick): cross/faceted disc ~25mm",
            "Face buttons (right): A/B/X/Y ~9mm in diamond pattern",
            "Right stick: lower-right position",
            "Xbox/Guide button (top center): ~10mm with logo",
            "Menu + View buttons: ~5mm each flanking Guide button",
            "Share button: below Guide button ~5mm",
            "LB/RB bumpers: ~32×8mm",
            "LT/RT triggers: ~35×15mm",
            "USB-C port top-center",
            "3.5mm headphone jack bottom",
            "Textured grip on back and triggers"
        ],
        "notes": "Asymmetric stick layout is key differentiator from PlayStation. Textured dot pattern on grips and triggers."
    },
    {
        "keywords": ["nintendo switch", "switch console"],
        "name": "Nintendo Switch Console",
        "category": "Gaming",
        "dimensions": {
            "length": 239.0, "width": 102.0, "thickness": 13.9,
            "screen_size_diagonal": 162.56,
            "joycon_width": 35.9, "joycon_height": 102.0, "joycon_depth": 28.4
        },
        "features": [
            "Central tablet with rails on each side for Joy-Con attachment",
            "Left Joy-Con: analog stick (top), directional buttons, minus button, capture button",
            "Right Joy-Con: analog stick (lower), face buttons (ABXY), plus button, home button",
            "Rail grooves on each side: ~90mm long channel",
            "Kickstand on back (rectangular flap ~55×15mm)",
            "USB-C port on bottom of tablet",
            "Cartridge slot on top (hidden under cover)",
            "Volume buttons and power on top edge",
            "Headphone jack on top",
            "Air vents on top edge"
        ],
        "notes": "The central tablet body with side rail grooves is the distinctive shape. Joy-Cons can be modeled separately."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  WEARABLES
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["apple watch ultra", "apple watch ultra 2"],
        "name": "Apple Watch Ultra 2",
        "category": "Wearables",
        "dimensions": {
            "case_width": 49.0, "case_height": 44.0, "case_depth": 14.4,
            "corner_radius": 10.0, "lug_width": 22.0
        },
        "features": [
            "Titanium case, larger than standard Apple Watch",
            "Flat sapphire front crystal with raised edge guard",
            "Digital Crown (right side, upper): ~8mm diameter knob with guard bumper",
            "Side button (right side, lower): ~14×5mm",
            "Action button (left side, upper): ~10×5mm in international orange",
            "Speaker grille (left side): 3 horizontal slots",
            "Band attachment lugs: top and bottom, 22mm width"
        ],
        "notes": "More rugged/squared-off than standard Apple Watch. Raised edges around crystal. Orange accent action button."
    },
    {
        "keywords": ["apple watch", "apple watch series"],
        "name": "Apple Watch Series 10 (46mm)",
        "category": "Wearables",
        "dimensions": {
            "case_width": 46.0, "case_height": 42.0, "case_depth": 9.7,
            "corner_radius": 14.0
        },
        "features": [
            "Aluminum or stainless steel case, rounded-rectangular shape",
            "Curved front glass wrapping into case edges",
            "Digital Crown (right, upper): ~7mm",
            "Side button (right, lower): ~12×4mm",
            "Speaker/mic grille on left side",
            "Band attachment: slide-in mechanism top and bottom"
        ],
        "notes": "Very rounded — the glass curves into the case body. Thinner than Ultra."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  COMPUTER PERIPHERALS
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["magic keyboard", "apple keyboard"],
        "name": "Apple Magic Keyboard",
        "category": "Peripherals",
        "dimensions": {
            "length": 278.9, "width": 114.9, "height_rear": 10.9, "height_front": 4.0,
            "corner_radius": 6.0
        },
        "features": [
            "Ultra-thin aluminum body with slight rear-to-front taper",
            "78 keys with ~1mm travel, flat keycaps",
            "Lightning or USB-C port on rear edge for charging",
            "Power switch on rear edge (slider)",
            "Rubber base strip for grip"
        ],
        "notes": "Very low profile. The body tapers from ~11mm at the back to ~4mm at the front. Keys are almost flush."
    },
    {
        "keywords": ["magic mouse", "apple mouse"],
        "name": "Apple Magic Mouse",
        "category": "Peripherals",
        "dimensions": {
            "length": 113.5, "width": 57.1, "height": 21.6,
            "corner_radius": 15.0
        },
        "features": [
            "Smooth, continuous curved top surface (touch-sensitive)",
            "No visible buttons — entire top is multi-touch surface",
            "Low profile, almost wedge-like from side view",
            "Lightning/USB-C port on BOTTOM (infamous placement)",
            "Thin base with minimal rubber feet"
        ],
        "notes": "The top surface is one continuous curve. No scroll wheel — multi-touch surface for gestures. Port on the bottom is a notorious design choice."
    },
    {
        "keywords": ["logitech mx master", "mx master 3s", "mx master mouse"],
        "name": "Logitech MX Master 3S",
        "category": "Peripherals",
        "dimensions": {
            "length": 124.9, "width": 84.3, "height": 51.0
        },
        "features": [
            "Ergonomic sculpted right-hand design",
            "MagSpeed electromagnetic scroll wheel (steel, machined texture)",
            "Horizontal thumb scroll wheel on left side (~8mm diameter)",
            "Thumb rest area with textured surface",
            "2 thumb buttons (forward/back) on left side",
            "Left/right click buttons with subtle split line",
            "USB-C charging port on front edge",
            "Bottom: power switch, Bolt receiver storage, sensor window"
        ],
        "notes": "Highly sculpted ergonomic shape — NOT symmetrical. The thumb area has a concave rest. Side profile looks like a wave."
    },
    {
        "keywords": ["mechanical keyboard", "gaming keyboard", "60% keyboard", "custom keyboard"],
        "name": "60% Mechanical Keyboard",
        "category": "Peripherals",
        "dimensions": {
            "length": 293.0, "width": 103.0, "height_rear": 38.0, "height_front": 22.0,
            "corner_radius": 3.0
        },
        "features": [
            "Compact 61-key layout (no function row, arrows, or numpad)",
            "Aluminum or plastic case with slight rear angle",
            "Switch plate visible between keycaps",
            "USB-C port centered on rear edge",
            "Rubber feet on bottom (4-6 pads)",
            "Optional angle adjustment feet"
        ],
        "notes": "Approximately 29.3cm × 10.3cm for 60% layout. Full-size (100%) is ~44cm × 14cm. TKL (80%) is ~36cm × 14cm."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  DESK ACCESSORIES
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["laptop stand", "macbook stand", "notebook stand"],
        "name": "Laptop Stand (adjustable/fixed)",
        "category": "Desk Accessories",
        "dimensions": {
            "platform_width": 300.0, "platform_depth": 230.0, "platform_thickness": 4.0,
            "stand_height": 120.0, "tilt_angle": 15.0
        },
        "features": [
            "Angled platform with anti-slip silicone pads",
            "Open-center or slot-style ventilation cutouts",
            "Front lip/stop to prevent laptop sliding (~5mm raised edge)",
            "Cable management channel or hole at back center (~30mm diameter)",
            "Stable base (either solid feet or A-frame legs)",
            "Rounded edges for aesthetics and safety"
        ],
        "notes": "The platform should be slightly larger than a 13-14in laptop. Height elevates screen to eye level. Ventilation is important."
    },
    {
        "keywords": ["monitor riser", "monitor stand", "desk shelf"],
        "name": "Monitor Riser / Desk Shelf",
        "category": "Desk Accessories",
        "dimensions": {
            "width": 500.0, "depth": 230.0, "height": 100.0,
            "wall_thickness": 10.0, "corner_radius": 5.0
        },
        "features": [
            "Flat top surface for monitor (~500×230mm)",
            "Storage space underneath (keyboard slides under)",
            "Either solid side panels or 4 legs",
            "Optional: cable management slots in back panel",
            "Optional: drawer built into front face",
            "Non-slip pads on bottom"
        ],
        "notes": "A simple elevated platform. Width should accommodate a 24-27in monitor. Height gives ~10cm clearance for keyboard storage."
    },
    {
        "keywords": ["headphone stand", "headset stand", "headphone holder"],
        "name": "Headphone Stand",
        "category": "Desk Accessories",
        "dimensions": {
            "base_width": 120.0, "base_depth": 120.0, "base_height": 12.0,
            "stem_height": 200.0, "stem_diameter": 20.0,
            "arm_width": 80.0, "arm_depth": 30.0, "arm_rise": 30.0
        },
        "features": [
            "Weighted base for stability (circular or rectangular)",
            "Vertical stem rising from center of base",
            "Curved arm at top extending outward to hold headband",
            "Optional: cable management channel in stem",
            "Optional: USB passthrough hub in base",
            "Smooth surfaces to avoid scratching headphones"
        ],
        "notes": "The arm should extend ~60-80mm outward and rise ~30mm to cradle headband. Stem should be tall enough for over-ear headphones (~200mm)."
    },
    {
        "keywords": ["desk organizer", "desk caddy", "pen holder", "office organizer"],
        "name": "Desk Organizer",
        "category": "Desk Accessories",
        "dimensions": {
            "width": 250.0, "depth": 150.0, "height": 120.0,
            "wall_thickness": 3.0, "divider_thickness": 2.5
        },
        "features": [
            "Multiple compartments: large section for notebooks, medium for phones, small for pens",
            "Pen/pencil slots: 3-5 cylindrical holes ~12mm diameter, ~80mm deep",
            "Wide slot at back for tablets/notebooks (~15mm wide × 100mm tall)",
            "Shallow tray at front for paper clips, USB drives (~40mm × 100mm × 20mm deep)",
            "Internal dividers creating 3-5 sections",
            "Rounded edges and fillets for clean appearance",
            "Bottom with non-slip pads"
        ],
        "notes": "Think modular — multiple heights and widths for different items. Angled sections are more accessible."
    },
    {
        "keywords": ["cable organizer", "cable management", "cable clip", "cable holder"],
        "name": "Cable Management Clip/Organizer",
        "category": "Desk Accessories",
        "dimensions": {
            "width": 80.0, "depth": 40.0, "height": 25.0,
            "channel_diameter": 6.0, "num_channels": 5
        },
        "features": [
            "Multiple curved channels/slots to hold cables",
            "Each channel: C-shaped groove ~6mm wide (fits USB cables)",
            "Weighted or adhesive base to stay in place",
            "Smooth rounded entries so cables slide in easily",
            "Can hold 3-6 cables side by side"
        ],
        "notes": "Each cable channel is a C-shaped cut — wide enough to push a cable in but narrow enough to hold it. Space channels ~12-15mm apart."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  DRINKWARE & KITCHENWARE
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["coffee mug", "mug", "coffee cup"],
        "name": "Standard Coffee Mug",
        "category": "Drinkware",
        "dimensions": {
            "outer_diameter": 82.0, "height": 95.0, "wall_thickness": 4.0,
            "handle_width": 30.0, "handle_height": 65.0, "handle_thickness": 10.0,
            "base_diameter": 65.0
        },
        "features": [
            "Cylindrical or slightly tapered body (wider at top)",
            "C-shaped handle on one side, attached at two points",
            "Flat bottom with slight foot ring (~2mm raised edge)",
            "Rounded lip at top (~1.5mm radius)",
            "Interior smooth, slightly draft-angled walls"
        ],
        "notes": "Classic proportions: ~82mm top diameter, ~95mm tall, holds ~350ml. Handle is roughly 65mm tall and extends ~30mm from body."
    },
    {
        "keywords": ["travel mug", "tumbler", "insulated tumbler", "stanley tumbler", "yeti tumbler"],
        "name": "Insulated Travel Tumbler",
        "category": "Drinkware",
        "dimensions": {
            "outer_diameter": 76.0, "height": 265.0, "wall_thickness": 3.0,
            "lid_diameter": 80.0, "lid_height": 25.0,
            "base_diameter": 65.0, "handle_width": 35.0
        },
        "features": [
            "Tall cylindrical body, slightly tapered (narrower at bottom)",
            "Double-wall insulated construction",
            "Flip-top or slide lid with drinking hole and straw slot",
            "Integrated handle on one side (large enough for 3-4 fingers)",
            "Flat wide bottom for stability",
            "Rubber base pad for non-slip",
            "Narrow mouth for drinking, wide enough for ice cubes"
        ],
        "notes": "Stanley/YETI style. Tall (~265mm), narrow (~76mm). The handle wraps vertically alongside the body. Lid is the most complex part."
    },
    {
        "keywords": ["water bottle", "sport bottle"],
        "name": "Sport Water Bottle",
        "category": "Drinkware",
        "dimensions": {
            "body_diameter": 73.0, "height": 260.0, "wall_thickness": 2.0,
            "neck_diameter": 45.0, "cap_diameter": 50.0, "cap_height": 30.0
        },
        "features": [
            "Cylindrical body with slight waist taper in middle",
            "Screw-cap top with flip-top spout or pop-up nozzle",
            "Carrying loop integrated into cap",
            "Flat bottom, sometimes with concave center",
            "Capacity markers on side (subtle ridges)"
        ],
        "notes": "Simple revolution profile. The cap/lid is the most distinctive part — can be a flip-top or twist-open."
    },
    {
        "keywords": ["coaster", "drink coaster"],
        "name": "Drink Coaster",
        "category": "Drinkware",
        "dimensions": {
            "diameter": 100.0, "height": 8.0,
            "lip_height": 2.0, "corner_radius": 3.0
        },
        "features": [
            "Round or square platform with raised lip edge",
            "Slightly recessed center to catch condensation (~1mm deep)",
            "Non-slip bottom (groove pattern or rubber pad recess)",
            "Optional: decorative pattern, logo engraving, or drainage channels on top surface"
        ],
        "notes": "Simple but precise. The raised lip catches drips. Standard coaster is 100mm round or 100×100mm square."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  TOOLS & HARDWARE
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["screwdriver handle", "screwdriver"],
        "name": "Screwdriver Handle",
        "category": "Tools",
        "dimensions": {
            "handle_length": 105.0, "handle_max_diameter": 34.0,
            "handle_min_diameter": 20.0, "shaft_diameter": 6.5,
            "shaft_length": 100.0
        },
        "features": [
            "Ergonomic grip with bulge in middle tapering to each end",
            "Hex anti-roll flats on the widest section (6 flat facets)",
            "Finger grip ridges or rubber insert grooves",
            "Hole at butt-end for hanging",
            "Metal shaft extending from narrow end",
            "Tip geometry: Phillips #2 cross or flat blade"
        ],
        "notes": "The handle profile is a smooth spline that bulges in the grip area. Anti-roll flats prevent rolling off a table."
    },
    {
        "keywords": ["wrench", "spanner", "adjustable wrench"],
        "name": "Adjustable Wrench (8-inch)",
        "category": "Tools",
        "dimensions": {
            "overall_length": 200.0, "head_width": 30.0, "head_depth": 12.0,
            "jaw_opening_max": 25.0, "handle_width": 18.0, "handle_thickness": 10.0
        },
        "features": [
            "Fixed jaw integrated with handle body",
            "Movable jaw with worm gear adjustment wheel",
            "Adjustment wheel: knurled cylinder ~10mm diameter",
            "Hanging hole at handle end ~10mm",
            "Handle tapers from head to tail",
            "Measurement scale etched near jaw opening"
        ],
        "notes": "Profile is mostly 2D (flat cross-section). The head with jaw mechanism is the complex part — can be simplified as a block with a slot."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  ENCLOSURES & ELECTRONICS
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["raspberry pi case", "rpi case", "pi case", "raspberry pi enclosure"],
        "name": "Raspberry Pi 4/5 Case",
        "category": "Enclosures",
        "dimensions": {
            "inner_length": 85.6, "inner_width": 56.5, "inner_height": 20.0,
            "wall_thickness": 2.0, "corner_radius": 3.0,
            "board_mount_spacing_x": 58.0, "board_mount_spacing_y": 49.0
        },
        "features": [
            "Bottom shell + snap-fit or screw-fit lid",
            "4 PCB mounting posts: M2.5, height 3mm, at board hole positions",
            "Port cutouts on sides: 2× micro-HDMI (~7×3mm), USB-C power (~9×3.5mm)",
            "2× USB-A ports (~15×6mm stacked), 1× Ethernet (~16×14mm)",
            "SD card slot access on short edge (~12×2mm)",
            "GPIO header slot in lid: ~52×6mm opening",
            "Ventilation slots or holes on top/sides",
            "Optional: fan mount recess 30×30mm or 40×40mm in lid"
        ],
        "notes": "Pi 4 board is 85.6×56.5mm. Mounting holes are at specific coordinates. All ports are on two edges (USB/Ethernet on one long edge, power/HDMI on another)."
    },
    {
        "keywords": ["arduino case", "arduino uno case", "arduino enclosure"],
        "name": "Arduino Uno R3 Case",
        "category": "Enclosures",
        "dimensions": {
            "inner_length": 68.6, "inner_width": 53.4, "inner_height": 18.0,
            "wall_thickness": 2.0, "corner_radius": 3.0
        },
        "features": [
            "Bottom + lid design",
            "4 PCB mounting posts at Arduino mounting hole positions",
            "USB-B port cutout on short edge (~12×11mm)",
            "Barrel jack cutout (~9mm diameter circular)",
            "Pin header access slots on long edges (for shields or wiring)",
            "Reset button access hole (~3mm)",
            "Ventilation slots"
        ],
        "notes": "Arduino Uno has an irregular shape (one corner is not 90°). The USB-B connector is tall. Include header access for prototyping."
    },
    {
        "keywords": ["project box", "electronics enclosure", "junction box", "project enclosure"],
        "name": "Generic Electronics Project Box",
        "category": "Enclosures",
        "dimensions": {
            "length": 100.0, "width": 60.0, "height": 30.0,
            "wall_thickness": 2.5, "corner_radius": 3.0,
            "screw_boss_diameter": 8.0, "screw_hole_diameter": 3.0
        },
        "features": [
            "Bottom shell + screw-down lid",
            "4 corner screw bosses with countersunk holes",
            "4 internal PCB mounting posts (M3)",
            "Blank side panels (user drills port holes as needed)",
            "Optional: cable gland holes on one end (~16mm PG7 knockouts)",
            "Recessed lid that sits flush with walls",
            "Label recess on top surface (~60×20mm, 0.5mm deep)"
        ],
        "notes": "A generic enclosure. The 4 corner bosses provide secure lid attachment. Internal posts hold a PCB elevated above the bottom for airflow."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  FURNITURE & HOME
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["shelf bracket", "wall bracket", "l bracket", "shelf support"],
        "name": "Shelf Bracket / L-Bracket",
        "category": "Hardware",
        "dimensions": {
            "arm_length": 200.0, "height": 200.0, "thickness": 5.0,
            "width": 30.0, "hole_diameter": 6.0,
            "gusset_thickness": 3.0
        },
        "features": [
            "L-shaped profile: horizontal arm + vertical mounting plate",
            "Mounting holes in vertical plate: 2-3 holes for wall screws",
            "Shelf support holes in horizontal arm: 2 holes for shelf attachment",
            "Triangular gusset/rib connecting arm to plate for strength",
            "Rounded end on horizontal arm",
            "Chamfer or fillet on inner L-corner for strength"
        ],
        "notes": "Standard L-bracket with 1:1 arm-to-height ratio. The gusset is critical for load bearing. Holes should be countersunk for flat screws."
    },
    {
        "keywords": ["bookend", "book end", "book holder"],
        "name": "Bookend",
        "category": "Home",
        "dimensions": {
            "width": 130.0, "depth": 100.0, "height": 150.0,
            "base_thickness": 5.0, "upright_thickness": 5.0
        },
        "features": [
            "L-shaped: flat base + vertical upright",
            "Base slides under books for weight-stabilization",
            "Non-slip pads on bottom of base",
            "Optional: decorative cutout or pattern on upright face",
            "Rounded or chamfered top edge of upright",
            "Heavy base or weighted for stability"
        ],
        "notes": "Simple L-shape. The base must extend far enough under the books to prevent tipping. Weight distribution is key."
    },
    {
        "keywords": ["hook", "wall hook", "coat hook", "towel hook"],
        "name": "Wall Hook",
        "category": "Home",
        "dimensions": {
            "backplate_width": 30.0, "backplate_height": 60.0, "backplate_thickness": 5.0,
            "hook_reach": 40.0, "hook_rise": 25.0, "hook_diameter": 8.0,
            "screw_hole_diameter": 4.0
        },
        "features": [
            "Flat backplate with 1-2 screw holes for wall mounting",
            "Curved hook arm extending outward and upward from plate",
            "Hook tip curves upward to prevent items from sliding off",
            "Rounded hook profile (no sharp edges to damage clothing)",
            "Optional: decorative shape on backplate"
        ],
        "notes": "The hook curve can be a sweep along a spline path, or built from arc segments. The tip should curve upward."
    },
    {
        "keywords": ["drawer handle", "drawer pull", "cabinet handle", "cabinet pull"],
        "name": "Drawer Pull Handle",
        "category": "Hardware",
        "dimensions": {
            "center_to_center": 128.0, "total_length": 148.0,
            "handle_height": 30.0, "handle_diameter": 12.0,
            "mount_post_diameter": 8.0, "mount_post_height": 22.0,
            "screw_hole_diameter": 4.0
        },
        "features": [
            "Arched bar spanning between two mounting posts",
            "Two mounting posts that bolt through drawer face",
            "M4 threaded hole in bottom of each post (for bolts from inside drawer)",
            "Smooth ergonomic bar — circular or oval cross-section",
            "Slight arch in the bar (rises ~30mm from drawer surface)",
            "Rounded ends where bar meets posts"
        ],
        "notes": "Standard center-to-center distances: 64mm, 96mm, 128mm, or 160mm. The handle is essentially a sweep along an arc path."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  PHOTOGRAPHY & MOUNTS
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["phone mount", "phone holder", "phone tripod mount", "phone clamp"],
        "name": "Universal Phone Mount/Clamp",
        "category": "Mounts",
        "dimensions": {
            "jaw_min_width": 55.0, "jaw_max_width": 90.0,
            "jaw_height": 30.0, "jaw_depth": 15.0,
            "mount_thread": "1/4-20"
        },
        "features": [
            "Spring-loaded or screw-adjustable jaws",
            "Two jaw pads with rubber grip surface",
            "1/4-20 threaded hole on bottom for tripod mounting",
            "Cold shoe adapter on top (optional)",
            "Ball joint or hinge for angle adjustment"
        ],
        "notes": "The adjustable jaw mechanism is the key feature. Width adjusts from ~55mm to ~90mm to fit various phones."
    },
    {
        "keywords": ["gopro mount", "action camera mount", "gopro case"],
        "name": "GoPro-Style Action Camera Mount",
        "category": "Mounts",
        "dimensions": {
            "finger_width": 15.0, "finger_height": 14.5, "finger_thickness": 3.0,
            "bolt_hole_diameter": 5.0, "mount_base_width": 35.0
        },
        "features": [
            "GoPro standard 2-prong or 3-prong finger mount",
            "Bolt-through hole for thumb screw (M5)",
            "Various base types: flat adhesive, clip, suction cup",
            "Quick-release buckle geometry (J-hook style)",
            "Compatible with standard GoPro spacing: fingers 3mm thick, 3mm gap"
        ],
        "notes": "GoPro mounting system uses interlocking fingers with a bolt through. 3-prong (camera side) fits into 2-prong (mount side). Standard dimensions for compatibility."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  3D PRINTING SPECIFIC
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["spool holder", "filament holder", "filament spool holder"],
        "name": "3D Printer Filament Spool Holder",
        "category": "3D Printing",
        "dimensions": {
            "spool_hub_diameter": 55.0, "spool_outer_diameter": 200.0,
            "spool_width": 70.0, "axle_diameter": 20.0,
            "base_width": 120.0, "base_depth": 100.0, "base_height": 180.0
        },
        "features": [
            "A-frame or T-frame base for stability",
            "Horizontal axle/rod to hold spool (smooth for free spinning)",
            "Bearings or PTFE tube on axle for low friction",
            "Adjustable width to accommodate different spool sizes",
            "Guide hole or tube for filament path",
            "Weighted or wide base to prevent tipping"
        ],
        "notes": "Standard spool has 55mm center hole and 200mm outer diameter. The holder needs to let the spool spin freely for smooth feeding."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  MECHANICAL COMPONENTS
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["spur gear", "gear", "gear wheel"],
        "name": "Spur Gear",
        "category": "Mechanical",
        "dimensions": {
            "module": 2.0, "num_teeth": 24, "pressure_angle": 20.0,
            "face_width": 10.0, "bore_diameter": 10.0,
            "hub_diameter": 20.0, "hub_length": 15.0,
            "keyway_width": 3.0, "keyway_depth": 1.5
        },
        "features": [
            "Involute tooth profile (standard 20° pressure angle)",
            "Central bore for shaft with keyway",
            "Hub extending beyond gear face for bearing support",
            "Chamfer on tooth tips and edges",
            "Lightening holes in web (for larger gears)"
        ],
        "notes": "Pitch radius = module × teeth / 2. Outer radius = pitch + module. Root radius = pitch - 1.25 × module. Tooth width at pitch circle ≈ π × module / 2."
    },
    {
        "keywords": ["bearing housing", "bearing block", "pillow block"],
        "name": "Pillow Block Bearing Housing",
        "category": "Mechanical",
        "dimensions": {
            "bore_diameter": 20.0, "housing_diameter": 47.0,
            "overall_width": 100.0, "center_height": 33.0,
            "base_length": 100.0, "base_width": 38.0, "base_thickness": 12.0,
            "bolt_hole_diameter": 12.0, "bolt_spacing": 75.0
        },
        "features": [
            "Cylindrical bearing pocket centered in housing",
            "Split or one-piece housing around bearing",
            "Flat base with 2 bolt holes for mounting",
            "Grease nipple/zerk fitting hole on top",
            "Seals on each side of bearing pocket",
            "Flat machined bottom surface"
        ],
        "notes": "The housing is a cylindrical pocket on a flat rectangular base. The bearing OD sits in the pocket. Bolt holes on each side of center."
    },
    {
        "keywords": ["pulley", "belt pulley", "timing pulley"],
        "name": "Timing Belt Pulley",
        "category": "Mechanical",
        "dimensions": {
            "outer_diameter": 40.0, "bore_diameter": 8.0,
            "width": 16.0, "num_teeth": 20,
            "flange_diameter": 44.0, "flange_thickness": 1.5,
            "hub_diameter": 20.0, "hub_length": 10.0,
            "set_screw_diameter": 3.0
        },
        "features": [
            "Toothed outer circumference for belt engagement",
            "Flanges on both sides to keep belt centered",
            "Central bore with set screw hole (or keyway) for shaft",
            "Hub extending on one side for support",
            "Lightening holes in web for weight reduction (larger pulleys)"
        ],
        "notes": "GT2 pitch = 2mm, MXL pitch = 2.032mm, XL pitch = 5.08mm. Outer diameter = (teeth × pitch) / π. Flanges are thin discs slightly larger than tooth OD."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  STORAGE & ORGANIZATION
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["battery holder", "battery case", "18650 holder", "aa battery holder"],
        "name": "Battery Holder (AA / 18650)",
        "category": "Storage",
        "dimensions": {
            "aa_diameter": 14.5, "aa_length": 50.5,
            "18650_diameter": 18.6, "18650_length": 65.2,
            "wall_thickness": 2.0, "spring_contact_depth": 3.0
        },
        "features": [
            "Cylindrical channels sized for battery diameter + 0.5mm clearance",
            "Spring contact pocket at negative end (deeper channel ~3mm)",
            "Flat contact pad at positive end",
            "Wire routing channels on bottom",
            "Optional: lid with snap-fit tabs"
        ],
        "notes": "AA cell: 14.5mm × 50.5mm. AAA: 10.5mm × 44.5mm. 18650: 18.6mm × 65.2mm. Add 0.5mm clearance around diameter, 3mm extra length for spring."
    },
    {
        "keywords": ["sd card holder", "memory card case", "sd card case"],
        "name": "SD/MicroSD Card Holder",
        "category": "Storage",
        "dimensions": {
            "sd_width": 24.0, "sd_height": 32.0, "sd_thickness": 2.1,
            "microsd_width": 11.0, "microsd_height": 15.0, "microsd_thickness": 1.0,
            "case_padding": 2.0, "wall_thickness": 2.0
        },
        "features": [
            "Individual slots for each card with tight fit",
            "Hinged or slide-out lid",
            "Label area for marking each slot",
            "Holds 4-12 cards in a grid arrangement",
            "Credit-card sized for portability (~85×54mm)",
            "Snap-fit closure mechanism"
        ],
        "notes": "Full SD card is 24×32×2.1mm. MicroSD is 11×15×1mm. Size the slots with 0.3mm clearance on each side."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  DRONES & RC
    # ─────────────────────────────────────────────────────────────────────────

    # --- RACING / FPV QUADCOPTER (250-class) ---
    {
        "keywords": ["drone", "quadcopter", "drone frame", "racing drone", "fpv drone", "fpv quadcopter", "250 drone"],
        "name": "Racing FPV Quadcopter (250-class)",
        "category": "Drones & RC",
        "dimensions": {
            "motor_to_motor": 250.0, "arm_width": 15.0, "arm_thickness": 5.0,
            "center_plate_diameter": 80.0, "center_plate_thickness": 3.0,
            "motor_mount_diameter": 16.0, "motor_mount_holes": 12.0,
            "prop_diameter": 127.0, "motor_height": 15.0, "motor_diameter": 22.0,
            "canopy_height": 30.0, "landing_leg_height": 40.0
        },
        "features": [
            "X-configuration: 4 arms extending from central body at 90° intervals (45° from forward)",
            "Central body: stacked plates with spacer posts for electronics mounting",
            "4 MOTORS: visible cylindrical motor cans on TOP of each arm tip (diameter ~22mm, height ~15mm)",
            "4 PROPELLERS: disc/blade shapes on top of each motor (2 CW + 2 CCW, diameter ~127mm)",
            "CANOPY/COVER: streamlined dome or shell over center electronics (aerodynamic shape)",
            "LANDING GEAR: 4 legs or 2 skid rails under central body (~40mm ground clearance)",
            "Motor mounts at arm tips: 4 holes in 12mm or 16mm square pattern",
            "Battery strap slots on bottom plate",
            "Camera/gimbal mount bracket hanging under front of center body",
            "FPV camera mount: angled 30° forward-tilted bracket on front",
            "Antenna mount tube on rear (SMA pigtail holder)",
            "LED indicators on each arm (navigation: front=red/green, rear=white)",
            "Weight-reduction cutouts in arms",
            "Flight controller mounting holes on top plate (30.5mm pattern)"
        ],
        "notes": "250mm class = motor-to-motor diagonal distance. Compact, agile racer. CRITICAL: Build COMPLETE drone — not just the frame. Include visible motors, propellers, canopy, and landing gear as separate geometric features unioned to the frame."
    },

    # --- PHOTOGRAPHY / CAMERA DRONE (DJI-style) ---
    {
        "keywords": ["camera drone", "photography drone", "dji", "aerial photography", "dji mavic", "mavic", "photo drone", "filming drone", "videography drone"],
        "name": "Photography Camera Drone (DJI-style)",
        "category": "Drones & RC",
        "dimensions": {
            "body_length": 200.0, "body_width": 100.0, "body_height": 55.0,
            "arm_length": 170.0, "arm_width": 18.0, "arm_thickness": 12.0,
            "motor_to_motor": 350.0, "prop_diameter": 230.0,
            "motor_height": 18.0, "motor_diameter": 28.0,
            "gimbal_width": 45.0, "gimbal_depth": 45.0, "gimbal_height": 40.0,
            "camera_diameter": 25.0,
            "landing_leg_height": 55.0, "landing_leg_spread": 160.0,
            "battery_length": 100.0, "battery_width": 65.0, "battery_height": 30.0
        },
        "features": [
            "Streamlined aerodynamic body: lofted/rounded fuselage (NOT a flat plate — use .loft() or .spline())",
            "4 foldable arms with motor pods at tips (arms attach at body sides, pivot forward/backward)",
            "4 MOTORS: cylindrical brushless motors on arm tips (28mm Ø, 18mm tall) — MUST be visible",
            "4 PROPELLERS: large folding propellers on top of motors (230mm Ø × 3mm thin discs)",
            "3-AXIS GIMBAL: articulated camera mount hanging under front of body — box frame with camera sphere",
            "CAMERA: sphere or cylinder lens unit inside gimbal frame",
            "LANDING GEAR: 2 retractable skid legs or 4 spring legs under body (55mm ground clearance)",
            "BATTERY COMPARTMENT: rear-loading battery bay with release latch outline on top/rear",
            "Obstacle avoidance sensors: forward + downward sensor windows (small lens circles)",
            "GPS module dome on top of body (small raised hemisphere)",
            "Front status LED bar across nose",
            "Rear exhaust vents / cooling slots on body sides",
            "Downward optical flow sensor window on belly (small circle)",
            "Propeller fold hinge detail on each arm tip"
        ],
        "notes": "DJI Mavic-style camera drone. Body is STREAMLINED — use .loft() or .spline()+.revolve() NOT a flat plate. Arms fold but model them extended. Gimbal is a 3-axis bracket under front body. Build COMPLETE drone — motors, propellers, gimbal, camera, landing gear ALL visible."
    },

    # --- HEXACOPTER (6-motor heavy-lift) ---
    {
        "keywords": ["hexacopter", "hex drone", "6 motor drone", "heavy lift drone", "hexadrone", "six rotor", "industrial drone"],
        "name": "Hexacopter Heavy-Lift Drone",
        "category": "Drones & RC",
        "dimensions": {
            "motor_to_motor": 550.0, "center_plate_diameter": 150.0,
            "center_plate_thickness": 4.0, "arm_length": 220.0,
            "arm_width": 25.0, "arm_thickness": 8.0,
            "motor_height": 22.0, "motor_diameter": 35.0,
            "prop_diameter": 330.0, "prop_thickness": 3.0,
            "canopy_height": 50.0, "canopy_width": 130.0,
            "landing_leg_height": 120.0, "landing_leg_width": 15.0,
            "payload_rail_length": 200.0
        },
        "features": [
            "6-arm star configuration: arms at 60° intervals from center (hexagonal symmetry)",
            "Large central body: reinforced circular plates (top + bottom) with tall spacer posts",
            "6 MOTORS: heavy-duty cylindrical motor cans on arm tips (35mm Ø × 22mm) — MUST be visible",
            "6 PROPELLERS: large prop discs on top of motors (330mm Ø × 3mm thin) — MUST be visible",
            "CANOPY: large dome or box cover over center electronics (50mm tall, aerodynamic shape)",
            "TALL LANDING GEAR: 2 long skid rails or 6 legs under body (120mm clearance for payload)",
            "PAYLOAD RAILS: 2 parallel bars under body between landing legs for camera/cargo mounting",
            "Retractable gear mechanism: visible pivot mount at leg tops",
            "Gimbal/camera mount on payload rails under center body",
            "GPS puck dome on top of canopy",
            "Dual battery bays on bottom plate (front + rear for balance)",
            "FPV camera mount on front arm base",
            "Redundancy indicator LEDs on each arm (6 LED holes)",
            "Cable routing channels along arm tops"
        ],
        "notes": "Professional heavy-lift hexacopter for cinematography or cargo. 6 arms at 60° intervals. Tall landing gear for payload clearance. Build COMPLETE — 6 motors, 6 propellers, canopy, tall landing gear, and payload rails all visible."
    },

    # --- OCTOCOPTER (8-motor professional) ---
    {
        "keywords": ["octocopter", "octo drone", "8 motor drone", "8 rotor", "professional drone", "cinema drone"],
        "name": "Octocopter Professional Cinema Drone",
        "category": "Drones & RC",
        "dimensions": {
            "motor_to_motor": 800.0, "center_plate_diameter": 200.0,
            "center_plate_thickness": 5.0, "arm_length": 300.0,
            "arm_width": 30.0, "arm_thickness": 10.0,
            "motor_height": 25.0, "motor_diameter": 40.0,
            "prop_diameter": 380.0, "prop_thickness": 3.0,
            "canopy_height": 60.0, "canopy_width": 180.0,
            "landing_leg_height": 150.0, "landing_leg_width": 20.0,
            "payload_capacity_mm": 250.0
        },
        "features": [
            "8-arm radial configuration: arms at 45° intervals from center (octagonal symmetry)",
            "Heavy-duty central hub: thick stacked plates with reinforced spacers",
            "8 MOTORS: large cylindrical motor cans on arm tips (40mm Ø × 25mm) — MUST be visible",
            "8 PROPELLERS: large prop discs on top of motors (380mm Ø × 3mm) — MUST be visible",
            "CANOPY: large aerodynamic cover over center electronics (60mm tall)",
            "RETRACTABLE LANDING GEAR: 2 long carbon-style skid rails (150mm clearance for cinema camera)",
            "Retractable gear servo mount detail at rail pivot points",
            "Dual gimbal mount under center (for heavy cinema camera)",
            "Dual GPS module domes on top (main + backup)",
            "Parachute deployment tube on top of canopy",
            "Navigation lights on all 8 arms",
            "Battery tray: 2 large batteries strapped to bottom plate (front + rear)",
            "FPV camera pod on front",
            "Power distribution board visible between plates"
        ],
        "notes": "Professional 8-motor cinema drone. 8 arms at 45° intervals. Very large with tall retractable landing gear. Build COMPLETE — all 8 motors + 8 propellers + canopy + tall gear visible. This is an industrial-class UAV."
    },

    # --- TRICOPTER (Y-frame, 3 motors) ---
    {
        "keywords": ["tricopter", "tri drone", "3 motor drone", "y frame drone", "three rotor", "y drone"],
        "name": "Tricopter Y-Frame Drone",
        "category": "Drones & RC",
        "dimensions": {
            "motor_to_motor": 350.0, "arm_length": 200.0,
            "arm_width": 18.0, "arm_thickness": 6.0,
            "center_plate_length": 100.0, "center_plate_width": 60.0,
            "center_plate_thickness": 3.0,
            "motor_height": 16.0, "motor_diameter": 24.0,
            "prop_diameter": 254.0, "prop_thickness": 2.0,
            "tail_servo_width": 12.0, "tail_servo_length": 25.0,
            "canopy_height": 30.0,
            "landing_leg_height": 45.0
        },
        "features": [
            "Y-configuration: 2 front arms at ±45° and 1 rear tail arm (120° between each, Y-shape from above)",
            "Central body: elongated rectangular/oval plate (longer front-to-back than a quadcopter)",
            "3 MOTORS: cylindrical motor cans on arm tips (24mm Ø × 16mm) — MUST be visible",
            "3 PROPELLERS: large prop discs on motors (254mm Ø / 10 inch) — MUST be visible",
            "TAIL SERVO: pivoting motor mount on rear arm for yaw control (visible servo box + tilt mechanism)",
            "CANOPY: streamlined cover over center electronics",
            "LANDING GEAR: 3 legs (one under each arm tip) or 2-rail skid under front arms",
            "Battery mount on bottom plate (strapped between front arms)",
            "Camera mount: forward-facing bracket under nose",
            "Antenna mounts on rear boom",
            "LED navigation lights: red on left front arm, green on right front, white on rear",
            "Tail boom reinforcement tube (rear arm often longer/thinner than fronts)"
        ],
        "notes": "Tricopter: Y-shaped frame with only 3 motors. The rear motor tilts via a servo for yaw control — the tail servo mechanism is a KEY visual feature. Build COMPLETE — 3 motors, 3 propellers, tail servo, canopy, landing gear all visible."
    },

    # --- FIXED-WING DRONE / VTOL ---
    {
        "keywords": ["fixed wing drone", "plane drone", "vtol drone", "flying wing", "vtol", "wing drone", "survey drone", "mapping drone", "fixed wing vtol", "fixed wing"],
        "name": "Fixed-Wing VTOL Survey Drone",
        "category": "Drones & RC",
        "dimensions": {
            "wingspan": 1200.0, "fuselage_length": 600.0,
            "fuselage_width": 120.0, "fuselage_height": 100.0,
            "wing_chord": 200.0, "wing_thickness": 25.0,
            "tail_length": 250.0, "tail_height": 150.0,
            "vtol_motor_height": 18.0, "vtol_motor_diameter": 28.0,
            "vtol_prop_diameter": 254.0,
            "pusher_motor_diameter": 35.0, "pusher_prop_diameter": 280.0,
            "landing_skid_length": 300.0
        },
        "features": [
            "FUSELAGE: streamlined tubular body (use .loft() from rounded nose to tapered tail — NOT a box)",
            "WINGS: two flat airfoil-profile wings extending from mid-fuselage (use thin .extrude() with rounded leading edge)",
            "V-TAIL or conventional tail: angled stabilizers at rear of fuselage",
            "4 VTOL MOTORS: cylindrical motor cans on wing-mounted booms (28mm Ø × 18mm) for vertical takeoff — MUST be visible",
            "4 VTOL PROPELLERS: prop discs on top of VTOL motors (254mm Ø) — MUST be visible",
            "1 PUSHER MOTOR: larger motor at rear of fuselage for forward flight (35mm Ø)",
            "1 PUSHER PROPELLER: prop disc behind tail (280mm Ø) — MUST be visible",
            "PAYLOAD BAY: hatch/door on belly for camera or sensor equipment",
            "Landing skid rails under fuselage (or retractable gear)",
            "GPS dome on top of fuselage behind wings",
            "Pitot tube probe extending from nose (thin cylinder, speed sensor)",
            "Wing-tip navigation lights (red left, green right)",
            "Aileron control surface outlines on wing trailing edges",
            "Elevator/rudder hinge lines on tail surfaces"
        ],
        "notes": "VTOL fixed-wing hybrid: takes off vertically like a quadcopter, then transitions to airplane flight. Fuselage MUST be streamlined (loft/spline) — NOT a box. Has BOTH vertical lift motors on booms AND a pusher motor at rear. Build COMPLETE — wings, fuselage, all motors, all propellers, tail surfaces, landing gear."
    },

    # --- MINI / MICRO QUADCOPTER (tiny whoop style) ---
    {
        "keywords": ["mini drone", "micro drone", "tiny drone", "nano drone", "toy drone", "tiny whoop", "small drone", "indoor drone"],
        "name": "Mini Indoor Quadcopter (Tiny Whoop Style)",
        "category": "Drones & RC",
        "dimensions": {
            "frame_size": 65.0, "motor_to_motor": 65.0,
            "prop_diameter": 31.0, "prop_guard_outer": 40.0,
            "motor_height": 10.0, "motor_diameter": 7.0,
            "body_height": 20.0, "body_width": 35.0, "body_length": 35.0,
            "canopy_height": 15.0,
            "prop_guard_height": 10.0, "prop_guard_wall": 1.5,
            "battery_length": 30.0, "battery_width": 15.0, "battery_height": 8.0
        },
        "features": [
            "Compact integrated frame: single-piece body with 4 integrated ducted fan guards (NOT separate arms)",
            "4 DUCTED PROP GUARDS: circular rings around each propeller (protective duct walls ~1.5mm thick)",
            "4 MOTORS: tiny cylindrical brushed motors inside each duct (7mm Ø × 10mm) — MUST be visible",
            "4 PROPELLERS: small prop discs inside ducts on top of motors (31mm Ø) — MUST be visible",
            "CANOPY: small clip-on cover over center flight controller (15mm tall dome or shell)",
            "NO separate landing gear — frame bottom IS the landing surface (flat-bottom design)",
            "FPV micro camera: tiny camera pod on front (8mm × 8mm lens window)",
            "Battery holder: slot/tray on bottom for LiPo (30×15×8mm)",
            "Antenna wire stub on rear (thin cylinder)",
            "LED lights visible through frame (1-2 per arm duct)",
            "USB charging port hole on side of center body",
            "Bind/pair button hole on top"
        ],
        "notes": "Tiny Whoop style micro drone for indoor flying. Key difference: INTEGRATED DUCTED FRAME — the prop guards are circular rings fused into the main body, not separate arms. Very compact. Build COMPLETE — motors (tiny), propellers inside ducts, canopy, FPV camera. No landing legs needed (flat bottom)."
    },

    # --- DELIVERY / CARGO DRONE ---
    {
        "keywords": ["delivery drone", "cargo drone", "package drone", "logistics drone", "amazon drone", "delivery uav"],
        "name": "Delivery Cargo Drone",
        "category": "Drones & RC",
        "dimensions": {
            "motor_to_motor": 700.0, "arm_length": 280.0,
            "arm_width": 30.0, "arm_thickness": 10.0,
            "center_body_length": 300.0, "center_body_width": 200.0,
            "center_body_height": 120.0,
            "motor_height": 22.0, "motor_diameter": 35.0,
            "prop_diameter": 330.0, "prop_thickness": 3.0,
            "canopy_height": 45.0,
            "cargo_bay_length": 250.0, "cargo_bay_width": 200.0, "cargo_bay_height": 150.0,
            "landing_leg_height": 180.0
        },
        "features": [
            "6 or 8 arms in hexagonal/octagonal layout for redundancy",
            "Large enclosed center body: streamlined box/lofted fuselage housing electronics + battery",
            "6-8 MOTORS: industrial cylindrical motors on arm tips (35mm Ø × 22mm) — MUST be visible",
            "6-8 PROPELLERS: large prop discs on motors (330mm Ø) — MUST be visible",
            "CANOPY: integrated body cover (electronics enclosed in fuselage, not exposed plates)",
            "CARGO BAY: open-bottom compartment under body with release mechanism outline",
            "Cargo hook or winch cylinder hanging from cargo bay center",
            "TALL LANDING GEAR: 4 or 6 legs providing cargo clearance (180mm ground clearance)",
            "Landing gear cross-brace for stability (horizontal struts between legs)",
            "Package cradle rails inside cargo bay",
            "GPS + communication domes on top of fuselage (2 domes)",
            "Obstacle avoidance sensor windows (front, sides, bottom: small lens circles)",
            "Parachute tube on top for emergency recovery",
            "LED strips along bottom for visibility during delivery"
        ],
        "notes": "Delivery/cargo drone for autonomous package delivery. Key feature: CARGO BAY with release mechanism under body. Tall landing gear for package clearance. Build COMPLETE — all motors, propellers, enclosed fuselage body, cargo bay, tall landing gear, sensor windows."
    },

    # --- UNDERWATER DRONE / ROV ---
    {
        "keywords": ["underwater drone", "rov", "rov drone", "submarine drone", "submersible drone", "aquatic drone", "ocean drone", "underwater robot", "underwater rov", "underwater"],
        "name": "Underwater ROV Drone",
        "category": "Drones & RC",
        "dimensions": {
            "body_length": 350.0, "body_width": 250.0, "body_height": 180.0,
            "thruster_diameter": 60.0, "thruster_length": 80.0,
            "thruster_prop_diameter": 50.0,
            "camera_dome_diameter": 60.0,
            "buoyancy_foam_height": 40.0,
            "frame_rail_width": 15.0,
            "tether_port_diameter": 20.0
        },
        "features": [
            "Open frame structure: cage/rail frame (NOT an enclosed fuselage — open water flow-through design)",
            "4-6 THRUSTERS: horizontal + vertical thruster pods mounted on frame (cylindrical with prop inside)",
            "2 HORIZONTAL thrusters: rear-facing for forward/backward + yaw movement",
            "2-4 VERTICAL thrusters: downward-facing for depth + pitch/roll control",
            "THRUSTER PROPELLERS: small props visible inside each thruster tube — MUST be visible",
            "CAMERA: forward-facing camera inside clear dome/hemisphere on front of frame",
            "LED FLOOD LIGHTS: 2 large cylindrical lights flanking the camera dome",
            "BUOYANCY FOAM: bright-colored foam block on top of frame (keeps ROV right-side up)",
            "Electronics housing: sealed cylindrical or box tube in center of frame",
            "Tether connection port: circular connector on rear for control/power cable",
            "Manipulator arm mount: bracket on front bottom for optional gripper attachment",
            "Depth sensor port on electronics housing",
            "Guard cage around propellers for safety"
        ],
        "notes": "Underwater ROV-style drone. COMPLETELY different from air drones: open frame, enclosed thrusters, camera dome, buoyancy foam, tether port. No arms/propellers on top — thrusters are enclosed tubes mounted on a cage frame. Build the cage frame, thrusters, camera dome, lights, buoyancy foam, electronics tube."
    },

    # --- AGRICULTURAL SPRAY DRONE ---
    {
        "keywords": ["agriculture drone", "spray drone", "farm drone", "crop drone", "agricultural drone", "sprayer drone", "crop sprayer", "agricultural spray drone", "agricultural spray", "spray", "agriculture"],
        "name": "Agricultural Spray Drone",
        "category": "Drones & RC",
        "dimensions": {
            "motor_to_motor": 900.0, "arm_length": 350.0,
            "arm_width": 35.0, "arm_thickness": 12.0,
            "center_body_diameter": 200.0, "center_body_height": 80.0,
            "motor_height": 25.0, "motor_diameter": 40.0,
            "prop_diameter": 380.0, "prop_thickness": 3.0,
            "tank_length": 300.0, "tank_width": 250.0, "tank_height": 200.0,
            "spray_boom_length": 600.0, "nozzle_count": 4,
            "landing_leg_height": 200.0
        },
        "features": [
            "6 or 8 heavy-duty arms in hexagonal/octagonal layout (farm drones need redundancy)",
            "Robust center body: reinforced plate stack or box frame for vibration resistance",
            "6-8 MOTORS: large agricultural-grade cylindrical motors (40mm Ø × 25mm) — MUST be visible",
            "6-8 PROPELLERS: large prop discs (380mm Ø) — MUST be visible",
            "SPRAY TANK: large translucent/visible tank on top of or under center body (10-20 liter capacity shape)",
            "SPRAY BOOM: horizontal bar under body with 4+ spray nozzle outlets (cylindrical nozzle tips)",
            "Pump assembly: cylindrical pump unit connected to tank and boom",
            "CANOPY: protective cover over electronics (separate from tank)",
            "WIDE TALL LANDING GEAR: 4 or 6 wide-stance legs (200mm clearance for spray boom + crops)",
            "Landing gear spreader bars for stability on uneven terrain",
            "GPS + RTK antenna dome on top (precision navigation for spray patterns)",
            "Flow sensor module on spray line",
            "Tank fill port cap on top of tank",
            "LED strips for night/low-visibility operation"
        ],
        "notes": "Agricultural spray drone. KEY FEATURES: large liquid spray tank, spray boom with nozzles, extra-wide landing gear for crop clearance. Very robust build. 6-8 motors for payload capacity. Build COMPLETE — motors, propellers, tank, spray boom with nozzles, wide landing gear, canopy."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  AUTOMOTIVE
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["phone car mount", "car phone holder", "vent mount", "dashboard mount"],
        "name": "Car Phone Vent Mount",
        "category": "Automotive",
        "dimensions": {
            "clamp_width": 70.0, "clamp_depth": 25.0, "clamp_height": 50.0,
            "vent_clip_depth": 20.0, "vent_clip_width": 30.0,
            "ball_joint_diameter": 17.0
        },
        "features": [
            "Spring-loaded side clamps for phone grip (55-90mm range)",
            "Vent clip mechanism: spring-loaded fingers that grip vent slats",
            "Ball joint between clip and cradle for angle adjustment",
            "Rubber pads on clamp faces for grip and scratch protection",
            "One-hand operation: squeeze to release, spring to grip",
            "Bottom support lip for phone weight"
        ],
        "notes": "The vent clip is a U-shaped spring mechanism. The phone cradle has two side arms and a bottom lip. Ball joint allows 360° rotation."
    },
    {
        "keywords": ["cup holder insert", "cup holder adapter"],
        "name": "Cup Holder Insert/Adapter",
        "category": "Automotive",
        "dimensions": {
            "outer_diameter": 80.0, "inner_diameter": 55.0,
            "height": 50.0, "wall_thickness": 2.5,
            "lip_width": 5.0
        },
        "features": [
            "Tapered cylindrical adapter (wider at top, narrower at bottom)",
            "Top lip/flange that rests on cup holder rim",
            "Inner bore sized for smaller cup/can",
            "Non-slip ridges on inner surface",
            "Drainage hole in bottom"
        ],
        "notes": "Adapts a large car cup holder (~80mm) to fit a smaller cup or can (~55-65mm). Simple revolution profile."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  SPORTS & FITNESS
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["dumbbell", "hand weight", "gym weight"],
        "name": "Dumbbell / Hand Weight",
        "category": "Fitness",
        "dimensions": {
            "total_length": 170.0, "handle_length": 120.0, "handle_diameter": 32.0,
            "weight_diameter": 85.0, "weight_thickness": 25.0,
            "knurl_pitch": 1.5
        },
        "features": [
            "Central handle grip (~32mm diameter, ~120mm long)",
            "Knurled texture on handle for grip (diamond crosshatch pattern)",
            "Two weight heads on each end (hexagonal or round cross-section)",
            "Hex shape on weights prevents rolling on floor",
            "Chamfered edges on weight faces",
            "Smooth transition (fillet) between handle and weight heads"
        ],
        "notes": "Hex dumbbells have hexagonal cross-section weights to prevent rolling. Revolution profile for handle, hex extrude for weight heads."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  CONTAINERS & PLANTERS
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["plant pot", "flower pot", "planter"],
        "name": "Plant Pot / Planter",
        "category": "Home",
        "dimensions": {
            "top_diameter": 150.0, "bottom_diameter": 100.0, "height": 140.0,
            "wall_thickness": 4.0, "rim_width": 8.0, "rim_height": 10.0,
            "drain_hole_diameter": 15.0
        },
        "features": [
            "Tapered cylindrical body (wider at top)",
            "Rolled rim at top (thicker lip ~8mm wide)",
            "Drainage hole(s) in bottom (1 large or 3-4 small)",
            "Flat or slightly raised bottom ring for airflow",
            "Optional: saucer/tray that nests underneath",
            "Optional: decorative ribs or texture on exterior"
        ],
        "notes": "Classic flowerpot shape is a truncated cone. The rim is important for grip when lifting. Drainage holes are essential."
    },
    {
        "keywords": ["vase", "flower vase"],
        "name": "Flower Vase",
        "category": "Home",
        "dimensions": {
            "base_diameter": 70.0, "body_diameter": 90.0, "neck_diameter": 50.0,
            "top_diameter": 60.0, "height": 250.0, "wall_thickness": 3.0
        },
        "features": [
            "Revolution profile with elegant S-curve",
            "Wide stable base tapering outward to body bulge",
            "Narrow neck above body",
            "Flared lip at top opening",
            "Smooth interior (no internal features)",
            "Flat bottom, optionally with foot ring"
        ],
        "notes": "Classic vase is a spline revolution. The profile should have: flat base → outward curve to body max → inward curve to narrow neck → slight outward flare at lip. Use .revolve() with a spline profile."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  SCULPTURES & ART
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["chess piece", "chess king", "chess queen", "chess set", "chess pawn", "chess rook", "chess bishop", "chess knight"],
        "name": "Chess Piece Set (Staunton Style)",
        "category": "Sculptures & Art",
        "dimensions": {
            "king_height": 95.0, "king_base_diameter": 30.0,
            "queen_height": 85.0, "queen_base_diameter": 28.0,
            "bishop_height": 70.0, "bishop_base_diameter": 26.0,
            "knight_height": 60.0, "knight_base_diameter": 26.0,
            "rook_height": 50.0, "rook_base_diameter": 26.0,
            "pawn_height": 45.0, "pawn_base_diameter": 22.0
        },
        "features": [
            "King: cross finial on top, collar below cross, tapered body",
            "Queen: coronet (small crown with points) on top, smooth tapered body",
            "Bishop: mitre (diagonal slit in dome top), tapered body",
            "Knight: horse head profile (2D cut or lofted shape), on pedestal base",
            "Rook: crenellated top (castle battlements), cylindrical body",
            "Pawn: small ball on top, simple tapered body",
            "All pieces: wide stable base with molding ring, tapered stem, distinctive top"
        ],
        "notes": "Best approach: revolution profile for the base/stem/body, then add the distinctive top feature. Knight is hardest — use a 2D profile extrusion for the horse head. Each piece follows: wide base → narrow stem → wider body → characteristic top."
    },
    {
        "keywords": ["trophy", "award trophy", "trophy cup", "winner cup", "gold cup"],
        "name": "Trophy / Award Cup",
        "category": "Sculptures & Art",
        "dimensions": {
            "total_height": 300.0, "cup_diameter": 120.0, "cup_height": 100.0,
            "stem_height": 100.0, "stem_diameter": 20.0,
            "base_width": 100.0, "base_height": 60.0,
            "handle_width": 40.0, "handle_height": 80.0
        },
        "features": [
            "Flared cup/bowl on top (revolution profile: narrow bottom flaring to wide rim)",
            "Narrow decorative stem connecting cup to base",
            "Tiered pedestal base (2-3 stacked rectangles or cylinders, each smaller going up)",
            "Two handles curving outward from cup sides (swept C-shapes)",
            "Engraving area on base front face",
            "Decorative rings/collars at stem junctions"
        ],
        "notes": "Revolution profile for the cup and stem. Handles are swept circles along arc paths on either side. Base is stacked rectangular blocks with chamfered edges. Consider nameplate recess on front of base."
    },
    {
        "keywords": ["bust", "head bust", "portrait bust", "sculpture bust"],
        "name": "Portrait Bust / Head Sculpture",
        "category": "Sculptures & Art",
        "dimensions": {
            "head_width": 150.0, "head_depth": 180.0, "head_height": 220.0,
            "neck_diameter": 80.0, "neck_height": 40.0,
            "shoulder_width": 300.0, "shoulder_height": 80.0,
            "pedestal_diameter": 120.0, "pedestal_height": 60.0
        },
        "features": [
            "Ovoid head shape (ellipsoid: slightly taller than wide, deeper front-to-back)",
            "Neck: short cylinder or tapered cone connecting head to shoulders",
            "Shoulders: lofted shape tapering from wide at base to neck width",
            "Facial features (simplified): nose ridge (extruded triangle), brow ridge, chin",
            "Optional: hair volume on top (sphere or spline shell)",
            "Pedestal base: circular or rectangular plinth",
            "Cut flat at shoulder line or mid-chest"
        ],
        "notes": "CadQuery can't do fine sculptural detail like facial features — focus on overall head shape, proportions, and silhouette. Build head as an elongated ellipsoid, add simplified features via boolean operations. The shoulder-to-pedestal transition is the most visually important part."
    },
    {
        "keywords": ["abstract sculpture", "modern sculpture", "abstract art", "desktop sculpture", "art piece"],
        "name": "Abstract Desktop Sculpture",
        "category": "Sculptures & Art",
        "dimensions": {
            "total_height": 200.0, "base_width": 80.0, "base_depth": 80.0,
            "body_width": 60.0, "body_depth": 40.0,
            "twist_angle": 90.0, "wall_thickness": 5.0
        },
        "features": [
            "Flowing organic form created by lofting between rotated cross-sections",
            "Twist effect: each cross-section rotated slightly from the one below",
            "Cross-sections vary between elliptical and rectangular with rounded corners",
            "Optional: hollow interior (shell) for dramatic light/shadow",
            "Smooth transitions between sections (loft blending)",
            "Stable pedestal base (rectangular or circular, polished look)",
            "Optional: through-holes or cutouts for negative space"
        ],
        "notes": "Use STRATEGY 8 (multi-section loft with rotation). Create 4-6 cross-sections at different heights, each slightly rotated and scaled. Loft them together for a smooth twisted form. Can shell to make hollow."
    },
    {
        "keywords": ["figurine", "human figurine", "statue", "person statue", "human statue", "action figure"],
        "name": "Human Figurine / Statue",
        "category": "Sculptures & Art",
        "dimensions": {
            "total_height": 180.0, "base_diameter": 50.0, "base_height": 10.0,
            "head_radius": 12.0,
            "torso_width": 35.0, "torso_depth": 20.0, "torso_height": 50.0,
            "arm_radius": 5.0, "arm_length": 55.0,
            "leg_radius": 7.0, "leg_length": 65.0,
            "neck_radius": 5.0, "neck_height": 8.0
        },
        "features": [
            "Head: sphere proportional to body (1:7.5 ratio to total height)",
            "Torso: lofted ellipses — wide shoulders tapering to narrower waist",
            "Arms: cylinders or tapered cones, attached at shoulder width",
            "Legs: cylinders slightly thicker than arms, hip-width apart",
            "Neck: short cylinder connecting head to torso",
            "Circular pedestal base for stability",
            "Proportions: head=1, torso≈3 heads, legs≈4 heads, arms≈3.5 heads"
        ],
        "notes": "Build each body part as a separate primitive (spheres, cylinders, lofted ellipses) then union them together. Position using translate. Arms can be angled slightly outward. Simple geometric style works better in CadQuery than trying to sculpt realistic anatomy."
    },
    {
        "keywords": ["medal", "medallion", "coin", "commemorative coin", "challenge coin"],
        "name": "Medal / Commemorative Coin",
        "category": "Sculptures & Art",
        "dimensions": {
            "diameter": 50.0, "thickness": 3.0,
            "rim_width": 2.0, "rim_height": 0.5,
            "relief_depth": 1.0, "text_size": 4.0
        },
        "features": [
            "Circular disc with raised rim on both faces",
            "Obverse (front): raised text, emblem, or geometric pattern",
            "Reverse (back): text inscription or secondary design",
            "Edge: smooth, reeded (grooved), or lettered",
            "Raised elements: 0.5-1.5mm above disc surface",
            "Optional: ribbon slot hole at top (for neck ribbon)"
        ],
        "notes": "Start with a cylinder for the disc. Add raised rim using annular extrusion. Use .text() for inscriptions. Geometric emblems can be built from basic shapes (stars = polygon, shields = sketch profiles). Reeded edge = polarArray of small cuts around circumference."
    },
    {
        "keywords": ["obelisk", "monument", "memorial", "pillar monument"],
        "name": "Obelisk / Monument",
        "category": "Sculptures & Art",
        "dimensions": {
            "base_width": 60.0, "base_depth": 60.0, "base_height": 20.0,
            "shaft_width_bot": 40.0, "shaft_width_top": 30.0,
            "shaft_height": 200.0,
            "pyramidion_height": 30.0
        },
        "features": [
            "Stepped pedestal base (2-3 tiers of decreasing platforms)",
            "Tapered square shaft (loft from larger square to smaller)",
            "Pyramidion cap on top (small pyramid)",
            "Inscriptions on front face (engraved text)",
            "Optional: decorative moldings at base-shaft junction",
            "Slightly tapered — about 1mm narrower per 30mm of height"
        ],
        "notes": "Classic obelisk is a loft from a square cross-section to a smaller square, topped with a small pyramid. The base is 2-3 stacked rectangular platforms. Very achievable in CadQuery."
    },
    {
        "keywords": ["plaque", "wall plaque", "award plaque", "name plaque", "sign"],
        "name": "Award Plaque / Wall Sign",
        "category": "Sculptures & Art",
        "dimensions": {
            "width": 200.0, "height": 150.0, "thickness": 12.0,
            "border_width": 10.0, "border_depth": 3.0,
            "text_size": 12.0, "text_depth": 1.5,
            "corner_radius": 8.0
        },
        "features": [
            "Rectangular or shield-shaped base plate",
            "Raised border frame around edges",
            "Engraved or raised text (title, name, date)",
            "Optional: recessed nameplate area in different material",
            "Mounting holes on back (countersunk, 2-4 holes)",
            "Decorative elements: stars, laurel wreath outline, logo"
        ],
        "notes": "Strategy 11 (relief sculpture). Start with a rounded rectangle, add raised frame using boolean. Use .text() for inscriptions. Shield shape can be done with a sketch profile (rect bottom, pointed or arched top)."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  BUILDINGS & ARCHITECTURE
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["house", "house model", "residential house", "cottage", "home model"],
        "name": "Residential House Model",
        "category": "Architecture",
        "dimensions": {
            "width": 200.0, "depth": 150.0, "wall_height": 80.0,
            "roof_height": 50.0, "wall_thickness": 5.0,
            "window_width": 20.0, "window_height": 25.0,
            "door_width": 25.0, "door_height": 40.0,
            "roof_overhang": 10.0, "chimney_size": 15.0
        },
        "features": [
            "Rectangular main volume with gabled (triangular) roof",
            "Windows: 2-3 on front face, 1-2 on each side (rectangular cutouts)",
            "Front door: centered on front face, ground level",
            "Gabled roof: triangular cross-section, extends beyond walls (overhang)",
            "Chimney: small rectangular prism on one side of roof",
            "Optional: porch/veranda extending from front (flat roof, columns)",
            "Optional: garage wing attached to one side",
            "Shutters beside windows (thin raised rectangles)"
        ],
        "notes": "Main box → cut windows and door → add triangular prism roof (extrude triangle profile) → add chimney box. The roof is a triangular cross-section extruded along the building depth. This is Strategy 9."
    },
    {
        "keywords": ["skyscraper", "skyscraper model", "office tower", "high rise", "tall building", "tower building"],
        "name": "Skyscraper / Office Tower Model",
        "category": "Architecture",
        "dimensions": {
            "base_width": 80.0, "base_depth": 80.0,
            "total_height": 400.0, "num_floors": 40,
            "floor_height": 10.0,
            "window_width": 6.0, "window_height": 7.0,
            "setback_height": 250.0, "setback_inset": 10.0,
            "crown_height": 30.0
        },
        "features": [
            "Tall rectangular tower with window grid on all 4 faces",
            "Lobby level: taller ground floor with large entrance opening",
            "Setback: upper floors narrower than lower floors",
            "Window grid: rows of rectangular recesses on each face",
            "Horizontal floor lines (thin grooves) every floor",
            "Mechanical floor: solid band without windows every 10-15 floors",
            "Crown/parapet: distinctive top treatment (stepped, pointed, or flat)",
            "Optional: antenna/spire on top"
        ],
        "notes": "Stack boxes with decreasing widths for setbacks. Use loops to cut window arrays on each face. Add floor line grooves. The crown gives character — can be a simple chamfered top, a stepped pyramid, or a spire loft."
    },
    {
        "keywords": ["church", "cathedral", "chapel", "church model", "cathedral model", "gothic church"],
        "name": "Church / Cathedral Model",
        "category": "Architecture",
        "dimensions": {
            "nave_length": 200.0, "nave_width": 80.0, "nave_height": 100.0,
            "tower_width": 40.0, "tower_height": 160.0,
            "transept_length": 120.0, "transept_width": 40.0,
            "apse_radius": 40.0, "apse_height": 80.0,
            "roof_pitch": 45.0, "window_width": 10.0
        },
        "features": [
            "Cruciform (cross-shaped) floor plan: long nave + perpendicular transept",
            "Front tower(s): one or two square towers flanking entrance",
            "Gabled roof along nave and transept",
            "Apse: semicircular extension at east end (half-cylinder capped with half-dome)",
            "Rose window: large circular recess on front face",
            "Pointed arch windows along nave sides (simplified as tall narrow cutouts)",
            "Bell tower: tallest element, with arched openings near top",
            "Flying buttresses on sides (optional, for Gothic style)",
            "Front entrance: large arched doorway"
        ],
        "notes": "Build as intersecting rectangular volumes (nave + transept = cross plan). Add tower(s) at front. Apse is a half-cylinder at the back. Gabled roofs are triangular prism extrusions. Windows are rectangular or pointed-arch cutouts."
    },
    {
        "keywords": ["castle", "castle model", "medieval castle", "fortress"],
        "name": "Medieval Castle Model",
        "category": "Architecture",
        "dimensions": {
            "outer_wall_length": 250.0, "outer_wall_width": 200.0, "outer_wall_height": 60.0,
            "wall_thickness": 8.0,
            "tower_radius": 25.0, "tower_height": 90.0,
            "keep_width": 60.0, "keep_height": 80.0,
            "gate_width": 30.0, "gate_height": 40.0,
            "merlon_width": 8.0, "merlon_height": 10.0, "merlon_spacing": 12.0
        },
        "features": [
            "Outer curtain walls forming rectangular enclosure",
            "Corner towers: cylindrical, taller than walls, with conical or crenellated tops",
            "Gatehouse: thicker section in front wall with arched opening",
            "Central keep (tallest structure): rectangular or square tower inside walls",
            "Crenellations (battlements): rectangular merlons along tops of all walls/towers",
            "Arrow slits: narrow vertical cuts in walls and towers",
            "Courtyard: open space between walls and keep",
            "Optional: drawbridge (flat plate in front of gate), moat (groove around base)"
        ],
        "notes": "Build walls as rectangular shells (box minus inner box). Place cylinder towers at corners. Cut gate arch from front wall. Add merlons as small boxes along wall tops using loops. The keep is a central box/tower. This is a great Strategy 7 (multi-boolean assembly) project."
    },
    {
        "keywords": ["lighthouse", "lighthouse model", "beacon tower"],
        "name": "Lighthouse Model",
        "category": "Architecture",
        "dimensions": {
            "base_radius": 30.0, "top_radius": 18.0,
            "tower_height": 200.0, "wall_thickness": 5.0,
            "gallery_radius": 25.0, "gallery_height": 5.0,
            "lantern_radius": 15.0, "lantern_height": 30.0,
            "dome_radius": 15.0,
            "door_width": 15.0, "door_height": 30.0
        },
        "features": [
            "Tapered cylindrical tower (wider at base, narrower at top)",
            "Gallery platform: ring extending beyond tower top with railing",
            "Lantern room: octagonal or cylindrical glass house above gallery",
            "Dome cap on top of lantern room",
            "Entrance door at base (arched top)",
            "Small windows spiraling up tower (rectangular cutouts)",
            "Horizontal painted stripes (colored bands, or thin grooves)",
            "Base platform or rock foundation"
        ],
        "notes": "Loft between two circles (large at bottom, small at top) for the tapered tower. Gallery is an annular extrusion wider than the tower top. Lantern room is a polygon extrusion. Dome is a half-sphere. Windows can be cut as small rectangles spiraling up."
    },
    {
        "keywords": ["bridge", "bridge model", "arch bridge", "stone bridge", "foot bridge"],
        "name": "Arch Bridge Model",
        "category": "Architecture",
        "dimensions": {
            "total_span": 300.0, "deck_width": 60.0, "deck_thickness": 8.0,
            "arch_rise": 60.0, "arch_thickness": 15.0,
            "pier_width": 30.0, "pier_height": 50.0, "pier_depth": 60.0,
            "railing_height": 20.0, "railing_post_spacing": 30.0,
            "num_arches": 3
        },
        "features": [
            "Multiple semicircular arches supporting the deck",
            "Flat deck/roadway on top of arches",
            "Stone piers between arches (rectangular supports)",
            "Abutments at each end (larger end supports)",
            "Railings along both sides of deck (posts + top rail)",
            "Spandrel walls between arch and deck (filled or open)",
            "Keystone detail at top of each arch (optional)"
        ],
        "notes": "Each arch is a swept rectangle along a semicircular path. Piers are boxes between arches. Deck is a long flat box on top. Railings are loops of thin cylinders/boxes. Strategy 6 (sweep) for arches + Strategy 7 (assembly) for the whole bridge."
    },
    {
        "keywords": ["pyramid", "pyramid model", "egyptian pyramid", "great pyramid"],
        "name": "Pyramid Model",
        "category": "Architecture",
        "dimensions": {
            "base_side": 200.0, "height": 130.0,
            "entrance_width": 15.0, "entrance_height": 20.0,
            "tip_truncation": 3.0
        },
        "features": [
            "Square base tapering to a point (or slightly truncated tip)",
            "Smooth faces — 4 triangular sides meeting at apex",
            "Optional: entrance opening on one face (north side traditionally)",
            "Optional: stepped layers instead of smooth sides (step pyramid variant)",
            "Base platform/foundation slightly larger than pyramid base",
            "Sand/ground base plate"
        ],
        "notes": "Simple loft from a square to a very small square (or near-point) at the top. For stepped pyramid: stack decreasing-size rectangular platforms. The Great Pyramid has a 51.8° slope angle."
    },
    {
        "keywords": ["dome", "dome model", "cupola", "dome building", "capitol dome", "mosque dome"],
        "name": "Dome / Cupola Model",
        "category": "Architecture",
        "dimensions": {
            "dome_radius": 80.0, "dome_height": 60.0,
            "drum_radius": 80.0, "drum_height": 30.0,
            "wall_thickness": 5.0,
            "oculus_radius": 10.0,
            "column_count": 12, "column_radius": 5.0,
            "lantern_height": 20.0
        },
        "features": [
            "Hemispherical or slightly pointed dome shell (hollow inside)",
            "Cylindrical drum base supporting the dome (with window openings)",
            "Optional: oculus (circular opening at dome apex, like the Pantheon)",
            "Optional: lantern (small structure sitting on top of dome)",
            "Coffers (recessed square panels on interior, decorative)",
            "Columns or pilasters around drum exterior",
            "Base/entablature ring connecting dome to supporting structure"
        ],
        "notes": "Dome = half-sphere minus a slightly smaller inner half-sphere (shell). The drum is a cylinder with window cuts below the dome. For a pointed dome, loft between a circle and a smaller circle above. Oculus is a cylindrical cut through the apex."
    },
    {
        "keywords": ["column", "pillar", "greek column", "roman column", "doric column", "ionic column", "corinthian column", "classical column"],
        "name": "Classical Column (Doric/Ionic/Corinthian)",
        "category": "Architecture",
        "dimensions": {
            "total_height": 250.0,
            "shaft_radius_bottom": 20.0, "shaft_radius_top": 17.0,
            "shaft_height": 180.0,
            "base_radius": 25.0, "base_height": 15.0,
            "capital_radius": 25.0, "capital_height": 20.0,
            "plinth_width": 55.0, "plinth_height": 10.0,
            "num_flutes": 20, "flute_radius": 4.0
        },
        "features": [
            "Square plinth (lowest block)",
            "Molded base (torus + cylinder stack for Ionic/Corinthian; simple for Doric)",
            "Tapered shaft with entasis (slight inward curve, thinner at top)",
            "Vertical fluting: 20 concave grooves around shaft circumference",
            "Capital (top): Doric=simple plate+echinus, Ionic=scroll volutes, Corinthian=acanthus leaves",
            "Abacus: square flat block at very top of capital"
        ],
        "notes": "Revolution profile for the full column. Fluting done by cutting cylinders arranged in a polar array around the shaft. Capital style depends on order: Doric is simplest (chamfered cylinder), Ionic has scroll shapes, Corinthian is most ornate. Focus on proportions — shaft height is typically 6× (Doric) to 10× (Corinthian) the shaft diameter."
    },
    {
        "keywords": ["arch", "roman arch", "archway", "triumphal arch", "gothic arch"],
        "name": "Architectural Arch / Archway",
        "category": "Architecture",
        "dimensions": {
            "span": 100.0, "rise": 50.0, "depth": 30.0,
            "pier_width": 20.0, "pier_height": 80.0,
            "arch_thickness": 15.0,
            "keystone_width": 15.0, "keystone_depth": 5.0
        },
        "features": [
            "Semicircular (Roman) or pointed (Gothic) arch opening",
            "Two vertical piers/pillars supporting the arch",
            "Voussoir stones (wedge-shaped blocks forming the arch, decorative)",
            "Keystone at apex (central wedge, often larger/decorated)",
            "Imposts: horizontal molding where arch meets pier",
            "Optional: spandrels filled or with relief medallions",
            "Entablature/cornice above arch"
        ],
        "notes": "The arch is a sweep of a rectangular cross-section along a semicircular path. Piers are simple boxes. For a Gothic pointed arch, use two arcs meeting at a point instead of a semicircle. Keystone can be a trapezoidal extrusion at the apex."
    },
    {
        "keywords": ["pagoda", "pagoda model", "japanese pagoda", "chinese pagoda", "temple pagoda"],
        "name": "Pagoda / Tiered Tower",
        "category": "Architecture",
        "dimensions": {
            "base_width": 100.0, "base_depth": 100.0,
            "num_tiers": 5, "tier_height": 30.0,
            "tier_shrink": 0.8,
            "roof_overhang": 15.0, "roof_thickness": 3.0, "roof_curve_rise": 8.0,
            "spire_height": 30.0, "spire_base_radius": 8.0
        },
        "features": [
            "Stacked tiers, each smaller than the one below (scaling factor ~0.8×)",
            "Upward-curving roofs extending beyond walls at each tier",
            "Roof edges curve upward at corners (characteristic swept tips)",
            "Central supporting structure (hidden or visible)",
            "Spire/finial on top (narrow pointed element)",
            "Balconies/railings at each tier (optional)",
            "Door/entrance arch on ground floor front face"
        ],
        "notes": "Build each tier as a box (walls) + wider roof plate. Stack tiers with decreasing size. The swept roof tips are the signature element — approximate with chamfered or angled cuts on roof corners. Top the whole structure with a conical or tapered spire."
    },
    {
        "keywords": ["windmill", "windmill model", "dutch windmill", "wind mill"],
        "name": "Windmill Model",
        "category": "Architecture",
        "dimensions": {
            "tower_base_radius": 35.0, "tower_top_radius": 20.0,
            "tower_height": 150.0,
            "cap_radius": 25.0, "cap_height": 30.0,
            "blade_length": 100.0, "blade_width": 15.0, "blade_thickness": 3.0,
            "hub_radius": 8.0,
            "door_width": 18.0, "door_height": 35.0,
            "platform_height": 10.0
        },
        "features": [
            "Tapered tower: cylindrical or octagonal, wider at base",
            "Rotating cap on top (conical or dome shape)",
            "4 or 6 sails/blades attached to hub on cap front",
            "Each blade: long thin rectangle or tapered plank",
            "Observation platform/gallery around tower mid-height or at cap level",
            "Door at base, small windows ascending",
            "Optional: tail pole extending from cap rear (for wind direction)"
        ],
        "notes": "Tower: loft between circles/octagons. Cap: cone or half-sphere. Blades: thin boxes rotated 90° apart from a central hub cylinder. Use .rotate() to position each blade. The gallery is an annular ring around the tower."
    },
    {
        "keywords": ["eiffel tower", "eiffel tower model", "paris tower"],
        "name": "Eiffel Tower Model (Simplified)",
        "category": "Architecture",
        "dimensions": {
            "base_width": 120.0, "total_height": 330.0,
            "first_platform_height": 60.0, "first_platform_width": 70.0,
            "second_platform_height": 120.0, "second_platform_width": 40.0,
            "top_section_width": 15.0,
            "leg_width": 15.0, "leg_thickness": 10.0,
            "antenna_height": 30.0
        },
        "features": [
            "4 curved legs meeting at the top, spreading wide at base",
            "First observation platform at ~1/5 height",
            "Second observation platform at ~1/3 height",
            "Lattice structure (simplified as tapered box legs with cutouts)",
            "Arched opening between legs at first platform level",
            "Antenna/spire extending from top",
            "Each leg curves inward — use loft or tapered profile"
        ],
        "notes": "Simplified approach: 4 tapered box legs positioned at corners, angled inward. Connect with platforms (flat plates) at two heights. The lattice ironwork can be suggested by cutting rectangular windows into the legs. Top section is a simple tapered box with antenna cylinder."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  LANDMARKS & MONUMENTS
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["statue of liberty", "liberty statue"],
        "name": "Statue of Liberty (Simplified)",
        "category": "Landmarks",
        "dimensions": {
            "total_height": 300.0, "pedestal_height": 90.0,
            "pedestal_base_width": 80.0, "pedestal_top_width": 50.0,
            "figure_height": 210.0, "head_radius": 15.0,
            "crown_radius": 20.0, "crown_points": 7,
            "torch_height": 40.0, "arm_length": 70.0,
            "tablet_width": 15.0, "tablet_height": 30.0
        },
        "features": [
            "Trapezoidal pedestal (wider at base, narrower at top)",
            "Robed figure: cylindrical body with draped effect (tapered cone or loft)",
            "Right arm raised holding torch (cylinder arm + flame shape on top)",
            "Left arm holding tablet against body (flat box)",
            "Crown with 7 rays/spikes radiating outward",
            "Head: sphere with simple features",
            "Flowing robe creates wider base to figure"
        ],
        "notes": "Highly simplified: pedestal = tapered box (loft), body = tapered cylinder (robe), raised arm = angled cylinder, torch = small cone on top. Crown spikes = thin boxes in polarArray around head sphere. Focus on iconic silhouette, not detail."
    },
    {
        "keywords": ["big ben", "clock tower", "elizabeth tower"],
        "name": "Big Ben / Elizabeth Tower Model",
        "category": "Landmarks",
        "dimensions": {
            "base_width": 50.0, "total_height": 300.0,
            "main_shaft_width": 40.0, "main_shaft_height": 200.0,
            "clock_face_diameter": 25.0,
            "belfry_width": 45.0, "belfry_height": 40.0,
            "spire_height": 60.0, "spire_base_width": 30.0
        },
        "features": [
            "Square tower shaft — main tall rectangular body",
            "Clock faces on all 4 sides near the top (circular recesses or raised rings)",
            "Belfry section above clock (arched openings on each face)",
            "Pointed spire/roof at very top (pyramid or octagonal cone)",
            "Decorative horizontal bands/cornices separating sections",
            "Gothic window details (simplified as pointed arch cutouts)",
            "Base plinth slightly wider than tower"
        ],
        "notes": "Stacked rectangular boxes of slightly varying widths. Clock faces are circular recesses on 4 faces. Belfry has arched window openings. Spire is a loft from square to small point. Add horizontal groove lines for floor divisions."
    },
    {
        "keywords": ["taj mahal", "taj mahal model"],
        "name": "Taj Mahal Model (Simplified)",
        "category": "Landmarks",
        "dimensions": {
            "platform_width": 250.0, "platform_depth": 250.0, "platform_height": 20.0,
            "main_building_width": 100.0, "main_building_height": 80.0,
            "dome_radius": 40.0, "dome_height": 50.0,
            "minaret_radius": 8.0, "minaret_height": 150.0,
            "arch_width": 25.0, "arch_height": 50.0,
            "num_minarets": 4
        },
        "features": [
            "Large raised platform/terrace base",
            "Central cubic main building with chamfered corners",
            "Grand onion dome on top (pointed dome, not hemisphere)",
            "4 minarets at platform corners (tall thin cylinders with small domes)",
            "Large iwan arches on each face (pointed arch recesses)",
            "Smaller decorative arches flanking main arch",
            "Small domed chattris (kiosks) on platform corners near main building"
        ],
        "notes": "Platform is a flat box. Main building is a chamfered box or octagonal prism. The onion dome is the key feature — loft from a circle up to a point with a bulging spline profile (wider than hemisphere then narrowing). Minarets are simple cylinders capped with small domes."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  FURNITURE (Phase 3 Expansion)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["office chair", "desk chair", "swivel chair", "ergonomic chair"],
        "name": "Office Desk Chair (Simplified)",
        "category": "Furniture",
        "dimensions": {
            "seat_width": 480.0, "seat_depth": 450.0, "seat_height": 450.0,
            "backrest_width": 460.0, "backrest_height": 550.0, "backrest_thickness": 25.0,
            "armrest_length": 250.0, "armrest_width": 60.0, "armrest_height": 200.0,
            "base_radius": 320.0, "caster_count": 5, "gas_lift_diameter": 50.0
        },
        "features": [
            "5-star base with caster wheels (5 arms radiating from center)",
            "Gas lift cylinder connecting base to seat mechanism",
            "Contoured seat pan with rounded front edge for comfort",
            "Curved backrest with lumbar support bulge",
            "Adjustable armrests (simplified as fixed positions)",
            "Tilt mechanism housing under seat",
            "Rounded edges on all user-contact surfaces"
        ],
        "notes": "Build the 5-star base using polar array of 5 arm extrusions. Gas lift is a cylinder. Seat is a box with filleted edges. Backrest is a curved panel. Armrests are L-shaped supports."
    },
    {
        "keywords": ["bookshelf", "book shelf", "shelving unit", "shelf"],
        "name": "Bookshelf (4-Shelf)",
        "category": "Furniture",
        "dimensions": {
            "total_width": 800.0, "total_depth": 300.0, "total_height": 1200.0,
            "shelf_thickness": 18.0, "side_thickness": 18.0,
            "shelf_count": 4, "shelf_spacing": 280.0,
            "back_panel_thickness": 6.0
        },
        "features": [
            "Two vertical side panels (full height)",
            "4 horizontal shelf panels at even spacing",
            "Thin back panel for rigidity",
            "Adjustable shelf pin holes (5mm holes in vertical columns)",
            "Chamfered front edges on shelves for clean look",
            "Anti-tip bracket mounting holes on back"
        ],
        "notes": "Build as two vertical side boxes, then union shelf boxes between them. Add thin back panel. Cut arrays of shelf-pin holes into inner faces of sides."
    },
    {
        "keywords": ["dining table", "table", "kitchen table", "desk table"],
        "name": "Dining Table",
        "category": "Furniture",
        "dimensions": {
            "top_length": 1400.0, "top_width": 800.0, "top_thickness": 30.0,
            "top_height": 750.0, "leg_width": 60.0, "leg_depth": 60.0,
            "apron_height": 80.0, "apron_thickness": 20.0,
            "leg_inset": 50.0, "corner_radius": 5.0
        },
        "features": [
            "Rectangular tabletop with rounded edges",
            "4 tapered legs (wider at top, slightly narrower at bottom)",
            "Apron rails on all 4 sides connecting leg tops",
            "Tabletop overhangs apron by 30-50mm on each side",
            "Chamfered bottom edges of legs (anti-chip)",
            "Optional: cable management grommet hole in top for desk use"
        ],
        "notes": "Tabletop is a box with filleted edges at top height. Four legs are tapered boxes from ground to underside of apron. Apron rails connect leg tops. Tabletop sits on top of apron."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  KITCHEN & COOKWARE (Phase 3 Expansion)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["coffee mug", "mug", "tea mug", "cup"],
        "name": "Coffee Mug",
        "category": "Kitchen & Cookware",
        "dimensions": {
            "outer_diameter": 85.0, "height": 95.0, "wall_thickness": 3.0,
            "bottom_thickness": 4.0, "handle_width": 12.0,
            "handle_height": 65.0, "handle_depth": 30.0,
            "lip_thickness": 2.0, "foot_ring_diameter": 70.0, "foot_ring_height": 2.0
        },
        "features": [
            "Cylindrical body, slightly tapered (wider at top)",
            "D-shaped handle on one side with comfortable grip",
            "Rolled lip/rim at top edge for drinking comfort",
            "Recessed foot ring on bottom for stability",
            "Smooth interior with no sharp transitions",
            "Handle attached at 2 points (top and bottom of handle arc)"
        ],
        "notes": "Use revolution profile for main body. Handle is a swept C/D-shape attached to the side. The body should taper slightly — bottom diameter ~80mm, top diameter ~85mm."
    },
    {
        "keywords": ["cutting board", "chopping board"],
        "name": "Cutting Board",
        "category": "Kitchen & Cookware",
        "dimensions": {
            "length": 400.0, "width": 280.0, "thickness": 18.0,
            "juice_groove_width": 8.0, "juice_groove_depth": 3.0,
            "juice_groove_inset": 25.0, "handle_hole_diameter": 25.0,
            "corner_radius": 15.0
        },
        "features": [
            "Flat rectangular board with generously rounded corners",
            "Juice groove channel running around the perimeter (inset 25mm from edges)",
            "Handle hole at one end for hanging",
            "Slightly raised non-slip feet (4 small rubber pad recesses)",
            "All edges rounded for food safety (no sharp corners ≥ R3mm)",
            "Smooth top cutting surface"
        ],
        "notes": "Flat box with large corner fillets. Cut juice groove as a rounded rectangular channel on top face. Add through-hole near one short edge for hanging."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  TOYS & GAMES (Phase 3 Expansion)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["lego brick", "building brick", "lego block", "toy brick"],
        "name": "Building Brick (LEGO-Compatible 2×4)",
        "category": "Toys & Games",
        "dimensions": {
            "stud_pitch": 8.0, "stud_diameter": 4.8, "stud_height": 1.8,
            "brick_height": 9.6, "wall_thickness": 1.5,
            "tube_outer_diameter": 6.5, "tube_inner_diameter": 4.8,
            "cols": 4, "rows": 2
        },
        "features": [
            "Rectangular hollow brick body (32×16×9.6mm for 2×4)",
            "8 cylindrical studs on top in 2×4 grid (8mm pitch)",
            "3 anti-stud tubes on underside between stud columns",
            "Uniform wall thickness ~1.5mm",
            "Very small fillets on all edges (0.2mm — injection mold style)",
            "Logo recess on each stud top (simplified as tiny circle)"
        ],
        "notes": "Outer box, hollow inside. Studs are small cylinders on top in grid. Anti-stud tubes on bottom for clutch mechanism. Precise 8mm grid is critical for compatibility."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  LIGHTING (Phase 3 Expansion)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["desk lamp", "table lamp", "reading lamp"],
        "name": "Desk Lamp (Modern)",
        "category": "Lighting & Lamps",
        "dimensions": {
            "base_diameter": 150.0, "base_height": 15.0,
            "stem_diameter": 12.0, "stem_height": 350.0,
            "shade_bottom_diameter": 120.0, "shade_top_diameter": 60.0,
            "shade_height": 100.0, "shade_wall_thickness": 2.0,
            "cable_hole_diameter": 8.0
        },
        "features": [
            "Weighted circular base with anti-slip rubber bottom",
            "Slim cylindrical stem rising from base center",
            "Conical shade (empire style) at top — wider at bottom, narrower at top",
            "Bulb socket recess inside shade (cylinder hole at top of shade)",
            "Cable hole through base for cord exit",
            "On/off switch on cord or base",
            "Smooth transitions between base, stem, and shade"
        ],
        "notes": "Base is a flat cylinder at Z=0. Stem is a thin cylinder. Shade is a lofted cone (large circle at bottom, small circle at top), hollowed. Union all three sections."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  CONTAINERS (Phase 3 Expansion)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["toolbox", "tool box", "tool case", "tackle box"],
        "name": "Toolbox (Portable)",
        "category": "Containers & Packaging",
        "dimensions": {
            "length": 400.0, "width": 200.0, "height": 180.0,
            "wall_thickness": 3.0, "handle_width": 20.0, "handle_height": 30.0,
            "latch_width": 30.0, "latch_height": 15.0,
            "tray_height": 50.0, "divider_count": 3
        },
        "features": [
            "Main box body with hinged lid (simplified as separate top half)",
            "Fold-down carrying handle on top center",
            "Two front latches/clasps for closure",
            "Internal removable tray with dividers",
            "Reinforced corners (thicker material or ribs)",
            "Drainage holes in bottom corners",
            "Label holder slot on front face"
        ],
        "notes": "Body is a shelled box. Lid is a separate shelled box that sits on top. Handle is a U-shape on lid. Latches are small raised features on front face. Add dividers as internal walls."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  SPORTS EQUIPMENT (Phase 3 Expansion)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["dumbbell", "weight", "hand weight", "free weight"],
        "name": "Dumbbell (Hex)",
        "category": "Sports Equipment",
        "dimensions": {
            "total_length": 280.0, "handle_diameter": 32.0, "handle_length": 130.0,
            "head_diameter": 80.0, "head_length": 60.0,
            "knurling_length": 100.0, "collar_width": 10.0
        },
        "features": [
            "Hexagonal weight heads at each end (anti-roll design)",
            "Contoured cylindrical grip handle in center",
            "Knurled grip texture on handle surface",
            "Smooth collar transitions between handle and weight heads",
            "Flat hex faces on weight heads for stable resting",
            "Chrome-plated handle, rubber-coated heads (surface zones)"
        ],
        "notes": "Handle is a cylinder. Weight heads are hexagonal prisms (6-sided polygon extruded). Add collar rings between handle and heads. Knurling is simplified as grip grooves on handle."
    },
    {
        "keywords": ["skateboard", "longboard", "skate deck"],
        "name": "Skateboard Deck",
        "category": "Sports Equipment",
        "dimensions": {
            "deck_length": 800.0, "deck_width": 200.0, "deck_thickness": 10.0,
            "nose_kick_height": 40.0, "tail_kick_height": 45.0,
            "concave_depth": 8.0, "truck_hole_diameter": 5.0,
            "truck_hole_spacing_x": 42.0, "truck_hole_spacing_y": 155.0,
            "wheelbase": 355.0
        },
        "features": [
            "Elongated oval-shaped deck with rounded nose and tail",
            "Nose kick (upward curve at front end)",
            "Tail kick (upward curve at back end, slightly steeper)",
            "Concave cross-section (edges slightly higher than center for grip)",
            "4 truck mounting holes in two groups of 4 (standard old-school pattern)",
            "Grip tape area on top (full surface minus nose/tail tips)",
            "Rounded edges all around for safety"
        ],
        "notes": "Deck is a lofted or spline-extruded shape. The cross-section is slightly concave. Nose and tail kicks are upward curves at each end. Mounting holes in standard pattern."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  JEWELRY (Phase 3 Expansion)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["ring", "wedding ring", "band ring", "signet ring"],
        "name": "Band Ring (Classic)",
        "category": "Jewelry & Accessories",
        "dimensions": {
            "inner_diameter": 18.0, "band_width": 5.0, "band_thickness": 2.0,
            "outer_diameter": 22.0
        },
        "features": [
            "Simple torus/ring band with comfortable rounded cross-section",
            "Smooth polished outer surface",
            "Slightly domed (comfort-fit) interior profile",
            "Optional: engraving recess on inner surface",
            "Optional: setting platform on top for stone"
        ],
        "notes": "Create a revolution profile: draw the band cross-section (rounded rectangle ~5mm wide × 2mm thick) offset from the Y-axis by the ring radius, then revolve 360° around Y."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  MUSICAL INSTRUMENTS (Phase 3 Expansion)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["guitar", "acoustic guitar", "guitar body"],
        "name": "Acoustic Guitar Body (Simplified)",
        "category": "Musical Instruments",
        "dimensions": {
            "body_length": 500.0, "upper_bout_width": 280.0,
            "lower_bout_width": 380.0, "waist_width": 240.0,
            "body_depth": 100.0, "top_thickness": 3.0,
            "sound_hole_diameter": 100.0, "sound_hole_y_offset": 60.0,
            "neck_width": 50.0, "neck_length": 480.0
        },
        "features": [
            "Figure-8 body shape (upper bout + waist + lower bout)",
            "Circular sound hole on top face of lower bout area",
            "Bridge pad: raised rectangle below sound hole",
            "Neck stub extending from upper bout",
            "Curved top surface with slight arch",
            "Hollow interior resonance chamber",
            "Decorative rosette ring around sound hole"
        ],
        "notes": "Body is best built by lofting or spline-extruding the figure-8 outline. Shell to hollow. Sound hole is a through-cut on the top face. Bridge is a small raised box. Neck is a tapered rectangular extrusion."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  MEDICAL & SCIENTIFIC (Phase 3 Expansion)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["test tube rack", "tube rack", "lab rack", "tube holder"],
        "name": "Test Tube Rack",
        "category": "Medical & Scientific",
        "dimensions": {
            "rack_length": 200.0, "rack_width": 80.0, "rack_height": 80.0,
            "tube_diameter": 16.0, "tube_count_x": 6, "tube_count_y": 2,
            "tube_spacing": 25.0, "wall_thickness": 3.0,
            "base_thickness": 5.0, "support_rod_diameter": 8.0
        },
        "features": [
            "Two horizontal plates with arrays of tube holes (top and middle)",
            "4 vertical support rods at corners connecting the plates",
            "Angled back rest to tilt tubes slightly",
            "Drainage holes below each tube position",
            "Label strip slot on front face",
            "Stable wide base for bench use"
        ],
        "notes": "Top plate and middle plate are flat boxes with arrays of through-holes. 4 corner posts (cylinders) connect the plates. Base extends slightly wider for stability."
    },

    # ─────────────────────────────────────────────────────────────────────────
    #  PIPES & PLUMBING (Phase 3 Expansion)
    # ─────────────────────────────────────────────────────────────────────────
    {
        "keywords": ["pipe elbow", "elbow fitting", "90 degree elbow", "pipe bend"],
        "name": "90° Pipe Elbow Fitting",
        "category": "Pipes & Plumbing",
        "dimensions": {
            "nominal_bore": 25.0, "outer_diameter": 33.7, "wall_thickness": 3.4,
            "bend_radius": 38.0, "socket_depth": 15.0
        },
        "features": [
            "90-degree swept tube section",
            "Socket ends (slightly wider ID at each end for pipe insertion)",
            "Smooth inner bore with consistent wall thickness through the bend",
            "Orientation marks (small ridge line on outer radius)",
            "Pipe stop shoulder inside each socket end"
        ],
        "notes": "Draw a circle profile (annular ring) and sweep it along a 90° arc path. The sweep path is a quarter-circle on XZ plane. Socket ends are slightly enlarged cylinder bores at each end."
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
# SEARCH ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

def _normalize(text: str) -> str:
    """Lower-case, strip punctuation, collapse whitespace"""
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def search_products(prompt: str, max_results: int = 3) -> List[Dict[str, Any]]:
    """
    Search the product library for entries matching the user's prompt.
    Returns up to max_results best-matching products.
    
    Matching strategy:
    1. Exact keyword phrase match (highest priority)
    2. All-words-present match
    3. Partial word overlap scoring
    """
    query = _normalize(prompt)
    query_words = set(query.split())
    
    scored: List[tuple] = []
    
    for product in PRODUCTS:
        best_score = 0.0
        
        for keyword in product["keywords"]:
            kw_norm = _normalize(keyword)
            kw_words = set(kw_norm.split())
            
            # Exact phrase match → highest score
            if kw_norm in query:
                best_score = max(best_score, 100.0 + len(kw_words))
                continue
            
            # Check if all keyword words appear in query
            if kw_words.issubset(query_words):
                best_score = max(best_score, 50.0 + len(kw_words))
                continue
            
            # Partial overlap: fraction of keyword words found in query
            overlap = len(kw_words & query_words)
            if overlap > 0:
                frac = overlap / len(kw_words)
                best_score = max(best_score, frac * 30.0)
        
        # Also check the product name
        name_norm = _normalize(product["name"])
        name_words = set(name_norm.split())
        name_overlap = len(name_words & query_words)
        if name_overlap > 0:
            frac = name_overlap / len(name_words)
            best_score = max(best_score, frac * 25.0)
        
        # Also check category
        cat_norm = _normalize(product["category"])
        if cat_norm in query:
            best_score = max(best_score, 10.0)
        
        if best_score > 5.0:  # minimum threshold
            scored.append((best_score, product))
    
    # Sort by score descending, take top N
    scored.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored[:max_results]]


def format_product_reference(products: List[Dict[str, Any]]) -> str:
    """
    Format matched products into a reference block for inclusion in the AI prompt.
    """
    if not products:
        return ""
    
    lines = [
        "═══════════════════════════════════════════════════════════════════════════════",
        "REAL-WORLD PRODUCT REFERENCE (from library — use these exact dimensions)",
        "═══════════════════════════════════════════════════════════════════════════════",
        ""
    ]
    
    for i, product in enumerate(products, 1):
        lines.append(f"■ MATCH {i}: {product['name']}  [{product['category']}]")
        lines.append("")
        
        # Dimensions
        lines.append("  DIMENSIONS:")
        for key, value in product["dimensions"].items():
            label = key.replace("_", " ").title()
            unit = "mm" if isinstance(value, (int, float)) and "angle" not in key and "teeth" not in key and "count" not in key and "gram" not in key else ""
            if "gram" in key:
                unit = "g"
            elif "teeth" in key or "count" in key or "num" in key:
                unit = ""
            elif "angle" in key:
                unit = "°"
            lines.append(f"    {label}: {value}{unit}")
        lines.append("")
        
        # Features — emphasized as MANDATORY
        lines.append("  ⚠️  MANDATORY FEATURES (do NOT skip ANY of these):")
        for j, feat in enumerate(product["features"], 1):
            lines.append(f"    {j}. {feat}")
        lines.append("")
        
        # Design notes
        if product.get("notes"):
            lines.append(f"  DESIGN NOTES: {product['notes']}")
            lines.append("")
        
        # Visual & construction knowledge (from product_visual_knowledge module)
        visual_block = format_visual_knowledge(product["name"], product["category"])
        if visual_block:
            lines.append(visual_block)
        
        lines.append("  ─────────────────────────────────────────────────────────────────")
        lines.append("")
    
    lines.append("⚠️  CRITICAL: Every feature listed above MUST appear in your CadQuery code.")
    lines.append("Missing a cutout, port, button, window, or detail = INCOMPLETE design.")
    lines.append("Use the dimensions and features above as your starting point.")
    lines.append("Follow the BUILD STRATEGY to construct the geometry correctly.")
    lines.append("Ensure ALL RECOGNITION FEATURES are present — without them the model looks wrong.")
    lines.append("The user may override specific values — respect their changes.")
    lines.append("═══════════════════════════════════════════════════════════════════════════════")
    
    return "\n".join(lines)


# Convenience
def lookup(prompt: str) -> str:
    """One-call: search + format. Returns empty string if no matches."""
    matches = search_products(prompt)
    return format_product_reference(matches)
