"""Phase 32 — Feature Positioning fix validation"""
import sys
sys.path.insert(0, 'Backend')

from services.product_visual_knowledge import (
    CATEGORY_VISUAL_KNOWLEDGE,
    PRODUCT_VISUAL_OVERRIDES,
    get_visual_knowledge,
    format_visual_knowledge,
)
from services.claude_service import claude_service

errors = []

# 1. Check all categories have required fields
cats = list(CATEGORY_VISUAL_KNOWLEDGE.keys())
print(f"Categories: {len(cats)}")
for c in cats:
    vk = CATEGORY_VISUAL_KNOWLEDGE[c]
    for key in ("visual_profile", "build_strategy", "recognition_features"):
        if key not in vk:
            errors.append(f"Category '{c}' missing '{key}'")

# 2. Check which categories have position_map
with_pm = [c for c in cats if "position_map" in CATEGORY_VISUAL_KNOWLEDGE[c]]
without_pm = [c for c in cats if "position_map" not in CATEGORY_VISUAL_KNOWLEDGE[c]]
print(f"Categories WITH position_map ({len(with_pm)}): {with_pm}")
print(f"Categories WITHOUT position_map ({len(without_pm)}): {without_pm}")

# 3. Check product overrides are valid
prods = list(PRODUCT_VISUAL_OVERRIDES.keys())
print(f"Product overrides: {len(prods)}")
for p in prods:
    vk = PRODUCT_VISUAL_OVERRIDES[p]
    if not isinstance(vk, dict):
        errors.append(f"Product override '{p}' is not a dict")

# 4. Test format_visual_knowledge includes position_map
test_cases = [
    ("Apple iPhone 16 Pro Max", "Smartphones"),
    ("Medieval Castle Model", "Architecture"),
    ("Raspberry Pi 4/5 Case", "Enclosures"),
    ("Sony DualSense Controller (PS5)", "Gaming"),
    ("Apple Watch Ultra 2", "Wearables"),
    ("Generic Phone Case", "Phone Cases"),
    ("Generic Laptop", "Laptops"),
    ("Generic Tablet", "Tablets"),
]
for name, cat in test_cases:
    result = format_visual_knowledge(name, cat)
    if "POSITION MAP" not in result:
        errors.append(f"format_visual_knowledge('{name}', '{cat}') missing POSITION MAP")
    if "ORIENTATION" not in result:
        errors.append(f"format_visual_knowledge('{name}', '{cat}') missing ORIENTATION in build strategy")
    print(f"  ✓ {name} ({cat}): pos_map={'YES' if 'POSITION MAP' in result else 'NO'}, orient={'YES' if 'ORIENTATION' in result else 'NO'}")

# 5. Test system prompt has orientation convention
prompt = claude_service._get_design_system_prompt()
print(f"\nSystem prompt length: {len(prompt)} chars")
checks = {
    "MASTER SPATIAL ORIENTATION": "Master orientation convention",
    "CUTTER ORIENTATION EXAMPLES": "Cutter orientation examples",
    "FEATURE PLACEMENT RECIPE": "Feature placement recipe",
    "PRODUCT-TYPE ORIENTATION RULES": "Product-type orientation rules",
}
for needle, label in checks.items():
    if needle not in prompt:
        errors.append(f"System prompt missing '{label}'")
    else:
        print(f"  ✓ System prompt has: {label}")

# 6. Test build message includes position data
msg = claude_service._format_build_message("iphone 16 pro max case", None, "high")
msg_checks = {
    "POSITION MAP": "Position map in build message",
    "ORIENTATION": "Orientation in build message",
    "<Z": "Bottom face reference (<Z)",
    ">Y": "Back face reference (>Y)",
    "<X": "Left face reference (<X)",
    "SPATIAL ORIENTATION CROSS-CHECK": "Spatial orientation cross-check (in build msg)",
}
for needle, label in msg_checks.items():
    if needle not in msg:
        errors.append(f"Build message missing '{label}'")
    else:
        print(f"  ✓ Build message has: {label}")

# 7. Test modification message still works
mod_msg = claude_service._format_build_message(
    "add a lanyard hole",
    {"code": "import cadquery as cq\nresult = cq.Workplane('XY').box(10,10,10)", "parameters": []},
    "standard"
)
if "MODIFICATION REQUEST" not in mod_msg:
    errors.append("Modification message missing MODIFICATION REQUEST header")
else:
    print("  ✓ Modification flow still works")

# Summary
print("\n" + "=" * 60)
if errors:
    print(f"❌ FAILED — {len(errors)} error(s):")
    for e in errors:
        print(f"  • {e}")
else:
    print("✅ ALL CHECKS PASSED — No bugs or errors found")
print("=" * 60)
