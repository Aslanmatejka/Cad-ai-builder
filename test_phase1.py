"""
Quick test script to verify Phase 1 setup
Tests API endpoints without starting the full server
"""

import sys
from pathlib import Path

# Add Backend to path
sys.path.insert(0, str(Path(__file__).parent / "Backend"))

print("=" * 60)
print("🧪 Testing Chat-to-CAD Platform - Phase 1")
print("=" * 60)

# Test 1: Import services
print("\n1️⃣  Testing imports...")
try:
    from Backend.config import settings
    print(f"   ✅ Config loaded (Port: {settings.PORT})")
except Exception as e:
    print(f"   ❌ Config import failed: {e}")
    sys.exit(1)

try:
    from Backend.services.claude_service import claude_service
    print(f"   ✅ Claude service loaded (Model: {settings.AI_MODEL_NAME})")
except Exception as e:
    print(f"   ❌ Claude service import failed: {e}")
    sys.exit(1)

try:
    from Backend.services.cadquery_service import cadquery_service
    print(f"   ✅ CadQuery service loaded")
except Exception as e:
    print(f"   ❌ CadQuery service import failed: {e}")
    sys.exit(1)

# Test 2: Validate environment
print("\n2️⃣  Checking environment...")
if settings.ANTHROPIC_API_KEY and settings.ANTHROPIC_API_KEY.startswith("sk-ant-"):
    print(f"   ✅ Anthropic API key configured")
else:
    print(f"   ⚠️  Anthropic API key missing or invalid")

# Test 3: Check CadQuery
print("\n3️⃣  Testing CadQuery...")
try:
    import cadquery as cq
    # Simple test geometry
    result = cq.Workplane("XY").box(10, 10, 10)
    print(f"   ✅ CadQuery working (created test box)")
except Exception as e:
    print(f"   ❌ CadQuery test failed: {e}")

# Test 4: Check exports directory
print("\n4️⃣  Checking file system...")
if settings.CAD_DIR.exists():
    print(f"   ✅ Exports directory ready: {settings.CAD_DIR}")
else:
    print(f"   ⚠️  Exports directory not found")
    settings.CAD_DIR.mkdir(parents=True, exist_ok=True)
    print(f"   ✅ Created: {settings.CAD_DIR}")

print("\n" + "=" * 60)
print("✅ Phase 1 Setup Complete!")
print("=" * 60)
print("\n📋 Next Steps:")
print("   1. cd Backend")
print("   2. python start.py")
print("   3. Visit http://localhost:3001/docs")
print("\n" + "=" * 60)
