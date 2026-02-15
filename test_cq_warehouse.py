"""Quick test: cq_warehouse parts through parametric_cad_service exec pipeline."""
import sys
sys.path.insert(0, "Backend")

from services.parametric_cad_service import ParametricCADService

svc = ParametricCADService()

def run_test(name, code):
    print(f"{name}...")
    try:
        result = svc._execute_cadquery_code(code, [])
        print(f"  ✅ OK  |  type={type(result).__name__}")
    except Exception as e:
        print(f"  ❌ FAIL: {e}")

# ── Test 1: HexNut ──────────────────────────────────────────
run_test("Test 1 — HexNut (simple)", """
import cadquery as cq
import cq_warehouse.extensions
from cq_warehouse.fastener import HexNut

nut = HexNut(size="M8-1.25", fastener_type="iso4032", simple=True)
result = nut.cq_object
""")

# ── Test 2: SocketHeadCapScrew ──────────────────────────────
run_test("Test 2 — SocketHeadCapScrew M6x20", """
import cadquery as cq
import cq_warehouse.extensions
from cq_warehouse.fastener import SocketHeadCapScrew

screw = SocketHeadCapScrew(size="M6-1", fastener_type="iso4762", length=20, simple=True)
result = screw.cq_object
""")

# ── Test 3: Bearing ─────────────────────────────────────────
run_test("Test 3 — SingleRowDeepGrooveBallBearing", """
import cadquery as cq
import cq_warehouse.extensions
from cq_warehouse.bearing import SingleRowDeepGrooveBallBearing

bearing = SingleRowDeepGrooveBallBearing(size="M8-22-7", bearing_type="SKT")
result = bearing.cq_object
""")

# ── Test 4: Plate with clearance holes (fastener INSTANCE) ──
run_test("Test 4 — Plate with clearance holes", """
import cadquery as cq
import cq_warehouse.extensions
from cq_warehouse.fastener import SocketHeadCapScrew

screw = SocketHeadCapScrew(size="M6-1", fastener_type="iso4762", length=20, simple=True)
plate = (
    cq.Workplane("XY")
    .box(60, 60, 5)
    .faces(">Z")
    .workplane()
    .rect(40, 40, forConstruction=True)
    .vertices()
    .clearanceHole(fastener=screw, fit="Normal", counterSunk=False)
)
result = plate
""")

# ── Test 5: Combined plate with 4 mounting holes ───────────
run_test("Test 5 — Plate with 4 mounting holes", """
import cadquery as cq
import cq_warehouse.extensions
from cq_warehouse.fastener import SocketHeadCapScrew

screw = SocketHeadCapScrew(size="M4-0.7", fastener_type="iso4762", length=16, simple=True)
plate = (
    cq.Workplane("XY")
    .box(80, 80, 10)
    .faces(">Z")
    .workplane()
    .pushPoints([(25, 25), (-25, 25), (25, -25), (-25, -25)])
    .clearanceHole(fastener=screw, fit="Normal", counterSunk=False)
)
result = plate
""")

# ── Test 6: Sprocket ────────────────────────────────────────
run_test("Test 6 — Sprocket 25T", """
import cadquery as cq
import cq_warehouse.extensions
from cq_warehouse.sprocket import Sprocket

sprocket = Sprocket(
    num_teeth=25,
    chain_pitch=12.7,
    roller_diameter=7.9375,
    clearance=0.1,
    bore_diameter=10,
    num_mount_bolts=4,
    bolt_circle_diameter=30
)
result = sprocket.cq_object
""")

# ── Test 7: IsoThread ──────────────────────────────────────
run_test("Test 7 — IsoThread M10 (simple=False)", """
import cadquery as cq
import cq_warehouse.extensions
from cq_warehouse.thread import IsoThread

thread = IsoThread(
    major_diameter=10,
    pitch=1.5,
    length=10,
    external=True,
    simple=False
)
result = thread.cq_object
""")

print("\n🏁 All tests complete.")
