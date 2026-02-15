import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Canvas, useThree } from '@react-three/fiber';
import { OrbitControls, Grid, PerspectiveCamera, TransformControls } from '@react-three/drei';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader';
import * as THREE from 'three';
import './MultiProductCanvas.css';

// ── Color palette for visual distinction ──
const PRODUCT_COLORS = [
  '#8b9dc3', '#a3c4f3', '#90caf9', '#80deea', '#a5d6a7',
  '#c5e1a5', '#fff59d', '#ffe082', '#ffcc80', '#ef9a9a',
  '#f48fb1', '#ce93d8', '#b39ddb', '#9fa8da', '#81d4fa',
];

function snapValue(val, gridSize) {
  if (!gridSize || gridSize <= 0) return val;
  return Math.round(val / gridSize) * gridSize;
}

function toFixed(val, decimals) {
  return Number(Number(val).toFixed(decimals));
}

function radToDeg(rad) { return Number((rad * 180 / Math.PI).toFixed(2)); }
function degToRad(deg) { return deg * Math.PI / 180; }

// ── Precision Input Row ──
function PrecisionInput({ label, value, onChange, step, min, max, decimals, locked, onToggleLock, color }) {
  const [localValue, setLocalValue] = useState(String(toFixed(value, decimals)));
  const inputRef = useRef();

  useEffect(() => {
    if (document.activeElement !== inputRef.current) {
      setLocalValue(String(toFixed(value, decimals)));
    }
  }, [value, decimals]);

  const commit = (v) => {
    let parsed = parseFloat(v);
    if (isNaN(parsed)) parsed = 0;
    if (min !== undefined) parsed = Math.max(min, parsed);
    if (max !== undefined) parsed = Math.min(max, parsed);
    parsed = toFixed(parsed, decimals);
    setLocalValue(String(parsed));
    onChange(parsed);
  };

  return (
    <div className={`precision-input-row ${locked ? 'locked' : ''}`}>
      <span className="precision-label" style={{ color: color || '#b0b3bc' }}>{label}</span>
      <input
        ref={inputRef}
        type="number"
        className="precision-field"
        value={localValue}
        step={step || 1}
        onChange={(e) => setLocalValue(e.target.value)}
        onBlur={(e) => commit(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter') { commit(e.target.value); e.target.blur(); }
        }}
        disabled={locked}
      />
      {onToggleLock && (
        <button
          className={`axis-lock-btn ${locked ? 'active' : ''}`}
          onClick={onToggleLock}
          title={locked ? `Unlock ${label} axis` : `Lock ${label} axis`}
        >
          {locked ? '🔒' : '🔓'}
        </button>
      )}
    </div>
  );
}

