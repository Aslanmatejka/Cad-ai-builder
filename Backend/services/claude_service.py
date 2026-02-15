"""
Claude 3.5 Sonnet Integration Service
Handles natural language to CAD design JSON conversion
"""

from anthropic import Anthropic
from typing import Dict, Any, List, Optional
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import settings
from services.product_library import lookup as product_lookup

class ClaudeService:
    """LLM service for converting natural language to CAD design specifications"""
    
    # Keywords that signal a complex/professional design requiring more tokens & detail
    COMPLEXITY_KEYWORDS_HIGH = [
        "detailed", "professional", "realistic", "engineering", "mechanical",
        "assembly", "multi-part", "industrial", "precision", "production",
        "complex", "intricate", "ornate", "articulated", "functional",
        "threaded", "geared", "hinged", "interlocking", "mechanism",
        "sculpture", "figurine", "cathedral", "castle", "skyscraper",
        "engine", "turbine", "robot", "drone", "weapon", "vehicle",
        "furniture", "cabinet", "chair", "table", "desk",
        "building", "house", "tower", "bridge", "monument",
        "with internal", "hollow", "nested", "moving parts",
        "every detail", "exact replica", "scale model", "to scale",
    ]
    COMPLEXITY_KEYWORDS_MED = [
        "case", "enclosure", "bracket", "mount", "stand", "holder",
        "organizer", "dock", "tray", "rack", "shelf",
        "bottle", "cup", "vase", "trophy", "gear", "knob",
    ]

    def __init__(self):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        self.model = settings.AI_MODEL_NAME

    def _detect_complexity(self, prompt: str) -> str:
        """Classify prompt complexity as 'high', 'medium', or 'standard'."""
        prompt_lower = prompt.lower()
        word_count = len(prompt.split())
        
        # Long prompts with lots of detail are inherently complex
        if word_count > 80:
            return "high"
        
        for kw in self.COMPLEXITY_KEYWORDS_HIGH:
            if kw in prompt_lower:
                return "high"
        
        if word_count > 40:
            return "medium"
        
        for kw in self.COMPLEXITY_KEYWORDS_MED:
            if kw in prompt_lower:
                return "medium"
        
        return "standard"

    def _get_adaptive_tokens(self, complexity: str) -> int:
        """Return higher token limits for complex designs."""
        base = settings.AI_MAX_TOKENS
        if complexity == "high":
            return max(base, 16384)
        elif complexity == "medium":
            return max(base, 12288)
        return base

    def _get_adaptive_temperature(self, complexity: str) -> float:
        """Slightly lower temperature for complex designs to reduce hallucination."""
        if complexity == "high":
            return min(settings.AI_TEMPERATURE, 0.25)
        return settings.AI_TEMPERATURE
        
    def analyze_code_completeness(self, code: str, prompt: str) -> Dict[str, Any]:
        """
        Programmatically analyze generated CadQuery code for feature completeness.
        Returns a dict with is_complete, missing_features, and metrics.
        This is the CODE-LEVEL enforcement — not prompt engineering.
        """
        import re
        
        code_lower = code.lower()
        prompt_lower = prompt.lower()
        
        # Count operations — include ALL cut-like methods
        cut_count = len(re.findall(r'\.cut(?:Blind|ThruAll|Each)?\(', code))
        hole_count = len(re.findall(r'\.(?:hole|cboreHole|cskHole)\(', code))
        cut_count += hole_count  # .hole()/.cboreHole()/.cskHole() are cuts too
        union_count = len(re.findall(r'\.union\(', code))
        fillet_count = len(re.findall(r'\.fillet\(', code))
        chamfer_count = len(re.findall(r'\.chamfer\(', code))
        shell_count = len(re.findall(r'\.shell\(', code))
        translate_count = len(re.findall(r'\.translate\(', code))
        cylinder_count = len(re.findall(r'\.cylinder\(', code))
        slot2d_count = len(re.findall(r'\.slot2D\(', code))
        circle_extrude_count = len(re.findall(r'\.circle\([^)]+\)\s*\.extrude\(', code))
        
        # Sketch shapes used before .cutBlind()/.cutThruAll() — detect round vs rect
        rect_sketch_cut_count = len(re.findall(r'\.rect\([^)]+\)\s*\.cut(?:Blind|ThruAll)\(', code))
        circle_sketch_cut_count = len(re.findall(r'\.circle\([^)]+\)\s*\.cut(?:Blind|ThruAll)\(', code))
        slot_sketch_cut_count = len(re.findall(r'\.slot2D\([^)]+\)\s*\.cut(?:Blind|ThruAll)\(', code))
        
        # Shape variety: count rounded vs rectangular cutters
        # box_cutter: standalone box cutters used with .cut(), also rect sketch-based cuts
        box_cutter_count = len(re.findall(r'(?:cq\.Workplane\([^)]*\)(?:\.[a-zA-Z]+\([^)]*\))*\.box\()', code)) + rect_sketch_cut_count
        # round_cutter: cylinders, slots, circle-extrudes, holes, circle-sketch-cutThruAll
        round_cutter_count = cylinder_count + slot2d_count + circle_extrude_count + hole_count + circle_sketch_cut_count + slot_sketch_cut_count
        
        # Advanced body construction techniques
        spline_count = len(re.findall(r'\.spline\(', code))
        loft_count = len(re.findall(r'\.loft\(', code))
        revolve_count = len(re.findall(r'\.revolve\(', code))
        sweep_count = len(re.findall(r'\.sweep\(', code))
        three_point_arc_count = len(re.findall(r'\.threePointArc\(', code))
        tangent_arc_count = len(re.findall(r'\.tangentArcPoint\(', code))
        ellipse_count = len(re.findall(r'\.ellipse\(', code))
        lineto_count = len(re.findall(r'\.lineTo\(', code))
        
        # Body construction quality score
        advanced_technique_count = spline_count + loft_count + revolve_count + sweep_count + three_point_arc_count + tangent_arc_count
        
        # Does the main body use .box() as its foundation?
        main_body_is_box = bool(re.search(r'(?:body|case|frame|base|main|result)\s*=\s*cq\.Workplane\([^)]+\)\.box\(', code))
        
        # Count non-empty, non-comment code lines
        lines = [l.strip() for l in code.split('\n') if l.strip() and not l.strip().startswith('#')]
        code_lines = len(lines)
        
        total_features = cut_count + union_count
        total_treatments = fillet_count + chamfer_count
        
        missing_features = []
        product_type = "generic"
        
        # ── Product-specific feature checks ──────────────────────────────
        
        # PHONE / TABLET CASE
        if any(kw in prompt_lower for kw in ['phone case', 'phone cover', 'tablet case',
                                               'iphone', 'samsung case', 'pixel case',
                                               'galaxy case', 'phone shell', 'phone bumper',
                                               'smartphone case']):
            product_type = "phone_case"
            if not any(w in code_lower for w in ['usb', 'charging', 'port', 'lightning']):
                missing_features.append("USB-C/charging port cutout on bottom edge (z=0)")
            if not any(w in code_lower for w in ['camera', 'cam_', 'cam ']):
                missing_features.append("camera cutout on back face with raised protective lip")
            if not any(w in code_lower for w in ['speaker', 'grille', 'grill']):
                missing_features.append("speaker grille holes on bottom edge")
            if not any(w in code_lower for w in ['button', 'volume', 'power', 'btn']):
                missing_features.append("side button cutouts (volume up/down on left, power on right)")
            if cut_count < 4:
                missing_features.append(f"only {cut_count} cutouts — a phone case needs at least 5 (USB, camera, speaker, volume, power)")
        
        # LAPTOP / NOTEBOOK COMPUTER
        elif any(kw in prompt_lower for kw in ['laptop', 'notebook computer', 'macbook',
                                                 'chromebook', 'thinkpad']):
            product_type = "laptop"
            if not any(w in code_lower for w in ['screen', 'display', 'lid', 'monitor']):
                missing_features.append("screen/display lid section (upper half of laptop)")
            if not any(w in code_lower for w in ['keyboard', 'key', 'keycap']):
                missing_features.append("keyboard area with key recesses on top face of base")
            if not any(w in code_lower for w in ['trackpad', 'touchpad', 'track_pad']):
                missing_features.append("trackpad/touchpad recessed area below keyboard")
            if not any(w in code_lower for w in ['hinge', 'pivot', 'joint']):
                missing_features.append("hinge mechanism connecting screen to base")
            if not any(w in code_lower for w in ['port', 'usb', 'hdmi', 'jack']):
                missing_features.append("port cutouts on sides (USB, HDMI, headphone jack)")
            if not any(w in code_lower for w in ['vent', 'ventilation', 'grille']):
                missing_features.append("ventilation grille on bottom or sides for cooling")

        # TABLET / IPAD
        elif any(kw in prompt_lower for kw in ['tablet', 'ipad', 'surface pro',
                                                 'galaxy tab', 'fire tablet']):
            product_type = "tablet"
            if not any(w in code_lower for w in ['screen', 'display', 'bezel']):
                missing_features.append("screen area with bezel frame (front face recessed)")
            if not any(w in code_lower for w in ['camera', 'cam_', 'lens']):
                missing_features.append("camera module on back face")
            if not any(w in code_lower for w in ['button', 'volume', 'power', 'btn']):
                missing_features.append("side buttons (power, volume)")
            if not any(w in code_lower for w in ['port', 'usb', 'charging', 'lightning']):
                missing_features.append("charging port cutout on bottom edge")
            if not any(w in code_lower for w in ['speaker', 'grille']):
                missing_features.append("speaker grille cutouts on top/bottom edges")

        # SMARTPHONE / MOBILE PHONE
        elif any(kw in prompt_lower for kw in ['smartphone', 'mobile phone', 'cell phone',
                                                 'iphone', 'android phone', 'pixel phone',
                                                 'galaxy phone']):
            product_type = "smartphone"
            if not any(w in code_lower for w in ['screen', 'display', 'bezel']):
                missing_features.append("screen/display area on front face")
            if not any(w in code_lower for w in ['camera', 'cam_', 'lens']):
                missing_features.append("camera module/island on back (with lens circles)")
            if not any(w in code_lower for w in ['button', 'volume', 'power', 'btn']):
                missing_features.append("side buttons (power on right, volume on left)")
            if not any(w in code_lower for w in ['port', 'usb', 'charging', 'lightning']):
                missing_features.append("USB-C/charging port cutout on bottom edge")
            if not any(w in code_lower for w in ['speaker', 'grille', 'earpiece']):
                missing_features.append("speaker grille holes on bottom + earpiece on top")
            if fillet_count < 2:
                missing_features.append("smartphones need generous rounded corners (fillet all vertical edges R≥4mm)")

        # HEADPHONES / EARBUDS / AUDIO WEARABLE
        elif any(kw in prompt_lower for kw in ['headphone', 'headset', 'earphone',
                                                 'earbud', 'over-ear', 'on-ear',
                                                 'beats', 'airpods max']):
            product_type = "audio_headphones"
            if any(kw in prompt_lower for kw in ['earbud', 'airpod', 'in-ear']):
                # Earbuds — different checks
                if not any(w in code_lower for w in ['stem', 'stalk', 'stick']):
                    missing_features.append("earbud stem/stalk extending downward")
                if not any(w in code_lower for w in ['tip', 'nozzle', 'ear_tip']):
                    missing_features.append("ear tip/nozzle for insertion")
                if not any(w in code_lower for w in ['driver', 'grille', 'speaker', 'mesh']):
                    missing_features.append("speaker driver grille/mesh on inner face")
            else:
                # Over-ear / On-ear headphones
                if not any(w in code_lower for w in ['earcup', 'ear_cup', 'cup', 'earpiece']):
                    missing_features.append("earcup housings (left and right)")
                if not any(w in code_lower for w in ['headband', 'band', 'arc', 'bridge']):
                    missing_features.append("headband/arc connecting the two earcups")
                if not any(w in code_lower for w in ['pad', 'cushion', 'foam']):
                    missing_features.append("ear cushion pads on earcups")
                if not any(w in code_lower for w in ['adjust', 'slider', 'extend', 'telescop']):
                    missing_features.append("headband size adjustment slider/mechanism")
                if not any(w in code_lower for w in ['driver', 'grille', 'mesh', 'vent']):
                    missing_features.append("driver grille/mesh on outer earcup faces")

        # SPEAKER / BLUETOOTH SPEAKER / SOUND SYSTEM
        elif any(kw in prompt_lower for kw in ['speaker', 'bluetooth speaker', 'soundbar',
                                                 'subwoofer', 'studio monitor', 'boombox']):
            product_type = "audio_speaker"
            if not any(w in code_lower for w in ['driver', 'cone', 'woofer', 'tweeter']):
                missing_features.append("speaker driver/cone recessed on front face")
            if not any(w in code_lower for w in ['grille', 'mesh', 'perforate', 'array']):
                missing_features.append("speaker grille or perforated cover on front")
            if not any(w in code_lower for w in ['port', 'bass', 'reflex', 'vent']):
                missing_features.append("bass reflex port/vent (rear or front)")
            if not any(w in code_lower for w in ['foot', 'feet', 'pad', 'stand', 'base']):
                missing_features.append("anti-vibration feet or stand base")
            if not any(w in code_lower for w in ['button', 'control', 'knob', 'volume']):
                missing_features.append("control buttons or volume knob")

        # SMARTWATCH / WEARABLE WATCH
        elif any(kw in prompt_lower for kw in ['smartwatch', 'smart watch', 'watch',
                                                 'apple watch', 'fitness band', 'fitness tracker',
                                                 'wristband', 'wearable']):
            product_type = "wearable_watch"
            if not any(w in code_lower for w in ['face', 'dial', 'display', 'screen', 'crystal']):
                missing_features.append("watch face/display area (recessed circle or rounded rectangle)")
            if not any(w in code_lower for w in ['band', 'strap', 'lug', 'attachment']):
                missing_features.append("band/strap attachment lugs (top and bottom of case)")
            if not any(w in code_lower for w in ['crown', 'button', 'digital_crown', 'pusher']):
                missing_features.append("side crown/button (digital crown or pushers)")
            if not any(w in code_lower for w in ['back', 'sensor', 'case_back', 'rear']):
                missing_features.append("case back with sensor window or cover")
            if revolve_count == 0 and fillet_count < 3:
                missing_features.append("watch cases need smooth rounded edges — use .fillet() generously on all edges")

        # MOUSE / COMPUTER MOUSE
        elif any(kw in prompt_lower for kw in ['mouse', 'computer mouse', 'gaming mouse',
                                                 'wireless mouse', 'ergonomic mouse', 'trackball']):
            product_type = "peripheral_mouse"
            if not any(w in code_lower for w in ['button', 'click', 'left_button', 'right_button']):
                missing_features.append("left and right click buttons (split top surface)")
            if not any(w in code_lower for w in ['scroll', 'wheel', 'roller']):
                missing_features.append("scroll wheel between buttons")
            if not any(w in code_lower for w in ['sensor', 'optical', 'bottom', 'base_plate']):
                missing_features.append("sensor window/optical opening on bottom")
            if not any(w in code_lower for w in ['skid', 'feet', 'foot', 'pad', 'glide']):
                missing_features.append("glide pads/feet on bottom surface")
            if loft_count == 0 and revolve_count == 0:
                missing_features.append("BODY SHAPE: Mouse needs ergonomic .loft() body — box shape is unrealistic")

        # KEYBOARD / COMPUTER KEYBOARD
        elif any(kw in prompt_lower for kw in ['keyboard', 'mechanical keyboard', 'keeb',
                                                 'numpad', 'keypad']):
            product_type = "peripheral_keyboard"
            if not any(w in code_lower for w in ['key', 'keycap', 'switch']):
                missing_features.append("key/keycap array (at minimum suggest rows of raised rectangles)")
            if not any(w in code_lower for w in ['plate', 'base', 'case', 'housing']):
                missing_features.append("keyboard case/housing base")
            if not any(w in code_lower for w in ['foot', 'feet', 'tilt', 'riser', 'pad']):
                missing_features.append("tilt feet/risers on bottom for angle adjustment")
            if not any(w in code_lower for w in ['port', 'usb', 'cable', 'connector']):
                missing_features.append("USB port/cable exit on back edge")

        # DESK ACCESSORY / ORGANIZER / PEN HOLDER / MONITOR STAND
        elif any(kw in prompt_lower for kw in ['pen holder', 'pencil holder', 'desk organizer',
                                                 'monitor stand', 'monitor riser',
                                                 'desk caddy', 'letter tray', 'paper tray',
                                                 'business card holder', 'phone dock']):
            product_type = "desk_accessory"
            if not any(w in code_lower for w in ['compartment', 'slot', 'hole', 'pocket', 'recess']):
                missing_features.append("compartments, slots, or holes for organizing items")
            if not any(w in code_lower for w in ['foot', 'feet', 'pad', 'base', 'rubber']):
                missing_features.append("non-slip feet or weighted base")
            if not any(w in code_lower for w in ['cable', 'wire', 'channel', 'route']):
                if any(kw in prompt_lower for kw in ['monitor', 'phone dock', 'charging']):
                    missing_features.append("cable management channel/hole")

        # ELECTRONICS ENCLOSURE
        elif any(kw in prompt_lower for kw in ['enclosure', 'electronics box', 'pcb case',
                                                 'raspberry pi', 'arduino', 'project box']):
            product_type = "electronics_enclosure"
            if not any(w in code_lower for w in ['vent', 'ventilation', 'slot', 'grille']):
                missing_features.append("ventilation slots or grille (minimum 6 slots)")
            if cut_count < 3:
                missing_features.append(f"only {cut_count} port cutouts — need USB, power, HDMI/ethernet cutouts")
            if not any(w in code_lower for w in ['boss', 'standoff', 'mount', 'screw']):
                missing_features.append("mounting bosses or screw holes for PCB standoffs")
        

        # TOOLS (wrench, pliers, screwdriver, hammer)
        elif any(kw in prompt_lower for kw in ['wrench', 'pliers', 'screwdriver', 'hammer',
                                                 'saw', 'drill', 'clamp', 'scissors',
                                                 'knife', 'blade', 'spatula', 'trowel',
                                                 'chisel', 'file', 'rasp']):
            product_type = "tools"
            if not any(w in code_lower for w in ['handle', 'grip', 'shaft']):
                missing_features.append("handle/grip section with ergonomic shape")
            if not any(w in code_lower for w in ['jaw', 'head', 'blade', 'bit', 'tip', 'edge', 'teeth', 'tooth']):
                missing_features.append("working end geometry (jaw, blade, bit, head)")
            if not any(w in code_lower for w in ['texture', 'knurl', 'groove', 'grip_', 'ribbing']):
                missing_features.append("grip texture/knurling on handle")
            if not any(w in code_lower for w in ['hole', 'hang', 'lanyard']):
                missing_features.append("hanging hole at handle end")

        # MECHANICAL PARTS (gears, bearings, cams, springs)
        elif any(kw in prompt_lower for kw in ['gear', 'bearing', 'cam', 'spring',
                                                 'pulley', 'sprocket', 'cog',
                                                 'shaft', 'coupling', 'bushing']):
            product_type = "mechanical"
            if any(kw in prompt_lower for kw in ['gear', 'cog', 'sprocket']):
                if not any(w in code_lower for w in ['tooth', 'teeth', 'involute']):
                    missing_features.append("gear teeth around circumference (use cut array around circle)")
                if not any(w in code_lower for w in ['bore', 'hole', 'shaft', 'hub']):
                    missing_features.append("center bore/shaft hole with keyway")
            elif any(kw in prompt_lower for kw in ['bearing']):
                if not any(w in code_lower for w in ['race', 'inner', 'outer', 'ring']):
                    missing_features.append("inner and outer races (concentric rings)")
                if not any(w in code_lower for w in ['ball', 'roller', 'element']):
                    missing_features.append("rolling elements (balls or rollers) between races")
            if not any(w in code_lower for w in ['chamfer', 'fillet', 'radius']):
                missing_features.append("chamfers or fillets on edges (machined parts have edge breaks)")

        # HOME DECOR (clock, picture frame, mirror, vase)
        elif any(kw in prompt_lower for kw in ['wall clock', 'clock', 'picture frame',
                                                 'photo frame', 'mirror frame',
                                                 'wall art', 'wall shelf']):
            product_type = "home_decor"
            if any(kw in prompt_lower for kw in ['clock']):
                if not any(w in code_lower for w in ['dial', 'face', 'number', 'marker', 'hour']):
                    missing_features.append("clock face with hour markers or numbers")
                if not any(w in code_lower for w in ['hand', 'needle', 'pointer']):
                    missing_features.append("clock hands (hour, minute, optionally second)")
            if any(kw in prompt_lower for kw in ['frame', 'mirror']):
                if not any(w in code_lower for w in ['frame', 'border', 'molding']):
                    missing_features.append("frame border/molding around opening")
                if not any(w in code_lower for w in ['opening', 'recess', 'glass', 'insert']):
                    missing_features.append("recessed opening for photo/mirror insert")
            if not any(w in code_lower for w in ['hang', 'hook', 'mount', 'keyhole', 'bracket']):
                missing_features.append("wall mounting feature (keyhole slot, hook, or bracket on back)")

        # 3D PRINTING ACCESSORIES
        elif any(kw in prompt_lower for kw in ['3d print', 'filament holder', 'spool holder',
                                                 'print bed', 'nozzle holder']):
            product_type = "3d_printing"
            if not any(w in code_lower for w in ['hole', 'slot', 'mount', 'clip']):
                missing_features.append("mounting features (holes, slots, or clips for attachment)")
            if not any(w in code_lower for w in ['fillet', 'chamfer']):
                missing_features.append("filleted/chamfered edges (3D printing accessories should showcase good design)")


        # MOUNT / BRACKET / HOLDER
        elif any(kw in prompt_lower for kw in ['mount', 'bracket', 'holder',
                                                 'phone mount', 'tablet stand', 'tv mount',
                                                 'clamp', 'cradle']):
            product_type = "mount"
            if not any(w in code_lower for w in ['grip', 'clamp', 'jaw', 'cradle', 'clip', 'arm']):
                missing_features.append("gripping/clamping mechanism to hold the device")
            if not any(w in code_lower for w in ['mount', 'bolt', 'screw', 'attach', 'base', 'plate']):
                missing_features.append("mounting base with bolt holes or adhesive surface")
            if not any(w in code_lower for w in ['adjust', 'pivot', 'hinge', 'ball', 'tilt', 'angle']):
                missing_features.append("angle adjustment mechanism (pivot, ball joint, or hinge)")

        # AUTOMOTIVE PARTS (vent mount, cup holder, trim, bumper)
        elif any(kw in prompt_lower for kw in ['car', 'automotive', 'vehicle', 'vent mount',
                                                 'cup holder', 'dash', 'dashboard',
                                                 'bumper', 'fender', 'spoiler', 'wheel rim',
                                                 'hubcap']):
            product_type = "automotive"
            if not any(w in code_lower for w in ['mount', 'clip', 'bolt', 'screw', 'snap', 'tab', 'bracket']):
                missing_features.append("mounting/attachment features (clips, bolt holes, snap-fits)")
            if not any(w in code_lower for w in ['fillet', 'radius', 'chamfer']):
                missing_features.append("edge fillets and radii (automotive parts must have smooth edges)")
            if not any(w in code_lower for w in ['rib', 'boss', 'wall', 'reinforce']):
                missing_features.append("structural ribs or bosses on back face for rigidity")

        # FITNESS / GYM EQUIPMENT
        elif any(kw in prompt_lower for kw in ['dumbbell', 'barbell', 'kettlebell',
                                                 'weight plate', 'jump rope', 'resistance band',
                                                 'yoga block', 'foam roller', 'pull-up bar',
                                                 'gym', 'fitness']):
            product_type = "fitness"
            if not any(w in code_lower for w in ['grip', 'handle', 'knurl', 'texture']):
                missing_features.append("grip/handle with knurling or texture for secure hold")
            if any(kw in prompt_lower for kw in ['dumbbell', 'barbell', 'kettlebell']):
                if not any(w in code_lower for w in ['weight', 'plate', 'mass', 'head']):
                    missing_features.append("weight heads/plates on ends")
            if not any(w in code_lower for w in ['fillet', 'chamfer', 'round']):
                missing_features.append("smooth edges (safety — all fitness equipment needs rounded edges)")

        # SCULPTURE / ART / TROPHY / FIGURINE
        elif any(kw in prompt_lower for kw in ['sculpture', 'statue', 'figurine', 'trophy',
                                                 'bust', 'monument', 'award', 'medallion',
                                                 'relief', 'carving']):
            product_type = "sculpture"
            if not any(w in code_lower for w in ['base', 'pedestal', 'plinth', 'stand']):
                missing_features.append("pedestal/base (sculptures need a stable weighted base)")
            if not any(w in code_lower for w in ['detail', 'feature', 'texture', 'engrav', 'relief']):
                if advanced_technique_count < 2:
                    missing_features.append("surface details — sculptures need .spline()/.loft() for organic forms, not flat surfaces")
            if not any(w in code_lower for w in ['fillet', 'smooth', 'blend']):
                missing_features.append("smooth transitions between body sections (fillets at joints)")

        # LANDMARK / FAMOUS STRUCTURE
        elif any(kw in prompt_lower for kw in ['eiffel', 'tower bridge', 'big ben',
                                                 'colosseum', 'statue of liberty',
                                                 'pyramid', 'lighthouse', 'pagoda',
                                                 'taj mahal', 'landmark', 'monument',
                                                 'famous building']):
            product_type = "landmark"
            if not any(w in code_lower for w in ['base', 'foundation', 'platform', 'ground']):
                missing_features.append("foundation/base platform")
            if code_lines < 40:
                missing_features.append(f"only {code_lines} lines — landmarks need extensive detail (minimum 40+ lines)")
            if total_features < 6:
                missing_features.append(f"only {total_features} features — landmarks need 8+ distinct architectural features")

        # KITCHEN / COOKWARE (cutting board, pot, pan, utensil)
        elif any(kw in prompt_lower for kw in ['cutting board', 'chopping board', 'pot',
                                                 'pan', 'frying pan', 'saucepan',
                                                 'kettle', 'teapot', 'colander',
                                                 'rolling pin', 'ladle', 'whisk',
                                                 'grater', 'peeler', 'can opener',
                                                 'cookware', 'baking']):
            product_type = "kitchen"
            if not any(w in code_lower for w in ['handle', 'grip', 'knob']):
                missing_features.append("handle or grip (essential for safe use of cookware)")
            if any(kw in prompt_lower for kw in ['pot', 'pan', 'saucepan', 'kettle', 'teapot']):
                if not any(w in code_lower for w in ['spout', 'pour', 'lip']):
                    missing_features.append("pour spout or drip lip")
                if shell_count == 0:
                    missing_features.append("hollow interior (use .shell() for pots/pans/kettles)")
            if not any(w in code_lower for w in ['fillet', 'radius', 'round']):
                missing_features.append("food-safe fillets on all internal corners (minimum R2mm)")

        # TOYS / GAMES (building brick, toy car, action figure, board game piece)
        elif any(kw in prompt_lower for kw in ['toy', 'lego', 'building brick', 'action figure',
                                                 'toy car', 'toy train', 'board game',
                                                 'chess piece', 'dice', 'puzzle',
                                                 'spinning top', 'fidget', 'yo-yo',
                                                 'nerf', 'play']):
            product_type = "toy"
            if not any(w in code_lower for w in ['fillet', 'chamfer', 'round']):
                missing_features.append("rounded edges everywhere (child safety — all corners must be radiused)")
            if any(kw in prompt_lower for kw in ['building brick', 'lego']):
                if not any(w in code_lower for w in ['stud', 'knob', 'peg', 'bump']):
                    missing_features.append("connection studs/pegs on top surface")
                if not any(w in code_lower for w in ['tube', 'socket', 'clutch', 'recess']):
                    missing_features.append("clutch tubes/sockets on bottom for stacking")
            if any(kw in prompt_lower for kw in ['chess', 'piece']):
                if not any(w in code_lower for w in ['base', 'pedestal', 'foot']):
                    missing_features.append("weighted base/pedestal for stability")

        # LIGHTING / LAMP / CHANDELIER
        elif any(kw in prompt_lower for kw in ['lamp', 'desk lamp', 'floor lamp',
                                                 'table lamp', 'chandelier', 'sconce',
                                                 'pendant light', 'lantern', 'flashlight',
                                                 'lighting', 'light fixture']):
            product_type = "lamp"
            if not any(w in code_lower for w in ['shade', 'diffuser', 'globe', 'cone', 'lampshade']):
                missing_features.append("lamp shade/diffuser (cone, dome, globe, or cylinder)")
            if not any(w in code_lower for w in ['base', 'stand', 'foot', 'weight']):
                missing_features.append("weighted base for stability")
            if not any(w in code_lower for w in ['socket', 'bulb', 'led', 'light']):
                missing_features.append("bulb socket/LED module recess")
            if not any(w in code_lower for w in ['arm', 'stem', 'neck', 'pole', 'column']):
                if not any(kw in prompt_lower for kw in ['sconce', 'pendant', 'ceiling']):
                    missing_features.append("arm/stem/pole connecting shade to base")
            if not any(w in code_lower for w in ['switch', 'button', 'cable', 'cord', 'wire']):
                missing_features.append("switch or cable entry hole")

        # SPORTS EQUIPMENT (skateboard, basketball hoop, bat, racket)
        elif any(kw in prompt_lower for kw in ['skateboard', 'basketball hoop', 'tennis racket',
                                                 'baseball bat', 'hockey stick', 'golf club',
                                                 'helmet', 'shin guard', 'paddle',
                                                 'surfboard', 'snowboard', 'ski']):
            product_type = "sports"
            if not any(w in code_lower for w in ['grip', 'handle', 'tape', 'wrap']):
                if any(kw in prompt_lower for kw in ['bat', 'racket', 'club', 'stick', 'paddle']):
                    missing_features.append("grip/handle wrap area with texture")
            if any(kw in prompt_lower for kw in ['skateboard', 'snowboard', 'surfboard']):
                if not any(w in code_lower for w in ['truck', 'wheel', 'fin', 'binding', 'hardware']):
                    missing_features.append("hardware mounting points (trucks, fins, or bindings)")
                if not any(w in code_lower for w in ['concave', 'kick', 'nose', 'tail', 'rocker']):
                    missing_features.append("board shape features (kicktail, concave, nose/tail curve)")
            if any(kw in prompt_lower for kw in ['basketball hoop']):
                if not any(w in code_lower for w in ['rim', 'ring', 'hoop']):
                    missing_features.append("hoop/rim ring at top")
                if not any(w in code_lower for w in ['backboard', 'board', 'panel']):
                    missing_features.append("backboard panel behind rim")
                if not any(w in code_lower for w in ['net', 'mesh', 'chain']):
                    missing_features.append("net attachment hooks or net cylinder below rim")
            if any(kw in prompt_lower for kw in ['helmet']):
                if shell_count == 0:
                    missing_features.append("helmet shell (use .shell() for hollow interior)")
                if not any(w in code_lower for w in ['visor', 'face', 'guard', 'cage']):
                    missing_features.append("visor or face guard opening")
                if not any(w in code_lower for w in ['vent', 'hole', 'air']):
                    missing_features.append("ventilation holes on top/sides")

        # JEWELRY / ACCESSORIES (ring, bracelet, necklace, pendant)
        elif any(kw in prompt_lower for kw in ['ring', 'bracelet', 'necklace', 'pendant',
                                                 'earring', 'brooch', 'tiara', 'crown',
                                                 'cufflink', 'tie clip', 'jewelry']):
            product_type = "jewelry"
            if any(kw in prompt_lower for kw in ['ring']):
                if revolve_count == 0:
                    missing_features.append("BODY SHAPE: Ring MUST use .revolve() — it's a circular band")
                if not any(w in code_lower for w in ['setting', 'prong', 'bezel', 'stone', 'gem', 'diamond']):
                    if any(kw in prompt_lower for kw in ['diamond', 'gem', 'stone', 'engagement', 'solitaire']):
                        missing_features.append("stone setting with prongs or bezel for the gemstone")
            if any(kw in prompt_lower for kw in ['bracelet', 'bangle']):
                if not any(w in code_lower for w in ['clasp', 'hinge', 'closure', 'snap']):
                    missing_features.append("clasp or closure mechanism")
            if not any(w in code_lower for w in ['fillet', 'smooth', 'polish']):
                missing_features.append("smooth polished edges (jewelry must have no sharp edges)")

        # MUSICAL INSTRUMENTS (guitar, drum, piano, violin, flute)
        elif any(kw in prompt_lower for kw in ['guitar', 'drum', 'piano', 'violin',
                                                 'flute', 'trumpet', 'saxophone',
                                                 'ukulele', 'bass guitar', 'cello',
                                                 'keyboard instrument', 'synthesizer',
                                                 'xylophone', 'harmonica']):
            product_type = "instrument"
            if any(kw in prompt_lower for kw in ['guitar', 'ukulele', 'bass guitar', 'violin', 'cello']):
                if not any(w in code_lower for w in ['body', 'bout', 'soundboard']):
                    missing_features.append("instrument body/sound chamber")
                if not any(w in code_lower for w in ['neck', 'fretboard', 'fingerboard']):
                    missing_features.append("neck/fretboard extending from body")
                if not any(w in code_lower for w in ['headstock', 'head', 'scroll', 'pegbox']):
                    missing_features.append("headstock at end of neck")
                if not any(w in code_lower for w in ['tuning', 'peg', 'tuner', 'machine_head']):
                    missing_features.append("tuning pegs/machine heads on headstock")
                if not any(w in code_lower for w in ['sound_hole', 'f_hole', 'soundhole', 'f-hole', 'rosette']):
                    missing_features.append("sound hole(s) on body face")
                if not any(w in code_lower for w in ['bridge', 'saddle', 'tailpiece']):
                    missing_features.append("bridge/saddle on body for string support")
            if any(kw in prompt_lower for kw in ['drum']):
                if not any(w in code_lower for w in ['shell', 'barrel', 'cylinder']):
                    missing_features.append("drum shell/cylinder body")
                if not any(w in code_lower for w in ['head', 'skin', 'membrane', 'batter']):
                    missing_features.append("drum head/skin on top (thin disc)")
                if not any(w in code_lower for w in ['rim', 'hoop', 'counterhoop']):
                    missing_features.append("rim/hoop holding the drum head")
                if not any(w in code_lower for w in ['lug', 'tension', 'rod']):
                    missing_features.append("tension lugs/rods around shell for tuning")
            if any(kw in prompt_lower for kw in ['trumpet', 'saxophone', 'flute', 'trombone']):
                if not any(w in code_lower for w in ['bell', 'flare']):
                    missing_features.append("bell/flare at output end")
                if not any(w in code_lower for w in ['key', 'valve', 'piston', 'pad', 'finger']):
                    missing_features.append("keys/valves/finger holes along body")
                if not any(w in code_lower for w in ['mouthpiece', 'embouchure', 'reed']):
                    missing_features.append("mouthpiece at input end")

        # MEDICAL / SCIENTIFIC (test tube rack, beaker, microscope, syringe)
        elif any(kw in prompt_lower for kw in ['test tube', 'beaker', 'flask', 'microscope',
                                                 'syringe', 'stethoscope', 'petri dish',
                                                 'lab', 'medical', 'scientific',
                                                 'pill box', 'medicine']):
            product_type = "medical"
            if any(kw in prompt_lower for kw in ['test tube rack', 'tube rack', 'tube holder']):
                if not any(w in code_lower for w in ['hole', 'slot', 'well', 'bore']):
                    missing_features.append("tube holes/wells array (properly sized and spaced)")
                if not any(w in code_lower for w in ['base', 'foot', 'stand']):
                    missing_features.append("stable base/feet (lab equipment must be tip-resistant)")
            if any(kw in prompt_lower for kw in ['beaker', 'flask', 'graduated']):
                if shell_count == 0:
                    missing_features.append("hollow interior (use .shell() for beaker/flask)")
                if not any(w in code_lower for w in ['spout', 'pour', 'lip']):
                    missing_features.append("pouring spout/lip")
                if not any(w in code_lower for w in ['graduat', 'mark', 'scale', 'line']):
                    missing_features.append("graduation marks/measurement lines")
            if any(kw in prompt_lower for kw in ['microscope']):
                if not any(w in code_lower for w in ['eyepiece', 'ocular', 'lens']):
                    missing_features.append("eyepiece/ocular at top")
                if not any(w in code_lower for w in ['stage', 'platform', 'slide']):
                    missing_features.append("specimen stage/platform")
                if not any(w in code_lower for w in ['objective', 'turret', 'nosepiece']):
                    missing_features.append("objective lens turret")
                if not any(w in code_lower for w in ['base', 'foot', 'arm', 'stand']):
                    missing_features.append("arm and base structure")

        # PIPES / PLUMBING / FITTINGS
        elif any(kw in prompt_lower for kw in ['pipe', 'fitting', 'elbow', 'tee fitting',
                                                 'coupling', 'valve', 'faucet', 'tap',
                                                 'plumbing', 'nozzle', 'hose']):
            product_type = "pipe"
            if not any(w in code_lower for w in ['bore', 'inner', 'hole', 'shell', 'hollow']):
                missing_features.append("hollow bore/interior (pipes must be hollow)")
            if not any(w in code_lower for w in ['thread', 'flange', 'barb', 'crimp', 'solder', 'slip']):
                missing_features.append("connection features (threads, flanges, barbs, or slip joints)")
            if any(kw in prompt_lower for kw in ['valve', 'faucet', 'tap']):
                if not any(w in code_lower for w in ['handle', 'knob', 'lever', 'wheel']):
                    missing_features.append("operating handle/knob/lever")
                if not any(w in code_lower for w in ['seat', 'gate', 'ball', 'disc']):
                    missing_features.append("valve mechanism (seat, gate, ball, or disc)")
            if not any(w in code_lower for w in ['chamfer', 'bevel', 'deburr']):
                missing_features.append("chamfered pipe ends (deburring for safe assembly)")

        # HARDWARE (hinges, brackets, fasteners)
        elif any(kw in prompt_lower for kw in ['hinge', 'bracket', 'fastener', 'bolt',
                                                 'nut', 'screw', 'washer', 'nail',
                                                 'hook', 'clasp', 'latch', 'hasp']):
            product_type = "hardware"
            if any(kw in prompt_lower for kw in ['hinge']):
                if not any(w in code_lower for w in ['pin', 'knuckle', 'barrel', 'pivot']):
                    missing_features.append("hinge pin/knuckle mechanism (the pivot point)")
                if not any(w in code_lower for w in ['leaf', 'plate', 'wing', 'flap']):
                    missing_features.append("hinge leaves/plates (the two pivoting surfaces)")
                if not any(w in code_lower for w in ['hole', 'screw', 'mount']):
                    missing_features.append("mounting screw holes on both leaves")
            if any(kw in prompt_lower for kw in ['bolt', 'screw']):
                if not any(w in code_lower for w in ['thread', 'helix']):
                    missing_features.append("thread/helix pattern on shaft")
                if not any(w in code_lower for w in ['head', 'hex', 'cap', 'phillips', 'slot', 'drive']):
                    missing_features.append("head with drive feature (hex, phillips, slot, etc.)")

        # BUILDING / HOUSE
        elif any(kw in prompt_lower for kw in ['building', 'house', 'log cabin', 'cottage',
                                                 'apartment', 'office building', 'skyscraper',
                                                 'church', 'cathedral', 'mosque', 'temple',
                                                 'wooden cabin', 'cabin house']):
            product_type = "building"
            if not any(w in code_lower for w in ['window', 'win_', 'win ']):
                missing_features.append("windows on at least 2 walls (minimum 4 windows total)")
            if not any(w in code_lower for w in ['door', 'entrance']):
                missing_features.append("entrance door on front face")
            if not any(w in code_lower for w in ['roof', 'gable', 'hip_roof']):
                missing_features.append("roof structure (gabled or hip roof, not flat-top box)")
            if cut_count < 5:
                missing_features.append(f"only {cut_count} cutouts — a building needs windows, doors, and architectural details")
        
        # CASTLE / FORTRESS
        elif any(kw in prompt_lower for kw in ['castle', 'fortress', 'medieval']):
            product_type = "castle"
            if not any(w in code_lower for w in ['tower', 'turret']):
                missing_features.append("corner towers (minimum 2)")
            if not any(w in code_lower for w in ['gate', 'entrance', 'arch']):
                missing_features.append("gate/entrance with arch")
            if not any(w in code_lower for w in ['crenel', 'battlement', 'merlon']):
                missing_features.append("crenellations/battlements on tower tops")
        
        # DRONE / QUADCOPTER / HEXACOPTER / TRICOPTER / OCTOCOPTER / VTOL / ROV / DELIVERY / AGRICULTURE
        elif any(kw in prompt_lower for kw in ['drone', 'quadcopter', 'quadrotor', 'uav',
                                                 'hexacopter', 'octocopter', 'tricopter',
                                                 'vtol', 'flying wing', 'fpv drone',
                                                 'camera drone', 'photography drone',
                                                 'delivery drone', 'cargo drone',
                                                 'mini drone', 'micro drone', 'tiny whoop',
                                                 'underwater drone', 'rov',
                                                 'spray drone', 'agriculture drone',
                                                 'farm drone', 'crop drone']):
            product_type = "drone"

            # Determine drone sub-type for accurate checks
            drone_subtype = "quadcopter"  # default
            if any(kw in prompt_lower for kw in ['hexacopter', 'hex drone', '6 motor', 'six rotor']):
                drone_subtype = "hexacopter"
            elif any(kw in prompt_lower for kw in ['octocopter', 'octo drone', '8 motor', 'eight rotor']):
                drone_subtype = "octocopter"
            elif any(kw in prompt_lower for kw in ['tricopter', 'tri drone', '3 motor', 'y frame']):
                drone_subtype = "tricopter"
            elif any(kw in prompt_lower for kw in ['vtol', 'fixed wing drone', 'flying wing',
                                                     'wing drone', 'survey drone', 'mapping drone']):
                drone_subtype = "fixedwing_vtol"
            elif any(kw in prompt_lower for kw in ['mini drone', 'micro drone', 'tiny whoop',
                                                     'nano drone', 'tiny drone', 'indoor drone']):
                drone_subtype = "mini"
            elif any(kw in prompt_lower for kw in ['delivery drone', 'cargo drone', 'package drone',
                                                     'logistics drone']):
                drone_subtype = "delivery"
            elif any(kw in prompt_lower for kw in ['underwater drone', 'rov', 'submersible',
                                                     'aquatic drone']):
                drone_subtype = "rov"
            elif any(kw in prompt_lower for kw in ['spray drone', 'agriculture drone', 'farm drone',
                                                     'crop drone', 'agricultural drone']):
                drone_subtype = "agriculture"
            elif any(kw in prompt_lower for kw in ['camera drone', 'photography drone', 'dji',
                                                     'mavic', 'filming drone']):
                drone_subtype = "camera"
            elif any(kw in prompt_lower for kw in ['fpv', 'racing drone', '250 drone']):
                drone_subtype = "racing"

            # --- Sub-type specific arm/body checks ---
            arm_count_map = {
                "quadcopter": 4, "racing": 4, "camera": 4, "mini": 4,
                "hexacopter": 6, "delivery": 6, "agriculture": 6,
                "octocopter": 8, "tricopter": 3
            }
            expected_arms = arm_count_map.get(drone_subtype, 4)

            # Skip arm check for fixed-wing VTOL and ROV (different structure)
            if drone_subtype == "fixedwing_vtol":
                if not any(w in code_lower for w in ['wing', 'fuselage']):
                    missing_features.append("MISSING WINGS/FUSELAGE: A fixed-wing VTOL has streamlined fuselage + wings")
                if not any(w in code_lower for w in ['tail', 'stabilizer', 'v_tail']):
                    missing_features.append("MISSING TAIL: Fixed-wing needs a tail section (V-tail or conventional)")
            elif drone_subtype == "rov":
                if not any(w in code_lower for w in ['frame', 'cage', 'rail']):
                    missing_features.append("MISSING FRAME: Underwater ROV needs an open cage/rail frame structure")
                if not any(w in code_lower for w in ['thruster', 'thrust']):
                    missing_features.append("MISSING THRUSTERS: Underwater ROV needs enclosed thruster pods (not open propellers)")
                if not any(w in code_lower for w in ['camera', 'dome', 'lens']):
                    missing_features.append("MISSING CAMERA DOME: ROV needs a forward camera dome/hemisphere")
                if not any(w in code_lower for w in ['buoyancy', 'foam', 'float']):
                    missing_features.append("MISSING BUOYANCY FOAM: ROV needs buoyancy foam block on top of frame")
                if not any(w in code_lower for w in ['tether', 'cable', 'connector']):
                    missing_features.append("MISSING TETHER PORT: ROV needs a tether connection port on rear")
            else:
                # Air drones: check for arms (except mini which has ducts)
                if drone_subtype == "mini":
                    if not any(w in code_lower for w in ['duct', 'guard', 'ring', 'arm']):
                        missing_features.append("MISSING DUCTED GUARDS: Mini drone needs integrated circular prop guards/ducts")
                elif not any(w in code_lower for w in ['arm', 'motor_arm', 'boom']):
                    missing_features.append(f"{expected_arms} motor mount arms extending from central body")

            # --- Motor and propeller checks for all air drones ---
            if drone_subtype != "rov":
                if not any(w in code_lower for w in ['motor_can', 'motor_body', 'motor_cylinder',
                                                       'motor_height', 'motor_h', 'motor_dia', 'motor']):
                    has_motor_bodies = bool(re.search(
                        r'motor\w*\s*=\s*cq\.Workplane\([^)]+\)\.cylinder\(', code_lower))
                    if has_motor_bodies:
                        has_motor_bodies = bool(re.search(r'\.union\(\s*motor', code_lower))
                    if not has_motor_bodies:
                        missing_features.append(
                            f"MISSING MOTORS: Need {expected_arms} visible cylindrical motor cans "
                            f"on arm tips — use .cylinder(motor_height, motor_r) unioned above each mount. "
                            "Without motors it looks like a bare flat PCB.")
                if not any(w in code_lower for w in ['propeller', 'prop_', 'blade', 'rotor']):
                    missing_features.append(
                        f"MISSING PROPELLERS: Need {expected_arms} propeller discs/blades on top of motors — "
                        "use thin .cylinder(2, prop_r) or blade shapes. Props are THE iconic drone visual feature.")

            # --- Canopy/cover check for air drones ---
            if drone_subtype not in ("rov", "mini"):
                if not any(w in code_lower for w in ['canopy', 'cover', 'dome', 'hood', 'shroud',
                                                       'fuselage_cover', 'body_shell', 'top_cover', 'fuselage']):
                    missing_features.append(
                        "MISSING CANOPY: drone needs a protective cover/dome over center electronics — "
                        "use .sphere() sliced in half, or .loft() for a streamlined aerodynamic shape.")

            # --- Landing gear check (skip for mini drones which are flat-bottom) ---
            if drone_subtype not in ("rov", "mini"):
                if not any(w in code_lower for w in ['landing', 'leg', 'skid', 'gear', 'stand']):
                    missing_features.append(
                        "MISSING LANDING GEAR: drone needs landing legs or skid rails under body.")

            # --- Type-specific extras ---
            if drone_subtype == "camera":
                if not any(w in code_lower for w in ['gimbal', 'camera', 'cam']):
                    missing_features.append("MISSING GIMBAL/CAMERA: Camera drone needs a 3-axis gimbal + camera under front of body")
            elif drone_subtype == "delivery":
                if not any(w in code_lower for w in ['cargo', 'bay', 'payload', 'hook', 'winch']):
                    missing_features.append("MISSING CARGO BAY: Delivery drone needs a cargo compartment under body with release mechanism")
            elif drone_subtype == "agriculture":
                if not any(w in code_lower for w in ['tank', 'spray', 'nozzle', 'boom']):
                    missing_features.append("MISSING SPRAY SYSTEM: Agriculture drone needs a spray tank + spray boom with nozzles")
            elif drone_subtype == "tricopter":
                if not any(w in code_lower for w in ['servo', 'tilt']):
                    missing_features.append("MISSING TAIL SERVO: Tricopter needs a visible servo/tilt mechanism on the rear motor for yaw control")
        
        # GAME CONTROLLER
        elif any(kw in prompt_lower for kw in ['controller', 'gamepad', 'joystick']):
            product_type = "game_controller"
            if not any(w in code_lower for w in ['button', 'btn']):
                missing_features.append("button holes (A/B/X/Y face buttons)")
            if not any(w in code_lower for w in ['thumbstick', 'stick', 'analog']):
                missing_features.append("thumbstick/analog stick holes (2)")
            if not any(w in code_lower for w in ['grip', 'texture', 'groove']):
                missing_features.append("grip texture on handle areas")
        
        # FURNITURE (desk, table, chair, shelf, stand)
        elif any(kw in prompt_lower for kw in ['desk', 'table', 'chair', 'shelf', 'bookshelf',
                                                 'stand', 'organizer', 'rack']):
            product_type = "furniture"
            if not any(w in code_lower for w in ['foot', 'feet', 'pad', 'leg']):
                missing_features.append("feet/legs or non-slip pads on bottom")
            if cut_count < 2 and union_count < 2:
                missing_features.append(f"only {total_features} features — furniture needs functional details (cable holes, slots, compartments)")
        
        # DRINKWARE (cup, mug, bottle, tumbler)
        elif any(kw in prompt_lower for kw in ['mug', 'cup', 'bottle', 'tumbler', 'glass', 'vase']):
            product_type = "drinkware"
            if not any(w in code_lower for w in ['handle', 'grip']):
                if any(kw in prompt_lower for kw in ['mug', 'cup']):
                    missing_features.append("handle on the side")
            if not any(w in code_lower for w in ['rim', 'lip', 'edge']):
                missing_features.append("rounded rim/lip at top for comfortable drinking")
        
        # CONTAINER / BOX / STORAGE
        elif any(kw in prompt_lower for kw in ['box', 'container', 'bin', 'storage',
                                                 'crate', 'toolbox']):
            product_type = "container"
            if not any(w in code_lower for w in ['handle', 'grip', 'recess']):
                missing_features.append("handle cutouts or grip recesses on sides")
            if not any(w in code_lower for w in ['foot', 'feet', 'pad']):
                missing_features.append("non-slip feet on bottom")
        
        # ── Generic completeness checks (all products) ──────────────────
        
        # Per-type minimum cutout requirements (overrides generic minimum)
        min_cuts_by_type = {
            "phone_case": 6,         # USB-C, camera, 2+ buttons, speaker holes, mic
            "electronics_enclosure": 5,  # USB, power, HDMI, ethernet, vent slots
            "game_controller": 6,    # buttons, thumbsticks, triggers, ports
            "laptop": 5,             # ports, vents, screen hinge, trackpad, keys
            "tablet": 4,             # charging, speakers, camera, buttons
            "smartphone": 5,         # USB-C, speaker, earpiece, camera, buttons
            "audio_speaker": 3,      # driver, port, controls
            "audio_headphones": 2,   # drivers, controls
            "wearable_watch": 3,     # display, buttons, band slots
            "peripheral_mouse": 2,   # button splits, scroll slot, sensor hole
            "peripheral_keyboard": 3,  # key recesses, port, feet
            "building": 5,           # windows, doors
            "castle": 6,             # gates, windows, crenellations, arrow slits
            "automotive": 4,         # mount holes, vent slots, clip features
            "kitchen": 2,            # handle, pour spout
            "pipe": 2,               # bore, thread/flange
            "medical": 3,            # holes, slots, openings
            "hardware": 2,           # holes, pivot holes
            "lamp": 2,               # socket hole, switch/cable hole
            "instrument": 3,         # sound hole, tuning holes, bridge slot
        }
        min_cuts = min_cuts_by_type.get(product_type, 3)
        
        if cut_count < min_cuts and "only" not in " ".join(missing_features):
            missing_features.append(
                f"only {cut_count} cutout operations — {product_type.replace('_',' ')} needs {min_cuts}+ "
                "(ports, holes, vents, slots)")
        
        if fillet_count < 1 and chamfer_count < 1:
            missing_features.append("no edge fillets or chamfers — product looks unfinished with sharp edges")
        
        if code_lines < 20:
            missing_features.append(f"only {code_lines} lines of code — too simple for a complete product")
        
        # ── Shape quality checks (anti-brick) ───────────────────────────
        # Products with 3+ cutouts should have at least SOME rounded shapes
        if total_features >= 3 and round_cutter_count == 0:
            missing_features.append(
                "ALL cutouts are rectangular boxes — use .cylinder() for round holes "
                "(speakers, LEDs, screws), .slot2D() for rounded slots (USB ports, buttons), "
                "and .hole() for precision bores. Match the real-world shape of each feature.")
        
        # Electronics products MUST have round cutouts (speakers, LEDs, screws are round)
        electronics_types = ("phone_case", "electronics_enclosure", "game_controller",
                            "laptop", "tablet", "smartphone", "audio_speaker",
                            "wearable_watch", "peripheral_mouse", "peripheral_keyboard")
        if product_type in electronics_types and round_cutter_count == 0 and cut_count >= 2:
            missing_features.append(
                f"CUTOUT SHAPES: {product_type.replace('_',' ')} has no round cutouts "
                "(.cylinder/.slot2D/.hole) — real electronics have circular speaker holes, "
                "round screw bosses, pill-shaped ports, and cylindrical LED holes")
        
        # Products where MOST cutters should be round (not box)
        round_dominant_types = ("phone_case", "game_controller", "audio_speaker",
                               "electronics_enclosure", "peripheral_mouse")
        if product_type in round_dominant_types and box_cutter_count > 0:
            total_cutters = box_cutter_count + round_cutter_count
            if total_cutters > 0 and box_cutter_count > round_cutter_count:
                missing_features.append(
                    f"BRICK-LIKE CUTOUTS: {product_type.replace('_',' ')} has too many "
                    f"rectangular .box() cutters ({box_cutter_count} boxes vs {round_cutter_count} rounded). "
                    "REPLACE .box() cutters with: .slot2D() for ports/buttons (pill shape), "
                    ".cylinder() for speakers/mic/LED/screws (circles), .hole() for precision bores, "
                    ".rect()+.fillet() for camera islands. Match the REAL shape of each feature.")

        # Cutout depth check: warn if cutters are likely too shallow
        # Look for patterns like .box(w, h, 1) or .cylinder(1, r) where depth < 2
        shallow_box_cuts = len(re.findall(r'\.box\([^)]*,\s*[01]\.?\d?\s*\)', code))
        shallow_cyl_cuts = len(re.findall(r'\.cylinder\(\s*[01]\.?\d?\s*,', code))
        if (shallow_box_cuts + shallow_cyl_cuts) > 0 and shell_count > 0:
            missing_features.append(
                f"SHALLOW CUTTERS: {shallow_box_cuts + shallow_cyl_cuts} cutters have depth < 2mm — "
                "cutouts must use wall*3 depth to guarantee they punch THROUGH the wall")
        
        # ── Body construction quality checks (anti-toy) ──────────────────
        # Products that MUST use revolve (cylindrical/round products)
        revolve_required_types = ("drinkware", "jewelry")
        if product_type in revolve_required_types and revolve_count == 0:
            missing_features.append(
                "BODY SHAPE: This round product MUST use .revolve() + .spline() profile — "
                "using .box() for a mug/bottle/vase makes it look like a toy. "
                "Build a 2D spline profile and .revolve(360) around the Y axis.")
        
        # Products that SHOULD use loft for ergonomic body shape
        loft_preferred_types = ("game_controller", "peripheral_mouse", "audio_headphones")
        if product_type in loft_preferred_types and loft_count == 0 and revolve_count == 0:
            missing_features.append(
                "BODY SHAPE: This ergonomic product should use multi-section .loft() — "
                "using .box() for a controller/mouse makes it look toy-like. "
                "Loft between elliptical cross-sections for an organic body shape.")
        
        # Profile quality: flag all-lineTo profiles for products that need curves
        organic_product_types = ("drinkware", "game_controller", "peripheral_mouse", "audio_headphones", "sculpture", "lamp", "jewelry")
        if product_type in organic_product_types and lineto_count > 4 and spline_count == 0:
            missing_features.append(
                "PROFILE QUALITY: Using only .lineTo() chains for curved surfaces — "
                "replace straight-line profiles with .spline() control points for smooth organic curves. "
                "A mug/bottle/controller should have NO straight diagonal lines in its body profile.")
        
        # Handle/sweep quality: check for straight-line sweep paths
        if sweep_count > 0 and three_point_arc_count == 0 and spline_count == 0:
            missing_features.append(
                "SWEEP PATH: .sweep() uses straight-line path — use .threePointArc() or "
                ".spline() for curved handles/rails. Straight-line sweep = angular robot look.")
        
        # ── Check user-specified features were implemented ───────────────
        # Extract key nouns from the user prompt and check they appear in code
        user_feature_keywords = self._extract_user_feature_keywords(prompt)
        for keyword, description in user_feature_keywords:
            if keyword.lower() not in code_lower:
                missing_features.append(f"user requested '{description}' but it's not in the code")
        
        is_complete = len(missing_features) == 0
        
        return {
            "is_complete": is_complete,
            "product_type": product_type,
            "cut_count": cut_count,
            "union_count": union_count,
            "fillet_count": fillet_count,
            "cylinder_count": cylinder_count,
            "slot2d_count": slot2d_count,
            "round_cutter_count": round_cutter_count,
            "box_cutter_count": box_cutter_count,
            "spline_count": spline_count,
            "loft_count": loft_count,
            "revolve_count": revolve_count,
            "sweep_count": sweep_count,
            "advanced_technique_count": advanced_technique_count,
            "main_body_is_box": main_body_is_box,
            "code_lines": code_lines,
            "total_features": total_features,
            "missing_features": missing_features,
        }

    def _extract_user_feature_keywords(self, prompt: str) -> list:
        """
        Extract specific feature keywords from user prompt that MUST appear in the code.
        Returns list of (keyword_to_search, description) tuples.
        """
        import re
        features = []
        prompt_lower = prompt.lower()
        
        # Pattern: "with a X" or "with X" or "including X" or "add X"
        # Look for common feature phrases
        feature_patterns = [
            # "with a camera mount" → ("camera", "camera mount")
            r'with\s+(?:a\s+)?(\w+[\s\w]*?)(?:\s+and\s+|\s*,\s*|$|\s+on\s+|\s+at\s+|\s+in\s+)',
            r'(?:add|include|including|has|having)\s+(?:a\s+)?(\w+[\s\w]*?)(?:\s+and\s+|\s*,\s*|$|\s+on\s+|\s+at\s+)',
        ]
        
        # Known feature words that map to code keywords
        feature_map = {
            'camera mount': 'camera',
            'camera': 'camera',
            'led light': 'led',
            'led': 'led',
            'handle': 'handle',
            'grip': 'grip',
            'window': 'window',
            'door': 'door',
            'wheel': 'wheel',
            'wing': 'wing',
            'propeller': 'propeller',
            'antenna': 'antenna',
            'battery': 'battery',
            'screen': 'screen',
            'display': 'display',
            'speaker': 'speaker',
            'microphone': 'mic',
            'usb': 'usb',
            'charging port': 'port',
            'headphone jack': 'headphone',
            'slot': 'slot',
            'hole': 'hole',
            'button': 'button',
            'knob': 'knob',
            'shelf': 'shelf',
            'drawer': 'drawer',
            'hinge': 'hinge',
            'latch': 'latch',
            'lock': 'lock',
            'vent': 'vent',
            'fan': 'fan',
            'chimney': 'chimney',
            'balcony': 'balcony',
            'stairs': 'stair',
            'steps': 'step',
            'railing': 'rail',
            'fence': 'fence',
            'roof': 'roof',
            'dome': 'dome',
            'tower': 'tower',
            'arch': 'arch',
            'column': 'column',
            'pillar': 'pillar',
            'kickstand': 'kickstand',
            'stand': 'stand',
            'mount': 'mount',
            'bracket': 'bracket',
            'hook': 'hook',
            'clip': 'clip',
            'magnet': 'magnet',
            'magsafe': 'magsafe',
            'wireless charging': 'wireless',
            'cup holder': 'cup',
            'pen holder': 'pen',
            'card slot': 'card',
            'compartment': 'compartment',
            'divider': 'divider',
            'lid': 'lid',
            'cover': 'cover',
            'foot': 'foot',
            'feet': 'feet',
            'leg': 'leg',
            'arm': 'arm',
        }
        
        for user_term, code_keyword in feature_map.items():
            if user_term in prompt_lower:
                features.append((code_keyword, user_term))
        
        return features

    async def enhance_incomplete_design(
        self,
        design_json: Dict[str, Any],
        prompt: str,
        analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Send an incomplete design back to Claude with specific instructions
        to add the missing features. This is the automatic enhancement pass.
        Only called when analyze_code_completeness finds issues.
        """
        missing = "\n".join(f"  • {f}" for f in analysis["missing_features"])
        
        # Add shape variety guidance if the design uses only rectangular cutouts
        shape_note = ""
        if analysis.get("round_cutter_count", 0) == 0 and analysis.get("total_features", 0) >= 3:
            shape_note = """

SHAPE VARIETY FIX — Your current design uses ONLY rectangular .box() cutouts, making it look like a BRICK.
Real products have ROUNDED features. When adding/fixing features, use:
  • .cylinder(h, r) for round holes (speakers, LEDs, screws, microphones, sensor holes)
  • .slot2D(length, diameter).extrude(h) for rounded slots (USB ports, buttons, vents)
  • .hole(diameter) or .hole(diameter, depth) for precision bores (screw holes, pin holes)
  • .cboreHole(d, cboreDia, cboreDepth) for counterbored screw holes
  • .rect(w, h) then .fillet() for rounded-corner rectangles (camera cutouts, screens)
  • NEVER use .box() for: ports, buttons, speakers, screws, LEDs, microphones, vents
  • .box() cutters are ONLY correct for: windows, doors, drawers, panel slots
  CUTOUT DEPTH RULE: All cutters must use wall*3 depth minimum to punch through."""

        # Electronics products: flag box-dominant cutters (not just phone cases)
        electronics_round_types = ("phone_case", "electronics_enclosure", "game_controller",
                                   "laptop", "tablet", "smartphone", "audio_speaker",
                                   "wearable_watch", "peripheral_mouse")
        if not shape_note and analysis.get("product_type") in electronics_round_types:
            box_cutters = analysis.get("box_cutter_count", 0)
            round_cutters = analysis.get("round_cutter_count", 0)
            if box_cutters > 0 and box_cutters > round_cutters:
                ptype = analysis.get("product_type", "").replace("_", " ")
                shape_note = f"""

CUTOUT SHAPE FIX FOR {ptype.upper()} — Too many rectangular .box() cutters vs round ones ({box_cutters} boxes vs {round_cutters} round).
Real {ptype}s have mostly ROUND features. Fix each cutout to match its real-world shape:
  • Ports (USB, HDMI, jack) → .slot2D(w, h).extrude(wall*3) — rounded pill/stadium shape
  • Speaker/mic holes → .cylinder(wall*3, r) — circular holes
  • Screw holes → .hole(diameter) — precision circles
  • LED indicators → .cylinder(wall*3, r) — tiny circles
  • Vent grilles → Array of .slot2D() or .cylinder() — rounded patterns
  • Buttons/keys → .slot2D(length, depth).extrude(wall*3) — rounded slots
  • Camera/sensor → .rect(w,h).extrude(d) + .edges().fillet(r) — rounded rectangle
  • Screen recess → .rect(w,h) is OK (screens ARE rectangular)
  DEPTH RULE: All cutters must overlap the wall by wall*3."""

        # Add body shape guidance if the design uses primitive box body for organic products
        body_note = ""
        has_body_issues = any("BODY SHAPE:" in f or "PROFILE QUALITY:" in f or "SWEEP PATH:" in f 
                             or "BRICK-LIKE CUTOUTS:" in f
                             or "MISSING MOTORS:" in f or "MISSING PROPELLERS:" in f
                             or "MISSING CANOPY:" in f or "MISSING LANDING GEAR:" in f
                             or "MISSING WINGS" in f or "MISSING THRUSTERS" in f
                             or "MISSING GIMBAL" in f or "MISSING CARGO BAY" in f
                             or "MISSING SPRAY SYSTEM" in f or "MISSING FRAME" in f
                             or "INCOMPLETE DRONE" in f
                             for f in analysis.get("missing_features", []))
        if has_body_issues:
            product_type = analysis.get("product_type", "generic")
            if product_type == "drinkware":
                body_note = """

BODY SHAPE FIX — Your design uses .box() or .lineTo() chains for a ROUND product.
REWRITE THE MAIN BODY using .revolve() + .spline():
  profile = (cq.Workplane("XZ").moveTo(0, 0)
    .lineTo(base_r, 0)                                         # Flat base
    .spline([(base_r+1, 5), (mid_r, H*0.5), (top_r, H-lip*2)])  # Smooth organic taper  
    .tangentArcPoint((top_r-lip, H))                            # Rolled lip
    .lineTo(0, H).close()
    .revolve(360, (0,0,0), (0,1,0)))
Do NOT use .box() for the main body of mugs, bottles, vases, cups, etc."""
            elif product_type == "game_controller":
                body_note = """

BODY SHAPE FIX — Your design uses .box() for an ERGONOMIC product.
REWRITE THE MAIN BODY using multi-section .loft():
  body = (cq.Workplane("XY")
    .ellipse(W*0.4, D*0.35)                    # Bottom: narrow
    .workplane(offset=H*0.3).ellipse(W*0.5, D*0.45)   # Middle: wider
    .workplane(offset=H*0.4).ellipse(W*0.45, D*0.4)    # Upper
    .workplane(offset=H*0.3).ellipse(W*0.3, D*0.25)    # Top: tapered
    .loft())
Do NOT use .box() for the main body of controllers, mice, remotes, etc."""
            elif product_type == "phone_case":
                body_note = """

PHONE CASE CUTOUT SHAPE FIX — The main body (box+shell) is FINE, but your CUTOUTS are wrong.
Do NOT change the body shape. Instead, REPLACE every .box() cutter with the correct shape:
  • USB-C: .slot2D(usb_w, usb_h) on XZ plane — pill/stadium shape
  • Buttons: .slot2D(btn_len, btn_depth) on YZ plane — rounded slots
  • Camera island: .rect(cam_w, cam_h) + .fillet(cam_r) — rounded rectangle
  • Camera lenses: .cylinder(wall*3, lens_r) — perfect circles
  • Speaker grille: Array of .cylinder(wall*3, dot_r) — row of circles
  • Microphone: .cylinder(wall*3, mic_r) — tiny circle
  • Action/mute: .cylinder(wall*3, mute_r) — small circle
  • SIM tray: .slot2D(sim_len, sim_w) — narrow pill
KEEP the body as .box() + .shell(). ONLY change the CUTTER shapes."""
            elif product_type == "drone":
                body_note = """

INCOMPLETE DRONE FIX — Your design is missing critical components. Identify the drone TYPE from the prompt:
  • Quadcopter/Racing: 4 arms + 4 motors + 4 propellers + canopy + landing gear
  • Hexacopter: 6 arms at 60° + 6 motors + 6 props + canopy + tall gear + payload rails
  • Octocopter: 8 arms at 45° + 8 motors + 8 props + canopy + very tall gear
  • Tricopter: Y-frame (2 front + 1 rear arm) + 3 motors + 3 props + TAIL SERVO + canopy + gear
  • Camera/DJI: lofted fuselage + 4 arms + motors + props + GIMBAL+CAMERA under front + retractable gear
  • Fixed-wing VTOL: lofted fuselage + WINGS + TAIL + 4 VTOL motors on booms + 1 pusher motor + all props
  • Mini: integrated ducted frame + 4 tiny motors inside ducts + props + tiny canopy (no legs)
  • Delivery: enclosed fuselage + 6-8 arms + motors + props + CARGO BAY under body + very tall gear
  • Underwater ROV: cage frame + enclosed thrusters + camera dome + LED lights + buoyancy foam + tether port
  • Agri spray: heavy frame + 6-8 arms + motors + props + SPRAY TANK + SPRAY BOOM + nozzles + wide tall gear

  KEEP the frame and ADD missing components by unioning them. Example for motors (adapt arm count):
  for angle in arm_angles:  # e.g., [45,135,225,315] for quad, [0,60,120,180,240,300] for hex
      rad = math.radians(angle)
      mx = tip_r * math.cos(rad); my = tip_r * math.sin(rad)
      motor = cq.Workplane("XY").cylinder(motor_h, motor_r)
      motor = motor.translate((mx, my, arm_top_z + motor_h/2))
      body = body.union(motor)
  Similarly add propellers (thin discs on motors), canopy (sphere half), landing gear (legs/skids).
  For type-specific features: gimbal bracket, cargo bay box, spray tank, thruster tubes, wing extrusions, etc."""
            elif product_type == "peripheral_mouse":
                body_note = """

MOUSE BODY SHAPE FIX — Your design uses .box() for an ERGONOMIC mouse.
REWRITE THE MAIN BODY using multi-section .loft():
  body = (cq.Workplane("XY")
    .ellipse(W*0.45, D*0.35)                              # Bottom: wide
    .workplane(offset=H*0.4).ellipse(W*0.5, D*0.45)       # Middle: widest bulge
    .workplane(offset=H*0.4).ellipse(W*0.35, D*0.3)       # Upper: narrowing
    .workplane(offset=H*0.2).ellipse(W*0.15, D*0.15)      # Top: tapered front
    .loft())
Then SPLIT the top surface for left/right buttons with a .cut() along centerline.
Add scroll wheel as .cylinder() recessed between buttons.
Do NOT use .box() for mice — they MUST be ergonomically shaped."""
            elif product_type == "audio_headphones":
                body_note = """

HEADPHONE BODY SHAPE FIX — Your design needs organic shapes.
Earcups should use multi-section .loft() for an organic oval shape:
  earcup = (cq.Workplane("XY")
    .ellipse(cup_w*0.45, cup_h*0.45)                      # Back face
    .workplane(offset=cup_d*0.3).ellipse(cup_w*0.5, cup_h*0.5)  # Widest
    .workplane(offset=cup_d*0.5).ellipse(cup_w*0.4, cup_h*0.4)  # Ear side
    .workplane(offset=cup_d*0.2).ellipse(cup_w*0.3, cup_h*0.3)  # Pad contact
    .loft())
Headband should use .sweep() along a curved arc:
  path = cq.Workplane("XZ").threePointArc((0, arc_h), (band_span, 0))
  band = cq.Workplane("XY").rect(band_w, band_t).sweep(path)
Do NOT use .box() for earcups or straight cylinders for the headband."""
            elif product_type == "laptop":
                body_note = """

LAPTOP COMPLETENESS FIX — A laptop has TWO main sections connected by a hinge:
  # Base section (keyboard half):
  base = cq.Workplane("XY").box(W, D, base_h).edges("|Z").fillet(R)
  # Screen section (display half):
  screen = cq.Workplane("XY").box(W, screen_t, screen_h).edges("|Z").fillet(R)
  screen = screen.translate((0, -D/2 + screen_t/2, base_h))  # Angled or vertical behind base
  # Hinge cylinders connecting them:
  hinge = cq.Workplane("XY").cylinder(hinge_w, hinge_r)
  hinge = hinge.translate((-W/4, -D/2, base_h))
ADD: keyboard key grid (array of small raised rectangles on base top face),
trackpad recess (rounded rectangle cut on front of base top),
port cutouts on sides (USB, HDMI, headphone jack), ventilation slots on bottom."""
            elif product_type == "wearable_watch":
                body_note = """

WATCH COMPLETENESS FIX — A smartwatch needs these key parts:
  # Round/rounded-rect case body (use .revolve() for round watches):
  case = cq.Workplane("XZ").moveTo(0,0).lineTo(case_r,0)
    .spline([(case_r, case_h*0.3), (case_r*0.95, case_h)])
    .lineTo(0, case_h).close().revolve(360, (0,0,0), (0,1,0))
  # Display recess on front face:
  case = case.faces(">Z").workplane().circle(display_r).cutBlind(-1.5)
  # Band attachment lugs (top and bottom):
  lug = cq.Workplane("XY").box(lug_w, lug_l, lug_h)
  case = case.union(lug.translate((0, case_r+lug_l/2, case_h/2)))
  case = case.union(lug.translate((0, -case_r-lug_l/2, case_h/2)))
  # Side crown/button:
  crown = cq.Workplane("YZ").cylinder(crown_l, crown_r)
  case = case.union(crown.translate((case_r+crown_l/2, 0, case_h*0.6)))"""
            elif product_type == "lamp":
                body_note = """

LAMP COMPLETENESS FIX — A desk/table lamp needs these components:
  # Weighted base (wide, stable):
  base = cq.Workplane("XY").circle(base_r).extrude(base_h).edges(">Z").fillet(base_h*0.3)
  # Stem/arm (cylinder or tube, optionally with a curve):
  stem = cq.Workplane("XY").circle(stem_r).extrude(stem_h)
  body = base.union(stem.translate((0, 0, base_h)))
  # Shade (truncated cone via .revolve() or .loft()):
  shade = (cq.Workplane("XY").transformed(offset=(0,0,total_h-shade_h))
    .circle(shade_top_r).workplane(offset=shade_h).circle(shade_bot_r).loft())
  body = body.union(shade)
  # Switch recess on stem, cable hole on base bottom"""
            elif product_type == "instrument":
                body_note = """

INSTRUMENT COMPLETENESS FIX — A string instrument (guitar/violin) needs:
  # Body: loft between cross-sections for the curved shape
  body = (cq.Workplane("XZ")
    .ellipse(body_w*0.4, body_d*0.4)                    # Upper bout
    .workplane(offset=body_l*0.4).ellipse(body_w*0.25, body_d*0.3)  # Waist
    .workplane(offset=body_l*0.6).ellipse(body_w*0.5, body_d*0.45)  # Lower bout
    .loft()).shell(-wall_t)  # Hollow it out
  # Sound hole: circular cut on top face
  body = body.faces(">Y").workplane().circle(sound_hole_r).cutThruAll()
  # Neck: rectangular prism with rounded edges
  neck = cq.Workplane("XZ").rect(neck_w, neck_d).extrude(neck_l)
  neck = neck.translate((0, 0, body_l))
  # Headstock + tuning pegs + bridge on body face"""
            elif product_type == "jewelry":
                body_note = """

JEWELRY BODY SHAPE FIX — Rings MUST be made with .revolve():
  # Ring band profile:
  profile = (cq.Workplane("XZ").moveTo(inner_r, 0)
    .lineTo(outer_r, 0)
    .spline([(outer_r+crown_h*0.3, band_h*0.5), (outer_r, band_h)])  # Slightly convex outer
    .lineTo(inner_r, band_h)
    .close())
  ring = profile.revolve(360, (0,0,0), (0,1,0))
  # For engagement ring: add raised setting on top
  setting = cq.Workplane("XY").polygon(6, prong_r).extrude(setting_h)  # 6-prong setting
  ring = ring.union(setting.translate((0, outer_r, band_h/2)))
NEVER use .box() for rings — they are revolved circular bands."""
            elif product_type == "sculpture":
                body_note = """

SCULPTURE COMPLETENESS FIX — Sculptures need organic forms:
  # Base/pedestal:
  base = cq.Workplane("XY").rect(base_w, base_d).extrude(base_h)
  base = base.edges(">Z").fillet(base_h*0.2)
  # Main form: use .loft() between shaped cross-sections for organic form:
  form = (cq.Workplane("XY").transformed(offset=(0,0,base_h))
    .ellipse(body_w*0.5, body_d*0.5)
    .workplane(offset=body_h*0.3).ellipse(body_w*0.4, body_d*0.35)
    .workplane(offset=body_h*0.5).ellipse(body_w*0.3, body_d*0.3)
    .workplane(offset=body_h*0.2).ellipse(body_w*0.15, body_d*0.15)
    .loft())
  result = base.union(form)
Use .spline() for surface detail and .fillet() liberally at all joints."""
            elif product_type == "kitchen":
                body_note = """

KITCHEN/COOKWARE COMPLETENESS FIX — Pots, pans, kettles need:
  # Body: use .revolve() for round cookware:
  profile = (cq.Workplane("XZ").moveTo(0, 0)
    .lineTo(base_r, 0)
    .spline([(base_r+2, 5), (top_r, H)])  # Slightly flared walls
    .lineTo(0, H).close()
    .revolve(360, (0,0,0), (0,1,0)))
  pot = profile.shell(-wall_t)  # Hollow interior
  # Handle: use .sweep() along curved arc
  handle_path = cq.Workplane("XZ").threePointArc((handle_rise, handle_len/2), (0, handle_len))
  handle = cq.Workplane("XY").circle(handle_r).sweep(handle_path)
  pot = pot.union(handle.translate((top_r, 0, H*0.7)))
  # Pour spout: small triangular cut tilted at rim
  # Lid: disc with knob on top"""
            else:
                body_note = """

BODY SHAPE FIX — Your design uses primitive box/lineTo construction.
Use advanced CadQuery techniques to make it look like a REAL manufactured product:
  • .spline() for curved profiles (not .lineTo() chains)
  • .loft() for transitions between cross-sections
  • .revolve() for axially symmetric shapes
  • .sweep() with .threePointArc() for curved handles
  • .tangentArcPoint() for smooth lip/rim transitions"""

        enhancement_prompt = f"""Your previous design for "{prompt}" is INCOMPLETE. It has these issues:

{missing}{shape_note}{body_note}

CURRENT CODE (keep ALL of this, ADD the missing features):
```python
{design_json['code']}
```

CURRENT PARAMETERS:
{json.dumps(design_json.get('parameters', []), indent=2)}

YOUR TASK:
1. KEEP all existing code exactly as-is (unless a BODY SHAPE FIX is required above)
2. INSERT new code to add EACH missing feature listed above
3. If BODY SHAPE FIX is required: REWRITE the main body construction using the recommended technique
4. ADD new parameters for each new feature
5. Position features using existing body dimension variables
6. Wrap new fillets in try/except

Return the COMPLETE updated JSON with parameters, code, and explanation.
Do NOT remove or simplify existing features — ONLY ADD what's missing."""

        print(f"🔄 Enhancement pass — adding {len(analysis['missing_features'])} missing features")
        
        import httpx
        max_stream_retries = 3
        for stream_attempt in range(1, max_stream_retries + 1):
            try:
                full_text = ""
                with self.client.messages.stream(
                    model=self.model,
                    max_tokens=16384,
                    temperature=0.25,
                    system=self._get_design_system_prompt(),
                    messages=[{"role": "user", "content": enhancement_prompt}]
                ) as stream:
                    for text in stream.text_stream:
                        full_text += text
                break
            except (httpx.ReadError, httpx.RemoteProtocolError, httpx.ConnectError,
                    ConnectionError, OSError) as net_err:
                print(f"⚠️ Network error on enhancement attempt {stream_attempt}: {net_err}")
                if stream_attempt == max_stream_retries:
                    print(f"⚠️ Enhancement failed after {max_stream_retries} attempts, using original design")
                    return design_json
                import time
                time.sleep(2 * stream_attempt)
        
        try:
            enhanced = self._extract_json_from_response(full_text)
            # Verify the enhancement didn't break things
            enhanced_code = enhanced.get("code", "")
            original_code = design_json.get("code", "")
            if len(enhanced_code) < len(original_code) * 0.7:
                print(f"⚠️ Enhancement produced shorter code ({len(enhanced_code)} vs {len(original_code)} chars) — keeping original")
                return design_json
            print(f"✅ Enhancement successful: {len(original_code)} → {len(enhanced_code)} chars")
            return enhanced
        except (ValueError, json.JSONDecodeError) as e:
            print(f"⚠️ Enhancement response parse failed: {e} — keeping original design")
            return design_json

    async def generate_design_from_prompt(
        self,
        prompt: str,
        previous_design: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Single-shot: Convert natural language prompt to complete CAD design JSON
        Uses streaming to handle large responses without SDK timeout errors.
        Adapts token budget and temperature based on prompt complexity.
        
        NOTE: Call analyze_code_completeness() and enhance_incomplete_design()
        separately after this to check and fix completeness.
        """
        
        complexity = self._detect_complexity(prompt)
        max_tokens = self._get_adaptive_tokens(complexity)
        temperature = self._get_adaptive_temperature(complexity)
        
        print(f"🧠 Complexity: {complexity} → tokens={max_tokens}, temp={temperature}")
        
        system_prompt = self._get_design_system_prompt()
        user_message = self._format_build_message(prompt, previous_design, complexity)
        
        # Use streaming to avoid SDK timeout for large max_tokens
        # Retry on transient network errors (WinError 10054, connection reset, etc.)
        import httpx
        max_stream_retries = 3
        for stream_attempt in range(1, max_stream_retries + 1):
            try:
                full_text = ""
                with self.client.messages.stream(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}]
                ) as stream:
                    for text in stream.text_stream:
                        full_text += text
                break  # Success — exit retry loop
            except (httpx.ReadError, httpx.RemoteProtocolError, httpx.ConnectError,
                    ConnectionError, OSError) as net_err:
                print(f"⚠️ Network error on stream attempt {stream_attempt}/{max_stream_retries}: {net_err}")
                if stream_attempt == max_stream_retries:
                    raise RuntimeError(
                        f"Anthropic API connection failed after {max_stream_retries} attempts. "
                        f"Last error: {net_err}. Please try again."
                    ) from net_err
                import time
                time.sleep(2 * stream_attempt)  # Backoff: 2s, 4s
        
        # Extract JSON from Claude's response
        design_json = self._extract_json_from_response(full_text)
        return design_json

    async def fix_code_with_error(
        self,
        failed_code: str,
        error_message: str,
        original_prompt: str,
        attempt: int,
        max_retries: int
    ) -> Dict[str, Any]:
        """
        Intelligent self-healing: send failed code + classified error to Claude
        for targeted repair. Each retry gets progressively more conservative.
        """
        
        # Classify the error to give Claude targeted advice
        error_lower = error_message.lower()
        error_category = "unknown"
        targeted_fix = ""
        
        if any(k in error_lower for k in ["standard_nullvalue", "stdfail_notdone", "fillet", "chamfer", "brep_api"]):
            error_category = "GEOMETRY_FILLET_CHAMFER"
            targeted_fix = (
                "The fillet or chamfer CRASHED — this is the #1 failure cause.\n"
                "ROOT CAUSE: Usually edges('%Circle').fillet(r) or fillet applied AFTER boolean cuts.\n"
                "The '%Circle' selector catches ALL circular edges including TINY internal edges from\n"
                "boolean cuts (holes, ports, slots) that are too small for the fillet radius.\n\n"
                "MANDATORY FIX STEPS:\n"
                "1. REMOVE ALL edges('%Circle').fillet() and edges('%Circle').chamfer() calls\n"
                "2. Replace with SPECIFIC selectors: edges('|Z'), edges('>Z'), edges('<Z')\n"
                "3. Wrap EVERY fillet/chamfer in try/except:\n"
                "   try:\n"
                "       body = body.edges('|Z').fillet(min(r, min(L,W) * 0.25))\n"
                "   except:\n"
                "       pass\n"
                "4. Do ALL fillets BEFORE boolean cuts (holes, slots, ports)\n"
                "5. If fillet was AFTER cuts, move it BEFORE cuts or remove it entirely\n"
                "6. Reduce ALL fillet radii by 60%: use min(desired_r, min(L,W,H) * 0.2)\n"
                "7. A working model without fillets is INFINITELY better than a crashing model"
            )
        elif any(k in error_lower for k in ["shell"]):
            error_category = "GEOMETRY_SHELL"
            targeted_fix = (
                "The shell operation failed — likely wall thickness too large, or conflicting geometry.\n"
                "FIX: Reduce shell thickness to min(wall, min(L,W,H) * 0.3).\n"
                "Ensure FILLET is done BEFORE shell. If shell still fails, switch to manual\n"
                "cavity subtraction: body.cut(cq.Workplane('XY').box(L-2*w, W-2*w, H).translate((0,0,w)))."
            )
        elif any(k in error_lower for k in ["wire is not closed", "not closed", "close()"]):
            error_category = "SKETCH_NOT_CLOSED"
            targeted_fix = (
                "A 2D sketch was not closed before extrude/revolve.\n"
                "FIX: Add .close() before .extrude() or .revolve().\n"
                "Verify the sketch path returns to its start point."
            )
        elif any(k in error_lower for k in ["selector", "topods", "no matching", "not found", "item()"]):
            error_category = "SELECTOR_FAILED"
            targeted_fix = (
                "A face/edge selector returned no results — the geometry doesn't have the expected topology.\n"
                "FIX: Use broader selectors. Replace .edges('|Z and >X') with .edges('|Z').\n"
                "Replace .faces('>Z').workplane() with .faces(cq.selectors.NearestToPointSelector((0,0,H)))\n"
                "or simply use .transformed(offset=...) positioning instead."
            )
        elif any(k in error_lower for k in ["geom_undefinedderivative", "tangent", "spline", "derivative"]):
            error_category = "CURVE_TANGENT"
            targeted_fix = (
                "A spline or arc has undefined tangent — degenerate curve.\n"
                "FIX: Replace the spline/arc with simpler lineTo() segments, or reduce\n"
                "the number of spline control points. Ensure no two adjacent points are identical."
            )
        elif any(k in error_lower for k in ["gp_islinearvectornullvector", "null vector", "revolve"]):
            error_category = "REVOLVE_AXIS"
            targeted_fix = (
                "The revolve axis passes through the profile, or profile is on the wrong side.\n"
                "FIX: Ensure the profile sketch stays entirely on ONE side of the revolve axis.\n"
                "For XZ revolve around Y: all X coordinates must be >= 0."
            )
        elif any(k in error_lower for k in ["division by zero", "zerodivision", "math domain"]):
            error_category = "MATH_ERROR"
            targeted_fix = (
                "A calculation produced division by zero or invalid math.\n"
                "FIX: Add guards: max(value, 0.1) for denominators, abs() for sqrt arguments.\n"
                "Check that loop counters and spacing calculations don't produce zero."
            )
        elif any(k in error_lower for k in ["loft", "not enough", "cross-section", "sections"]):
            error_category = "LOFT_FAILED"
            targeted_fix = (
                "A loft operation failed — cross-sections may be incompatible or too few.\n"
                "FIX: Ensure at least 2 cross-sections with the same wire count.\n"
                "Keep cross-sections simple (circles/rects). If loft fails, switch to\n"
                "extrude + taper using .transformed(offset=...) and boolean unions."
            )
        elif any(k in error_lower for k in ["boolean", "cut", "union", "intersect", "overlap"]):
            error_category = "BOOLEAN_FAILED"
            targeted_fix = (
                "A boolean operation (cut/union) failed — bodies may not overlap, or\n"
                "produce degenerate thin walls.\n"
                "FIX: Increase cutting body size by 1-2mm in each direction.\n"
                "Use wall*3 depth for cuts. Ensure boolean operands physically intersect."
            )
        elif any(k in error_lower for k in ["unexpected keyword", "centered", "got an unexpected"]):
            error_category = "WRONG_PARAMETER"
            targeted_fix = (
                "You passed a parameter to a method that doesn't accept it.\n"
                "MOST COMMON CAUSE: centered=(True,True,False) on .extrude() — WRONG!\n"
                "centered= is ONLY valid on .box(). NEVER on .extrude(), .rect(), .circle() etc.\n\n"
                "FIX:\n"
                "1. REMOVE centered= from ALL .extrude() calls\n"
                "2. REMOVE centered= from ALL .rect(), .circle(), .cylinder() calls\n"
                "3. centered=(True,True,False) goes ONLY on the MAIN BODY .box() call\n"
                "4. CUTTER .box() calls should NOT have centered= (use default centering)"
            )
        elif any(k in error_lower for k in ["sweep", "path", "makepipe", "pipe"]):
            error_category = "SWEEP_FAILED"
            targeted_fix = (
                "A sweep operation failed — the profile could not follow the path.\n"
                "COMMON CAUSES: path has sharp corners, profile is too large for the path radius,\n"
                "path is self-intersecting, or profile plane is not perpendicular to path start.\n\n"
                "FIX:\n"
                "1. Fillet the sweep path corners: use .radiusArc() instead of sharp .lineTo()\n"
                "2. Make the profile smaller (reduce cross-section by 30%)\n"
                "3. Ensure the profile workplane is at the START of the path and perpendicular to it\n"
                "4. If sweep still fails, replace with extrude + translate + union segments\n"
                "5. For tubes/pipes: use .circle(outer_r).circle(inner_r).extrude() instead"
            )
        elif any(k in error_lower for k in ["workplane", "stack", "pending wires", "no wire"]):
            error_category = "WORKPLANE_STACK"
            targeted_fix = (
                "Workplane stack error — operations were chained in the wrong order.\n"
                "COMMON CAUSES: calling .extrude() when there's no pending sketch,\n"
                "calling .workplane() on a face that doesn't exist, or sketch operations\n"
                "mixed with solid operations.\n\n"
                "FIX:\n"
                "1. Always start a new sketch with .workplane() or .faces('>Z').workplane()\n"
                "2. Complete sketch → .extrude() before starting next sketch\n"
                "3. Don't mix .rect()/.circle() with .box()/.cylinder() in same chain\n"
                "4. Break complex chains into separate variables for clarity\n"
                "5. Use .end() to pop back to parent context when needed"
            )
        elif any(k in error_lower for k in ["standard_failure", "occ", "kernel", "brep", "gp_pnt"]):
            error_category = "OCC_KERNEL_ERROR"
            targeted_fix = (
                "The OpenCascade (OCC) geometry kernel hit an internal error.\n"
                "This usually means the geometry request is impossible or degenerate.\n\n"
                "FIX:\n"
                "1. Check for zero-thickness walls, zero-radius arcs, or overlapping faces\n"
                "2. Increase minimum dimensions: no feature smaller than 0.5mm\n"
                "3. Add small gaps (0.1mm) between touching-but-not-intersecting bodies\n"
                "4. Simplify the failing region — replace complex geometry with a simple primitive\n"
                "5. If a compound boolean chain fails, split into individual cut/union steps\n"
                "6. Avoid fillets/chamfers on edges that share a vertex with other features"
            )
        elif any(k in error_lower for k in ["nonetype", "has no attribute", "attributeerror", "'none'"]):
            error_category = "ATTRIBUTE_ERROR"
            targeted_fix = (
                "An operation returned None or an unexpected type — the chain is broken.\n"
                "COMMON CAUSES: a selector returned nothing, a method was misspelled,\n"
                "or a variable was overwritten with an incompatible type.\n\n"
                "FIX:\n"
                "1. Check selector results: .faces('>Z') may fail if shape has no top face\n"
                "2. Make sure variable names aren't reused for different types\n"
                "3. Use .val() carefully — it returns a Shape, not a Workplane\n"
                "4. Ensure .pushPoints() receives a list of tuples, not a generator\n"
                "5. Replace .item(i) with broader selectors like .first() or direct index"
            )
        elif any(k in error_lower for k in ["typeerror", "expected", "argument", "not callable", "int object"]):
            error_category = "TYPE_ERROR"
            targeted_fix = (
                "A type mismatch — wrong argument type passed to a CadQuery method.\n\n"
                "FIX:\n"
                "1. Ensure numeric arguments are float, not int or string: use 5.0 not 5\n"
                "2. Check tuple vs list: .box(L, W, H) not .box([L, W, H])\n"
                "3. centered= must be a tuple of 3 bools: centered=(True, True, False)\n"
                "4. Selector strings must be str, not raw expressions\n"
                "5. .pushPoints() takes List[Tuple[float, float]], not a list of lists"
            )
        elif any(k in error_lower for k in ["empty", "no solid", "null shape", "compound is empty"]):
            error_category = "EMPTY_RESULT"
            targeted_fix = (
                "The geometry operation produced an empty or null result.\n"
                "COMMON CAUSES: a cut removed the entire body, an extrude height was 0,\n"
                "or two bodies didn't actually intersect for a boolean op.\n\n"
                "FIX:\n"
                "1. Check cut depths — cutters should NOT exceed body dimensions\n"
                "2. Ensure extrude heights are > 0.1mm\n"
                "3. For .cut(): verify the cutter actually overlaps the body\n"
                "4. For .intersect(): verify both bodies share volume\n"
                "5. Add dimension guards: extrude_height = max(value, 0.5)"
            )
        elif any(k in error_lower for k in ["name", "is not defined", "nameerror"]):
            error_category = "NAME_ERROR"
            targeted_fix = (
                "A variable or function name is not defined — likely a typo or missing definition.\n\n"
                "FIX:\n"
                "1. Check for typos in variable names (e.g., 'boby' vs 'body')\n"
                "2. Ensure all variables are defined before use\n"
                "3. CadQuery is 'cq' not 'cadquery' after import — use cq.Workplane()\n"
                "4. Math functions need 'import math' — math.sin(), math.pi, etc.\n"
                "5. Don't use undefined helper functions — inline the logic"
            )
        else:
            error_category = "GENERAL"
            targeted_fix = (
                "General execution error.\n"
                "FIX: Simplify the failing section. Break complex chains into variables.\n"
                "Test each operation independently. If an advanced operation fails,\n"
                "replace it with a simpler primitive equivalent."
            )
        
        # Progressive conservatism: graduated phases that cycle for infinite retries
        # Phase 1 (attempts 1):     Targeted fix — change only the failing operation
        # Phase 2 (attempts 2-3):   Conservative — reduce radii, simplify risky ops
        # Phase 3 (attempts 4-5):   Aggressive — strip fillets/chamfers, simplify geometry
        # Phase 4 (attempts 6-7):   Rebuild — rewrite the failing section from scratch
        # Phase 5 (attempts 8+):    Nuclear — rebuild entire model using only safe primitives
        conservatism_note = ""
        if attempt == 1:
            conservatism_note = (
                "\n🔧 RETRY #1 — TARGETED FIX:\n"
                "• Fix ONLY the specific failing operation\n"
                "• Reduce fillet/chamfer radii by 30%\n"
                "• Wrap risky operations in try/except\n"
                "• Keep all features and detail intact"
            )
        elif attempt <= 3:
            conservatism_note = (
                f"\n⚠️ RETRY #{attempt} — CONSERVATIVE MODE:\n"
                "• Reduce ALL fillet/chamfer radii by 60%\n"
                "• Simplify complex splines (reduce control points, keep .spline() with fewer points)\n"
                "• Break complex booleans into simpler steps\n"
                "• Wrap EVERY fillet/chamfer in try/except with pass fallback\n"
                "• KEEP .revolve(), .loft(), .sweep() if they are the main body — simplify them, don't remove\n"
                "• If a loft fails, reduce to 2 cross-sections. If revolve fails, simplify the profile.\n"
                "• If a feature is risky, simplify it — don't remove it"
            )
        elif attempt <= 5:
            conservatism_note = (
                f"\n🚨 RETRY #{attempt} — AGGRESSIVE SIMPLIFICATION:\n"
                "• REDUCE all fillet/chamfer radii by 80% (use min(r*0.2, 1.0))\n"
                "• Wrap EVERY fillet/chamfer in try/except with pass\n"
                "• Simplify spline profiles to 2-3 control points or replace with .threePointArc()\n"
                "• If .loft() crashes: replace with .extrude() + taper via boolean\n"
                "• If .revolve() crashes: simplify profile to lineTo + one threePointArc\n"
                "• If .sweep() crashes: replace with .extrude() along the straight direction\n"
                "• Replace shells with manual cavity cuts\n"
                "• Replace complex selectors with simple ones: edges('|Z'), faces('>Z')\n"
                "• Keep .cylinder() and .slot2D() cutouts — only simplify if they crash\n"
                "• A working model with small fillets is better than a crashing detailed one"
            )
        elif attempt <= 7:
            conservatism_note = (
                f"\n🔥 RETRY #{attempt} — REWRITE THE FAILING SECTION:\n"
                "• The previous fixes did NOT work. Do NOT make small tweaks.\n"
                "• REWRITE the failing section from scratch using a different approach\n"
                "• Use these safe patterns:\n"
                "  - .box(), .cylinder() for primitives\n"
                "  - .cut() / .union() for booleans\n"
                "  - .translate() for positioning\n"
                "  - .workplane().center(x,y) for 2D placement\n"
                "  - .rect().extrude() / .circle().extrude() for features\n"
                "  - .revolve(360) with SIMPLE lineTo-only profile (if product is round)\n"
                "• MINIMAL fillets only: wrap in try/except, use radius <= 1.0mm\n"
                "• NO shells, NO complex splines, NO multi-section loft\n"
                "• You MAY use .revolve() with a simple lineTo profile for round products\n"
                "• Use .transformed(offset=(...)) instead of face selectors"
            )
        else:
            conservatism_note = (
                f"\n☢️ RETRY #{attempt} — NUCLEAR REBUILD:\n"
                "• EVERY previous approach has failed. Start the code from SCRATCH.\n"
                "• Build the product using ONLY the simplest possible geometry:\n"
                "  1. One main .box() or .cylinder() with centered=(True,True,False)\n"
                "     For round products: use .circle(R).extrude(H) instead of .box()\n"
                "  2. Simple .cut() operations with .box()/.cylinder() cutters\n"
                "  3. NO shells, lofts, sweeps, complex splines, or complex selectors\n"
                "  4. Position everything with .translate() — NO face selectors\n"
                "  5. Keep ALL parameters but simplify the geometry that uses them\n"
                "• You MAY add try/except wrapped fillets on the main body edges\n"
                "• Use .cylinder() for round cutouts to avoid total brick appearance\n"
                "• For round products (mugs etc.), use .circle(R).extrude(H) not .box()\n"
                "• The goal is a working .stl that still resembles the product"
            )
        
        # Extract code context from error message if available (added by enhanced error reporting)
        code_context_block = ""
        if "CODE CONTEXT:" in error_message:
            parts = error_message.split("CODE CONTEXT:")
            error_msg_clean = parts[0].strip()
            code_context_block = f"\n\n═══ FAILING CODE CONTEXT (>>> marks the crashing line) ═══\n{parts[1].strip()}\n"
        else:
            error_msg_clean = error_message
        
        fix_prompt = (
            f"═══ ERROR CATEGORY: {error_category} ═══\n"
            f"ERROR MESSAGE: {error_msg_clean}\n"
            f"{code_context_block}\n"
            f"TARGETED FIX STRATEGY:\n{targeted_fix}\n"
            f"{conservatism_note}\n\n"
            f"FAILED CODE:\n```python\n{failed_code}\n```\n\n"
            f"ORIGINAL REQUEST: {original_prompt}\n\n"
        )
        
        # Adapt rules based on healing phase
        if attempt <= 3:
            fix_prompt += (
                "RULES:\n"
                "1. FIX ONLY the failing operation — do NOT remove features or strip detail\n"
                "2. Keep ALL parameters, ALL cutouts, ALL features intact\n"
                "3. If a fillet fails, reduce radius — don't remove the fillet entirely\n"
                "4. If a boolean fails, increase overlap — don't remove the cut\n"
                "5. If a loft fails, simplify cross-sections — don't remove the shape\n"
                "6. Test your fix mentally: will THIS specific change resolve the error?\n"
                "7. The code must still produce the SAME product with the SAME features\n"
                "8. Look at the CODE CONTEXT above — the >>> line is EXACTLY where it crashed.\n"
                "   Fix THAT line specifically. Don't rewrite the whole code.\n\n"
            )
        elif attempt <= 5:
            fix_prompt += (
                "RULES:\n"
                "1. You may REDUCE fillet/chamfer radii to 20% or wrap in try/except\n"
                "2. You may replace shells with manual cavity cuts\n"
                "3. You may replace lofts and sweeps with simpler extrusions\n"
                "4. Keep ALL functional features (cuts, holes, ports, slots)\n"
                "5. Keep .cylinder() and .slot2D() cutouts — don't replace them with .box()\n"
                "6. Keep ALL parameters — but simplify how geometry uses them\n"
                "7. Do NOT just tweak — if an approach failed twice, use a DIFFERENT approach\n\n"
            )
        elif attempt <= 7:
            fix_prompt += (
                "RULES:\n"
                "1. REWRITE the failing portion completely — small tweaks are NOT enough\n"
                "2. Keep the overall product shape but rebuild using basic operations\n"
                "3. Keep ALL parameters — they must still appear in the code\n"
                "4. Preferred: .box(), .cylinder(), .cut(), .union(), .translate(), .extrude()\n"
                "5. For ROUND products: you MAY still use .revolve() with simple lineTo profile\n"
                "6. You MAY include try/except wrapped .fillet() with radius <= 1.0mm\n"
                "7. AVOID: .shell(), complex splines, multi-section loft, complex selectors\n\n"
            )
        else:
            fix_prompt += (
                "RULES:\n"
                "1. Write the ENTIRE code from SCRATCH — do NOT copy the failed code\n"
                "2. Build the product using ONLY .box(), .cylinder(), .cut(), .union()\n"
                "3. For round products: use .circle(R).extrude(H) instead of .box()\n"
                "4. Keep ALL parameter names and use them, but simplify geometry drastically\n"
                "5. Use .cylinder() for round features to avoid total brick appearance\n"
                "6. You MAY add try/except wrapped .fillet() on main body edges only\n"
                "7. The result MUST be a valid solid that exports to STL\n\n"
            )
        
        fix_prompt += "Return the COMPLETE corrected design JSON with parameters, code, and explanation."
        
        print(f"🔧 Fix attempt {attempt} | Category: {error_category}")
        
        return await self.generate_design_from_prompt(prompt=fix_prompt)
    
    async def chat_about_design(
        self,
        message: str,
        conversation_history: List[Dict[str, str]],
        current_design: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Conversational: Guide user through design parameters
        
        Returns:
            {
                "message": "Claude's response",
                "updatedDesign": {...} or None,
                "shouldBuild": bool
            }
        """
        
        system_prompt = self._get_chat_system_prompt()
        messages = self._format_chat_messages(message, conversation_history, current_design)
        
        # Retry on transient network errors (WinError 10054, connection reset, etc.)
        import httpx
        max_stream_retries = 3
        for stream_attempt in range(1, max_stream_retries + 1):
            try:
                full_text = ""
                with self.client.messages.stream(
                    model=self.model,
                    max_tokens=settings.AI_MAX_TOKENS,
                    temperature=settings.AI_TEMPERATURE,
                    system=system_prompt,
                    messages=messages
                ) as stream:
                    for text in stream.text_stream:
                        full_text += text
                break  # Success — exit retry loop
            except (httpx.ReadError, httpx.RemoteProtocolError, httpx.ConnectError,
                    ConnectionError, OSError) as net_err:
                print(f"⚠️ Chat network error on attempt {stream_attempt}/{max_stream_retries}: {net_err}")
                if stream_attempt == max_stream_retries:
                    raise RuntimeError(
                        f"Anthropic API connection failed after {max_stream_retries} attempts. "
                        f"Last error: {net_err}. Please try again."
                    ) from net_err
                import time
                time.sleep(2 * stream_attempt)  # Backoff: 2s, 4s
        
        assistant_message = full_text
        
        # Parse response for design updates and build readiness
        result = self._parse_chat_response(assistant_message, current_design)
        return result
    
    def _get_design_system_prompt(self) -> str:
        """System prompt for single-shot design generation with CadQuery expertise"""
        return """You are a WORLD-CLASS CadQuery CAD engineer and industrial designer. You translate natural language — from vague ideas to hyper-detailed specs — into production-quality parametric CadQuery Python code.

═══════════════════════════════════════════════════════════════════════════════
CRITICAL: OUTPUT FORMAT (RAW JSON — NO MARKDOWN WRAPPING)
═══════════════════════════════════════════════════════════════════════════════

Return ONLY this JSON object (no ```json fences, no text before/after):

{
  "parameters": [
    {
      "name": "body_length",
      "description": "Main body length (X-axis)",
      "default": 150.0,
      "min": 10.0,
      "max": 2000.0,
      "unit": "mm"
    }
  ],
  "code": "import cadquery as cq\\nimport math\\n\\nresult = ...",
  "explanation": {
    "design_intent": "What was built and the key design decisions",
    "features_created": "Bullet-point list of every feature/detail in the model (e.g., '• USB-C charging port cutout on bottom edge', '• Volume buttons on left side')",
    "dimensions_summary": "Key dimensions in plain English (e.g., '146.6 × 70.6 × 8.3 mm body with 1.5mm walls')",
    "construction_method": "How it was built step-by-step (e.g., 'Started with a solid box, hollowed with shell, cut button openings, added fillets')",
    "what_you_can_modify": "Plain-English list of what the user can ask to change (e.g., 'Ask me to adjust wall thickness, add grip texture, change corner radius, etc.')",
    "suggested_next_steps": [
      "Add grip texture to the sides",
      "Add a lanyard hole at the bottom corner",
      "Add a kickstand on the back",
      "Round the edges more for comfort",
      "Add ventilation slots"
    ]
  }
}

IMPORTANT — "suggested_next_steps" RULES:
  • Generate 3-6 SHORT suggestions (under 10 words each) specific to THIS product.
  • Each suggestion must be something you CAN actually implement in CadQuery.
  • Think like a product designer: what would make this product more professional, more functional, more polished?
  • Suggestions should be DIFFERENT types: aesthetic (fillets, textures), functional (holes, mounts, clips), structural (ribs, thickness).
  • Examples by product type:
    - Phone case: "Add grip texture", "Add a wrist strap hole", "Add card slot on back", "Thicken the corners for drop protection"
    - Desk organizer: "Add pen holes", "Add cable routing slot", "Add non-slip feet", "Add a phone stand slot"
    - Building: "Add a chimney", "Add window shutters", "Add front steps", "Add a garage door"
    - Enclosure: "Add mounting ears", "Add ventilation grille", "Add LED window", "Add rubber foot recesses"
  • NEVER suggest something already in the model.
  • Each must be a simple command the user can click to apply.

═══════════════════════════════════════════════════════════════════════════════
DESIGN PHILOSOPHY — THINK LIKE AN INDUSTRIAL DESIGNER
═══════════════════════════════════════════════════════════════════════════════

When the user describes a product, ALWAYS ask yourself:

1. **What is this product's PRIMARY FUNCTION?**
   → A phone case protects; a stand supports; a bracket mounts.

2. **What SUB-FEATURES make it real?**
   → Holes, slots, lips, ribs, chamfers, fillets, textures, vents, snap-fits.

3. **What are REALISTIC DIMENSIONS for this product?**
   Reference table (all in mm):
   • Phone case:      150×75×10, wall 1.5-2
   • Tablet stand:    250×180×8
   • Laptop stand:    300×250, height 80-150
   • Desk organizer:  250×150×120
   • Bottle/tumbler:  Ø65×180, wall 2-3
   • Headphone stand: 120×120×250
   • Game controller: 155×105×60
   • Keyboard wrist rest: 440×80×25
   • Monitor riser:   500×250×100
   • Gear: module 2-5, 12-60 teeth
   • Bearing housing: Ø40-80, wall 5-10
   • Enclosure (PCB): 100×60×30, wall 2-3
   • Furniture leg:   Ø40×400
   • Drawer handle:   128mm center-to-center
   • Cable organizer: 80×80×30
   • Pen holder:      Ø60×100
   • Bookend:         130×100×150
   • Coaster:         Ø90×5
   • Hook/hanger:     50×30×80
   • Speaker housing: 120×120×180
   • Drone frame:     250×250×40
   • RC car chassis:  300×180×60
   • Watch stand:     80×60×100
   — SCULPTURES & ART —
   • Desktop figurine: 40-80mm tall, base Ø30-50
   • Trophy:          base 80×80, height 200-300
   • Bust (head+shoulders): 150×120×200
   • Abstract sculpture: 100-300mm tall
   • Chess piece (king): Ø25×80, base Ø30
   • Award plaque:     200×150×15
   • Relief panel:      150×100×10, relief depth 2-5
   — ARCHITECTURE & BUILDINGS —
   • House model:      200×150×120 (1:100 scale)
   • Skyscraper model: 80×80×400 (1:500 scale)
   • Church/cathedral: 200×100×250
   • Castle:           300×200×180
   • Bridge model:     400×60×100
   • Column (Doric):   Ø40×200
   • Arch:             span 100, rise 60, depth 30
   • Lighthouse:       Ø60×250
   • Dome:             Ø120×80
   • Tower (clock):    60×60×200
   • Pyramid:          base 150×150, height 100
   • Pagoda:           base 100×100, height 200, 3-5 tiers

4. **How would this be MANUFACTURED?** (3D printed / CNC / injection moulded)
   → This informs wall thickness, draft angles, rib placement.

5. **What makes it ELEGANT?** → Fillets on exposed edges, chamfers on internal edges, consistent radii.

GOLDEN RULE: If the user gives detailed instructions, follow EVERY detail.
If the user is vague, INFER the missing details using your product knowledge.

═══════════════════════════════════════════════════════════════════════════════
MANDATORY FUNCTIONAL DETAIL COMPLETENESS
═══════════════════════════════════════════════════════════════════════════════

⚠️  CRITICAL: The #1 quality issue is MISSING SMALL DETAILS. A phone case
without a charging port cutout is USELESS. A building without windows is
a featureless box. EVERY product has functional details that MUST be modeled.

BEFORE writing ANY code, you MUST mentally enumerate ALL functional details
for the product. Use the checklists below as a starting point, then add any
product-specific details.

──── UNIVERSAL DETAIL CHECKLIST (applies to ALL products) ────
□ Openings & ports     — charging ports, USB cutouts, cable holes, ventilation
□ Buttons & controls   — power buttons, volume keys, switches, dials, toggles
□ Mounting features    — screw holes, brackets, tabs, snap-fit clips, pegs
□ Edge treatment       — fillets on exposed edges, chamfers on internal edges
□ Surface features     — grip textures, labels/text, logos, grooves, ribs
□ Structural details   — internal ribs, gussets, bosses, standoffs, walls
□ Functional geometry  — lips, rims, ledges, channels, guides, rails, stops
□ Assembly features    — alignment pins, interlocking tabs, press-fit sockets
□ Aesthetic details    — decorative lines, bevels, contours, insets, patterns

──── PRODUCT-SPECIFIC DETAIL CHECKLISTS ────

📱 PHONE/TABLET CASE:
  □ Charging port cutout (USB-C or Lightning — check phone model!)
  □ Speaker grille cutout(s) at bottom
  □ Microphone hole(s)
  □ Camera island cutout with raised protective lip
  □ Each side button cutout (volume up, volume down, power/side button)
  □ Mute toggle / Action button cutout (model-specific!)
  □ Screen lip (raised edge ~1mm to protect screen when face-down)
  □ Camera lip (raised ring around camera cutout ~0.5mm)
  □ SIM tray access (slot or cutout)
  □ Rounded/filleted internal edges for easy phone insertion

💻 ELECTRONICS ENCLOSURE / PCB BOX:
  □ Ventilation slots or grille pattern
  □ Mounting bosses (4 corners with screw holes for PCB standoffs)
  □ Cable/connector pass-through holes on walls
  □ LED window/light pipe hole
  □ Power jack / barrel connector cutout
  □ USB / HDMI / Ethernet port cutouts on appropriate walls
  □ Lid attachment features (screw tabs, snap clips, or tongue-and-groove)
  □ Rubber foot recesses on bottom
  □ Internal PCB rail guides or standoffs
  □ Label recess area for stickers

🏠 BUILDING / HOUSE / STRUCTURE:
  □ Windows on EVERY appropriate wall (arrays with proper spacing)
  □ Door(s) — main entrance + side/back doors as appropriate
  □ Roof — gabled, flat, hip, or dome (NOT just a flat-top box)
  □ Chimney (for residential buildings)
  □ Foundation / base platform with slight step
  □ Window sills and lintels
  □ Door frame / doorstep
  □ Gutters / roof overhang
  □ Steps/stairs at entrance(s)
  □ Architectural details: cornices, skirting, quoins (corner stones)

🏰 CASTLE / FORTRESS:
  □ Crenellations (battlements) on ALL tower tops and walls
  □ Gate with arch (pointed or rounded)
  □ Drawbridge outline or portcullis groove
  □ Arrow slits / loopholes in walls
  □ Corner towers (round or square)
  □ Curtain walls connecting towers
  □ Keep (central fortified building)
  □ Turret caps / conical roofs on towers

🗿 SCULPTURE / FIGURINE / TROPHY:
  □ Pedestal or base (weighted, stable)
  □ Surface details — facial features, clothing folds, texture
  □ Proportional limbs / body sections
  □ Nameplate recess or engraving area on base
  □ Smooth transitions between body parts (fillets at joints)

🎮 GAME CONTROLLER / PERIPHERAL:
  □ All buttons (A/B/X/Y, bumpers, triggers, D-pad)
  □ Thumbstick holes
  □ Grip texture on handles
  □ Charging port at bottom/front
  □ Speaker/microphone holes
  □ Light bar slot / LED window
  □ Battery compartment cover outline

🚁 DRONE (COMPLETE ASSEMBLY — match type to user request!):

  QUADCOPTER / RACING FPV (default when just "drone" or "quadcopter"):
  □ Central body: stacked circular plates with spacer posts
  □ 4 Arms in X-config (45° from forward)
  □ 4 MOTORS: cylinders on arm tips (~22mm Ø × 15mm)
  □ 4 PROPELLERS: thin discs on motors (~127mm Ø × 2mm)
  □ CANOPY: dome over center, LANDING GEAR: legs/skids

  HEXACOPTER (when "hexacopter", "hex drone", "heavy lift"):
  □ 6 Arms at 60° intervals, 6 MOTORS, 6 PROPELLERS
  □ Large center body, tall landing gear (120mm+), payload rails

  OCTOCOPTER (when "octocopter", "8 motor", "cinema drone"):
  □ 8 Arms at 45° intervals, 8 MOTORS, 8 PROPELLERS
  □ Heavy-duty center hub, very tall retractable gear (150mm+)

  TRICOPTER (when "tricopter", "Y-frame", "3 motor"):
  □ Y-shaped frame: 2 front arms + 1 rear tail boom
  □ 3 MOTORS, 3 PROPELLERS, TAIL SERVO tilt mechanism on rear arm

  CAMERA/PHOTO DRONE (when "camera drone", "DJI", "photography drone"):
  □ Lofted/streamlined fuselage body (NOT flat plates)
  □ 4 Arms, 4 MOTORS, 4 large PROPELLERS (230mm)
  □ 3-AXIS GIMBAL + CAMERA under front body, retractable gear

  FIXED-WING VTOL (when "fixed wing", "VTOL", "survey/mapping drone"):
  □ Streamlined fuselage (loft, NOT box) + WINGS + TAIL
  □ 4 VTOL motors on wing booms + 1 pusher motor at rear + all props
  □ Landing skids, pitot tube, GPS dome

  MINI DRONE (when "tiny whoop", "mini drone", "micro drone"):
  □ Integrated ducted frame (4 circular guards fused into body)
  □ 4 tiny motors inside ducts, 4 small props
  □ Tiny canopy, no legs (flat-bottom), micro FPV camera

  DELIVERY DRONE (when "delivery drone", "cargo drone"):
  □ Enclosed fuselage + 6-8 arms + motors + props
  □ CARGO BAY under body with release hook/winch
  □ Very tall landing gear (180mm+) for package clearance

  UNDERWATER ROV (when "underwater drone", "ROV"):
  □ Open cage frame (NOT enclosed fuselage)
  □ 4-6 enclosed thrusters (tubes with props inside)
  □ Camera dome + LED floodlights on front
  □ Buoyancy foam on top, tether port on rear

  AGRICULTURAL SPRAY DRONE (when "spray drone", "farm drone"):
  □ 6-8 heavy arms + large motors + props
  □ SPRAY TANK on body + SPRAY BOOM with nozzles underneath
  □ Extra-wide tall landing gear (200mm+) for crop clearance

  ⚠️ Every air drone MUST have visible MOTORS + PROPELLERS — without them it's a flat PCB!

☕ DRINKWARE (MUG / BOTTLE / TUMBLER):
  □ Handle (C-shape, D-shape, or integrated grip)
  □ Lip / rim at top (rounded for comfort)
  □ Base foot ring or non-slip bottom
  □ Lid features (spout, straw hole, flip mechanism)
  □ Double-wall gap if insulated
  □ Capacity/measurement marks

🔧 TOOLS / HARDWARE:
  □ Grip texture / knurling on handles
  □ Anti-roll flats (hex section)
  □ Hanging hole at end
  □ Working end geometry (blade, bit, jaw)
  □ Material transition points (metal shaft meets plastic handle)

🗄️ FURNITURE / DESK ACCESSORIES:
  □ Non-slip feet / pads on bottom
  □ Cable management holes or channels
  □ Ventilation slots (for electronics stands)
  □ Lip/stop edge (prevent items sliding off)
  □ Compartment dividers at correct heights
  □ Pen/tool holes at correct diameters
  □ Drawer slides / handle recesses

🚗 AUTOMOTIVE / VEHICLE PARTS:
  □ Mounting holes / bolt patterns for attachment
  □ Draft angles on molded surfaces (1-3°)
  □ Ribbing on reverse side for structural rigidity
  □ Snap-fit clips or screw bosses for assembly
  □ Gasket groove or seal channel around perimeter
  □ Wire/cable pass-through holes with strain relief slots
  □ Alignment pins or datum features for positioning
  □ Fillet all internal corners (stress concentrators)
  □ Part number / mold mark recess on hidden face

⚙️ MECHANICAL ASSEMBLY / MECHANISM:
  □ Bearing seats with correct bore tolerances
  □ Shaft keyways or set screw flats
  □ Clearance gaps between moving parts
  □ Assembly guides (chamfered lead-ins on mating parts)
  □ Fastener holes with counterbore or countersink
  □ Alignment pins / dowel holes for accurate assembly
  □ Grease channels or lubrication ports
  □ Travel limits / mechanical stops

📦 CONTAINERS / STORAGE (bins, boxes, crates):
  □ Stacking features (rim + recess for nesting)
  □ Handle cutouts or grip recesses on sides
  □ Drainage holes (if outdoor/wet use)
  □ Label holder slot or tag window
  □ Reinforced corners or edge guards
  □ Lid retention features (snap lip, hinge recess, or gasket groove)
  □ Internal dividers or compartment walls
  □ Anti-slip feet or base texture

🎸 MUSICAL INSTRUMENTS / AUDIO:
  □ Sound holes / resonance ports with decorative surround
  □ String / wire anchor points
  □ Tuning peg holes at correct spacing
  □ Finger position markers / fret inlays
  □ Volume/control knob recesses
  □ Input/output jack cutouts
  □ Strap button mounting bosses
  □ Speaker grille pattern (perforated array)

⚽ SPORTING GOODS / FITNESS:
  □ Grip texture / knurling on handles
  □ Weight reduction holes or channels
  □ Strap/lanyard anchor points
  □ Protective bumpers on impact zones
  □ Contoured grip following hand ergonomics
  □ Measurement markings or scale indicators
  □ Drainage / ventilation holes for moisture
  □ Quick-release or locking mechanism features

🍳 KITCHEN / APPLIANCE:
  □ Pour spout or drip channel
  □ Measurement graduations (embossed or recessed lines)
  □ Steam / ventilation holes on lid
  □ Handle with heat-break gap (air gap from hot body)
  □ Non-slip base (feet or textured bottom)
  □ Cable exit channel with strain relief
  □ Control panel recess (button holes, display cutout)
  □ Drip tray or condensation channel
  □ Food-safe fillets (no sharp internal corners ≥ R2mm)

⌚ WEARABLE / ACCESSORY:
  □ Strap/band attachment lugs with pin holes
  □ Curved back surface matching body contour
  □ Display window / crystal recess
  □ Button recesses on sides (crown, pushers)
  □ Sensor window on back (for smartwatches)
  □ Charging contact pad recess
  □ Water resistance gasket groove around crystal
  □ Clasp / buckle mechanism features

💡 LIGHTING / LAMP:
  □ Bulb socket / LED module recess
  □ Ventilation slots for heat dissipation
  □ Cable entry hole with grommet recess
  □ Switch cutout or rocker switch recess
  □ Diffuser panel slot or lens holder groove
  □ Mounting bracket holes (for wall/ceiling mount)
  □ Reflector cavity with parabolic or conical interior
  □ Weighted base (wider/heavier bottom for stability)

🔌 CONNECTORS / ADAPTERS:
  □ Male/female mating features with guide chamfers
  □ Locking tab or retention clip
  □ Keying features (asymmetric shape prevents wrong insertion)
  □ Contact pin holes at correct pitch
  □ Strain relief at cable entry
  □ Housing shell with snap-fit seam
  □ Protective cap recess or tether loop

──── DETAIL ENFORCEMENT RULE ────

TIER 1 — ABSOLUTE MINIMUM (every product, no exceptions):
  • 4+ cutouts/openings (ports, holes, vents, windows, slots, channels)
  • 3+ surface treatments (fillets, chamfers, textures, grooves, bevels)
  • 2+ functional sub-features (lip, rib, boss, mounting point, foot, bracket)
  • Fillets on ALL visible external edges (no sharp corners on consumer products)
  • At least 1 text element or label recess (brand name, model number, or indicator)
  • NO BLANK FACES — every face must have at least one feature or edge treatment

TIER 2 — GOOD QUALITY (aim for this on standard complexity):
  • 6+ cutouts/openings
  • 4+ surface treatments
  • 3+ functional sub-features
  • Edge treatment varies by function (larger fillets on grip areas, small chamfers on mating edges)
  • At least 1 array/pattern feature (vent grid, screw pattern, decorative holes)

TIER 3 — PROFESSIONAL (expected for high-complexity designs):
  • 8+ cutouts/openings with varied sizes and purposes
  • 6+ surface treatments including micro-details (panel lines, grip texture grooves)
  • 5+ functional sub-features (ribs, bosses, guides, clips, stops, gasket grooves)
  • Multi-level edge treatment (exterior fillets, interior chamfers, transition radii)
  • Secondary structure (internal ribs, stiffener walls, wire channels, screw posts)
  • Tertiary details (indicator dots, assembly marks, anti-slip patterns, logo recess)

THE NO-BLANK-FACE RULE:
  Examine EVERY face of the finished product. If ANY face is a completely flat,
  featureless rectangle/surface with no cutouts, fillets, labels, or texture,
  then the design is INCOMPLETE. Real products have:
  • Top face: labels, buttons, display cutout, ventilation, grip texture
  • Bottom face: rubber feet, label recess, serial number area, anti-slip pattern
  • Side faces: ports, buttons, vents, panel lines, grip contours
  • Front face: display, branding, controls, indicator LEDs
  • Back face: ports, vents, mounting slots, label/compliance markings

DETAIL SELF-AUDIT (run this before returning):
  For each face of the product, write a mental comment:
    "Top face: has ventilation slots + logo text + fillet edges ✓"
    "Bottom face: has 4 rubber feet + label recess + drainage holes ✓"
    "Front face: has display cutout + LED indicator holes + chamfer edge ✓"
  If you can't list at least ONE feature per face, ADD features.

A product with FEWER THAN 4 cutouts is almost certainly WRONG.
A box with no edge treatment is UNACCEPTABLE.
If the product would look like a plain box/cylinder — you are MISSING details.
If the BOTTOM has no feet/pads/label — you forgot about it.

═══════════════════════════════════════════════════════════════════════════════
MICRO-DETAIL PATTERNS — COPY THESE TO ADD PROFESSIONAL FINISH
═══════════════════════════════════════════════════════════════════════════════

These small-scale details are what separate a "3D box" from a "real product."
Add 2-4 of these micro-details to EVERY design.

── PATTERN: RUBBER FEET (bottom of any product that sits on a desk) ──
  foot_r = 4.0    # radius of each foot pad
  foot_h = 1.5    # height of foot recess
  foot_inset = 8.0  # inset from edges
  for (fx, fy) in [(-body_length/2 + foot_inset, -body_width/2 + foot_inset),
                    ( body_length/2 - foot_inset, -body_width/2 + foot_inset),
                    (-body_length/2 + foot_inset,  body_width/2 - foot_inset),
                    ( body_length/2 - foot_inset,  body_width/2 - foot_inset)]:
      foot_recess = cq.Workplane("XY").cylinder(foot_h + 1, foot_r)
      foot_recess = foot_recess.translate((fx, fy, 0))
      body = body.cut(foot_recess)

── PATTERN: LABEL / SERIAL NUMBER RECESS (shallow rectangle on bottom) ──
  label_w = body_length * 0.4
  label_h = body_width * 0.25
  label_depth = 0.3
  label_recess = cq.Workplane("XY").box(label_w, label_h, label_depth + 1)
  label_recess = label_recess.translate((0, 0, 0))  # sits on bottom face
  body = body.cut(label_recess)

── PATTERN: VENTILATION GRILLE (array of slots on a face) ──
  vent_count = 8
  vent_w = 1.5
  vent_h = body_height * 0.4
  vent_spacing = 3.5
  vent_start_x = -((vent_count - 1) * vent_spacing) / 2
  for i in range(vent_count):
      vent = cq.Workplane("XY").box(vent_w, wall * 3, vent_h)
      vent = vent.translate((vent_start_x + i * vent_spacing, -body_width / 2, body_height * 0.5))
      body = body.cut(vent)

── PATTERN: PANEL LINE / PARTING LINE (thin groove across a face) ──
  # Horizontal parting line around the body at mid-height
  panel_line_depth = 0.4
  panel_line_w = 0.6
  panel_cutter = cq.Workplane("XY").box(body_length + 2, body_width + 2, panel_line_w)
  panel_cutter = panel_cutter.translate((0, 0, body_height * 0.55))
  body = body.cut(panel_cutter)

── PATTERN: GRIP TEXTURE (parallel grooves on side faces) ──
  grip_count = 6
  grip_w = 0.8
  grip_depth = 0.5
  grip_spacing = 2.5
  grip_start = -((grip_count - 1) * grip_spacing) / 2
  for i in range(grip_count):
      groove = cq.Workplane("XY").box(wall * 3, grip_w, grip_depth + 1)
      groove = groove.translate((-body_length / 2, grip_start + i * grip_spacing, body_height * 0.5))
      body = body.cut(groove)

── PATTERN: INDICATOR LED HOLES (small circles on front face) ──
  led_r = 1.0
  led_positions = [(-body_length * 0.3, body_height * 0.8),
                   (-body_length * 0.25, body_height * 0.8)]
  for (lx, lz) in led_positions:
      led_hole = cq.Workplane("XY").cylinder(wall * 3, led_r)
      led_hole = led_hole.rotate((0,0,0), (1,0,0), 90)
      led_hole = led_hole.translate((lx, -body_width / 2, lz))
      body = body.cut(led_hole)

── PATTERN: SCREW HEAD RECESS (countersink on mounting face) ──
  screw_head_r = 3.5
  screw_shaft_r = 1.5
  screw_head_depth = 1.2
  # Counterbore: wider shallow + narrow through
  screw_recess = cq.Workplane("XY").cylinder(screw_head_depth + 1, screw_head_r)
  screw_through = cq.Workplane("XY").cylinder(wall * 3, screw_shaft_r)
  screw_cut = screw_recess.union(screw_through)
  screw_cut = screw_cut.translate((body_length * 0.35, body_width * 0.35, 0))
  body = body.cut(screw_cut)

── PATTERN: LOGO / BRAND RECESS (debossed rectangle on front) ──
  logo_w = body_length * 0.25
  logo_h = 8.0
  logo_depth = 0.5
  logo_recess = cq.Workplane("XY").box(logo_w, logo_depth + 1, logo_h)
  logo_recess = logo_recess.translate((0, -body_width / 2, body_height * 0.75))
  body = body.cut(logo_recess)
  # Or use text directly:
  # body = body.faces("<Y").workplane().text("BRAND", fontsize=8, distance=-0.5)

── PATTERN: INTERNAL RIBS (structural stiffeners inside a shell) ──
  rib_t = 1.5
  rib_h = body_height * 0.6
  # Cross rib along X axis
  rib_x = cq.Workplane("XY").box(body_length - 2 * wall, rib_t, rib_h)
  rib_x = rib_x.translate((0, 0, wall + rib_h / 2))
  body = body.union(rib_x)
  # Cross rib along Y axis
  rib_y = cq.Workplane("XY").box(rib_t, body_width - 2 * wall, rib_h)
  rib_y = rib_y.translate((0, 0, wall + rib_h / 2))
  body = body.union(rib_y)

── PATTERN: DRAINAGE / WEEP HOLES (small holes in bottom corners) ──
  drain_r = 1.5
  drain_positions = [(-body_length * 0.35, -body_width * 0.35),
                     ( body_length * 0.35, -body_width * 0.35)]
  for (dx, dy) in drain_positions:
      drain = cq.Workplane("XY").cylinder(wall * 3, drain_r)
      drain = drain.translate((dx, dy, 0))
      body = body.cut(drain)

── PATTERN: LIP / RIM (raised edge around opening for lid seating) ──
  lip_h = 2.0
  lip_t = 1.0
  lip_outer = cq.Workplane("XY").transformed(offset=(0, 0, body_height))\\
      .rect(body_length - 2 * wall + lip_t, body_width - 2 * wall + lip_t).extrude(lip_h)
  lip_inner = cq.Workplane("XY").transformed(offset=(0, 0, body_height))\\
      .rect(body_length - 2 * wall - lip_t, body_width - 2 * wall - lip_t).extrude(lip_h + 1)
  lip = lip_outer.cut(lip_inner)
  body = body.union(lip)

── PATTERN: CHAMFERED TRANSITIONS (where two sections meet) ──
  # Apply small chamfer at the base of a raised section
  # After unioning a feature, select the transition edges:
  body = body.edges(">Z and |X").chamfer(0.5)

── PATTERN: ANTI-SLIP TEXTURE (cross-hatch grooves on grip surface) ──
  texture_area_w = body_width * 0.5
  texture_area_h = body_height * 0.5
  groove_count = 5
  groove_w = 0.5
  groove_depth = 0.3
  groove_spacing = texture_area_h / (groove_count + 1)
  for i in range(groove_count):
      gz = body_height * 0.25 + (i + 1) * groove_spacing
      # Horizontal groove on side
      g = cq.Workplane("XY").box(wall * 3, texture_area_w, groove_w)
      g = g.translate((-body_length / 2, 0, gz))
      body = body.cut(g)

WHEN TO ADD WHICH MICRO-DETAILS:
  • Electronics/devices → rubber feet, vents, LED holes, label recess, panel lines
  • Containers/storage → drainage holes, lip/rim, anti-slip feet, label recess
  • Cases/enclosures → screw recesses, grip texture, panel lines, logo recess
  • Furniture/stands → rubber feet, cable channels, anti-slip, edge chamfers
  • Buildings → window sills, cornices, panel lines (floor dividers), drain holes
  • Tools/hardware → grip texture (knurling), anti-roll flats, hanging hole

═══════════════════════════════════════════════════════════════════════════════
CONSTRUCTION STRATEGIES — CHOOSE THE RIGHT APPROACH
═══════════════════════════════════════════════════════════════════════════════

STRATEGY 1: ADDITIVE (union bodies) — Best for multi-part assemblies
  base = cq.Workplane("XY").box(L, W, H)
  pillar = cq.Workplane("XY").transformed(offset=(x, y, z)).cylinder(h, r)
  result = base.union(pillar)

STRATEGY 2: SUBTRACTIVE (cut away) — Best for enclosures, cases, molds
  block = cq.Workplane("XY").box(L, W, H)
  cavity = cq.Workplane("XY").transformed(offset=(0, 0, wall)).box(L-2*w, W-2*w, H)
  result = block.cut(cavity)

STRATEGY 3: PROFILE + EXTRUDE — Best for custom cross-sections
  result = (cq.Workplane("XY")
    .moveTo(-W/2, 0).lineTo(-W/2, H).threePointArc((0, H+R), (W/2, H))
    .lineTo(W/2, 0).close().extrude(depth))

STRATEGY 4: PROFILE + REVOLVE — Best for bottles, vases, cups, knobs
  result = (cq.Workplane("XZ")
    .moveTo(0, 0).lineTo(R_base, 0)
    .spline([(R_base, 0), (R_body, H*0.4), (R_neck, H)])
    .lineTo(0, H).close()
    .revolve(360, (0,0,0), (0,1,0)))

STRATEGY 5: LOFT — Best for tapered/organic transitions
  base_wire = cq.Workplane("XY").rect(W1, H1)
  top_wire = cq.Workplane("XY").transformed(offset=(0,0,height)).rect(W2, H2)
  result = cq.Workplane("XY").rect(W1,H1).workplane(offset=height).rect(W2,H2).loft()

STRATEGY 6: SWEEP — Best for curved rails, handles, tubes
  path = cq.Workplane("XZ").spline([(0,0),(50,80),(100,80),(150,0)])
  result = cq.Workplane("XY").circle(R).sweep(path)

STRATEGY 7: MULTI-STEP BOOLEAN ASSEMBLY — Best for complex products
  # Build each feature as a separate body, then combine
  body = cq.Workplane("XY").box(...)
  feature1 = cq.Workplane("XY").transformed(...).cylinder(...)
  feature2 = cq.Workplane("XY").transformed(...).box(...)
  cutout1 = cq.Workplane("XY").transformed(...).rect(...).extrude(...)
  result = body.union(feature1).union(feature2).cut(cutout1)

STRATEGY 8: SCULPTED ORGANIC FORMS — Best for statues, figurines, abstract art
  # Build organic shapes by combining primitives with spline lofts and booleans
  # Torso: loft between elliptical cross-sections at varying heights
  torso = (cq.Workplane("XY")
    .ellipse(chest_w/2, chest_d/2)
    .workplane(offset=torso_h*0.5).ellipse(waist_w/2, waist_d/2)
    .workplane(offset=torso_h*0.5).ellipse(hip_w/2, hip_d/2)
    .loft())
  # Limbs: sweep circles along spline paths
  arm_path = cq.Workplane("XZ").spline([(0,0),(10,40),(5,80)])
  arm = cq.Workplane("XY").circle(arm_r).sweep(arm_path)
  # Head: sphere + cut features
  head = cq.Workplane("XY").sphere(head_r)
  # Combine all parts
  result = torso.union(head.translate((0,0,neck_h))).union(arm)

STRATEGY 9: ARCHITECTURAL MASS MODEL — Best for buildings, towers, houses
  # Base footprint extrusion + stacked floors + roof
  # Main volume
  building = cq.Workplane("XY").rect(width, depth).extrude(height)
  # Floor divisions (horizontal groove cuts)
  for i in range(num_floors):
      floor_line = cq.Workplane("XY").transformed(offset=(0,0,i*floor_h))
          .rect(width+2, depth+2).extrude(line_t)
      building = building.cut(floor_line)  # or union for ledges
  # Window arrays
  win = cq.Workplane("XZ").transformed(offset=(0,-depth/2,floor_h*0.3))
      .rect(win_w, win_h).extrude(win_depth)
  for col in range(win_cols):
      for row in range(num_floors):
          building = building.cut(win.translate((col*spacing, 0, row*floor_h)))
  # Roof: loft or chamfered top
  roof = cq.Workplane("XY").transformed(offset=(0,0,height))
      .rect(width+overhang, depth+overhang).workplane(offset=roof_h)
      .rect(1, depth+overhang).loft()
  result = building.union(roof)

STRATEGY 10: COLUMNAR / CLASSICAL ARCHITECTURE — Best for columns, temples, arches
  # Column: cylinder + base/capital moldings via revolution profiles
  shaft = cq.Workplane("XY").circle(col_r).extrude(col_h)
  # Doric capital: stacked cylinders + chamfers
  capital = (cq.Workplane("XY").transformed(offset=(0,0,col_h))
    .circle(col_r*1.3).extrude(cap_h)
    .edges(">Z").chamfer(cap_h*0.3))
  # Base: wider stepped cylinder
  base = cq.Workplane("XY").circle(col_r*1.5).extrude(base_h)
  column = base.union(shaft.translate((0,0,base_h))).union(capital.translate((0,0,base_h)))
  # Fluting: cut vertical grooves around circumference
  flute = cq.Workplane("XZ").transformed(offset=(col_r,0,base_h))
      .rect(flute_w, col_h).extrude(flute_d)
  for i in range(num_flutes):
      column = column.cut(flute.rotate((0,0,0),(0,0,1), i*360/num_flutes))
  result = column

STRATEGY 11: TERRAIN / RELIEF SCULPTURE — Best for plaques, bas-reliefs, signs
  # Flat base plate + raised/cut features on surface
  base = cq.Workplane("XY").rect(plaque_w, plaque_h).extrude(base_t)
  # Raised border frame
  frame = (cq.Workplane("XY").rect(plaque_w, plaque_h).extrude(base_t + frame_h)
    .cut(cq.Workplane("XY").rect(plaque_w-2*frame_w, plaque_h-2*frame_w).extrude(base_t+frame_h+1)))
  body = base.union(frame)
  # Raised text
  body = body.faces(">Z").workplane().text("HELLO", fontsize=20, distance=1.5)
  # Raised geometric features / relief patterns
  result = body

MANDATORY STRATEGY SELECTION — MATCH STRATEGY TO PRODUCT TYPE:
  ┌────────────────────────────────────────────────────────────────────────┐
  │ Product Category              │ Required Strategy                      │
  ├────────────────────────────────────────────────────────────────────────┤
  │ Mug, cup, bottle, vase,       │ Strategy 4 (revolve + .spline())       │
  │ tumbler, glass, bowl           │ NEVER box+cut for round drinkware     │
  │                                │                                        │
  │ Phone case, tablet case,       │ Strategy 2 (box+shell) with R≥6mm     │
  │ enclosure, electronics box     │ corners + generous body fillets        │
  │                                │                                        │
  │ Game controller, mouse,        │ Strategy 8 (multi-loft ergonomic body)│
  │ remote control, headphones     │ Loft between elliptical sections      │
  │                                │                                        │
  │ Wrench, pliers, tool, knife,   │ Strategy 3 (profile+extrude) with     │
  │ spatula, scissors              │ .spline() curves, NOT lineTo chains   │
  │                                │                                        │
  │ Furniture (desk, table, chair) │ Strategy 1 (additive) with chamfers   │
  │ shelf, rack, stand             │ and filleted members                   │
  │                                │                                        │
  │ Drone, quadcopter (COMPLETE)    │ Strategy 1 (additive) — frame +       │
  │ hexacopter, octocopter,        │ motors + propellers + canopy + legs    │
  │ tricopter, FPV/racing          │ Arm count: tri=3, quad=4, hex=6, oct=8│
  │                                │                                        │
  │ Camera/photography drone        │ Strategy 1+8 — lofted fuselage body + │
  │ (DJI-style, gimbal)            │ arms + motors + props + gimbal/camera  │
  │                                │                                        │
  │ Fixed-wing VTOL / survey drone │ Strategy 3+1 — lofted fuselage + wings│
  │                                │ + tail + VTOL motors + pusher motor    │
  │                                │                                        │
  │ Mini/micro drone (Tiny Whoop)  │ Strategy 1 — integrated duct frame +  │
  │                                │ motors inside ducts + tiny canopy      │
  │                                │                                        │
  │ Delivery/cargo drone           │ Strategy 1 — arms + motors + props +  │
  │                                │ enclosed fuselage + CARGO BAY + tall   │
  │                                │ landing gear for clearance             │
  │                                │                                        │
  │ Underwater ROV drone           │ Strategy 1 — open cage frame +        │
  │                                │ enclosed thrusters + camera dome +     │
  │                                │ buoyancy foam + tether port            │
  │                                │                                        │
  │ Agricultural spray drone       │ Strategy 1 — heavy arms + motors +    │
  │                                │ spray tank + spray boom with nozzles + │
  │                                │ extra-wide tall landing gear           │
  │                                │                                        │
  │ Lamp, chandelier, trophy,      │ Strategy 4 or 5 (revolve/loft)        │
  │ decorative object              │ for organic/artistic form              │
  │                                │                                        │
  │ Building, tower, house         │ Strategy 9 (architectural)             │
  │ Temple, column                 │ Strategy 10 (columnar)                 │
  │ Plaque, sign, badge            │ Strategy 11 (relief)                   │
  │                                │                                        │
  │ Storage box, crate, toolbox    │ Strategy 7 (box+boolean) — legitimate │
  │ Simple container, tray         │ for genuinely rectangular products     │
  │                                │                                        │
  │ Laptop, tablet, smartphone     │ Strategy 2 (box+shell) with fillets + │
  │                                │ feature cutouts on all faces           │
  │                                │                                        │
  │ Headphones, earbuds            │ Strategy 8 (multi-loft) for earcups + │
  │                                │ Strategy 6 (sweep) for headband arc   │
  │                                │                                        │
  │ Smartwatch, wearable           │ Strategy 4 (revolve) for round watch + │
  │                                │ Strategy 1 (additive) for lugs/crown  │
  │                                │                                        │
  │ Keyboard, numpad               │ Strategy 7 (box+boolean) + arrays of  │
  │                                │ raised keycaps on top surface          │
  │                                │                                        │
  │ Speaker, soundbar, subwoofer   │ Strategy 2 (box+shell) or Strategy 4  │
  │                                │ (revolve) for round + driver grilles  │
  │                                │                                        │
  │ Ring, bracelet, jewelry        │ Strategy 4 (revolve) — circular bands │
  │ pendant, earring               │ with profile details                   │
  │                                │                                        │
  │ Guitar, violin, cello          │ Strategy 8 (loft between bouts) +     │
  │ ukulele                        │ Strategy 3 (extrude) for neck         │
  │                                │                                        │
  │ Drum, trumpet, saxophone       │ Strategy 4 (revolve) for cylindrical  │
  │ flute                          │ bodies + feature cutouts for keys     │
  │                                │                                        │
  │ Skateboard, surfboard          │ Strategy 3 (profile+extrude) with     │
  │ snowboard                      │ spline curves for deck shape          │
  │                                │                                        │
  │ Helmet, protective gear        │ Strategy 4 (revolve) or 8 (loft) +   │
  │                                │ shell for hollow + vent cutouts       │
  │                                │                                        │
  │ Gear, sprocket, pulley         │ Strategy 3 (profile+extrude) with     │
  │                                │ circular array cuts for teeth         │
  │                                │                                        │
  │ Pot, pan, kettle, cookware     │ Strategy 4 (revolve + spline) + shell │
  │                                │ for hollow body + swept handle        │
  │                                │                                        │
  │ Pipe, fitting, valve, faucet   │ Strategy 4 (revolve) for cylindrical  │
  │                                │ bodies + boolean for through-bore     │
  │                                │                                        │
  │ Clock, picture frame, mirror   │ Strategy 3 (profile+extrude) or 4    │
  │                                │ (revolve for round clocks) + cutouts  │
  │                                │                                        │
  │ Dumbbell, kettlebell, weight   │ Strategy 4 (revolve) for round heads  │
  │                                │ Strategy 1 (additive) for handle      │
  │                                │                                        │
  │ Microscope, beaker, flask      │ Strategy 4 (revolve) for glassware +  │
  │ test tube rack                 │ Strategy 1 (additive) for assemblies  │
  │                                │                                        │
  │ Hinge, bolt, nut, fastener     │ Strategy 4 (revolve) for threaded     │
  │                                │ parts + Strategy 3 for flat hardware  │
  └────────────────────────────────────────────────────────────────────────┘

  ⚠️ Strategy 7 (box+boolean) is ONLY for genuinely rectangular products.
  NEVER use Strategy 7 as a lazy default for curved/organic products.

  ⚠️⚠️⚠️ DRONE ASSEMBLY RULE (NON-NEGOTIABLE) — APPLIES TO ALL DRONE TYPES:
  Match the drone type to the user's request:

  QUADCOPTER / RACING FPV (default): frame + 4 arms + 4 MOTORS + 4 PROPELLERS + canopy + landing gear
  HEXACOPTER: frame + 6 arms (60° apart) + 6 MOTORS + 6 PROPELLERS + canopy + tall landing gear + payload rails
  OCTOCOPTER: frame + 8 arms (45° apart) + 8 MOTORS + 8 PROPELLERS + canopy + retractable tall gear
  TRICOPTER: Y-frame + 3 arms + 3 MOTORS + 3 PROPELLERS + TAIL SERVO tilt mechanism + canopy + gear
  CAMERA/PHOTO DRONE: lofted fuselage body + 4 arms + 4 motors + 4 props + 3-AXIS GIMBAL+CAMERA + retractable gear
  FIXED-WING VTOL: streamlined fuselage + WINGS + TAIL + 4 VTOL motors on booms + 1 PUSHER motor + all props + skids
  MINI DRONE: integrated ducted frame (4 circular guards) + 4 tiny motors inside ducts + 4 props + tiny canopy (no legs)
  DELIVERY DRONE: enclosed fuselage + 6-8 arms + motors + props + CARGO BAY with hook + very tall gear (180mm+)
  UNDERWATER ROV: open cage frame + 4-6 ENCLOSED THRUSTERS + camera dome + LED lights + buoyancy foam + tether port
  AGRICULTURAL DRONE: heavy frame + 6-8 arms + motors + props + SPRAY TANK + SPRAY BOOM with nozzles + extra-wide gear

  KEY RULE: EVERY air drone MUST have visible MOTORS (cylinders on arm tips) and PROPELLERS (thin discs on motors).
  A drone with ONLY a frame is INCOMPLETE and will be REJECTED.

═══════════════════════════════════════════════════════════════════════════════
REALISTIC BODY FORM — THE DIFFERENCE BETWEEN "TOY" AND "REAL PRODUCT"
═══════════════════════════════════════════════════════════════════════════════

A "toy version" starts with .box() and cuts holes. A "real product" builds the body
shape FIRST with proper contours, THEN adds features on the shaped body.

RULE 1 — Use .spline() for ANY profile that should be curved:
  BAD:  .lineTo(R_base, 0).lineTo(R_top, H)           ← straight diagonal = faceted toy look
  GOOD: .spline([(R_base, 2), (R_mid, H*0.5), (R_top, H-2)])  ← smooth organic curve
  Use .spline() for: handle tapers, body contours, bottle profiles, tool shapes

RULE 2 — Use multi-section .loft() for body transitions:
  BAD:  .box(W1, D, H1).union(.box(W2, D, H2))        ← stacked boxes
  GOOD: .rect(W1,D).workplane(offset=H).rect(W2,D2).loft()  ← smooth blend

RULE 3 — Build curvature INTO the profile geometry:
  BAD:  .box(L,W,H) then try: .fillet(5) except: pass  ← afterthought, often fails
  GOOD: 2D profile with .threePointArc() for corners, then .extrude()  ← curvature is structural

RULE 4 — MANDATORY .revolve() + .spline() for axially symmetric products:
  Mugs, bottles, vases, bowls, cups: profile = moveTo → lineTo base → .spline([control points]) → close → revolve(360)
  The spline control points create the organic taper — NOT lineTo chains

RULE 5 — Use .sweep() with CURVED path for handles, rails, pipes:
  BAD:  handle_path with lineTo segments              ← angular robot handle
  GOOD: .threePointArc((mid_x, mid_y), (end_x, end_y))  ← smooth C-curve handle

RULE 6 — Use .tangentArcPoint() for smooth lip/rim transitions:
  .spline([..., (R_top, H-lip_r*2)])
  .tangentArcPoint((R_top-lip_r, H))                  ← smooth rolled lip, not sharp edge

EXAMPLES OF REAL vs TOY BODY CONSTRUCTION:

  Phone case body (REAL):
    body = cq.Workplane("XY").box(W, D, H, centered=(True,True,False))
    try: body = body.edges("|Z").fillet(min(corner_r, W*0.10))            # Round corners
    try: body = body.edges("|Y").fillet(min(edge_r, D*0.3))              # Round vertical edges
    try: body = body.edges("#Z and >Z").fillet(min(top_r, D*0.15))       # Soften top edges
    body = body.faces("<Y").shell(-wall)
    → Result: organically rounded shell, not a rectangular box with sharp edges

  Phone case cutouts (REAL — NEVER use .box() for cutouts!):
    ⚠️ EVERY cutout on a phone case MUST use the correct real-world shape:

    # USB-C port (bottom, Z=0) — PILL/STADIUM shape, NEVER rectangular:
    usb = cq.Workplane("XZ").slot2D(usb_w, usb_h).extrude(wall*3)
    usb = usb.translate((0, 0, -wall))
    body = body.cut(usb)

    # Speaker grille (bottom, Z=0) — ROW OF CIRCLES, NEVER rectangular slots:
    for i in range(speaker_holes):
        dot = cq.Workplane("XY").cylinder(wall*3, speaker_r)
        dot = dot.translate((speaker_start_x + i * speaker_spacing, 0, 0))
        body = body.cut(dot)

    # Microphone hole (bottom or top) — TINY CIRCLE:
    mic = cq.Workplane("XY").cylinder(wall*3, mic_r)
    mic = mic.translate((mic_x, 0, mic_z))
    body = body.cut(mic)

    # Camera island (back face, +Y) — ROUNDED RECTANGLE with fillet:
    cam = cq.Workplane("XZ").rect(cam_w, cam_h).extrude(wall*3)
    cam = cam.translate((cam_x, back_y - wall, cam_z))
    try: cam = cam.edges("|Y").fillet(min(cam_corner_r, min(cam_w, cam_h)*0.3))
    except: pass
    body = body.cut(cam)
    # Add camera lip (protective raised ring around camera):
    cam_lip = cq.Workplane("XZ").rect(cam_w+lip*2, cam_h+lip*2).extrude(lip)
    cam_lip = cam_lip.translate((cam_x, back_y, cam_z))
    try: cam_lip = cam_lip.edges("|Y").fillet(min(cam_corner_r+lip, (cam_w+lip*2)*0.3))
    except: pass
    body = body.union(cam_lip)

    # Individual camera lenses (inside island) — CIRCLES:
    for lx, lz in lens_positions:
        lens = cq.Workplane("XY").cylinder(wall*3, lens_r)
        lens = lens.translate((cam_x + lx, back_y - wall, cam_z + lz))
        body = body.cut(lens)

    # Volume buttons (left side, -X) — PILL/STADIUM slots:
    vol_up = cq.Workplane("YZ").slot2D(vol_btn_len, vol_btn_depth).extrude(wall*3)
    vol_up = vol_up.translate((-W/2 - wall, 0, vol_up_z))
    body = body.cut(vol_up)
    vol_down = cq.Workplane("YZ").slot2D(vol_btn_len, vol_btn_depth).extrude(wall*3)
    vol_down = vol_down.translate((-W/2 - wall, 0, vol_down_z))
    body = body.cut(vol_down)

    # Power button (right side, +X) — PILL/STADIUM slot:
    pwr = cq.Workplane("YZ").slot2D(pwr_btn_len, pwr_btn_depth).extrude(wall*3)
    pwr = pwr.translate((W/2 - wall, 0, pwr_z))
    body = body.cut(pwr)

    # Action/mute button (left side, -X) — SMALL CIRCLE:
    mute = cq.Workplane("XY").cylinder(wall*3, mute_r)
    mute = mute.rotate((0,0,0), (0,0,1), 90)
    mute = mute.translate((-W/2 - wall, 0, mute_z))
    body = body.cut(mute)

    # SIM tray slot (left or right side) — NARROW PILL:
    sim = cq.Workplane("YZ").slot2D(sim_len, sim_w).extrude(wall*3)
    sim = sim.translate((W/2 - wall, 0, sim_z))
    body = body.cut(sim)

    # Screen lip (raised edge around front opening):
    → The .shell() already creates the screen opening. The lip height comes from
      the wall extending ~1mm above the phone surface on the front edge.

    ⚠️ SHAPE RULES FOR PHONE CASE CUTOUTS:
    ┌────────────────────────┬────────────────────────────────────────────┐
    │ Cutout Feature         │ REQUIRED Shape (NEVER .box())              │
    ├────────────────────────┼────────────────────────────────────────────┤
    │ USB-C / Lightning port │ .slot2D(w, h) — pill/stadium shape        │
    │ Volume button(s)       │ .slot2D(len, depth) — rounded slot        │
    │ Power / side button    │ .slot2D(len, depth) — rounded slot        │
    │ Action / mute switch   │ .cylinder(h, r) — round hole              │
    │ Camera island          │ .rect(w,h) + .fillet(r) — rounded rect    │
    │ Camera lens holes      │ .cylinder(h, r) — perfect circles         │
    │ Speaker grille         │ Array of .cylinder() — row of circles     │
    │ Microphone hole        │ .cylinder(h, r) — tiny circle             │
    │ SIM tray slot          │ .slot2D(len, w) — narrow pill shape       │
    │ Flash / LED            │ .cylinder(h, r) — small circle            │
    │ Screen opening         │ .shell() on front face (not a cutter)     │
    └────────────────────────┴────────────────────────────────────────────┘
    ZERO .box() cutters on a phone case. If you use .box() for a port or
    button, the case will look like a BRICK with rectangular holes punched in.

  Mug body (REAL — revolve with spline):
    profile = (cq.Workplane("XZ").moveTo(0,0)
      .lineTo(base_r, 0)                                                  # Flat base
      .spline([(base_r+1, 5), (mid_r, H*0.5), (top_r, H-lip*2)])        # Organic taper
      .tangentArcPoint((top_r-lip, H))                                    # Rolled lip
      .lineTo(0, H).close()
      .revolve(360, (0,0,0), (0,1,0)))

  Wrench body (REAL — profile with curves):
    profile = (cq.Workplane("XY")
      .moveTo(-L/2, -handle_w/2)
      .spline([(-L/2+handle_len, handle_w_start/2), (-jaw_x, jaw_w/2)])  # Smooth taper
      .threePointArc((-jaw_x+jaw_r, jaw_w/2+jaw_r), (jaw_tip, 0))       # Jaw curve
      .close()
      .extrude(thickness))

  Controller body (REAL — multi-section loft):
    body = (cq.Workplane("XY")
      .ellipse(W*0.4, D*0.35)                                            # Bottom: narrow
      .workplane(offset=H*0.3).ellipse(W*0.5, D*0.45)                    # Middle: wider
      .workplane(offset=H*0.4).ellipse(W*0.45, D*0.4)                    # Upper: slightly narrow
      .workplane(offset=H*0.3).ellipse(W*0.3, D*0.25)                    # Top: tapered
      .loft())

  Drone (REAL — COMPLETE ASSEMBLY, not just a frame!):
    ⚠️ A drone is NOT just a flat frame plate with holes. A COMPLETE drone includes:
       Frame + Motors + Propellers + Canopy + Landing Gear + Camera Mount.
       Without motors and propellers it looks like a bare PCB, not a drone.

    # 1. FRAME: Center body plates + arms
    bottom_plate = cq.Workplane("XY").circle(center_r).extrude(plate_t)
    top_plate = cq.Workplane("XY").transformed(offset=(0,0,plate_t+spacing))
    top_plate = top_plate.circle(center_r).extrude(plate_t)
    body = bottom_plate.union(top_plate)
    # Spacer posts between plates
    for sx, sy in [(20,0),(-20,0),(0,20),(0,-20)]:
        post = cq.Workplane("XY").transformed(offset=(sx,sy,plate_t))
        body = body.union(post.circle(3).extrude(spacing))
    # Arms (X-config at 45/135/225/315 degrees)
    for angle in [45, 135, 225, 315]:
        arm = cq.Workplane("XY").box(arm_len, arm_w, arm_t)
        arm = arm.translate((arm_len/2, 0, center_z))
        arm = arm.rotate((0,0,0), (0,0,1), angle)
        body = body.union(arm)

    # 2. MOTORS — cylindrical cans ON TOP of each arm tip (CRITICAL!)
    for angle in [45, 135, 225, 315]:
        rad = math.radians(angle)
        mx = tip_r * math.cos(rad)
        my = tip_r * math.sin(rad)
        motor = cq.Workplane("XY").cylinder(motor_h, motor_r)
        motor = motor.translate((mx, my, arm_top_z + motor_h/2))
        body = body.union(motor)

    # 3. PROPELLERS — flat discs on top of each motor (CRITICAL!)
    for angle in [45, 135, 225, 315]:
        rad = math.radians(angle)
        px = tip_r * math.cos(rad)
        py = tip_r * math.sin(rad)
        prop = cq.Workplane("XY").cylinder(prop_thickness, prop_r)
        prop = prop.translate((px, py, motor_top_z + prop_thickness/2))
        body = body.union(prop)

    # 4. CANOPY — dome/cover over center electronics
    canopy = cq.Workplane("XY").sphere(canopy_r)
    canopy = canopy.cut(cq.Workplane("XY").box(canopy_r*3, canopy_r*3, canopy_r*3)
                        .translate((0, 0, -canopy_r*1.5)))  # keep top half
    canopy = canopy.translate((0, 0, top_plate_z))
    body = body.union(canopy)

    # 5. LANDING GEAR — 4 legs or 2 skid rails under body
    for lx, ly in [(20,20),(-20,20),(20,-20),(-20,-20)]:
        leg = cq.Workplane("XY").cylinder(leg_h, leg_r)
        leg = leg.translate((lx, ly, -leg_h/2))
        body = body.union(leg)

    # 6. Camera mount under front
    cam_bracket = cq.Workplane("XY").box(cam_w, cam_d, cam_h)
    cam_bracket = cam_bracket.translate((0, center_r, -cam_h/2))
    body = body.union(cam_bracket)

    result = body
    → Result: A complete, recognizable drone — not a flat plate with holes.

    ⚠️ MANDATORY DRONE COMPONENTS (all required for a complete drone):
    ┌────────────────────────┬──────────────────────────────────────────────┐
    │ Component              │ How to Model                                 │
    ├────────────────────────┼──────────────────────────────────────────────┤
    │ Frame (center + arms)  │ .circle().extrude() plates + .box() arms    │
    │ Motors                 │ .cylinder(motor_h, motor_r) on arm tips     │
    │ Propellers             │ .cylinder(2, prop_r) thin discs on motors   │
    │ Canopy                 │ .sphere() half or .loft() dome over center  │
    │ Landing gear           │ .cylinder() legs or .box() skid rails       │
    │ Camera mount           │ .box() bracket under front                  │
    └────────────────────────┴──────────────────────────────────────────────┘
    Build the frame FIRST, then union motors, propellers, canopy, and landing gear.

    DRONE TYPE CONSTRUCTION HINTS:
    • HEXACOPTER: Use loop `for angle in range(0, 360, 60):` for 6 arms/motors/props at 60° intervals.
    • OCTOCOPTER: Use `for angle in range(0, 360, 45):` for 8 arms/motors/props at 45° intervals.
    • TRICOPTER: Y-frame — 2 front arms at ±120° and 1 rear. Add servo box on rear arm before motor.
    • CAMERA DRONE: Use .loft() for fuselage body. Add gimbal bracket + camera sphere under front body.
    • FIXED-WING VTOL: .loft() fuselage from nose to tail + wing .extrude() + 4 boom motors + 1 pusher.
    • MINI DRONE: Single .box() body with 4 .circle().extrude() duct rings — motors INSIDE ducts.
    • DELIVERY: enclosed .box()/.loft() fuselage + cargo bay box under body + hook cylinder.
    • UNDERWATER ROV: .box() cage rails + .cylinder() thruster tubes + .sphere() camera dome + .box() foam.
    • AGRI SPRAY: .box() tank on top + .box() spray boom bar under body + .cylinder() nozzle tips.

═══════════════════════════════════════════════════════════════════════════════
CADQUERY API — COMPLETE REFERENCE
═══════════════════════════════════════════════════════════════════════════════

**IMPORTS (always include both):**
  import cadquery as cq
  import math
  # For engineering parts (fasteners, bearings, etc.):
  import cq_warehouse.extensions  # REQUIRED for clearanceHole, tapHole, pressFitHole
  # Individual part classes are pre-imported in namespace (no import needed)
  # but you CAN import explicitly:
  # from cq_warehouse.fastener import SocketHeadCapScrew, HexNut, PlainWasher
  # from cq_warehouse.bearing import SingleRowDeepGrooveBallBearing
  # from cq_warehouse.sprocket import Sprocket
  # from cq_warehouse.chain import Chain
  # from cq_warehouse.thread import IsoThread

**PRIMITIVES:**
  .box(L, W, H)                            # Centered on ALL axes by default
  .box(L, W, H, centered=(True, True, False))  # Z starts at 0 (USE FOR MAIN BODY)
  .cylinder(height, radius)                 # Along Z-axis, centered
  .sphere(radius)                           # At origin
  .rect(W, H).extrude(D)                   # 2D → 3D extrusion (NO centered parameter!)
  .circle(R).extrude(H)                    # Circular extrusion (NO centered parameter!)
  .polygon(N, diameter).extrude(H)         # N-sided regular polygon
  .slot2D(length, diameter).extrude(H)     # Stadium/slot shape
  .ellipse(x_radius, y_radius).extrude(H) # Elliptical extrusion

⚠️ centered=(True,True,False) is ONLY for .box() — NEVER use it on .extrude(), .circle(), .rect() etc.

**2D SKETCH OPERATIONS (for complex cross-sections):**
  .moveTo(x, y)                            # Move pen without drawing
  .lineTo(x, y)                            # Straight line to absolute coords
  .line(dx, dy)                            # Straight line relative
  .hLine(d) / .vLine(d)                    # Horizontal / vertical line
  .hLineTo(x) / .vLineTo(y)               # H/V line to absolute coord
  .threePointArc((x1,y1), (x2,y2))        # Arc through midpoint & endpoint
  .tangentArcPoint((x, y))                 # Tangent-continuous arc
  .sagittaArc((x, y), sag)                # Arc defined by sagitta (bulge)
  .radiusArc((x, y), radius)              # Arc defined by radius (+ = CCW, - = CW)
  .spline([(x1,y1), (x2,y2), ...])        # Smooth B-spline
  .spline(pts, tangents=[v1, v2])          # Spline with endpoint tangents
  .close()                                 # Close path back to start ← REQUIRED before extrude!

**EXTRUSION & REVOLUTION:**
  .extrude(depth)                          # Extrude along normal
  .extrude(depth, both=True)               # Extrude symmetrically
  .revolve(angleDegrees)                   # Revolve around Z (default)
  .revolve(360, (0,0,0), (0,1,0))         # Revolve around Y-axis
  .twistExtrude(height, angleDegrees)      # Helical twist

**BOOLEAN OPERATIONS:**
  body.union(other)                        # Add shapes
  body.cut(other)                          # Subtract shapes
  body.intersect(other)                    # Keep intersection only

**FEATURES (applied to existing solid):**
  .fillet(radius)                          # Round selected edges
  .chamfer(distance)                       # Bevel selected edges
  .chamfer(d1, d2)                         # Asymmetric chamfer
  .shell(thickness)                        # Hollow out (positive = outward, negative = inward)
  .shell(-t)                               # Shell inward, remove face with largest area (top)
  .hole(diameter)                          # Through-hole at current WP center
  .hole(diameter, depth)                   # Blind hole
  .cboreHole(d, cbore_d, cbore_depth)      # Counterbore hole
  .cskHole(d, csk_d, csk_angle)           # Countersink hole

**SELECTORS (for targeting faces/edges):**
  Face: ">Z" "<Z" ">X" "<X" ">Y" "<Y"    # Max/min along axis
  Face: "|Z" "|X" "|Y"                    # Parallel to axis
  Face: "#Z" "#X" "#Y"                    # Perpendicular to axis
  Face: "%Plane" "%Cylinder"               # By surface type
  Edge: "|Z" "|X" "|Y"                    # Parallel to axis
  Edge: "#Z" "#X" "#Y"                    # Perpendicular to axis
  Edge: "%Circle" "%Line"                  # By edge type
  Compound: ">Z and >X"                   # Boolean AND
  Inverted: not "|Z"                       # Negate selector
  Indexed: .edges("|Z").item(0)            # Pick Nth edge by index

═══════════════════════════════════════════════════════════════════════════════
⚠️⚠️⚠️  MASTER SPATIAL ORIENTATION CONVENTION  ⚠️⚠️⚠️
═══════════════════════════════════════════════════════════════════════════════

╔══════════════════════════════════════════════════════════════════════════╗
║  THE GOLDEN RULE OF AXIS ASSIGNMENT:                                    ║
║                                                                          ║
║  Z = the dimension that goes UPWARD when the product sits naturally.     ║
║  Z is ALWAYS the TALLEST axis for upright products (phones, bottles,     ║
║  buildings, cases standing up) or the THICKNESS axis for flat products   ║
║  (tablets lying flat, PCBs, plates).                                     ║
║                                                                          ║
║  .box(X_dim, Y_dim, Z_dim, centered=(True, True, False))                ║
║                                                                          ║
║  STEP 1: Decide how the product SITS (upright or flat).                  ║
║  STEP 2: Assign the VERTICAL dimension to Z.                            ║
║  STEP 3: Assign the two HORIZONTAL dimensions to X and Y.               ║
║  STEP 4: Write an AXIS ASSIGNMENT comment BEFORE the .box() call.       ║
╚══════════════════════════════════════════════════════════════════════════╝

                    +Z  (UP / VERTICAL)
                     |
                     |
                     |_________ +X (LEFT-RIGHT / HORIZONTAL)
                    /
                   /
                 +Y  (FRONT-BACK / DEPTH)
            Z=0 is the GROUND PLANE (bottom of product)

  PHYSICAL DIRECTION    CadQuery AXIS     Face Selector    Coordinate at wall
  ─────────────────     ─────────────     ─────────────    ──────────────────
  TOP    (lid/cap)       +Z               ">Z"             z = body_height
  BOTTOM (feet/base)     -Z               "<Z"             z = 0
  RIGHT  (right side)    +X               ">X"             x = +body_x/2
  LEFT   (left side)     -X               "<X"             x = -body_x/2
  BACK   (rear/back)     +Y               ">Y"             y = +body_y/2
  FRONT  (user-facing)   -Y               "<Y"             y = -body_y/2

  ⚠️ Z IS NEVER NEGATIVE. Bottom = 0, Top = body_height. ALWAYS.
  ⚠️ X and Y use ±dimension/2 for walls. Center is at 0.

══════════════════════════════════════════════════════════════
MANDATORY AXIS ASSIGNMENT STEP (do this BEFORE writing .box())
══════════════════════════════════════════════════════════════

For EVERY product, write this comment block before the body .box() call:

  # ═══ AXIS ASSIGNMENT ═══
  # Product: [product name]
  # Natural position: [upright / flat / etc.]
  # X axis = [which physical dimension] = [value] mm   (left-right)
  # Y axis = [which physical dimension] = [value] mm   (front-back / depth)
  # Z axis = [which physical dimension] = [value] mm   (up-down / vertical)
  # ═══════════════════════

EXAMPLES of correct axis assignment:

  📱 iPhone 16 case (UPRIGHT — tallest dimension is vertical):
    # X axis = case width      = 73.6 mm   (left-right)
    # Y axis = case depth      = 10.5 mm   (front-back / thickness — screen on -Y)
    # Z axis = case tall height = 149.6 mm  (up-down / vertical — USB-C at Z=0)
    body = cq.Workplane("XY").box(73.6, 10.5, 149.6, centered=(True, True, False))

  🏠 House (UPRIGHT — wall height is vertical):
    # X axis = building width  = 12000 mm  (left-right)
    # Y axis = building depth  = 10000 mm  (front-back — front door on -Y)
    # Z axis = wall height     = 8000 mm   (up-down / vertical)
    body = cq.Workplane("XY").box(12000, 10000, 8000, centered=(True, True, False))

  💻 Laptop (FLAT on desk — thickness is vertical):
    # X axis = laptop width    = 320 mm    (left-right)
    # Y axis = laptop depth    = 220 mm    (front-back — touchpad edge on -Y)
    # Z axis = laptop thickness = 18 mm    (up-down / vertical)
    body = cq.Workplane("XY").box(320, 220, 18, centered=(True, True, False))

  ☕ Coffee mug (UPRIGHT — height is vertical):
    # X axis = mug diameter    = 85 mm     (left-right)
    # Y axis = mug diameter    = 85 mm     (front-back)
    # Z axis = mug height      = 95 mm     (up-down / vertical)
    → use .cylinder(95, 42.5) or revolved profile

══════════════════════════════════════════════════════════════
PRODUCT-TYPE ORIENTATION RULES
══════════════════════════════════════════════════════════════

  📱 PHONES & PHONE CASES (UPRIGHT — tallest dimension = Z):
      .box(body_width, body_depth, body_tall, centered=(True, True, False))
      body_width = 73.6mm (X)   body_depth = 10.5mm (Y)   body_tall = 149.6mm (Z)

      Screen/front:  -Y face ("<Y")    y = -body_depth/2   (the THIN face)
      Back:          +Y face (">Y")    y = +body_depth/2   (the THIN face)
      Top:           +Z face (">Z")    z = body_tall        (where mic is)
      Bottom:        -Z face ("<Z")    z = 0                (where USB-C is!)
      Left side:     -X face ("<X")    x = -body_width/2   (volume buttons)
      Right side:    +X face (">X")    x = +body_width/2   (power button)

      → USB-C:    translate((0, 0, 0))                              bottom center
      → Camera:   translate((cam_x, +body_depth/2, body_tall*0.85)) back face, upper
      → Volume:   translate((-body_width/2, 0, body_tall*0.65))     left side
      → Power:    translate((+body_width/2, 0, body_tall*0.60))     right side
      → Speaker:  translate((±offset, 0, 0))                        bottom

  🏠 BUILDINGS & ARCHITECTURE (UPRIGHT — wall height = Z):
      .box(building_width, building_depth, wall_height, centered=(True, True, False))

      Front:         -Y face ("<Y")    y = -building_depth/2  (main entrance)
      Back:          +Y face (">Y")    y = +building_depth/2
      Left:          -X face ("<X")    x = -building_width/2
      Right:         +X face (">X")    x = +building_width/2
      Roof/top:      +Z face (">Z")    z = wall_height
      Ground:        -Z face ("<Z")    z = 0

      → Door:    translate((0, -building_depth/2, door_h/2))
      → Windows: translate((win_x, -building_depth/2, floor_z))

  🎮 CONTROLLERS (face-buttons UP — body height = Z):
      .box(body_width, body_depth, body_height, centered=(True, True, False))

      Face (buttons): +Z face (">Z")  z = body_height
      Bottom:         -Z face ("<Z")   z = 0
      Front:          -Y face ("<Y")   y = -body_depth/2
      Back:           +Y face (">Y")   y = +body_depth/2
      Left grip:      -X face ("<X")   x = -body_width/2
      Right grip:     +X face (">X")   x = +body_width/2

  ☕ DRINKWARE (UPRIGHT — drinking height = Z):
      Opening/top:    +Z face (">Z")   z = mug_height
      Base/bottom:    -Z face ("<Z")   z = 0
      Handle side:    +X or -X face    x = ±radius

  💻 ELECTRONICS (FLAT on desk — case thickness = Z):
      .box(case_width, case_depth, case_height, centered=(True, True, False))

      Top/lid:        +Z face (">Z")   z = case_height
      Bottom/feet:    -Z face ("<Z")   z = 0
      Front (ports):  -Y face ("<Y")   y = -case_depth/2
      Back (cables):  +Y face (">Y")   y = +case_depth/2

  📦 CONTAINERS / BOXES (UPRIGHT — box height = Z):
      .box(box_width, box_depth, box_height, centered=(True, True, False))

      Opening/lid:    +Z face (">Z")   z = box_height
      Base/bottom:    -Z face ("<Z")   z = 0
      Front:          -Y face ("<Y")   y = -box_depth/2
      Back:           +Y face (">Y")   y = +box_depth/2

⚠️ KEY INSIGHT: For phones/cases the TALLEST dimension (149.6mm) goes in Z, NOT in X.
   The phone WIDTH (73.6mm) goes in X, and the THIN depth (10.5mm) goes in Y.
   This ensures z=0 is the bottom edge (USB-C) and z=body_tall is the top edge.

══════════════════════════════════════════════════════════════
FEATURE PLACEMENT RECIPE (use for EVERY feature)
══════════════════════════════════════════════════════════════

  1. Identify which PHYSICAL face the feature belongs on (e.g., "USB-C goes on bottom")
  2. Look up the CadQuery axis from the table above (e.g., bottom = <Z)
  3. Set the wall-coordinate (e.g., bottom = z=0, top = z=body_tall, left = x=left_x)
  4. Position along the other two axes for centering (e.g., x=0, y=0 for centered)
  5. Orient the cutter to penetrate THROUGH the wall:
     • Feature on X wall: cutter is thin in X, extends in Y and Z → box(wall*3, cut_w, cut_h)
     • Feature on Y wall: cutter is thin in Y, extends in X and Z → box(cut_w, wall*3, cut_h)
     • Feature on Z wall: cutter is thin in Z, extends in X and Y → box(cut_w, cut_h, wall*3)
  6. Translate the cutter to the wall position:
     cutter = cutter.translate((x_pos, y_pos, z_pos))
  7. Cut: body = body.cut(cutter)

CUTTER ORIENTATION EXAMPLES:
  # USB-C port on BOTTOM face (<Z), Z=0 — ROUNDED (slot2D for realistic shape):
  usb_cutter = cq.Workplane("XY").slot2D(usb_w, usb_h).extrude(wall*3)
  usb_cutter = usb_cutter.translate((0, 0, bottom_z - wall))  # center at Z=0 (bottom)
  body = body.cut(usb_cutter)

  # Volume buttons on LEFT face (<X) — ROUNDED SLOT:
  vol_cutter = cq.Workplane("YZ").slot2D(btn_tall, btn_depth).extrude(wall*3)
  vol_cutter = vol_cutter.translate((left_x - wall, 0, body_tall * 0.65))  # left wall
  body = body.cut(vol_cutter)

  # Camera hole on BACK face (>Y) — ROUNDED RECTANGLE:
  cam_cutter = cq.Workplane("XZ").rect(cam_w, cam_tall).extrude(wall*3)
  cam_cutter = cam_cutter.translate((cam_x, back_y - wall, body_tall * 0.85))
  try:
      cam_cutter = cam_cutter.edges('|Y').fillet(min(cam_r, min(cam_w, cam_tall) * 0.3))
  except:
      pass
  body = body.cut(cam_cutter)

  # ROUND hole (speaker, LED, microphone, screw) — CYLINDER:
  hole_cutter = cq.Workplane("XY").cylinder(wall*3, hole_r)
  hole_cutter = hole_cutter.translate((hole_x, hole_y, hole_z))
  body = body.cut(hole_cutter)

  # Speaker grille (array of round holes):
  for i in range(grille_count):
      dot = cq.Workplane("XY").cylinder(wall*3, grille_r)
      dot = dot.translate((grille_start_x + i * grille_spacing, 0, bottom_z))
      body = body.cut(dot)

  # Window on FRONT face (<Y) of a building — BOX shape is fine for windows:
  win_cutter = cq.Workplane("XY").box(win_w, wall*3, win_h)  # thin in Y
  win_cutter = win_cutter.translate((win_x, front_y, win_z))
  body = body.cut(win_cutter)

══════════════════════════════════════════════════════════════
SHAPE VARIETY — REAL PRODUCTS ARE NOT ALL RECTANGLES
══════════════════════════════════════════════════════════════

⚠️ THE #2 QUALITY ISSUE IS "BRICK SYNDROME" — everything looks like a box.
  Real manufactured products have ROUNDED cutouts, CIRCULAR holes, and CURVED edges.
  NEVER make every cutout a rectangular box.

  MATCH THE SHAPE TO THE REAL-WORLD FEATURE:
  ┌────────────────────────┬──────────────────────────────────────────────┐
  │ Feature Type            │ CadQuery Shape to Use                        │
  ├────────────────────────┼──────────────────────────────────────────────┤
  │ USB/charging port       │ .slot2D(w, h) — rounded stadium shape        │
  │ Buttons (vol, power)    │ .slot2D(tall, depth) — rounded slot          │
  │ Camera hole             │ .rect(w,h) + .fillet(r) — rounded rectangle  │
  │ Camera lens             │ .cylinder(h, r) — perfect circle             │
  │ Speaker grille          │ Array of .cylinder() holes — circular dots   │
  │ Microphone hole         │ .cylinder(h, r) — tiny circle                │
  │ Screw hole              │ .cylinder(h, r) — circle                     │
  │ LED indicator           │ .cylinder(h, r) — small circle               │
  │ Ventilation slots       │ .slot2D(l, w) — rounded-end slots            │
  │ Windows (buildings)     │ .box(w, d, h) — rectangular is correct       │
  │ Door                    │ .box(w, d, h) — rectangular is correct       │
  │ Mounting boss           │ .cylinder(h, r) — cylindrical post           │
  │ Drainage hole           │ .cylinder(h, r) — round hole                 │
  │ Thumbstick hole         │ .cylinder(h, r) — circular                   │
  │ Knob/dial recess        │ .cylinder(h, r) — circular recess            │
  └────────────────────────┴──────────────────────────────────────────────┘

  RULE: If a feature is ROUND in real life → use .cylinder() or .slot2D()
  RULE: If a feature is RECTANGULAR in real life → use .box()
  RULE: At least 30% of cutouts should be NON-rectangular (cylinders, slots, rounded)
  RULE: FILLET the main body edges aggressively — real products have rounded corners

═══════════════════════════════════════════════════════════════════════════════

**WORKPLANES & POSITIONING:**
  .faces(">Z").workplane()                 # New WP on selected face
  .faces(">Z").workplane(offset=5)         # Offset from face
  .workplane(offset=Z)                     # Offset from current WP
  .center(x, y)                           # Shift 2D origin on WP
  .pushPoints([(x1,y1), ...])              # Define multiple 2D locations
  .transformed(offset=(x,y,z), rotate=(rx,ry,rz))  # Full WP transform

**PATTERNS (for repeated features):**
  .rarray(xSpacing, ySpacing, xCount, yCount)  # Rectangular grid
  .polarArray(radius, startAngle, angle, count)  # Circular pattern
  .pushPoints([(x1,y1),(x2,y2),...])       # Arbitrary positions

**TRANSFORMS (on solids):**
  .translate((dx, dy, dz))                 # Move
  .rotate((ox,oy,oz), (ax,ay,az), deg)     # Rotate about axis through point
  .mirror("XY") / .mirror("XZ") / .mirror("YZ")  # Mirror about plane

**ADVANCED — LOFT, SWEEP:**
  # Loft between two cross-sections:
  result = (cq.Workplane("XY")
    .rect(W1, H1)                          # Bottom cross-section
    .workplane(offset=height)
    .rect(W2, H2)                          # Top cross-section
    .loft())                               # Blend between them

  # Sweep along a path:
  path = cq.Workplane("XZ").spline([(0,0),(50,100),(100,0)])
  result = cq.Workplane("XY").rect(W, H).sweep(path)

**TEXT (for labels, engravings):**
  .text("HELLO", fontsize=10, distance=-0.5)  # Engraved text on face
  .text("HELLO", fontsize=10, distance=1)     # Raised text on face

═══════════════════════════════════════════════════════════════════════════════
ADVANCED CADQUERY TECHNIQUES — FOR PROFESSIONAL / COMPLEX DESIGNS
═══════════════════════════════════════════════════════════════════════════════

**COMPOUND SOLIDS (multiple bodies combined):**
  # Combine many parts into a single compound
  parts = [body, lid, hinge_pin, bracket]
  compound = cq.Compound.makeCompound([p.val() for p in parts])
  result = cq.Workplane("XY")
  result.objects = [compound]

**MULTI-SECTION LOFT (3+ cross-sections for organic shapes):**
  result = (cq.Workplane("XY")
    .rect(60, 40)                          # Bottom: rectangle
    .workplane(offset=30)
    .ellipse(35, 25)                       # Middle: ellipse
    .workplane(offset=30)
    .circle(15)                            # Top: circle
    .loft(ruled=False))                    # ruled=True for flat panels

**RULED vs SMOOTH LOFT:**
  .loft(ruled=True)     # Straight edges between sections (like a prism transition)
  .loft(ruled=False)    # Smooth curved blend (default — better for organic shapes)

**OFFSET 2D CURVES (for creating walls, margins):**
  # Create an outer profile offset from inner
  outer = cq.Workplane("XY").rect(100, 60)
  inner = cq.Workplane("XY").rect(100 - 2*wall, 60 - 2*wall)
  wall_ring = outer.extrude(H).cut(inner.extrude(H))

**SECTION / SPLIT (cut a solid in half for visualization):**
  # Cut the model in half to show internal structure
  half = body.cut(cq.Workplane("XZ").box(1000, 1000, 1000).translate((500, 0, 0)))

**WIRE + EDGE OPERATIONS (for decorative lines, panel lines):**
  # Engrave a groove/channel along a face
  groove_path = cq.Workplane("XY").transformed(offset=(0, 0, H))
  groove_cutter = groove_path.rect(groove_w, groove_w).extrude(-groove_depth)

**ARRAY FEATURES EFFICIENTLY:**
  # Rectangular array of holes
  body = (body.faces(">Z").workplane()
    .rarray(spacing_x, spacing_y, count_x, count_y)
    .hole(hole_d, depth))

  # Polar array of features
  body = (body.faces(">Z").workplane()
    .polarArray(radius, 0, 360, count)
    .hole(hole_d))

  # Custom positions
  body = (body.faces(">Z").workplane()
    .pushPoints([(x1,y1), (x2,y2), (x3,y3)])
    .hole(hole_d))

**EMBOSSED / DEBOSSED PATTERNS:**
  # Raised text
  body = body.faces(">Z").workplane().text("BRAND", fontsize=12, distance=1.0)
  # Engraved text
  body = body.faces(">Z").workplane().text("BRAND", fontsize=12, distance=-0.5)
  # Text on curved surface (requires cq_warehouse.extensions)
  # import cq_warehouse.extensions
  # shape.textOnPath(txt="HELLO WORLD", fontsize=5, distance=1.0, positionOnPath=0.0)

**DRAFT ANGLES (for injection molding):**
  # Add draft angle to vertical faces for mold release
  # Approximate with loft between slightly different cross-sections
  body = (cq.Workplane("XY")
    .rect(L + 2*draft_offset, W + 2*draft_offset)     # Bottom larger
    .workplane(offset=H)
    .rect(L, W)                                         # Top nominal
    .loft())

**SNAP-FIT CLIPS / CANTILEVER HOOKS:**
  # Build a flexible clip as a thin angled plate
  clip_base = cq.Workplane("XY").box(clip_w, clip_t, clip_h)
  # Hook at the top
  hook = cq.Workplane("XY").box(clip_w, clip_t + hook_depth, hook_h)
  hook = hook.translate((0, hook_depth/2, clip_h - hook_h/2))
  clip = clip_base.union(hook)
  # Position on wall
  clip = clip.translate((clip_x, -body_width/2 - clip_t/2, clip_z))
  body = body.union(clip)

**KNURLING / GRIP TEXTURE (simplified):**
  # Diamond knurl pattern using intersecting grooves
  for i in range(num_grooves):
      angle = i * groove_spacing
      groove = cq.Workplane("XY").box(body_length * 2, groove_w, groove_w)
      groove = groove.rotate((0,0,0), (0,0,1), 45 + angle)
      groove = groove.translate((0, 0, knurl_z))
      body = body.cut(groove)

**LIVING HINGE (for foldable parts):**
  # Thin section connecting two thick panels
  left_panel = cq.Workplane("XY").box(panel_w, panel_d, panel_t)
  hinge_section = cq.Workplane("XY").box(panel_w, hinge_width, hinge_t)
  hinge_section = hinge_section.translate((0, panel_d/2 + hinge_width/2, 0))
  right_panel = cq.Workplane("XY").box(panel_w, panel_d, panel_t)
  right_panel = right_panel.translate((0, panel_d + hinge_width, 0))
  result = left_panel.union(hinge_section).union(right_panel)

**THREADED INSERTS / BOSSES (for 3D printing):**
  # Boss with screw hole for heat-set insert
  boss = cq.Workplane("XY").circle(boss_outer_r).extrude(boss_h)
  boss = boss.faces(">Z").workplane().hole(insert_d, boss_h - boss_floor)
  boss = boss.edges("|Z").fillet(min(1.5, boss_outer_r * 0.3))
  boss = boss.translate((boss_x, boss_y, 0))
  body = body.union(boss)

**DOVETAIL / TONGUE-AND-GROOVE JOINTS:**
  # Dovetail profile
  dovetail = (cq.Workplane("XZ")
    .moveTo(-top_w/2, h)
    .lineTo(-bot_w/2, 0)
    .lineTo(bot_w/2, 0)
    .lineTo(top_w/2, h)
    .close()
    .extrude(depth))

**HELICAL / SPIRAL FEATURES:**
  # Helical sweep for springs, threads
  helix = cq.Wire.makeHelix(pitch=pitch, height=helix_h, radius=helix_r)
  spring = cq.Workplane("XY").circle(wire_r).sweep(cq.Workplane("XY").add(helix))

═══════════════════════════════════════════════════════════════════════════════
SURFACE FINISH & EDGE TREATMENT — WHAT SEPARATES AMATEUR FROM PROFESSIONAL
═══════════════════════════════════════════════════════════════════════════════

EDGE TREATMENT RULES (non-negotiable):

1. **EVERY external edge gets treatment** — no raw sharp edges on consumer products
   • Grip/handle areas: large fillets (R2-R5mm) for comfort
   • Structural joints: small chamfers (0.5-1mm) for strength appearance
   • Decorative edges: medium fillets (R1-R3mm) for visual appeal
   • Mating/seam edges: tiny chamfer (0.3-0.5mm) for assembly guide
   • Opening edges (ports, slots): small fillet (R0.5-R1mm) for safety

2. **EDGE SELECTION ORDER** (to avoid fillet/chamfer conflicts):
   a. Apply fillets to VERTICAL edges ("|Z") first — these are the large visual corners
   b. Apply fillets to TOP edges (">Z") — these are the user-facing edges
   c. Apply chamfers to BOTTOM edges ("<Z") — functional, not decorative
   d. Apply specific edge treatments LAST (individual feature edges)
   e. ⚠️ NEVER use "%Circle" selector for fillet/chamfer — it selects ALL circular
      edges including tiny ones from boolean cuts, causing StdFail_NotDone crashes
   f. ALWAYS wrap every fillet/chamfer in try/except — NO EXCEPTIONS

3. **TRANSITION ZONES** — where different sections meet:
   • Where a raised feature meets the main body → fillet (R0.5-R2mm)
   • Where a cutout meets the wall → tiny fillet (R0.3-R0.5mm) if safe
   • Where two different thicknesses meet → chamfer or fillet for smooth blend
   • Where a handle/grip meets the body → generous fillet (R3-R8mm)

SURFACE QUALITY GUIDELINES:

4. **FACE CONTINUITY** — no unintended flat spots or kinks:
   • Splines should have 3+ control points for smooth curves
   • Loft sections should transition gradually (no abrupt size changes)
   • Revolved profiles should use splines, not straight segments, for organic shapes

5. **VISUAL HIERARCHY** — the most important face gets the most detail:
   • Front/user-facing: logo, controls, display cutout, indicator LEDs
   • Top: labels, buttons, status indicators, ventilation
   • Sides: functional ports, buttons, grip texture, panel lines
   • Back: connectivity ports, cable routing, mounting features, compliance label
   • Bottom: feet, serial label recess, drainage, mounting screws

6. **THICKNESS CONSISTENCY** — walls should be uniform unless structurally needed:
   • Consumer electronics: 1.5-2.5mm walls everywhere
   • Structural parts: thicker at stress points, thinner elsewhere
   • If using shell(), add internal ribs where large flat spans exist

FINISHING TOUCHES CHECKLIST (apply after main geometry is done):
  □ Run mental "finger test" — slide a finger along every edge, would it feel sharp?
  □ Check bottom: does it have feet/pads so it won't scratch surfaces?
  □ Check back: are there mounting features or a label area?
  □ Check transitions: are all union joints blended with fillets?
  □ Is there at least ONE decorative element? (panel line, logo, pattern)
  □ Would a customer pick this up and say "this feels finished"?

═══════════════════════════════════════════════════════════════════════════════
ERROR PREVENTION — FOLLOW THESE OR CODE WILL CRASH
═══════════════════════════════════════════════════════════════════════════════

1. **FILLET ≤ 15% of smallest adjacent dimension:**
   safe_fillet = min(corner_radius, min(length, width, height) * 0.15)
   body.edges("|Z").fillet(safe_fillet)
   ⚠️ CRITICAL: For phone cases & thin bodies (thinnest dim < 20mm), use 0.10 not 0.15!
   Example: case_depth=10.5mm → max fillet = 10.5 * 0.10 = 1.05mm

2. **SHELL thickness < 50% of smallest wall:**
   safe_shell = min(wall_thickness, min(length, width, height) * 0.45)

2b. **PREFER MANUAL CAVITY over .shell() when thinnest dimension < 15mm:**
   Instead of: body.faces("<Y").shell(-wall_thickness)
   Use:        cavity = cq.Workplane("XY").box(body_x - 2*wall, body_y - wall, body_z - wall)
               cavity = cavity.translate((0, 0, wall))
               body = body.cut(cavity)
   This avoids shell failures on thin/complex geometry.

3. **ALWAYS FILLET → THEN SHELL (never reverse):**
   ✅ .box(..., centered=(True,True,False)).edges("|Z").fillet(r).faces(">Z").shell(-t)  ← ONLY on main body box
   ❌ .box(...).shell(-t).edges(...).fillet(r)  # CRASHES

4. **CLOSE sketches before extrude:** .moveTo(...).lineTo(...).close().extrude(d)

5. **Boolean bodies MUST physically overlap or share a face.**

6. **Hole diameter < smallest face dimension.**

7. **All extrude/box/cylinder dimensions > 0** (no zero-thickness).

8. **Selectors must be explicit** — never bare .faces() or .edges()

9. **Revolve profiles must stay on one side of the axis.**

10. **The MAIN BODY .box() MUST include centered=(True, True, False). Cutter .box() must NOT.**
    Never put centered= on .extrude(), .rect(), .circle(), or any method other than .box().

10. **For risky fillet/chamfer — apply to SPECIFIC edges by axis or type, not all.**

11. **When cutting many features (holes, slots) into the same face:**
    Build all cuts as separate bodies, then .cut() them one by one or union them
    into a single cutter, then do ONE .cut() operation.

12. **Avoid chaining too many operations on one fluent chain.**
    Break complex geometry into named intermediate variables:
    ✅ body = cq.Workplane("XY").box(L,W,H)
       body = body.edges("|Z").fillet(r)
       body = body.faces(">Z").shell(-t)
    ❌ result = cq.Workplane("XY").box(L,W,H).edges("|Z").fillet(r).faces(">Z").shell(-t).faces("<Z").workplane()...

13. **DEFENSIVE FILLET — wrap in try/except in your mind:**
    If a fillet might fail, use a SMALLER radius than you think you need.
    Rule: max safe fillet = min(all_adjacent_edge_lengths) * 0.35

14. **DEFENSIVE SHELL — manual cavity as fallback:**
    If shell(-t) is risky, use subtraction instead:
    cavity = cq.Workplane("XY").box(L-2*t, W-2*t, H-t).translate((0,0,t))
    body = body.cut(cavity)  # Equivalent to shell but more reliable

15. **BOOLEAN ORDER MATTERS:**
    Do ALL fillets BEFORE cuts. Do ALL big cuts BEFORE small detail cuts.
    Order: box → fillet → shell → large cuts → small cuts → detail features

16. **LOOP SAFETY — guard iteration counts:**
    count = max(1, int(count))  # Never zero or negative
    spacing = max(0.1, total_span / count)  # Never zero spacing

17. **WALL CUTTER SAFETY — prevent severing thin walls:**
    When cutting button/port slots into filleted walls of thin bodies:
    • Cutter perpendicular dim = wall_thickness * 3 (OK — penetrates through wall)
    • Cutter PARALLEL dim (along the thin axis) must be < (thin_dim - 2 * fillet_radius)
    • Example: case_depth=10.5, fillet=1.5 → max cutter Y = 10.5 - 2*1.5 = 7.5mm
    • If the cutter Y exceeds this, it clips through the filleted corners and severs the wall!
    • SAFE PATTERN: cutter Y = min(button_width, thin_dim * 0.5)  # never more than half

18. **FILLET + SHELL + CUT INTERACTION:**
    On thin bodies (any dim < 20mm), large fillets + shell + side cuts = DISASTER.
    The filleted corner zone gets severed by cutters, creating disconnected fragments.
    FIX: On thin bodies, use fillet ≤ 1.0mm on vertical edges, OR skip vertical fillets
    entirely and only fillet horizontal edges after all cuts are done.

═══════════════════════════════════════════════════════════════════════════════
⚠️⚠️⚠️ CRITICAL FILLET SAFETY — #1 CAUSE OF BUILD FAILURES ⚠️⚠️⚠️
═══════════════════════════════════════════════════════════════════════════════

**THE PROBLEM**: Fillet operations crash with `StdFail_NotDone: BRep_API: command not done`
when applied to edges that are too small for the fillet radius. This is the MOST COMMON
build failure. YOU MUST follow these rules EXACTLY:

🚫 **ABSOLUTELY BANNED FILLET PATTERNS** (these WILL crash):
   ❌ body.edges("%Circle").fillet(r)     — catches ALL circular edges including tiny internal ones from boolean cuts
   ❌ body.edges().fillet(r)               — fillets EVERY edge, including degenerate ones
   ❌ body.edges("%Circle").chamfer(r)     — same problem as fillet
   ❌ body.edges("not %Circle").fillet(r)  — still catches too many edges
   ❌ Fillet AFTER boolean cuts             — cut intersections create tiny edges that can't be filleted

✅ **REQUIRED SAFE FILLET PATTERNS** (use ONLY these):
   ✅ body.edges("|Z").fillet(r)           — ONLY vertical edges (predictable, safe)
   ✅ body.edges("|X").fillet(r)           — ONLY edges parallel to X
   ✅ body.edges("|Y").fillet(r)           — ONLY edges parallel to Y
   ✅ body.edges(">Z").fillet(r)           — ONLY top-most edges
   ✅ body.edges("<Z").chamfer(c)          — ONLY bottom-most edges

🛡️ **MANDATORY: EVERY FILLET/CHAMFER MUST USE try/except** — NO EXCEPTIONS:
   ```
   try:
       body = body.edges("|Z").fillet(min(corner_fillet, min(body_length, body_width) * 0.15))
   except:
       pass  # Skip fillet if geometry can't support it
   ```

   This is NON-NEGOTIABLE. Every single .fillet() and .chamfer() call in your code
   MUST be wrapped in try/except. A model without fillets is 1000x better than a crash.

📐 **FILLET EXECUTION ORDER** (strict sequence):
   1. Create basic body shape (box/cylinder/etc)
   2. Apply LARGE corner fillets to the basic body FIRST (while edges are simple)
   3. Apply shell (if needed)
   4. THEN do boolean cuts (holes, slots, ports)
   5. Do NOT fillet after cuts — the cut edges are often too complex/small to fillet
   6. If you MUST fillet after cuts, use try/except and a VERY small radius (0.1-0.3mm max)

📏 **FILLET RADIUS LIMITS** (enforced):
   • Corner fillets: min(desired_r, min(L, W, H) * 0.15)  — use 0.15 not 0.25
   • For thin bodies (any dim < 20mm): min(desired_r, thin_dim * 0.10)  — max ~1mm
   • Edge fillets after cuts: max 0.3mm — TINY radius only
   • When in doubt, use 0.5mm or less
   • NEVER use fillet radius > 2mm on any edge after a boolean cut operation
   • Phone cases: fillet ≤ 1.0mm on vertical edges (case_depth is only ~10mm!)

💡 **SAFE EDGE TREATMENT PATTERN** (copy this exactly):
   ```
   # Step 1: Fillet the basic body BEFORE any cuts
   try:
       body = body.edges("|Z").fillet(min(corner_r, min(L, W) * 0.15))
   except:
       pass

   # Step 2: Do all boolean cuts (holes, slots, ports)
   body = body.cut(usb_port).cut(speaker_holes).cut(camera_cutout)

   # Step 3: OPTIONAL tiny edge cleanup after cuts (very conservative)
   try:
       body = body.edges("|Z").fillet(0.2)
   except:
       pass  # Model is complete without this polish
   ```

═══════════════════════════════════════════════════════════════════════════════
COORDINATE SYSTEM & BODY CENTERING — UNDERSTAND THIS FIRST
═══════════════════════════════════════════════════════════════════════════════

⚠️ centered=(True, True, False) goes ONLY on the MAIN BODY .box() ⚠️
⚠️ centered= is ONLY a .box() parameter — NEVER put it on .extrude(), .circle(), .rect() etc. ⚠️

MAIN BODY (the product shell):
  body = cq.Workplane("XY").box(X_dim, Y_dim, Z_dim, centered=(True, True, False))
  → X: -X_dim/2 to +X_dim/2, Y: -Y_dim/2 to +Y_dim/2, Z: 0 to Z_dim (sits on ground)

  ⚠️ CRITICAL: Z_dim is the VERTICAL dimension — the one that goes UP.
  For upright products: Z = tallest dimension. For flat products: Z = thickness.
  See AXIS ASSIGNMENT in the MASTER SPATIAL ORIENTATION section above.

CUTTERS — Choose the CORRECT shape for each feature:
  ⚠️ NEVER use .box() for round features (ports, speakers, LEDs, screws, buttons).
  ⚠️ Only use .box() for: windows, doors, drawers, panel slots, screen recesses.

  RECTANGULAR cutter (windows, doors, drawers):
    cutter = cq.Workplane("XY").box(cut_x, cut_y, cut_z)  ← NO centered!
    → The cutter is centered on ALL axes. .translate((x, y, z)) moves the CENTER.

  ROUND cutter (speakers, screws, LEDs, sensors, microphones):
    hole = cq.Workplane("XY").cylinder(wall*3, radius)
    hole = hole.translate((x, y, z))

  PILL-SHAPED cutter (USB ports, buttons, vent slots):
    port = cq.Workplane("XZ").slot2D(width, height).extrude(wall*3)
    port = port.translate((x, y, z))

  ROUNDED-RECTANGLE cutter (camera islands, screens):
    cam = cq.Workplane("XZ").rect(w, h).extrude(wall*3)
    cam = cam.edges("|Y").fillet(min(4, min(w,h)*0.15))
    cam = cam.translate((x, y, z))

  PRECISION HOLE (screw holes, pin holes):
    body = body.faces(">Z").workplane().pushPoints([(x,y)]).hole(diameter)

  DEPTH RULE: All cutters must use wall*3 or more — guarantees punch-through.

MANDATORY COORDINATE VARIABLE BLOCK (put this at the top of EVERY script):
  # ═══ COORDINATE REFERENCE (computed from body dimensions) ═══
  left_x    = -body_x / 2             # Left wall X position
  right_x   =  body_x / 2             # Right wall X position
  front_y   = -body_y / 2             # Front wall Y position
  back_y    =  body_y / 2             # Back wall Y position
  bottom_z  =  0                      # Bottom face Z position (ALWAYS 0)
  top_z     =  body_z                 # Top face Z position (ALWAYS body_z)

  Where body_x, body_y, body_z are whatever you named the .box() dimensions.
  These 6 variables must be used for ALL feature placement. NEVER hardcode coordinates.
  NEVER use ±height/2 for Z — Z is ALWAYS 0 to body_z.

═══════════════════════════════════════════════════════════════════════════════
POSITIONAL ANCHORING — FEATURES MUST BE PLACED RELATIVE TO THE PRODUCT
═══════════════════════════════════════════════════════════════════════════════

Every cutout, button, port, window, or sub-feature MUST be positioned using
the parent body's dimensions as reference. NEVER hardcode absolute coordinates.

⚠️ BODY box: centered=(True, True, False) — Z goes 0 to H
⚠️ CUTTER boxes: NO centered parameter — cutter is centered on all axes
   so translate((x, y, z)) puts the CENTER of the cutter at (x, y, z)
⚠️ centered= is ONLY for .box() — NEVER on .extrude(), .rect(), .circle()

─── THE SIMPLEST AND MOST RELIABLE PATTERN FOR CUTOUTS ───

For EVERY cutout, use this pattern:
  1. Create a cutter box (NO centered parameter — default centering on all axes)
  2. Translate so the CENTER of the cutter is at the wall position
  3. Cut from the body

The cutter must be THIN in the wall's perpendicular axis and WIDE enough to
penetrate THROUGH the wall (use wall*3 for guaranteed penetration).

  WALL YOU'RE CUTTING    CUTTER box() DIMENSIONS         WHY
  ──────────────────     ─────────────────────           ───────────
  ±X wall (left/right)   box(wall*3, cut_Y, cut_Z)      thin in X
  ±Y wall (front/back)   box(cut_X, wall*3, cut_Z)      thin in Y
  ±Z wall (top/bottom)   box(cut_X, cut_Y, wall*3)      thin in Z

─── FEATURE POSITION RECIPES (COPY THESE PATTERNS) ───

═══ RECTANGULAR CUTOUT PATTERNS (for windows, doors, drawers, panels) ═══

PATTERN A — Rectangular cutout on FRONT wall (−Y face), e.g., window/door:
  cutter = cq.Workplane("XY").box(cut_w, wall*3, cut_h)
  cutter = cutter.translate((cut_x, front_y, cut_z))
  body = body.cut(cutter)

PATTERN B — Rectangular cutout on BACK wall (+Y face):
  cutter = cq.Workplane("XY").box(cut_w, wall*3, cut_h)
  cutter = cutter.translate((cut_x, back_y, cut_z))
  body = body.cut(cutter)

PATTERN C — Rectangular cutout on LEFT wall (−X face):
  cutter = cq.Workplane("XY").box(wall*3, cut_w, cut_h)
  cutter = cutter.translate((left_x, cut_y, cut_z))
  body = body.cut(cutter)

PATTERN D — Rectangular cutout on RIGHT wall (+X face):
  cutter = cq.Workplane("XY").box(wall*3, cut_w, cut_h)
  cutter = cutter.translate((right_x, cut_y, cut_z))
  body = body.cut(cutter)

PATTERN E — Rectangular cutout on TOP (+Z) or BOTTOM (Z=0):
  cutter = cq.Workplane("XY").box(cut_w, cut_h, wall*3)
  cutter = cutter.translate((cut_x, cut_y, top_z))   # or bottom_z
  body = body.cut(cutter)

═══ ROUND/SHAPED CUTOUT PATTERNS (for ports, holes, speakers, buttons) ═══
⚠️ USE THESE for electronics, mechanical, and consumer products — NOT .box()!

PATTERN R1 — Round hole on any face (speaker, LED, screw, mic, sensor):
  hole = cq.Workplane("XY").cylinder(wall*3, radius)
  hole = hole.translate((hole_x, hole_y, hole_z))  # center on wall
  body = body.cut(hole)

PATTERN R2 — Rounded-slot port on BOTTOM/TOP face (USB-C, headphone, vent):
  port = cq.Workplane("XZ").slot2D(port_w, port_h).extrude(wall*3)
  port = port.translate((port_x, port_y, bottom_z))
  body = body.cut(port)

PATTERN R3 — Rounded-slot button on LEFT/RIGHT wall (volume, power):
  btn = cq.Workplane("YZ").slot2D(btn_len, btn_depth).extrude(wall*3)
  btn = btn.translate((left_x - wall, btn_y, btn_z))
  body = body.cut(btn)

PATTERN R4 — Rounded-rect camera island on BACK face:
  cam = cq.Workplane("XZ").rect(cam_w, cam_h).extrude(wall*3)
  try:
      cam = cam.edges("|Y").fillet(min(4.0, min(cam_w, cam_h) * 0.15))
  except: pass
  cam = cam.translate((cam_x, back_y - wall, cam_z))
  body = body.cut(cam)

PATTERN R5 — Precision bore hole (screw hole, pin hole) on face:
  body = body.faces(">Z").workplane().pushPoints([(x1,y1),(x2,y2)]).hole(diameter, depth)

PATTERN R6 — Counterbored screw hole (common in electronics enclosures):
  body = body.faces(">Z").workplane().pushPoints([(x1,y1)]).cboreHole(screw_d, cbore_d, cbore_depth)

PATTERN R7 — Array of round holes (speaker grille, vent pattern):
  for i in range(count):
      offset = -total_span/2 + i * spacing + spacing/2
      hole = cq.Workplane("XY").cylinder(wall*3, hole_r)
      hole = hole.translate((offset, front_y, hole_z))
      body = body.cut(hole)

PATTERN R8 — Array of rounded vent slots:
  for i in range(count):
      offset = -total_span/2 + i * spacing + spacing/2
      vent = cq.Workplane("XZ").slot2D(slot_len, slot_w).extrude(wall*3)
      vent = vent.translate((offset, back_y, vent_z))
      body = body.cut(vent)

═══ OTHER PATTERNS ═══

PATTERN G — Rectangular array (windows, drawers, grid features):
  for i in range(count):
      offset = -total_span/2 + i * spacing + spacing/2
      cutter = cq.Workplane("XY").box(feat_w, wall*3, feat_h)
      cutter = cutter.translate((offset, front_y, feat_z))
      body = body.cut(cutter)

PATTERN H — Raised feature / boss (button bump, decorative ridge):
  bump = cq.Workplane("XY").box(bump_w, bump_d, bump_h)
  bump = bump.translate((left_x - bump_d/2, bump_y, bump_z))
  body = body.union(bump)

═══ CUTOUT SHAPE SELECTION RULE ═══
┌──────────────────────────┬───────────────────────────────────┐
│ Feature is ROUND in life │ Use PATTERN R1-R8 (.cylinder      │
│                          │   .slot2D .hole .cboreHole)       │
├──────────────────────────┼───────────────────────────────────┤
│ Feature is RECTANGULAR   │ Use PATTERN A-E (.box)            │
│ in life (window, door,   │                                   │
│ drawer, panel, screen)   │                                   │
├──────────────────────────┼───────────────────────────────────┤
│ Feature is IRREGULAR     │ Use sketch (.lineTo .spline       │
│ (cross-shaped, organic)  │   .close) + .cutThruAll()         │
└──────────────────────────┴───────────────────────────────────┘

─── COMPREHENSIVE EXAMPLE — iPhone CASE (UPRIGHT, Z = tall) ───

✅ CORRECT — Phone case standing upright. The TALLEST dimension is Z.
  # ═══ AXIS ASSIGNMENT ═══
  # Product: iPhone case (upright)
  # X axis = case width    = 75.0 mm   (left-right — volume/power buttons on ±X)
  # Y axis = case depth    = 12.0 mm   (front-back — screen opens on -Y, back on +Y)
  # Z axis = case tall     = 152.0 mm  (up-down — USB-C at Z=0, mic at Z=top)
  body_x = 75.0     # width (left-right)
  body_y = 12.0     # depth/thickness (front-back)
  body_z = 152.0    # tall height (up-down)
  wall = 2.0

  # ═══ COORDINATE REFERENCE ═══
  left_x   = -body_x / 2     # = -37.5
  right_x  =  body_x / 2     # = +37.5
  front_y  = -body_y / 2     # = -6.0  (screen side)
  back_y   =  body_y / 2     # = +6.0  (back side)
  bottom_z =  0               # USB-C edge
  top_z    =  body_z          # = 152.0 (mic/top edge)

  # Fillet guard — CRITICAL for thin bodies like phone cases
  # body_y = 12mm, so max fillet = min(8, 12 * 0.10) = 1.2mm
  # Using 0.10 because body_y < 20mm (thin body rule)
  safe_corner_fillet = min(8, min(body_x, body_y, body_z) * 0.10)

  # Build shell — ONLY the main body gets centered=(True, True, False)
  case = cq.Workplane("XY").box(body_x, body_y, body_z, centered=(True, True, False))
  try:
      case = case.edges("|Z").fillet(safe_corner_fillet)  # round the 4 tall corners
  except:
      pass
  case = case.faces("<Y").shell(-wall)  # open the screen side (-Y face)

  # USB-C port — centered on BOTTOM face (Z=0) — ROUNDED SLOT shape
  port_w, port_h = 12.0, 6.0
  port_cutter = cq.Workplane("XZ").slot2D(port_w, port_h).extrude(wall*3)
  port_cutter = port_cutter.translate((0, 0, bottom_z - wall))
  case = case.cut(port_cutter)

  # Speaker grille — array of ROUND holes on BOTTOM face
  for i in range(6):
      hole = cq.Workplane("XY").cylinder(wall*3, 0.8)  # cylindrical hole
      hole = hole.translate((15 + i*3, 0, bottom_z))
      case = case.cut(hole)

  # Volume buttons — ROUNDED SLOTS on LEFT wall (-X)
  for z_frac in [0.55, 0.65]:
      btn = cq.Workplane("YZ").slot2D(12.0, 4.0).extrude(wall*3)
      btn = btn.translate((left_x - wall, 0, body_z * z_frac))
      case = case.cut(btn)

  # Power button — ROUNDED SLOT on RIGHT wall (+X)
  pwr = cq.Workplane("YZ").slot2D(18.0, 4.0).extrude(wall*3)
  pwr = pwr.translate((right_x, 0, body_z * 0.60))
  case = case.cut(pwr)

  # Camera cutout — ROUNDED RECTANGLE on BACK face (+Y)
  cam_w, cam_h = 35.0, 40.0
  cam = cq.Workplane("XZ").rect(cam_w, cam_h).extrude(wall*3)
  cam = cam.translate((-body_x*0.2, back_y - wall, body_z * 0.85))
  try:
      cam = cam.edges("|Y").fillet(min(4.0, min(cam_w, cam_h) * 0.15))
  except:
      pass
  case = case.cut(cam)

  result = case

❌ WRONG — Common mistakes:
  # ❌ WRONG AXIS ASSIGNMENT — putting tallest dim in X instead of Z:
  body = cq.Workplane("XY").box(150, 75, 10, centered=(True, True, False))
  # → This makes Z=10mm (thickness!) and X=150mm. Features using body_height*0.65
  #   will compute to 6.5mm — nonsense on a 10mm thick body! Z must be the tall axis.
  # ❌ centered on extrude — TypeError! centered is ONLY for .box()
  shape = cq.Workplane("XY").rect(10, 5).extrude(3, centered=(True, True, False))
  # ❌ centered on cutter — messes up translate positioning
  cutter = cq.Workplane("XY").box(12, 6, 6, centered=(True, True, False)).translate((0, 0, 5))
  # ❌ Missing centered on main body — Z will go from -H/2 to +H/2 instead of 0 to H
  case = cq.Workplane("XY").box(150, 75, 10)
  # ❌ Using z=-height/2 (wrong! bottom is z=0 with centered=(T,T,F) on body)
  usb = cq.Workplane("XY").box(12, 6, 6).translate((0, 0, -body_z/2))
  # ❌ Feature at Y=0 (center of body, not on a wall!)
  port = cq.Workplane("XY").box(12, 6, 6).translate((0, 0, 3))

─── KEY RULES (MEMORIZE THESE) ───

1. MAIN BODY .box() MUST include centered=(True, True, False). CUTTER .box() must NOT.
   centered= is ONLY for .box() — NEVER on .extrude(), .rect(), .circle(), .cylinder() etc.
2. Z_dim MUST be the VERTICAL/UPWARD dimension. For upright products: Z = tallest. For flat: Z = thickness.
3. Z=0 is ALWAYS the bottom. Z=body_z is ALWAYS the top. Z IS NEVER NEGATIVE.
4. EVERY feature position MUST use coordinate variables (left_x, right_x, front_y, back_y, bottom_z, top_z).
5. Cutout depth: ALWAYS wall*3 or more — guarantees it punches through.
6. Use .translate((x, y, z)) with coordinate variables — simplest and least error-prone.
7. Features on a wall: ONE coordinate aligns with the wall, the other two position along the surface.
8. Positions along the tall axis use fractions: body_z * 0.3, body_z * 0.7, etc.
9. The AXIS ASSIGNMENT comment is MANDATORY — write it before the .box() call.
10. NEVER use .transformed(offset=...) on XZ or YZ workplanes — it maps axes differently and causes errors.

═══════════════════════════════════════════════════════════════════════════════
MODIFICATION MODE — WHEN PREVIOUS CODE IS PROVIDED
═══════════════════════════════════════════════════════════════════════════════

⚠️⚠️⚠️ THIS IS THE MOST IMPORTANT SECTION WHEN MODIFYING ⚠️⚠️⚠️

When the user's message includes PREVIOUS CADQUERY CODE, you are in 
MODIFICATION MODE. You must EDIT the existing code, NOT write new code.

THE GOLDEN RULE: Your output code must be 90%+ IDENTICAL to the previous code.
The only differences should be the specific lines you added/changed.

STEP-BY-STEP PROCESS:
  1. COPY the entire previous code into your output AS-IS.
  2. FIND the right place to insert your modification (usually just before `result = ...`).
  3. ADD your new code lines at that insertion point.
  4. KEEP the `result = ...` line at the end.
  5. ADD any new parameters to the parameters list (keep ALL existing ones).

WHAT YOU MUST PRESERVE (do NOT change):
  ✓ All import statements — keep them exactly the same
  ✓ All parameter variable definitions — same names, same default values
  ✓ All derived/guarded dimension calculations
  ✓ The main body construction (box, fillet, shell, etc.)
  ✓ ALL existing .cut() and .union() operations
  ✓ The `result = ...` assignment at the end
  ✓ All existing comments

WHAT YOU MAY ADD:
  ✓ New parameter variables (with new names)
  ✓ New .cut() or .union() operations on the existing body variable
  ✓ New comments explaining your additions

WHAT YOU MAY CHANGE (only if user explicitly asks):
  ✓ A specific parameter's default value (e.g., "make it taller")
  ✓ A specific feature (e.g., "remove the handle", "make the hole bigger")

POSITIONING new features:
  ✓ USE the body dimension variables from the existing code
  ✓ Match cutout SHAPE to real-world feature: .cylinder() for round, .slot2D() for rounded slots, .box() for rectangular
  ✓ Cutout depth MUST be wall*3 or more
  ✓ Wall positions are ±body_dim/2

EXAMPLE — if previous code builds a box with a hole:
  ```
  body = cq.Workplane("XY").box(100, 60, 40)
  hole = cq.Workplane("XY").box(10, 20, 10).translate((0, -30, 20))
  body = body.cut(hole)
  result = body
  ```
  
  And user says "add a slot on top", your code should be:
  ```
  body = cq.Workplane("XY").box(100, 60, 40)              # ← KEPT
  hole = cq.Workplane("XY").box(10, 20, 10).translate((0, -30, 20))  # ← KEPT
  body = body.cut(hole)                                     # ← KEPT
  # NEW: Slot on top face
  slot = cq.Workplane("XY").box(30, 5, 12).translate((0, 0, 40))  # ← ADDED
  body = body.cut(slot)                                     # ← ADDED
  result = body                                             # ← KEPT
  ```

  NOT this (rewriting from scratch):
  ```
  body = cq.Workplane("XY").box(100, 60, 40)  # Started over!
  body = body.faces(">Z").workplane().slot2D(30, 5).cutBlind(-12)  # Different approach!
  result = body  # Lost the hole!
  ```

═══════════════════════════════════════════════════════════════════════════════
cq_warehouse — REAL PARAMETRIC PARTS LIBRARY (AVAILABLE IN EXEC NAMESPACE)
═══════════════════════════════════════════════════════════════════════════════

cq_warehouse provides REAL ENGINEERING PARTS — fasteners, bearings, sprockets,
chains, threads — with accurate ISO/DIN dimensions. All classes below are
PRE-IMPORTED in the execution namespace (no import needed in your code, but you
CAN import them explicitly from cq_warehouse if desired).

**IMPORTANT:** When using cq_warehouse parts, add `import cq_warehouse.extensions`
at the top of your code to enable Workplane extensions like clearanceHole(),
tapHole(), pressFitHole(), etc.

─────────────────────────────────────────────────────────────────
FASTENERS — Nuts, Screws, Washers (from cq_warehouse.fastener)
─────────────────────────────────────────────────────────────────

**SCREWS** (all are CadQuery Solid sub-classes, usable directly):
  SocketHeadCapScrew(size="M6-1", fastener_type="iso4762", length=20, simple=True)
  HexHeadScrew(size="M8-1.25", fastener_type="iso4017", length=30, simple=True)
  ButtonHeadScrew(size="M4-0.7", fastener_type="iso7380_1", length=12, simple=True)
  CounterSunkScrew(size="M5-0.8", fastener_type="iso10642", length=16, simple=True)
  PanHeadScrew(size="M3-0.5", fastener_type="iso1580", length=10, simple=True)
  SetScrew(size="M6-1", fastener_type="iso4026", length=10, simple=True)
  CheeseHeadScrew(size="M4-0.7", fastener_type="iso1207", length=12, simple=True)
  HexHeadWithFlangeScrew(size="M8-1.25", fastener_type="din1665", length=25, simple=True)

  Parameters:
    size: "M{diameter}-{pitch}" (metric) or "#{gauge}-{TPI}" (imperial)
    fastener_type: ISO/DIN standard identifier
    length: screw shaft length in mm (base of head to tip)
    simple: True=no threads (fast), False=accurate threads (slow)
    hand: "right" or "left" (default "right")

  Useful class methods:
    SocketHeadCapScrew.types()           → ['iso4762', 'asme_b18.3']
    SocketHeadCapScrew.sizes("iso4762")  → ['M2-0.4', 'M3-0.5', ..., 'M36-4']
    Screw.select_by_size("M6-1")        → {class: [types...], ...}

  Common metric sizes: M2-0.4, M2.5-0.45, M3-0.5, M4-0.7, M5-0.8,
    M6-1, M8-1.25, M10-1.5, M12-1.75, M16-2, M20-2.5

**NUTS:**
  HexNut(size="M6-1", fastener_type="iso4032", simple=True)
  HexNutWithFlange(size="M8-1.25", fastener_type="din1665")
  SquareNut(size="M6-1", fastener_type="din557")
  DomedCapNut(size="M6-1", fastener_type="din1587")
  HeatSetNut(size="M4-0.7-Standard", fastener_type="McMaster-Carr")
  BradTeeNut(size="M8-1.25", fastener_type="Hilitchi")

  Properties: .nut_thickness, .nut_diameter, .info

**WASHERS:**
  PlainWasher(size="M6", fastener_type="iso7089")
  ChamferedWasher(size="M8", fastener_type="iso7090")
  CheeseHeadWasher(size="M4", fastener_type="iso7092")

  Properties: .washer_thickness, .washer_diameter

**CREATING HOLES FOR FASTENERS (via cq_warehouse.extensions):**
  # Clearance hole (for bolts to pass through)
  plate = (cq.Workplane("XY").box(50, 50, 10)
    .faces(">Z").workplane()
    .clearanceHole(fastener=screw, fit="Normal"))

  # Tap hole (threaded hole for screws)
  plate = (cq.Workplane("XY").box(50, 50, 10)
    .faces(">Z").workplane()
    .tapHole(fastener=screw, material="Soft", depth=8))

  # Threaded hole (with actual thread geometry)
  plate = (cq.Workplane("XY").box(50, 50, 10)
    .faces(">Z").workplane()
    .threadedHole(fastener=screw, depth=8))

  # Insert hole (for heat-set inserts in 3D prints)
  plate.insertHole(fastener=heatset_nut)

  fit options: "Close", "Normal", "Loose"
  material options: "Soft", "Hard"

**ASSEMBLY WORKFLOW (fasteners in correct positions):**
  assembly = cq.Assembly(None, name="my_assembly")
  screw = SocketHeadCapScrew(size="M4-0.7", fastener_type="iso4762", length=16)
  plate = (cq.Workplane("XY").box(80, 60, 10)
    .faces(">Z").workplane()
    .pushPoints([(20, 15), (-20, 15), (20, -15), (-20, -15)])
    .clearanceHole(fastener=screw, baseAssembly=assembly))
  assembly.add(plate, name="plate", color=cq.Color(0.8, 0.8, 0.8))
  # Screw positions are auto-added to assembly!
  print(assembly.fastenerQuantities())

─────────────────────────────────────────────────────────────────
BEARINGS (from cq_warehouse.bearing)
─────────────────────────────────────────────────────────────────

  SingleRowDeepGrooveBallBearing(size="M8-22-7", bearing_type="SKT")
  SingleRowCappedDeepGrooveBallBearing(size="M8-22-7", bearing_type="SKT")
  SingleRowAngularContactBallBearing(size="M10-30-9", bearing_type="SKT")
  SingleRowCylindricalRollerBearing(size="M10-30-9", bearing_type="SKT")
  SingleRowTaperedRollerBearing(size="M20-42-15", bearing_type="SKT")

  Size format: "M{bore}-{outer_diameter}-{width}" in mm
  bearing_type: "SKT" (standard)

  Available sizes (SingleRowDeepGrooveBallBearing):
    M3-10-4, M4-11-4, M4-13-5, M5-13-4, M5-16-5, M6-15-5, M6-19-6,
    M8-22-7, M8-24-8, M10-26-8, M10-30-9, M10-35-11

  **Creating press-fit holes for bearings:**
  bearing = SingleRowDeepGrooveBallBearing(size="M8-22-7", bearing_type="SKT")
  housing = (cq.Workplane("XY").box(60, 40, 15)
    .faces(">Z").workplane()
    .pressFitHole(bearing=bearing, baseAssembly=assembly))

─────────────────────────────────────────────────────────────────
SPROCKETS (from cq_warehouse.sprocket)
─────────────────────────────────────────────────────────────────

  sprocket = Sprocket(
    num_teeth=32,           # Number of teeth
    chain_pitch=12.7,       # Default: 1/2 inch (standard bicycle)
    roller_diameter=7.9375, # Default: 5/16 inch
    clearance=0.0,
    thickness=2.13,         # Default: 0.084 inch
    bolt_circle_diameter=104,  # For mounting bolts (0 = none)
    num_mount_bolts=4,         # (0 = no bolt holes)
    mount_bolt_diameter=10,
    bore_diameter=80           # Center hole (0 = no bore)
  )

  Properties: .pitch_radius, .outer_radius, .pitch_circumference

─────────────────────────────────────────────────────────────────
CHAINS (from cq_warehouse.chain)
─────────────────────────────────────────────────────────────────

  chain = Chain(
    spkt_teeth=[32, 16],                         # Teeth per sprocket
    positive_chain_wrap=[True, True],            # Wrap direction
    spkt_locations=[(0, 0), (200, 0)],           # Sprocket centers
    chain_pitch=12.7,                            # 1/2 inch default
    roller_diameter=7.9375                        # 5/16 inch default
  )

  Properties: .chain_links, .num_rollers, .pitch_radii

  # Full transmission assembly:
  transmission = chain.assemble_chain_transmission(spkts=[sprocket1, sprocket2])

─────────────────────────────────────────────────────────────────
THREADS (from cq_warehouse.thread)
─────────────────────────────────────────────────────────────────

  ⚠️  CRITICAL: For threads, ALWAYS use simple=False. simple=True produces
  null geometry and will crash. Threads are slow to generate — keep length
  short (≤30mm) to avoid timeout.

  # ISO metric thread (60° angle — standard bolts/nuts)
  thread = IsoThread(
    major_diameter=10,   # M10 thread
    pitch=1.5,           # 1.5mm pitch
    length=20,           # 20mm long
    external=True,       # True=bolt, False=nut
    hand="right",
    end_finishes=("fade", "square"),  # Options: "raw","fade","square","chamfer"
    simple=False         # MUST be False — True produces null shape!
  )

  # ACME thread (29° — for lead screws)
  thread = AcmeThread(size="3/4", length=50, external=True)

  # Metric trapezoidal thread (30° — ISO 2904)
  thread = MetricTrapezoidalThread(size="8x1.5", length=30, external=True)

  # Plastic bottle thread (ASTM D2911)
  thread = PlasticBottleThread(size="M38SP444", external=False)

─────────────────────────────────────────────────────────────────
WORKPLANE EXTENSIONS (from cq_warehouse.extensions)
─────────────────────────────────────────────────────────────────

After `import cq_warehouse.extensions`, these methods are added to Workplane:

  .clearanceHole(fastener, fit="Normal", depth=None, counterSunk=True,
                 baseAssembly=None)
  .tapHole(fastener, material="Soft", depth=None, counterSunk=True,
           baseAssembly=None)
  .threadedHole(fastener, depth, hand="right", simple=False,
                baseAssembly=None)
  .insertHole(fastener, fit="Normal", depth=None, baseAssembly=None)
  .pressFitHole(bearing, interference=0, fit="Normal", depth=None,
                baseAssembly=None)
  .textOnPath(txt, fontsize, distance, positionOnPath=0.0)
  .hexArray(diagonal, xCount, yCount, center=True)
  .thicken(depth)

Shape extensions:
  shape.embossText(txt, fontsize, depth, path)
  shape.projectText(txt, fontsize, depth, path)
  shape.maxFillet(edgeList)

─────────────────────────────────────────────────────────────────
cq_warehouse EXAMPLE — PILLOW BLOCK WITH BEARING & SCREWS
─────────────────────────────────────────────────────────────────

  import cadquery as cq
  import cq_warehouse.extensions

  bearing = SingleRowDeepGrooveBallBearing(size="M8-22-7", bearing_type="SKT")
  screw = SocketHeadCapScrew(size="M3-0.5", fastener_type="iso4762", length=12)
  assembly = cq.Assembly(None, name="pillow_block")

  base = (cq.Workplane("XY")
    .box(60, 80, 10)
    .faces(">Z").workplane()
    .pressFitHole(bearing=bearing, baseAssembly=assembly)
    .faces(">Z").workplane()
    .rect(40, 60, forConstruction=True).vertices()
    .clearanceHole(fastener=screw, baseAssembly=assembly)
    .edges("|Z").fillet(2))
  assembly.add(base, name="base", color=cq.Color(0.6, 0.5, 1.0))

  # For export, use the base plate as result (screws/bearing are in assembly)
  result = base

─────────────────────────────────────────────────────────────────
WHEN TO USE cq_warehouse vs MANUAL GEOMETRY
─────────────────────────────────────────────────────────────────

USE cq_warehouse when:
  ✅ User asks for bolts, screws, nuts, washers, fasteners
  ✅ User asks for bearings, pillow blocks
  ✅ User asks for sprockets, chains, gears with chains
  ✅ User asks for threaded parts, lead screws
  ✅ User wants mounting holes with proper clearance/tap sizing
  ✅ User mentions specific ISO/DIN standards

USE manual CadQuery geometry when:
  ✅ User asks for consumer products (cases, stands, organizers)
  ✅ Custom shapes, enclosures, brackets
  ✅ Anything without standard engineering components

COMBINE BOTH when:
  ✅ A bracket with mounting bolt holes → manual body + clearanceHole()
  ✅ A motor mount with bearings → manual housing + pressFitHole()
  ✅ An enclosure with screwed lid → manual shell + tapHole() + screws

⚠️ RESULT ASSIGNMENT for cq_warehouse parts:
  # For standalone part: use .cq_object
  nut = HexNut(size="M8-1.25", fastener_type="iso4032", simple=True)
  result = nut.cq_object

  # For plate with holes: the plate IS the result
  screw = SocketHeadCapScrew(...)
  plate = cq.Workplane("XY").box(60,60,5).faces(">Z").workplane()
    .clearanceHole(fastener=screw, fit="Normal")
  result = plate

  # For assemblies: use the main body as result
  result = base_plate  # NOT the assembly object

═══════════════════════════════════════════════════════════════════════════════
COMPLEX PRODUCT RECIPES — PROVEN PATTERNS
═══════════════════════════════════════════════════════════════════════════════

■ PHONE / TABLET CASE:
  body = cq.Workplane("XY").box(L, W, H)
  body = body.edges("|Z").fillet(corner_r)
  body = body.edges("|X").fillet(min(edge_r, H*0.4))
  body = body.faces(">Z").shell(-wall)
  # Camera island (rectangular rounded cutout)
  cam_cut = (cq.Workplane("XY")
    .transformed(offset=(cam_x, cam_y, -H/2))
    .rect(cam_w, cam_h).extrude(wall * 3))
  body = body.cut(cam_cut)
  # Side button slots
  for (bx, by, bw, bh) in button_positions:
      slot = cq.Workplane("XZ").transformed(offset=(bx, 0, by)).rect(bw, bh).extrude(W)
      body = body.cut(slot)
  # Charging port cutout at bottom
  port = cq.Workplane("XZ").transformed(offset=(0, 0, -H/2+port_h/2)).rect(port_w, port_h).extrude(W)
  result = body.cut(port)

■ ELECTRONICS ENCLOSURE (with lid):
  # Bottom shell
  body = cq.Workplane("XY").box(L, W, H).edges("|Z").fillet(r)
  body = body.faces(">Z").shell(-wall)
  # Mounting bosses in corners
  for (bx, by) in [(-L/2+8, -W/2+8), (L/2-8, -W/2+8), (-L/2+8, W/2-8), (L/2-8, W/2-8)]:
      boss = cq.Workplane("XY").transformed(offset=(bx, by, wall)).circle(boss_r).extrude(boss_h)
      boss_hole = cq.Workplane("XY").transformed(offset=(bx, by, wall)).circle(screw_r).extrude(boss_h)
      body = body.union(boss).cut(boss_hole)
  # Ventilation slot array on side
  for i in range(vent_count):
      vx = -vent_total/2 + i * vent_spacing
      vent = cq.Workplane("XZ").transformed(offset=(vx, -W/2, H*0.4)).rect(vent_w, vent_h).extrude(wall*2)
      body = body.cut(vent)
  result = body

■ DESK ORGANIZER (multi-compartment):
  # Outer shell
  outer = cq.Workplane("XY").box(total_w, total_d, total_h)
  outer = outer.edges("|Z").fillet(outer_r)
  # Inner cavity
  inner = cq.Workplane("XY").transformed(offset=(0, 0, base_t)).box(
      total_w - 2*wall, total_d - 2*wall, total_h)
  body = outer.cut(inner)
  # Divider walls
  for dx in divider_positions:
      div = cq.Workplane("XY").transformed(offset=(dx, 0, total_h/2)).box(wall, total_d-2*wall, total_h-base_t)
      body = body.union(div)
  # Pen holes in one section
  for (px, py) in pen_positions:
      pen_hole = cq.Workplane("XY").transformed(offset=(px, py, 0)).circle(pen_r).extrude(total_h+1)
      body = body.cut(pen_hole)
  result = body

■ GEAR (accurate tooth geometry):
  import math
  pitch_radius = module * num_teeth / 2
  outer_radius = pitch_radius + module
  root_radius = pitch_radius - 1.25 * module
  tooth_angle = 360.0 / num_teeth
  tooth_width = math.pi * module / 2
  # Base cylinder
  gear = cq.Workplane("XY").circle(root_radius).extrude(thickness)
  # Create one tooth and rotate copies
  half_tooth_angle = tooth_width / (2 * pitch_radius) * 180 / math.pi
  tooth = (cq.Workplane("XY")
    .moveTo(root_radius, -tooth_width/2)
    .lineTo(outer_radius, -tooth_width/2 * 0.7)
    .lineTo(outer_radius, tooth_width/2 * 0.7)
    .lineTo(root_radius, tooth_width/2)
    .close().extrude(thickness))
  for i in range(num_teeth):
      rotated = tooth.rotate((0,0,0), (0,0,1), i * tooth_angle)
      gear = gear.union(rotated)
  # Center bore + keyway
  gear = gear.faces(">Z").workplane().hole(bore_diameter)
  result = gear

■ BOTTLE / TUMBLER (revolution profile):
  # Profile on XZ plane (positive X = radius, Y = height)
  profile = (cq.Workplane("XZ")
    .moveTo(0, 0)
    .lineTo(base_r, 0)
    .lineTo(base_r, 3)  # base flat
    .spline([(base_r, 3), (body_r, total_h * 0.2),
             (body_r, total_h * 0.7), (neck_r, total_h * 0.9)])
    .lineTo(neck_r, total_h)
    .lineTo(lip_r, total_h)
    .lineTo(lip_r, total_h - lip_h)
    .lineTo(0, total_h - lip_h)
    .close()
    .revolve(360, (0,0,0), (0,1,0)))
  result = profile

■ LAPTOP / MONITOR STAND:
  # Angled platform
  platform = cq.Workplane("XY").box(plat_w, plat_d, plat_t)
  platform = platform.edges("|Z").fillet(plat_r)
  # Support legs (angled)
  leg_profile = (cq.Workplane("XZ")
    .moveTo(-leg_w/2, 0).lineTo(-leg_w/2, stand_h)
    .lineTo(leg_w/2, stand_h - leg_w)
    .lineTo(leg_w/2, 0).close().extrude(leg_d))
  left_leg = leg_profile.translate((-plat_w/2 + leg_inset, 0, 0))
  right_leg = leg_profile.translate((plat_w/2 - leg_inset, 0, 0))
  body = platform.translate((0, 0, stand_h)).union(left_leg).union(right_leg)
  # Cable management hole
  cable_hole = cq.Workplane("XY").transformed(offset=(0, -plat_d*0.3, stand_h)).circle(cable_r).extrude(plat_t+2)
  body = body.cut(cable_hole)
  # Ventilation slots
  for i in range(num_slots):
      sx = -slot_area/2 + i * slot_spacing
      slot = cq.Workplane("XY").transformed(offset=(sx, 0, stand_h)).rect(slot_w, slot_l).extrude(plat_t+2)
      body = body.cut(slot)
  result = body

■ HEADPHONE STAND:
  # Base plate
  base = cq.Workplane("XY").ellipse(base_rx, base_ry).extrude(base_h)
  base = base.edges(">Z").fillet(base_h * 0.3)
  # Vertical stem
  stem = cq.Workplane("XY").circle(stem_r).extrude(stem_h)
  body = base.union(stem)
  # Curved arm at top (sweep or arc)
  arm = (cq.Workplane("XZ")
    .moveTo(0, stem_h)
    .sagittaArc((arm_reach, stem_h + arm_rise), arm_curve)
    .lineTo(arm_reach, stem_h + arm_rise - arm_t)
    .sagittaArc((0, stem_h - arm_t), -arm_curve * 0.8)
    .close().extrude(arm_w))
  arm = arm.translate((-arm_w/2, 0, 0))
  body = body.union(arm)
  result = body

■ BRACKET / WALL MOUNT (L-bracket with gusset):
  # Base plate with holes
  base = cq.Workplane("XY").box(base_l, base_w, base_t)
  base = base.faces(">Z").workplane().pushPoints(hole_positions).hole(hole_d)
  # Vertical arm
  arm = cq.Workplane("XY").transformed(offset=(0, -base_w/2 + arm_t/2, arm_h/2 + base_t/2)).box(base_l, arm_t, arm_h)
  body = base.union(arm)
  # Triangular gusset for strength
  gusset = (cq.Workplane("YZ")
    .moveTo(-base_w/2, base_t)
    .lineTo(-base_w/2, base_t + gusset_h)
    .lineTo(-base_w/2 + arm_t, base_t)
    .close().extrude(gusset_t))
  body = body.union(gusset.translate((-gusset_t/2, 0, 0)))
  # Fillets on inner edges for strength
  result = body

■ CHESS PIECE / TROPHY (revolution + booleans):
  # Profile on XZ plane: base → stem → body → finial
  profile = (cq.Workplane("XZ")
    .moveTo(0, 0)
    .lineTo(base_r, 0)                  # Base bottom
    .lineTo(base_r, base_h*0.3)         # Base side
    .lineTo(base_r*0.8, base_h)         # Base taper
    .lineTo(stem_r, base_h+2)           # Stem start
    .lineTo(stem_r, base_h+stem_h)      # Stem
    .spline([(stem_r, base_h+stem_h),   # Body curve
             (body_r, base_h+stem_h+body_h*0.4),
             (body_r*0.7, base_h+stem_h+body_h)])
    .lineTo(0, base_h+stem_h+body_h)    # Top center
    .close()
    .revolve(360, (0,0,0), (0,1,0)))
  # Add decorative ring/collar
  ring = cq.Workplane("XY").transformed(offset=(0,0,base_h)).circle(base_r*0.9).circle(stem_r).extrude(3)
  result = profile.union(ring)

■ ABSTRACT SCULPTURE (multi-loft organic):
  # Create flowing organic form by lofting between cross-sections
  import math
  body = (cq.Workplane("XY")
    .ellipse(base_w/2, base_d/2)                    # Bottom: wide ellipse
    .workplane(offset=total_h*0.25)
    .transformed(rotate=(0, 0, twist_angle*0.33))
    .ellipse(mid_w/2, mid_d/2)                      # Mid: rotated smaller
    .workplane(offset=total_h*0.25)
    .transformed(rotate=(0, 0, twist_angle*0.66))
    .ellipse(mid_w*0.8/2, mid_d*0.8/2)              # Upper-mid
    .workplane(offset=total_h*0.25)
    .transformed(rotate=(0, 0, twist_angle))
    .ellipse(top_w/2, top_d/2)                      # Top: rotated narrow
    .loft())
  # Hollow for weight saving (optional)
  # body = body.shell(-wall_t)
  # Pedestal base
  pedestal = cq.Workplane("XY").rect(ped_w, ped_d).extrude(ped_h)
  pedestal = pedestal.edges("|Z").fillet(ped_r)
  result = pedestal.union(body.translate((0, 0, ped_h)))

■ HUMAN FIGURE / FIGURINE (primitive assembly):
  # Head
  head = cq.Workplane("XY").sphere(head_r)
  # Neck
  neck = cq.Workplane("XY").cylinder(neck_h, neck_r)
  # Torso: loft from shoulders to waist
  torso = (cq.Workplane("XY")
    .ellipse(shoulder_w/2, chest_d/2)
    .workplane(offset=torso_h)
    .ellipse(waist_w/2, waist_d/2)
    .loft())
  # Arms: cylinders or swept shapes
  arm = cq.Workplane("XY").circle(arm_r).extrude(arm_len)
  left_arm = arm.translate((-shoulder_w/2 - arm_r, 0, torso_h*0.85))
  right_arm = arm.translate((shoulder_w/2 + arm_r, 0, torso_h*0.85))
  # Legs
  leg = cq.Workplane("XY").circle(leg_r).extrude(leg_len)
  left_leg = leg.translate((-hip_spacing/2, 0, -leg_len))
  right_leg = leg.translate((hip_spacing/2, 0, -leg_len))
  # Assemble from bottom up
  body_z = leg_len  # ground offset
  figure = (left_leg.translate((0,0,body_z))
    .union(right_leg.translate((0,0,body_z)))
    .union(torso.translate((0,0,body_z)))
    .union(left_arm.translate((0,0,body_z)))
    .union(right_arm.translate((0,0,body_z)))
    .union(neck.translate((0,0,body_z+torso_h)))
    .union(head.translate((0,0,body_z+torso_h+neck_h+head_r))))
  # Optional: base/pedestal
  base = cq.Workplane("XY").cylinder(base_h, base_r)
  result = base.union(figure.translate((0,0,base_h)))

■ BUILDING / HOUSE (box booleans + roof):
  # Main volume
  building = cq.Workplane("XY").box(bldg_w, bldg_d, bldg_h)
  building = building.translate((0, 0, bldg_h/2))  # sit on ground
  # Windows: array of rectangular cuts on front face
  for row in range(num_floors):
      for col in range(windows_per_floor):
          wx = -bldg_w/2 + wall_margin + col * win_spacing
          wz = floor_h * (row + 0.5) + win_h * 0.3
          win_cut = (cq.Workplane("XZ")
            .transformed(offset=(wx, -bldg_d/2, wz))
            .rect(win_w, win_h).extrude(wall_t*2))
          building = building.cut(win_cut)
  # Door
  door_cut = (cq.Workplane("XZ")
    .transformed(offset=(0, -bldg_d/2, door_h/2))
    .rect(door_w, door_h).extrude(wall_t*2))
  building = building.cut(door_cut)
  # Gabled roof (triangular prism)
  roof = (cq.Workplane("XZ")
    .moveTo(-bldg_w/2 - overhang, 0)
    .lineTo(0, roof_h)
    .lineTo(bldg_w/2 + overhang, 0)
    .close()
    .extrude(bldg_d + 2*overhang, both=True))
  roof = roof.translate((0, 0, bldg_h))
  result = building.union(roof)

■ SKYSCRAPER / TOWER (stacked floors + setbacks):
  # Base floors (wider)
  base_block = cq.Workplane("XY").rect(base_w, base_d).extrude(base_floors * floor_h)
  # Mid section (narrower)
  mid_block = (cq.Workplane("XY")
    .transformed(offset=(0, 0, base_floors * floor_h))
    .rect(mid_w, mid_d).extrude(mid_floors * floor_h))
  # Top section (narrowest)
  top_block = (cq.Workplane("XY")
    .transformed(offset=(0, 0, (base_floors + mid_floors) * floor_h))
    .rect(top_w, top_d).extrude(top_floors * floor_h))
  tower = base_block.union(mid_block).union(top_block)
  # Crown / spire
  spire = (cq.Workplane("XY")
    .transformed(offset=(0, 0, total_h))
    .circle(spire_base_r)
    .workplane(offset=spire_h)
    .circle(1)
    .loft())
  tower = tower.union(spire)
  # Window grid pattern on each face
  for face_dir, face_offset in [(">Y", base_d/2), ("<Y", base_d/2), (">X", base_w/2), ("<X", base_w/2)]:
      for floor_i in range(total_floors):
          for win_i in range(wins_per_side):
              # Cut window recesses
              pass  # detailed positioning per face
  result = tower

■ CASTLE (towers + walls + gate):
  # Main keep (central building)
  keep = cq.Workplane("XY").rect(keep_w, keep_d).extrude(keep_h)
  keep = keep.translate((0, 0, keep_h/2))
  # Corner towers (4 cylinders)
  positions = [(keep_w/2, keep_d/2), (-keep_w/2, keep_d/2),
               (keep_w/2, -keep_d/2), (-keep_w/2, -keep_d/2)]
  towers = keep
  for (tx, ty) in positions:
      tower = cq.Workplane("XY").circle(tower_r).extrude(tower_h)
      tower = tower.translate((tx, ty, 0))
      # Crenellations (battlements) on top
      for j in range(num_merlons):
          angle = j * 360.0 / num_merlons
          merlon = (cq.Workplane("XY")
            .transformed(offset=(tx + tower_r*0.7*math.cos(math.radians(angle)),
                                 ty + tower_r*0.7*math.sin(math.radians(angle)),
                                 tower_h))
            .box(merlon_w, merlon_w, merlon_h))
          tower = tower.union(merlon)
      towers = towers.union(tower)
  # Curtain walls between towers
  wall_front = (cq.Workplane("XY")
    .transformed(offset=(0, keep_d/2, wall_h/2))
    .box(keep_w, wall_t, wall_h))
  towers = towers.union(wall_front)
  # Gate arch (cut from front wall)
  gate = (cq.Workplane("XZ")
    .transformed(offset=(0, keep_d/2, gate_h/2))
    .rect(gate_w, gate_h).extrude(wall_t*2))
  arch_top = (cq.Workplane("XY")
    .transformed(offset=(0, keep_d/2, gate_h))
    .cylinder(wall_t*2, gate_w/2))
  gate_cut = gate.union(arch_top.rotate((0,0,0),(1,0,0),90))
  result = towers.cut(gate_cut)

■ CLASSICAL COLUMN (revolution profile + fluting):
  # Build column profile on XZ plane
  col_profile = (cq.Workplane("XZ")
    .moveTo(0, 0)
    .lineTo(plinth_r, 0)              # Plinth base
    .lineTo(plinth_r, plinth_h)       # Plinth top
    .lineTo(base_r, plinth_h)         # Base molding start
    .lineTo(base_r, plinth_h+base_h)  # Base top
    .lineTo(shaft_r_bot, plinth_h+base_h+2)  # Shaft start
    .lineTo(shaft_r_top, plinth_h+base_h+shaft_h) # Shaft top (entasis taper)
    .lineTo(cap_r, plinth_h+base_h+shaft_h+2)  # Capital start
    .lineTo(cap_r, plinth_h+base_h+shaft_h+cap_h) # Capital top
    .lineTo(0, plinth_h+base_h+shaft_h+cap_h)
    .close()
    .revolve(360, (0,0,0), (0,1,0)))
  # Add fluting (vertical grooves)
  for i in range(num_flutes):
      angle = i * 360.0 / num_flutes
      rad = math.radians(angle)
      fx = (shaft_r_bot + 2) * math.cos(rad)
      fy = (shaft_r_bot + 2) * math.sin(rad)
      flute = (cq.Workplane("XY")
        .transformed(offset=(fx, fy, plinth_h+base_h+2))
        .circle(flute_r).extrude(shaft_h - 4))
      col_profile = col_profile.cut(flute)
  result = col_profile

■ ARCH / BRIDGE (sweep or boolean):
  # Roman arch: semicircular sweep
  arch_path = (cq.Workplane("XZ")
    .moveTo(-span/2, 0)
    .threePointArc((0, rise), (span/2, 0)))
  arch_body = (cq.Workplane("XY")
    .rect(arch_width, arch_depth)
    .sweep(arch_path))
  # Abutments (vertical supports)
  left_pier = cq.Workplane("XY").box(pier_w, arch_depth, pier_h)
  left_pier = left_pier.translate((-span/2 - pier_w/2, 0, pier_h/2))
  right_pier = cq.Workplane("XY").box(pier_w, arch_depth, pier_h)
  right_pier = right_pier.translate((span/2 + pier_w/2, 0, pier_h/2))
  result = arch_body.union(left_pier).union(right_pier)

■ LIGHTHOUSE (tapered cylinder + gallery + lantern):
  # Tapered tower: loft between circles
  tower = (cq.Workplane("XY")
    .circle(base_r)
    .workplane(offset=tower_h)
    .circle(top_r)
    .loft())
  # Gallery platform (observation deck ring)
  gallery = (cq.Workplane("XY")
    .transformed(offset=(0, 0, tower_h))
    .circle(gallery_r).circle(top_r - wall_t)
    .extrude(gallery_h))
  # Railing posts around gallery
  for i in range(railing_count):
      angle = i * 360.0 / railing_count
      rad = math.radians(angle)
      post = cq.Workplane("XY").cylinder(railing_h, railing_r)
      post = post.translate((gallery_r*0.9*math.cos(rad), gallery_r*0.9*math.sin(rad), tower_h+gallery_h))
      gallery = gallery.union(post)
  # Lantern room (glass housing)
  lantern = (cq.Workplane("XY")
    .transformed(offset=(0, 0, tower_h + gallery_h))
    .polygon(8, lantern_r*2).extrude(lantern_h))
  # Dome cap
  dome = (cq.Workplane("XY")
    .transformed(offset=(0, 0, tower_h + gallery_h + lantern_h))
    .sphere(lantern_r))
  result = tower.union(gallery).union(lantern).union(dome)

■ PYRAMID (with internal chamber option):
  # Simple pyramid: loft from square base to point
  pyramid = (cq.Workplane("XY")
    .rect(base_side, base_side)
    .workplane(offset=pyramid_h)
    .rect(tip_size, tip_size)   # Small square at top (flat tip)
    .loft())
  # Optional: stepped pyramid (stack of decreasing platforms)
  # for i in range(num_steps):
  #     step = cq.Workplane("XY").transformed(offset=(0,0,i*step_h))
  #         .rect(base_side - i*step_inset*2, base_side - i*step_inset*2).extrude(step_h)
  #     pyramid = pyramid.union(step)  # or start from scratch
  result = pyramid

■ DOME / CUPOLA (half-sphere on drum):
  # Cylindrical drum
  drum = cq.Workplane("XY").circle(dome_r).extrude(drum_h)
  drum = drum.cut(cq.Workplane("XY").circle(dome_r - wall_t).extrude(drum_h))
  # Hemispherical dome
  full_sphere = cq.Workplane("XY").sphere(dome_r)
  half_sphere = full_sphere.cut(
    cq.Workplane("XY").transformed(offset=(0,0,-dome_r)).box(dome_r*3, dome_r*3, dome_r*2))
  # Hollow interior
  inner_sphere = cq.Workplane("XY").sphere(dome_r - wall_t)
  inner_half = inner_sphere.cut(
    cq.Workplane("XY").transformed(offset=(0,0,-dome_r)).box(dome_r*3, dome_r*3, dome_r*2))
  dome_shell = half_sphere.cut(inner_half)
  dome_shell = dome_shell.translate((0, 0, drum_h))
  # Lantern/oculus on top
  oculus = cq.Workplane("XY").transformed(offset=(0,0,drum_h+dome_r*0.85)).circle(oculus_r).extrude(oculus_h)
  result = drum.union(dome_shell).union(oculus)

═══════════════════════════════════════════════════════════════════════════════
HANDLING DETAILED USER INSTRUCTIONS
═══════════════════════════════════════════════════════════════════════════════

When the user gives a detailed description:

1. **PARSE every noun as a FEATURE** — "three pen slots" = 3 cylindrical cuts,
   "ventilation grille" = array of rectangular cuts, "cable channel" = groove.

2. **PARSE every adjective as a PARAMETER** — "rounded corners" = fillet,
   "thin walls" = wall_thickness=1.5, "angled surface" = rotation.

3. **PARSE every dimension literally** — "120mm wide" = width=120.0.

4. **PARSE relationships** — "centered on the top face" = .faces(">Z").workplane().center(0,0),
   "offset 20mm from the edge" = .center(L/2 - 20, 0).

5. **If the user specifies a count**, use a loop or pushPoints:
   "6 holes evenly spaced" → .polarArray(radius, 0, 360, 6).hole(d)
   "5 slots across the top" → for i in range(5): ... cut slot ...

6. **If the user specifies an arrangement**, follow it exactly:
   "in a 3×2 grid" → .rarray(spacing_x, spacing_y, 3, 2)
   "along the left edge" → position each feature at x = -L/2 + offset

═══════════════════════════════════════════════════════════════════════════════
PARAMETRIC EXCELLENCE
═══════════════════════════════════════════════════════════════════════════════

1. **Every measurement → named parameter** with realistic default, min, max, unit
2. **Derived values computed from parameters:**
     inner_width = width - 2 * wall_thickness
     safe_fillet = min(corner_radius, min(length, width, height) * 0.15)
3. **Guard ALL fillets and shells:**
     fillet_r = min(corner_radius, min(length, width) * 0.15)  # 0.10 if any dim < 20mm
     shell_t = min(wall_thickness, min(length, width, height) * 0.45)
4. **Realistic defaults** — consult the dimension reference table above
5. **Provide 10-20 parameters for complex products**, including:
   - Overall dimensions (length, width, height)
   - Wall/material thickness
   - Corner/edge radii
   - Feature dimensions (hole_diameter, slot_width, slot_depth)
   - Feature positions (hole_offset_x, slot_spacing)
   - Counts (num_slots, num_holes, num_teeth)
   - Functional (tilt_angle, lip_height, cable_hole_diameter)
6. **snake_case names**, units always "mm" (or "degrees" for angles)

═══════════════════════════════════════════════════════════════════════════════
CODE STRUCTURE (MANDATORY)
═══════════════════════════════════════════════════════════════════════════════

import cadquery as cq
import math
import cq_warehouse.extensions  # Always include when using fasteners/bearings

# ── Parameters ──────────────────────────────────
body_length = 150.0
body_width = 75.0
body_height = 40.0
wall_thickness = 2.5
corner_radius = 6.0
# ... more feature-specific parameters

# ── Derived / guarded dimensions ────────────────
safe_fillet = min(corner_radius, min(body_length, body_width) * 0.15)  # use 0.10 if any dim < 20mm
inner_length = body_length - 2 * wall_thickness
safe_shell = min(wall_thickness, min(body_length, body_width, body_height) * 0.45)

# ── Build geometry step by step ─────────────────
body = cq.Workplane("XY").box(body_length, body_width, body_height)
body = body.edges("|Z").fillet(safe_fillet)
body = body.faces(">Z").shell(-safe_shell)

# ── Add features using box() + translate() ──────
# Feature on FRONT wall (-Y): one coord is -body_width/2
port_w = 12.0
port_h = 6.0
port_cutter = cq.Workplane("XY").box(port_w, wall_thickness * 3, port_h)
port_cutter = port_cutter.translate((0, -body_width / 2, body_height * 0.25))
body = body.cut(port_cutter)

# Feature on LEFT wall (-X): one coord is -body_length/2
btn_w = 3.0
btn_h = 12.0
btn_cutter = cq.Workplane("XY").box(wall_thickness * 3, btn_w, btn_h)
btn_cutter = btn_cutter.translate((-body_length / 2, 0, body_height * 0.6))
body = body.cut(btn_cutter)

# ── Final result ────────────────────────────────
result = body  # MUST be cq.Workplane

═══════════════════════════════════════════════════════════════════════════════
UNIVERSAL PRODUCT STRATEGY — FOR ANY PRODUCT TYPE
═══════════════════════════════════════════════════════════════════════════════

If the requested product does NOT match any known category above, follow this
universal decision tree to produce a professional model:

1. IDENTIFY THE FORM FACTOR:
   □ Box-like (case, container, housing) → Start with .box() + .shell()
   □ Cylindrical (bottle, can, tube, knob) → Start with .circle().extrude() or .revolve()
   □ Flat/plate (board, bracket, panel) → Start with .rect().extrude(thin_height)
   □ Sculptural/organic (figurine, trophy, toy) → Start with loft between cross-sections
   □ Profile-based (channel, rail, beam) → Start with sketch profile + .extrude(length)
   □ Compound (multi-part assembly) → Build parts separately, combine with .union()

2. UNIVERSAL DETAIL RULES (apply to ANY product):
   □ Add fillets to ALL external edges (min 0.5mm, max 15% of smallest dimension)
   □ Add at least 3 functional features (holes, slots, cutouts, bosses)
   □ Add at least 2 surface treatments (grooves, panel lines, texture)
   □ Add bottom features if product sits on a surface (feet, pads, non-slip)
   □ Wall thickness should be realistic (1.5-4mm for plastic, 2-8mm for metal)
   □ No featureless faces larger than 40mm × 40mm

3. ORGANIC / SCULPTURAL SHAPES:
   □ Build from lofted cross-sections (ellipses at varying heights)
   □ Use .union() to attach limbs/protrusions built from swept circles
   □ Carve surface detail with shallow .cut() operations (depth 0.5-2mm)
   □ Smooth transitions: fillet union joints with r = min(3, feature_size * 0.2)
   □ For symmetric shapes: build half, then mirror
   □ AVOID: complex splines with >6 control points (crash risk)

4. THIN-WALLED / HOLLOW SHAPES:
   □ Use .shell(-thickness) on simple bodies; thickness < 45% of smallest dim
   □ If shell fails: manually cut interior with slightly-smaller body
   □ Add ribs for structural rigidity (rib_thickness = wall * 0.8, spacing = 15-25mm)
   □ Add lip/rim at openings (1-2mm raised edge)
   □ Draft angle 1-3° on tall walls (use .transformed(rotate=(...)) for tapered extrude)

5. COMPOUND CURVED SURFACES:
   □ Approximate double-curvature with segmented lofts (3-5 cross-sections)
   □ Use .ellipse() for oval cross-sections, not splines
   □ Blend shapes via .fillet() on union joints instead of complex surface modeling
   □ For domes: use half-sphere .sphere(r).cut() or stepped cylinder approximation

6. FEATURE PLACEMENT INTELLIGENCE:
   □ Controls/buttons → front or top, within thumb reach zone
   □ Ports/connectors → bottom or back edges
   □ Vents/cooling → sides or bottom, never where hands grip
   □ Labels/logos → front face center, or bottom for regulatory

═══════════════════════════════════════════════════════════════════════════════
FINAL CHECKLIST
═══════════════════════════════════════════════════════════════════════════════

✓ Output is RAW JSON (no markdown fences, no commentary)
✓ Code starts with "import cadquery as cq" and "import math"
✓ If using fasteners/bearings: "import cq_warehouse.extensions" included
✓ ALL numeric literals are named parameters
✓ Every parameter has realistic default, min, max, unit
✓ Fillet/shell values are GUARDED with min()
✓ Selectors are ALWAYS explicit (">Z", "|Z", etc.)
✓ 2D sketches are .close()'d before .extrude()
✓ Complex geometry is built step-by-step with intermediate variables
✓ 'result' is defined as a cq.Workplane
✓ Design includes REAL functional features (not just a box)
✓ DETAIL COMPLETENESS: 4+ cutouts/openings minimum (ports, vents, holes, slots)
✓ DETAIL COMPLETENESS: 3+ surface treatments (fillets, chamfers, grooves, bevels)
✓ DETAIL COMPLETENESS: 2+ functional sub-features (feet, ribs, bosses, lips)
✓ DETAIL COMPLETENESS: No featureless faces — every visible surface has appropriate treatment
✓ DETAIL COMPLETENESS: Product-specific checklist items addressed (see MANDATORY DETAIL section)
✓ DETAIL COMPLETENESS: Bottom face has feet/pads + label recess (unless floating/wall-mounted)
✓ DETAIL COMPLETENESS: At least 1 decorative element (logo recess, panel line, text, or pattern)
✓ MICRO-DETAILS: 2+ patterns from the MICRO-DETAIL section applied (feet, vents, lines, texture)
✓ EDGE TREATMENT: Fillets on ALL external vertical edges
✓ EDGE TREATMENT: Transitions between joined features are filleted/chamfered
✓ Every detail from the user's prompt is addressed
✓ No os/sys/subprocess/eval/exec/__import__/open calls
✓ When user asks for engineering parts, use cq_warehouse classes
✓ simple=True for fasteners unless user specifically wants thread detail
✓ POSITIONING: Every feature coordinate is derived from body dimension variables
✓ POSITIONING: Wall features use ±body_dim/2 for the wall coordinate
✓ POSITIONING: Cutout depth is wall*3 or more
✓ POSITIONING: No feature uses .transformed(offset=...) on XZ/YZ workplanes — use primitive+translate() instead
✓ SHAPE VARIETY: At least 30% of cutouts use .cylinder() or .slot2D() — not all .box()
✓ REALISTIC BODY: Round products use .revolve()+.spline(), NOT .box()
✓ REALISTIC BODY: Organic profiles use .spline() for curves, NOT chains of .lineTo()
✓ REALISTIC BODY: Handles/rails use .sweep() with curved path (.threePointArc or .spline)
✓ REALISTIC BODY: Body transitions use .loft() between cross-sections, not stacked boxes
✓ POSITIONING: Z coordinates are between 0 and body_height
✓ POSITIONING: Features make physical sense (port on bottom edge, buttons on sides, camera on back)
✓ ROBUSTNESS: All fillets wrapped in try/except or guarded with min()
✓ ROBUSTNESS: No .extrude(0) or zero-dimension operations
✓ ROBUSTNESS: Variable 'result' is explicitly assigned as final line
✓ UNIVERSALITY: If product doesn't match a known category, follow Universal Product Strategy section
✓ UNIVERSALITY: Organic shapes use loft + sweep, not impossible splines
✓ UNIVERSALITY: Thin-walled parts have ribs or structural support
✓ ⚠️ PRE-FLIGHT AUDIT: ALL checks in the PRE-FLIGHT AUDIT section PASSED

═══════════════════════════════════════════════════════════════════════════════
RESPOND WITH RAW JSON ONLY
═══════════════════════════════════════════════════════════════════════════════"""

    def _get_chat_system_prompt(self) -> str:
        """System prompt for conversational design refinement"""
        return """You are a friendly CAD engineering assistant. Help users design parts through conversation.

WORKFLOW:
1. Ask clarifying questions about dimensions, features, materials
2. Build up the design JSON incrementally
3. When design is complete, set shouldBuild=true

RESPONSE FORMAT (JSON):
{
  "message": "Your conversational response to the user",
  "updatedDesign": {...},  // Updated design JSON or null
  "shouldBuild": false     // Set true when ready to generate CAD
}

Be helpful, ask one question at a time, and guide beginners."""

    def _format_build_message(
        self,
        prompt: str,
        previous_design: Optional[Dict[str, Any]],
        complexity: str = "standard"
    ) -> str:
        """Format user prompt for single-shot generation with structured guidance.
        Searches the product library for matching real-world specs and injects them.
        Adapts detail expectations based on detected complexity."""
        
        # Complexity-specific instructions
        complexity_boost = ""
        if complexity == "high":
            complexity_boost = """
═══════════════════════════════════════════════════════════════
🔥 HIGH COMPLEXITY DETECTED — PROFESSIONAL MODE
═══════════════════════════════════════════════════════════════
This prompt requires MAXIMUM DETAIL and PROFESSIONAL quality:
• Include 15-25 parameters covering every dimension
• Add EVERY sub-feature: ribs, bosses, chamfers, fillets, channels, lips, slots
• Use advanced techniques: multi-section lofts, sweeps, compound booleans
• Break geometry into 10+ named intermediate variables
• Add structural features: gussets, ribs, draft angles where appropriate
• Edge treatment on EVERY visible edge — no sharp corners on final product
• Think like a senior mechanical engineer designing for production
• If the product has internal structure, model it (ribs, walls, channels)
• Add manufacturing-aware features: draft angles, fillet radii ≥0.5mm, uniform wall thickness

PROFESSIONAL DETAIL HIERARCHY — implement ALL THREE levels:
  Level 1 (PRIMARY): Main body shape, major cutouts, functional openings
  Level 2 (SECONDARY): Mounting features, internal structure, assembly features
    → screw bosses, PCB standoffs, rib walls, cable channels, snap clips
  Level 3 (TERTIARY): Micro-details that make it look REAL
    → panel lines, grip texture grooves, LED indicator holes, logo recess,
       serial number label area, rubber foot recesses, parting line groove,
       drain holes, chamfered mating edges, alignment marks

SURFACE FINISH EXPECTATIONS for professional mode:
  • EVERY external edge has a fillet (R0.5-R5mm depending on function)
  • BOTTOM face has 4+ rubber feet AND a label recess
  • At least ONE face has a text/logo element
  • At least ONE face has an array pattern (vents, speaker holes, etc.)
  • Internal ribs if any span exceeds 40mm without support
  • Panel lines or parting lines separating visual zones
"""
        elif complexity == "medium":
            complexity_boost = """
═══════════════════════════════════════════════════════════════
📐 MEDIUM COMPLEXITY — DETAILED MODE
═══════════════════════════════════════════════════════════════
This prompt requires solid detail and completeness:
• Include 10-18 parameters
• Add all functional features: ports, holes, mounting points, lips
• Edge treatment on all visible edges
• Use intermediate variables for clean code
• Every face should have appropriate treatment (not blank)

EXPECTED DETAILS for medium complexity:
  • ALL functional cutouts present (ports, buttons, vents, slots)
  • Rubber feet or anti-slip features on bottom
  • At least 1 array/pattern feature (ventilation grid, hole pattern)
  • Label area or logo recess on one face
  • Fillets on ALL external vertical edges
  • Internal structure if it's a shell (at least cross ribs)
"""
        
        # Search the product library for matching reference data
        product_ref = product_lookup(prompt)
        
        if previous_design:
            # CRITICAL: Log what we received to debug modification flow
            print(f"\n{'='*60}")
            print(f"🔧 MODIFICATION DETECTED")
            print(f"{'='*60}")
            print(f"Previous design keys: {list(previous_design.keys())}")
            print(f"Has 'code': {bool(previous_design.get('code', ''))}")
            print(f"Code length: {len(previous_design.get('code', ''))} characters")
            print(f"Has 'parameters': {bool(previous_design.get('parameters', []))}")
            print(f"Param count: {len(previous_design.get('parameters', []))}")
            print(f"{'='*60}\n")
            
            ref_block = f"\n\n{product_ref}\n" if product_ref else ""
            
            # Extract the previous CadQuery code if available
            previous_code = previous_design.get("code", "")
            previous_params = previous_design.get("parameters", [])
            previous_explanation = previous_design.get("explanation", {})
            
            # CRITICAL: If no code, this is NOT really a modification
            if not previous_code:
                print(f"⚠️ WARNING: Modification requested but no previous code found!")
                print(f"⚠️ Will treat as NEW BUILD instead")
                # Fall through to new build path below
            else:
                code_block = f"""

══════════════════════════════════════════════════════════════
PREVIOUS CADQUERY CODE — THIS IS YOUR STARTING POINT
══════════════════════════════════════════════════════════════
Copy this code EXACTLY, then INSERT your modifications into it.
Do NOT rewrite from scratch. Do NOT delete any existing lines
unless the user specifically asked to remove something.

```python
{previous_code}
```"""
                
                params_block = ""
                if previous_params:
                    params_block = f"""

CURRENT PARAMETERS (keep ALL of these, add new ones for new features):
{json.dumps(previous_params, indent=2)}"""
                
                return f"""MODIFICATION REQUEST — Edit the existing code, do NOT rewrite from scratch.
{ref_block}
{code_block}
{params_block}

USER'S CHANGE REQUEST:
{prompt}

MODIFICATION RULES:
1. COPY the previous code as your base. INSERT new lines where needed. Do NOT delete existing lines.
2. Your output line count = previous line count + new lines (5-40 extra). NEVER fewer lines.
3. ALL existing parameters, .cut() operations, .fillet() calls, and variable names MUST remain.
4. ADD new parameters for new features — append to the existing parameters list.
5. Position new features using existing dimension variables (body_x/2, body_height, etc.) — never hardcode coordinates.
6. Match cutout shapes to real features: .cylinder() for round holes, .slot2D() for rounded slots, .box() for rectangular openings. Cutter depth = wall*3.
7. Update explanation.design_intent to describe what was ADDED/CHANGED.

VERIFICATION before returning:
- First 3 lines of your code match previous code exactly (same imports, same order)
- All previous .cut() and .fillet() operations are present in your code
- Previous param count = N → your param count >= N
- Variable names match (case/body/frame = same as previous)

Return the COMPLETE updated design JSON with ALL parameters (old + new) and the FULL code."""

        # New build path (also used as fallthrough when previous_design has no code)
        ref_block = f"\n\n{product_ref}\n" if product_ref else ""
        return f"""PRODUCT REQUEST:
{prompt}{ref_block}
{complexity_boost}

INSTRUCTIONS:
1. Implement EVERY feature the user mentioned — do not skip or simplify any.
   If user says "drone with camera mount and LED lights" → code MUST have drone + camera mount + LED lights.
   If user gives a dimension "200mm tall" → use exactly 200.0 for the height parameter.
   If user specifies a location "USB on the left" → place it on the left wall (x = -body_x/2).

2. If a REAL-WORLD PRODUCT REFERENCE is provided above, use those dimensions and features.
   If VISUAL & CONSTRUCTION KNOWLEDGE is provided, follow the BUILD STRATEGY and POSITION MAP.

3. BUILD A REAL PRODUCT, NOT A TOY VERSION:
   • Select the MANDATORY STRATEGY from the strategy table for this product category.
   • Use .spline() for organic profiles — NEVER use .lineTo() chains for curved surfaces.
   • Use .revolve() + .spline() for round products (mugs, bottles, vases) — MANDATORY.
   • Use .loft() for body transitions between cross-sections.
   • Use .sweep() with .threePointArc() path for handles — NEVER straight-line sweep paths.
   • Build curvature INTO the profile (spline, arc) — don't rely only on fillet afterthoughts.
   • If the product is round/cylindrical → MUST use revolve or cylinder, NEVER box.
   • If the product is organic/ergonomic → MUST use multi-section loft, NEVER box.

4. AXIS ASSIGNMENT (mandatory before writing .box()):
   - Z = vertical/upward dimension (tallest for upright products, thickness for flat)
   - Write the axis assignment comment and 6 coordinate variables (left_x, right_x, front_y, back_y, bottom_z, top_z)
   - MAIN body: .box(X, Y, Z, centered=(True, True, False)). CUTTER boxes: NO centered parameter.
   - centered= is ONLY for .box() — NEVER on .extrude(), .rect(), .circle()

5. Build with COMPLETE DETAIL — a real manufactured product, not a simplified look-alike:
   • 4+ cutouts minimum (ports, holes, vents, slots, windows, doors)
   • Fillets on ALL visible edges (wrapped in try/except)
   • Build body curvature with .spline() and .loft() — not just fillet afterthoughts
   • Bottom face: feet/pads + label recess
   • Every face should have at least one feature — no blank faces
   • For known product types, include ALL standard features:
     - Phone case: USB port, camera cutout, speaker grille, volume/power buttons, screen lip
     - Building: windows on 2+ walls, door with frame, roof, window sills
     - Drone: Match type to request — quadcopter=4 arms+motors+props, hexacopter=6, octocopter=8, tricopter=3+tail servo, camera drone=gimbal+lofted body, VTOL=wings+tail+pusher, mini=ducted frame, delivery=cargo bay, ROV=cage+thrusters, spray=tank+boom. EVERY air drone needs visible MOTORS + PROPELLERS + CANOPY + GEAR. A frame alone is NOT a drone!
     - Electronics: vent slots (6+), port cutouts (3+), mounting bosses, LED holes
     - Controller: button holes, thumbstick holes, grip texture, charging port
   • For curved products (mug, bottle, vase): use .revolve() + .spline() body — NO boxes
   • For ergonomic products (controller, mouse): use multi-section .loft() body — NO boxes

6. Match cutout shapes to real features: .cylinder() for round holes (speakers, LEDs, screws),
   .slot2D() for rounded slots (USB ports, buttons), .box() only for rectangular openings (windows, doors).
   Cutter depth = wall*3. Position with body dimension variables — never hardcode coordinates.

7. Include 10-20 parameters with realistic defaults, min, max, unit.
   Guard fillets: min(r, min(L,W,H) * 0.25). Guard shells: min(t, min(L,W,H) * 0.45).

SPATIAL ORIENTATION CROSS-CHECK — verify before returning:
  • Z-axis = vertical/up. The TALLEST real-world dimension maps to Z (or thickness for flat products).
  • Bottom face at Z=0 (centered=(True,True,False) on main body).
  • Features on correct faces: USB/ports on <Y or >Y, buttons on <X or >X, screen on >Z.
  • Coordinate signs: left_x < 0 < right_x, front_y < 0 < back_y, bottom_z = 0.
  • Every .workplaneFromTagged()/.faces() selector matches the intended physical face.

Return the complete design JSON now."""
    
    def _format_chat_messages(
        self,
        message: str,
        history: List[Dict[str, str]],
        current_design: Optional[Dict[str, Any]]
    ) -> List[Dict[str, str]]:
        """Format conversation history for Claude"""
        messages = []
        
        # Add conversation history
        for msg in history:
            messages.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        
        # Add current message with design context
        content = message
        if current_design:
            content = f"Current design state:\n{json.dumps(current_design, indent=2)}\n\nUser: {message}"
        
        messages.append({"role": "user", "content": content})
        return messages
    
    def _extract_json_from_response(self, text: str) -> Dict[str, Any]:
        """Extract JSON from Claude's response with robust fallback parsing"""
        import re
        
        original_text = text
        
        # Try 1: Remove markdown code blocks if present
        if "```json" in text:
            text = text.split("```json")[1].split("```")[0]
        elif "```" in text:
            text = text.split("```")[1].split("```")[0]
        
        try:
            return json.loads(text.strip())
        except json.JSONDecodeError:
            pass
        
        # Try 2: Find JSON object with regex (first { to last })
        match = re.search(r'(\{[\s\S]*\})', original_text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Try 3: Claude may have refused — raise a descriptive error
        preview = original_text[:300].strip()
        raise ValueError(
            f"Claude did not return valid JSON. Response preview: {preview}"
        )
    
    def _parse_chat_response(
        self,
        response: str,
        current_design: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Parse conversational response for design updates"""
        try:
            # Try to parse as JSON response format
            parsed = json.loads(response)
            return {
                "message": parsed.get("message", response),
                "updatedDesign": parsed.get("updatedDesign"),
                "shouldBuild": parsed.get("shouldBuild", False)
            }
        except json.JSONDecodeError:
            # Fallback: treat as plain text response
            return {
                "message": response,
                "updatedDesign": current_design,
                "shouldBuild": False
            }

# Singleton instance
claude_service = ClaudeService()