// ── Precision Panel (right sidebar) ──
function PrecisionPanel({ selectedProduct, onTransformChange, decimals, setDecimals, lockedAxes, setLockedAxes, nudgeAmount, setNudgeAmount, boundingBox }) {
  if (!selectedProduct) return null;

  const pos = selectedProduct.position || { x: 0, y: 0, z: 0 };
  const rot = selectedProduct.rotation || { x: 0, y: 0, z: 0 };
  const scl = selectedProduct.scale || { x: 1, y: 1, z: 1 };

  const updatePos = (axis, val) => {
    if (lockedAxes[axis]) return;
    const newPos = { ...pos, [axis]: val };
    onTransformChange(selectedProduct.instanceId, { position: newPos, rotation: rot, scale: scl });
  };

  const updateRot = (axis, degVal) => {
    const newRot = { ...rot, [axis]: degToRad(degVal) };
    onTransformChange(selectedProduct.instanceId, { position: pos, rotation: newRot, scale: scl });
  };

  // Uniform scale handler
  const updateScaleUniform = (axis, val) => {
    const ratio = scl[axis] !== 0 ? val / scl[axis] : 1;
    const newScl = { x: scl.x * ratio, y: scl.y * ratio, z: scl.z * ratio };
    onTransformChange(selectedProduct.instanceId, { position: pos, rotation: rot, scale: newScl });
  };

  const updateScaleAxis = (axis, val) => {
    const newScl = { ...scl, [axis]: val };
    onTransformChange(selectedProduct.instanceId, { position: pos, rotation: rot, scale: newScl });
  };

  const toggleLock = (axis) => {
    setLockedAxes(prev => ({ ...prev, [axis]: !prev[axis] }));
  };

  return (
    <div className="precision-panel">
      <div className="precision-header">
        <h4>📐 Precision Controls</h4>
        <div className="precision-settings">
          <label title="Decimal places">
            <span>Decimals:</span>
            <select value={decimals} onChange={(e) => setDecimals(Number(e.target.value))}>
              <option value={0}>0</option>
              <option value={1}>1</option>
              <option value={2}>2</option>
              <option value={3}>3</option>
            </select>
          </label>
          <label title="Arrow key nudge amount in mm">
            <span>Nudge:</span>
            <select value={nudgeAmount} onChange={(e) => setNudgeAmount(Number(e.target.value))}>
              <option value={0.1}>0.1mm</option>
              <option value={0.5}>0.5mm</option>
              <option value={1}>1mm</option>
              <option value={5}>5mm</option>
              <option value={10}>10mm</option>
              <option value={25}>25mm</option>
            </select>
          </label>
        </div>
      </div>

      <div className="precision-section">
        <div className="precision-section-title">Position (mm)</div>
        <PrecisionInput label="X" value={pos.x} onChange={(v) => updatePos('x', v)} step={1} decimals={decimals} locked={lockedAxes.x} onToggleLock={() => toggleLock('x')} color="#ff6b6b" />
        <PrecisionInput label="Y" value={pos.y} onChange={(v) => updatePos('y', v)} step={1} decimals={decimals} locked={lockedAxes.y} onToggleLock={() => toggleLock('y')} color="#6bff6b" />
        <PrecisionInput label="Z" value={pos.z} onChange={(v) => updatePos('z', v)} step={1} decimals={decimals} locked={lockedAxes.z} onToggleLock={() => toggleLock('z')} color="#6b9fff" />
      </div>

      <div className="precision-section">
        <div className="precision-section-title">Rotation (°)</div>
        <PrecisionInput label="X" value={radToDeg(rot.x)} onChange={(v) => updateRot('x', v)} step={5} min={-360} max={360} decimals={Math.min(decimals, 1)} color="#ff6b6b" />
        <PrecisionInput label="Y" value={radToDeg(rot.y)} onChange={(v) => updateRot('y', v)} step={5} min={-360} max={360} decimals={Math.min(decimals, 1)} color="#6bff6b" />
        <PrecisionInput label="Z" value={radToDeg(rot.z)} onChange={(v) => updateRot('z', v)} step={5} min={-360} max={360} decimals={Math.min(decimals, 1)} color="#6b9fff" />
      </div>

      <div className="precision-section">
        <div className="precision-section-title">Scale</div>
        <PrecisionInput label="X" value={scl.x} onChange={(v) => updateScaleAxis('x', v)} step={0.1} min={0.01} decimals={Math.max(decimals, 2)} color="#ff6b6b" />
        <PrecisionInput label="Y" value={scl.y} onChange={(v) => updateScaleAxis('y', v)} step={0.1} min={0.01} decimals={Math.max(decimals, 2)} color="#6bff6b" />
        <PrecisionInput label="Z" value={scl.z} onChange={(v) => updateScaleAxis('z', v)} step={0.1} min={0.01} decimals={Math.max(decimals, 2)} color="#6b9fff" />
        <button className="uniform-scale-btn" onClick={() => updateScaleUniform('x', 1)} title="Reset scale to 1">↺ Reset Scale</button>
      </div>

      {boundingBox && (
        <div className="precision-section">
          <div className="precision-section-title">Dimensions (mm)</div>
          <div className="dimension-readout">
            <span className="dim-axis" style={{ color: '#ff6b6b' }}>W:</span>
            <span className="dim-value">{toFixed(boundingBox.x * (scl.x || 1), decimals)}</span>
          </div>
          <div className="dimension-readout">
            <span className="dim-axis" style={{ color: '#6bff6b' }}>H:</span>
            <span className="dim-value">{toFixed(boundingBox.y * (scl.y || 1), decimals)}</span>
          </div>
          <div className="dimension-readout">
            <span className="dim-axis" style={{ color: '#6b9fff' }}>D:</span>
            <span className="dim-value">{toFixed(boundingBox.z * (scl.z || 1), decimals)}</span>
          </div>
        </div>
      )}

      <div className="precision-footer">
        <span>↑↓←→ nudge by {nudgeAmount}mm</span>
        <span>Shift+Arrow = 10× nudge</span>
      </div>
    </div>
  );
}

// ── Auto-fit camera to scene bounds ──
function CameraFitter({ products, trigger }) {
  const { camera, scene } = useThree();

  useEffect(() => {
    if (products.length === 0) return;
    const timer = setTimeout(() => {
      const box = new THREE.Box3();
      scene.traverse((obj) => {
        if (obj.isMesh) box.union(new THREE.Box3().setFromObject(obj));
      });
      if (box.isEmpty()) return;
      const center = box.getCenter(new THREE.Vector3());
      const size = box.getSize(new THREE.Vector3());
      const maxDim = Math.max(size.x, size.y, size.z);
      const dist = maxDim * 2.5;
      camera.position.set(center.x + dist * 0.6, center.y + dist * 0.5, center.z + dist * 0.6);
      camera.lookAt(center);
      camera.updateProjectionMatrix();
    }, 300);
    return () => clearTimeout(timer);
  }, [trigger]); // eslint-disable-line react-hooks/exhaustive-deps

  return null;
}

// ── Draggable 3D Model Component ──
function DraggableModel({
  instanceId, url, position, rotation, scale, color,
  wireframe, isSelected, isMultiSelected, onSelect,
  onTransformChange, transformMode, snapGrid, orbitRef, assemblyId,
  onBoundingBox
}) {
  const meshRef = useRef();
  const transformRef = useRef();
  const [geometry, setGeometry] = useState(null);

  useEffect(() => {
    if (!url) return;
    const loader = new STLLoader();
    loader.load(
      url,
      (loadedGeometry) => {
        loadedGeometry.computeBoundingBox();
        const bbox = loadedGeometry.boundingBox;
        const center = bbox.getCenter(new THREE.Vector3());
        const size = bbox.getSize(new THREE.Vector3());
        loadedGeometry.translate(-center.x, -center.y, -center.z);
        setGeometry(loadedGeometry);
        if (onBoundingBox) onBoundingBox(instanceId, { x: size.x, y: size.y, z: size.z });
      },
      undefined,
      (error) => console.error('STL loading error:', error)
    );
  }, [url]); // eslint-disable-line react-hooks/exhaustive-deps

  // Disable orbit controls while dragging transform gizmo
  useEffect(() => {
    const ctrl = transformRef.current;
    if (!ctrl || !orbitRef?.current) return;
    const handler = (e) => {
      if (orbitRef.current) orbitRef.current.enabled = !e.value;
    };
    ctrl.addEventListener('dragging-changed', handler);
    return () => ctrl.removeEventListener('dragging-changed', handler);
  }, [orbitRef, geometry]);

  if (!geometry) return null;

  const highlight = isSelected || isMultiSelected;
  const outlineColor = assemblyId ? '#00ff88' : (isMultiSelected ? '#ff6600' : '#ffcc00');
  const emissiveColor = assemblyId ? '#004422' : (isMultiSelected ? '#442200' : '#443300');

  return (
    <group>
      <mesh
        ref={meshRef}
        geometry={geometry}
        position={[position.x, position.y, position.z]}
        rotation={[rotation.x, rotation.y, rotation.z]}
        scale={[scale.x, scale.y, scale.z]}
        onClick={(e) => {
          e.stopPropagation();
          onSelect(instanceId, e.nativeEvent.ctrlKey || e.nativeEvent.metaKey);
        }}
      >
        <meshStandardMaterial
          color={highlight ? outlineColor : color}
          metalness={0.3}
          roughness={0.4}
          wireframe={wireframe}
          side={THREE.DoubleSide}
          emissive={highlight ? emissiveColor : '#000000'}
          emissiveIntensity={highlight ? 0.4 : 0}
        />
      </mesh>

      {isSelected && meshRef.current && (
        <TransformControls
          ref={transformRef}
          object={meshRef.current}
          mode={transformMode}
          translationSnap={snapGrid > 0 ? snapGrid : null}
          rotationSnap={snapGrid > 0 ? THREE.MathUtils.degToRad(15) : null}
          scaleSnap={snapGrid > 0 ? 0.1 : null}
          onObjectChange={() => {
            if (!meshRef.current) return;
            const p = meshRef.current.position;
            const r = meshRef.current.rotation;
            const s = meshRef.current.scale;
            onTransformChange(instanceId, {
              position: {
                x: snapGrid > 0 ? snapValue(p.x, snapGrid) : p.x,
                y: snapGrid > 0 ? snapValue(p.y, snapGrid) : p.y,
                z: snapGrid > 0 ? snapValue(p.z, snapGrid) : p.z
              },
              rotation: { x: r.x, y: r.y, z: r.z },
              scale: { x: s.x, y: s.y, z: s.z }
            });
          }}
        />
      )}
    </group>
  );
}

// ── Scene Component ──
function Scene({
  products, selectedId, multiSelectedIds, onSelect,
  onTransformChange, transformMode, wireframe, snapGrid,
  orbitRef, assemblies, cameraTrigger, onBoundingBox
}) {
  return (
    <>
      <ambientLight intensity={0.6} />
      <directionalLight position={[10, 10, 5]} intensity={0.8} castShadow />
      <directionalLight position={[-10, -10, -5]} intensity={0.3} />
      <hemisphereLight intensity={0.4} groundColor="#1a1d24" />

      <Grid
        args={[100, 100]}
        cellSize={10}
        cellThickness={0.5}
        cellColor="#6e6e6e"
        sectionSize={50}
        sectionThickness={1}
        sectionColor="#9d9d9d"
        fadeDistance={400}
        fadeStrength={1}
        followCamera={false}
        infiniteGrid={true}
      />

      {products.map((product, idx) => {
        const assembly = assemblies.find(a =>
          a.parentInstanceId === product.instanceId ||
          a.childInstanceIds?.includes(product.instanceId)
        );
        return (
          <DraggableModel
            key={product.instanceId}
            instanceId={product.instanceId}
            url={product.stlUrl}
            position={product.position || { x: idx * 100, y: 0, z: 0 }}
            rotation={product.rotation || { x: 0, y: 0, z: 0 }}
            scale={product.scale || { x: 1, y: 1, z: 1 }}
            color={product.color || PRODUCT_COLORS[idx % PRODUCT_COLORS.length]}
            wireframe={wireframe}
            isSelected={product.instanceId === selectedId}
            isMultiSelected={multiSelectedIds.includes(product.instanceId)}
            onSelect={onSelect}
            onTransformChange={onTransformChange}
            transformMode={transformMode}
            snapGrid={snapGrid}
            orbitRef={orbitRef}
            assemblyId={assembly?.assemblyId}
            onBoundingBox={onBoundingBox}
          />
        );
      })}

      <CameraFitter products={products} trigger={cameraTrigger} />
    </>
  );
}

// ── Main Multi-Product Canvas Component ──
function MultiProductCanvas({ sceneId, initialProducts = [] }) {
  const [products, setProducts] = useState(initialProducts);
  const [selectedId, setSelectedId] = useState(null);
  const [multiSelectedIds, setMultiSelectedIds] = useState([]);
  const [transformMode, setTransformMode] = useState('translate');
  const [wireframe, setWireframe] = useState(false);
  const [assemblies, setAssemblies] = useState([]);
  const [snapGrid, setSnapGrid] = useState(0);
  const [cameraTrigger, setCameraTrigger] = useState(0);
  const [showPrecision, setShowPrecision] = useState(true);
  const [decimals, setDecimals] = useState(1);
  const [lockedAxes, setLockedAxes] = useState({ x: false, y: false, z: false });
  const [nudgeAmount, setNudgeAmount] = useState(5);
  const [boundingBoxes, setBoundingBoxes] = useState({});
  const orbitRef = useRef();

  const handleBoundingBox = useCallback((instanceId, size) => {
    setBoundingBoxes(prev => ({ ...prev, [instanceId]: size }));
  }, []);

  // Sync with parent & auto-fit camera
  useEffect(() => {
    setProducts(initialProducts);
    if (initialProducts.length > 0) setCameraTrigger(c => c + 1);
  }, [initialProducts]);

  // ── Keyboard Shortcuts + Arrow-key nudge ──
  useEffect(() => {
    const onKeyDown = (e) => {
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) return;

      // Arrow-key precision nudging
      if (['arrowup', 'arrowdown', 'arrowleft', 'arrowright'].includes(e.key.toLowerCase()) && selectedId) {
        e.preventDefault();
        const product = products.find(p => p.instanceId === selectedId);
        if (!product) return;
        const amount = (e.shiftKey ? 10 : 1) * nudgeAmount;
        const pos = { ...(product.position || { x: 0, y: 0, z: 0 }) };

        switch (e.key) {
          case 'ArrowRight': if (!lockedAxes.x) pos.x += amount; break;
          case 'ArrowLeft':  if (!lockedAxes.x) pos.x -= amount; break;
          case 'ArrowUp':    if (!lockedAxes.z) pos.z -= amount; break;
          case 'ArrowDown':  if (!lockedAxes.z) pos.z += amount; break;
          default: break;
        }
        handleTransformChange(selectedId, { position: pos, rotation: product.rotation, scale: product.scale });
        return;
      }

      switch (e.key.toLowerCase()) {
        case 'g': setTransformMode('translate'); break;
        case 'r': setTransformMode('rotate'); break;
        case 's':
          if (!e.ctrlKey && !e.metaKey) setTransformMode('scale');
          break;
        case 'delete':
        case 'backspace':
          if (selectedId || multiSelectedIds.length > 0) handleDeleteSelected();
          break;
        case 'd':
          if (e.ctrlKey || e.metaKey) { e.preventDefault(); handleDuplicate(); }
          break;
        case 'a':
          if (e.ctrlKey || e.metaKey) {
            e.preventDefault();
            setMultiSelectedIds(products.map(p => p.instanceId));
            if (products.length > 0) setSelectedId(products[0].instanceId);
          }
          break;
        case 'escape':
          setSelectedId(null);
          setMultiSelectedIds([]);
          break;
        case 'f':
          setCameraTrigger(c => c + 1);
          break;
        case 'p':
          setShowPrecision(prev => !prev);
          break;
        default: break;
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [selectedId, multiSelectedIds, products, nudgeAmount, lockedAxes]); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Transform ──
  const handleTransformChange = useCallback((instanceId, transform) => {
    setProducts(prev => prev.map(p => p.instanceId === instanceId ? { ...p, ...transform } : p));
    if (sceneId) {
      fetch(`http://localhost:3001/api/scene/product/${instanceId}/transform`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(transform)
      }).catch(err => console.error('Transform update failed:', err));
    }
  }, [sceneId]);

  // ── Select / Multi-Select ──
  const handleSelect = useCallback((instanceId, isCtrl) => {
    if (isCtrl) {
      setMultiSelectedIds(prev =>
        prev.includes(instanceId) ? prev.filter(id => id !== instanceId) : [...prev, instanceId]
      );
      setSelectedId(instanceId);
    } else {
      setSelectedId(prev => prev === instanceId ? null : instanceId);
      setMultiSelectedIds([]);
    }
  }, []);

  // ── Duplicate ──
  const handleDuplicate = useCallback(() => {
    if (!selectedId) return;
    const selected = products.find(p => p.instanceId === selectedId);
    if (!selected) return;

    const offset = {
      x: (selected.position?.x || 0) + 50,
      y: selected.position?.y || 0,
      z: selected.position?.z || 0
    };

    fetch(`http://localhost:3001/api/scene/product/${selectedId}/duplicate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ offset })
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          const newProduct = {
            ...selected,
            instanceId: data.duplicate.instanceId,
            instanceName: (selected.instanceName || 'Product') + ' (Copy)',
            position: offset,
            color: PRODUCT_COLORS[products.length % PRODUCT_COLORS.length]
          };
          setProducts(prev => [...prev, newProduct]);
          setSelectedId(data.duplicate.instanceId);
        }
      })
      .catch(err => console.error('Duplicate failed:', err));
  }, [selectedId, products]);

  // ── Delete (multi-aware) ──
  const handleDeleteSelected = useCallback(() => {
    const ids = multiSelectedIds.length > 0
      ? multiSelectedIds
      : (selectedId ? [selectedId] : []);
    if (ids.length === 0) return;

    ids.forEach(id => {
      fetch(`http://localhost:3001/api/scene/product/${id}`, { method: 'DELETE' })
        .catch(err => console.error('Delete failed:', err));
    });
    setProducts(prev => prev.filter(p => !ids.includes(p.instanceId)));
    setSelectedId(null);
    setMultiSelectedIds([]);
  }, [selectedId, multiSelectedIds]);

  // ── Assemble (multi-select aware) ──
  const handleAssemble = useCallback(() => {
    if (!sceneId || products.length < 2) return;

    let selected = multiSelectedIds.length >= 2
      ? products.filter(p => multiSelectedIds.includes(p.instanceId))
      : [];

    if (selected.length < 2) {
      alert('Select at least 2 products to assemble.\nUse Ctrl+Click to multi-select, then click 🔗 Assemble.');
      return;
    }

    fetch(`http://localhost:3001/api/scene/${sceneId}/assemble`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: 'Assembly',
        parentInstanceId: selected[0].instanceId,
        childInstanceIds: selected.slice(1).map(p => p.instanceId)
      })
    })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          setAssemblies(prev => [...prev, data.assembly]);
          setMultiSelectedIds([]);
        }
      })
      .catch(err => console.error('Assembly failed:', err));
  }, [sceneId, products, multiSelectedIds]);

  // ── Disassemble ──
  const handleDisassemble = useCallback(() => {
    if (!selectedId || assemblies.length === 0) return;
    const assembly = assemblies.find(a =>
      a.parentInstanceId === selectedId || a.childInstanceIds?.includes(selectedId)
    );
    if (!assembly) { alert('Selected product is not part of an assembly'); return; }

    fetch(`http://localhost:3001/api/scene/assembly/${assembly.assemblyId}`, { method: 'DELETE' })
      .then(res => res.json())
      .then(data => {
        if (data.success) setAssemblies(prev => prev.filter(a => a.assemblyId !== assembly.assemblyId));
      })
      .catch(err => console.error('Disassembly failed:', err));
  }, [selectedId, assemblies]);

  // ── Alignment helpers ──
  const getSelectedProducts = useCallback(() => {
    const ids = multiSelectedIds.length > 0 ? multiSelectedIds : (selectedId ? [selectedId] : []);
    return products.filter(p => ids.includes(p.instanceId));
  }, [products, selectedId, multiSelectedIds]);

  const handleAlign = useCallback((axis, mode) => {
    const sel = getSelectedProducts();
    if (sel.length < 2) { alert('Select 2+ products to align (Ctrl+Click).'); return; }

    const vals = sel.map(p => p.position?.[axis] || 0);
    let target;

    if (mode === 'distribute') {
      const sorted = [...sel].sort((a, b) => (a.position?.[axis] || 0) - (b.position?.[axis] || 0));
      const lo = sorted[0].position?.[axis] || 0;
      const hi = sorted[sorted.length - 1].position?.[axis] || 0;
      const step = (hi - lo) / (sorted.length - 1);
      sorted.forEach((p, i) => {
        const newPos = { ...(p.position || { x: 0, y: 0, z: 0 }), [axis]: lo + i * step };
        handleTransformChange(p.instanceId, { position: newPos, rotation: p.rotation, scale: p.scale });
      });
      return;
    }

    if (mode === 'min') target = Math.min(...vals);
    else if (mode === 'max') target = Math.max(...vals);
    else target = (Math.min(...vals) + Math.max(...vals)) / 2;

    sel.forEach(p => {
      const newPos = { ...(p.position || { x: 0, y: 0, z: 0 }), [axis]: target };
      handleTransformChange(p.instanceId, { position: newPos, rotation: p.rotation, scale: p.scale });
    });
  }, [getSelectedProducts, handleTransformChange]);

  const handleResetPosition = useCallback(() => {
    if (!selectedId) return;
    handleTransformChange(selectedId, {
      position: { x: 0, y: 0, z: 0 },
      rotation: { x: 0, y: 0, z: 0 },
      scale: { x: 1, y: 1, z: 1 }
    });
  }, [selectedId, handleTransformChange]);

  const handleSpreadProducts = useCallback(() => {
    if (products.length < 2) return;
    const spacing = 80;
    products.forEach((p, i) => {
      const newPos = { x: i * spacing - ((products.length - 1) * spacing) / 2, y: 0, z: 0 };
      handleTransformChange(p.instanceId, { position: newPos, rotation: p.rotation || { x: 0, y: 0, z: 0 }, scale: p.scale || { x: 1, y: 1, z: 1 } });
    });
  }, [products, handleTransformChange]);

  const hasMulti = multiSelectedIds.length >= 2;
  const selCount = multiSelectedIds.length > 0 ? multiSelectedIds.length : (selectedId ? 1 : 0);

  return (
    <div className="multi-product-canvas">
      <div className="canvas-toolbar">
        {/* Transform */}
        <div className="transform-controls">
          <button className={transformMode === 'translate' ? 'active' : ''} onClick={() => setTransformMode('translate')} title="Move (G)">↔️ Move</button>
          <button className={transformMode === 'rotate' ? 'active' : ''} onClick={() => setTransformMode('rotate')} title="Rotate (R)">🔄 Rotate</button>
          <button className={transformMode === 'scale' ? 'active' : ''} onClick={() => setTransformMode('scale')} title="Scale (S)">⤢ Scale</button>
        </div>

        {/* Snap */}
        <div className="snap-controls">
          <button className={snapGrid > 0 ? 'active' : ''} onClick={() => setSnapGrid(prev => prev > 0 ? 0 : 10)} title="Toggle snap-to-grid">
            🧲 {snapGrid > 0 ? `Snap ${snapGrid}` : 'Snap'}
          </button>
          {snapGrid > 0 && (
            <select value={snapGrid} onChange={(e) => setSnapGrid(Number(e.target.value))} className="snap-select">
              <option value={5}>5mm</option>
              <option value={10}>10mm</option>
              <option value={25}>25mm</option>
              <option value={50}>50mm</option>
            </select>
          )}
        </div>

        {/* View */}
        <div className="view-controls">
          <button onClick={() => setWireframe(!wireframe)} title="Toggle wireframe">{wireframe ? '🔲 Solid' : '📐 Wire'}</button>
          <button onClick={() => setCameraTrigger(c => c + 1)} title="Fit camera to scene (F)">🎯 Fit</button>
          <button className={showPrecision ? 'active' : ''} onClick={() => setShowPrecision(!showPrecision)} title="Toggle precision panel (P)">📐 Precise</button>
        </div>

        {/* Product actions */}
        <div className="product-controls">
          <button onClick={handleDuplicate} disabled={!selectedId} title="Duplicate (Ctrl+D)">📋 Duplicate</button>
          <button onClick={handleDeleteSelected} disabled={selCount === 0} className="danger" title="Delete (Del)">🗑️ Delete{selCount > 1 ? ` (${selCount})` : ''}</button>
          <button onClick={handleResetPosition} disabled={!selectedId} title="Reset to origin">📍 Reset</button>
        </div>

        {/* Assembly */}
        <div className="assembly-controls">
          <button onClick={handleAssemble} disabled={!hasMulti} title="Group into assembly">🔗 Assemble{hasMulti ? ` (${multiSelectedIds.length})` : ''}</button>
          <button onClick={handleDisassemble} disabled={!selectedId} title="Break assembly apart">🔓 Break</button>
        </div>

        {/* Align (shown when multi-selected or 2+ products) */}
        {(hasMulti || products.length >= 2) && (
          <div className="align-controls">
            <button onClick={() => handleAlign('x', 'min')} disabled={!hasMulti} title="Align left (X min)">⬅ Left</button>
            <button onClick={() => handleAlign('x', 'center')} disabled={!hasMulti} title="Align center X">⬌ Center</button>
            <button onClick={() => handleAlign('x', 'max')} disabled={!hasMulti} title="Align right (X max)">➡ Right</button>
            <button onClick={() => handleAlign('x', 'distribute')} disabled={!hasMulti} title="Distribute evenly along X">⟺ Distribute</button>
            <button onClick={handleSpreadProducts} disabled={products.length < 2} title="Spread all products apart">↔ Spread</button>
          </div>
        )}
      </div>

      <div className="canvas-wrapper">
        {products.length === 0 && (
          <div className="empty-workspace">
            <div className="empty-ws-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.2">
                <path d="M12 2L2 7l10 5 10-5-10-5z"/>
                <path d="M2 17l10 5 10-5"/>
                <path d="M2 12l10 5 10-5"/>
              </svg>
            </div>
            <h3>Your 3D model will appear here</h3>
            <p>Type what you want to build in the chat on the left, and your design will load right here.</p>
            <div className="empty-ws-controls">
              <span>🖱️ Drag to orbit</span>
              <span>🔍 Scroll to zoom</span>
              <span>👆 Click to select</span>
              <span>⌨️ Ctrl+Click multi-select</span>
            </div>
          </div>
        )}
        <Canvas onPointerMissed={() => { setSelectedId(null); setMultiSelectedIds([]); }}>
          <PerspectiveCamera makeDefault position={[400, 300, 400]} fov={50} />
          <Scene
            products={products}
            selectedId={selectedId}
            multiSelectedIds={multiSelectedIds}
            onSelect={handleSelect}
            onTransformChange={handleTransformChange}
            transformMode={transformMode}
            wireframe={wireframe}
            snapGrid={snapGrid}
            orbitRef={orbitRef}
            assemblies={assemblies}
            cameraTrigger={cameraTrigger}
            onBoundingBox={handleBoundingBox}
          />
          <OrbitControls
            ref={orbitRef}
            makeDefault
            minDistance={10}
            maxDistance={2000}
            enableDamping={true}
            dampingFactor={0.05}
          />
        </Canvas>
      </div>

      {showPrecision && selectedId && (
        <PrecisionPanel
          selectedProduct={products.find(p => p.instanceId === selectedId)}
          onTransformChange={handleTransformChange}
          decimals={decimals}
          setDecimals={setDecimals}
          lockedAxes={lockedAxes}
          setLockedAxes={setLockedAxes}
          nudgeAmount={nudgeAmount}
          setNudgeAmount={setNudgeAmount}
          boundingBox={boundingBoxes[selectedId]}
        />
      )}

      <div className="scene-info">
        <p>Products: {products.length}{assemblies.length > 0 ? ` · Assemblies: ${assemblies.length}` : ''}</p>
        {selCount > 0 && (
          <p>Selected: {selCount > 1
            ? `${selCount} products`
            : (products.find(p => p.instanceId === selectedId)?.instanceName || 'Product')
          }</p>
        )}
        {selectedId && products.find(p => p.instanceId === selectedId)?.position && (
          <p className="position-info">
            Pos: {toFixed(products.find(p => p.instanceId === selectedId).position.x, decimals)},
            {toFixed(products.find(p => p.instanceId === selectedId).position.y, decimals)},
            {toFixed(products.find(p => p.instanceId === selectedId).position.z, decimals)}
          </p>
        )}
        {snapGrid > 0 && <p className="snap-indicator">🧲 Snap: {snapGrid}mm</p>}
        {Object.values(lockedAxes).some(v => v) && (
          <p className="lock-indicator">🔒 Locked: {Object.entries(lockedAxes).filter(([,v]) => v).map(([k]) => k.toUpperCase()).join(', ')}</p>
        )}
      </div>
    </div>
  );
}

export default MultiProductCanvas;
